from __future__ import annotations
import math, statistics
from dataclasses import dataclass
from .constants import R_J,R_L_ATM,F,KW_25C
from .chemistry import molar_mass,parse_formula,balance_equation,electron_configuration
from .periodic import ELEMENTS,BY_Z
from .acidbase import (
    hydrogen_strong_acid, hydrogen_strong_base, hydrogen_weak_acid,
    hydrogen_weak_base, buffer_state, titration_state, titration_curve,
    monoprotic_speciation,
)

H=6.62607015e-34; C=299792458.0; E_CHARGE=1.602176634e-19; NA=6.02214076e23

@dataclass
class Result:
    value: str
    details: str
    data: dict | None=None


def fnum(x):
    if isinstance(x,str): return x
    if not math.isfinite(float(x)): return str(x)
    return f'{x:.10g}'

def pos(x,name):
    x=float(x)
    if not math.isfinite(x) or x<=0: raise ValueError(f'{name} deve ser maior que zero e finito.')
    return x

def nonneg(x,name):
    x=float(x)
    if not math.isfinite(x) or x<0: raise ValueError(f'{name} deve ser não negativo e finito.')
    return x

def pct(x,name):
    x=float(x)
    if not 0<=x<=100: raise ValueError(f'{name} deve estar entre 0 e 100%.')
    return x

def num(d,k): return float(d[k])
def text(d,k): return str(d[k]).strip()

def R(title,val,unit,eq,sub,notes=(),data=None):
    body=f'{title}\n\nEquação / modelo\n{eq}\n\nSubstituição / desenvolvimento\n{sub}'
    if notes: body+='\n\nHipóteses e limites\n'+'\n'.join('• '+x for x in notes)
    return Result(f'{fnum(val)} {unit}'.strip(),body,data)

def plot(title,xlabel,ylabel,series,markers=None):
    return {"title":title,"xlabel":xlabel,"ylabel":ylabel,"series":series,"markers":markers or []}


def calc_molar(d):
    formula=text(d,'formula'); c=parse_formula(formula); M=molar_mass(formula)
    rows='; '.join(f'{e}: {n}×{ELEMENTS[e]["mass"]:.8g}' for e,n in c.items())
    return R('Massa molar',M,'g/mol','M = Σ nᵢAᵣ,ᵢ',rows,
             ['Usa valores representativos de massas atômicas padrão da base local; materiais isotopicamente enriquecidos exigem composição isotópica explícita.'],{'composition':c})

def calc_balance(d):
    b,co,L,Rr=balance_equation(text(d,'equation'))
    return Result(b,f'Balanceamento por conservação elementar e álgebra linear racional.\n\n{b}\n\nLimite: esta ferramenta balanceia fórmulas moleculares neutras; reações iônicas/redox devem ser tratadas com carga e elétrons explicitamente.',{'coefficients':co})

def calc_stoich(d):
    eq=text(d,'equation'); b,co,L,Rr=balance_equation(eq); rf=text(d,'reactant'); pf=text(d,'product')
    if rf not in L or pf not in Rr: raise ValueError('Reagente/produto precisam aparecer exatamente na equação.')
    mass=pos(d['reactant_mass_g'],'massa'); nr=mass/molar_mass(rf)
    np_=nr*co[len(L)+Rr.index(pf)]/co[L.index(rf)]; mp=np_*molar_mass(pf); y=pct(d.get('yield_percent',100),'Rendimento')/100
    return R('Produto obtido',mp*y,'g','n = m/M; n_prod = n_reag·ν_prod/ν_reag',
             f'{b}\nn({rf})={mass:.8g}/{molar_mass(rf):.8g}={nr:.8g} mol\nm({pf}) teórica={mp:.8g} g; rendimento={100*y:.5g}%',
             ['O reagente selecionado é tratado como limitante. Para misturas com vários reagentes, compare n/ν antes de usar esta ferramenta.'])

