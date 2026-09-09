from __future__ import annotations
import numpy as np
from scipy.optimize import nnls
from .numerics import positive


def multicomponent_beer(absorbance, epsilon_matrix, path_cm=1.0, nonnegative=True):
    """Resolve A(lambda)=b E(lambda,species) c by LS/NNLS."""
    A=np.asarray(absorbance,dtype=float); E=np.asarray(epsilon_matrix,dtype=float); b=positive(path_cm,"Caminho óptico")
    if A.ndim!=1 or E.ndim!=2 or E.shape[0]!=len(A): raise ValueError("A deve ter M pontos e epsilon uma matriz MxN.")
    if np.any(~np.isfinite(A)) or np.any(~np.isfinite(E)): raise ValueError("Dados espectrais não finitos.")
    M=b*E
    if nonnegative:
        c,rnorm=nnls(M,A)
    else:
        c,*_=np.linalg.lstsq(M,A,rcond=None); rnorm=float(np.linalg.norm(M@c-A))
    pred=M@c; resid=A-pred
    return {"concentrations_m":c.tolist(),"predicted":pred.tolist(),"residuals":resid.tolist(),"rmse":float(np.sqrt(np.mean(resid**2))),"rank":int(np.linalg.matrix_rank(M)),"condition_number":float(np.linalg.cond(M))}
