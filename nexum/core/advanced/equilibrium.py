from __future__ import annotations
import math
import numpy as np
from scipy.optimize import minimize
from .activities import ionic_strength, activity_coefficients, model_validity
from .numerics import positive, nonnegative, root_log10, normalize_composition

KW25=1e-14


def polyprotic_fractions(h_conc, kas, gammas=None):
    """Distribution fractions for neutral H_nA -> ... -> A^n-.

    Computed in log space so extreme pH/activity coefficients do not overflow.
    gammas order: [gamma_H, gamma_HnA, gamma_H(n-1)A-, ..., gamma_An-].
    Ka values are thermodynamic; concentrations are relative to the declared
    standard concentration/molality scale.
    """
    h=positive(h_conc,"[H+]"); kas=[positive(k,"Ka") for k in kas]; n=len(kas)
    if gammas is None: gammas=[1.0]*(n+2)
    if len(gammas)!=n+2: raise ValueError("gammas incompatível com número de dissociações.")
    gs=[max(float(g),1e-300) for g in gammas]
    gh=gs[0]; logw=[0.0]
    for j,k in enumerate(kas,1):
        logratio=math.log(k)+math.log(gs[j])-math.log(gh)-math.log(gs[j+1])-math.log(h)
        logw.append(logw[-1]+logratio)
    m=max(logw); w=[math.exp(max(-745.0,min(700.0,x-m))) for x in logw]; den=sum(w)
    return [x/den for x in w]


def solve_polyprotic_acid(total_m, kas, *, spectator_cation_m=0.0, spectator_anion_m=0.0,
                           activity_model="ideal", kw=KW25, max_outer=80):
    """General neutral polyprotic acid in water with strong spectator ions.

    Solves charge balance in log[H+] space and, for Davies/Debye-Huckel,
    self-consistently updates ionic strength and activity coefficients.
    """
    ct=nonnegative(total_m,"Concentração analítica"); cat=nonnegative(spectator_cation_m,"Cátion espectador"); an=nonnegative(spectator_anion_m,"Ânion espectador")
    kas=[positive(k,"Ka") for k in kas]; kw=positive(kw,"Kw"); n=len(kas)
    if n<1: raise ValueError("Informe ao menos um Ka.")

    def state_for_h(h):
        # At fixed [H+], solve the self-consistent ionic strength rather than
        # relying on a fragile fixed-point iteration. This matters especially
        # at the very acidic/basic bracket endpoints used by the pH root.
        charges=[1]+[0]+[-j for j in range(1,n+1)]+[-1]  # H, HnA...A^n-, OH

        def evaluate(I):
            g=activity_coefficients(charges,I,activity_model)
            gh=g[0]; species_g=g[1:n+2]; goh=g[-1]
            fr=polyprotic_fractions(h,kas,[gh]+species_g)
            species=[ct*a for a in fr]
            logoh=math.log(kw)-math.log(max(gh,1e-300))-math.log(max(goh,1e-300))-math.log(h)
            oh=math.exp(max(-745.0,min(700.0,logoh)))
            conc=[h]+species+[oh,cat,an]
            zz=[1]+[0]+[-j for j in range(1,n+1)]+[-1,1,-1]
            Icalc=ionic_strength(conc,zz)
            return Icalc,g,fr,species,oh

        if str(activity_model).strip().lower() in {"ideal","none","1"}:
            I0=max(0.0,0.5*(cat+an+h+kw/h))
            Icalc,g,fr,species,oh=evaluate(I0)
            return h,oh,species,Icalc,g,fr

        from scipy.optimize import brentq
        # Conservative upper bound: spectator ions + water ions + fully
        # deprotonated acid carrying charge n. Activity models may be outside
        # their validity at the bracket edges; this is only a numerical bound.
        upper=max(1.0, 2.0*(0.5*(cat+an+h+kw/h+ct*n*n)+1.0))
        def gi(I):
            return evaluate(I)[0]-I
        lo=0.0; flo=gi(lo); fhi=gi(upper)
        grow=0
        while fhi>0 and grow<30:
            upper*=2.0; fhi=gi(upper); grow+=1
        if flo==0:
            I=lo
        elif flo*fhi>0:
            raise RuntimeError("Não foi possível delimitar a força iônica auto-consistente.")
        else:
            I=float(brentq(gi,lo,upper,xtol=1e-13,rtol=1e-12,maxiter=300))
        Icalc,g,fr,species,oh=evaluate(I)
        return h,oh,species,Icalc,g,fr

    def charge(h):
        h,oh,species,I,g,fr=state_for_h(h)
        acid_charge=sum(j*species[j] for j in range(1,n+1))
        return h+cat-oh-an-acid_charge

    if str(activity_model).strip().lower() in {"ideal","none","1"}:
        h,diag=root_log10(charge,-16,1)
    else:
        # Non-ideal models can be mathematically nonsensical at the extreme
        # bracket endpoints (where their own validity is already violated).
        # Scan log[H+] and bracket the physical charge-balance root only over
        # points where the activity model itself evaluates successfully.
        from scipy.optimize import brentq
        grid=np.linspace(-14.0,1.0,301)
        vals=[]
        for lg in grid:
            try: vals.append((lg,float(charge(10.0**lg))))
            except Exception: vals.append((lg,None))
        bracket=None
        for (a,fa),(b,fb) in zip(vals[:-1],vals[1:]):
            if fa is None or fb is None: continue
            if fa==0: bracket=(a,a); break
            if fa*fb<0: bracket=(a,b); break
        if bracket is None:
            raise RuntimeError("Não foi possível delimitar a raiz de eletroneutralidade dentro da faixa numericamente válida do modelo de atividade.")
        if bracket[0]==bracket[1]:
            root=bracket[0]; iters=0
        else:
            root,info=brentq(lambda lg:charge(10.0**lg),bracket[0],bracket[1],xtol=1e-13,rtol=1e-12,maxiter=300,full_output=True)
            iters=int(info.iterations)
        h=10.0**root
        from .numerics import SolverDiagnostics
        diag=SolverDiagnostics(True,abs(charge(h)),iters,"converged")
    h,oh,species,I,g,fr=state_for_h(h)
    gh=g[0]
    aH=gh*h
    return {"h_m":h,"oh_m":oh,"pH_activity":-math.log10(aH),"pH_concentration":-math.log10(h),
            "species_m":species,"alpha":fr,"ionic_strength":I,"gamma_h":gh,"activity_model":activity_model,
            "charge_residual":charge(h),"solver":diag,"validity":model_validity(activity_model,I)}


