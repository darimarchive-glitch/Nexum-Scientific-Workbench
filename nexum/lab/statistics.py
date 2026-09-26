"""Small factorial designs and explicit, user-defined quality criteria."""

import itertools
import numpy as np
from scipy.stats import t


def factorial(factors, replicates=2, centers=3, seed=42):
    if not 1 <= len(factors) <= 5:
        raise ValueError("Use de 1 a 5 fatores.")
    if len({f["name"] for f in factors}) != len(factors):
        raise ValueError("Nomes de fatores devem ser únicos.")
    for f in factors:
        if not np.isfinite([f["low"], f["high"]]).all() or f["low"] >= f["high"]:
            raise ValueError("Cada fator precisa de mínimo < máximo finitos.")
    if (
        type(replicates) is not int
        or not 1 <= replicates <= 10
        or type(centers) is not int
        or not 0 <= centers <= 20
    ):
        raise ValueError("Réplicas: 1–10; pontos centrais: 0–20.")
    rows = []
    for code in (
        list(itertools.product((-1, 1), repeat=len(factors))) * replicates
        + [(0,) * len(factors)] * centers
    ):
        values = [
            (f["low"] + f["high"]) / 2 + c * (f["high"] - f["low"]) / 2
            for f, c in zip(factors, code)
        ]
        rows.append({"coded": list(code), "values": values, "response": None})
    np.random.default_rng(seed).shuffle(rows)
    return {
        "factors": factors,
        "runs": rows,
        "seed": seed,
        "replicates": replicates,
        "centers": centers,
        "method": "Fatorial completo 2^k com réplicas e pontos centrais; ordem aleatorizada.",
    }


def fit_design(design, responses):
    codes = np.array([r["coded"] for r in design["runs"]], float)
    y = np.asarray(responses, float)
    if y.shape != (len(codes),) or not np.isfinite(y).all():
        raise ValueError("Informe uma resposta finita para cada ensaio.")
    terms = ["Intercepto"] + [f["name"] for f in design["factors"]]
    columns = [np.ones(len(codes))] + [codes[:, i] for i in range(codes.shape[1])]
    for i in range(codes.shape[1]):
        for j in range(i + 1, codes.shape[1]):
            terms.append(f"{terms[i + 1]} × {terms[j + 1]}")
            columns.append(codes[:, i] * codes[:, j])
    x = np.column_stack(columns)
    beta, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if rank < len(columns) or len(y) <= rank:
        raise ValueError(
            "Ensaios insuficientes para ajustar e estimar o erro; inclua réplicas."
        )
    predicted = x @ beta
    res = y - predicted
    dof = len(y) - rank
    s2 = float(res @ res / dof)
    se = np.sqrt(np.maximum(0, np.diag(np.linalg.inv(x.T @ x)) * s2))
    margin = t.ppf(0.975, dof) * se
    ss = float(np.sum((y - y.mean()) ** 2))
    return {
        "coefficients": [
            {"term": n, "value": float(v), "ci95": [float(v - m), float(v + m)]}
            for n, v, m in zip(terms, beta, margin)
        ],
        "predicted": predicted.tolist(),
        "observed": y.tolist(),
        "residuals": res.tolist(),
        "rmse": float(np.sqrt(np.mean(res**2))),
        "residual_standard_error": float(np.sqrt(s2)),
        "r2": float(1 - res @ res / ss) if ss > 0 else None,
        "degrees_of_freedom": int(dof),
        "method": "Mínimos quadrados em fatores codificados; efeitos principais e interações de dois fatores. IC95% t de Student. Não ajusta curvatura quadrática nem demonstra causalidade.",
    }


def quality(values, target, sigma, lower=None, upper=None):
    a = np.asarray(values, float)
    target = float(target)
    sigma = float(sigma)
    if (
        a.ndim != 1
        or not 2 <= len(a) <= 100000
        or not np.isfinite(a).all()
        or not np.isfinite([target, sigma]).all()
        or sigma <= 0
    ):
        raise ValueError(
            "Use ≥2 resultados finitos, alvo finito e desvio de referência positivo."
        )
    if lower is not None and (
        not np.isfinite(lower)
        or upper is None
        or not np.isfinite(upper)
        or lower >= upper
    ):
        raise ValueError(
            "Informe ambos os limites de especificação, com inferior < superior."
        )
    if upper is not None and lower is None:
        raise ValueError("Informe também o limite inferior.")
    mean = float(a.mean())
    sd = float(a.std(ddof=1))
    z = (a - target) / sigma
    return {
        "n": len(a),
        "mean": mean,
        "sd": sd,
        "rsd_percent": 100 * sd / abs(mean) if abs(mean) > 1e-15 else None,
        "bias": mean - target,
        "control_limits": [target - 3 * sigma, target + 3 * sigma],
        "values": a.tolist(),
        "z": z.tolist(),
        "outside_control": [int(i + 1) for i in np.flatnonzero(np.abs(z) > 3)],
        "outside_specification": [
            int(i + 1) for i in np.flatnonzero((a < lower) | (a > upper))
        ]
        if lower is not None
        else [],
        "specification": [lower, upper],
        "method": "Carta individual com alvo e σ de referência fornecidos; limites de controle ±3σ não são limites de especificação.",
    }


def recovery(original, fortified, added):
    original, fortified, added = map(float, (original, fortified, added))
    if not np.isfinite([original, fortified, added]).all() or added <= 0:
        raise ValueError(
            "Adição deve ser positiva e valores finitos, na mesma unidade e base de diluição."
        )
    return 100 * (fortified - original) / added
