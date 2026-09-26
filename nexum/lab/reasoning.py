"""Explicit chemical models, correlated uncertainty and ideal speciation.

First-order uncertainty follows JCGM 100 (GUM). Monte Carlo samples the stated
normal input distributions (JCGM 101 approach); it is not a substitute for a
measurement model, calibration, or an uncertainty budget established by a lab.
"""

import numpy as np
from .project import fingerprint

R = 8.31446261815324  # exact SI product N_A*k_B, J mol^-1 K^-1
MODELS = {
    "dilution": {
        "name": "Diluição — C₂ = C₁ V₁ / V₂",
        "inputs": [("C₁", "mol/L", 0.1), ("V₁", "mL", 10.0), ("V₂", "mL", 100.0)],
        "unit": "mol/L",
        "assumptions": "Conservação do soluto, sem reação ou perda; V₂ é o volume final da solução.",
    },
    "beer": {
        "name": "Beer–Lambert — c = A / (ε l)",
        "inputs": [("A", "Abs", 0.5), ("ε", "L/(mol·cm)", 100.0), ("l", "cm", 1.0)],
        "unit": "mol/L",
        "assumptions": "Sinal corrigido por branco, espécie única, caminho óptico uniforme, ausência de espalhamento e faixa linear.",
    },
    "kinetics": {
        "name": "Cinética de primeira ordem — k = ln(C₀/C) / t",
        "inputs": [("C₀", "mol/L", 1.0), ("C", "mol/L", 0.5), ("t", "s", 10.0)],
        "unit": "s⁻¹",
        "assumptions": "Reação irreversível de primeira ordem, volume constante; duas medições não demonstram ordem nem mecanismo.",
    },
    "gas": {
        "name": "Gás ideal — n = PV / (RT)",
        "inputs": [
            ("P absoluta", "Pa", 101325.0),
            ("V", "m³", 0.024),
            ("T absoluta", "K", 298.15),
        ],
        "unit": "mol",
        "assumptions": "Gás ideal, pressão e temperatura absolutas; não estima erro de idealidade nem equilíbrio de fases.",
    },
}


def _function(key, a):
    x, y, z = a
    if key == "dilution":
        return x * y / z
    if key == "beer":
        return x / (y * z)
    if key == "kinetics":
        return np.log(x / y) / z
    return x * y / (R * z)


def _gradient(key, a):
    x, y, z = a
    f = _function(key, a)
    if key == "dilution":
        return np.array([y / z, x / z, -f / z])
    if key == "beer":
        return np.array([1 / (y * z), -f / y, -f / z])
    if key == "kinetics":
        return np.array([1 / (x * z), -1 / (y * z), -f / z])
    return np.array([y / (R * z), x / (R * z), -f / z])


