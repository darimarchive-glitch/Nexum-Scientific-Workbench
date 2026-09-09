from __future__ import annotations
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk,Adw,Gdk
from nexum.core.registry import GROUPS,TOOLS,TOOL_SCOPE
from nexum.core.calculators import CALCS
from nexum.core.search import match
from .plot_widget import ScientificPlot

class CalculatorPage(Gtk.Box):
    """Compact GNOME scientific workspace.

    Navigation shows one category at a time; global search temporarily spans every
    category. This replaces the oversized permanently-expanded v5 sidebar.
    """
    def __init__(self,window,history):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL,spacing=0);self.set_hexpand(True);self.set_vexpand(True)
        self.window=window;self.history=history;self.tool=None;self.inputs={};self.tool_rows=[];self._category_idx=0
        self._build_sidebar();self._build_content();self._rebuild_tool_list();self.select_tool(TOOLS[0])

    def _build_sidebar(self):
        self.revealer=Gtk.Revealer();self.revealer.set_reveal_child(True);self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        side=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=9);side.set_size_request(184,-1);side.set_vexpand(True);side.add_css_class('sidebar')
        side.set_margin_top(10);side.set_margin_bottom(10);side.set_margin_start(10);side.set_margin_end(8)
        self.search=Gtk.SearchEntry();self.search.set_placeholder_text('Buscar ferramenta…');self.search.connect('search-changed',lambda *_:self._rebuild_tool_list());side.append(self.search)
        self.category=Gtk.DropDown.new_from_strings([g[1] for g in GROUPS]);self.category.set_selected(0);self.category.connect('notify::selected',self._category_changed);side.append(self.category)
        sw=Gtk.ScrolledWindow();sw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);sw.set_vexpand(True);sw.set_propagate_natural_height(False)
        self.listbox=Gtk.ListBox();self.listbox.set_selection_mode(Gtk.SelectionMode.NONE);self.listbox.add_css_class('navigation-sidebar');sw.set_child(self.listbox);side.append(sw)
        self.revealer.set_child(side);self.append(self.revealer);self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

    def _build_content(self):
        self.content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);self.content.set_hexpand(True);self.content.set_vexpand(True)
        self.content.set_margin_top(16);self.content.set_margin_bottom(16);self.content.set_margin_start(18);self.content.set_margin_end(18);self.append(self.content)
        top=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        toggle=Gtk.Button(icon_name='sidebar-show-symbolic');toggle.add_css_class('flat');toggle.set_tooltip_text('Mostrar/ocultar navegação');toggle.connect('clicked',lambda *_:self.revealer.set_reveal_child(not self.revealer.get_reveal_child()));top.append(toggle)
        h=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=1);self.eyebrow=Gtk.Label(xalign=0);self.eyebrow.add_css_class('caption');self.title=Gtk.Label(xalign=0);self.title.add_css_class('title-1');self.desc=Gtk.Label(xalign=0);self.desc.add_css_class('dim-label');self.desc.set_wrap(True);h.append(self.eyebrow);h.append(self.title);h.append(self.desc);top.append(h);top.append(Gtk.Box(hexpand=True))
        self.validation=Gtk.Label(label='ESCOPO');self.validation.add_css_class('status-pill');top.append(self.validation);self.content.append(top)
        self.paned=Gtk.Paned.new(Gtk.Orientation.HORIZONTAL);self.paned.set_wide_handle(False);self.paned.set_hexpand(True);self.paned.set_vexpand(True);self.paned.set_resize_start_child(True);self.paned.set_resize_end_child(True);self.paned.set_shrink_start_child(True);self.paned.set_shrink_end_child(True);self.content.append(self.paned)

    def _category_changed(self,w,*_):self._category_idx=w.get_selected();self.search.set_text('');self._rebuild_tool_list()
    def _clear_list(self):
        while (c:=self.listbox.get_first_child()) is not None:self.listbox.remove(c)
        self.tool_rows=[]
    def _rebuild_tool_list(self):
        self._clear_list();q=self.search.get_text().strip();gid=GROUPS[self._category_idx][0]
        items=[]
        if q:
            for t in TOOLS:
                g=dict(GROUPS).get(t[1],'')
                if match(q,t[0],t[2],t[3],g):items.append(t)
        else:items=[t for t in TOOLS if t[1]==gid]
        for t in items:
            row=Adw.ActionRow(title=t[2],subtitle=dict(GROUPS).get(t[1],''));row.set_subtitle_lines(1);row.set_activatable(True);row.connect('activated',lambda _,tt=t:self.select_tool(tt));self.listbox.append(row);self.tool_rows.append((row,t))
        if not items:
            row=Adw.ActionRow(title='Nenhuma ferramenta encontrada',subtitle='Tente outro termo ou categoria.');row.set_sensitive(False);self.listbox.append(row)

    def select_tool(self,tool):
        self.tool=tool;tid,gid,title,desc,fields=tool;self.eyebrow.set_text(dict(GROUPS).get(gid,'').upper());self.title.set_text(title);self.desc.set_text(desc);self.inputs={};scope,scope_note=TOOL_SCOPE.get(tid,('MODELO','Consulte a auditoria científica.'));self.validation.set_text(scope);self.validation.set_tooltip_text(scope_note+' Consulte SCIENTIFIC-AUDIT.md para o domínio validado.')
        if not self.search.get_text().strip():
            idx=next((i for i,g in enumerate(GROUPS) if g[0]==gid),0)
            if idx!=self._category_idx:self._category_idx=idx;self.category.set_selected(idx);self._rebuild_tool_list()
        form_sw=Gtk.ScrolledWindow();form_sw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);form_sw.set_hexpand(True);form_sw.set_vexpand(True);form_sw.set_min_content_width(300);form_sw.set_propagate_natural_height(False)
        form=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);form.set_margin_top(4);form.set_margin_end(16);form.set_margin_bottom(16)
        group=Adw.PreferencesGroup(title='Entradas',description='Edite os dados do problema. Unidades e hipóteses aparecem no desenvolvimento.')
        for spec in fields:
            if spec['kind']=='select':
                row=Adw.ComboRow(title=spec['label']);row.set_model(Gtk.StringList.new(spec['options']));row.set_selected(spec['options'].index(spec['default']) if spec['default'] in spec['options'] else 0)
            else:
                row=Adw.EntryRow(title=spec['label']);row.set_text(spec['default'])
            group.add(row);self.inputs[spec['key']]=(row,spec)
        form.append(group)
        buttons=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8);calc=Gtk.Button(label='Calcular',icon_name='media-playback-start-symbolic');calc.add_css_class('suggested-action');calc.connect('clicked',self._calculate);clear=Gtk.Button(label='Limpar');clear.connect('clicked',self._clear);buttons.append(calc);buttons.append(clear);form.append(buttons);form_sw.set_child(form)
        result_sw=Gtk.ScrolledWindow();result_sw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);result_sw.set_hexpand(True);result_sw.set_vexpand(True);result_sw.set_min_content_width(390);result_sw.set_propagate_natural_height(False)
        result=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);result.set_margin_start(16);result.set_margin_top(4);result.set_margin_bottom(16)
        rg=Adw.PreferencesGroup(title='Resultado');self.value=Gtk.Label(label='—',xalign=0);self.value.add_css_class('numeric-result');self.value.set_selectable(True);self.value.set_wrap(True);rg.add(self.value);result.append(rg)
        dg=Adw.PreferencesGroup(title='Desenvolvimento, unidades e hipóteses');self.details=Gtk.Label(label='Calcule para ver o desenvolvimento.',xalign=0);self.details.set_selectable(True);self.details.set_wrap(True);self.details.set_wrap_mode(2);self.details.add_css_class('monospace');dg.add(self.details);result.append(dg)
        self.plot=ScientificPlot();self.plot.set_visible(False);result.append(self.plot)
        copy=Gtk.Button(label='Copiar resultado',icon_name='edit-copy-symbolic');copy.set_halign(Gtk.Align.START);copy.connect('clicked',self._copy);result.append(copy);result_sw.set_child(result)
        self.paned.set_start_child(form_sw);self.paned.set_end_child(result_sw);self.paned.set_position(470)

    def _getdata(self):
        out={}
        for key,(row,spec) in self.inputs.items():
            if isinstance(row,Adw.ComboRow):
                item=row.get_selected_item();out[key]=item.get_string() if item else ''
            else:out[key]=row.get_text().strip()
        return out
    def _calculate(self,*_):
        try:
            data=self._getdata();r=CALCS[self.tool[0]](data);self.value.set_text(r.value);self.details.set_text(r.details);self.plot.set_plot((r.data or {}).get('plot'));self.history.add(self.tool[0],data,{'value':r.value,'data':r.data or {}});self.window.toast('Cálculo concluído')
        except Exception as exc:self.window.toast(f'Entrada ou modelo inválido: {exc}')
    def _clear(self,*_):
        for row,_ in self.inputs.values():
            if isinstance(row,Adw.EntryRow):row.set_text('')
    def _copy(self,*_):
        Gdk.Display.get_default().get_clipboard().set((self.value.get_text()+'\n\n'+self.details.get_text()).strip());self.window.toast('Resultado copiado')
