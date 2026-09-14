from __future__ import annotations
from pathlib import Path
from nexum.paths import cache_dir
import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio

from nexum.core.structures import suggestions, pubchem, rcsb, parse_sdf, parse_pdb, parse_mmcif
from .gl_viewer import GLMoleculeView


REPRESENTATIONS = [
    ("Fitas", "ribbon"),
    ("Bolas e ligações", "ball-stick"),
    ("Preenchimento VDW", "spacefill"),
    ("Varetas", "sticks"),
    ("Backbone", "backbone"),
    ("Linhas", "lines"),
]


class StructurePage(Gtk.Box):
    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True);self.set_vexpand(True)
        self.window=window;self.cache=cache_dir()/"structures";self.selected_suggestion=None;self.search_source="Todos";self.search_timer=0;self._fullscreen=False;self.search_generation=0
        self.viewer=GLMoleculeView();self.viewer.selection_callback=self._atom_selected
        style=Adw.StyleManager.get_default();self.viewer.set_dark(style.get_dark());style.connect("notify::dark",lambda *_:self.viewer.set_dark(style.get_dark()))
        self._build_searchbar();self._build_workspace()

    def _build_searchbar(self):
        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0);outer.add_css_class("toolbar")
        row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8);row.set_margin_top(8);row.set_margin_bottom(8);row.set_margin_start(12);row.set_margin_end(12)
        self.search=Gtk.SearchEntry();self.search.set_hexpand(True);self.search.set_placeholder_text("Molécula, proteína, DNA ou código PDB…")
        self.search.connect("search-changed",self._search_changed);self.search.connect("activate",lambda *_:self._search_now())
        self.source=Gtk.DropDown.new_from_strings(["Todas as fontes","PubChem","RCSB PDB"]);self.source.set_selected(0);self.source.connect("notify::selected",self._source_changed)
        btn_import=Gtk.Button(icon_name="document-open-symbolic");btn_import.set_tooltip_text("Importar SDF/MOL/PDB/mmCIF");btn_import.connect("clicked",self._import_file)
        btn_full=Gtk.Button(icon_name="view-fullscreen-symbolic");btn_full.set_tooltip_text("Visualizador em tela cheia");btn_full.connect("clicked",self._toggle_fullscreen);self.full_btn=btn_full
        row.append(self.search);row.append(self.source);row.append(btn_import);row.append(btn_full);outer.append(row)
        self.results_revealer=Gtk.Revealer();self.results_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        result_frame=Gtk.Frame();self.results=Gtk.ListBox();self.results.set_selection_mode(Gtk.SelectionMode.NONE);self.results.add_css_class("boxed-list");result_frame.set_child(self.results);result_frame.set_margin_start(12);result_frame.set_margin_end(12);result_frame.set_margin_bottom(8);self.results_revealer.set_child(result_frame);outer.append(self.results_revealer)
        self.search_area=outer;self.append(outer)

    def _build_workspace(self):
        paned=Gtk.Paned.new(Gtk.Orientation.HORIZONTAL);paned.set_wide_handle(False);paned.set_hexpand(True);paned.set_vexpand(True);paned.set_shrink_start_child(True);paned.set_shrink_end_child(True);paned.set_resize_start_child(True);paned.set_resize_end_child(False)
        viewer_overlay=Gtk.Overlay();viewer_overlay.set_hexpand(True);viewer_overlay.set_vexpand(True);viewer_overlay.set_child(self.viewer)
        controls=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=6);controls.set_halign(Gtk.Align.START);controls.set_valign(Gtk.Align.START);controls.set_margin_top(12);controls.set_margin_start(12);controls.add_css_class("floating-toolbar")
        fit=Gtk.Button(icon_name="zoom-fit-best-symbolic");fit.set_tooltip_text("Reenquadrar");fit.connect("clicked",lambda *_:self.viewer.fit())
        reset=Gtk.Button(icon_name="view-refresh-symbolic");reset.set_tooltip_text("Restaurar câmera");reset.connect("clicked",lambda *_:self.viewer.fit())
        controls.append(fit);controls.append(reset);viewer_overlay.add_overlay(controls)
        self.empty=Adw.StatusPage(title="Estruturas 3D",description="Pesquise e selecione uma estrutura. Moléculas pequenas usam PubChem; macromoléculas usam RCSB/mmCIF.",icon_name="applications-science-symbolic");viewer_overlay.add_overlay(self.empty)
        paned.set_start_child(viewer_overlay)
        self.inspector=self._build_inspector();paned.set_end_child(self.inspector);paned.set_position(980)
        self.paned=paned;self.viewer_overlay=viewer_overlay;self.append(paned)

    def _build_inspector(self):
        sw=Gtk.ScrolledWindow();sw.set_min_content_width(300);sw.set_max_content_width(390);sw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC);sw.set_vexpand(True);sw.set_propagate_natural_height(False)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18);box.set_margin_top(16);box.set_margin_bottom(20);box.set_margin_start(16);box.set_margin_end(16)
        self.title=Gtk.Label(label="Nenhuma estrutura carregada",xalign=0);self.title.add_css_class("title-3");self.title.set_wrap(True);box.append(self.title)
        self.meta=Gtk.Label(label="",xalign=0);self.meta.add_css_class("dim-label");self.meta.set_wrap(True);box.append(self.meta)
        rep_group=Adw.PreferencesGroup(title="Representação")
        self.rep=Adw.ComboRow(title="Modo");self.rep.set_model(Gtk.StringList.new([x[0] for x in REPRESENTATIONS]));self.rep.set_selected(0);self.rep.connect("notify::selected",self._viewer_options_changed);rep_group.add(self.rep)
        self.hydrogen=Adw.SwitchRow(title="Hidrogênios");self.hydrogen.set_active(False);self.hydrogen.connect("notify::active",self._viewer_options_changed);rep_group.add(self.hydrogen)
        self.ligands=Adw.SwitchRow(title="Ligantes e cofatores");self.ligands.set_active(True);self.ligands.connect("notify::active",self._viewer_options_changed);rep_group.add(self.ligands)
        self.fog=Adw.SwitchRow(title="Névoa de profundidade",subtitle="Integra estruturas distantes ao fundo e reforça perspectiva");self.fog.set_active(True);self.fog.connect("notify::active",self._viewer_options_changed);rep_group.add(self.fog);box.append(rep_group)
        camera_group=Adw.PreferencesGroup(title="Câmera")
        depth_row=Adw.ActionRow(title="Perspectiva",subtitle="Campo de visão maior reforça a diferença entre frente e fundo")
        self.perspective=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,28,58,1);self.perspective.set_value(38);self.perspective.set_draw_value(False);self.perspective.set_size_request(120,-1);self.perspective.set_tooltip_text("Intensidade da perspectiva")
        self.perspective.connect("value-changed",lambda w:self.viewer.set_fov(w.get_value()));depth_row.add_suffix(self.perspective);camera_group.add(depth_row);box.append(camera_group)
        chain_group=Adw.PreferencesGroup(title="Cadeias");self.chain_box=Gtk.FlowBox();self.chain_box.set_selection_mode(Gtk.SelectionMode.NONE);self.chain_box.set_column_spacing(6);self.chain_box.set_row_spacing(6);chain_group.add(self.chain_box);box.append(chain_group)
        sel_group=Adw.PreferencesGroup(title="Seleção");self.atom_info=Adw.ActionRow(title="Clique em um átomo",subtitle="Elemento, resíduo e cadeia aparecerão aqui.");sel_group.add(self.atom_info);box.append(sel_group)
        info=Adw.PreferencesGroup(title="Método");method=Adw.ActionRow(title="Macromoléculas",subtitle="mmCIF → backbone CA/P → fita 3D nativa; ligantes renderizados separadamente.");method.set_subtitle_lines(3);info.add(method);box.append(info)
        sw.set_child(box);return sw

    def _source_changed(self,*_):
        self.search_source=["Todos","PubChem","RCSB PDB"][self.source.get_selected()];self._schedule_search()
    def _search_changed(self,*_):self._schedule_search()
    def _schedule_search(self):
        if self.search_timer:GLib.source_remove(self.search_timer)
        if len(self.search.get_text().strip())<2:self._clear_results();return
        self.search_timer=GLib.timeout_add(350,self._search_now)
    def _clear_results(self):
        while (c:=self.results.get_first_child()) is not None:self.results.remove(c)
        self.results_revealer.set_reveal_child(False)
    def _search_now(self,*_):
        self.search_timer=0;q=self.search.get_text().strip()
        if len(q)<2:return False
        self.search_generation+=1
        generation=self.search_generation
        self.window.toast("Buscando estruturas…",timeout=1)
        threading.Thread(target=self._search_worker,args=(q,self.search_source,generation),daemon=True).start();return False
    def _search_worker(self,q,source,generation):
        try:items=suggestions(q,source,4);GLib.idle_add(self._show_results,items,generation)
        except Exception as exc:GLib.idle_add(self._search_error,str(exc),generation)
    def _search_error(self,message,generation):
        if generation==self.search_generation:self.window.toast(f"Busca indisponível: {message}")
        return False
    def _show_results(self,items,generation=None):
        if generation is not None and generation!=self.search_generation:return False
        self._clear_results()
        for s in items:
            row=Adw.ActionRow(title=s.title,subtitle=f"{s.source} · {s.subtitle}");row.set_activatable(True);row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"));row.connect("activated",lambda _,ss=s:self._load_suggestion(ss));self.results.append(row)
        self.results_revealer.set_reveal_child(bool(items));return False
    def _load_suggestion(self,s):
        self.search_generation+=1
        self.selected_suggestion=s;self.results_revealer.set_reveal_child(False);self.window.toast(f"Carregando {s.identifier}…",timeout=2)
        threading.Thread(target=self._load_worker,args=(s,),daemon=True).start()
    def _load_worker(self,s):
        try:
            mol=pubchem(s.identifier,self.cache) if s.source=="PubChem" else rcsb(s.identifier,self.cache)
            GLib.idle_add(self._apply_molecule,mol)
        except Exception as exc:GLib.idle_add(self.window.toast,f"Não foi possível carregar a estrutura: {exc}")
    def _apply_molecule(self,mol):
        self.empty.set_visible(False);self.title.set_text(mol.name);md=mol.metadata;self.meta.set_text(f"{mol.source} · {mol.identifier}\n{len(mol.atoms):,} átomos · {md.get('residue_count',0)} resíduos · {md.get('chain_count',0)} cadeias\n{mol.description}".replace(",","."))
        is_poly=md.get("polymer_backbone_atoms",0)>2;self.rep.set_selected(0 if is_poly else 1);self.viewer.visible_chains=None;self.viewer.set_molecule(mol);self._rebuild_chain_buttons(md.get("chains",[]));self._viewer_options_changed();self.window.toast("Estrutura carregada");return False
    def _rebuild_chain_buttons(self,chains):
        while (c:=self.chain_box.get_first_child()) is not None:self.chain_box.remove(c)
        self.chain_buttons=[]
        for chain in chains:
            b=Gtk.ToggleButton(label=chain);b.set_active(True);b.connect("toggled",self._chains_changed);self.chain_box.append(b);self.chain_buttons.append((chain,b))
    def _chains_changed(self,*_):
        active={c for c,b in getattr(self,"chain_buttons",[]) if b.get_active()};self.viewer.configure(visible_chains=active or set())
    def _viewer_options_changed(self,*_):
        rep=REPRESENTATIONS[self.rep.get_selected()][1];self.viewer.configure(representation=rep,show_hydrogens=self.hydrogen.get_active(),show_ligands=self.ligands.get_active(),fog=self.fog.get_active())
    def _atom_selected(self,idx,a):
        title=f"{a.element} · {a.name or 'átomo'}";sub=f"{a.residue} {a.residue_id} · cadeia {a.chain}" if a.residue else f"índice {idx+1}";self.atom_info.set_title(title);self.atom_info.set_subtitle(sub)

    def _import_file(self,*_):
        chooser=Gtk.FileChooserNative.new("Importar estrutura",self.window,Gtk.FileChooserAction.OPEN,"Abrir","Cancelar");f=Gtk.FileFilter();f.set_name("Estruturas químicas");[f.add_pattern(x) for x in ("*.sdf","*.mol","*.pdb","*.cif","*.mmcif")];chooser.add_filter(f);chooser.connect("response",self._file_response);chooser.show()
    def _file_response(self,chooser,response):
        if response!=Gtk.ResponseType.ACCEPT:return
        file=chooser.get_file();path=Path(file.get_path());txt=path.read_text(encoding="utf-8",errors="replace")
        try:
            suf=path.suffix.lower();mol=parse_mmcif(txt,path.stem) if suf in (".cif",".mmcif") else parse_pdb(txt,path.stem) if suf==".pdb" else parse_sdf(txt,path.stem);self._apply_molecule(mol)
        except Exception as exc:self.window.toast(f"Arquivo inválido: {exc}")
    def _toggle_fullscreen(self,*_):
        self._fullscreen=not self._fullscreen
        self.search_area.set_visible(not self._fullscreen);self.inspector.set_visible(not self._fullscreen)
        if self._fullscreen:self.window.fullscreen();self.full_btn.set_icon_name("view-restore-symbolic")
        else:self.window.unfullscreen();self.full_btn.set_icon_name("view-fullscreen-symbolic")