def calc_empirical(d):
    pairs=[]
    for token in text(d,'composition').split(','):
        e,p=token.strip().split(':'); e=e.strip()
        if e not in ELEMENTS: raise ValueError(f'Elemento desconhecido: {e}')
        pairs.append((e,float(p)))
    s=sum(p for _,p in pairs)
    if abs(s-100)>0.5: raise ValueError('As porcentagens devem somar aproximadamente 100%.')
    mol=[(e,p/ELEMENTS[e]['mass']) for e,p in pairs]; mn=min(x for _,x in mol); ratios=[(e,x/mn) for e,x in mol]
    best=None
    for mult in range(1,25):
        ints=[round(r*mult) for _,r in ratios]
        err=max(abs(r*mult-i) for (_,r),i in zip(ratios,ints))
        if err<0.04: best=(mult,ints); break
    if not best: raise ValueError('Não foi possível obter razão inteira simples; verifique as porcentagens/precisão experimental.')
    ints=best[1]; formula=''.join(e+(str(n) if n!=1 else '') for (e,_),n in zip(ratios,ints)); mm=molar_mass(formula)
    exp=text(d,'experimental_molar_mass'); molecular='—'
    if exp:
        ratio=pos(exp,'Massa molar experimental')/mm; k=round(ratio)
        if k<1 or abs(ratio-k)>0.12: raise ValueError('A massa molar experimental não é múltiplo compatível da fórmula empírica.')
        molecular=''.join(e+(str(n*k) if n*k!=1 else '') for (e,_),n in zip(ratios,ints))
    return Result(formula,f'Moles relativos: {ratios}\nFórmula empírica: {formula}\nMassa molar empírica: {mm:.8g} g/mol\nFórmula molecular: {molecular}')

def calc_calor(d):
    m=pos(d['mass_g'],'massa'); cp=pos(d['cp_j_gk'],'calor específico'); ti=num(d,'ti_c'); tf=num(d,'tf_c'); q=m*cp*(tf-ti)
    return R('Calor sensível',q,'J','q = m·cₚ·ΔT',f'q={m:g}×{cp:g}×({tf:g}−{ti:g})',['cₚ assumido constante no intervalo.'])

def calc_reaction(d):
    dh=num(d,'delta_h_kj'); ds=num(d,'delta_s_jk'); T=pos(d['temperature_k'],'temperatura'); dg=dh-T*ds/1000; logk=-dg*1000/(R_J*T*math.log(10))
    tmin=max(100.0,min(298.15,T)*0.70); tmax=max(T*1.35,700.0 if T<700 else T*1.2)
    pts=[]
    for i in range(241):
        tt=tmin+(tmax-tmin)*i/240; pts.append((tt,dh-tt*ds/1000))
    pdata=plot('ΔG no modelo ΔH/ΔS constantes','T / K','ΔG / kJ mol⁻¹',[{'name':'ΔG','points':pts}],markers=[{'x':T,'label':'T avaliada'}])
    return R('ΔG',dg,'kJ/mol','ΔG = ΔH − TΔS; lnK = −ΔG°/RT',f'ΔG={dh:g}−{T:g}×{ds:g}/1000={dg:.8g}; log10K={logk:.8g}',
             ['ΔH e ΔS tratados como constantes com T.', 'K é termodinâmico e adimensional; usar dados padrão coerentes.'],{'log10K':logk,'plot':pdata})

def calc_hess(d):
    vals=[]
    for tok in text(d,'steps').split(';'):
        f,h=tok.split(':'); vals.append((float(f),float(h)))
    total=sum(a*b for a,b in vals)
    return R('ΔH combinado',total,'kJ','ΔH = Σ fᵢΔHᵢ',' + '.join(f'({a:g})({b:g})' for a,b in vals))

def calc_clap(d):
    P1=pos(d['p1'],'P1'); T1=pos(d['t1'],'T1'); T2=pos(d['t2'],'T2'); hv=pos(d['hvap_jmol'],'ΔHvap'); P2=P1*math.exp(-hv/R_J*(1/T2-1/T1))
    lo=max(1.0,min(T1,T2)-35.0); hi=max(T1,T2)+35.0
    pts=[]
    for i in range(241):
        tt=lo+(hi-lo)*i/240; pp=P1*math.exp(-hv/R_J*(1/tt-1/T1)); pts.append((tt,pp))
    pdata=plot('Pressão de vapor no modelo integrado','T / K','P / unidade de P₁',[{'name':'P(T)','points':pts}],markers=[{'x':T1,'label':'T₁'},{'x':T2,'label':'T₂'}])
    return R('P₂',P2,'mesma unidade de P₁','ln(P₂/P₁)=−ΔHvap/R(1/T₂−1/T₁)',f'P₂={P1:g}·exp[−{hv:g}/{R_J:.10g}(1/{T2:g}−1/{T1:g})]',['Vapor ideal e ΔHvap constante.'],{'plot':pdata})

