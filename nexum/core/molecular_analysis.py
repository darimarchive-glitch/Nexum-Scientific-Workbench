"""Geometric analysis and bounded grid surfaces. Coordinates are in angstroms."""
from dataclasses import asdict
import math
import numpy as np
from scipy.ndimage import distance_transform_edt, map_coordinates
from .structures import Atom, Molecule, vdw_radius

def measurement(molecule, indices):
    ids=list(indices)
    if len(ids) not in (2,3,4) or len(set(ids))!=len(ids):
        raise ValueError("Selecione 2, 3 ou 4 átomos distintos.")
    if any(type(i) is not int or not 0<=i<len(molecule.atoms) for i in ids):
        raise ValueError("Índice de átomo inválido.")
    p=np.array([molecule.atoms[i].position for i in ids],dtype=float)
    if len(ids)==2:
        return "Distância",float(np.linalg.norm(p[1]-p[0])),"Å"
    if len(ids)==3:
        a,b=p[0]-p[1],p[2]-p[1]
        d=np.linalg.norm(a)*np.linalg.norm(b)
        if d<1e-12:raise ValueError("Ângulo indefinido: pontos coincidentes.")
        return "Ângulo",float(np.degrees(np.arccos(np.clip(np.dot(a,b)/d,-1,1)))),"°"
    b0=-(p[1]-p[0]);b1=p[2]-p[1];b2=p[3]-p[2]
    if np.linalg.norm(b1)<1e-12:raise ValueError("Diedro indefinido.")
    b1/=np.linalg.norm(b1)
    v=b0-np.dot(b0,b1)*b1;w=b2-np.dot(b2,b1)*b1
    if min(np.linalg.norm(v),np.linalg.norm(w))<1e-12:
        raise ValueError("Diedro indefinido: átomos colineares.")
    return "Diedro",float(np.degrees(np.arctan2(np.dot(np.cross(b1,v),w),np.dot(v,w)))),"°"

def molecule_from_dict(data):
    if not isinstance(data,dict):raise ValueError("Estrutura inválida.")
    atoms=data.get("atoms",[])
    if not 1<=len(atoms)<=200000:raise ValueError("Estrutura deve conter 1–200.000 átomos.")
    aa=[Atom(**a) for a in atoms]
    if not np.isfinite([[a.x,a.y,a.z] for a in aa]).all():raise ValueError("Coordenadas não finitas.")
    bonds=data.get("bonds",[])
    for bond in bonds:
        if len(bond)!=3 or any(type(i) is not int or not 0<=i<len(aa) for i in bond[:2]):
            raise ValueError("Ligação inválida.")
    return Molecule(str(data.get("name","Estrutura")),aa,[tuple(b) for b in bonds],
                    str(data.get("source","local")),str(data.get("identifier","")),
                    str(data.get("description","")),dict(data.get("metadata",{})))

def annotate(data):
    """RDKit operation; used through the chemistry worker on Windows."""
    from rdkit import Chem
    from rdkit.Chem import AllChem, rdDepictor
    molecule=molecule_from_dict(data)
    if len(molecule.atoms)>3000:raise ValueError("Anotação 2D limitada a 3.000 átomos.")
    rw=Chem.RWMol()
    for a in molecule.atoms:rw.AddAtom(Chem.Atom(a.element))
    for i,j,order in molecule.bonds:
        if i!=j and not rw.GetBondBetweenAtoms(i,j):
            rw.AddBond(i,j,{1:Chem.BondType.SINGLE,2:Chem.BondType.DOUBLE,3:Chem.BondType.TRIPLE}.get(order,Chem.BondType.SINGLE))
    mol=rw.GetMol()
    Chem.SanitizeMol(mol)
    rdDepictor.Compute2DCoords(mol)
    molecule.metadata["coordinates_2d"]=[[mol.GetConformer().GetAtomPosition(i).x,mol.GetConformer().GetAtomPosition(i).y] for i in range(mol.GetNumAtoms())]
    patterns={"Hidroxila":"[OX2H]","Carbonila":"[CX3]=[OX1]","Carboxila":"[CX3](=O)[OX2H1]","Amina":"[NX3;!$(N-C=O)]","Amida":"[NX3][CX3](=[OX1])","Anel aromático":"a1aaaaa1"}
    molecule.metadata["functional_groups"]={name:[list(match) for match in mol.GetSubstructMatches(Chem.MolFromSmarts(smarts))] for name,smarts in patterns.items()}
    try:
        AllChem.ComputeGasteigerCharges(mol)
        charges=[float(a.GetProp("_GasteigerCharge")) for a in mol.GetAtoms()]
        if np.isfinite(charges).all():
            molecule.metadata["partial_charges"]=charges
            molecule.metadata["charge_method"]="Gasteiger (estimativa empírica; cargas em e)"
    except (ValueError,RuntimeError):pass
    molecule.metadata["annotation_method"]="RDKit; conectividade e ordens de ligação carregadas"
    return molecule

