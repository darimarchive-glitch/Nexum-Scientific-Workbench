"""Traceable XY data analysis. Raw samples are never modified in place."""
import csv
import io
import json
import math
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.optimize import curve_fit

def xy_data(x,y,minimum=3):
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    if x.ndim!=1 or y.shape!=x.shape or not minimum<=len(x)<=100000:
        raise ValueError(f"Informe {minimum}–100.000 pares x,y.")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(np.diff(x)<=0):
        raise ValueError("Dados finitos com x estritamente crescente são necessários.")
    return x,y

def read_csv(text):
    if len(text)>12000000:raise ValueError("CSV excede 12 MB.")
    lines=[l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lines:raise ValueError("Arquivo vazio.")
    delimiter=";" if ";" in lines[0] else "\t" if "\t" in lines[0] else ","
    rows=list(csv.reader(lines,delimiter=delimiter));pairs=[]
    for i,row in enumerate(rows):
        if len(row)<2:raise ValueError(f"Linha {i+1}: duas colunas são necessárias.")
        try:pairs.append([float(v.strip().replace(",",".") if delimiter!="," else v.strip()) for v in row[:2]])
        except ValueError:
            if i==0:continue
            raise ValueError(f"Linha {i+1}: número inválido.")
    if not pairs:raise ValueError("Nenhum dado numérico.")
    a=np.array(pairs);order=np.argsort(a[:,0]);a=a[order]
    x,y=xy_data(a[:,0],a[:,1])
    return x,y

def analyze_spectrum(x,y,baseline="none",prominence=.05,lower=None,upper=None):
    x,y=xy_data(x,y)
    if baseline not in ("none","linear"):raise ValueError("Linha de base desconhecida.")
    prominence=float(prominence)
    if not math.isfinite(prominence) or prominence<0:raise ValueError("Proeminência deve ser não negativa.")
    bg=np.interp(x,[x[0],x[-1]],[y[0],y[-1]]) if baseline=="linear" else np.zeros_like(y)
    corrected=y-bg
    peaks,props=signal.find_peaks(corrected,prominence=prominence)
    lo=x[0] if lower is None else float(lower);hi=x[-1] if upper is None else float(upper)
    if not np.isfinite([lo,hi]).all() or not x[0]<=lo<hi<=x[-1]:
        raise ValueError("Limites de integração devem estar dentro dos dados, com início < fim.")
    mask=(x>lo)&(x<hi);xx=np.r_[lo,x[mask],hi];yy=np.interp(xx,x,corrected)
    area=float(np.sum(np.diff(xx)*(yy[:-1]+yy[1:])/2))
    return {"corrected":corrected,"baseline":bg,"area":area,
            "peaks":[{"x":float(x[i]),"y":float(corrected[i]),"prominence":float(p)} for i,p in zip(peaks,props["prominences"])],
            "method":"Máximos locais; proeminência em unidades de y; integração trapezoidal. Base linear usa os extremos."}

def calibration(x,y,sample):
    x,y=xy_data(x,y,minimum=4);sample=float(sample)
    if not math.isfinite(sample):raise ValueError("Sinal da amostra deve ser finito.")
    design=np.column_stack((x,np.ones(len(x))))
    beta=np.linalg.lstsq(design,y,rcond=None)[0];slope,intercept=beta
    if abs(slope)<1e-12:raise ValueError("Inclinação insuficiente para determinar concentração.")
    fitted=design@beta;res=y-fitted;s2=float(res@res/(len(x)-2))
    covariance=s2*np.linalg.inv(design.T@design)
    estimate=float((sample-intercept)/slope)
    # First-order inverse prediction, one unknown reading, homoscedastic residuals.
    u=math.sqrt(max(0,s2/(slope*slope)*(1+1/len(x)+(estimate-x.mean())**2/np.sum((x-x.mean())**2))))
    return {"slope":float(slope),"intercept":float(intercept),"estimate":estimate,"u":u,
            "slope_u":float(math.sqrt(covariance[0,0])),"fitted":fitted,"residuals":res,
            "extrapolation":not x.min()<=estimate<=x.max(),
            "method":"Mínimos quadrados ordinários; x sem incerteza, resíduos independentes homocedásticos; u padrão (k=1), uma leitura da amostra."}

def kinetic_curve(t,c0,k,order):
    t=np.asarray(t,dtype=float)
    if order==0:return np.maximum(0,c0-k*t)
    if order==1:return c0*np.exp(-k*t)
    if order==2:return c0/(1+k*c0*t)
    raise ValueError("Ordem deve ser 0, 1 ou 2.")

def fit_kinetics(t,c):
    t,c=xy_data(t,c,minimum=5)
    if t[0]<0 or np.any(c<0) or np.max(c)<=0:raise ValueError("Tempo e concentração devem ser não negativos.")
    results=[]
    for order in (0,1,2):
        guess=max(float(c[0]-c[-1]),.001)/(t[-1]-t[0])
        if order==1:guess/=max(c[0],1e-9)
        if order==2:guess/=max(c[0]**2,1e-9)
        fn=lambda tt,c0,k:kinetic_curve(tt,c0,k,order)
        try:
            p,cov=curve_fit(fn,t,c,p0=[max(c[0],1e-9),guess],bounds=(0,np.inf),maxfev=15000)
            fitted=fn(t,*p);res=c-fitted;sse=float(res@res)
            results.append({"order":order,"c0":float(p[0]),"k":float(p[1]),"k_u":float(np.sqrt(cov[1,1])) if np.isfinite(cov[1,1]) else None,
                            "rmse":float(np.sqrt(sse/len(t))),"aic":float(len(t)*np.log(max(sse/len(t),1e-300))+4),
                            "fitted":fitted,"residuals":res})
        except (RuntimeError,ValueError):continue
    if not results:raise ValueError("Nenhum ajuste convergiu.")
    return sorted(results,key=lambda r:r["aic"])

def simulate_calibration(slope=100,intercept=0,noise=.005,seed=42):
    if not np.isfinite([slope,intercept,noise]).all() or noise<0:raise ValueError("Parâmetros inválidos.")
    x=np.linspace(0,.01,11)
    y=intercept+slope*x+np.random.default_rng(int(seed)).normal(0,noise,len(x))
    return x,y

def simulate_kinetics(c0=1,k=.1,order=1,duration=50,noise=.01,seed=42):
    if not np.isfinite([c0,k,duration,noise]).all() or c0<=0 or k<0 or duration<=0 or noise<0:
        raise ValueError("c₀ e duração positivos; k e ruído não negativos.")
    t=np.linspace(0,duration,101)
    # Do not clip noisy measurements: negative readings can expose detection limits.
    y=kinetic_curve(t,c0,k,order)+np.random.default_rng(int(seed)).normal(0,noise,len(t))
    return t,y

def polyprotic_titration(pkas=(2.15,7.2,12.35),acid_c=.1,acid_ml=25,base_c=.1,max_ml=100):
    from scipy.optimize import brentq
    pkas=np.asarray(pkas,dtype=float)
    if not 1<=len(pkas)<=3 or not np.isfinite(pkas).all() or np.any(np.diff(pkas)<=0):
        raise ValueError("Informe 1–3 pKa finitos e crescentes.")
    if not np.isfinite([acid_c,acid_ml,base_c,max_ml]).all() or min(acid_c,acid_ml,base_c,max_ml)<=0:
        raise ValueError("Concentrações e volumes devem ser positivos.")
    volumes=np.linspace(0,max_ml,201);ph=[]
    logs=np.r_[0,-np.cumsum(pkas)]
    for v in volumes:
        ct=acid_c*acid_ml/(acid_ml+v);sodium=base_c*v/(acid_ml+v)
        def charge(pH):
            terms=logs+np.arange(len(logs))*pH
            weights=10**(terms-terms.max());weights/=weights.sum()
            return 10**(-pH)+sodium-10**(pH-14)-ct*np.dot(np.arange(len(logs)),weights)
        ph.append(brentq(charge,-4,20))
    return volumes,np.array(ph)

def isotope_pattern(formula,charge=1):
    from rdkit import Chem
    from .chemistry import parse_formula
    counts=parse_formula(formula)
    raw_charge=float(charge)
    if not math.isfinite(raw_charge) or not raw_charge.is_integer():raise ValueError('Carga deve ser inteira e finita.')
    charge=int(raw_charge)
    if charge==0 or abs(charge)>10:raise ValueError("Carga entre −10 e +10, diferente de zero.")
    if sum(counts.values())>150:raise ValueError("Padrão limitado a 150 átomos.")
    pt=Chem.GetPeriodicTable();distribution={0.:1.}
    for element,count in counts.items():
        z=pt.GetAtomicNumber(element)
        isotopes=[(pt.GetMassForIsotope(z,a),pt.GetAbundanceForIsotope(z,a)/100) for a in range(1,295)]
        isotopes=[(m,p) for m,p in isotopes if p>0]
        if not isotopes:raise ValueError(f"Sem abundâncias naturais para {element}.")
        for _ in range(int(count)):
            nxt={}
            for mass,p in distribution.items():
                for m,q in isotopes:
                    prob=p*q
                    if prob>=1e-10:
                        key=round(mass+m,6);nxt[key]=nxt.get(key,0)+prob
            distribution=dict(sorted(nxt.items(),key=lambda v:v[1],reverse=True)[:2048])
    peak=max(distribution.values())
    return [[(m-charge*.000548579909)/abs(charge),p/peak*100] for m,p in sorted(distribution.items()) if p/peak>=.0001]

def json_safe(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)

def write_session(path,payload):
    text=json.dumps({"format":"nexum-session","version":1,"payload":payload},ensure_ascii=False,allow_nan=False,default=json_safe)
    if len(text.encode("utf-8"))>100000000:raise ValueError("Sessão excede 100 MB.")
    path=Path(path);temp=path.with_name(path.name+".tmp")
    temp.write_text(text,encoding="utf-8");temp.replace(path)

def read_session(path):
    path=Path(path)
    if path.stat().st_size>100000000:raise ValueError("Sessão excede 100 MB.")
    obj=json.loads(path.read_text(encoding="utf-8"),parse_constant=lambda _:(_ for _ in ()).throw(ValueError("Número não finito.")))
    if obj.get("format")!="nexum-session" or obj.get("version")!=1 or not isinstance(obj.get("payload"),dict):
        raise ValueError("Formato/versão da sessão não suportado.")
    return obj["payload"]