def calc_arrhenius(d):
    k1=pos(d['k1'],'k₁'); t1=pos(d['t1_k'],'T₁'); t2=pos(d['t2_k'],'T₂'); ea=pos(d['ea_kjmol'],'Eₐ')*1000
    k2=k1*math.exp(-ea/R_J*(1/t2-1/t1))
    lo=max(1.0,min(t1,t2)-35); hi=max(t1,t2)+35; pts=[]
    for i in range(241):
        tt=lo+(hi-lo)*i/240; kk=k1*math.exp(-ea/R_J*(1/tt-1/t1)); pts.append((tt,kk))
    pdata=plot('Arrhenius no intervalo','T / K','k / unidade de k₁',[{'name':'k(T)','points':pts}],markers=[{'x':t1,'label':'T₁'},{'x':t2,'label':'T₂'}])
    return R('k₂',k2,'mesma unidade de k₁','ln(k₂/k₁)=−Eₐ/R(1/T₂−1/T₁)',f'k₂={k1:g}·exp[−{ea:g}/{R_J:.10g}(1/{t2:g}−1/{t1:g})]',['Eₐ constante no intervalo; mecanismo não muda.'],{'plot':pdata})

def calc_ideal(d):
    P=text(d,'p_atm'); V=text(d,'v_l'); n=text(d,'n_mol'); T=text(d,'t_k'); vals=[P,V,n,T]
    if sum(x=='' for x in vals)!=1: raise ValueError('Deixe exatamente uma variável vazia.')
    P=float(P) if P else None; V=float(V) if V else None; n=float(n) if n else None; T=float(T) if T else None
    for val,name in ((P,'P'),(V,'V'),(n,'n'),(T,'T')):
        if val is not None and val<=0: raise ValueError(f'{name} deve ser maior que zero.')
    if P is None: val=n*R_L_ATM*T/V; key='P'; unit='atm'
    elif V is None: val=n*R_L_ATM*T/P; key='V'; unit='L'
    elif n is None: val=P*V/(R_L_ATM*T); key='n'; unit='mol'
    else: val=P*V/(n*R_L_ATM); key='T'; unit='K'
    return R(key,val,unit,'PV=nRT',f'R={R_L_ATM:.12g} L·atm·mol⁻¹·K⁻¹',['Modelo de gás ideal; Z=1.'])

def calc_real(d):
    model=text(d,'model').lower(); n=pos(d['n_mol'],'n'); V=pos(d['v_l'],'V'); T=pos(d['t_k'],'T'); a=pos(d['a'],'a'); b=pos(d['b'],'b')
    if V<=n*b: raise ValueError('V deve ser maior que n·b.')
    Rb=0.08314462618
    def eos(v):
        if model.startswith('red'): return n*Rb*T/(v-n*b)-a*n*n/(math.sqrt(T)*v*(v+n*b))
        if model.startswith('van'): return n*Rb*T/(v-n*b)-a*(n/v)**2
        raise ValueError('Modelo real desconhecido.')
    P=eos(V)
    eq='Redlich–Kwong: P=nRT/(V−nb)−a n²/[√T·V(V+nb)]' if model.startswith('red') else 'van der Waals: P=nRT/(V−nb)−a(n/V)²'
    vlo=max(n*b*1.04,V*0.45); vhi=max(V*2.2,vlo*1.2); pts=[]
    for i in range(241):
        vv=vlo+(vhi-vlo)*i/240; pp=eos(vv)
        if math.isfinite(pp): pts.append((vv,pp))
    pdata=plot(f'Isoterma {"Redlich–Kwong" if model.startswith("red") else "van der Waals"}','V / L','P / bar',[{'name':f'T={T:g} K','points':pts}],markers=[{'x':V,'label':'estado'}])
    return R('Pressão',P,'bar',eq,f'n={n:g}, V={V:g} L, T={T:g} K, a={a:g}, b={b:g}',['Use a e b compatíveis com L, bar, mol e K. Não resolve coexistência líquido-vapor; trechos instáveis da isoterma não devem ser interpretados como equilíbrio bifásico.'],{'plot':pdata})

def calc_concentration(d):
    mass=pos(d['solute_mass_g'],'massa de soluto'); mm=pos(d['molar_mass_gmol'],'massa molar'); V=pos(d['volume_l'],'volume'); n=mass/mm; M=n/V; gL=mass/V
    return R('Molaridade',M,'mol/L','n=m/M; C=n/V',f'n={mass:g}/{mm:g}={n:.8g} mol; C={n:.8g}/{V:g}={M:.8g} mol/L',data={'g_L':gL})

def calc_dilution(d):
    c1=pos(d['c1'],'C1'); v1=pos(d['v1_ml'],'V1'); c2=pos(d['c2'],'C2'); v2=c1*v1/c2
    return R('V₂',v2,'mL','C₁V₁=C₂V₂',f'V₂={c1:g}×{v1:g}/{c2:g}',['Volumes aditivos; quantidade de soluto conservada.'])

