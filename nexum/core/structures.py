from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json, math, re, time

import numpy as np


@dataclass
class Atom:
    element: str
    x: float
    y: float
    z: float
    name: str = ""
    residue: str = ""
    residue_id: str = ""
    chain: str = ""
    hetero: bool = False

    @property
    def position(self):
        return np.array((self.x, self.y, self.z), dtype=np.float32)


@dataclass
class Molecule:
    name: str
    atoms: list[Atom]
    bonds: list[tuple[int, int, int]]
    source: str = "local"
    identifier: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class StructureSuggestion:
    source: str
    identifier: str
    title: str
    subtitle: str = ""


COMMON_COLORS = {
    "H": (0.93, 0.93, 0.93), "C": (0.23, 0.25, 0.28), "N": (0.20, 0.36, 0.88),
    "O": (0.91, 0.16, 0.16), "F": (0.35, 0.80, 0.38), "Cl": (0.24, 0.78, 0.30),
    "Br": (0.55, 0.16, 0.10), "I": (0.47, 0.18, 0.62), "P": (0.95, 0.50, 0.12),
    "S": (0.92, 0.78, 0.12), "B": (0.95, 0.62, 0.62), "Si": (0.75, 0.62, 0.48),
    "Fe": (0.88, 0.39, 0.16), "Cu": (0.78, 0.45, 0.20), "Zn": (0.50, 0.52, 0.70),
    "Mg": (0.45, 0.82, 0.35), "Ca": (0.30, 0.72, 0.34), "Na": (0.45, 0.38, 0.88),
    "K": (0.55, 0.28, 0.72), "Mn": (0.60, 0.32, 0.70), "Co": (0.92, 0.40, 0.48),
    "Ni": (0.35, 0.70, 0.45), "Se": (0.96, 0.63, 0.10), "Hg": (0.72, 0.72, 0.82),
}
COMMON_VDW = {
    "H":1.20,"He":1.40,"Li":1.82,"Be":1.53,"B":1.92,"C":1.70,"N":1.55,"O":1.52,"F":1.47,"Ne":1.54,
    "Na":2.27,"Mg":1.73,"Al":1.84,"Si":2.10,"P":1.80,"S":1.80,"Cl":1.75,"Ar":1.88,"K":2.75,"Ca":2.31,
    "Fe":2.00,"Co":2.00,"Ni":1.63,"Cu":1.40,"Zn":1.39,"Ga":1.87,"Ge":2.11,"As":1.85,"Se":1.90,"Br":1.85,
    "Kr":2.02,"Ag":1.72,"Cd":1.58,"In":1.93,"Sn":2.17,"Sb":2.06,"Te":2.06,"I":1.98,"Xe":2.16,"Au":1.66,
    "Hg":1.55,"Pb":2.02,"Bi":2.07,"U":1.86,
}
COMMON_COV = {
    "H":0.31,"C":0.76,"N":0.71,"O":0.66,"F":0.57,"P":1.07,"S":1.05,"Cl":1.02,"Br":1.20,"I":1.39,
    "Fe":1.32,"Cu":1.32,"Zn":1.22,"Mg":1.41,"Ca":1.76,"Na":1.66,"K":2.03,"Se":1.20,"Si":1.11,
}
CHAIN_COLORS = [
    (0.22,0.48,0.86),(0.87,0.43,0.26),(0.28,0.66,0.45),(0.68,0.43,0.83),
    (0.84,0.64,0.20),(0.20,0.66,0.72),(0.82,0.38,0.58),(0.52,0.61,0.28),
    (0.39,0.52,0.78),(0.76,0.51,0.32),(0.34,0.62,0.56),(0.59,0.48,0.72),
]


def _norm_el(symbol: str) -> str:
    s = re.sub(r"[^A-Za-z]", "", symbol or "")
    if not s: return "C"
    return s[:1].upper() + s[1:2].lower()


def element_color(symbol: str):
    s = _norm_el(symbol)
    if s in COMMON_COLORS: return COMMON_COLORS[s]
    # Stable, restrained fallback: no element disappears even when it lacks a hand-tuned CPK color.
    h = sum((i+1)*ord(c) for i,c in enumerate(s))
    return (0.35 + ((h*37)%45)/100, 0.35 + ((h*53)%45)/100, 0.35 + ((h*71)%45)/100)


