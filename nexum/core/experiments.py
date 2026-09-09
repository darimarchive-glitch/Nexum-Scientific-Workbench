from __future__ import annotations
from dataclasses import dataclass
import math
from .acidbase import titration_state as _shared_titration_state, titration_curve as _shared_titration_curve

R = 8.31446261815324          # J mol-1 K-1, CODATA 2022
R_L_BAR = R / 100.0          # L bar mol-1 K-1
F = 96485.33212              # C mol-1, CODATA 2022
KW_25C = 1e-14
P_STANDARD_BAR = 1.0


def _finite(x, name):
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(f"{name} deve ser finito.")
    return x


def _positive(x, name):
    x = _finite(x, name)
    if x <= 0:
        raise ValueError(f"{name} deve ser maior que zero.")
    return x


def _nonnegative(x, name):
    x = _finite(x, name)
    if x < 0:
        raise ValueError(f"{name} não pode ser negativo.")
    return x


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class ExperimentDefinition:
    id: str
    title: str
    subtitle: str
    kind: str              # dynamic | equilibrium | measurement
    model_label: str
    assumptions: tuple[str, ...]


EXPERIMENTS = [
    ExperimentDefinition(
        "gas", "Pistão de gás ideal", "Compressão/expansão isotérmica quase-estática", "dynamic",
        "pV = nRT; ΔU = 0 para gás ideal isotérmico",
        ("Gás ideal.", "Processo quase-estático e isotérmico.", "A duração é um protocolo imposto, não cinética molecular."),
    ),
    ExperimentDefinition(
        "titration", "Titulação ácido-base", "Ácido monoprótico + base forte; pH por balanço de cargas", "dynamic",
        "Balanço de matéria + eletroneutralidade + Kₐ/Kw",
        ("25 °C e Kw = 10⁻¹⁴.", "Soluções ideais; atividades aproximadas por concentrações.", "Ácido monoprótico."),
    ),
    ExperimentDefinition(
        "electro", "Célula de Daniell sob corrente", "Faraday altera composição; Nernst calcula E reversível", "dynamic",
        "ξ = It/(2F); E = E° − RT/(2F) ln Q",
        ("Volumes constantes.", "Atividades aproximadas por concentrações.", "E mostrado é potencial reversível; queda ôhmica e sobrepotenciais não são modelados."),
    ),
    ExperimentDefinition(
        "calorimetry", "Calorimetria elétrica", "Aquecimento com capacidade térmica e perda opcional", "dynamic",
        "C dT/dt = P − k(T−Tamb)",
        ("cₚ e capacidade do calorímetro constantes.", "Perda térmica linear de Newton quando k > 0.", "Mistura perfeitamente homogênea."),
    ),
    ExperimentDefinition(
        "haber", "Equilíbrio de Haber", "N₂ + 3 H₂ ⇌ 2 NH₃ por termodinâmica e balanço material", "equilibrium",
        "Qp(ξ) = Kp(T); propriedades padrão por Shomate",
        ("Mistura gasosa ideal.", "Estado final de equilíbrio; nenhuma velocidade de reação é inventada.", "Faixa do modelo: 298,15–1400 K."),
    ),
    ExperimentDefinition(
        "spectro", "Beer–Lambert", "Absorbância e transmitância de uma solução", "measurement",
        "A = εbc; T = 10⁻ᴬ",
        ("Meio homogêneo e região linear de Beer–Lambert.", "Sem espalhamento, fluorescência ou saturação instrumental."),
    ),
    ExperimentDefinition(
        "kinetics", "Cinética de primeira ordem", "Evolução temporal de A → produtos", "dynamic",
        "[A](t) = [A]₀ e⁻ᵏᵗ",
        ("k constante.", "Sistema fechado e modelo de primeira ordem."),
    ),
    ExperimentDefinition(
        "nuclear", "Decaimento radioativo", "População esperada a partir da meia-vida", "dynamic",
        "N(t) = N₀ 2⁻ᵗ/ᵗ½",
        ("Modelo estatístico macroscópico.", "A animação não tenta prever qual núcleo individual decai."),
    ),
]
EXPERIMENT_BY_ID = {x.id: x for x in EXPERIMENTS}