def calc_collig(d):
    mode=text(d,'mode').lower(); i=pos(d['i'],'fator i'); m=nonneg(d['molality'],'molalidade')
    if mode.startswith('eb'):
        kb=pos(d['kb'],'Kb'); val=i*kb*m; unit='K'; eq='ΔTᵦ=iKᵦm'
    elif mode.startswith('cr') or mode.startswith('fr'):
        kf=pos(d['kf'],'Kf'); val=i*kf*m; unit='K'; eq='ΔT𝒻=iK𝒻m'
    elif mode.startswith('osm'):
        M=nonneg(d['molarity'],'Molaridade'); T=pos(d['temperature_k'],'T'); val=i*M*R_L_ATM*T; unit='atm'; eq='π=iMRT'
    else: raise ValueError('Modo coligativo desconhecido.')
    return R('Resultado coligativo',val,unit,eq,'Modelo de solução ideal diluída.',['i efetivo deve ser informado pelo usuário; associação/dissociação não ideal não é prevista.'])

def calc_kconvert(d):
    K=pos(d['k'],'K'); dn=float(d['delta_n']); T=pos(d['temperature_k'],'T'); direction=text(d,'direction').lower(); factor=(0.08314462618*T)**dn
    forward='kc' in direction and 'kp' in direction and direction.index('kc')<direction.index('kp')
    val=K*factor if forward else K/factor
    return R('Constante convertida',val,'','Kp=Kc(RT·c°/p°)^Δn',f'Com c°=1 mol/L e p°=1 bar, fator numérico=(RT)^Δn={factor:.8g}',
             ['R=0,08314462618 L·bar·mol⁻¹·K⁻¹; relação numérica pressupõe os estados padrão indicados.'])

def calc_ice(d):
    K=pos(d['kc'],'Kc'); A=pos(d['a0'],'[A]0'); B=pos(d['b0'],'[B]0'); C0=nonneg(d['c0'],'[C]0')
    aa=K; bb=-(K*(A+B)+1); cc=K*A*B-C0; disc=bb*bb-4*aa*cc
    if disc<0: raise ValueError('Dados não produzem raiz real.')
    roots=[(-bb+s*math.sqrt(disc))/(2*aa) for s in (-1,1)]; valid=[x for x in roots if -C0<=x<=min(A,B)]
    if not valid: raise ValueError('Não existe raiz física para os dados informados.')
    x=valid[0]
    return R('Extensão x',x,'mol/L','Kc=([C]₀+x)/(([A]₀−x)([B]₀−x))',f'[A]eq={A-x:.8g}; [B]eq={B-x:.8g}; [C]eq={C0+x:.8g}',['Modelo específico A+B⇌C, solução ideal.'])

def calc_ph(d):
    kind=text(d,'kind').lower(); C0=nonneg(d['concentration'],'concentração')
    if 'strong acid' in kind or 'ácido forte' in kind:
        Hc=hydrogen_strong_acid(C0); desc='ácido forte monoprotônico'
    elif 'strong base' in kind or 'base forte' in kind:
        Hc=hydrogen_strong_base(C0); desc='base forte monobásica'
    elif 'weak acid' in kind or 'ácido fraco' in kind:
        Ka=pos(d['ka_kb'],'Ka'); Hc=hydrogen_weak_acid(C0,Ka); desc='ácido fraco monoprotônico'
    elif 'weak base' in kind or 'base fraca' in kind:
        Kb=pos(d['ka_kb'],'Kb'); Hc=hydrogen_weak_base(C0,Kb); desc='base fraca monobásica'
    else: raise ValueError('Tipo ácido/base desconhecido.')
    ph=-math.log10(Hc)
    return R('pH ideal por concentração',ph,'','Balanço de matéria + eletroneutralidade + Kw',f'[H⁺]={Hc:.10g} mol/L; modelo={desc}',
             ['Kw=1,0×10⁻¹⁴ a 25 °C.', 'O valor é pH aproximado por concentração; pH termodinâmico é definido por atividade de H⁺.'])

def calc_buffer(d):
    pka=float(d['pka']); acid=nonneg(d['acid'],'[HA] formal'); base=nonneg(d['base'],'[A⁻] formal')
    if acid+base<=0: raise ValueError('Informe alguma quantidade de tampão.')
    ka=10**(-pka); st=buffer_state(acid,base,ka)
    hh='—' if st['hh_ph'] is None else f'{st["hh_ph"]:.8g}'
    return R('pH ideal por balanço',st['ph'],'','Balanço de matéria + carga + Ka + Kw',
             f'pKa={pka:g}; C(HA)formal={acid:g}; C(A⁻)formal={base:g}\npH exato ideal={st["ph"]:.8g}; Henderson–Hasselbalch={hh}\nβ≈{st["buffer_capacity_m_per_ph"]:.8g} mol·L⁻¹·pH⁻¹',
             ['Mistura ideal HA + sal 1:1; atividades≈concentrações.', 'Henderson–Hasselbalch é mostrado apenas como comparação, não como solucionador principal.'], st)