def vdw_radius(symbol: str):
    s = _norm_el(symbol)
    try:
        import gemmi
        r = float(gemmi.Element(s).vdw_r)
        if r > 0: return r
    except Exception:
        pass
    return COMMON_VDW.get(s, 1.80)


def covalent_radius(symbol: str):
    s = _norm_el(symbol)
    try:
        import gemmi
        r = float(gemmi.Element(s).covalent_r)
        if r > 0: return r
    except Exception:
        pass
    return COMMON_COV.get(s, 0.90)


def parse_sdf(text, name="Molécula"):
    lines=text.splitlines()
    if len(lines)<4: raise ValueError("SDF inválido.")
    counts=lines[3]; na=int(counts[:3]); nb=int(counts[3:6]); atoms=[]; bonds=[]
    for line in lines[4:4+na]:
        el=_norm_el(line[31:34].strip() or "C")
        atoms.append(Atom(el,float(line[:10]),float(line[10:20]),float(line[20:30]),name=el))
    for line in lines[4+na:4+na+nb]:
        bonds.append((int(line[:3])-1,int(line[3:6])-1,max(1,int(line[6:9]) or 1)))
    if not atoms: raise ValueError("SDF sem átomos.")
    return Molecule(name,atoms,bonds,"SDF")


def parse_pdb(text,name="PDB"):
    atoms=[]; serial={}; bonds=[]
    for line in text.splitlines():
        if line.startswith(("ATOM  ","HETATM")):
            try:
                alt=line[16:17]
                if alt not in (" ","A","1"): continue
                idx=len(atoms); s=int(line[6:11]); serial[s]=idx
                an=line[12:16].strip(); res=line[17:20].strip(); chain=line[21:22].strip() or "∅"; resid=line[22:27].strip()
                el=_norm_el(line[76:78].strip() or re.sub(r"[^A-Za-z]","",an)[:2])
                atoms.append(Atom(el,float(line[30:38]),float(line[38:46]),float(line[46:54]),an,res,resid,chain,line.startswith("HETATM")))
            except (ValueError,IndexError):
                continue
    seen=set()
    for line in text.splitlines():
        if line.startswith("CONECT"):
            p=line.split()
            if len(p)<3: continue
            try:a=serial.get(int(p[1]))
            except ValueError:continue
            if a is None:continue
            for tok in p[2:]:
                try:b=serial.get(int(tok))
                except ValueError:continue
                if b is None:continue
                key=tuple(sorted((a,b)))
                if key not in seen: seen.add(key); bonds.append((key[0],key[1],1))
    if not atoms: raise ValueError("Nenhum átomo reconhecido no PDB.")
    if not bonds and len(atoms)<=5000: bonds=infer_bonds(atoms)
    return Molecule(name,atoms,bonds,"PDB",identifier=name,metadata=_structure_metadata(atoms))


def parse_mmcif(text,name="mmCIF"):
    try:
        import gemmi
    except Exception as exc:
        raise RuntimeError("Leitura mmCIF requer gemmi.") from exc
    doc=gemmi.cif.read_string(text)
    st=gemmi.make_structure_from_block(doc.sole_block())
    if len(st)==0:
        raise ValueError("mmCIF sem modelo estrutural.")
    model=st[0]
    atoms=[]
    residue_order=[]
    for chain in model:
        cname=chain.name or "∅"
        for res in chain:
            # Keep the best alternate location for each atom name first, then classify
            # the residue.  Relying only on gemmi's het_flag proved too fragile across
            # deposited mmCIF files and could mark a polymer chain as hetero, making the
            # CA/P ribbon disappear entirely.
            by_name={}
            for a in res:
                key=a.name.strip()
                if not key:
                    continue
                alt=str(a.altloc).strip("\x00 ") if hasattr(a,"altloc") else ""
                score=(1 if alt in ("","A","1") else 0, float(getattr(a,"occ",0.0) or 0.0))
                old=by_name.get(key)
                if old is None or score>old[0]:
                    by_name[key]=(score,a)
            names=set(by_name)
            protein_like="CA" in names and ("N" in names or "C" in names)
            nucleic_like="P" in names and any(x in names for x in ("C4'","C3'","O3'","O5'","C4*","C3*"))
            atom_record_like=str(getattr(res,"het_flag","")).strip() == "A"
            polymer=protein_like or nucleic_like or atom_record_like
            hetero=not polymer
            residue_order.append((cname,str(res.seqid),res.name,hetero))
            for key,(_,a) in by_name.items():
                atoms.append(Atom(_norm_el(a.element.name),float(a.pos.x),float(a.pos.y),float(a.pos.z),key,res.name,str(res.seqid),cname,hetero))
    if not atoms:
        raise ValueError("Nenhum átomo reconhecido no mmCIF.")
    bonds=[]
    # For biological structures the ribbon/backbone does not need full inferred bonding.
    # Infer ligand/hetero connectivity so heme, cofactors and ions remain visible.
    hetero_idx=[i for i,a in enumerate(atoms) if a.hetero]
    if 1 < len(hetero_idx) <= 6000:
        bonds=infer_bonds_subset(atoms,hetero_idx)
    md=_structure_metadata(atoms)
    md.update({"residue_count":len(residue_order),"format":"PDBx/mmCIF"})
    return Molecule(name,atoms,bonds,"mmCIF",identifier=name,metadata=md)


