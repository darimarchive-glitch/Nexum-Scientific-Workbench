"""Versioned sessions: JSON only, validated before replacing the workspace."""
from gi.repository import Gtk,Adw
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

def validate_structure(data):
    if data is None:return
    m=molecule_from_dict(data['molecule'])
    if any(type(i) is not int or not 0<=i<len(m.atoms) for i in data.get('selection',[])):raise ValueError('Seleção salva inválida.')
    for key,value in data.get('camera',{}).items():
        if not np.isfinite(float(value)) or abs(float(value))>100000:raise ValueError('Câmera inválida.')
    for key,lo,hi in [('zoom',.25,5),('fov_deg',26,62)]:
        if key in data.get('camera',{}) and not lo<=data['camera'][key]<=hi:raise ValueError('Câmera fora dos limites.')
    mesh=data.get('surface')
    if mesh:
        arrays=[np.asarray(mesh[k],dtype=float) for k in ('vertices','normals','colors')]
        if any(a.ndim!=2 or a.shape[1]!=3 or len(a)>1950000 or not np.isfinite(a).all() for a in arrays) or len({a.shape for a in arrays})!=1 or len(arrays[0])%3:raise ValueError('Superfície salva inválida.')
    for key,ncols in [('coordinates_2d',2)]:
        if key in m.metadata:
            a=np.asarray(m.metadata[key],dtype=float)
            if a.shape!=(len(m.atoms),ncols) or not np.isfinite(a).all():raise ValueError('Anotação salva inválida.')
    if any(type(i) is not int or not 0<=i<len(m.atoms) for i in data.get('measurement',[])):raise ValueError('Medição salva inválida.')
    if data.get('view',{}).get('representation','ribbon') not in ('ribbon','ball-stick','spacefill','sticks','backbone','lines'):raise ValueError('Representação inválida.')
    if data.get('view',{}).get('color_mode','element') not in ('element','chain','residue','charge'):raise ValueError('Cor inválida.')
    modes=data.get('vibrations')
    if modes:
        f=np.asarray(modes['frequencies_cm1'],dtype=float);v=np.asarray(modes['displacements'],dtype=float)
        intensity=np.asarray(modes.get('intensities',np.ones(len(f))),dtype=float)
        if f.ndim!=1 or not 1<=len(f)<=3000 or v.shape!=(len(f),len(m.atoms),3) or intensity.shape!=f.shape or not all(np.isfinite(a).all() for a in (f,v,intensity)):raise ValueError('Modos salvos inválidos.')
    charges=m.metadata.get('partial_charges')
    if charges is not None and (len(charges)!=len(m.atoms) or not np.isfinite(charges).all()):raise ValueError('Cargas salvas inválidas.')

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
    for icon,title,callback in [('document-save-symbolic','Salvar sessão completa',save),('document-open-symbolic','Abrir sessão',load)]:
        button=Gtk.Button(icon_name=icon);button.set_tooltip_text(title);button.connect('clicked',callback);header.pack_end(button)
