"""Reproducible synthetic educational data, explicitly labeled as simulated."""

import uuid
import numpy as np

SCENARIOS = {
    "calibration": "Concentração desconhecida por UV-Vis",
    "kinetics": "Identificar uma constante cinética",
    "titration": "Concentração por titulação ácido forte/base forte",
}


def create(kind="calibration", seed=42, noise=0.01):
    if kind not in SCENARIOS or not 0 <= float(noise) <= 0.1:
        raise ValueError("Cenário ou ruído inválido (0–0,1).")
    rng = np.random.default_rng(int(seed))
    if kind == "calibration":
        truth = float(rng.uniform(2, 8))
        x = np.linspace(0, 10, 11)
        a = 0.075
        b = 0.02
        y = a * x + b + rng.normal(0, noise, len(x))
        extra = {"unknown_signal": float(a * truth + b + rng.normal(0, noise))}
        unit = "mg/L"
        xu = "mg/L"
        yu = "Abs"
        question = "Construa a calibração e estime a concentração da amostra desconhecida. Justifique o método e discuta o ruído."
    elif kind == "kinetics":
        truth = float(rng.uniform(0.02, 0.1))
        x = np.linspace(0, 100, 51)
        y = np.exp(-truth * x) + rng.normal(0, noise, len(x))
        extra = {"initial_concentration": 1}
        unit = "s⁻¹"
        xu = "s"
        yu = "mol/L"
        question = "Estime k para o modelo C=C₀ exp(−kt). Justifique o ajuste e discuta os resíduos."
    else:
        truth = float(rng.uniform(0.04, 0.14))
        va = 20.0
        cb = 0.1
        # Include equivalence explicitly so a sparse sampling grid does not skip the jump.
        x = np.unique(np.r_[np.linspace(0, 40, 161), truth * va / cb])
        excess = (cb * x - truth * va) / (va + x)
        h = (-excess + np.sqrt(excess**2 + 4e-14)) / 2
        # Stable expression for the basic branch avoids cancellation.
        h = np.where(excess > 0, 2e-14 / (excess + np.sqrt(excess**2 + 4e-14)), h)
        y = -np.log10(h) + rng.normal(0, noise, len(x))
        extra = {"sample_volume_ml": va, "titrant_mol_l": cb}
        unit = "mol/L"
        xu = "mL"
        yu = "pH"
        question = "Localize a equivalência e estime a concentração do ácido. Modelo ideal, ácido/base fortes, 25 °C."
    dataset = {
        "id": uuid.uuid4().hex,
        "name": SCENARIOS[kind],
        "x": x.tolist(),
        "y": y.tolist(),
        "xunit": xu,
        "yunit": yu,
        "origin": "Simulado",
        "source": {"seed": int(seed), "noise_sd": float(noise), "scenario": kind},
    }
    return {
        "kind": kind,
        "seed": int(seed),
        "noise": float(noise),
        "dataset": dataset,
        "question": question,
        "known": extra,
        "answer": truth,
        "unit": unit,
        "attempts": [],
        "revealed": False,
        "notice": "Atividade formativa local; o arquivo contém o gabarito e não é uma prova protegida.",
    }


def submit(case, estimate, reasoning):
    estimate = float(estimate)
    if not np.isfinite(estimate) or not reasoning.strip():
        raise ValueError("Informe estimativa finita e justificativa.")
    truth = case["answer"]
    error = 100 * (estimate - truth) / abs(truth)
    return {
        "estimate": estimate,
        "reasoning": reasoning,
        "relative_error_percent": float(error),
        "feedback": "Compare sua estimativa com o ruído, o modelo e os dados. O erro relativo não substitui a avaliação da justificativa.",
    }