def _structure_metadata(atoms):
    chains=[]
    for a in atoms:
        if a.chain not in chains: chains.append(a.chain)
    residues=[]; seen=set()
    for a in atoms:
        k=(a.chain,a.residue_id,a.residue)
        if k not in seen: seen.add(k); residues.append(k)
    return {
        "chains":chains,"chain_count":len(chains),"residue_count":len(residues),
        "polymer_backbone_atoms":sum(1 for a in atoms if not a.hetero and a.name in ("CA","P")),
        "hetero_atoms":sum(1 for a in atoms if a.hetero),
    }


def infer_bonds(atoms):
    return infer_bonds_subset(atoms,range(len(atoms)))


def infer_bonds_subset(atoms, indices):
    indices=list(indices); out=[]; cell=2.6; bins={}
    for i in indices:
        a=atoms[i]; bins.setdefault((math.floor(a.x/cell),math.floor(a.y/cell),math.floor(a.z/cell)),[]).append(i)
    for i in indices:
        a=atoms[i]; bx,by,bz=math.floor(a.x/cell),math.floor(a.y/cell),math.floor(a.z/cell)
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    for j in bins.get((bx+dx,by+dy,bz+dz),[]):
                        if j<=i: continue
                        b=atoms[j]; d=math.dist((a.x,a.y,a.z),(b.x,b.y,b.z))
                        lim=covalent_radius(a.element)+covalent_radius(b.element)+0.48
                        if 0.25 < d < lim: out.append((i,j,1))
    return out


def _catmull_rom(p0,p1,p2,p3,t):
    t2=t*t; t3=t2*t
    return 0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t2+(-p0+3*p1-3*p2+p3)*t3)


def _smooth_trace(points, subdivisions=5):
    pts=np.asarray(points,dtype=np.float32)
    if len(pts)<2:return pts
    if len(pts)<4:return pts
    out=[]
    for i in range(len(pts)-1):
        p0=pts[max(0,i-1)];p1=pts[i];p2=pts[i+1];p3=pts[min(len(pts)-1,i+2)]
        for j in range(subdivisions): out.append(_catmull_rom(p0,p1,p2,p3,j/subdivisions))
    out.append(pts[-1]); return np.asarray(out,dtype=np.float32)


def backbone_traces(molecule: Molecule):
    """Return ordered CA (protein) or P (nucleic acid) traces per chain."""
    chains={}; seen={}
    # Preserve file order. One representative atom per residue.
    for a in molecule.atoms:
        if a.hetero: continue
        key=(a.chain,a.residue_id)
        if key in seen: continue
        if a.name=="CA":
            chains.setdefault(a.chain,[]).append(a.position); seen[key]=True
    # Chains without CA may be nucleic acid: use phosphate P.
    present=set(chains)
    seen2=set()
    for a in molecule.atoms:
        if a.hetero or a.chain in present: continue
        key=(a.chain,a.residue_id)
        if key in seen2: continue
        if a.name=="P": chains.setdefault(a.chain,[]).append(a.position); seen2.add(key)
    return {c:np.asarray(v,dtype=np.float32) for c,v in chains.items() if len(v)>=2}