def calc_titration(d):
    mode_txt=text(d,'mode').lower(); mode='weak-strong' if ('weak' in mode_txt or 'fraco' in mode_txt) else 'strong-strong'
    Ca=pos(d['acid_m'],'Ca'); Va=pos(d['acid_ml'],'Va'); Cb=pos(d['base_m'],'Cb'); Vb=nonneg(d['base_ml'],'Vb'); pka=float(d['pka']); ka=10**(-pka)
    st=titration_state(mode=mode,acid_c=Ca,acid_v_ml=Va,base_c=Cb,base_added_ml=Vb,ka=ka)
    vmax=max(Vb,st['equivalence_ml']*2,Va*2)
    curve=titration_curve(mode=mode,acid_c=Ca,acid_v_ml=Va,base_c=Cb,max_volume_ml=vmax,ka=ka,points=241)
    pdata=plot('Curva de titulação','V base / mL','pH',[{'name':'pH','points':curve}],markers=[{'x':st['equivalence_ml'],'label':'equivalência'}])
    data={**st,'plot':pdata}
    return R('pH',st['ph'],'','Balanço de matéria + eletroneutralidade + Ka/Kw',
             f'nácido={st["acid_moles"]:.8g} mol; nbase={st["base_moles"]:.8g} mol; Vtotal={st["total_volume_l"]:.8g} L\nVeq={st["equivalence_ml"]:.8g} mL; [H⁺]={st["h_m"]:.10g} mol/L',
             ['25 °C, Kw=10⁻¹⁴; soluções ideais; ácido monoprótico e titulante base forte.', 'A curva usa o mesmo solucionador de balanço em todos os pontos, inclusive perto da equivalência.'],data)

def calc_speciation(d):
    pka=float(d['pka']); ph=float(d['ph']); pmin=float(d['ph_min']); pmax=float(d['ph_max'])
    if pmax<=pmin: raise ValueError('pH máximo deve ser maior que pH mínimo.')
    st=monoprotic_speciation(pka,ph); pts_ha=[]; pts_a=[]
    for i in range(241):
        x=pmin+(pmax-pmin)*i/240; s=monoprotic_speciation(pka,x); pts_ha.append((x,s['alpha_ha'])); pts_a.append((x,s['alpha_a']))
    pdata=plot('Distribuição ácido-base','pH','fração',[{'name':'α(HA)','points':pts_ha},{'name':'α(A⁻)','points':pts_a}],markers=[{'x':pka,'label':'pKa'}])
    return R('Fração A⁻',st['alpha_a'],'','αHA=[H⁺]/([H⁺]+Ka); αA⁻=Ka/([H⁺]+Ka)',f'pH={ph:g}; pKa={pka:g}; αHA={st["alpha_ha"]:.8g}; αA⁻={st["alpha_a"]:.8g}',['Ácido monoprótico ideal.'],{'plot':pdata,**st})

def calc_cell(d):
    ec=float(d['e_cathode']); ea=float(d['e_anode']); n=int(d['n_e']);
    if n<=0: raise ValueError('n de elétrons deve ser inteiro positivo.')
    Q=pos(d['q'],'Q'); T=pos(d['temperature_k'],'T'); E0=ec-ea; E=E0-R_J*T/(n*F)*math.log(Q); dg=-n*F*E/1000
    center=math.log10(Q); xs=[center-4+8*i/240 for i in range(241)]; pts=[(x,E0-R_J*T/(n*F)*math.log(10**x)) for x in xs]
    pdata=plot('Nernst','log₁₀ Q','E / V',[{'name':'E(Q)','points':pts}],markers=[{'x':center,'label':'Q informado'}])
    return R('Potencial de equilíbrio da célula',E,'V','E=E°−RT/(nF)lnQ',f'E°={ec:g}−({ea:g})={E0:.8g}; E={E:.8g} V',
             ['Q deve ser adimensional e construído com atividades. Se concentrações forem usadas como aproximação, o resultado é um potencial formal/aproximado.'],{'delta_g_kjmol':dg,'plot':pdata})