def ideal_gas_path(*, n, temp_k, volume_initial_l, volume_final_l, duration_s, time_s):
    n = _positive(n, "n")
    temp_k = _positive(temp_k, "Temperatura")
    v0 = _positive(volume_initial_l, "Volume inicial")
    v1 = _positive(volume_final_l, "Volume final")
    duration_s = _positive(duration_s, "Duração")
    t = clamp(_nonnegative(time_s, "Tempo"), 0, duration_s)
    f = t / duration_s
    v = v0 + (v1 - v0) * f
    pbar = n * R_L_BAR * temp_k / v
    work_by = n * R * temp_k * math.log(v / v0)
    return {
        "time_s": t, "fraction": f, "volume_l": v, "pressure_bar": pbar,
        "temperature_k": temp_k, "work_by_gas_j": work_by,
        "work_on_gas_j": -work_by, "delta_u_j": 0.0, "heat_to_gas_j": work_by,
    }


def _hydrogen_from_strong_charge_balance(strong_acid_excess_m, kw=KW_25C):
    c = _finite(strong_acid_excess_m, "Excesso ácido forte")
    kw = _positive(kw, "Kw")
    return (c + math.sqrt(c * c + 4 * kw)) / 2


def _solve_weak_acid_h(total_acid_m, spectator_cation_m, ka, kw=KW_25C):
    ct = _nonnegative(total_acid_m, "Concentração analítica")
    cm = _nonnegative(spectator_cation_m, "Cátion espectador")
    ka = _positive(ka, "Ka")
    kw = _positive(kw, "Kw")
    def f(h):
        return h + cm - ct * ka / (ka + h) - kw / h
    lo, hi = 1e-16, max(10.0, ct + cm + 1.0)
    flo, fhi = f(lo), f(hi)
    if not (flo < 0 < fhi):
        raise RuntimeError("Não foi possível delimitar a raiz física do balanço de cargas.")
    for _ in range(240):
        mid = math.sqrt(lo * hi)
        fm = f(mid)
        if abs(fm) < 1e-15 or abs(math.log(hi / lo)) < 1e-12:
            return mid
        if fm > 0:
            hi = mid
        else:
            lo = mid
    return math.sqrt(lo * hi)


def titration_state(*, mode="strong-strong", acid_c, acid_v_ml, base_c, base_added_ml, ka=1.8e-5, kw=KW_25C):
    return _shared_titration_state(mode=mode, acid_c=acid_c, acid_v_ml=acid_v_ml, base_c=base_c, base_added_ml=base_added_ml, ka=ka, kw=kw)


def titration_curve(*, mode="strong-strong", acid_c, acid_v_ml, base_c, max_volume_ml, ka=1.8e-5, points=161):
    return _shared_titration_curve(mode=mode, acid_c=acid_c, acid_v_ml=acid_v_ml, base_c=base_c, max_volume_ml=max_volume_ml, ka=ka, points=points, kw=KW_25C)


def daniell_current_state(*, zn_conc0, cu_conc0, zn_volume_l, cu_volume_l, temp_k=298.15, current_a=0.0, time_s=0.0, e0_v=1.10):
    zn0 = _positive(zn_conc0, "[Zn²⁺] inicial")
    cu0 = _positive(cu_conc0, "[Cu²⁺] inicial")
    vz = _positive(zn_volume_l, "Volume Zn")
    vc = _positive(cu_volume_l, "Volume Cu")
    temp = _positive(temp_k, "Temperatura")
    current = _nonnegative(current_a, "Corrente")
    t = _nonnegative(time_s, "Tempo")
    e0 = _finite(e0_v, "E°")
    nzn0 = zn0 * vz
    ncu0 = cu0 * vc
    max_time = (2 * F * ncu0 / current) if current > 0 else math.inf
    teff = min(t, max_time) if math.isfinite(max_time) else t
    xi = current * teff / (2 * F)
    nzn = nzn0 + xi
    ncu = max(0.0, ncu0 - xi)
    zn = nzn / vz
    cu = ncu / vc
    if cu > 0:
        q = zn / cu
        e = e0 - (R * temp / (2 * F)) * math.log(q)
        dg = -2 * F * e / 1000
    else:
        q, e, dg = math.inf, None, None
    return {
        "time_s": teff, "max_time_s": max_time, "exhausted": t >= max_time,
        "extent_mol": xi, "zn_conc_m": zn, "cu_conc_m": cu,
        "reaction_quotient": q, "e_rev_v": e, "delta_g_kj_mol": dg,
        "zinc_mass_lost_g": xi * 65.38, "copper_mass_deposited_g": xi * 63.546,
        "charge_c": current * teff,
    }