def build_ribbon_mesh(molecule: Molecule, width=1.55, subdivisions=5, thickness=0.22):
    """Build an extruded 3-D polymer ribbon following each CA/P trace.

    v5 used a zero-thickness triangle strip.  It was mathematically 3-D but could
    almost vanish when a chain was viewed edge-on.  This mesh has top, bottom and
    side faces, so proteins such as hemoglobin keep visible depth while rotating.
    It is a structural cartoon derived from deposited coordinates, not an electron
    density or secondary-structure assignment.
    """
    meshes=[]
    half_w=max(0.05,float(width)/2)
    half_t=max(0.02,float(thickness)/2)
    for ci,(chain,raw) in enumerate(backbone_traces(molecule).items()):
        pts=_smooth_trace(raw,subdivisions)
        if len(pts)<2:
            continue
        tang=[]
        for i in range(len(pts)):
            if i==0:
                t=pts[1]-pts[0]
            elif i==len(pts)-1:
                t=pts[-1]-pts[-2]
            else:
                t=pts[i+1]-pts[i-1]
            n=np.linalg.norm(t)
            tang.append(t/n if n>1e-8 else np.array((1,0,0),dtype=np.float32))
        sides=[]; prev=None
        for t in tang:
            if prev is None:
                up=np.array((0,1,0),dtype=np.float32)
                if abs(float(np.dot(t,up)))>.88:
                    up=np.array((1,0,0),dtype=np.float32)
                side=np.cross(t,up); side/=max(np.linalg.norm(side),1e-8)
            else:
                side=prev-t*float(np.dot(prev,t)); n=np.linalg.norm(side)
                if n<1e-6:
                    up=np.array((0,1,0),dtype=np.float32)
                    if abs(float(np.dot(t,up)))>.88:
                        up=np.array((1,0,0),dtype=np.float32)
                    side=np.cross(t,up); n=np.linalg.norm(side)
                side/=max(n,1e-8)
                if float(np.dot(side,prev))<0:
                    side=-side
            sides.append(side); prev=side
        normals=[]
        for t,side in zip(tang,sides):
            n=np.cross(side,t); n/=max(np.linalg.norm(n),1e-8); normals.append(n)
        corners=[]
        for p,side,n in zip(pts,sides,normals):
            corners.append((
                p-side*half_w+n*half_t,  # left top
                p+side*half_w+n*half_t,  # right top
                p-side*half_w-n*half_t,  # left bottom
                p+side*half_w-n*half_t,  # right bottom
            ))
        verts=[]; norms=[]
        def tri(a,b,c,n):
            verts.extend((a,b,c)); norms.extend((n,n,n))
        for i in range(len(corners)-1):
            lt,rt,lb,rb=corners[i]; lt2,rt2,lb2,rb2=corners[i+1]
            n0=normals[i]+normals[i+1]; n0/=max(np.linalg.norm(n0),1e-8)
            side0=sides[i]+sides[i+1]; side0/=max(np.linalg.norm(side0),1e-8)
            # top and bottom
            tri(lt,rt,lt2,n0); tri(rt,rt2,lt2,n0)
            tri(lb2,rb,lb,-n0); tri(lb2,rb2,rb,-n0)
            # left and right side walls
            tri(lb,lt,lb2,-side0); tri(lt,lt2,lb2,-side0)
            tri(rt,rb,rt2,side0); tri(rb,rb2,rt2,side0)
        meshes.append({
            "chain":chain,
            "color":CHAIN_COLORS[ci%len(CHAIN_COLORS)],
            "vertices":np.asarray(verts,dtype=np.float32),
            "normals":np.asarray(norms,dtype=np.float32),
            "primitive":"triangles",
        })
    return meshes


def molecule_center_radius(molecule):
    if not molecule.atoms:return np.zeros(3,dtype=np.float32),1.0
    p=np.asarray([[a.x,a.y,a.z] for a in molecule.atoms],dtype=np.float32);c=p.mean(axis=0);r=float(np.max(np.linalg.norm(p-c,axis=1)))
    return c,max(1.0,r)


def _get(url,timeout=55):
    """HTTP GET with a small retry budget for transient API/network failures.

    404 is never retried because callers use it as a semantic signal (e.g. a
    PubChem record without a deposited 3-D conformer).  Rate-limit and server
    failures are retried once with a short backoff.
    """
    req=Request(url,headers={"User-Agent":"Nexum-GNOME/6.0","Accept":"application/json,text/plain,*/*"})
    last=None
    for attempt in range(2):
        try:
            with urlopen(req,timeout=timeout) as r:return r.read().decode("utf-8","replace")
        except HTTPError as exc:
            last=exc
            if exc.code==404 or (400 <= exc.code < 500 and exc.code!=429):raise
        except URLError as exc:
            last=exc
        if attempt==0:time.sleep(0.35)
    raise last


