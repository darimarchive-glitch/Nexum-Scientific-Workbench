from __future__ import annotations
from dataclasses import dataclass
import math
from .numerics import positive

R=8.31446261815324

@dataclass(frozen=True)
class ShomateCoefficients:
    A: float; B: float; C: float; D: float; E: float; F: float; G: float; H: float
    tmin: float = 0.0; tmax: float = float('inf')


def shomate(T, coeff:ShomateCoefficients):
    """NIST Shomate convention: Cp J/mol/K, H increment kJ/mol, S J/mol/K."""
    T=positive(T,"T")
    if not coeff.tmin <= T <= coeff.tmax:
        raise ValueError(f"T={T:g} K fora da faixa dos coeficientes ({coeff.tmin:g}–{coeff.tmax:g} K).")
    t=T/1000.0; A,B,C,D,E,Fc,G,H=(coeff.A,coeff.B,coeff.C,coeff.D,coeff.E,coeff.F,coeff.G,coeff.H)
    cp=A+B*t+C*t*t+D*t**3+E/t**2
    hinc=A*t+B*t*t/2+C*t**3/3+D*t**4/4-E/t+Fc-H
    s=A*math.log(t)+B*t+C*t*t/2+D*t**3/3-E/(2*t*t)+G
    return {"cp_j_mol_k":cp,"h_minus_h298_kj_mol":hinc,"s_j_mol_k":s,"h_f298_kj_mol":H,"h_kj_mol":H+hinc}


def reaction_thermodynamics(T, stoich, species_props):
    """Reaction functions from stoichiometric coefficients ν (products positive)."""
    if set(stoich)!=set(species_props): raise ValueError("stoich e species_props devem conter as mesmas espécies.")
    dh=sum(stoich[k]*species_props[k]["h_kj_mol"] for k in stoich)
    ds=sum(stoich[k]*species_props[k]["s_j_mol_k"] for k in stoich)
    dg=dh-T*ds/1000.0
    lnk=-dg*1000/(R*T)
    return {"delta_h_kj_mol":dh,"delta_s_j_mol_k":ds,"delta_g_kj_mol":dg,"lnK":lnk,"log10K":lnk/math.log(10)}