def electrical_calorimetry_state(*, mass_g, cp_j_gk, calorimeter_capacity_jk=0.0, initial_temp_k, ambient_temp_k=None, heater_power_w, loss_coefficient_wk=0.0, time_s=0.0):
    m = _positive(mass_g, "Massa")
    cp = _positive(cp_j_gk, "Calor específico")
    ccal = _nonnegative(calorimeter_capacity_jk, "Capacidade do calorímetro")
    ti = _positive(initial_temp_k, "Temperatura inicial")
    ta = ti if ambient_temp_k is None else _positive(ambient_temp_k, "Temperatura ambiente")
    p = _nonnegative(heater_power_w, "Potência")
    k = _nonnegative(loss_coefficient_wk, "Coeficiente de perda")
    t = _nonnegative(time_s, "Tempo")
    ctot = m * cp + ccal
    if k == 0:
        temp = ti + p * t / ctot
    else:
        steady = ta + p / k
        temp = steady + (ti - steady) * math.exp(-k * t / ctot)
    ein = p * t
    stored = ctot * (temp - ti)
    return {
        "time_s": t, "temperature_k": temp, "total_capacity_jk": ctot,
        "input_energy_j": ein, "stored_energy_j": stored, "heat_lost_j": ein - stored,
    }


def beer_lambert_state(*, epsilon_l_mol_cm, concentration_m, path_length_cm, incident=1.0):
    eps = _nonnegative(epsilon_l_mol_cm, "ε")
    c = _nonnegative(concentration_m, "Concentração")
    b = _positive(path_length_cm, "Caminho óptico")
    i0 = _nonnegative(incident, "Intensidade incidente")
    a = eps * c * b
    tr = 10 ** (-a)
    return {"absorbance": a, "transmittance": tr, "transmitted": i0 * tr}


def first_order_state(*, concentration0_m, k_s, time_s):
    c0 = _nonnegative(concentration0_m, "Concentração inicial")
    k = _nonnegative(k_s, "k")
    t = _nonnegative(time_s, "Tempo")
    c = c0 * math.exp(-k * t)
    return {"concentration_m": c, "fraction_remaining": 0.0 if c0 == 0 else c/c0, "half_life_s": math.inf if k == 0 else math.log(2)/k}


def nuclear_decay_state(*, nuclei0, half_life_s, time_s):
    n0 = _nonnegative(nuclei0, "Núcleos iniciais")
    half = _positive(half_life_s, "Meia-vida")
    t = _nonnegative(time_s, "Tempo")
    lam = math.log(2)/half
    rem = n0 * math.exp(-lam*t)
    return {"lambda_s": lam, "remaining": rem, "decayed": n0-rem, "fraction_remaining": 0.0 if n0 == 0 else rem/n0}


# NIST Chemistry WebBook Shomate coefficients used by the v4 audit.
_SHOMATE = {
    "N2": [
        (100,500,(28.98641,1.853978,-9.647459,16.63537,0.000117,-8.671914,226.4168,0.0)),
        (500,2000,(19.50583,19.88705,-8.598535,1.369784,0.527601,-4.935202,212.3900,0.0)),
    ],
    "H2": [
        (298,1000,(33.066178,-11.363417,11.432816,-2.772874,-0.158558,-9.980797,172.707974,0.0)),
        (1000,2500,(18.563083,12.257357,-2.859786,0.268238,1.977990,-1.147438,156.288133,0.0)),
    ],
    "NH3": [
        (298,1400,(19.99563,49.77119,-15.37599,1.921168,0.189174,-53.30667,203.8591,-45.89806)),
    ],
}
_HF298 = {"N2":0.0,"H2":0.0,"NH3":-45.89806}


def _shomate_species(name, temp_k):
    row = next((r for r in _SHOMATE[name] if r[0] <= temp_k <= r[1]), None)
    if row is None:
        raise ValueError(f"Temperatura fora da faixa Shomate validada para {name}.")
    A,B,C,D,E,Fc,G,H = row[2]
    t = temp_k/1000
    cp = A+B*t+C*t*t+D*t**3+E/t**2
    hincr = A*t+B*t*t/2+C*t**3/3+D*t**4/4-E/t+Fc-H
    s = A*math.log(t)+B*t+C*t*t/2+D*t**3/3-E/(2*t*t)+G
    return {"cp":cp,"h":_HF298[name]+hincr,"entropy":s}


def haber_thermodynamics(temp_k):
    t = _positive(temp_k, "Temperatura")
    if not 298.15 <= t <= 1400:
        raise ValueError("O modelo de Haber é validado de 298,15 a 1400 K.")
    n2,h2,nh3 = (_shomate_species("N2",t),_shomate_species("H2",t),_shomate_species("NH3",t))
    dh = 2*nh3["h"]-n2["h"]-3*h2["h"]
    ds = 2*nh3["entropy"]-n2["entropy"]-3*h2["entropy"]
    dg = dh-t*ds/1000
    lnk = -dg*1000/(R*t)
    return {"delta_h_kj_mol":dh,"delta_s_j_mol_k":ds,"delta_g_kj_mol":dg,"ln_kp":lnk,"log10_kp":lnk/math.log(10),"kp":math.exp(lnk) if -745 < lnk < 700 else (0.0 if lnk <= -745 else math.inf)}


