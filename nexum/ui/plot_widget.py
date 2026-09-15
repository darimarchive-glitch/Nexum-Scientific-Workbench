from __future__ import annotations
import math
import gi
gi.require_version('Gtk','4.0')
gi.require_version('Adw','1')
from gi.repository import Gtk, Adw

class ScientificPlot(Gtk.DrawingArea):
    """Small dependency-free scientific plot for native GTK pages.

    Input format: {title,xlabel,ylabel,series:[{name,points,scatter?}],markers:[{x,label}]}
    The widget intentionally avoids decorative animation: it renders only calculated data.
    """
    def __init__(self):
        super().__init__()
        self.data=None;self.on_point=None;self._bounds=None
        click=Gtk.GestureClick.new();click.connect("released",self._clicked);self.add_controller(click)
        self.set_content_height(300)
        self.set_hexpand(True); self.set_vexpand(False)
        self.set_draw_func(self._draw)

    def set_plot(self,data):
        self.data=data
        self.set_visible(bool(data))
        self.queue_draw()

    def _text(self,cr,x,y,text,size=12,bold=False):
        dark=Adw.StyleManager.get_default().get_dark(); v=.90 if dark else .22
        cr.set_source_rgba(v,v,v,.92)
        cr.select_font_face('Sans',0,1 if bold else 0);cr.set_font_size(size);cr.move_to(x,y);cr.show_text(str(text))

    def _draw(self,area,cr,w,h):
        d=self.data
        if not d:return
        legend_rows=(len(d.get("series",[]))+2)//3
        left,right,top,bottom=90,22,36,48+legend_rows*20
        pw=max(10,w-left-right);ph=max(10,h-top-bottom)
        pts=[]
        for s in d.get('series',[]):
            for x,y in s.get('points',[]):
                if math.isfinite(float(x)) and math.isfinite(float(y)):pts.append((float(x),float(y)))
        if not pts:return
        xs=[p[0] for p in pts];ys=[p[1] for p in pts]
        xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
        if xmax==xmin:xmax=xmin+1
        if ymax==ymin:ymax=ymin+1
        # modest padding; preserve pH 0-14 if naturally present
        ypad=(ymax-ymin)*.05;ypad=ypad or 1
        ymin-=ypad;ymax+=ypad
        self._bounds=(xmin,xmax,ymin,ymax,left,top,pw,ph)
        def xy(x,y):return left+(x-xmin)/(xmax-xmin)*pw, top+(1-(y-ymin)/(ymax-ymin))*ph
        cr.set_line_width(1);cr.set_source_rgba(.5,.5,.5,.22)
        cr.rectangle(left,top,pw,ph);cr.stroke()
        for i in range(6):
            f=i/5; x=left+f*pw; y=top+f*ph
            cr.set_source_rgba(.5,.5,.5,.10);cr.move_to(x,top);cr.line_to(x,top+ph);cr.stroke();cr.move_to(left,y);cr.line_to(left+pw,y);cr.stroke()
            self._text(cr,x-12,top+ph+20,f'{xmin+f*(xmax-xmin):.4g}',10)
            self._text(cr,30,top+ph-f*ph+4,f'{ymin+f*(ymax-ymin):.4g}',10)
        palette=[(.20,.50,.90,.95),(.90,.42,.18,.95),(.20,.68,.48,.95),(.62,.38,.84,.95)]
        for si,s in enumerate(d.get('series',[])):
            color=palette[si%len(palette)];valid=[(float(x),float(y)) for x,y in s.get('points',[]) if math.isfinite(float(x)) and math.isfinite(float(y))]
            if not valid:continue
            cr.set_source_rgba(*color);cr.set_line_width(2.2);cr.set_dash([6,3] if si%3==1 else [2,3] if si%3==2 else [])
            if not s.get('scatter'):
                first=True
                for x,y in valid:
                    px,py=xy(x,y)
                    if first:cr.move_to(px,py);first=False
                    else:cr.line_to(px,py)
                cr.stroke()
            if s.get('scatter') or len(valid)<40:
                for x,y in valid:
                    px,py=xy(x,y);cr.arc(px,py,2.7,0,2*math.pi);cr.fill()
        cr.set_dash([])
        for si,series in enumerate(d.get('series',[])):
            lx=left+(si%3)*pw/3;ly=top+ph+43+(si//3)*20
            cr.set_source_rgba(*palette[si%len(palette)]);cr.rectangle(lx,ly-8,10,3);cr.fill()
            self._text(cr,lx+14,ly,series.get('name','')[:28],10)
        for m in d.get('markers',[]):
            x=float(m.get('x',0))
            if xmin<=x<=xmax:
                px,_=xy(x,ymin);cr.set_source_rgba(.72,.28,.22,.72);cr.set_line_width(1.2);cr.move_to(px,top);cr.line_to(px,top+ph);cr.stroke();self._text(cr,min(px+4,w-130),top+15,m.get('label',''),10)
        self._text(cr,left,18,d.get('title',''),13,True);self._text(cr,left+pw/2-30,h-9,d.get('xlabel',''),11);cr.save();cr.translate(15,top+ph/2);cr.rotate(-math.pi/2);self._text(cr,-40,0,d.get('ylabel',''),10);cr.restore()


    def _clicked(self,gesture,n,x,y):
        if not self.on_point or not self._bounds:return
        xmin,xmax,ymin,ymax,left,top,pw,ph=self._bounds
        if left<=x<=left+pw and top<=y<=top+ph:
            self.on_point(xmin+(x-left)/pw*(xmax-xmin),ymax-(y-top)/ph*(ymax-ymin))

    def export(self,path,kind='svg'):
        import cairo
        if not self.data:raise ValueError('Nenhum gráfico para exportar.')
        surface=cairo.SVGSurface(str(path),1200,720) if kind=='svg' else cairo.PDFSurface(str(path),1200,720)
        cr=cairo.Context(surface)
        dark=Adw.StyleManager.get_default().get_dark();bg=.105 if dark else 1.
        cr.set_source_rgb(bg,bg,bg);cr.paint();self._draw(self,cr,1200,720);surface.finish()
