"""Versioned sessions: JSON only, validated before replacing the workspace."""
from gi.repository import Gtk,Adw,Gio
import numpy as np
from nexum.catalog import ANALYSES
from nexum.core.data_analysis import write_session,read_session,xy_data
from nexum.core.molecular_analysis import molecule_from_dict
from nexum.core.registry import TOOLS
from nexum.core.experiments import EXPERIMENTS
from nexum.core.experiment_session import ExperimentSession
from .molecular_tools import MolecularTools
from .file_actions import choose

def rows_snapshot(rows):return {k:w.get_selected() if isinstance(w,Adw.ComboRow) else w.get_text() for k,w in rows.items()}
def restore_rows(rows,data):
    for k,value in data.items():
        if k not in rows:continue
        w=rows[k]
        if isinstance(w,Adw.ComboRow):w.set_selected(int(value))
        else:w.set_text(str(value))

def snapshot(window):
    exp=window.exp;exp._pause()
    return {'active':window.stack.get_visible_child_name(),'structure':window.struct.analysis.snapshot() if window.struct.viewer.molecule else None,
            'reference':window.struct.analysis.reference,'analysis':window.analysis.snapshot(),
            'calculator':{'id':window.calc.tool[0],'fields':rows_snapshot({k:r for k,(r,_) in window.calc.inputs.items()}),'value':window.calc.value.get_text(),'details':window.calc.details.get_text(),'plots':[p.data for p in window.calc.plots]},
            'experiment':{'id':exp.exp.id,'fields':rows_snapshot(exp.fields),'elapsed':exp.session.elapsed if exp.session else 0,'config':exp.session.config if exp.session else None}}

from nexum.core.session_validation import validate_structure

def validate(data):
    validate_structure(data.get('structure'));validate_structure(data.get('reference'))
    analysis=data.get('analysis',{})
    if not 0<=int(analysis.get('mode',0))<len(ANALYSES):raise ValueError('Análise desconhecida.')
    if analysis.get('dataset'):xy_data(analysis['dataset']['x'],analysis['dataset']['y'],minimum=1)
    if len(analysis.get('references',[]))>8:raise ValueError('Referências demais na sessão.')
    calc=data.get('calculator',{})
    if calc.get('id') not in {t[0] for t in TOOLS}:raise ValueError('Calculadora desconhecida.')
    exp=data.get('experiment',{})
    if exp.get('id') not in {e.id for e in EXPERIMENTS}:raise ValueError('Experimento desconhecido.')
    if exp.get('config') is not None:ExperimentSession(exp['id'],exp['config']).seek(float(exp.get('elapsed',0)))

def restore(window,data):
    validate(data)
    window.analysis.restore(data.get('analysis',{}))
    state=data.get('structure')
    if state:
        window.struct._apply_molecule(molecule_from_dict(state['molecule']))
        MolecularTools.restore_view(window.struct.viewer,state)
        controls=window.struct;view=controls.viewer
        from .structures_page import REPRESENTATIONS
        controls.rep.set_selected(next(i for i,r in enumerate(REPRESENTATIONS) if r[1]==view.representation))
        controls.hydrogen.set_active(state['view'].get('show_hydrogens',False));controls.ligands.set_active(state['view'].get('show_ligands',True));controls.fog.set_active(state['view'].get('fog',True));controls.influence.set_active(state['view'].get('show_influence',False));controls.influence_opacity.set_value(state['view'].get('influence_opacity',.22)*100)
        controls.perspective.set_value(state.get('camera',{}).get('fov_deg',38))
        controls.analysis.mode.set_selected(int(state.get('selection_mode',0)))
        controls.analysis.ids=list(state.get('selection',[]));controls.analysis.vibrations=state.get('vibrations')
        controls.analysis.color.set_selected(['element','chain','residue','charge'].index(state['view'].get('color_mode','element')))
        controls.analysis.opacity.set_value(state['view'].get('surface_opacity',.35)*100);controls.analysis.cut.set_active(state['view'].get('clip_enabled',False));controls.analysis.cut_at.set_value(state['view'].get('clip_fraction',.5)*100)
        for chain,button in controls.chain_buttons:button.set_active(state.get('chains') is None or chain in state['chains'])
        MolecularTools.restore_view(view,state);controls.analysis.diagram.queue_draw()
        modes=controls.analysis.vibrations
        if modes:
            controls.analysis.mode_index.set_range(1,len(modes['frequencies_cm1']))
            controls.analysis.mode_plot.set_plot({'title':'Modos calculados','xlabel':'cm⁻¹','ylabel':'Intensidade relativa','series':[{'name':modes.get('method','Calculado'),'points':list(zip(modes['frequencies_cm1'],modes.get('intensities',[1]*len(modes['frequencies_cm1'])))),'scatter':True}]})
    else:
        window.struct.analysis.reset();view=window.struct.viewer
        view.molecule=None;view.surface_mesh=None;view.scene={};view.selection=set();view.measurement_indices=[];view.queue_render()
        window.struct.empty.set_visible(True);window.struct.title.set_text('Nenhuma estrutura carregada');window.struct.meta.set_text('');window.struct.provenance_text.set_text('')
    window.struct.analysis.reference=data.get('reference')
    calc=data['calculator'];window.calc.select_tool(next(t for t in TOOLS if t[0]==calc['id']));restore_rows({k:r for k,(r,_) in window.calc.inputs.items()},calc.get('fields',{}));window.calc.value.set_text(calc.get('value','—'));window.calc.details.set_text(calc.get('details',''))
    for chart,plot in zip(window.calc.plots,calc.get('plots',[])):chart.set_plot(plot)
    exp=data['experiment'];window.exp._select_experiment(next(i for i,e in enumerate(EXPERIMENTS) if e.id==exp['id']),sync_list=True);window.exp._loading=True
    try:restore_rows(window.exp.fields,exp.get('fields',{}))
    finally:window.exp._loading=False
    window.exp._parameters_changed()
    if window.exp.session:window.exp.session.seek(float(exp.get('elapsed',0)));window.exp._refresh()
    window.stack.set_visible_child_name(data.get('active','home'))

def add_actions(window,header):
    def save(*_):choose(window,'Salvar sessão Nexum',lambda path:write_session(path,snapshot(window)),True,'sessao.nexum')
    def opened(path):
        data=read_session(path);validate(data);previous=snapshot(window)
        try:restore(window,data)
        except Exception:
            restore(window,previous);raise
        window.toast('Sessão restaurada.')
    def load(*_):choose(window,'Abrir sessão Nexum',opened)
    menu=Gio.Menu();sessions=Gio.Menu()
    for name,title,callback in [('open-session','Abrir sessão',load),('save-session','Salvar sessão completa',save)]:
        action=Gio.SimpleAction.new(name,None);action.connect('activate',callback);window.add_action(action)
        sessions.append(title,'win.'+name)
    menu.append_section(None,sessions)
    menu.append_submenu('Tema',window.appearance.menu())
    button=Gtk.MenuButton(icon_name='open-menu-symbolic',menu_model=menu)
    button.set_tooltip_text('Sessões e aparência');header.pack_end(button)
