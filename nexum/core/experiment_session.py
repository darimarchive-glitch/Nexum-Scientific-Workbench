"""Experiment controls and calculated display states, independent of GTK."""
from __future__ import annotations

import math
from .experiments import (EXPERIMENT_BY_ID, ideal_gas_path, titration_state,
    daniell_current_state, electrical_calorimetry_state, haber_equilibrium,
    beer_lambert_state, first_order_state, nuclear_decay_state)

CONFIGS = {
    "gas": [
        ("n", "n (mol)", "1"),
        ("temp_k", "T (K)", "298.15"),
        ("volume_initial_l", "V inicial (L)", "24.465"),
        ("volume_final_l", "V final (L)", "12"),
        ("duration_s", "Duração do protocolo (s)", "20"),
    ],
    "titration": [
        ("mode", "Modelo", ("Ácido forte × base forte", "Ácido fraco × base forte")),
        ("acid_c", "C ácido (mol/L)", "0.1"),
        ("acid_v_ml", "V ácido (mL)", "25"),
        ("base_c", "C base (mol/L)", "0.1"),
        ("max_volume_ml", "Volume máximo de base (mL)", "50"),
        ("flow_ml_s", "Vazão da bureta (mL/s)", "0.5"),
        ("ka", "Ka (ácido fraco)", "1.8e-5"),
        ("indicator", "Indicador", ("Fenolftaleína", "Azul de bromotimol", "Sem indicador")),
    ],
    "electro": [
        ("zn_conc0", "[Zn²⁺] inicial (mol/L)", "1"),
        ("cu_conc0", "[Cu²⁺] inicial (mol/L)", "1"),
        ("zn_volume_l", "Volume Zn (L)", "0.25"),
        ("cu_volume_l", "Volume Cu (L)", "0.25"),
        ("temp_k", "T (K)", "298.15"),
        ("current_a", "Corrente imposta (A)", "1"),
        ("duration_s", "Duração máxima (s)", "120"),
    ],
    "calorimetry": [
        ("mass_g", "Massa da amostra (g)", "100"),
        ("cp_j_gk", "cₚ (J/g·K)", "4.184"),
        ("calorimeter_capacity_jk", "C calorímetro (J/K)", "20"),
        ("initial_temp_k", "T inicial (K)", "298.15"),
        ("ambient_temp_k", "T ambiente (K)", "298.15"),
        ("heater_power_w", "Potência (W)", "41.84"),
        ("loss_coefficient_wk", "Perda k (W/K)", "0.15"),
        ("duration_s", "Duração (s)", "120"),
    ],
    "haber": [
        ("n_n2", "n inicial N₂ (mol)", "1"),
        ("n_h2", "n inicial H₂ (mol)", "3"),
        ("n_nh3", "n inicial NH₃ (mol)", "0"),
        ("temp_k", "T (K)", "700"),
        ("pressure_bar", "P total (bar)", "200"),
    ],
    "spectro": [
        ("epsilon_l_mol_cm", "ε (L mol⁻¹ cm⁻¹)", "100"),
        ("concentration_m", "c (mol/L)", "0.002"),
        ("path_length_cm", "b (cm)", "1"),
        ("incident", "I₀ relativo", "1"),
    ],
    "kinetics": [
        ("concentration0_m", "[A]₀ (mol/L)", "1"),
        ("k_s", "k (s⁻¹)", "0.0693147"),
        ("duration_s", "Duração (s)", "40"),
    ],
    "nuclear": [
        ("nuclei0", "N₀", "1000"),
        ("half_life_s", "Meia-vida (s)", "10"),
        ("duration_s", "Duração (s)", "40"),
    ],
}


def default_config(experiment_id):
    return {key: ("strong-strong" if key == "mode" else value[0])
            if isinstance(value, tuple) else float(value)
            for key, _, value in CONFIGS[experiment_id]}


def number(value, digits=5):
    if value is None:
        return "—"
    if math.isinf(value):
        return "∞"
    return f"{value:.{digits}g}".replace(".", ",")


def indicator_state(ph, indicator):
    """Illustrative indicator palette; never used to compute the solution pH.

    The transition intervals follow standard aqueous indicator tables at 25 °C.
    RGB interpolation is a teaching aid, not a measured spectrum.
    """
    if indicator == "Sem indicador":
        return {"color": (.57, .77, .87, .16), "label": "Incolor", "range": None}
    if indicator == "Fenolftaleína":
        fraction = max(0., min(1., (ph - 8.2) / 1.8))
        return {"color": (.57+.33*fraction, .77-.61*fraction, .87-.28*fraction,
                          .16 + .56*fraction),
                "label": "Incolor" if fraction == 0 else "Rosa" if fraction == 1 else "Em viragem",
                "range": (8.2, 10.)}
    if indicator != "Azul de bromotimol":
        raise ValueError("Indicador desconhecido.")
    f = max(0., min(1., (ph - 6.) / 1.6))
    stops = ((.98, .77, .16), (.20, .70, .39), (.16, .41, .87))
    a, b = (stops[0], stops[1]) if f <= .5 else (stops[1], stops[2])
    blend = 2*f if f <= .5 else 2*f-1
    return {"color": tuple(x+(y-x)*blend for x, y in zip(a, b)) + (.63,),
            "label": "Amarelo" if f == 0 else "Azul" if f == 1 else "Em viragem (verde)",
            "range": (6., 7.6)}


