from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass
from .numerics import positive, normalize_composition

R_BAR_L = 0.0831446261815324  # L bar mol-1 K-1
SQRT2=math.sqrt(2.0)

@dataclass(frozen=True)
class PREOSResult:
    z: float
    roots: tuple[float,...]
    fugacity_coefficients: tuple[float,...]
    fugacities_bar: tuple[float,...]
    a_mix: float
    b_mix: float
    phase: str


def _kappa(omega):
    # Original Peng–Robinson correlation; adequate through common acentric-factor range.
    w=float(omega)
    return 0.37464 + 1.54226*w - 0.26992*w*w


def pr_pure_parameters(T,Tc,Pc,omega):
    T=positive(T,"T"); Tc=positive(Tc,"Tc"); Pc=positive(Pc,"Pc")
    kap=_kappa(omega); alpha=(1.0+kap*(1.0-math.sqrt(T/Tc)))**2
    a=0.45724*R_BAR_L**2*Tc**2/Pc*alpha
    b=0.07780*R_BAR_L*Tc/Pc
    return a,b,alpha


def _z_roots(A,B):
    coeff=[1.0, -(1.0-B), A-3.0*B*B-2.0*B, -(A*B-B*B-B**3)]
    roots=np.roots(coeff)
    real=sorted(float(r.real) for r in roots if abs(r.imag)<1e-9 and r.real>B+1e-12)
    if not real: raise RuntimeError("Peng–Robinson não produziu raiz física Z>B.")
    return tuple(real)


def peng_robinson_pure(T,P,Tc,Pc,omega,phase="vapor"):
    T=positive(T,"T"); P=positive(P,"P"); a,b,_=pr_pure_parameters(T,Tc,Pc,omega)
    A=a*P/(R_BAR_L**2*T*T); B=b*P/(R_BAR_L*T); roots=_z_roots(A,B)
    z=roots[0] if str(phase).lower().startswith("l") else roots[-1]
    if B<1e-14:
        lnphi=z-1-math.log(z)
    else:
        lnphi=(z-1)-math.log(z-B)-A/(2*SQRT2*B)*math.log((z+(1+SQRT2)*B)/(z+(1-SQRT2)*B))
    phi=math.exp(lnphi)
    return PREOSResult(z,roots,(phi,),(phi*P,),a,b,"liquid" if z==roots[0] and len(roots)>1 else "vapor")


def peng_robinson_mixture(T,P,y,Tc,Pc,omega,kij=None,phase="vapor"):
    """Classical quadratic mixing rules for a gas/liquid mixture.

    Inputs Tc[K], Pc[bar], omega and mole fractions y. kij defaults to zero.
    Returns component fugacity coefficients for the selected PR root.
    """
    T=positive(T,"T"); P=positive(P,"P"); y=normalize_composition(y)
    Tc=np.asarray(Tc,dtype=float); Pc=np.asarray(Pc,dtype=float); om=np.asarray(omega,dtype=float)
    n=len(y)
    if not (len(Tc)==len(Pc)==len(om)==n): raise ValueError("y, Tc, Pc e omega devem ter o mesmo tamanho.")
    pars=[pr_pure_parameters(T,Tc[i],Pc[i],om[i]) for i in range(n)]
    a_components=np.array([p[0] for p in pars]); bi=np.array([p[1] for p in pars])
    K=np.zeros((n,n)) if kij is None else np.asarray(kij,dtype=float)
    if K.shape!=(n,n): raise ValueError("kij deve ser matriz NxN.")
    aij=np.sqrt(a_components[:,None]*a_components[None,:])*(1.0-K)
    am=float(y@aij@y); bm=float(y@bi)
    A=am*P/(R_BAR_L**2*T*T); B=bm*P/(R_BAR_L*T); roots=_z_roots(A,B)
    z=roots[0] if str(phase).lower().startswith("l") else roots[-1]
    logterm=math.log((z+(1+SQRT2)*B)/(z+(1-SQRT2)*B)) if B>1e-14 else 0.0
    lnphis=[]
    for i in range(n):
        first=bi[i]/bm*(z-1)-math.log(z-B)
        if B>1e-14 and am>0:
            second=A/(2*SQRT2*B)*(2*float(aij[i]@y)/am-bi[i]/bm)*logterm
        else: second=0.0
        lnphis.append(first-second)
    phis=np.exp(lnphis)
    fug=phis*y*P
    return PREOSResult(z,roots,tuple(map(float,phis)),tuple(map(float,fug)),am,bm,"liquid" if z==roots[0] and len(roots)>1 else "vapor")


def rachford_rice(z,K):
    z=normalize_composition(z); K=np.asarray(K,dtype=float)
    if K.shape!=z.shape or np.any(~np.isfinite(K)) or np.any(K<=0): raise ValueError("K-values devem ser positivos e ter o mesmo tamanho de z.")
    def f(beta): return float(np.sum(z*(K-1)/(1+beta*(K-1))))
    f0,f1=f(0.0),f(1.0)
    if f0<=0:
        beta=0.0; phase="líquido"
    elif f1>=0:
        beta=1.0; phase="vapor"
    else:
        from scipy.optimize import brentq
        beta=float(brentq(f,0,1,xtol=1e-14,rtol=1e-13)); phase="duas fases"
    x=z/(1+beta*(K-1)); y=K*x
    x=x/x.sum(); y=y/y.sum()
    return {"vapor_fraction":beta,"x":x.tolist(),"y":y.tolist(),"phase":phase,"rr_residual":f(beta)}


