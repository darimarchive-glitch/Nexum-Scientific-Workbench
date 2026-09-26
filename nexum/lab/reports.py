"""Self-contained HTML/SVG figures. All free text is escaped."""

import html
import json
from pathlib import Path
import numpy as np
from .project import fingerprint

STYLE = """body{font:16px system-ui,sans-serif;color:#182d40;background:#f3f6fa;margin:0}main{max-width:1050px;margin:auto;padding:40px}h1{font-size:36px}h2{border-bottom:2px solid #087eac;padding-bottom:8px}section{background:white;padding:24px;margin:18px 0;border-radius:12px}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #dce4eb;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}.tag{color:#075e80}svg{max-width:100%;height:auto}small{color:#506273}@media print{body{background:white}main{padding:0}section{break-inside:avoid;border:1px solid #ddd}a{color:inherit}}"""


def esc(v):
    return html.escape(str(v))


def plot_svg(x, y, title="", xunit="", yunit=""):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if len(x) > 4000:
        # Min/max envelope per bin retains narrow peaks better than stride sampling.
        groups = np.array_split(np.arange(len(x)), 2000)
        ids = sorted(
            {int(g[np.argmin(y[g])]) for g in groups}
            | {int(g[np.argmax(y[g])]) for g in groups}
        )
        x = x[ids]
        y = y[ids]
    xmin, xmax = float(x.min()), float(x.max())
    ymin, ymax = float(y.min()), float(y.max())
    dx = xmax - xmin or 1
    dy = ymax - ymin or 1
    points = " ".join(
        f"{75 + (a - xmin) / dx * 800:.2f},{350 - (b - ymin) / dy * 285:.2f}"
        for a, b in zip(x, y)
    )
    ticks = ""
    for i in range(6):
        t = i / 5
        px = 75 + 800 * t
        py = 350 - 285 * t
        ticks += f'<path d="M {px} 65 V350 M75 {py} H875" stroke="#dde4ea"/><text x="{px}" y="375" text-anchor="middle">{xmin + t * dx:.4g}</text><text x="65" y="{py + 4}" text-anchor="end">{ymin + t * dy:.4g}</text>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 940 430" role="img" aria-label="{esc(title)}"><rect width="940" height="430" fill="white"/><g font-family="sans-serif" font-size="12" fill="#24394d"><text x="75" y="32" font-size="20">{esc(title)}</text>{ticks}<polyline points="{points}" fill="none" stroke="#087eac" stroke-width="2"/><text x="475" y="413" text-anchor="middle">{esc(xunit)}</text><text transform="translate(18 220) rotate(-90)" text-anchor="middle">{esc(yunit)}</text></g></svg>'


def process_svg(nodes):
    from .processes import KINDS

    h = max(160, len(nodes) * 105 + 30)
    parts = []
    positions = {n["id"]: i * 105 + 35 for i, n in enumerate(nodes)}
    for i, n in enumerate(nodes):
        y = positions[n["id"]]
        for key in n.get("inputs", []):
            py = positions.get(key.split(":")[0], 0)
            parts.append(
                f'<path d="M510 {py + 28} H{560 + i * 7} V{y + 28} H510" fill="none" stroke="#728698" marker-end="url(#arrow)"/>'
            )
        parts.append(
            f'<rect x="60" y="{y}" width="450" height="62" rx="9" fill="#eaf4fa" stroke="#087eac"/><text x="80" y="{y + 25}">{esc(n["id"])} · {esc(KINDS[n["kind"]])}</text><text x="80" y="{y + 46}" font-size="12">Entradas: {esc(", ".join(n.get("inputs", [])) or "externa")}</text>'
        )
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {h}" font-family="sans-serif" font-size="16"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#728698"/></marker></defs>{"".join(parts)}</svg>'