def isosurface(values,origin,axes,level):
    """Marching tetrahedra; bounded grids, no extra native dependency."""
    f=np.asarray(values,dtype=float)
    if f.ndim!=3 or min(f.shape)<2 or max(f.shape)>128 or f.size>1100000 or not np.isfinite(f).all():
        raise ValueError("Grade inválida ou muito grande (máximo 128 por eixo / 1,1 milhão de pontos).")
    level=float(level)
    if not math.isfinite(level) or not f.min()<level<f.max():
        raise ValueError("Isovalor fora do intervalo dos dados.")
    offsets=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]])
    shape=np.array(f.shape)-1
    fv=np.stack([f[o[0]:o[0]+shape[0],o[1]:o[1]+shape[1],o[2]:o[2]+shape[2]].ravel() for o in offsets],axis=1)
    active=(fv.min(axis=1)<level)&(fv.max(axis=1)>level)
    cells=np.argwhere(np.ones(tuple(shape),dtype=bool))[active]
    fv=fv[active]
    points=cells[:,None,:]+offsets[None,:,:]
    triangles=[]
    for tet in ((0,5,1,6),(0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6)):
        v=fv[:,tet];p=points[:,tet,:]
        codes=((v<level)*np.array([1,2,4,8])).sum(axis=1)
        for code in range(1,15):
            take=codes==code
            if not take.any():continue
            inside=[i for i in range(4) if code&(1<<i)]
            outside=[i for i in range(4) if not code&(1<<i)]
            vv=v[take];pp=p[take]
            def edge(i,j):
                t=(level-vv[:,i])/(vv[:,j]-vv[:,i])
                return pp[:,i]+t[:,None]*(pp[:,j]-pp[:,i])
            if len(inside)==1:
                i=inside[0];triangles.append(np.stack([edge(i,j) for j in outside],axis=1))
            elif len(inside)==3:
                j=outside[0];triangles.append(np.stack([edge(i,j) for i in inside],axis=1))
            else:
                a,b=inside;c,d=outside
                ac,ad,bc,bd=edge(a,c),edge(a,d),edge(b,c),edge(b,d)
                triangles.extend((np.stack([ac,ad,bc],axis=1),np.stack([ad,bd,bc],axis=1)))
    if not triangles:raise ValueError("Nenhuma superfície para esse isovalor.")
    vertices=np.concatenate(triangles)@np.asarray(axes)+np.asarray(origin)
    if len(vertices)>650000:raise ValueError("Superfície muito complexa; reduza a resolução.")
    normals=np.cross(vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0])
    lengths=np.linalg.norm(normals,axis=1)
    keep=lengths>1e-10
    normals=normals[keep]/lengths[keep,None]
    return {"vertices":vertices[keep].reshape(-1,3).astype("float32"),
            "normals":np.repeat(normals,3,axis=0).astype("float32")}

