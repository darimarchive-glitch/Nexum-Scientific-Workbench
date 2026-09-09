from __future__ import annotations
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import null_space
from .numerics import positive, nonnegative


def mass_action_network(initial, stoich, k_forward, *, k_reverse=None, t_end, points=301,
                        method="BDF", rtol=1e-9, atol=1e-12):
    """Integrate a homogeneous constant-volume reaction network.

    stoich is S x R. Negative entries are reactant stoichiometric coefficients.
    Forward rate r_j=kf_j prod_i c_i^(-nu_ij) over reactants; reverse analogous.
    """
    y0=np.asarray(initial,dtype=float); N=np.asarray(stoich,dtype=float); kf=np.asarray(k_forward,dtype=float)
    if y0.ndim!=1 or np.any(y0<0) or np.any(~np.isfinite(y0)): raise ValueError("Concentrações iniciais inválidas.")
    if N.ndim!=2 or N.shape[0]!=len(y0) or N.shape[1]!=len(kf): raise ValueError("Dimensões da rede incompatíveis.")
    if np.any(kf<0) or np.any(~np.isfinite(kf)): raise ValueError("Constantes cinéticas devem ser não negativas e finitas.")
    kr=np.zeros_like(kf) if k_reverse is None else np.asarray(k_reverse,dtype=float)
    if kr.shape!=kf.shape or np.any(kr<0) or np.any(~np.isfinite(kr)): raise ValueError("k_reverse inválido.")
    tend=positive(t_end,"Tempo final"); points=max(2,int(points)); t_eval=np.linspace(0,tend,points)
    react=np.maximum(-N,0); prod=np.maximum(N,0)
    def rhs(t,c):
        cc=np.maximum(c,0.0)
        vf=kf*np.prod(np.power(cc[:,None],react),axis=0)
        vr=kr*np.prod(np.power(cc[:,None],prod),axis=0)
        return N@(vf-vr)
    sol=solve_ivp(rhs,(0,tend),y0,t_eval=t_eval,method=method,rtol=rtol,atol=atol)
    Y=sol.y.T
    min_c=float(np.min(Y))
    # Linear invariants l^T c, where l belongs to null(N^T).
    L=null_space(N.T)
    inv_err=0.0
    if L.size:
        base=L.T@y0
        vals=Y@L
        inv_err=float(np.max(np.abs(vals-base)))
    return {"time":sol.t.tolist(),"concentrations":Y.tolist(),"success":bool(sol.success),"message":sol.message,
            "nfev":int(sol.nfev),"min_concentration":min_c,"linear_invariant_max_error":inv_err,
            "final":Y[-1].tolist()}


def arrhenius_rate_constant(preexponential, activation_energy_j_mol, T):
    from .numerics import positive, nonnegative
    import math
    A=positive(preexponential,"Fator pré-exponencial"); Ea=nonnegative(activation_energy_j_mol,"Ea"); T=positive(T,"T")
    return A*math.exp(-Ea/(8.31446261815324*T))


def arrhenius_network(initial, stoich, preexponential_forward, activation_energy_forward_j_mol,
                       *, preexponential_reverse=None, activation_energy_reverse_j_mol=None,
                       temperature_k, t_end, points=301, method="BDF", rtol=1e-9, atol=1e-12):
    """Mass-action network whose rate constants are calculated from Arrhenius data."""
    T=positive(temperature_k,"T")
    Af=np.asarray(preexponential_forward,dtype=float); Eaf=np.asarray(activation_energy_forward_j_mol,dtype=float)
    if Af.shape!=Eaf.shape: raise ValueError("A e Ea forward devem ter o mesmo tamanho.")
    kf=np.array([arrhenius_rate_constant(a,e,T) for a,e in zip(Af,Eaf)])
    if preexponential_reverse is None:
        kr=None
    else:
        Ar=np.asarray(preexponential_reverse,dtype=float); Ear=np.asarray(activation_energy_reverse_j_mol,dtype=float)
        if Ar.shape!=Ear.shape or Ar.shape!=Af.shape: raise ValueError("Parâmetros reverse incompatíveis.")
        kr=np.array([arrhenius_rate_constant(a,e,T) for a,e in zip(Ar,Ear)])
    out=mass_action_network(initial,stoich,kf,k_reverse=kr,t_end=t_end,points=points,method=method,rtol=rtol,atol=atol)
    out["temperature_k"]=T; out["k_forward"]=kf.tolist(); out["k_reverse"]=None if kr is None else kr.tolist()
    return out