def report(data, path):
    parts = [
        f'<h1>{esc(data["title"])}</h1><p class="tag">Nexum 7 · relatório de trabalho · {esc(data["modified"])}</p>',
        f'<section><h2>Caderno de laboratório</h2><p style="white-space:pre-wrap">{esc(data["notes"])}</p></section>',
    ]
    for d in data["datasets"]:
        parts.append(
            f"<section><h2>{esc(d['name'])}</h2><p>Origem: <strong>{esc(d.get('origin', 'Não informada'))}</strong> · {len(d['x'])} pontos</p>"
            + plot_svg(
                d["x"], d["y"], d["name"], d.get("xunit", ""), d.get("yunit", "")
            )
            + f"<small>SHA-256 da série: {fingerprint(d)}<br>Arquivo original: {esc(d.get('source', {}).get('sha256', 'não importado'))}</small></section>"
        )
    for r in data["results"]:
        payload = r["payload"]
        view = {
            k: v
            for k, v in payload.items()
            if k
            not in (
                "molecule",
                "x",
                "y",
                "predicted",
                "observed",
                "residuals",
                "values",
                "z",
                "streams",
                "geometries",
                "ph",
                "acid_fraction",
                "base_fraction",
            )
        }
        parts.append(
            f"<section><h2>{esc(r['kind'])}</h2><p>{esc(r['at'])}</p><p>Séries de origem: {esc(', '.join(r['sources']))}</p>"
            + result_summary(payload)
            + f"<p>{esc(payload.get('method', ''))}</p><details><summary>Método, parâmetros e rastreabilidade</summary><pre>{esc(json.dumps({'result': view, 'parameters': r.get('parameters', {})}, ensure_ascii=False, indent=2))}</pre></details>"
        )
        if "ph" in payload:
            parts.append(
                plot_svg(
                    payload["ph"], payload["acid_fraction"], "Fração HA", "pH", "Fração"
                )
                + plot_svg(
                    payload["ph"], payload["base_fraction"], "Fração A⁻", "pH", "Fração"
                )
            )
        if "x" in payload and "y" in payload:
            parts.append(
                plot_svg(
                    payload["x"],
                    payload["y"],
                    r["kind"],
                    "X",
                    payload.get("yunit", "Y"),
                )
            )
        if "predicted" in payload:
            parts.append(
                plot_svg(
                    range(1, len(payload["residuals"]) + 1),
                    payload["residuals"],
                    "Resíduos por ensaio",
                    "Ensaio",
                    "Resíduo",
                )
            )
        if "streams" in payload:
            parts.append(
                "<pre>"
                + esc(json.dumps(payload["streams"], ensure_ascii=False, indent=2))
                + "</pre>"
            )
        parts.append("</section>")
    if data["assignments"]:
        parts.append(
            "<section><h2>Atribuições manuais</h2><pre>"
            + esc(json.dumps(data["assignments"], ensure_ascii=False, indent=2))
            + "</pre></section>"
        )
    if data["process"]:
        parts.append(
            "<section><h2>Diagrama de processo</h2>"
            + process_svg(data["process"])
            + "</section>"
        )
    for scene in data["scenes"]:
        parts.append(
            f"<section><h2>{esc(scene['title'])}</h2><p>{esc(scene.get('caption', ''))}</p>"
        )
        if scene.get("png_base64"):
            parts.append(
                '<img alt="Cena molecular" style="max-width:100%" src="data:image/png;base64,'
                + esc(scene["png_base64"])
                + '">'
            )
        parts.append("</section>")
    parts.append(
        "<section><h2>Registro de operações</h2><pre>"
        + esc(json.dumps(data["events"], ensure_ascii=False, indent=2))
        + "</pre></section>"
    )
    parts.append(
        "<p>Interpretação e revisão científica: responsabilidade do autor. Resultados simulados e aproximações estão identificados. Use a impressão do navegador para gerar PDF.</p>"
    )
    Path(path).write_text(
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>'
        + esc(data["title"])
        + "</title><style>"
        + STYLE
        + "</style><main>"
        + "".join(parts)
        + "</main></html>",
        encoding="utf-8",
    )


