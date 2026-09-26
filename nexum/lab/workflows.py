"""Ordered blocks, deterministic execution and hashes for every transition."""

import numpy as np
from scipy.signal import savgol_filter
from nexum.core.data_analysis import xy_data
from .project import fingerprint

OPERATIONS = {
    "baseline": "Linha de base linear",
    "smooth": "Suavização Savitzky–Golay",
    "normalize": "Normalizar pelo máximo absoluto",
    "derivative": "Derivada numérica",
    "integrate": "Integrar intervalo",
    "calibrate": "Converter sinal em concentração",
}


def execute(dataset, steps):
    x, y = xy_data(dataset["x"], dataset["y"])
    y = y.copy()
    x = x.copy()
    if len(steps) > 30:
        raise ValueError("Máximo de 30 etapas por fluxo.")
    trace = []
    metrics = {}
    unit = dataset.get("yunit", "")
    for i, step in enumerate(steps):
        op = step["op"]
        p = step.get("parameters", {})
        before = fingerprint([x.tolist(), y.tolist()])
        if op == "baseline":
            y -= np.interp(x, [x[0], x[-1]], [y[0], y[-1]])
            method = "y − reta entre os extremos"
        elif op == "smooth":
            window = int(p.get("window", 7))
            degree = int(p.get("degree", 2))
            if (
                window < 3
                or window % 2 == 0
                or window > len(x)
                or not 0 <= degree < window
            ):
                raise ValueError(
                    "Janela ímpar ≥ 3, menor que a série; grau menor que a janela."
                )
            if not np.allclose(np.diff(x), np.diff(x)[0], rtol=1e-5):
                raise ValueError("Savitzky–Golay requer espaçamento uniforme de X.")
            y = savgol_filter(y, window, degree)
            method = f"Savitzky–Golay: janela {window}, grau {degree}"
        elif op == "normalize":
            m = float(np.max(np.abs(y)))
            if m <= 0:
                raise ValueError("Série nula não pode ser normalizada.")
            y /= m
            unit = "relativo"
            method = "y / máximo(|y|)"
        elif op == "derivative":
            y = np.gradient(y, x, edge_order=2)
            unit = f"({unit})/({dataset.get('xunit', 'X')})"
            method = "Diferenças finitas, ordem 2 nas extremidades"
        elif op == "integrate":
            lo = float(p.get("lower", x[0]))
            hi = float(p.get("upper", x[-1]))
            if not x[0] <= lo < hi <= x[-1]:
                raise ValueError("Intervalo de integração fora da série.")
            xx = np.r_[lo, x[(x > lo) & (x < hi)], hi]
            yy = np.interp(xx, x, y)
            area = float(np.sum(np.diff(xx) * (yy[:-1] + yy[1:]) / 2))
            metrics[f"area_{i + 1}"] = {
                "value": area,
                "unit": f"{unit} · {dataset.get('xunit', 'X')}",
                "interval": [lo, hi],
            }
            method = "Regra dos trapézios com interpolação dos limites"
        elif op == "calibrate":
            a = float(p.get("slope", 1))
            b = float(p.get("intercept", 0))
            if not np.isfinite([a, b]).all() or abs(a) < 1e-15:
                raise ValueError("Coeficientes inválidos.")
            y = (y - b) / a
            unit = str(p.get("unit", "concentração"))
            method = "c = (sinal − intercepto) / inclinação; incerteza não propagada nesta etapa"
        else:
            raise ValueError("Etapa desconhecida: " + str(op))
        if not np.isfinite(y).all():
            raise ValueError("Resultado não finito.")
        trace.append(
            {
                "step": i + 1,
                "op": op,
                "parameters": p,
                "method": method,
                "input_sha256": before,
                "output_sha256": fingerprint([x.tolist(), y.tolist()]),
            }
        )
    return {
        "x": x.tolist(),
        "y": y.tolist(),
        "yunit": unit,
        "metrics": metrics,
        "trace": trace,
        "source_id": dataset["id"],
        "source_sha256": fingerprint(dataset),
    }
