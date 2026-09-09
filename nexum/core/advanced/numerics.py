from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy.optimize import brentq, least_squares, minimize
from scipy.integrate import solve_ivp

@dataclass(frozen=True)
class SolverDiagnostics:
    converged: bool
    residual_norm: float
    iterations: int | None = None
    message: str = ""


def finite(x, name="valor") -> float:
    x=float(x)
    if not math.isfinite(x):
        raise ValueError(f"{name} deve ser finito.")
    return x


def positive(x, name="valor") -> float:
    x=finite(x,name)
    if x <= 0:
        raise ValueError(f"{name} deve ser maior que zero.")
    return x


def nonnegative(x, name="valor") -> float:
    x=finite(x,name)
    if x < 0:
        raise ValueError(f"{name} não pode ser negativo.")
    return x


def root_log10(func, lo=-16.0, hi=2.0, *, xtol=1e-13, rtol=1e-12):
    """Root solver for positive quantities using x=10**logx.

    This avoids catastrophic conditioning common when [H+] spans many decades.
    """
    def f(logx): return float(func(10.0**logx))
    flo,fhi=f(lo),f(hi)
    if flo == 0: return 10.0**lo, SolverDiagnostics(True,0.0,0,"endpoint")
    if fhi == 0: return 10.0**hi, SolverDiagnostics(True,0.0,0,"endpoint")
    if flo*fhi > 0:
        raise RuntimeError(f"Raiz não delimitada no intervalo log10=[{lo},{hi}] (f={flo:g},{fhi:g}).")
    root, info = brentq(f,lo,hi,xtol=xtol,rtol=rtol,full_output=True,maxiter=300)
    val=10.0**root
    return val, SolverDiagnostics(bool(info.converged),abs(f(root)),int(info.iterations),str(info.flag))


def safe_log(x, floor=1e-300):
    return np.log(np.maximum(np.asarray(x,dtype=float),floor))


def normalize_composition(z):
    a=np.asarray(z,dtype=float)
    if a.ndim != 1 or len(a)==0 or np.any(~np.isfinite(a)) or np.any(a<0):
        raise ValueError("Composição deve conter números não negativos e finitos.")
    s=float(a.sum())
    if s<=0: raise ValueError("A composição deve ter soma positiva.")
    return a/s
