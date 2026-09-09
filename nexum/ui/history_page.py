from __future__ import annotations
import json
import gi
gi.require_version("Gtk","4.0");gi.require_version("Adw","1")
from gi.repository import Gtk,Adw

class HistoryPage(Gtk.Box):
    def __init__(self,history):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.set_hexpand(True);self.set_vexpand(True);self.history=history;self.set_margin_top(18);self.set_margin_bottom(18);self.set_margin_start(22);self.set_margin_end(22)
        head=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8);titles=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2);t=Gtk.Label(label="Histórico local",xalign=0);t.add_css_class("title-1");s=Gtk.Label(label="Rastreabilidade dos cálculos executados neste computador.",xalign=0);s.add_css_class("dim-label");titles.append(t);titles.append(s);head.append(titles);head.append(Gtk.Box(hexpand=True));b=Gtk.Button(label="Atualizar",icon_name="view-refresh-symbolic");b.connect("clicked",lambda *_:self.reload());head.append(b);self.append(head)
        self.sw=Gtk.ScrolledWindow();self.sw.set_hexpand(True);self.sw.set_vexpand(True);self.sw.set_propagate_natural_height(False);self.list=Gtk.ListBox();self.list.add_css_class("boxed-list");self.list.set_selection_mode(Gtk.SelectionMode.NONE);self.sw.set_child(self.list);self.append(self.sw);self.reload()
    def reload(self):
        while (c:=self.list.get_first_child()) is not None:self.list.remove(c)
        rows=self.history.latest(100)
        for r in rows:
            try:inp=json.loads(r['inputs']);res=json.loads(r['result'])
            except Exception:inp=r['inputs'];res=r['result']
            row=Adw.ExpanderRow(title=f"{r['module']} · #{r['id']}",subtitle=r['created_at']);detail=Gtk.Label(label=f"Entradas\n{json.dumps(inp,ensure_ascii=False,indent=2) if isinstance(inp,dict) else inp}\n\nResultado\n{json.dumps(res,ensure_ascii=False,indent=2) if isinstance(res,dict) else res}",xalign=0);detail.set_selectable(True);detail.set_wrap(True);detail.add_css_class("monospace");row.add_row(detail);self.list.append(row)
        if not rows:
            row=Adw.ActionRow(title="Ainda não há cálculos",subtitle="Os resultados serão salvos aqui automaticamente.");self.list.append(row)