def presentation(data, path):
    if not data["scenes"]:
        raise ValueError("Salve pelo menos uma cena com imagem.")
    slides = []
    for s in data["scenes"]:
        slides.append(
            f'<section class="slide"><h1>{esc(s["title"])}</h1><p>{esc(s.get("caption", ""))}</p>'
            + (
                f'<img alt="Cena molecular" src="data:image/png;base64,{esc(s["png_base64"])}">'
                if s.get("png_base64")
                else "<p>Esta cena foi salva sem imagem.</p>"
            )
            + "</section>"
        )
    script = """let i=0;const s=[...document.querySelectorAll('.slide')];function show(n){i=Math.max(0,Math.min(s.length-1,n));s.forEach((e,j)=>e.hidden=j!==i);document.querySelector('#page').textContent=(i+1)+' / '+s.length}document.querySelector('#prev').onclick=()=>show(i-1);document.querySelector('#next').onclick=()=>show(i+1);document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')show(i+1);if(e.key==='ArrowLeft')show(i-1)});show(0);"""
    Path(path).write_text(
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>'
        + esc(data["title"])
        + "</title><style>"
        + STYLE
        + "img{max-width:100%;max-height:65vh}nav{padding:15px;text-align:center}button{padding:12px}</style><main>"
        + "".join(slides)
        + '</main><nav><button id="prev">Anterior</button> <span id="page"></span> <button id="next">Próxima</button></nav><script>'
        + script
        + "</script></html>",
        encoding="utf-8",
    )


def result_summary(payload):
    """Readable scientific results; detailed provenance stays in a disclosure."""

    def table(rows):
        return (
            "<table>"
            + "".join(
                "<tr><th>" + esc(k) + "</th><td>" + esc(v) + "</td></tr>"
                for k, v in rows
            )
            + "</table>"
        )

    if "standard_uncertainty" in payload:
        r = payload
        mc = r["monte_carlo"]
        unit = r["unit"]
        return table(
            [
                ("Modelo", r["name"]),
                ("Resultado nominal", f"{r['nominal']:.8g} {unit}"),
                (
                    "Incerteza padrão combinada",
                    f"{r['standard_uncertainty']:.3g} {unit}",
                ),
                ("Incerteza expandida (k=2)", f"{r['expanded_k2']:.3g} {unit}"),
                (
                    "Intervalo central Monte Carlo (95%)",
                    f"{mc['interval_95_percent'][0]:.6g} a {mc['interval_95_percent'][1]:.6g} {unit}",
                ),
                ("Hipóteses", r["assumptions"]),
            ]
        )
    if "coefficients" in payload:
        return table(
            [
                (
                    c["term"],
                    f"{c['value']:.6g}; IC95% {c['ci95'][0]:.6g} a {c['ci95'][1]:.6g}",
                )
                for c in payload["coefficients"]
            ]
            + [
                ("R²", payload["r2"]),
                ("Raiz do erro quadrático médio (RMSE)", payload["rmse"]),
            ]
        )
    if "outside_control" in payload:
        return table(
            [
                ("Resultados", payload["n"]),
                ("Média", payload["mean"]),
                ("Desvio padrão amostral", payload["sd"]),
                ("RSD (%)", payload["rsd_percent"]),
                ("Viés", payload["bias"]),
                ("Fora dos limites de controle", payload["outside_control"]),
                ("Fora da especificação", payload["outside_specification"]),
            ]
        )
    if "rmsd_angstrom" in payload:
        return table(
            [
                ("RMSD (Å)", f"{payload['rmsd_angstrom']:.6g}"),
                ("Correspondências", len(payload["pairs"])),
            ]
        )
    if "geometries" in payload:
        return table(
            [
                (
                    f"Conformero {i + 1}",
                    f"ΔE = {g['relative_energy_kcal_mol']:.6g} kcal/mol; convergiu: {g['molecule']['metadata']['optimization_converged']}",
                )
                for i, g in enumerate(payload["geometries"])
            ]
        )
    if "balances" in payload:
        return table(
            [
                (
                    b["id"],
                    f"Entrada {b['input_kg_h']:.6g} kg/h; saída {b['output_kg_h']:.6g} kg/h; Q = {b['heat_kj_h']:.6g} kJ/h",
                )
                for b in payload["balances"]
            ]
        )
    if "metrics" in payload:
        return table(
            [
                (k, f"{v['value']:.7g} {v['unit']}")
                for k, v in payload["metrics"].items()
            ]
        )
    if "pka" in payload:
        return table(
            [
                ("pKa", payload["pka"]),
                ("Espécies", "HA e A⁻, sob aproximação ideal"),
                ("Maior resíduo da soma das frações", payload["balance_max_error"]),
            ]
        )
    if "percent" in payload:
        return table([("Recuperação (%)", payload["percent"])])
    return "<p>Resultado registrado. Consulte os detalhes do método e dos parâmetros abaixo.</p>"