def _post_json(url,payload,timeout=35):
    body=json.dumps(payload).encode()
    req=Request(url,data=body,headers={"User-Agent":"Nexum-GNOME/6.0","Content-Type":"application/json","Accept":"application/json"},method="POST")
    with urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())


def resolve_pubchem_cid(identifier):
    raw=str(identifier).strip()
    if raw.isdigit():return raw
    data=json.loads(_get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(raw)}/cids/JSON"))
    cids=data.get("IdentifierList",{}).get("CID",[])
    if not cids:raise ValueError(f"Nenhum CID do PubChem corresponde a ‘{raw}’.")
    return str(cids[0])


def pubchem_suggestions(term,limit=4):
    term=term.strip()
    if len(term)<2:return []
    data=json.loads(_get(f"https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound/{quote(term)}/json?limit={int(max(limit,4))}"))
    names=data.get("dictionary_terms",{}).get("compound",[])[:max(limit,4)]
    out=[];seen=set()
    # Resolve suggestions to canonical CIDs before exposing them to the UI. This
    # prevents the selected autocomplete text from becoming a second ambiguous name lookup.
    for n in names:
        if len(out)>=limit:break
        try:
            cid=resolve_pubchem_cid(n)
            if cid in seen:continue
            props=_pubchem_properties(cid)
            title=props.get("Title") or n
            formula=props.get("MolecularFormula") or ""
            out.append(StructureSuggestion("PubChem",cid,title,f"CID {cid}"+(f" · {formula}" if formula else "")))
            seen.add(cid)
        except Exception:
            continue
    return out


def rcsb_suggestions(term,limit=4):
    q=term.strip()
    if len(q)<2:return []
    direct=[]
    if re.fullmatch(r"[A-Za-z0-9]{4}",q): direct=[StructureSuggestion("RCSB PDB",q.upper(),f"Estrutura PDB {q.upper()}","Identificador PDB direto")]
    payload={"query":{"type":"terminal","service":"full_text","parameters":{"value":q}},"return_type":"entry","request_options":{"paginate":{"start":0,"rows":int(limit)}}}
    try:data=_post_json("https://search.rcsb.org/rcsbsearch/v2/query",payload)
    except Exception:return direct[:limit]
    out=[];seen={x.identifier for x in direct}
    for item in data.get("result_set",[])[:limit]:
        pid=str(item.get("identifier","")).upper()
        if not pid or pid in seen:continue
        title=f"Estrutura PDB {pid}";subtitle="Macromolécula / complexo biológico"
        try:
            meta=json.loads(_get(f"https://data.rcsb.org/rest/v1/core/entry/{pid}",timeout=20))
            title=(meta.get("struct") or {}).get("title") or title
            methods=[x.get("method") for x in (meta.get("exptl") or []) if x.get("method")]
            if methods:subtitle=" · ".join(methods)
        except Exception:pass
        out.append(StructureSuggestion("RCSB PDB",pid,title,subtitle));seen.add(pid)
    return (direct+out)[:limit]


