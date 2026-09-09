from __future__ import annotations
import math
from .numerics import positive, nonnegative, finite

R=8.31446261815324; F=96485.33212


def butler_volmer(overpotential_v, exchange_current_density_a_m2, n, T=298.15, alpha_a=0.5, alpha_c=0.5):
    eta=finite(overpotential_v,"Sobrepotencial"); j0=positive(exchange_current_density_a_m2,"j0"); n=positive(n,"n"); T=positive(T,"T")
    aa=positive(alpha_a,"alpha_a"); ac=positive(alpha_c,"alpha_c")
    x=n*F*eta/(R*T)
    # prevent overflow but retain physically clear diagnostic
    if abs(x)*max(aa,ac)>700: raise OverflowError("Sobrepotencial fora da faixa numérica do modelo exponencial.")
    anod=j0*math.exp(aa*x); cath=j0*math.exp(-ac*x); j=anod-cath
    return {"current_density_a_m2":j,"anodic_a_m2":anod,"cathodic_magnitude_a_m2":cath,
            "tafel_anodic_a_m2":j0*math.exp(aa*x),"tafel_cathodic_a_m2":-j0*math.exp(-ac*x)}


def cottrell_current(n, area_m2, concentration_mol_m3, diffusion_m2_s, time_s):
    n=positive(n,"n"); A=positive(area_m2,"Área"); c=nonnegative(concentration_mol_m3,"Concentração"); D=positive(diffusion_m2_s,"Difusão"); t=positive(time_s,"Tempo")
    i=n*F*A*c*math.sqrt(D)/(math.sqrt(math.pi*t))
    return {"current_a":i,"current_density_a_m2":i/A}


def tafel_slope(T=298.15,n=1,alpha=0.5):
    T=positive(T,"T"); n=positive(n,"n"); alpha=positive(alpha,"alpha")
    return 2.303*R*T/(alpha*n*F)  # V per decade


def invert_butler_volmer(current_density_a_m2, exchange_current_density_a_m2, n, T=298.15, alpha_a=0.5, alpha_c=0.5):
    """Solve Butler–Volmer for overpotential at a requested current density."""
    from scipy.optimize import brentq
    target=finite(current_density_a_m2,"Densidade de corrente")
    j0=positive(exchange_current_density_a_m2,"j0"); n=positive(n,"n"); T=positive(T,"T")
    aa=positive(alpha_a,"alpha_a"); ac=positive(alpha_c,"alpha_c")
    if target==0: return {"overpotential_v":0.0,"iterations":0,"residual_a_m2":0.0,"converged":True}
    def f(eta): return butler_volmer(eta,j0,n,T,aa,ac)["current_density_a_m2"]-target
    lo,hi=-0.05,0.05
    for _ in range(60):
        try: flo,fhi=f(lo),f(hi)
        except OverflowError:
            break
        if flo<=0<=fhi: break
        lo*=1.5; hi*=1.5
    else:
        raise RuntimeError("Não foi possível delimitar o sobrepotencial Butler–Volmer.")
    root,info=brentq(f,lo,hi,xtol=1e-13,rtol=1e-12,maxiter=300,full_output=True)
    return {"overpotential_v":float(root),"iterations":int(info.iterations),"residual_a_m2":float(f(root)),"converged":bool(info.converged)}


def polarized_electrode(equilibrium_potential_v, current_density_a_m2, exchange_current_density_a_m2, n,
                         *, electrode_area_m2=1.0, series_resistance_ohm=0.0, T=298.15,
                         alpha_a=0.5, alpha_c=0.5):
    """Lumped electrode polarization = reversible E + kinetic eta + iR.

    Positive current is anodic by convention. This does not include mass
    transport; combine with a transport model rather than hiding it in j0.
    """
    Eeq=finite(equilibrium_potential_v,"Eeq"); j=finite(current_density_a_m2,"j")
    area=positive(electrode_area_m2,"Área"); Rs=nonnegative(series_resistance_ohm,"Resistência")
    inv=invert_butler_volmer(j,exchange_current_density_a_m2,n,T,alpha_a,alpha_c)
    current=j*area; ohmic=current*Rs; applied=Eeq+inv["overpotential_v"]+ohmic
    return {"equilibrium_potential_v":Eeq,"overpotential_v":inv["overpotential_v"],"current_a":current,
            "ohmic_drop_v":ohmic,"applied_potential_v":applied,"converged":inv["converged"],
            "iterations":inv["iterations"],"residual_a_m2":inv["residual_a_m2"]}