class ExperimentSession:
    """One validated parameter set and its deterministic timeline.

    Curves are computed once per configuration, never on every paint/timer tick.
    Seeking recomputes the actual state and derives the visible trace from the
    same model; editing parameters creates a new session at t=0.
    """

    def __init__(self, experiment_id, config=None):
        self.exp = EXPERIMENT_BY_ID[experiment_id]
        self.config = default_config(experiment_id)
        if config:
            unknown = set(config) - set(self.config)
            if unknown:
                raise ValueError(f"Parâmetro desconhecido: {', '.join(sorted(unknown))}")
            self.config.update(config)
        for key, label, default in CONFIGS[experiment_id]:
            if not isinstance(default, tuple):
                value = float(self.config[key])
                if not math.isfinite(value):
                    raise ValueError(f"{label}: informe um número finito.")
                self.config[key] = value
        c = self.config
        for key in ("duration_s", "flow_ml_s", "max_volume_ml"):
            if key in c and c[key] <= 0:
                raise ValueError(f"{dict((k, label) for k, label, _ in CONFIGS[experiment_id])[key]} deve ser maior que zero.")
        self.dynamic = self.exp.kind == "dynamic"
        self.duration = (c["max_volume_ml"] / c["flow_ml_s"]
                         if experiment_id == "titration" else c.get("duration_s", 1.))
        if not math.isfinite(self.duration) or self.duration <= 0:
            raise ValueError("A duração resultante deve ser finita e positiva.")
        self.elapsed = 0.
        self.state = self._sample(0.)  # Validate before constructing a curve.
        if experiment_id == "electro":
            self.duration = min(self.duration, self.state["max_time_s"])
        if not math.isfinite(self.duration) or self.duration <= 0:
            raise ValueError("A duração calculada está fora da faixa numérica do modelo.")
        self.initial_state = dict(self.state)
        self.reference_curve = []
        self.markers = []
        self.xlabel, self.ylabel = "Tempo / s", ""
        self._build_curve()
        self.seek(0.)

    def _sample(self, t):
        c, eid = self.config, self.exp.id
        if eid == "gas":
            s = ideal_gas_path(**c, time_s=t)
        elif eid == "titration":
            v = min(c["max_volume_ml"], c["flow_ml_s"] * t)
            s = titration_state(mode=c["mode"], acid_c=c["acid_c"], acid_v_ml=c["acid_v_ml"],
                               base_c=c["base_c"], base_added_ml=v, ka=c["ka"])
            s.update(base_added_ml=v, max_volume_ml=c["max_volume_ml"],
                     remaining_base_ml=max(0., c["max_volume_ml"]-v),
                     liquid_volume_ml=c["acid_v_ml"]+v,
                     indicator=indicator_state(s["ph"], c["indicator"]))
        elif eid == "electro":
            s = daniell_current_state(**{k: v for k, v in c.items() if k != "duration_s"}, time_s=t)
            s["current_a"] = 0. if s["exhausted"] else c["current_a"]
        elif eid == "calorimetry":
            s = electrical_calorimetry_state(**{k: v for k, v in c.items() if k != "duration_s"}, time_s=t)
            s["temperature_c"] = s["temperature_k"] - 273.15
            s["heat_flow_w"] = c["loss_coefficient_wk"] * (s["temperature_k"]-c["ambient_temp_k"])
        elif eid == "haber":
            s = haber_equilibrium(**c)
        elif eid == "spectro":
            s = beer_lambert_state(**c)
        elif eid == "kinetics":
            s = first_order_state(concentration0_m=c["concentration0_m"], k_s=c["k_s"], time_s=t)
            s["product_m"] = c["concentration0_m"] - s["concentration_m"]
            s["rate_m_s"] = c["k_s"] * s["concentration_m"]
        else:
            s = nuclear_decay_state(nuclei0=c["nuclei0"], half_life_s=c["half_life_s"], time_s=t)
            s["activity_bq"] = s["lambda_s"] * s["remaining"]
        s.setdefault("time_s", t)
        # Undefined reversible voltage and infinite half-life are legitimate;
        # overflowing a finite physical result is not.
        for key in ("ph", "temperature_k", "pressure_bar", "absorbance", "extent_mol",
                    "input_energy_j", "stored_energy_j", "activity_bq", "liquid_volume_ml"):
            if key in s and not math.isfinite(s[key]):
                raise ValueError("Os parâmetros excedem a faixa numérica do modelo.")
        return s

    def _point(self, s):
        eid = self.exp.id
        if eid == "haber":
            return None
        if eid == "spectro":
            return self.config["concentration_m"], s["absorbance"]
        if eid == "titration":
            return s["base_added_ml"], s["ph"]
        key = {"gas": "pressure_bar", "electro": "e_rev_v", "calorimetry": "temperature_c",
               "kinetics": "concentration_m", "nuclear": "remaining"}[eid]
        return None if s[key] is None else (s["time_s"], s[key])

    def _build_curve(self):
        eid, c = self.exp.id, self.config
        self.ylabel = {"gas": "P / bar", "titration": "pH", "electro": "E reversível / V",
                       "calorimetry": "T / °C", "haber": "Quantidade / mol", "spectro": "Absorbância A",
                       "kinetics": "[A] / mol L⁻¹", "nuclear": "N esperado"}[eid]
        if eid == "haber":
            self.xlabel = "Composição inicial e no equilíbrio"
            return
        if eid == "spectro":
            self.xlabel = "Concentração / mol L⁻¹"
            maximum = max(.001, c["concentration_m"]*1.5)
            for i in range(101):
                concentration = maximum*i/100
                s = beer_lambert_state(**{**c, "concentration_m": concentration})
                self.reference_curve.append((concentration, s["absorbance"]))
            return
        times = {self.duration*i/200 for i in range(201)}
        if eid == "titration":
            self.xlabel = "Base adicionada / mL"
            veq = self.state["equivalence_ml"]
            if veq <= c["max_volume_ml"]:
                self.markers.append((veq, "Equivalência"))
            # Resolve the steep pH jump even for coarse/large volume ranges.
            for offset in (0., -.001, .001, -.01, .01, -.05, .05, -.1, .1, -.5, .5):
                t = (veq + offset) / c["flow_ml_s"]
                if 0 <= t <= self.duration:
                    times.add(t)
        if eid in ("kinetics", "nuclear"):
            half = self.state.get("half_life_s", c.get("half_life_s", math.inf))
            for i in range(1, 5):
                if math.isfinite(half) and i*half <= self.duration:
                    times.add(i*half)
                    self.markers.append((i*half, "t½" if i == 1 else f"{i} t½"))
        self.reference_curve = [point for t in sorted(times) if (point := self._point(self._sample(t))) is not None]

    @property
    def complete(self):
        return self.dynamic and self.elapsed >= self.duration

    def seek(self, time_s):
        t = float(time_s)
        if not math.isfinite(t):
            raise ValueError("Tempo deve ser finito.")
        self.elapsed = min(self.duration, max(0., t)) if self.dynamic else 0.
        if self.dynamic:
            self.state = self._sample(self.elapsed)
        self.point = self._point(self.state)
        x = (self.config["flow_ml_s"]*self.elapsed if self.exp.id == "titration" else self.elapsed)
        self.history = [p for p in self.reference_curve if p[0] < x] if self.dynamic else []
        if self.dynamic and self.point is not None:
            self.history.append(self.point)
        self.metrics, self.guide = self._describe()
        return self.state

    def advance(self, seconds):
        return self.seek(self.elapsed + seconds)

    def step(self):
        seconds = .05/self.config["flow_ml_s"] if self.exp.id == "titration" else self.duration/100
        return self.advance(seconds)

    def _describe(self):
        s, c, eid = self.state, self.config, self.exp.id
        n = number
        metrics = [("Tempo", n(self.elapsed)+" s")] if self.dynamic else []
        if eid == "gas":
            metrics += [("Volume", n(s["volume_l"])+" L"), ("Pressão", n(s["pressure_bar"])+" bar"),
                        ("Trabalho pelo gás", n(s["work_by_gas_j"])+" J")]
            guide = "A temperatura permanece constante. Ao diminuir o volume, a pressão aumenta; ao expandir, ela diminui."
        elif eid == "titration":
            metrics += [("Base adicionada", n(s["base_added_ml"])+" mL"), ("Volume no Erlenmeyer", n(s["liquid_volume_ml"])+" mL"),
                        ("pH", n(s["ph"])), ("Equivalência", n(s["equivalence_ml"])+" mL"), ("Indicador", s["indicator"]["label"])]
            veq = s["equivalence_ml"]
            stage = ("Antes da equivalência: há ácido a neutralizar." if s["base_added_ml"] < veq-1e-8 else
                     "Na equivalência: as quantidades estequiométricas se igualam." if abs(s["base_added_ml"]-veq) < 1e-8 else
                     "Depois da equivalência: há base em excesso.")
            guide = stage + " O nível acompanha o volume total; a cor vem do indicador, conforme o pH. A viragem e a equivalência não são o mesmo conceito."
            if veq > c["max_volume_ml"]:
                guide += " O volume máximo escolhido não alcança a equivalência."
        elif eid == "electro":
            metrics += [("Corrente imposta", n(s["current_a"])+" A"), ("E reversível", n(s["e_rev_v"], 7)+" V"),
                        ("[Zn²⁺]", n(s["zn_conc_m"])+" mol/L"), ("[Cu²⁺]", n(s["cu_conc_m"])+" mol/L"),
                        ("Zn dissolvido", n(s["zinc_mass_lost_g"]*1000)+" mg"), ("Cu depositado", n(s["copper_mass_deposited_g"]*1000)+" mg"),
                        ("Carga transferida", n(s["charge_c"])+" C")]
            guide = "Elétrons percorrem o fio do Zn ao Cu; a corrente convencional tem sentido oposto. A ponte salina conduz íons. O zinco se dissolve e o cobre se deposita. O movimento é esquemático; as massas seguem Faraday."
            if c["current_a"] == 0:
                guide = "Corrente zero: não há transferência de carga nem alteração dos eletrodos. O potencial reversível pode ser diferente de zero."
            elif s["exhausted"]:
                guide = "O Cu²⁺ disponível se esgotou. A transferência foi encerrada; o potencial de Nernst não está definido nesse limite."
        elif eid == "calorimetry":
            metrics += [("Temperatura", n(s["temperature_c"])+" °C"), ("Variação de T", n(s["temperature_k"]-c["initial_temp_k"])+" K"),
                        ("Energia elétrica", n(s["input_energy_j"])+" J"), ("Energia armazenada", n(s["stored_energy_j"])+" J"),
                        ("Calor para o ambiente", n(s["heat_lost_j"])+" J")]
            guide = "O termômetro acompanha a temperatura calculada. A resistência transfere energia à amostra e as setas indicam a troca com o ambiente. A cor é uma escala de temperatura, não uma mudança química. Não há mudança de fase neste modelo."
        elif eid == "haber":
            metrics += [("Extensão ξ", n(s["extent_mol"])+" mol"), ("Conversão N₂", "—" if s["conversion_n2"] is None else n(100*s["conversion_n2"])+" %"),
                        ("log₁₀ Kp", n(s["log10_kp"])), ("n(NH₃) no equilíbrio", n(s["equilibrium_moles"]["n_nh3"])+" mol")]
            guide = "Compare a composição inicial com a de equilíbrio. Edite T, pressão ou quantidades para comparar cenários. As partículas são uma representação proporcional; as barras mostram as quantidades em mol. Esta comparação não representa o tempo da reação."
        elif eid == "spectro":
            metrics += [("Absorbância", n(s["absorbance"])), ("Transmitância do modelo", n(100*s["transmittance"])+" %"),
                        ("Intensidade incidente", n(c["incident"])), ("Intensidade transmitida", n(s["transmitted"]))]
            guide = "A cubeta absorve parte do feixe. Mais concentração ou maior caminho óptico aumenta A e reduz a fração transmitida. O ponto no gráfico acompanha a concentração atual; a cor da solução é ilustrativa."
            if c["incident"] == 0:
                guide = "Fonte apagada: I₀ = I = 0. A e a transmitância exibidas são previsões do modelo; não há leitura óptica com a fonte apagada."
        elif eid == "kinetics":
            metrics += [("[A] restante", n(s["concentration_m"])+" mol/L"), ("[B] formado", n(s["product_m"])+" mol/L"),
                        ("Velocidade de consumo", n(s["rate_m_s"])+" mol/L·s"), ("Meia-vida", n(s["half_life_s"])+" s")]
            guide = "Modelo A → B (1:1): o volume fica constante enquanto A é convertido em B. O azul representa A; B é incolor neste exemplo. A cada meia-vida, resta metade do A anterior."
            if c["k_s"] == 0:
                guide = "Com k = 0, a reação não avança: [A] permanece constante e não se forma B."
            elif c["concentration0_m"] == 0:
                guide = "Sem A inicialmente, não há reagente para transformar. O frasco permanece com o solvente."
        else:
            metrics += [("N esperado", n(s["remaining"])), ("N transformado", n(s["decayed"])),
                        ("Atividade esperada", n(s["activity_bq"])+" Bq"), ("Meias-vidas decorridas", n(self.elapsed/c["half_life_s"]))]
            guide = "O painel representa uma população virtual: marcas coloridas são núcleos restantes e marcas cinza são transformados. Cada marca resume 1% de N₀. A curva mostra a média esperada, sem prever eventos individuais."
        return metrics, guide
