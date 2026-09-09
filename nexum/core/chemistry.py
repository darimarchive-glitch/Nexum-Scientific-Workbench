from __future__ import annotations
import math,re
from fractions import Fraction
from .periodic import ELEMENTS, BY_Z

TOKEN=re.compile(r'([A-Z][a-z]?|\d+|[()\[\]])')
def parse_formula(formula:str):
    formula=formula.strip().replace('·','.'); total={}
    for part in formula.split('.'):
        m=re.match(r'^(\d+)(.*)$',part); mult=int(m.group(1)) if m else 1; body=m.group(2) if m else part
        toks=TOKEN.findall(body); stack=[{}]; i=0
        while i<len(toks):
            t=toks[i]
            if t in '([': stack.append({}); i+=1
            elif t in ')]':
                if len(stack)==1: raise ValueError('Parênteses desbalanceados.')
                group=stack.pop(); i+=1; n=int(toks[i]) if i<len(toks) and toks[i].isdigit() else 1; i+=1 if i<len(toks) and toks[i].isdigit() else 0
                for e,c in group.items(): stack[-1][e]=stack[-1].get(e,0)+c*n
            elif re.match(r'[A-Z]',t):
                if t not in ELEMENTS: raise ValueError(f'Elemento desconhecido: {t}')
                i+=1; n=int(toks[i]) if i<len(toks) and toks[i].isdigit() else 1; i+=1 if i<len(toks) and toks[i].isdigit() else 0
                stack[-1][t]=stack[-1].get(t,0)+n
            elif t.isdigit(): raise ValueError('Índice inesperado na fórmula.')
            else: i+=1
        if len(stack)!=1: raise ValueError('Parênteses desbalanceados.')
        for e,c in stack[0].items(): total[e]=total.get(e,0)+c*mult
    if not total: raise ValueError('Fórmula vazia ou inválida.')
    return total

def molar_mass(formula): return sum(ELEMENTS[e]['mass']*n for e,n in parse_formula(formula).items())

def _rref(mat):
    a=[[Fraction(x) for x in row] for row in mat]; rows=len(a); cols=len(a[0]); piv=[]; r=0
    for c in range(cols):
        p=next((i for i in range(r,rows) if a[i][c]),None)
        if p is None: continue
        a[r],a[p]=a[p],a[r]; q=a[r][c]; a[r]=[x/q for x in a[r]]
        for i in range(rows):
            if i!=r and a[i][c]: q=a[i][c]; a[i]=[x-q*y for x,y in zip(a[i],a[r])]
        piv.append(c); r+=1
        if r==rows: break
    return a,piv

def balance_equation(eq):
    if '->' in eq: left,right=eq.split('->',1)
    elif '=' in eq: left,right=eq.split('=',1)
    else: raise ValueError('Use -> entre reagentes e produtos.')
    L=[x.strip() for x in left.split('+') if x.strip()]; R=[x.strip() for x in right.split('+') if x.strip()]
    comps=[parse_formula(x) for x in L+R]; elems=sorted(set().union(*[set(c) for c in comps])); n=len(comps)
    mat=[]
    for e in elems: mat.append([comps[j].get(e,0)*(1 if j<len(L) else -1) for j in range(n)])
    rr,piv=_rref(mat); free=[c for c in range(n) if c not in piv]
    if not free: raise ValueError('Não foi encontrada solução não trivial.')
    f=free[-1]; x=[Fraction(0) for _ in range(n)]; x[f]=1
    for row,p in reversed(list(zip(rr,piv))): x[p]=-sum(row[j]*x[j] for j in free)
    den=math.lcm(*[v.denominator for v in x]); ints=[int(v*den) for v in x]
    if all(v<=0 for v in ints): ints=[-v for v in ints]
    if any(v<=0 for v in ints): raise ValueError('Equação não balanceável neste formato molecular simples.')
    g=math.gcd(*ints); ints=[v//g for v in ints]
    fmt=lambda c,s: ('' if c==1 else str(c)+' ')+s
    return ' + '.join(fmt(c,s) for c,s in zip(ints[:len(L)],L))+' -> '+' + '.join(fmt(c,s) for c,s in zip(ints[len(L):],R)), ints,L,R

_SUPERSCRIPT_TRANS=str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹','0123456789')
_ORBITAL_ORDER=[('1s',2),('2s',2),('2p',6),('3s',2),('3p',6),('4s',2),('3d',10),('4p',6),('5s',2),('4d',10),('5p',6),('6s',2),('4f',14),('5d',10),('6p',6),('7s',2),('5f',14),('6d',10),('7p',6)]
_NOBLE_Z={'He':2,'Ne':10,'Ar':18,'Kr':36,'Xe':54,'Rn':86}
_L={'s':0,'p':1,'d':2,'f':3}

def _parse_reference_configuration(z:int):
    """Expand the neutral reference configuration stored in periodic.py.

    Using the reference table preserves known neutral-atom exceptions (Cr, Cu, Nb,
    Mo, Pd, Pt, Au, ...).  Ionization is then applied by removing electrons from
    the highest principal shell first, which correctly removes ns before (n-1)d
    for transition-metal cations.
    """
    if z not in BY_Z: raise ValueError('Z deve estar entre 1 e 118.')
    txt=BY_Z[z][1]['config'].replace('(calculada)','').replace('(prevista)','').strip()
    occ={o:0 for o,_ in _ORBITAL_ORDER}
    core=re.search(r'\[([A-Z][a-z]?)\]',txt)
    if core:
        cz=_NOBLE_Z.get(core.group(1))
        if cz is None: raise ValueError('Núcleo eletrônico de referência desconhecido.')
        occ.update(_parse_reference_configuration(cz))
        txt=txt[core.end():]
    # accepts normal digits and Unicode superscripts from the periodic-data table
    normalized=txt.translate(_SUPERSCRIPT_TRANS)
    for n,l,q in re.findall(r'(\d)([spdf])\s*(\d+)',normalized):
        orb=n+l
        if orb in occ: occ[orb]=int(q)
    return occ

def electron_configuration(z:int, charge:int=0):
    z=int(z); charge=int(charge)
    if z not in BY_Z: raise ValueError('Z deve estar entre 1 e 118.')
    target=z-charge
    if target<0: raise ValueError('Carga remove mais elétrons do que o átomo possui.')
    occ=_parse_reference_configuration(z)
    current=sum(occ.values())
    if current!=z:
        # Safety fallback for a future/unknown table entry.
        occ={o:0 for o,_ in _ORBITAL_ORDER}; left=z
        for o,cap in _ORBITAL_ORDER:
            q=min(cap,left); occ[o]=q; left-=q
            if left<=0: break
    if target<z:
        remove=z-target
        # ionization: highest n first; for same n remove higher l first
        candidates=sorted(_ORBITAL_ORDER,key=lambda oc:(int(oc[0][0]),_L[oc[0][1]]),reverse=True)
        for orb,_cap in candidates:
            if remove<=0: break
            q=min(occ.get(orb,0),remove); occ[orb]-=q; remove-=q
    elif target>z:
        add=target-z
        # electron attachment: continue the Madelung/Aufbau sequence from the
        # chemically correct neutral reference occupancy.
        for orb,cap in _ORBITAL_ORDER:
            if add<=0: break
            room=cap-occ.get(orb,0)
            if room>0:
                q=min(room,add); occ[orb]+=q; add-=q
        if add>0: raise ValueError('Configuração além do escopo orbital 7p.')
    return ' '.join(f'{orb}{occ[orb]}' for orb,_ in _ORBITAL_ORDER if occ.get(orb,0)>0)