def ideal_reaction_equilibrium(initial, stoich, logK, *, phase="solution", pressure_bar=1.0, standard_conc=1.0):
    """Multireaction ideal equilibrium by constrained Gibbs minimization.

    initial: length S mole amounts (or concentrations at fixed V)
    stoich: R x S matrix, reactants negative / products positive
    logK: natural logarithm equilibrium constants, length R

    For phase='solution', a_i ~ n_i/standard_conc at fixed reference volume.
    For phase='gas', a_i = y_i P/P°.
    """
    n0=np.asarray(initial,dtype=float); nu=np.asarray(stoich,dtype=float); lk=np.asarray(logK,dtype=float)
    if n0.ndim!=1 or np.any(n0<0) or np.any(~np.isfinite(n0)): raise ValueError("Quantidades iniciais inválidas.")
    if nu.ndim!=2 or nu.shape[1]!=len(n0) or len(lk)!=nu.shape[0]: raise ValueError("Dimensões de estequiometria/logK incompatíveis.")
    if np.any(~np.isfinite(nu)) or np.any(~np.isfinite(lk)): raise ValueError("Dados de equilíbrio não finitos.")
    Rn,S=nu.shape
    # Find one set of dimensionless standard chemical potentials satisfying nu @ mu0 = -lnK.
    mu0=np.linalg.lstsq(nu,-lk,rcond=None)[0]
    eps=1e-14
    def n_of(x): return n0+nu.T@x
    def activities(n):
        if phase.lower().startswith("g"):
            nt=float(n.sum()); y=n/nt; return np.maximum(y*positive(pressure_bar,"P"),eps)
        return np.maximum(n/positive(standard_conc,"c°"),eps)
    def objective(x):
        n=n_of(x)
        if np.any(n<=0):
            return 1e100+1e80*float(np.sum(np.minimum(n,0)**2))
        a=activities(n)
        if phase.lower().startswith("g"):
            return float(np.sum(n*(mu0+np.log(a))))
        return float(np.sum(n*(mu0+np.log(a)-1.0)))

    def objective_jac(x):
        # Exact derivative dG/dxi = ΔrG/RT = lnQ-lnK. Providing the
        # analytical gradient avoids finite-difference steps crossing the
        # non-negativity boundary and falsely converging there.
        n=n_of(x); a=activities(n)
        return np.asarray(nu@np.log(a)-lk,dtype=float)

    cons={"type":"ineq","fun":lambda x:n_of(x)-eps,
          "jac":lambda x:nu.T}
    res=minimize(objective,np.zeros(Rn),jac=objective_jac,method="SLSQP",constraints=[cons],
                 options={"ftol":1e-13,"maxiter":2000,"disp":False})

    # Newton refinement of the reaction affinities. For an ideal fixed-volume
    # solution, J = nu diag(1/n) nu^T. For an ideal gas the mole-fraction term
    # adds -dnu dnu^T / nt. A feasibility-preserving line search prevents a
    # Newton step from creating negative species amounts.
    x=np.asarray(res.x,dtype=float).copy(); nit_refine=0
    for nit_refine in range(1,61):
        n=n_of(x); a=activities(n); affin=np.asarray(nu@np.log(a)-lk,dtype=float)
        r0=float(np.linalg.norm(affin,ord=np.inf))
        if r0 < 1e-11: break
        J=nu@np.diag(1.0/np.maximum(n,eps))@nu.T
        if phase.lower().startswith("g"):
            dnu=np.sum(nu,axis=1); J=J-np.outer(dnu,dnu)/float(np.sum(n))
        try: dx=np.linalg.solve(J,-affin)
        except np.linalg.LinAlgError: dx=np.linalg.lstsq(J,-affin,rcond=None)[0]
        dn=nu.T@dx
        lam=1.0
        bad=dn<0
        if np.any(bad):
            lam=min(lam,0.95*float(np.min((n[bad]-eps)/(-dn[bad]))))
        lam=max(min(lam,1.0),1e-12)
        accepted=False
        for _ in range(50):
            xn=x+lam*dx; nn=n_of(xn)
            if np.all(nn>eps):
                aa=activities(nn); rr=np.asarray(nu@np.log(aa)-lk,dtype=float)
                if float(np.linalg.norm(rr,ord=np.inf)) < r0:
                    x=xn; accepted=True; break
            lam*=0.5
        if not accepted: break

    n=n_of(x); a=activities(n); affin=np.asarray(nu@np.log(a)-lk,dtype=float)
    rnorm=float(np.linalg.norm(affin,ord=np.inf))
    return {"amounts":n.tolist(),"extents":x.tolist(),"activities":a.tolist(),"affinity_residuals":affin.tolist(),
            "residual_norm":rnorm,"iterations":int(getattr(res,"nit",0))+nit_refine,
            "converged":bool(np.all(n>=-1e-10) and rnorm<1e-9),
            "message":str(res.message)+("; Newton affinity refinement" if nit_refine else "")}


