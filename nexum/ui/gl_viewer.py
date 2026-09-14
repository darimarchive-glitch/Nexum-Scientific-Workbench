from __future__ import annotations
import math
import ctypes
import numpy as np

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from OpenGL import GL
from OpenGL.GL import shaders

from nexum.core.structures import (
    Molecule, element_color, vdw_radius, build_ribbon_mesh, backbone_traces,
    molecule_center_radius, CHAIN_COLORS,
)


POINT_VS = r"""
#version 330 core
layout(location=0) in vec3 a_pos;
layout(location=1) in vec3 a_color;
layout(location=2) in float a_radius;
uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_proj;
uniform float u_point_scale;
out vec3 v_color;
out float v_eye_z;
out float v_radius;
void main(){
    vec4 world = u_model * vec4(a_pos,1.0);
    vec4 eye = u_view * world;
    gl_Position = u_proj * eye;
    gl_PointSize = clamp(2.0*a_radius * u_point_scale / max(0.1,-eye.z), 2.0, 180.0);
    v_color = a_color;
    v_eye_z = eye.z;
    v_radius = a_radius;
}
"""
POINT_FS = r"""
#version 330 core
in vec3 v_color;
in float v_eye_z;
in float v_radius;
uniform mat4 u_proj;
uniform vec3 u_bg;
uniform float u_fog_near;
uniform float u_fog_far;
uniform bool u_fog;
uniform float u_alpha;
uniform bool u_influence;
uniform bool u_clip; uniform float u_clip_depth;
out vec4 frag;
void main(){
    vec2 q = gl_PointCoord*2.0-1.0;
    float rr = dot(q,q);
    if(rr>1.0) discard;
    float sphere_z = sqrt(max(0.0,1.0-rr));
    vec3 n = normalize(vec3(q.x,-q.y,sphere_z));
    vec3 light = normalize(vec3(-0.38,0.58,0.72));
    float diffuse = 0.27 + 0.73*max(0.0,dot(n,light));
    float rim = pow(1.0-max(0.0,n.z),2.2)*0.12;
    float spec = pow(max(0.0,dot(reflect(-light,n),vec3(0,0,1))),30.0)*0.32;
    vec3 c = v_color*diffuse + vec3(spec+rim);

    // Point sprites are billboards.  Write the depth of the spherical surface, not
    // the flat billboard plane, so overlapping atoms occlude one another correctly.
    float eye_z = v_eye_z + sphere_z*v_radius;
    vec4 clip = u_proj * vec4(0.0,0.0,eye_z,1.0);
    float ndc_z = clip.z / clip.w;
    gl_FragDepth = clamp(ndc_z*0.5+0.5,0.0,1.0);

    float depth = -eye_z;
    if(u_clip && depth<u_clip_depth)discard;
    if(u_fog){ float f=smoothstep(u_fog_near,u_fog_far,depth); c=mix(c,u_bg,f); }
    float alpha=u_alpha;
    if(u_influence){
        float rim=smoothstep(0.55,0.98,rr);
        bool dark=dot(u_bg,vec3(.2126,.7152,.0722))<.45;
        vec3 outline=dark?vec3(.30,.78,.90):vec3(.06,.25,.38);
        c=mix(c,outline,rim*.85);
        alpha=mix(u_alpha,min(.90,u_alpha+.38),rim);
    }
    frag=vec4(c,alpha);
}
"""
LINE_VS = r"""
#version 330 core
layout(location=0) in vec3 a_pos;
layout(location=1) in vec3 a_color;
uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_proj;
out vec3 v_color;
out float v_depth;
void main(){ vec4 eye=u_view*u_model*vec4(a_pos,1); gl_Position=u_proj*eye; v_color=a_color; v_depth=-eye.z; }
"""
LINE_FS = r"""
#version 330 core
in vec3 v_color; in float v_depth;
uniform vec3 u_bg; uniform float u_fog_near; uniform float u_fog_far; uniform bool u_fog;
uniform bool u_clip; uniform float u_clip_depth;
out vec4 frag;
void main(){ if(u_clip && v_depth<u_clip_depth)discard; vec3 c=v_color; if(u_fog){float f=smoothstep(u_fog_near,u_fog_far,v_depth); c=mix(c,u_bg,f);} frag=vec4(c,1.0); }
"""
RIBBON_VS = r"""
#version 330 core
layout(location=0) in vec3 a_pos;
layout(location=1) in vec3 a_normal;
layout(location=2) in vec3 a_color;
uniform mat4 u_model; uniform mat4 u_view; uniform mat4 u_proj;
out vec3 v_color; out vec3 v_normal; out float v_depth;
void main(){
  vec4 eye=u_view*u_model*vec4(a_pos,1); gl_Position=u_proj*eye;
  v_normal=mat3(u_view*u_model)*a_normal; v_color=a_color; v_depth=-eye.z;
}
"""
RIBBON_FS = r"""
#version 330 core
in vec3 v_color; in vec3 v_normal; in float v_depth;
uniform vec3 u_bg; uniform float u_fog_near; uniform float u_fog_far; uniform bool u_fog;
uniform float u_alpha; uniform bool u_clip; uniform float u_clip_depth;
out vec4 frag;
void main(){
  if(u_clip && v_depth<u_clip_depth)discard;
  vec3 n=normalize(v_normal); if(!gl_FrontFacing)n=-n;
  vec3 light=normalize(vec3(-0.3,0.6,0.75));
  float d=.34+.66*max(0,dot(n,light)); vec3 c=v_color*d;
  if(u_fog){float f=smoothstep(u_fog_near,u_fog_far,v_depth);c=mix(c,u_bg,f);} frag=vec4(c,u_alpha);
}
"""


