from __future__ import annotations
import ast, math
import numpy as np
from dataclasses import dataclass
from statistics import NormalDist
from .numerics import positive

_ALLOWED_FUNCS={k:getattr(math,k) for k in ['sqrt','exp','log','log10','sin','cos','tan','asin','acos','atan','sinh','cosh','tanh']}
_ALLOWED_FUNCS.update({'abs':abs,'pi':math.pi,'e':math.e})

class _ExprValidator(ast.NodeVisitor):
    allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.Constant,ast.Name,ast.Load,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,ast.Mod,ast.USub,ast.UAdd,ast.Call)
    def visit(self,node):
        if not isinstance(node,self.allowed): raise ValueError(f"Elemento não permitido na expressão: {type(node).__name__}")
        return super().visit(node)
    def visit_Call(self,node):
        if not isinstance(node.func,ast.Name) or node.func.id not in _ALLOWED_FUNCS or not callable(_ALLOWED_FUNCS[node.func.id]): raise ValueError("Função não permitida.")
        for a in node.args:self.visit(a)
        if node.keywords: raise ValueError("Argumentos nomeados não são permitidos.")


def compile_expression(expr, variables):
    tree=ast.parse(str(expr),mode='eval'); _ExprValidator().visit(tree); code=compile(tree,'<nexum-expression>','eval')
    vars=set(variables)
    names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
    bad=names-vars-set(_ALLOWED_FUNCS)
    if bad: raise ValueError(f"Variáveis desconhecidas: {', '.join(sorted(bad))}")
    def fn(values):
        env={**_ALLOWED_FUNCS,**{k:float(values[k]) for k in vars}}
        return float(eval(code,{"__builtins__":{}},env))
    return fn


def gum_propagation(expr, values, standard_uncertainties, covariance=None, coverage_factor=2.0):
    names=list(values); x=np.array([float(values[n]) for n in names]); u=np.array([positive(standard_uncertainties[n],f"u({n})") for n in names])
    fn=compile_expression(expr,names); y=fn(dict(zip(names,x)))
    C=np.diag(u*u) if covariance is None else np.asarray(covariance,dtype=float)
    if C.shape!=(len(names),len(names)): raise ValueError("Matriz de covariância incompatível.")
    if np.any(~np.isfinite(C)) or not np.allclose(C,C.T,rtol=1e-10,atol=1e-14):
        raise ValueError("Matriz de covariância deve ser finita e simétrica.")
    if float(np.min(np.linalg.eigvalsh(C))) < -1e-12*max(1.0,float(np.max(np.abs(C)))):
        raise ValueError("Matriz de covariância deve ser semidefinida positiva.")
    grad=[]
    for i in range(len(names)):
        h=max(abs(x[i])*1e-6,u[i]*1e-3,1e-8)
        xp=x.copy(); xm=x.copy(); xp[i]+=h; xm[i]-=h
        grad.append((fn(dict(zip(names,xp)))-fn(dict(zip(names,xm))))/(2*h))
    g=np.asarray(grad); var=float(g@C@g); var=max(var,0.0); uc=math.sqrt(var); k=positive(coverage_factor,"k")
    return {"value":y,"standard_uncertainty":uc,"expanded_uncertainty":k*uc,"coverage_factor":k,"sensitivity":dict(zip(names,g.tolist())),"variance":var}


def monte_carlo_propagation(expr, values, covariance, *, samples=50000, seed=12345, coverage=0.95):
    names=list(values); mean=np.array([float(values[n]) for n in names]); C=np.asarray(covariance,dtype=float)
    if C.shape!=(len(names),len(names)): raise ValueError("Covariância incompatível.")
    if np.any(~np.isfinite(C)) or not np.allclose(C,C.T,rtol=1e-10,atol=1e-14):
        raise ValueError("Covariância deve ser finita e simétrica.")
    if float(np.min(np.linalg.eigvalsh(C))) < -1e-12*max(1.0,float(np.max(np.abs(C)))):
        raise ValueError("Covariância deve ser semidefinida positiva.")
    samples=int(samples)
    if samples<1000 or samples>2_000_000: raise ValueError("samples deve ficar entre 1000 e 2.000.000.")
    fn=compile_expression(expr,names); rng=np.random.default_rng(int(seed)); X=rng.multivariate_normal(mean,C,size=samples)
    Y=np.empty(samples)
    for i,row in enumerate(X): Y[i]=fn(dict(zip(names,row)))
    if np.any(~np.isfinite(Y)): raise ValueError("A expressão produziu resultados não finitos durante Monte Carlo.")
    alpha=(1-float(coverage))/2
    lo,hi=np.quantile(Y,[alpha,1-alpha])
    return {"mean":float(np.mean(Y)),"median":float(np.median(Y)),"standard_uncertainty":float(np.std(Y,ddof=1)),"interval":[float(lo),float(hi)],"coverage":coverage,"samples":samples}


def weighted_linear_regression(x,y,sigma_y):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float); s=np.asarray(sigma_y,dtype=float)
    if not (x.ndim==y.ndim==s.ndim==1 and len(x)==len(y)==len(s) and len(x)>=2): raise ValueError("x, y, sigma devem ter mesmo tamanho >=2.")
    if np.any(s<=0) or np.any(~np.isfinite(x)) or np.any(~np.isfinite(y)) or np.any(~np.isfinite(s)): raise ValueError("Dados inválidos.")
    X=np.column_stack([np.ones_like(x),x]); W=np.diag(1/s**2); normal=X.T@W@X
    cov=np.linalg.inv(normal); beta=cov@(X.T@W@y); pred=X@beta; resid=y-pred; chi2=float(np.sum((resid/s)**2)); dof=len(x)-2
    red=chi2/dof if dof>0 else math.nan
    return {"intercept":float(beta[0]),"slope":float(beta[1]),"covariance":cov.tolist(),"se_intercept":float(math.sqrt(cov[0,0])),"se_slope":float(math.sqrt(cov[1,1])),"chi2":chi2,"dof":dof,"reduced_chi2":red,"residuals":resid.tolist()}
