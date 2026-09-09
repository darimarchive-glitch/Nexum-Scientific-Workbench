from __future__ import annotations
import math
import numpy as np
from .numerics import nonnegative

# Water, 25 °C. These are conventional dilute-solution constants for molal scale.
A_DH_25C = 0.5085
B_DH_25C_ANGSTROM = 0.3281


def ionic_strength(concentrations, charges):
    """I = 1/2 sum(c_i z_i²), on the same concentration/molality basis as input."""
    c=np.asarray(concentrations,dtype=float); z=np.asarray(charges,dtype=float)
    if c.shape != z.shape or c.ndim != 1: raise ValueError("concentrações e cargas devem ter o mesmo tamanho.")
    if np.any(~np.isfinite(c)) or np.any(c<0) or np.any(~np.isfinite(z)): raise ValueError("Dados iônicos inválidos.")
    return float(0.5*np.sum(c*z*z))


def debye_huckel_limiting_gamma(z, I, A=A_DH_25C):
    I=nonnegative(I,"Força iônica")
    return max(1e-300, 10.0**(-float(A)*float(z)**2*math.sqrt(I)))


def extended_debye_huckel_gamma(z, I, ion_size_angstrom, A=A_DH_25C, B=B_DH_25C_ANGSTROM):
    I=nonnegative(I,"Força iônica"); a=float(ion_size_angstrom)
    if a<=0: raise ValueError("Parâmetro de tamanho iônico deve ser positivo.")
    sq=math.sqrt(I)
    return max(1e-300, 10.0**(-float(A)*float(z)**2*sq/(1.0+float(B)*a*sq)))


def davies_gamma(z, I, A=A_DH_25C):
    """Davies activity coefficient at 25 °C.

    Commonly used as an engineering approximation up to roughly I~0.5 molal;
    it is not a replacement for SIT/Pitzer at high ionic strength.
    """
    I=nonnegative(I,"Força iônica"); sq=math.sqrt(I)
    exponent=-float(A)*float(z)**2*(sq/(1.0+sq)-0.3*I)
    return max(1e-300, min(1e300, 10.0**max(-300.0,min(300.0,exponent))))


def activity_coefficients(charges, I, model="davies", ion_sizes_angstrom=None):
    model=str(model).strip().lower()
    if model in {"ideal","none","1"}: return [1.0 for _ in charges]
    if model in {"davies","davie"}: return [davies_gamma(z,I) for z in charges]
    if model in {"debye-huckel","debye","limiting"}: return [debye_huckel_limiting_gamma(z,I) for z in charges]
    if model in {"extended","extended-debye-huckel"}:
        if ion_sizes_angstrom is None or len(ion_sizes_angstrom)!=len(charges):
            raise ValueError("Debye–Hückel estendido requer um tamanho iônico para cada espécie.")
        return [extended_debye_huckel_gamma(z,I,a) for z,a in zip(charges,ion_sizes_angstrom)]
    raise ValueError(f"Modelo de atividade desconhecido: {model}")


def model_validity(model, I):
    model=str(model).lower(); I=float(I)
    if model.startswith("ideal"): return "Ideal: coeficientes de atividade fixados em 1; adequado apenas quando a não idealidade é desprezível."
    if "davies" in model:
        return "Davies: aproximação de solução aquosa diluída/moderada; trate I > 0,5 como fora da faixa recomendada." if I<=0.5 else "ATENÇÃO: I > 0,5; Davies está fora da faixa recomendada. Use SIT/Pitzer/dados experimentais."
    if "extended" in model: return "Debye–Hückel estendido: solução diluída; exige parâmetros de tamanho iônico apropriados."
    return "Debye–Hückel limite: use apenas em força iônica muito baixa."
