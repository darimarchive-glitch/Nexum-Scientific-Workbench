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
        self.data=None
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
        left,right,top,bottom=62,22,30,48
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
        def xy(x,y):return left+(x-xmin)/(xmax-xmin)*pw, top+(1-(y-ymin)/(ymax-ymin))*ph
        cr.set_line_width(1);cr.set_source_rgba(.5,.5,.5,.22)
        cr.rectangle(left,top,pw,ph);cr.stroke()
        for i in range(6):
            f=i/5; x=left+f*pw; y=top+f*ph
            cr.set_source_rgba(.5,.5,.5,.10);cr.move_to(x,top);cr.line_to(x,top+ph);cr.stroke();cr.move_to(left,y);cr.line_to(left+pw,y);cr.stroke()
            self._text(cr,x-12,top+ph+20,f'{xmin+f*(xmax-xmin):.4g}',10)
            self._text(cr,4,top+ph-f*ph+4,f'{ymin+f*(ymax-ymin):.4g}',10)
        palette=[(.20,.50,.90,.95),(.90,.42,.18,.95),(.20,.68,.48,.95),(.62,.38,.84,.95)]
        for si,s in enumerate(d.get('series',[])):
            color=palette[si%len(palette)];valid=[(float(x),float(y)) for x,y in s.get('points',[]) if math.isfinite(float(x)) and math.isfinite(float(y))]
            if not valid:continue
            cr.set_source_rgba(*color);cr.set_line_width(2.2)
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
        for m in d.get('markers',[]):
            x=float(m.get('x',0))
            if xmin<=x<=xmax:
                px,_=xy(x,ymin);cr.set_source_rgba(.72,.28,.22,.72);cr.set_line_width(1.2);cr.move_to(px,top);cr.line_to(px,top+ph);cr.stroke();self._text(cr,min(px+4,w-130),top+15,m.get('label',''),10)
        self._text(cr,left,18,d.get('title',''),13,True);self._text(cr,left+pw/2-30,h-9,d.get('xlabel',''),11);self._text(cr,5,16,d.get('ylabel',''),10)