def calc_faraday(d):
    I=pos(d['current_a'],'corrente'); t=pos(d['time_s'],'tempo'); z=pos(d['z'],'z'); M=pos(d['molar_mass'],'M'); eff=pct(d['efficiency_percent'],'Eficiência')/100; mol_e=I*t/F; mol=mol_e/z; mass=mol*M*eff
    return R('Massa depositada',mass,'g','m = ItMη/(zF)',f'{I:g}×{t:g}×{M:g}×{eff:g}/({z:g}×{F:.8g})')

def calc_config(d):
    z=int(d['z']); charge=int(d['charge'])
    if z not in BY_Z: raise ValueError('Z deve estar entre 1 e 118.')
    sym,el=BY_Z[z]; cfg=electron_configuration(z,charge)
    return Result(cfg,f'{sym} — {el["name"]}\nZ={z}; carga={charge:+d}; elétrons={z-charge}\nConfiguração calculada: {cfg}\nReferência do átomo neutro: {el["config"]}\n\nPara cátions, elétrons são removidos primeiro do maior número quântico principal (ex.: 4s antes de 3d).')

def calc_photon(d):
    lam=pos(d['wavelength_nm'],'λ')*1e-9; nu=C/lam; E=H*nu; ev=E/E_CHARGE
    return R('Energia do fóton',ev,'eV','E=hν=hc/λ',f'ν={nu:.10g} Hz; E={E:.10g} J = {ev:.10g} eV')

def calc_photoelectric(d):
    lam=pos(d['wavelength_nm'],'λ')*1e-9; phi=pos(d['work_function_ev'],'função trabalho'); Eph=H*C/lam/E_CHARGE
    if Eph<phi:
        return Result('Sem emissão',f'Efóton={Eph:.8g} eV < φ={phi:g} eV. Pelo modelo de Einstein, não há fotoelétrons emitidos; Kmax e potencial de parada não se aplicam.',{'emission':False,'photon_ev':Eph})
    K=Eph-phi; Vs=K
    return R('Energia cinética máxima',K,'eV','Kmax=hν−φ',f'Efóton={Eph:.8g} eV; φ={phi:g} eV; Vparada={Vs:.8g} V',['Modelo de Einstein; despreza distribuição de estados e efeitos de superfície.'],{'emission':True,'stopping_v':Vs})

def calc_bohr(d):
    ni=int(d['n_i']); nf=int(d['n_f']); z=int(d['z'])
    if ni<1 or nf<1 or ni==nf or z<1: raise ValueError('n inicial/final e Z devem ser positivos; nᵢ≠n𝒻.')
    Ei=-13.605693122994*z*z/(ni*ni); Ef=-13.605693122994*z*z/(nf*nf); de=abs(Ef-Ei); lam=H*C/(de*E_CHARGE)*1e9
    return R('Comprimento de onda',lam,'nm','Eₙ=−13,6057 Z²/n²; |ΔE|=hc/λ',f'Ei={Ei:.8g} eV; Ef={Ef:.8g} eV; |ΔE|={de:.8g} eV',['Modelo de Bohr válido para espécies hidrogenoides (um elétron).'])

def calc_beer(d):
    eps=nonneg(d['epsilon'],'ε'); b=pos(d['path_cm'],'b'); c=nonneg(d['concentration'],'c'); A=eps*b*c; T=10**(-A)
    cmax=max(c*2,1/(eps*b) if eps*b>0 else 1.0,1e-6); pts=[(cmax*i/240,eps*b*(cmax*i/240)) for i in range(241)]
    pdata=plot('Beer–Lambert','c / mol L⁻¹','A',[{'name':'A=εbc','points':pts}],markers=[{'x':c,'label':'c informada'}])
    return R('Absorbância',A,'','A=εbc; T=10⁻ᴬ',f'{eps:g}×{b:g}×{c:g}={A:.8g}; transmitância={100*T:.8g}%',
             ['Radiação aproximadamente monocromática; meio homogêneo; sem espalhamento significativo; regime linear.'],{'transmittance':T,'plot':pdata})