def _perspective(fovy, aspect, near, far):
    f=1.0/math.tan(fovy/2);m=np.zeros((4,4),dtype=np.float32)
    m[0,0]=f/aspect;m[1,1]=f;m[2,2]=(far+near)/(near-far);m[2,3]=(2*far*near)/(near-far);m[3,2]=-1
    return m


def _translate(x,y,z):
    m=np.eye(4,dtype=np.float32);m[:3,3]=(x,y,z);return m


def _rotate_x(a):
    c,s=math.cos(a),math.sin(a);m=np.eye(4,dtype=np.float32);m[1,1]=c;m[1,2]=-s;m[2,1]=s;m[2,2]=c;return m


def _rotate_y(a):
    c,s=math.cos(a),math.sin(a);m=np.eye(4,dtype=np.float32);m[0,0]=c;m[0,2]=s;m[2,0]=-s;m[2,2]=c;return m


def _glmat(m):
    return np.ascontiguousarray(m.T,dtype=np.float32)


def _cylinder_mesh(p1, p2, radius, color, sides=10):
    """Return unindexed triangle geometry for an open cylinder.

    Used for bonds so ball-and-stick mode has real 3-D geometry rather than flat
    GL_LINES.  The function is intentionally small and CPU-side; small molecules and
    ligand bonds are well within this cost, while huge polymer views keep using their
    ribbon/backbone path.
    """
    p1=np.asarray(p1,dtype=np.float32);p2=np.asarray(p2,dtype=np.float32)
    axis=p2-p1;length=float(np.linalg.norm(axis))
    if length<1e-7:
        return np.empty((0,3),dtype=np.float32),np.empty((0,3),dtype=np.float32),np.empty((0,3),dtype=np.float32)
    d=axis/length
    helper=np.array((1,0,0),dtype=np.float32) if abs(float(d[0]))<.82 else np.array((0,1,0),dtype=np.float32)
    u=np.cross(d,helper);u/=max(float(np.linalg.norm(u)),1e-8)
    v=np.cross(d,u);v/=max(float(np.linalg.norm(v)),1e-8)
    verts=[];norms=[];cols=[]
    c=np.asarray(color,dtype=np.float32)
    for i in range(max(6,int(sides))):
        a0=2*math.pi*i/sides;a1=2*math.pi*(i+1)/sides
        n0=u*math.cos(a0)+v*math.sin(a0);n1=u*math.cos(a1)+v*math.sin(a1)
        q10=p1+n0*radius;q11=p1+n1*radius;q20=p2+n0*radius;q21=p2+n1*radius
        verts.extend((q10,q20,q11,q11,q20,q21))
        norms.extend((n0,n0,n1,n1,n0,n1))
        cols.extend((c,c,c,c,c,c))
    return np.asarray(verts,dtype=np.float32),np.asarray(norms,dtype=np.float32),np.asarray(cols,dtype=np.float32)