def _haber_lnq(n_n2,n_h2,n_nh3,pressure_bar):
    total=n_n2+n_h2+n_nh3
    if n_nh3 <= 0: return -math.inf
    if n_n2 <= 0 or n_h2 <= 0 or total <= 0: return math.inf
    a_n2=(n_n2/total)*pressure_bar/P_STANDARD_BAR
    a_h2=(n_h2/total)*pressure_bar/P_STANDARD_BAR
    a_nh3=(n_nh3/total)*pressure_bar/P_STANDARD_BAR
    return 2*math.log(a_nh3)-math.log(a_n2)-3*math.log(a_h2)


def haber_equilibrium(*, n_n2, n_h2, n_nh3=0.0, temp_k, pressure_bar):
    n_n2=_nonnegative(n_n2,"n(N₂)"); n_h2=_nonnegative(n_h2,"n(H₂)"); n_nh3=_nonnegative(n_nh3,"n(NH₃)")
    p=_positive(pressure_bar,"Pressão"); t=_positive(temp_k,"Temperatura")
    if n_n2+n_h2+n_nh3 <= 0: raise ValueError("Informe alguma quantidade inicial.")
    thermo=haber_thermodynamics(t)
    xi_min=-n_nh3/2; xi_max=min(n_n2,n_h2/3)
    if not xi_max > xi_min: raise ValueError("Não existe intervalo físico para a extensão da reação.")
    span=xi_max-xi_min; eps=max(1e-14,span*1e-12); lo=xi_min+eps; hi=xi_max-eps
    def f(xi): return _haber_lnq(n_n2-xi,n_h2-3*xi,n_nh3+2*xi,p)-thermo["ln_kp"]
    flo,fhi=f(lo),f(hi)
    if flo>=0: xi=lo
    elif fhi<=0: xi=hi
    else:
        for _ in range(240):
            mid=(lo+hi)/2; fm=f(mid)
            if abs(fm)<1e-12 or abs(hi-lo)<max(1e-13,span*1e-12): lo=hi=mid; break
            if fm>0: hi=mid
            else: lo=mid
        xi=(lo+hi)/2
    eq={"n_n2":n_n2-xi,"n_h2":n_h2-3*xi,"n_nh3":n_nh3+2*xi}
    total=sum(eq.values())
    partial={"N2":eq["n_n2"]/total*p,"H2":eq["n_h2"]/total*p,"NH3":eq["n_nh3"]/total*p}
    return {**thermo,"extent_mol":xi,"equilibrium_moles":eq,"total_moles":total,"partial_pressure_bar":partial,"ln_q":_haber_lnq(eq["n_n2"],eq["n_h2"],eq["n_nh3"],p),"conversion_n2":xi/n_n2 if n_n2>0 else None}


def run_benchmarks():
    gas=ideal_gas_path(n=1,temp_k=273.15,volume_initial_l=22.41396954,volume_final_l=22.41396954,duration_s=10,time_s=5)
    tit=titration_state(mode="strong-strong",acid_c=.1,acid_v_ml=25,base_c=.1,base_added_ml=25)
    dan=daniell_current_state(zn_conc0=1,cu_conc0=1,zn_volume_l=1,cu_volume_l=1,current_a=0,time_s=0)
    heat=electrical_calorimetry_state(mass_g=100,cp_j_gk=4.184,initial_temp_k=298.15,heater_power_w=41.84,time_s=10)
    beer=beer_lambert_state(epsilon_l_mol_cm=100,concentration_m=.01,path_length_cm=1)
    kin=first_order_state(concentration0_m=1,k_s=math.log(2)/10,time_s=10)
    nuc=nuclear_decay_state(nuclei0=1000,half_life_s=10,time_s=10)
    hab=haber_thermodynamics(298.15)
    return {
        "gas_stp_atm": gas["pressure_bar"]/1.01325,
        "titration_eq_ph": tit["ph"],
        "daniell_e_v": dan["e_rev_v"],
        "calorimetry_k": heat["temperature_k"],
        "beer_absorbance": beer["absorbance"],
        "kinetic_fraction": kin["fraction_remaining"],
        "nuclear_fraction": nuc["fraction_remaining"],
        "haber_log10_kp_298": hab["log10_kp"],
    }