def calc_regression(d):
    xs=[]; ys=[]
    for tok in text(d,'points').split(';'):
        x,y=tok.split(','); xs.append(float(x)); ys.append(float(y))
    if len(xs)<2: raise ValueError('Informe pelo menos dois pontos.')
    xm=statistics.mean(xs); ym=statistics.mean(ys); ssx=sum((x-xm)**2 for x in xs)
    if ssx<=0: raise ValueError('Os valores de x não podem ser todos iguais.')
    slope=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/ssx; intercept=ym-slope*xm
    residuals=[y-(slope*x+intercept) for x,y in zip(xs,ys)]; sse=sum(r*r for r in residuals); sst=sum((y-ym)**2 for y in ys); r2=1-sse/sst if sst else 1
    n=len(xs); dof=n-2; syx=math.sqrt(sse/dof) if dof>0 else None
    se_slope=syx/math.sqrt(ssx) if syx is not None else None
    se_intercept=syx*math.sqrt(1/n+xm*xm/ssx) if syx is not None else None
    xlo,xhi=min(xs),max(xs); line=[(xlo,slope*xlo+intercept),(xhi,slope*xhi+intercept)]
    pdata=plot('Calibração linear','x','y',[{'name':'dados','points':list(zip(xs,ys)),'scatter':True},{'name':'ajuste','points':line}])
    sub=f'm={slope:.10g}; b={intercept:.10g}; R²={r2:.10g}; SSE={sse:.10g}'
    if syx is not None: sub+=f'\ns(y|x)={syx:.8g}; SE(m)={se_slope:.8g}; SE(b)={se_intercept:.8g}; gl={dof}'
    return R('Inclinação',slope,'','OLS não ponderado: y=mx+b',sub,['Incertezas de regressão pressupõem resíduos independentes, homocedásticos e modelo linear correto.'],data={'intercept':intercept,'r2':r2,'rmse':syx,'se_slope':se_slope,'se_intercept':se_intercept,'plot':pdata})

def calc_lattice(d):
    typ=text(d,'type').lower(); a=pos(d['a_angstrom'],'a')*1e-8; M=pos(d['molar_mass'],'M');
    if typ not in ('sc','bcc','fcc'): raise ValueError('Rede deve ser sc, bcc ou fcc.')
    N={'sc':1,'bcc':2,'fcc':4}[typ]; rho=N*M/(NA*a**3); coord={'sc':6,'bcc':8,'fcc':12}[typ]
    return R('Densidade cristalina',rho,'g/cm³','ρ=Z·M/(N_A a³)',f'Z={N}; a={a:.8g} cm; coordenação={coord}',['Célula cúbica ideal, ocupação completa e composição estequiométrica.'],data={'coordination':coord})

def calc_bragg(d):
    lam=pos(d['wavelength_nm'],'λ'); theta_deg=float(d['theta_deg']); n=int(d['order'])
    if not 0<theta_deg<90: raise ValueError('θ deve estar entre 0° e 90°.')
    if n<1: raise ValueError('A ordem n deve ser inteira positiva.')
    theta=math.radians(theta_deg); spacing=n*lam/(2*math.sin(theta))
    return R('Espaçamento d',spacing,'nm','nλ=2d sinθ',f'd={n}×{lam:g}/(2 sin {theta_deg:g}°)')

def calc_decay(d):
    N0=nonneg(d['initial'],'N0'); t=nonneg(d['time'],'tempo'); half=pos(d['half_life'],'meia-vida'); N=N0*2**(-t/half)
    duration=max(t,5*half); pts=[(duration*i/240,N0*2**(-(duration*i/240)/half)) for i in range(241)]
    pdata=plot('Decaimento exponencial','tempo / unidade informada','quantidade',[{'name':'N(t)','points':pts}],markers=[{'x':half,'label':'t½'},{'x':t,'label':'t avaliado'}])
    return R('Quantidade restante',N,'','N=N₀·2^(−t/t½)',f'{N0:g}·2^(−{t:g}/{half:g})',['A unidade de tempo deve ser a mesma em t e t½.'],{'plot':pdata})

def calc_nuclear(d):
    A=int(d['a']); Z=int(d['z']); mode=text(d,'mode').lower()
    if A<=0 or Z<0 or Z>A: raise ValueError('Use A>0 e 0≤Z≤A.')
    if 'alpha' in mode or 'alfa' in mode: A2,Z2=A-4,Z-2; emitted='⁴₂He'
    elif 'beta-' in mode or 'β-' in mode: A2,Z2=A,Z+1; emitted='β⁻ + antineutrino (formal)'
    elif 'beta+' in mode or 'β+' in mode: A2,Z2=A,Z-1; emitted='β⁺ + neutrino (formal)'
    elif 'capture' in mode or 'captura' in mode: A2,Z2=A,Z-1; emitted='neutrino (formal)'
    else: A2,Z2=A,Z; emitted='γ'
    if A2<=0 or Z2<0 or Z2>A2: raise ValueError('Transformação gera nuclídeo formal inválido para esses A/Z.')
    sym=BY_Z.get(Z2,('?',{}))[0]; out=f'{A2}{sym}'
    return Result(out,f'Conservação formal de A e Z.\nNuclídeo-filho: A={A2}, Z={Z2} ({sym}); emissão: {emitted}\nNão prevê estabilidade, energia Q, canais concorrentes nem probabilidade de decaimento.')