def molecular_surface(molecule,kind="vdw",probe=1.4,resolution=48,indices=None):
    if kind not in ("vdw","sas","ses"):raise ValueError("Superfície desconhecida.")
    probe=float(probe);resolution=int(resolution)
    if not math.isfinite(probe) or not .1<=probe<=5 or not 20<=resolution<=80:
        raise ValueError("Sonda: 0,1–5 Å; resolução: 20–80.")
    atoms=molecule.atoms if indices is None else [molecule.atoms[i] for i in indices]
    if not atoms or len(atoms)>30000:raise ValueError("Selecione entre 1 e 30.000 átomos para a superfície.")
    p=np.array([[a.x,a.y,a.z] for a in atoms])
    r=np.array([vdw_radius(a.element) for a in atoms])+(0 if kind=="vdw" else probe)
    low=(p-r[:,None]).min(axis=0)-probe-1
    high=(p+r[:,None]).max(axis=0)+probe+1
    step=float((high-low).max()/(resolution-1))
    shape=np.maximum(3,np.ceil((high-low)/step).astype(int)+1)
    grid=np.full(tuple(shape),step*3,dtype=float)
    # Only touch the local bounding box of each sphere.
    for center,radius in zip(p,r):
        start=np.maximum(0,np.floor((center-radius-step-low)/step).astype(int))
        stop=np.minimum(shape,np.ceil((center+radius+step-low)/step).astype(int)+1)
        xyz=np.ogrid[tuple(slice(int(a),int(b)) for a,b in zip(start,stop))]
        d=np.sqrt(sum((low[k]+xyz[k]*step-center[k])**2 for k in range(3)))-radius
        sl=tuple(slice(int(a),int(b)) for a,b in zip(start,stop))
        grid[sl]=np.minimum(grid[sl],d)
    if kind=="ses":
        # Grid approximation to erosion of the probe-expanded union.
        grid=probe-distance_transform_edt(grid<0,sampling=step)
    mesh=isosurface(grid,low,np.eye(3)*step,0)
    mesh["method"]=f"{kind.upper()}; passo da grade {step:.3g} Å; sonda {probe:g} Å. SES: aproximação por erosão em grade."
    mesh["colors"]=np.tile(np.array([.25,.65,.72],dtype="float32"),(len(mesh["vertices"]),1))
    return mesh

def parse_cube(text):
    """Single scalar field Cube. Positive voxel counts mean Bohr, negative Å."""
    if len(text)>70000000:raise ValueError("Cube excede 70 MB.")
    lines=text.splitlines()
    if len(lines)<7:raise ValueError("Cube incompleto.")
    h=lines[2].split();n=int(h[0]);origin=np.array(list(map(float,h[1:4])))
    if n<0 or (len(h)>4 and int(h[4])!=1):
        raise ValueError("Exporte um único campo/orbital por arquivo Cube.")
    counts=[];axes=[]
    for line in lines[3:6]:
        parts=line.split();counts.append(int(parts[0]));axes.append(list(map(float,parts[1:4])))
    if any(c==0 for c in counts) or not (all(c>0 for c in counts) or all(c<0 for c in counts)):
        raise ValueError("Contagens/unidades de grade inconsistentes.")
    shape=tuple(abs(c) for c in counts)
    if min(shape)<2 or max(shape)>128 or math.prod(shape)>1100000 or n>200000:raise ValueError("Grade Cube fora dos limites.")
    factor=.529177210903 if counts[0]>0 else 1.
    axes=np.array(axes)*factor;origin*=factor
    if abs(np.linalg.det(axes))<1e-12:raise ValueError("Eixos Cube degenerados.")
    # Atom labels are resolved from the periodic table via a local standard list.
    symbols="X H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
    atoms=[]
    for line in lines[6:6+n]:
        a=line.split();z=int(a[0])
        if not 1<=z<len(symbols):raise ValueError("Número atômico Cube não suportado.")
        atoms.append(Atom(symbols[z],*(np.array(list(map(float,a[2:5])))*factor)))
    raw=" ".join(lines[6+n:]).replace("D","E").replace("d","e")
    values=np.fromstring(raw,sep=" ")
    if values.size!=math.prod(shape) or not np.isfinite(values).all():raise ValueError("Número de valores Cube incorreto.")
    return {"values":values.reshape(shape),"origin":origin,"axes":axes,
            "molecule":Molecule(lines[0] or "Cube",atoms,[],description=lines[1]),
            "description":" / ".join(lines[:2])}

def sample_cube(cube,points):
    coordinates=(np.asarray(points)-cube["origin"])@np.linalg.inv(cube["axes"])
    shape=np.array(cube["values"].shape)
    if ((coordinates<0)|(coordinates>shape-1)).any():
        raise ValueError("A superfície está fora da grade de potencial. Use grades alinhadas.")
    return map_coordinates(cube["values"],coordinates.T,order=1,mode="nearest")

def scalar_colors(values,limit=None):
    values=np.asarray(values,dtype=float)
    limit=float(limit or np.max(np.abs(values)) or 1)
    v=np.clip(values/limit,-1,1)
    # Blue negative / orange positive: diverging, with numeric legend in UI.
    neutral=np.array([.9,.9,.85]);neg=np.array([.15,.35,.8]);pos=np.array([.9,.35,.05])
    return np.where((v<0)[:,None],neutral+(-v[:,None])*(neg-neutral),neutral+v[:,None]*(pos-neutral)).astype("float32"),limit
