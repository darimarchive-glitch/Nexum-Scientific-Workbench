from __future__ import annotations
import math

KW_25C = 1e-14


def _positive(x, name):
    x=float(x)
    if not math.isfinite(x) or x<=0:
        raise ValueError(f"{name} deve ser maior que zero e finito.")
    return x


def _nonnegative(x, name):
    x=float(x)
    if not math.isfinite(x) or x<0:
        raise ValueError(f"{name} deve ser não negativo e finito.")
    return x


def hydrogen_strong_acid(c, kw=KW_25C):
    """Ideal monoprotic strong acid including water autoionization."""
    c=_nonnegative(c,"Concentração")
    kw=_positive(kw,"Kw")
    return (c + math.sqrt(c*c + 4*kw))/2


def hydrogen_strong_base(c, kw=KW_25C):
    """Ideal monobasic strong base including water autoionization."""
    c=_nonnegative(c,"Concentração")
    kw=_positive(kw,"Kw")
    return (-c + math.sqrt(c*c + 4*kw))/2


def solve_monoprotic_acid_h(total_acid_m, spectator_cation_m, ka, kw=KW_25C):
    """Solve H+ from mass balance + electroneutrality for HA/A- with a strong cation.

    C_T = [HA]+[A-]
    [A-] = C_T Ka/(Ka+[H+])
    charge balance: [H+] + C_M = [A-] + Kw/[H+]
    """
    ct=_nonnegative(total_acid_m,"Concentração analítica")
    cm=_nonnegative(spectator_cation_m,"Cátion espectador")
    ka=_positive(ka,"Ka")
    kw=_positive(kw,"Kw")
    def f(h):
        return h + cm - ct*ka/(ka+h) - kw/h
    lo=1e-18
    hi=max(10.0,ct+cm+1.0)
    flo,fhi=f(lo),f(hi)
    if not (flo<0<fhi):
        raise RuntimeError("Não foi possível delimitar a raiz física do balanço de cargas.")
    for _ in range(260):
        mid=math.sqrt(lo*hi)
        fm=f(mid)
        if abs(fm)<1e-15 or abs(math.log(hi/lo))<1e-13:
            return mid
        if fm>0: hi=mid
        else: lo=mid
    return math.sqrt(lo*hi)


def hydrogen_weak_acid(c, ka, kw=KW_25C):
    return solve_monoprotic_acid_h(c,0.0,ka,kw)


def hydrogen_weak_base(c, kb, kw=KW_25C):
    """Ideal weak base B/BH+ including water autoionization.

    Ka(BH+) = Kw/Kb; [BH+] = C_T [H+]/(Ka+[H+])
    charge balance: [H+] + [BH+] = Kw/[H+].
    """
    ct=_nonnegative(c,"Concentração analítica")
    kb=_positive(kb,"Kb")
    kw=_positive(kw,"Kw")
    ka=kw/kb
    def f(h):
        bh=ct*h/(ka+h)
        return h + bh - kw/h
    lo=1e-18; hi=max(10.0,ct+1.0)
    for _ in range(260):
        mid=math.sqrt(lo*hi)
        fm=f(mid)
        if abs(fm)<1e-15 or abs(math.log(hi/lo))<1e-13:
            return mid
        if fm>0: hi=mid
        else: lo=mid
    return math.sqrt(lo*hi)


def buffer_state(formal_acid_m, formal_base_m, ka, kw=KW_25C):
    """Ideal HA + salt MA buffer solved exactly, not via HH shortcut.

    formal_base_m is the analytical concentration of the conjugate-base salt and
    therefore also the spectator-cation concentration for a 1:1 salt.
    """
    ca=_nonnegative(formal_acid_m,"Concentração formal de HA")
    cb=_nonnegative(formal_base_m,"Concentração formal de A-")
    ka=_positive(ka,"Ka")
    kw=_positive(kw,"Kw")
    ct=ca+cb
    h=solve_monoprotic_acid_h(ct,cb,ka,kw)
    a_minus=ct*ka/(ka+h) if ct else 0.0
    ha=ct-a_minus
    ph=-math.log10(h)
    hh=-math.log10(ka)+math.log10(cb/ca) if ca>0 and cb>0 else None
    # Van Slyke ideal buffer-capacity expression plus water contribution.
    beta=math.log(10)*(ct*ka*h/(ka+h)**2 + h + kw/h)
    return {"h_m":h,"oh_m":kw/h,"ph":ph,"ha_m":ha,"a_minus_m":a_minus,
            "hh_ph":hh,"buffer_capacity_m_per_ph":beta}


def titration_state(*, mode="strong-strong", acid_c, acid_v_ml, base_c,
                    base_added_ml, ka=1.8e-5, kw=KW_25C):
    acid_c=_positive(acid_c,"Concentração do ácido")
    acid_v_ml=_positive(acid_v_ml,"Volume do ácido")
    base_c=_positive(base_c,"Concentração da base")
    base_added_ml=_nonnegative(base_added_ml,"Volume de titulante")
    kw=_positive(kw,"Kw")
    na=acid_c*acid_v_ml/1000
    nb=base_c*base_added_ml/1000
    v=(acid_v_ml+base_added_ml)/1000
    eq_ml=na/base_c*1000
    if mode=="strong-strong":
        c_signed=(na-nb)/v
        root = math.hypot(c_signed, 2*math.sqrt(kw))
        # Rationalized root avoids cancellation with excess base.
        h = (c_signed+root)/2 if c_signed >= 0 else 2*kw/(root-c_signed)
        species={"strong_acid_excess_m":c_signed}
    elif mode=="weak-strong":
        ka=_positive(ka,"Ka")
        ct=na/v
        spectator=nb/v
        h=solve_monoprotic_acid_h(ct,spectator,ka,kw)
        a=ct*ka/(ka+h)
        species={"total_acid_m":ct,"spectator_cation_m":spectator,
                 "a_minus_m":a,"ha_m":ct-a}
    else:
        raise ValueError("Modo de titulação desconhecido.")
    return {"mode":mode,"acid_moles":na,"base_moles":nb,"total_volume_l":v,
            "equivalence_ml":eq_ml,"h_m":h,"oh_m":kw/h,
            "ph":-math.log10(h),**species}


def titration_curve(*, mode="strong-strong", acid_c, acid_v_ml, base_c,
                    max_volume_ml, ka=1.8e-5, points=241, kw=KW_25C):
    vmax=_nonnegative(max_volume_ml,"Volume máximo")
    points=max(21,int(points))
    out=[]
    for i in range(points):
        v=vmax*i/(points-1)
        s=titration_state(mode=mode,acid_c=acid_c,acid_v_ml=acid_v_ml,
                          base_c=base_c,base_added_ml=v,ka=ka,kw=kw)
        out.append((v,s["ph"]))
    return out


def monoprotic_speciation(pka, ph):
    ka=10**(-float(pka)); h=10**(-float(ph))
    den=h+ka
    return {"alpha_ha":h/den,"alpha_a":ka/den}
