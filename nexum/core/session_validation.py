"""Structure snapshots validated without importing the desktop toolkit."""
import numpy as np
from .molecular_analysis import molecule_from_dict

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