def calc_ethanol(d):
    feed=pos(d['feed_mass_kg'],'massa de matéria-prima'); sugar=float(d['fermentable_fraction']); eff=pct(d['efficiency'],'Eficiência')/100
    if not 0<=sugar<=1: raise ValueError('Fração fermentável deve estar entre 0 e 1.')
    sugar_mass=feed*sugar; ethanol=sugar_mass*(2*46.06844/180.156)*eff
    return R('Etanol teórico corrigido',ethanol,'kg','C₆H₁₂O₆ → 2 C₂H₅OH + 2 CO₂',f'açúcar fermentável={sugar_mass:.8g} kg; eficiência={eff*100:.5g}%', ['Balanço ideal de glicose equivalente; composição real da biomassa e reações paralelas não são modeladas.'])

def calc_brix(d):
    mass=pos(d['solution_mass_kg'],'massa da solução'); brix=float(d['brix']); target=float(d['target_brix'])
    if not (0<brix<100 and 0<target<100): raise ValueError('Brix inicial e alvo devem estar entre 0 e 100.')
    solids=mass*brix/100; final=solids/(target/100); delta=mass-final
    if delta>=0:
        title='Água a evaporar'; value=delta; op='evaporação'
    else:
        title='Água a adicionar'; value=-delta; op='diluição'
    return R(title,value,'kg','m_sólidos = m·°Bx/100; m_final=m_sólidos/(°Bx_alvo/100)',f'sólidos={solids:.8g} kg; massa final={final:.8g} kg; operação={op}',['°Brix tratado como fração mássica idealizada de sólidos solúveis; matrizes reais podem exigir correção refratométrica.'])

def calc_kinetics(d):
    order=text(d,'order'); c0=pos(d['c0'],'[A]₀'); k=pos(d['k'],'k'); t=nonneg(d['time_s'],'tempo'); duration=pos(d['duration_s'],'duração do gráfico')
    if order=='0':
        c=max(0.0,c0-k*t); half=c0/(2*k); eq='[A]=[A]₀−kt'; kunit='mol·L⁻¹·s⁻¹'
        fn=lambda x:max(0.0,c0-k*x)
    elif order=='1':
        c=c0*math.exp(-k*t); half=math.log(2)/k; eq='[A]=[A]₀e⁻ᵏᵗ'; kunit='s⁻¹'
        fn=lambda x:c0*math.exp(-k*x)
    elif order=='2':
        c=c0/(1+k*c0*t); half=1/(k*c0); eq='1/[A]=1/[A]₀+kt'; kunit='L·mol⁻¹·s⁻¹'
        fn=lambda x:c0/(1+k*c0*x)
    else: raise ValueError('Ordem deve ser 0, 1 ou 2.')
    pts=[(duration*i/240,fn(duration*i/240)) for i in range(241)]
    pdata=plot(f'Cinética de ordem {order}','t / s','[A] / mol L⁻¹',[{'name':'[A]','points':pts}],markers=[{'x':half,'label':'t½'}])
    return R('[A](t)',c,'mol/L',eq,f'ordem={order}; [A]₀={c0:g}; k={k:g} {kunit}; t={t:g} s; t½={half:.8g} s',['Lei integrada de uma única ordem, volume e temperatura constantes; não identifica mecanismo.'],{'half_life_s':half,'plot':pdata})

CALCS={
'molar':calc_molar,'balance':calc_balance,'stoichiometry':calc_stoich,'empirical':calc_empirical,
'calorimetry':calc_calor,'reaction':calc_reaction,'hess':calc_hess,'clapeyron':calc_clap,'arrhenius':calc_arrhenius,
'ideal':calc_ideal,'real':calc_real,'concentration':calc_concentration,'dilution':calc_dilution,'colligative':calc_collig,
'constants':calc_kconvert,'ice':calc_ice,'ph':calc_ph,'buffer':calc_buffer,'titration':calc_titration,'speciation':calc_speciation,
'cell':calc_cell,'faraday':calc_faraday,'configuration':calc_config,'photon':calc_photon,'photoelectric':calc_photoelectric,'bohr':calc_bohr,
'beer':calc_beer,'regression':calc_regression,'lattice':calc_lattice,'bragg':calc_bragg,'decay':calc_decay,'nuclear':calc_nuclear,
'ethanol':calc_ethanol,'brix':calc_brix,'kinetics':calc_kinetics,
}