def formation_speciation_ideal(component_totals, formation_stoich, log_beta, *, log_base=10.0,
                                initial_free=None, rtol=1e-10, max_nfev=5000):
    """General ideal complexation/speciation from component balances.

    Parameters
    ----------
    component_totals : C-vector
        Analytical totals b_j (>0) for independent components.
    formation_stoich : SxC matrix
        Number of each component in formed species. Free components are
        represented implicitly and therefore are not rows of this matrix.
    log_beta : S-vector
        Overall formation constants for each formed species. `log_base=10`
        means log10(beta); use math.e for natural logs.

    The unknowns are log free-component concentrations. This guarantees
    positivity and the solver minimizes *scaled* component mass-balance
    residuals. No result is preselected; every species amount follows from the
    submitted totals and constants.
    """
    from scipy.optimize import least_squares
    b=np.asarray(component_totals,dtype=float)
    A=np.asarray(formation_stoich,dtype=float)
    lb=np.asarray(log_beta,dtype=float)
    if b.ndim!=1 or len(b)==0 or np.any(~np.isfinite(b)) or np.any(b<=0):
        raise ValueError("Totais de componentes devem ser positivos e finitos.")
    if A.ndim!=2 or A.shape[1]!=len(b) or A.shape[0]!=len(lb):
        raise ValueError("formation_stoich deve ser SxC e log_beta deve ter S elementos.")
    if np.any(~np.isfinite(A)) or np.any(A<0) or np.any(~np.isfinite(lb)):
        raise ValueError("Estequiometria/constantes de formação inválidas.")
    if np.any(np.sum(A,axis=1)<=0):
        raise ValueError("Cada espécie formada deve conter ao menos um componente.")
    base=float(log_base)
    if not math.isfinite(base) or base<=0 or abs(base-1.0)<1e-15:
        raise ValueError("Base logarítmica inválida.")
    ln_beta=lb*math.log(base)
    scale=np.maximum(b,1e-30)
    if initial_free is None:
        x0=np.log(np.maximum(b*0.5,1e-30))
    else:
        f0=np.asarray(initial_free,dtype=float)
        if f0.shape!=b.shape or np.any(f0<=0) or np.any(~np.isfinite(f0)):
            raise ValueError("initial_free deve ser positivo e ter o tamanho dos componentes.")
        x0=np.log(f0)

    def state(logfree):
        free=np.exp(np.clip(logfree,-745,700))
        # log c_s = ln beta_s + sum_j nu_sj ln c_j
        logformed=ln_beta + A@np.log(np.maximum(free,1e-300))
        formed=np.exp(np.clip(logformed,-745,700))
        calc=free + A.T@formed
        return free,formed,calc

    def residual(logfree):
        _,_,calc=state(logfree)
        return (calc-b)/scale

    res=least_squares(residual,x0,xtol=rtol,ftol=rtol,gtol=rtol,max_nfev=int(max_nfev),method="trf")
    free,formed,calc=state(res.x)
    abs_res=calc-b
    return {
        "free_components":free.tolist(),
        "formed_species":formed.tolist(),
        "reconstructed_totals":calc.tolist(),
        "mass_balance_residuals":abs_res.tolist(),
        "mass_balance_residual_norm":float(np.max(np.abs(abs_res)/scale)),
        "converged":bool(res.success and np.max(np.abs(abs_res)/scale)<max(1e-8,10*rtol)),
        "iterations":int(res.nfev),
        "nfev":int(res.nfev),
        "message":str(res.message),
    }