def uncertainty(
    key, means, standard_uncertainties, correlations=None, draws=20000, seed=42
):
    if key not in MODELS:
        raise ValueError("Modelo desconhecido.")
    a = np.asarray(means, float)
    u = np.asarray(standard_uncertainties, float)
    if (
        a.shape != (3,)
        or u.shape != (3,)
        or not np.isfinite(a).all()
        or not np.isfinite(u).all()
        or np.any(a <= 0)
        or np.any(u < 0)
    ):
        raise ValueError(
            "Três valores positivos e incertezas padrão não negativas são necessários."
        )
    if key == "kinetics" and a[1] > a[0]:
        raise ValueError("Este modelo de consumo exige C ≤ C₀.")
    if type(draws) is not int or not 1000 <= draws <= 100000:
        raise ValueError("Use 1.000–100.000 amostras.")
    c = np.eye(3) if correlations is None else np.asarray(correlations, float)
    if (
        c.shape != (3, 3)
        or not np.isfinite(c).all()
        or not np.allclose(c, c.T, rtol=0, atol=1e-12)
        or not np.allclose(np.diag(c), 1, rtol=0, atol=1e-12)
        or np.any(np.abs(c) > 1)
    ):
        raise ValueError(
            "A matriz de correlação precisa ser simétrica, diagonal 1 e entradas entre −1 e 1."
        )
    eig, q = np.linalg.eigh(c)
    if eig.min() < -1e-10:
        raise ValueError("As correlações não formam uma matriz semidefinida positiva.")
    covariance = c * np.outer(u, u)
    g = _gradient(key, a)
    variance = float(g @ covariance @ g)
    combined = float(np.sqrt(max(0, variance)))
    nominal = float(_function(key, a))
    # Factor the correlation matrix, then scale by each uncertainty: avoids
    # mixed-unit conditioning during covariance factorization.
    random = np.random.default_rng(int(seed)).standard_normal((3, draws))
    samples = a[:, None] + u[:, None] * (
        q @ np.diag(np.sqrt(np.maximum(eig, 0))) @ random
    )
    valid = np.all(samples > 0, axis=0)
    if key == "kinetics":
        valid &= samples[1] <= samples[0]
    rejected = int(draws - valid.sum())
    if rejected:
        raise ValueError(
            f"{rejected}/{draws} amostras normais ficaram fora do domínio físico. Revise as distribuições e incertezas; o Nexum não trunca nem descarta essas amostras para apresentar um intervalo artificial."
        )
    values = _function(key, samples)
    if not np.isfinite(values).all():
        raise ValueError("Propagação produziu valores não finitos.")
    lo, hi = np.quantile(values, [0.025, 0.975])
    sd = float(np.std(values, ddof=1))
    diagonal = [float(g[i] ** 2 * u[i] ** 2) for i in range(3)]
    cross = [
        {"inputs": [i, j], "value": float(2 * g[i] * g[j] * covariance[i, j])}
        for i in range(3)
        for j in range(i + 1, 3)
    ]
    return {
        "model": key,
        "name": MODELS[key]["name"],
        "nominal": nominal,
        "unit": MODELS[key]["unit"],
        "standard_uncertainty": combined,
        "expanded_k2": 2 * combined,
        "coverage_factor": 2,
        "monte_carlo": {
            "samples": draws,
            "seed": int(seed),
            "mean": float(np.mean(values)),
            "sd": sd,
            "median": float(np.median(values)),
            "interval_95_percent": [float(lo), float(hi)],
        },
        "gradient": g.tolist(),
        "effects_of_one_u": (g * u).tolist(),
        "diagonal_variance_terms": diagonal,
        "covariance_terms": cross,
        "parameters": {
            "means": a.tolist(),
            "standard_uncertainties": u.tolist(),
            "correlations": c.tolist(),
        },
        "input_sha256": fingerprint(
            [key, a.tolist(), u.tolist(), c.tolist(), draws, seed]
        ),
        "assumptions": MODELS[key]["assumptions"],
        "method": "Propagação linear JΣJᵀ e Monte Carlo com entradas normais correlacionadas. u são incertezas padrão. U=2u não garante cobertura de 95%; o intervalo Monte Carlo é um intervalo central do modelo probabilístico assumido. Não inclui erro de modelo.",
    }


def speciation(pka=4.76, ph_min=0.0, ph_max=14.0, points=281):
    pka, lo, hi = map(float, (pka, ph_min, ph_max))
    if (
        not np.isfinite([pka, lo, hi]).all()
        or not -20 <= pka <= 30
        or not -10 <= lo < hi <= 30
        or type(points) is not int
        or not 3 <= points <= 2000
    ):
        raise ValueError(
            "Use pKa −20 a 30, pH −10 a 30, mínimo < máximo e 3–2.000 pontos."
        )
    ph = (
        np.unique(np.r_[np.linspace(lo, hi, points), pka])
        if lo <= pka <= hi
        else np.linspace(lo, hi, points)
    )
    acid = 1 / (1 + 10.0 ** (ph - pka))
    base = 1 / (1 + 10.0 ** (pka - ph))
    return {
        "pka": pka,
        "ph": ph.tolist(),
        "acid_fraction": acid.tolist(),
        "base_fraction": base.tolist(),
        "balance_max_error": float(np.max(np.abs(acid + base - 1))),
        "method": "HA ⇌ H⁺ + A⁻; αHA = 1/(1+10^(pH−pKa)); αA⁻ = 1−αHA. Frações de concentração sob aproximação ideal; o pH é fornecido, não é resolvido a partir da concentração total. Sem correção por força iônica ou espécies adicionais.",
    }