class GLMoleculeView(Gtk.GLArea):
    """Native OpenGL molecular/macromolecular viewer for GTK4.

    Small molecules use shaded point-sphere atoms and bonds. Polymers use a real 3-D
    triangle ribbon built from CA/P coordinates, with ligands rendered independently.
    """
    def __init__(self):
        super().__init__()
        self.set_hexpand(True);self.set_vexpand(True);self.set_auto_render(True)
        self.set_required_version(3,3)
        self.set_use_es(False)
        # Gtk.GLArea does not guarantee a depth attachment unless explicitly requested.
        # Without it, rotation looks flat because later fragments can paint over nearer ones.
        self.set_has_depth_buffer(True)
        self.molecule: Molecule|None=None
        self.representation="ribbon";self.show_hydrogens=False;self.show_ligands=True;self.fog=True
        self.show_influence=False;self.influence_opacity=0.22
        self.visible_chains=None
        self.selection=set();self.color_mode="element";self.surface_mesh=None;self.surface_opacity=.35
        self.clip_enabled=False;self.clip_fraction=.5;self.camera_callback=None;self._export_size=None
        self.dark=False;self.bg=(0.965,0.961,0.949)
        self.center=np.zeros(3,dtype=np.float32);self.radius=10.0;self.distance=28.0;self.zoom=1.0
        self.rot_x=-0.22;self.rot_y=0.52;self.drag_base=(0,0);self.fov_deg=38.0
        self.selected_index=None;self.selection_callback=None
        self.programs={};self.buffers={};self.scene={}
        self.connect("realize",self._realize);self.connect("unrealize",self._unrealize);self.connect("render",self._render)
        drag=Gtk.GestureDrag.new();drag.connect("drag-begin",self._drag_begin);drag.connect("drag-update",self._drag_update);self.add_controller(drag)
        scroll=Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL);scroll.connect("scroll",self._scroll);self.add_controller(scroll)
        click=Gtk.GestureClick.new();click.connect("released",self._click);self.add_controller(click)

    def set_dark(self,dark:bool):
        self.dark=bool(dark);self.bg=(0.105,0.105,0.105) if self.dark else (0.965,0.961,0.949);self.queue_render()

    def set_fov(self,degrees:float):
        self.fov_deg=clamp_float(float(degrees),26.0,62.0);self.queue_render()

    def set_molecule(self,mol:Molecule):
        self.selection=set();self.surface_mesh=None
        self.molecule=mol;self.center,self.radius=molecule_center_radius(mol);self.fit();self.rebuild_scene();self.queue_render()

    def fit(self):
        self.zoom=1.0;self.distance=max(8.0,self.radius*2.55);self.rot_x=-0.24;self.rot_y=0.58;self.queue_render()

    def configure(self,representation=None,show_hydrogens=None,show_ligands=None,fog=None,visible_chains=None,show_influence=None,influence_opacity=None):
        if representation is not None:self.representation=representation
        if show_hydrogens is not None:self.show_hydrogens=show_hydrogens
        if show_ligands is not None:self.show_ligands=show_ligands
        if fog is not None:self.fog=fog
        if show_influence is not None:self.show_influence=bool(show_influence)
        if influence_opacity is not None:
            value=float(influence_opacity)
            if not math.isfinite(value):raise ValueError('Opacidade deve ser finita.')
            self.influence_opacity=clamp_float(value,0.05,0.60)
        if visible_chains is not None:self.visible_chains=visible_chains
        self.rebuild_scene();self.queue_render()

    def _realize(self,*_):
        self.make_current()
        if self.get_error():return
        self.programs["points"]=shaders.compileProgram(shaders.compileShader(POINT_VS,GL.GL_VERTEX_SHADER),shaders.compileShader(POINT_FS,GL.GL_FRAGMENT_SHADER))
        self.programs["lines"]=shaders.compileProgram(shaders.compileShader(LINE_VS,GL.GL_VERTEX_SHADER),shaders.compileShader(LINE_FS,GL.GL_FRAGMENT_SHADER))
        self.programs["ribbon"]=shaders.compileProgram(shaders.compileShader(RIBBON_VS,GL.GL_VERTEX_SHADER),shaders.compileShader(RIBBON_FS,GL.GL_FRAGMENT_SHADER))
        GL.glEnable(GL.GL_DEPTH_TEST);GL.glDepthFunc(GL.GL_LEQUAL);GL.glEnable(GL.GL_PROGRAM_POINT_SIZE);GL.glDisable(GL.GL_CULL_FACE);GL.glEnable(GL.GL_MULTISAMPLE)
        self.rebuild_scene()

    def _unrealize(self,*_):
        self.make_current()
        for p in self.programs.values():
            try:GL.glDeleteProgram(p)
            except Exception:pass
        self.programs.clear()

    def _atom_visible(self,a):
        if not self.show_hydrogens and a.element=="H":return False
        if not self.show_ligands and a.hetero:return False
        if self.visible_chains is not None and a.chain not in self.visible_chains:return False
        return True

    def rebuild_scene(self):
        if not self.molecule:return
        m=self.molecule;rep=self.representation
        self._atom_indices={id(a):i for i,a in enumerate(m.atoms)}
        self._chain_colors={v:CHAIN_COLORS[i%len(CHAIN_COLORS)] for i,v in enumerate(sorted({a.chain for a in m.atoms}))}
        self._residue_colors={v:CHAIN_COLORS[i%len(CHAIN_COLORS)] for i,v in enumerate(sorted({a.residue for a in m.atoms}))}
        self._charge_colors=None
        if self.color_mode=="charge" and len(m.metadata.get("partial_charges",[]))==len(m.atoms):
            from nexum.core.molecular_analysis import scalar_colors
            self._charge_colors=scalar_colors(m.metadata["partial_charges"])[0]
        idx=[]
        polymer=m.metadata.get("polymer_backbone_atoms",0)>2
        for i,a in enumerate(m.atoms):
            if not self._atom_visible(a):continue
            if polymer and rep=="ribbon" and not a.hetero:continue
            if polymer and rep=="backbone" and not a.hetero:continue
            idx.append(i)
        pos=[];col=[];rad=[]
        for i in idx:
            a=m.atoms[i];pos.append((a.x,a.y,a.z));col.append(self._atom_color(a))
            if rep=="spacefill":r=vdw_radius(a.element)
            elif polymer and a.hetero:r=0.38*vdw_radius(a.element)
            else:r=0.30*vdw_radius(a.element)
            rad.append(r)
        self.scene["point_indices"]=idx;self.scene["point_pos"]=np.asarray(pos,dtype=np.float32);self.scene["point_col"]=np.asarray(col,dtype=np.float32);self.scene["point_rad"]=np.asarray(rad,dtype=np.float32)
        # The overlay follows visibility filters but is independent of the base
        # representation, including polymer atoms when ribbons are selected.
        visible=[a for a in m.atoms if self._atom_visible(a)] if self.show_influence else []
        self.scene["influence_pos"]=np.asarray([(a.x,a.y,a.z) for a in visible],dtype=np.float32).reshape((-1,3))
        self.scene["influence_col"]=np.asarray([self._atom_color(a) for a in visible],dtype=np.float32).reshape((-1,3))
        self.scene["influence_rad"]=np.asarray([vdw_radius(a.element) for a in visible],dtype=np.float32)
        # Bonds: real cylinders for normal ball/stick views; GL lines remain the
        # scalable fallback for very large scenes and the explicit Lines mode.
        line_pos=[];line_col=[];bond_v=[];bond_n=[];bond_c=[]
        vis=set(idx)
        visible_bonds=[(i,j,o) for i,j,o in m.bonds if i in vis and j in vis]
        use_cylinders=rep in ("ball-stick","sticks","ribbon","backbone") and len(visible_bonds)<=6000
        cylinder_radius=.16 if rep=="sticks" else .105 if rep=="ball-stick" else .09
        for i,j,_order in visible_bonds:
            atom_i,atom_j=m.atoms[i],m.atoms[j];ci,cj=self._atom_color(atom_i),self._atom_color(atom_j)
            p1=np.array((atom_i.x,atom_i.y,atom_i.z),dtype=np.float32);p2=np.array((atom_j.x,atom_j.y,atom_j.z),dtype=np.float32);mid=(p1+p2)*.5
            if use_cylinders:
                for a,b,c in ((p1,mid,ci),(mid,p2,cj)):
                    vv,nn,cc=_cylinder_mesh(a,b,cylinder_radius,c,10);bond_v.extend(vv);bond_n.extend(nn);bond_c.extend(cc)
            else:
                line_pos.extend((p1,mid,mid,p2));line_col.extend((ci,ci,cj,cj))
        self.scene["bond_vertices"]=np.asarray(bond_v,dtype=np.float32).reshape((-1,3)) if bond_v else np.empty((0,3),dtype=np.float32)
        self.scene["bond_normals"]=np.asarray(bond_n,dtype=np.float32).reshape((-1,3)) if bond_n else np.empty((0,3),dtype=np.float32)
        self.scene["bond_colors"]=np.asarray(bond_c,dtype=np.float32).reshape((-1,3)) if bond_c else np.empty((0,3),dtype=np.float32)
        self.scene["line_pos"]=np.asarray(line_pos,dtype=np.float32).reshape((-1,3)) if line_pos else np.empty((0,3),dtype=np.float32)
        self.scene["line_col"]=np.asarray(line_col,dtype=np.float32).reshape((-1,3)) if line_col else np.empty((0,3),dtype=np.float32)
        # Backbone/ribbon are derived from real 3-D polymer coordinates.
        self.scene["ribbons"]=[];self.scene["backbone_pos"]=np.empty((0,3),dtype=np.float32);self.scene["backbone_col"]=np.empty((0,3),dtype=np.float32)
        if polymer:
            if rep=="ribbon":
                meshes=build_ribbon_mesh(m,width=max(1.25,min(2.05,self.radius/24)),subdivisions=6,thickness=max(.16,min(.34,self.radius/150)))
                if self.visible_chains is not None:meshes=[x for x in meshes if x["chain"] in self.visible_chains]
                self.scene["ribbons"]=meshes
            if rep in ("backbone","lines"):
                bp=[];bc=[]
                for ci,(chain,trace) in enumerate(backbone_traces(m).items()):
                    if self.visible_chains is not None and chain not in self.visible_chains:continue
                    c=CHAIN_COLORS[ci%len(CHAIN_COLORS)]
                    for a,b in zip(trace[:-1],trace[1:]):bp.extend((a,b));bc.extend((c,c))
                self.scene["backbone_pos"]=np.asarray(bp,dtype=np.float32);self.scene["backbone_col"]=np.asarray(bc,dtype=np.float32)

    def _matrices(self):
        w,h=self._viewport_size();aspect=w/h
        near=max(.05,self.radius*.01);far=max(100.0,self.distance*self.zoom+self.radius*6)
        proj=_perspective(math.radians(self.fov_deg),aspect,near,far)
        view=_translate(0,0,-self.distance*self.zoom)
        model=_rotate_x(self.rot_x)@_rotate_y(self.rot_y)@_translate(-float(self.center[0]),-float(self.center[1]),-float(self.center[2]))
        return model,view,proj

    def _uniform_common(self,prog,model,view,proj):
        GL.glUniform1i(GL.glGetUniformLocation(prog,"u_influence"),0)
        GL.glUniform1f(GL.glGetUniformLocation(prog,"u_alpha"),1.)
        GL.glUniform1i(GL.glGetUniformLocation(prog,"u_clip"),int(self.clip_enabled))
        GL.glUniform1f(GL.glGetUniformLocation(prog,"u_clip_depth"),float(self.distance*self.zoom+self.radius*(2*self.clip_fraction-1)))
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog,"u_model"),1,False,_glmat(model))
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog,"u_view"),1,False,_glmat(view))
        GL.glUniformMatrix4fv(GL.glGetUniformLocation(prog,"u_proj"),1,False,_glmat(proj))
        bg=np.asarray(self.bg,dtype=np.float32);loc=GL.glGetUniformLocation(prog,"u_bg")
        if loc>=0:GL.glUniform3fv(loc,1,bg)
        depth=self.distance*self.zoom;near=max(0.0,depth-self.radius*.15);far=depth+self.radius*1.15
        for name,val in (("u_fog_near",near),("u_fog_far",far)):
            loc=GL.glGetUniformLocation(prog,name)
            if loc>=0:GL.glUniform1f(loc,float(val))
        loc=GL.glGetUniformLocation(prog,"u_fog")
        if loc>=0:GL.glUniform1i(loc,1 if self.fog else 0)

    @staticmethod
    def _array_buffer(data,attrib,size):
        if data is None or len(data)==0:return None
        buf=GL.glGenBuffers(1);GL.glBindBuffer(GL.GL_ARRAY_BUFFER,buf);GL.glBufferData(GL.GL_ARRAY_BUFFER,data.nbytes,data,GL.GL_STREAM_DRAW)
        GL.glEnableVertexAttribArray(attrib);GL.glVertexAttribPointer(attrib,size,GL.GL_FLOAT,False,0,ctypes.c_void_p(0));return buf

    def _render(self,area,context):
        if self.get_error():return False
        scale=self.get_scale_factor()
        GL.glViewport(0,0,*self._viewport_size())
        GL.glClearColor(*self.bg,1);GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
        if not self.molecule:return True
        model,view,proj=self._matrices()
        temp=[]
        # ribbons first
        if self.scene.get("ribbons"):
            prog=self.programs["ribbon"];GL.glUseProgram(prog);self._uniform_common(prog,model,view,proj)
            vao=GL.glGenVertexArrays(1);GL.glBindVertexArray(vao);temp.append(("vao",vao))
            for mesh in self.scene["ribbons"]:
                v=mesh["vertices"];n=mesh["normals"];c=np.tile(np.asarray(mesh["color"],dtype=np.float32),(len(v),1))
                bufs=[self._array_buffer(v,0,3),self._array_buffer(n,1,3),self._array_buffer(c,2,3)];temp.extend(("buf",b) for b in bufs if b)
                GL.glDrawArrays(GL.GL_TRIANGLES,0,len(v))
        # cylindrical bonds use the same lit mesh shader as ribbons
        bv=self.scene.get("bond_vertices")
        if bv is not None and len(bv):
            prog=self.programs["ribbon"];GL.glUseProgram(prog);self._uniform_common(prog,model,view,proj)
            vao=GL.glGenVertexArrays(1);GL.glBindVertexArray(vao);temp.append(("vao",vao))
            b1=self._array_buffer(bv,0,3);b2=self._array_buffer(self.scene["bond_normals"],1,3);b3=self._array_buffer(self.scene["bond_colors"],2,3);temp.extend(("buf",b) for b in (b1,b2,b3) if b)
            GL.glDrawArrays(GL.GL_TRIANGLES,0,len(bv))
        # line fallback / backbone
        lp=self.scene.get("line_pos");lc=self.scene.get("line_col");bp=self.scene.get("backbone_pos");bc=self.scene.get("backbone_col")
        if (lp is not None and len(lp)) or (bp is not None and len(bp)):
            prog=self.programs["lines"];GL.glUseProgram(prog);self._uniform_common(prog,model,view,proj);GL.glLineWidth(2.0)
            for p,c in ((lp,lc),(bp,bc)):
                if p is None or not len(p):continue
                vao=GL.glGenVertexArrays(1);GL.glBindVertexArray(vao);temp.append(("vao",vao));b1=self._array_buffer(p,0,3);b2=self._array_buffer(c,1,3);temp.extend(("buf",b) for b in (b1,b2) if b);GL.glDrawArrays(GL.GL_LINES,0,len(p))
        # atoms
        pp=self.scene.get("point_pos")
        if pp is not None and len(pp) and self.representation not in ("sticks","lines","backbone"):
            prog=self.programs["points"];GL.glUseProgram(prog);self._uniform_common(prog,model,view,proj)
            GL.glUniform1f(GL.glGetUniformLocation(prog,"u_alpha"),1.0)
            h=self._viewport_size()[1];scale=h/(2*math.tan(math.radians(self.fov_deg)/2));GL.glUniform1f(GL.glGetUniformLocation(prog,"u_point_scale"),float(scale))
            vao=GL.glGenVertexArrays(1);GL.glBindVertexArray(vao);temp.append(("vao",vao));
            b1=self._array_buffer(pp,0,3);b2=self._array_buffer(self.scene["point_col"],1,3);b3=self._array_buffer(self.scene["point_rad"],2,1);temp.extend(("buf",b) for b in (b1,b2,b3) if b);GL.glDrawArrays(GL.GL_POINTS,0,len(pp))
        # Draw transparent spheres after opaque geometry, back-to-front.
        # Keep depth testing against the base model, but never write overlay depth.
        influence=self.scene.get("influence_pos")
        if self.show_influence and influence is not None and len(influence):
            eye=(view@model)
            order=np.argsort(influence@eye[2,:3]+eye[2,3],kind="stable")
            prog=self.programs["points"];GL.glUseProgram(prog);self._uniform_common(prog,model,view,proj)
            GL.glUniform1i(GL.glGetUniformLocation(prog,"u_influence"),1)
            GL.glUniform1f(GL.glGetUniformLocation(prog,"u_alpha"),self.influence_opacity)
            h=self._viewport_size()[1]
            GL.glUniform1f(GL.glGetUniformLocation(prog,"u_point_scale"),float(h/(2*math.tan(math.radians(self.fov_deg)/2))))
            vao=GL.glGenVertexArrays(1);GL.glBindVertexArray(vao);temp.append(("vao",vao))
            bufs=[self._array_buffer(np.ascontiguousarray(influence[order]),0,3),
                  self._array_buffer(np.ascontiguousarray(self.scene["influence_col"][order]),1,3),
                  self._array_buffer(np.ascontiguousarray(self.scene["influence_rad"][order]),2,1)]
            temp.extend(("buf",b) for b in bufs if b)
            GL.glEnable(GL.GL_BLEND);GL.glBlendFunc(GL.GL_SRC_ALPHA,GL.GL_ONE_MINUS_SRC_ALPHA);GL.glDepthMask(False)
            try:
                GL.glDrawArrays(GL.GL_POINTS,0,len(influence))
            finally:
                GL.glDepthMask(True);GL.glDisable(GL.GL_BLEND)
                GL.glUniform1f(GL.glGetUniformLocation(prog,"u_alpha"),1.0)
        mesh=self.surface_mesh
        if mesh is not None and len(mesh["vertices"]):
            prog=self.programs["ribbon"];GL.glUseProgram(prog);self._uniform_common(prog,model,view,proj)
            vertices=mesh["vertices"].reshape(-1,3,3)
            eye=view@model
            order=np.argsort(vertices.mean(axis=1)@eye[2,:3]+eye[2,3])
            vao=GL.glGenVertexArrays(1);GL.glBindVertexArray(vao);temp.append(("vao",vao))
            for attribute,key in enumerate(("vertices","normals","colors")):
                data=np.ascontiguousarray(mesh[key].reshape(-1,3,3)[order].reshape(-1,3))
                buf=self._array_buffer(data,attribute,3);temp.append(("buf",buf))
            GL.glUniform1f(GL.glGetUniformLocation(prog,"u_alpha"),self.surface_opacity)
            GL.glEnable(GL.GL_BLEND);GL.glBlendFunc(GL.GL_SRC_ALPHA,GL.GL_ONE_MINUS_SRC_ALPHA);GL.glDepthMask(False)
            try:GL.glDrawArrays(GL.GL_TRIANGLES,0,len(mesh["vertices"]))
            finally:
                GL.glDepthMask(True);GL.glDisable(GL.GL_BLEND);GL.glUniform1f(GL.glGetUniformLocation(prog,"u_alpha"),1.)
        if len(self.selection)>1:
            chosen=[i for i in sorted(self.selection) if self._atom_visible(self.molecule.atoms[i])]
            positions=np.array([self.molecule.atoms[i].position for i in chosen],dtype=np.float32)
            if len(positions)>1:
                prog=self.programs["lines"];GL.glUseProgram(prog);self._uniform_common(prog,model,view,proj)
                vao=GL.glGenVertexArrays(1);GL.glBindVertexArray(vao);temp.append(("vao",vao))
                temp.extend(("buf",b) for b in (self._array_buffer(positions,0,3),self._array_buffer(np.tile(np.array([1.,.6,.05],dtype=np.float32),(len(positions),1)),1,3)) if b)
                GL.glDrawArrays(GL.GL_LINE_STRIP,0,len(positions))
        GL.glBindVertexArray(0);GL.glBindBuffer(GL.GL_ARRAY_BUFFER,0)
        for typ,obj in temp:
            try:
                if typ=="buf":GL.glDeleteBuffers(1,[obj])
                else:GL.glDeleteVertexArrays(1,[obj])
            except Exception:pass
        return True

    def _drag_begin(self,gesture,x,y):self.drag_base=(self.rot_x,self.rot_y)
    def _drag_update(self,gesture,dx,dy):
        self.rot_x=self.drag_base[0]+dy*.008;self.rot_y=self.drag_base[1]+dx*.008;self.queue_render();self._camera_changed()
    def _scroll(self,controller,dx,dy):
        self.zoom=clamp_float(self.zoom*math.exp(dy*.10),.25,5.0);self.queue_render();self._camera_changed();return True

    def _click(self,gesture,n_press,x,y):
        if not self.molecule:return
        idx=self._pick_atom(x,y)
        if idx is not None:
            self.selected_index=idx
            if self.selection_callback:self.selection_callback(idx,self.molecule.atoms[idx])

    def _pick_atom(self,x,y):
        m=self.molecule
        if not m:return None
        model,view,proj=self._matrices();mvp=proj@view@model;w=max(1,self.get_allocated_width());h=max(1,self.get_allocated_height())
        best=None;bestd=22.0**2
        indices=self.scene.get("point_indices",[])
        for i in indices:
            a=m.atoms[i];v=mvp@np.array((a.x,a.y,a.z,1),dtype=np.float32)
            if abs(float(v[3]))<1e-8:continue
            ndc=v[:3]/v[3]
            if ndc[2]<-1 or ndc[2]>1:continue
            eye=view@model@np.array((a.x,a.y,a.z,1),dtype=np.float32)
            if self.clip_enabled and -eye[2]<self.distance*self.zoom+self.radius*(2*self.clip_fraction-1):continue
            sx=(ndc[0]*.5+.5)*w;sy=(1-(ndc[1]*.5+.5))*h;d=(sx-x)**2+(sy-y)**2
            if d<bestd:bestd=d;best=i
        return best


    def _viewport_size(self):
        return self._export_size or (max(1,self.get_allocated_width()*self.get_scale_factor()),max(1,self.get_allocated_height()*self.get_scale_factor()))

    def _atom_color(self,a):
        i=self._atom_indices.get(id(a),-1)
        if i in self.selection:return (1.,.6,.05)
        if self.color_mode=="chain":
            return self._chain_colors[a.chain]
        if self.color_mode=="residue":
            return self._residue_colors[a.residue]
        if self.color_mode=="charge" and self._charge_colors is not None:return tuple(self._charge_colors[i])
        return element_color(a.element)

    def _camera_changed(self):
        if self.camera_callback:self.camera_callback(self)

    def export_png(self,path,scale=2):
        import cairo
        self.make_current()
        if self.get_error():raise RuntimeError(str(self.get_error()))
        old=GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING)
        w,h=self._viewport_size();factor=min(float(scale),4096/max(w,h))
        w,h=max(1,int(w*factor)),max(1,int(h*factor))
        fbo=GL.glGenFramebuffers(1);color=GL.glGenRenderbuffers(1);depth=GL.glGenRenderbuffers(1)
        try:
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,fbo)
            GL.glBindRenderbuffer(GL.GL_RENDERBUFFER,color);GL.glRenderbufferStorage(GL.GL_RENDERBUFFER,GL.GL_RGBA8,w,h)
            GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER,GL.GL_COLOR_ATTACHMENT0,GL.GL_RENDERBUFFER,color)
            GL.glBindRenderbuffer(GL.GL_RENDERBUFFER,depth);GL.glRenderbufferStorage(GL.GL_RENDERBUFFER,GL.GL_DEPTH_COMPONENT24,w,h)
            GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER,GL.GL_DEPTH_ATTACHMENT,GL.GL_RENDERBUFFER,depth)
            if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)!=GL.GL_FRAMEBUFFER_COMPLETE:raise RuntimeError("Framebuffer de exportação incompleto.")
            self._export_size=(w,h);self._render(self,None)
            raw=GL.glReadPixels(0,0,w,h,GL.GL_BGRA,GL.GL_UNSIGNED_BYTE)
            pixels=np.frombuffer(raw,dtype=np.uint8).reshape(h,w,4)[::-1].copy()
            image=cairo.ImageSurface.create_for_data(pixels,cairo.FORMAT_ARGB32,w,h,w*4)
            image.write_to_png(str(path))
        finally:
            self._export_size=None;GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,int(old))
            GL.glDeleteRenderbuffers(1,[color]);GL.glDeleteRenderbuffers(1,[depth]);GL.glDeleteFramebuffers(1,[fbo])
            self.queue_render()

def clamp_float(x,a,b):return max(a,min(b,x))