def suggestions(term,source="Todos",limit=4):
    if source.startswith("PubChem"):return pubchem_suggestions(term,limit)
    if source.startswith("RCSB"):return rcsb_suggestions(term,limit)
    q=term.strip().lower()
    # Biological/macromolecular wording is deliberately routed to RCSB first.
    macro_words=("protein","proteína","enzyme","enzima","hemo","hemoglo","hemoglobin","hemoglobina","dna","rna","ribosom","antibody","anticorpo","receptor","kinase","quinase")
    macro_hint=bool(re.fullmatch(r"[a-z0-9]{4}",q)) or any(k in q for k in macro_words)
    a=[];b=[]
    try:b=rcsb_suggestions(term,limit if macro_hint else max(2,limit//2))
    except Exception:pass
    try:a=pubchem_suggestions(term,max(1,limit-len(b)) if macro_hint else max(2,limit//2))
    except Exception:pass
    merged=(b+a) if macro_hint else (a+b)
    return merged[:limit]


def _pubchem_properties(cid):
    props="Title,MolecularFormula,IsomericSMILES,CanonicalSMILES"
    data=json.loads(_get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/{props}/JSON"))
    rows=data.get("PropertyTable",{}).get("Properties",[])
    return rows[0] if rows else {}


def _rdkit_embed(mol,title,cid):
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except Exception as exc:
        raise RuntimeError("O registro não possui conformador 3D no PubChem e o gerador local RDKit não está disponível.") from exc
    if mol is None:raise RuntimeError("O registro químico não pôde ser convertido em uma estrutura molecular válida.")
    mol=Chem.AddHs(mol)
    params=AllChem.ETKDGv3();params.randomSeed=0x4E455855;params.useRandomCoords=True
    code=AllChem.EmbedMolecule(mol,params)
    if code!=0:raise RuntimeError("O gerador local não encontrou um conformador 3D para este registro.")
    optimizer="geometria ETKDGv3"
    try:
        if AllChem.MMFFHasAllMoleculeParams(mol):AllChem.MMFFOptimizeMolecule(mol,maxIters=800);optimizer="ETKDGv3 + MMFF"
        else:AllChem.UFFOptimizeMolecule(mol,maxIters=800);optimizer="ETKDGv3 + UFF"
    except Exception:pass
    block=Chem.MolToMolBlock(mol)
    m=parse_sdf(block,title);m.source="PubChem + RDKit";m.identifier=str(cid);m.metadata["conformer"]=f"{optimizer} local";return m


def _rdkit_conformer_from_smiles(smiles,title,cid):
    try:
        from rdkit import Chem
    except Exception as exc:
        raise RuntimeError("O gerador local RDKit não está disponível.") from exc
    return _rdkit_embed(Chem.MolFromSmiles(smiles or ""),title,cid)


def _rdkit_conformer_from_molblock(block,title,cid):
    try:
        from rdkit import Chem
    except Exception as exc:
        raise RuntimeError("O gerador local RDKit não está disponível.") from exc
    mol=Chem.MolFromMolBlock(block or "",sanitize=True,removeHs=False)
    return _rdkit_embed(mol,title,cid)


def pubchem(identifier,cache:Path):
    cache.mkdir(parents=True,exist_ok=True);cid=resolve_pubchem_cid(identifier);props={}
    try:props=_pubchem_properties(cid)
    except Exception:pass
    title=props.get("Title") or str(identifier);p=cache/f"pubchem_{cid}_3d.sdf"
    txt=None
    if p.exists() and p.stat().st_size>=50:
        txt=p.read_text(errors="replace")
    else:
        try:
            txt=_get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=3d")
            if len(txt)>=50:p.write_text(txt)
        except HTTPError as exc:
            if exc.code!=404:raise
            txt=None
    if txt and len(txt)>=50:
        m=parse_sdf(txt,title);m.source="PubChem";m.identifier=cid;m.description=props.get("MolecularFormula","");m.metadata.update({"conformer":"PubChem 3D"});return m
    smiles=props.get("IsomericSMILES") or props.get("CanonicalSMILES")
    if not smiles:
        try:
            props=_pubchem_properties(cid);smiles=props.get("IsomericSMILES") or props.get("CanonicalSMILES")
        except Exception:pass
    if smiles:
        m=_rdkit_conformer_from_smiles(smiles,title,cid);m.description=props.get("MolecularFormula","");return m
    # A minority of PubChem records have no useful SMILES/3-D record (notably
    # some salts/coordination records).  A 2-D SDF still contains connectivity,
    # which RDKit can use as the input graph for a local 3-D conformer.
    try:
        block2d=_get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=2d")
        m=_rdkit_conformer_from_molblock(block2d,title,cid);m.description=props.get("MolecularFormula","");return m
    except Exception as exc:
        raise RuntimeError("O PubChem não forneceu um conformador 3D e não foi possível gerar um conformador local a partir deste registro.") from exc


def rcsb(pdb_id,cache:Path):
    pid=pdb_id.strip().upper();cache.mkdir(parents=True,exist_ok=True)
    if not re.fullmatch(r"[A-Z0-9]{4,12}",pid):raise ValueError("Identificador PDB inválido.")
    cif=cache/f"rcsb_{pid}.cif"
    if not cif.exists() or cif.stat().st_size<100:
        txt=_get(f"https://files.rcsb.org/download/{pid}.cif",timeout=90)
        if len(txt)<100:raise RuntimeError("Resposta mmCIF vazia.")
        cif.write_text(txt)
    m=parse_mmcif(cif.read_text(errors="replace"),pid);m.source="RCSB PDB";m.identifier=pid
    try:
        meta=json.loads(_get(f"https://data.rcsb.org/rest/v1/core/entry/{pid}",timeout=20));m.description=(meta.get("struct") or {}).get("title","");m.metadata["experimental_methods"]=[x.get("method") for x in (meta.get("exptl") or []) if x.get("method")]
    except Exception:pass
    return m
