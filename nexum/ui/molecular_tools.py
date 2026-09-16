"""Native analysis panel, sharing the existing molecular renderer."""
from dataclasses import asdict
import copy,json
import numpy as np
from gi.repository import Gtk,Adw,GLib
from nexum.core.molecular_analysis import measurement,molecular_surface,parse_cube,isosurface,sample_cube,scalar_colors,molecule_from_dict
from nexum import chemistry_worker
from .file_actions import choose,background
from .gl_viewer import GLMoleculeView
from .plot_widget import ScientificPlot

class MolecularTools(Gtk.Box):
    def __init__(self,page):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        self.page=page;self.window=page.window;self.viewer=page.viewer;self.ids=[];self.generation=0;self.surface_generation=0;self.reference=None;self.vibrations=None;self.timer=0;self.original=None;self.positions=[]
        self.label('Análise molecular')
        self.mode=Gtk.DropDown.new_from_strings(['Inspecionar','Distância (2 átomos)','Ângulo (3 átomos)','Diedro (4 átomos)']);self.append(self.mode)
        self.mode.connect('notify::selected',lambda *_:self.clear())
        self.result=self.label('Clique na estrutura para selecionar átomos.');self.button('Limpar seleção',self.clear)
        self.query=Gtk.Entry(placeholder_text='O, água, ligantes, cadeia:A, resíduo:ALA');self.append(self.query);self.button('Selecionar grupo',self.select_group)
        self.query.set_tooltip_text('Grupos funcionais: grupo:Hidroxila, grupo:Carbonila, grupo:Carboxila, grupo:Amina, grupo:Amida. Exigem gerar as anotações primeiro.')
        self.color=Gtk.DropDown.new_from_strings(['Cor por elemento','Cor por cadeia','Cor por resíduo','Carga parcial estimada']);self.append(self.color);self.color.connect('notify::selected',self.colors)
        self.legend=self.label('C cinza · O vermelho · N azul · S amarelo. Seleção em amarelo.')
        self.button('Gerar 2D, grupos e cargas',self.annotate)
        self.diagram=Gtk.DrawingArea();self.diagram.set_content_height(220);self.diagram.set_draw_func(self.draw2d);self.append(self.diagram)
        click=Gtk.GestureClick.new();click.connect('released',self.click2d);self.diagram.add_controller(click)
        self.surface=Gtk.DropDown.new_from_strings(['Van der Waals','Acessível ao solvente','Molecular / SES em grade']);self.append(self.surface)
        self.probe=self.spin('Sonda (Å)',.1,5,.1,1.4);self.resolution=self.spin('Resolução',20,80,4,48)
        self.button('Calcular superfície dos átomos visíveis',self.make_surface);self.button('Remover superfície',self.remove_surface)
        self.opacity=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,5,100,1);self.opacity.set_value(35);self.append(self.opacity);self.opacity.set_tooltip_text('Opacidade da superfície (%)');self.opacity.connect('value-changed',self.options)
        self.cut=Gtk.CheckButton(label='Plano de corte');self.append(self.cut);self.cut.connect('toggled',self.options)
        self.cut_at=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,100,1);self.cut_at.set_value(50);self.append(self.cut_at);self.cut_at.connect('value-changed',self.options)
        self.note=self.label('Superfícies usam os filtros ativos no momento do cálculo. Recalcule ao mudar a seleção de cadeias ou átomos.')
        self.kind=Gtk.DropDown.new_from_strings(['Densidade (Cube)','Orbital ± (Cube)','Potencial sobre superfície (Cube)']);self.append(self.kind)
        self.method=Gtk.Entry(placeholder_text='Método/base e unidade do campo');self.append(self.method)
        self.level=Gtk.Entry(text='0.03',placeholder_text='Isovalor');self.append(self.level);self.button('Importar campo Cube',self.open_cube)
        self.button('Importar modos vibracionais JSON',self.open_modes)
        self.mode_index=self.spin('Modo vibracional',1,1,1,1)
        self.mode_plot=ScientificPlot();self.mode_plot.on_point=self.pick_mode;self.append(self.mode_plot)
        self.button('Animar / parar modo',self.animate)
        self.button('Fixar referência',self.pin);self.button('Comparar com referência',self.compare)
        self.button('Exportar imagem PNG',lambda:choose(self.window,'Exportar figura',self.viewer.export_png,True,'estrutura.png'))
        self.connect('unmap',lambda *_:self.stop())
    def label(self,text):
        w=Gtk.Label(label=text,xalign=0);w.set_wrap(True);w.set_selectable(True);self.append(w);return w
    def spin(self,title,lo,hi,step,value):
        w=Gtk.SpinButton.new_with_range(lo,hi,step);w.set_value(value);row=Adw.ActionRow(title=title);row.add_suffix(w);self.append(row);return w
    def button(self,title,fn):
        w=Gtk.Button(label=title)
        def clicked(*_):
            try:fn()
            except Exception as exc:self.window.toast(str(exc),8)
        w.connect('clicked',clicked);self.append(w)
    def require(self):
        if not self.viewer.molecule:raise ValueError('Carregue uma estrutura primeiro.')
        return self.viewer.molecule
    def reset(self):
        self.stop();self.generation+=1;self.ids=[];self.vibrations=None;self.mode_plot.set_plot(None);self.positions=[];self.diagram.queue_draw()
    def clear(self):
        self.ids=[];self.viewer.measurement_indices=[];self.viewer.selection=set();self.viewer.rebuild_scene();self.viewer.queue_render();self.result.set_text('Seleção vazia.');self.diagram.queue_draw()
    def selected(self,index):
        count=self.mode.get_selected()+1
        if count==1 or len(self.ids)>=count:self.ids=[]
        if index not in self.ids:self.ids.append(index)
        self.viewer.measurement_indices=list(self.ids) if count>1 else []
        self.highlight()
        if count>1 and len(self.ids)==count:
            try:
                name,value,unit=measurement(self.require(),self.ids);self.result.set_text(f'{name}: {value:.4g} {unit}\nOrdem: '+', '.join(str(i+1) for i in self.ids))
            except ValueError as exc:self.result.set_text(str(exc))
    def highlight(self):
        self.viewer.selection=set(self.ids);self.viewer.rebuild_scene();self.viewer.queue_render();self.diagram.queue_draw();self.result.set_text(f'{len(self.ids)} átomos selecionados; filtros continuam ativos.')
    def select_group(self):
        self.viewer.measurement_indices=[]
        m=self.require();q=self.query.get_text().casefold().strip()
        if q.startswith('grupo:'):
            self.ids=sorted({i for k,groups in m.metadata.get('functional_groups',{}).items() if k.casefold()==q[6:] for g in groups for i in g})
        else:
            def match(a):
                if q in ('água','agua'):return a.residue in ('HOH','WAT','H2O')
                if q=='ligantes':return a.hetero and a.residue not in ('HOH','WAT','H2O')
                if q.startswith('cadeia:'):return a.chain.casefold()==q.split(':',1)[1]
                if q.startswith(('resíduo:','residuo:')):return a.residue.casefold()==q.split(':',1)[1]
                return a.element.casefold()==q
            self.ids=[i for i,a in enumerate(m.atoms) if match(a)]
        self.highlight()
    def colors(self,*_):
        mode=self.color.get_selected();m=self.viewer.molecule
        if mode==3 and (not m or len(m.metadata.get('partial_charges',[]))!=len(m.atoms)):
            self.window.toast('Gere as cargas a partir da conectividade primeiro.');self.color.set_selected(0);return
        self.viewer.color_mode=['element','chain','residue','charge'][mode]
        if mode==3:
            limit=max(map(abs,m.metadata['partial_charges'])) or 1
            self.legend.set_text(f'Azul −{limit:.3g} e · neutro 0 · laranja +{limit:.3g} e. '+m.metadata.get('charge_method',''))
        elif mode in (1,2):self.legend.set_text('Paleta cíclica por categoria: '+', '.join(sorted({a.chain if mode==1 else a.residue for a in m.atoms})) if m else '')
        else:self.legend.set_text('C cinza · O vermelho · N azul · S amarelo. Seleção em amarelo.')
        self.viewer.rebuild_scene();self.viewer.queue_render()
    def annotate(self):
        m=self.require();data=asdict(m);generation=self.generation
        def work():
            if chemistry_worker.configured():return chemistry_worker.call('annotate',data)
            from nexum.core.molecular_analysis import annotate
            return annotate(data)
        def done(result):
            if generation!=self.generation:return
            m.metadata.update(result.metadata);self.diagram.queue_draw();self.result.set_text('Grupos: '+', '.join(k for k,v in m.metadata['functional_groups'].items() if v))
        background(self.window,work,done)
    def draw2d(self,area,cr,w,h):
        self.positions=[];m=self.viewer.molecule
        if not m:return
        xy=np.asarray(m.metadata.get('coordinates_2d',[]))
        if xy.shape!=(len(m.atoms),2):return
        scale=min((w-35)/max(np.ptp(xy[:,0]),1),(h-35)/max(np.ptp(xy[:,1]),1))
        xy=(xy-(xy.min(0)+xy.max(0))/2)*[scale,-scale]+[w/2,h/2];self.positions=xy
        cr.set_source_rgb(.5,.5,.5);cr.set_line_width(1.3)
        for i,j,order in m.bonds:
            direction=xy[j]-xy[i];normal=np.array([-direction[1],direction[0]])/max(np.linalg.norm(direction),1)
            for n in range(min(order,3)):
                offset=normal*(n-(min(order,3)-1)/2)*3;cr.move_to(*(xy[i]+offset));cr.line_to(*(xy[j]+offset));cr.stroke()
        for i,(a,p) in enumerate(zip(m.atoms,xy)):
            cr.set_source_rgb(*( (1,.6,.05) if i in self.viewer.selection else (.25,.55,.8)))
            cr.arc(*p,5,0,2*np.pi);cr.fill();cr.set_source_rgb(.5,.5,.5);cr.set_font_size(10);cr.move_to(p[0]+6,p[1]-4);cr.show_text(a.element+str(i+1))
    def click2d(self,g,n,x,y):
        if len(self.positions):
            distances=np.linalg.norm(self.positions-[x,y],axis=1);i=int(np.argmin(distances))
            if distances[i]<16:self.page._atom_selected(i,self.viewer.molecule.atoms[i])
    def options(self,*_):
        self.viewer.surface_opacity=self.opacity.get_value()/100;self.viewer.clip_enabled=self.cut.get_active();self.viewer.clip_fraction=self.cut_at.get_value()/100;self.viewer.queue_render()
    def remove_surface(self):self.surface_generation+=1;self.viewer.surface_mesh=None;self.viewer.queue_render()
    def make_surface(self):
        m=copy.deepcopy(self.require());indices=[i for i,a in enumerate(m.atoms) if self.viewer._atom_visible(a)]
        self.surface_generation+=1;token=self.surface_generation
        generation=self.generation;kind=['vdw','sas','ses'][self.surface.get_selected()];probe=self.probe.get_value();resolution=self.resolution.get_value_as_int()
        def done(mesh):
            if generation==self.generation and token==self.surface_generation:self.viewer.surface_mesh=mesh;self.note.set_text(mesh['method']);self.viewer.queue_render()
        self.note.set_text('Calculando superfície…');background(self.window,lambda:molecular_surface(m,kind,probe,resolution,indices),done)
    def open_cube(self):
        method=self.method.get_text().strip();level=float(self.level.get_text().replace(',','.'));kind=self.kind.get_selected()
        if not method or not np.isfinite(level) or level<=0:raise ValueError('Informe método/base, unidade e isovalor positivo.')
        mesh=copy.deepcopy(self.viewer.surface_mesh);generation=self.generation
        def opened(path):
            def work():
                if path.stat().st_size>70000000:raise ValueError('Cube excede 70 MB.')
                cube=parse_cube(path.read_text());parts=[]
                if kind==2:
                    if mesh is None:raise ValueError('Calcule uma superfície no mesmo referencial do Cube antes de mapear potencial.')
                    values=sample_cube(cube,mesh['vertices']);mesh['colors'],limit=scalar_colors(values);mesh['method']=f'Potencial: azul −{limit:.4g}; laranja +{limit:.4g}. {method}';return cube,mesh
                for sign,color in [(1,[.95,.4,.12])]+([(-1,[.2,.4,.9])] if kind==1 else []):
                    if cube['values'].min()<sign*level<cube['values'].max():
                        part=isosurface(cube['values'],cube['origin'],cube['axes'],sign*level);part['colors']=np.tile(np.array(color,dtype='float32'),(len(part['vertices']),1));parts.append(part)
                if not parts:raise ValueError('Isovalor fora da faixa do arquivo.')
                result={k:np.concatenate([p[k] for p in parts]) for k in ('vertices','normals','colors')};result['method']=f'{method}; isovalor {level:g}; '+('orbital: azul negativo / laranja positivo' if kind==1 else 'densidade')
                return cube,result
            def done(result):
                if generation!=self.generation:return
                cube,surface=result
                if kind!=2 and cube['molecule'].atoms:self.page._apply_molecule(cube['molecule'])
                self.viewer.surface_mesh=surface;self.note.set_text(surface['method']);self.viewer.queue_render()
            background(self.window,work,done)
        choose(self.window,'Importar campo Cube',opened)
    def snapshot(self):
        self.stop()
        return {'molecule':asdict(self.require()),'camera':{k:getattr(self.viewer,k) for k in ('rot_x','rot_y','zoom','fov_deg')},'view':{k:getattr(self.viewer,k) for k in ('representation','show_hydrogens','show_ligands','fog','show_influence','influence_opacity','color_mode','surface_opacity','clip_enabled','clip_fraction')},'selection':self.ids,'measurement':self.viewer.measurement_indices,'selection_mode':self.mode.get_selected(),'chains':None if self.viewer.visible_chains is None else sorted(self.viewer.visible_chains),'surface':self.viewer.surface_mesh,'vibrations':self.vibrations}
    @staticmethod
    def restore_view(view,data):
        view.set_molecule(molecule_from_dict(data['molecule']))
        for key in ('rot_x','rot_y','zoom','fov_deg'):
            if key in data.get('camera',{}):setattr(view,key,float(data['camera'][key]))
        for key in ('representation','show_hydrogens','show_ligands','fog','show_influence','influence_opacity','color_mode','surface_opacity','clip_enabled','clip_fraction'):
            if key in data.get('view',{}):setattr(view,key,data['view'][key])
        view.measurement_indices=list(data.get('measurement',[]))
        view.selection=set(data.get('selection',[]));view.visible_chains=None if data.get('chains') is None else set(data['chains']);mesh=data.get('surface')
        if mesh:
            mesh=dict(mesh)
            for key in ('vertices','normals','colors'):mesh[key]=np.asarray(mesh[key],dtype='float32')
        view.surface_mesh=mesh;view.rebuild_scene();view.queue_render()
    def pin(self):self.reference=copy.deepcopy(self.snapshot());self.window.toast('Referência fixada.')
    def compare(self):
        if not self.reference:raise ValueError('Fixe uma referência primeiro.')
        dialog=Adw.Window(transient_for=self.window,title='Comparar estruturas',default_width=1100,default_height=650);box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);box.append(Adw.HeaderBar());box.append(Gtk.Label(label='Rotação e zoom vinculados; enquadramentos independentes.'));row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8);views=[]
        for state in (self.reference,self.snapshot()):
            column=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);column.set_hexpand(True);column.append(Gtk.Label(label=state['molecule']['name']));view=GLMoleculeView();view.set_dark(self.viewer.dark);self.restore_view(view,state);column.append(view);row.append(column);views.append(view)
        for i,view in enumerate(views):
            def sync(source,target=views[1-i]):target.rot_x=source.rot_x;target.rot_y=source.rot_y;target.zoom=source.zoom;target.queue_render()
            view.camera_callback=sync
        box.append(row);dialog.set_content(box);dialog.present()
    def open_modes(self):
        def opened(path):
            if path.stat().st_size>20000000:raise ValueError('Arquivo excede 20 MB.')
            data=json.loads(path.read_text());freq=np.asarray(data['frequencies_cm1'],dtype=float);vectors=np.asarray(data['displacements'],dtype=float);intensities=np.asarray(data.get('intensities',np.ones(len(freq))),dtype=float)
            if not data.get('method') or freq.ndim!=1 or not 1<=len(freq)<=3000 or vectors.shape!=(len(freq),len(self.require().atoms),3) or intensities.shape!=freq.shape or not all(np.isfinite(a).all() for a in (freq,vectors,intensities)):raise ValueError('Modos inválidos ou incompatíveis com a estrutura.')
            self.vibrations=data;self.mode_index.set_range(1,len(freq));self.mode_plot.set_plot({'title':'Modos calculados: clique para selecionar','xlabel':'cm⁻¹','ylabel':'Intensidade relativa','series':[{'name':data['method'],'points':list(zip(freq,intensities)),'scatter':True}]})
        choose(self.window,'Importar modos calculados',opened)
    def pick_mode(self,x,y):
        if self.vibrations:self.mode_index.set_value(int(np.argmin(np.abs(np.asarray(self.vibrations['frequencies_cm1'])-x)))+1)
    def stop(self):
        if self.timer:GLib.source_remove(self.timer);self.timer=0
        if self.original is not None:
            molecule,positions=self.original
            for atom,p in zip(molecule.atoms,positions):atom.x,atom.y,atom.z=map(float,p)
            self.original=None;self.viewer.rebuild_scene();self.viewer.queue_render()
    def animate(self):
        if self.timer:self.stop();return
        if not self.vibrations:raise ValueError('Importe os modos calculados primeiro.')
        m=self.require();index=self.mode_index.get_value_as_int()-1
        if self.vibrations['frequencies_cm1'][index]<=0:raise ValueError('Modo nulo/imaginário não representa vibração estável.')
        vectors=np.asarray(self.vibrations['displacements'][index]);maximum=np.max(np.linalg.norm(vectors,axis=1))
        if maximum<1e-12:raise ValueError('Modo sem deslocamento.')
        vectors=vectors/maximum*.3;positions=np.array([a.position for a in m.atoms]);self.original=(m,positions);self.remove_surface()
        import time
        start=time.monotonic()
        def tick():
            for a,p in zip(m.atoms,positions+vectors*np.sin(2*np.pi*(time.monotonic()-start))):a.x,a.y,a.z=map(float,p)
            self.viewer.rebuild_scene();self.viewer.queue_render();return True
        self.note.set_text('Animação didática: 1 ciclo/s, amplitude máxima 0,3 Å; não é a velocidade física da vibração.');self.timer=GLib.timeout_add(50,tick)