def wilson_k_values(T,P,Tc,Pc,omega):
    """Wilson K-value estimate used only to initialize a TP flash."""
    T=positive(T,"T"); P=positive(P,"P")
    Tc=np.asarray(Tc,dtype=float); Pc=np.asarray(Pc,dtype=float); om=np.asarray(omega,dtype=float)
    if not (Tc.ndim==Pc.ndim==om.ndim==1 and len(Tc)==len(Pc)==len(om)):
        raise ValueError("Tc, Pc e omega devem ser vetores do mesmo tamanho.")
    if np.any(Tc<=0) or np.any(Pc<=0) or np.any(~np.isfinite(Tc)) or np.any(~np.isfinite(Pc)) or np.any(~np.isfinite(om)):
        raise ValueError("Parâmetros críticos inválidos.")
    return (Pc/P)*np.exp(5.373*(1.0+om)*(1.0-Tc/T))


def isothermal_flash_pr(T,P,z,Tc,Pc,omega,kij=None,*,max_iter=200,tol=1e-9,damping=0.5):
    """TP flash with Peng–Robinson fugacity coefficients.

    Successive substitution on K_i=phi_i^L/phi_i^V with Rachford–Rice material
    balance. The function reports fugacity equality and material-balance
    residuals. It deliberately does *not* claim full phase-stability analysis.
    """
    T=positive(T,"T"); P=positive(P,"P"); z=normalize_composition(z)
    Tc=np.asarray(Tc,dtype=float); Pc=np.asarray(Pc,dtype=float); om=np.asarray(omega,dtype=float)
    if not (len(Tc)==len(Pc)==len(om)==len(z)):
        raise ValueError("z, Tc, Pc e omega devem ter o mesmo tamanho.")
    max_iter=max(1,int(max_iter)); tol=positive(tol,"tol"); damp=float(damping)
    if not 0<damp<=1: raise ValueError("damping deve estar em (0,1].")
    K=np.clip(wilson_k_values(T,P,Tc,Pc,om),1e-12,1e12)
    beta=0.0; x=z.copy(); y=z.copy(); phase="indeterminado"; residual=math.inf
    phiL=phiV=np.ones_like(z)
    for it in range(1,max_iter+1):
        rr=rachford_rice(z,K); beta=float(rr["vapor_fraction"]); x=np.asarray(rr["x"]); y=np.asarray(rr["y"]); phase=rr["phase"]
        # In an obvious single phase, a two-phase fugacity iteration is not
        # physically meaningful without a stability test. Return that state.
        if phase != "duas fases":
            selected = peng_robinson_mixture(T,P,z,Tc,Pc,om,kij=kij,phase="liquid" if phase=="líquido" else "vapor")
            return {
                "phase":phase,"vapor_fraction":beta,"x":x.tolist(),"y":y.tolist(),
                "z_factor":selected.z,"fugacity_coefficients":list(selected.fugacity_coefficients),
                "iterations":it,"converged":True,"fugacity_residual_norm":None,
                "material_balance_residual_norm":float(np.max(np.abs(z-((1-beta)*x+beta*y)))),
                "message":"Estado monofásico segundo Rachford–Rice/Wilson; nenhum teste de estabilidade de plano tangente foi executado.",
            }
        l=peng_robinson_mixture(T,P,x,Tc,Pc,om,kij=kij,phase="liquid")
        v=peng_robinson_mixture(T,P,y,Tc,Pc,om,kij=kij,phase="vapor")
        phiL=np.asarray(l.fugacity_coefficients); phiV=np.asarray(v.fugacity_coefficients)
        knew=np.clip(phiL/phiV,1e-14,1e14)
        # fL/fV = x phiL / (y phiV); y=Kx
        fres=np.log(np.maximum(x*phiL,1e-300)/np.maximum(y*phiV,1e-300))
        residual=float(np.max(np.abs(fres)))
        if residual<tol:
            mb=float(np.max(np.abs(z-((1-beta)*x+beta*y))))
            return {"phase":"duas fases","vapor_fraction":beta,"x":x.tolist(),"y":y.tolist(),
                    "phi_liquid":phiL.tolist(),"phi_vapor":phiV.tolist(),"iterations":it,"converged":True,
                    "fugacity_residuals":fres.tolist(),"fugacity_residual_norm":residual,
                    "material_balance_residual_norm":mb,"message":"Convergência de igualdade de fugacidades atingida."}
        lnK=(1-damp)*np.log(K)+damp*np.log(knew)
        K=np.exp(np.clip(lnK,-32,32))
    mb=float(np.max(np.abs(z-((1-beta)*x+beta*y))))
    return {"phase":phase,"vapor_fraction":beta,"x":x.tolist(),"y":y.tolist(),"iterations":max_iter,"converged":False,
            "fugacity_residual_norm":residual,"material_balance_residual_norm":mb,
            "message":"Flash PR não convergiu no número máximo de iterações."}
