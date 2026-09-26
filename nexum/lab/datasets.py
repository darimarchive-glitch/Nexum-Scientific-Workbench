"""Explicit table import; no silently dropped rows or guessed physical units."""

import base64
import csv
import hashlib
import uuid
from pathlib import Path
import numpy as np


def table(text, delimiter="auto", decimal="auto", header=True):
    if len(text.encode()) > 12_000_000:
        raise ValueError("Arquivo excede 12 MB.")
    lines = [
        l
        for l in text.lstrip("\ufeff").splitlines()
        if l.strip() and not l.lstrip().startswith("#")
    ]
    if not lines:
        raise ValueError("Arquivo vazio.")
    if delimiter == "auto":
        delimiter = ";" if ";" in lines[0] else "\t" if "\t" in lines[0] else ","
    if delimiter not in (";", ",", "\t"):
        raise ValueError("Separador inválido.")
    if decimal == "auto":
        decimal = "," if delimiter in (";", "\t") else "."
    rows = list(csv.reader(lines, delimiter=delimiter))
    width = len(rows[0])
    if not 2 <= width <= 256:
        raise ValueError("Selecione uma tabela com 2–256 colunas.")
    names = (
        [s.strip() or f"Coluna {i + 1}" for i, s in enumerate(rows[0])]
        if header
        else [f"Coluna {i + 1}" for i in range(width)]
    )
    values = []
    for i, row in enumerate(rows[1:] if header else rows, 2 if header else 1):
        if len(row) != width:
            raise ValueError(f"Linha {i}: número de colunas diferente.")
        try:
            value = [
                float(v.strip().replace(",", ".") if decimal == "," else v.strip())
                for v in row
            ]
        except ValueError:
            raise ValueError(
                f"Linha {i}: valor ausente ou não numérico; corrija o arquivo."
            )
        if not np.isfinite(value).all():
            raise ValueError(f"Linha {i}: valor não finito.")
        values.append(value)
    if not 3 <= len(values) <= 100000:
        raise ValueError("Use de 3 a 100.000 linhas numéricas.")
    return {
        "columns": names,
        "rows": values,
        "delimiter": delimiter,
        "decimal": decimal,
        "header": header,
    }


def from_table(
    parsed, xcol, ycol, name, raw=b"", xunit="", yunit="", origin="Experimental"
):
    if xcol == ycol:
        raise ValueError("Escolha colunas X e Y distintas.")
    a = np.asarray(parsed["rows"], dtype=float)
    if (
        a.ndim != 2
        or a.shape[1] < 2
        or not 3 <= len(a) <= 100000
        or not np.isfinite(a).all()
    ):
        raise ValueError("Tabela numérica inválida.")
    if (
        type(xcol) is not int
        or type(ycol) is not int
        or not 0 <= xcol < a.shape[1]
        or not 0 <= ycol < a.shape[1]
    ):
        raise ValueError("Índice de coluna fora da tabela.")
    x = a[:, xcol]
    y = a[:, ycol]
    order = np.argsort(x, kind="stable")
    x = x[order]
    y = y[order]
    if np.any(np.diff(x) <= 0):
        raise ValueError(
            "X repetido: organize as réplicas em colunas/séries separadas."
        )
    d = {
        "id": uuid.uuid4().hex,
        "name": name,
        "x": x.tolist(),
        "y": y.tolist(),
        "xunit": xunit,
        "yunit": yunit,
        "origin": origin,
        "source": {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "original_base64": base64.b64encode(raw).decode(),
            "xcol": int(xcol),
            "ycol": int(ycol),
            "columns": parsed["columns"],
            "delimiter": parsed["delimiter"],
            "decimal": parsed["decimal"],
            "header": parsed["header"],
        },
    }
    validate_dataset(d)
    return d


def validate_dataset(d):
    from nexum.core.data_analysis import xy_data

    x, y = xy_data(d["x"], d["y"])
    if not np.all(np.diff(np.asarray(d["x"], float)) > 0):
        raise ValueError("X deve estar em ordem crescente sem repetições.")
    if len(x) > 100000:
        raise ValueError("Série excede 100.000 pontos.")
    if not isinstance(d.get("id"), str) or not isinstance(d.get("name"), str):
        raise ValueError("Série inválida.")
    source = d.get("source", {})
    if "original_base64" in source:
        raw = base64.b64decode(source["original_base64"], validate=True)
        if len(raw) > 12_000_000 or hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("Os dados originais não correspondem ao hash da série.")


def import_jcamp(text, name="Espectro JCAMP", raw=None):
    """Only uncompressed explicit XYPOINTS; compressed XYDATA is rejected."""
    if len(text.encode()) > 12_000_000:
        raise ValueError("Arquivo excede 12 MB.")
    meta = {}
    pairs = []
    active = False
    for line in text.splitlines():
        line = line.split("$$", 1)[0].strip()
        if not line:
            continue
        if line.startswith("##"):
            key, _, value = line[2:].partition("=")
            key = key.strip().upper()
            meta[key] = value.strip()
            active = key == "XYPOINTS"
            if key in ("XYDATA", "PEAK TABLE", "NTUPLES"):
                raise ValueError("Use JCAMP XYPOINTS sem compressão, ou exporte CSV.")
        elif active:
            fields = line.replace(",", " ").replace(";", " ").split()
            if len(fields) % 2:
                raise ValueError("Pares XYPOINTS incompletos.")
            pairs.extend(
                [
                    [float(fields[i]), float(fields[i + 1])]
                    for i in range(0, len(fields), 2)
                ]
            )
    if not pairs:
        raise ValueError("Nenhum bloco XYPOINTS explícito.")
    xf = float(meta.get("XFACTOR", 1))
    yf = float(meta.get("YFACTOR", 1))
    parsed = {
        "columns": ["X", "Y"],
        "rows": [[x * xf, y * yf] for x, y in pairs],
        "delimiter": "JCAMP XYPOINTS",
        "decimal": ".",
        "header": True,
    }
    return from_table(
        parsed,
        0,
        1,
        name,
        text.encode() if raw is None else raw,
        meta.get("XUNITS", ""),
        meta.get("YUNITS", ""),
    )


def export_csv(d, path):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([f"X ({d.get('xunit', '')})", f"Y ({d.get('yunit', '')})"])
        for x, y in zip(d["x"], d["y"]):
            w.writerow([str(x).replace(".", ","), str(y).replace(".", ",")])
