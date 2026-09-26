"""Bounds and structural checks for portable, untrusted project documents."""

import base64
import math
import re
import struct


def graph(value):
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("atoms"), list)
        or not isinstance(value.get("bonds"), list)
    ):
        raise ValueError("Desenho molecular inválido.")
    atoms = value["atoms"]
    bonds = value["bonds"]
    if len(atoms) > 200 or len(bonds) > 800:
        raise ValueError("Desenho molecular muito grande.")
    for a in atoms:
        if isinstance(a, dict) and set(a) - {
            "element",
            "charge",
            "explicit_h",
            "no_implicit",
            "x",
            "y",
        }:
            raise ValueError(
                "O desenho contém atributos atômicos não suportados por este editor."
            )
        if (
            not isinstance(a, dict)
            or not isinstance(a.get("element"), str)
            or not re.fullmatch("[A-Z][a-z]?", a["element"])
        ):
            raise ValueError("Símbolo de elemento inválido.")
        if type(a.get("charge", 0)) is not int or abs(a.get("charge", 0)) > 10:
            raise ValueError("Carga formal inválida.")
        if any(
            not isinstance(a.get(k, 0), (int, float))
            or not math.isfinite(a.get(k, 0))
            or abs(a.get(k, 0)) > 1000
            for k in ("x", "y")
        ):
            raise ValueError("Coordenadas do desenho inválidas.")
        if (
            type(a.get("explicit_h", 0)) is not int
            or not 0 <= a.get("explicit_h", 0) <= 8
            or type(a.get("no_implicit", False)) is not bool
        ):
            raise ValueError("Estado de hidrogênios inválido.")
    seen = set()
    for bond in bonds:
        if not isinstance(bond, (list, tuple)) or len(bond) != 3:
            raise ValueError("Ligação inválida.")
        i, j, order = bond
        if (
            type(i) is not int
            or type(j) is not int
            or not 0 <= i < len(atoms)
            or not 0 <= j < len(atoms)
            or i == j
            or order not in (1, 1.5, 2, 3)
        ):
            raise ValueError("Ligação fora do desenho.")
        pair = tuple(sorted((i, j)))
        if pair in seen:
            raise ValueError("Ligação repetida.")
        seen.add(pair)


def nested(data):
    from .workflows import OPERATIONS
    from .processes import simulate
    from nexum.core.molecular_analysis import molecule_from_dict
    from nexum.core.session_validation import validate_structure

    if not isinstance(data.get("id"), str) or not re.fullmatch(
        "[a-f0-9]{32}", data["id"]
    ):
        raise ValueError("Identificador de projeto inválido.")
    if any(not isinstance(data.get(k), str) for k in ("notes", "created", "modified")):
        raise ValueError("Caderno ou datas inválidos.")
    graph(data.get("graph"))
    if data.get("molecule") is not None:
        molecule_from_dict(data["molecule"])
    steps = data.get("pipeline")
    if not isinstance(steps, list) or len(steps) > 30:
        raise ValueError("Fluxo inválido (máximo 30 etapas).")
    for s in steps:
        if (
            not isinstance(s, dict)
            or s.get("op") not in OPERATIONS
            or not isinstance(s.get("parameters", {}), dict)
        ):
            raise ValueError("Etapa de fluxo inválida.")
    nodes = data.get("process")
    if not isinstance(nodes, list):
        raise ValueError("Fluxograma inválido.")
    if nodes:
        simulate(nodes)
    ids = {d["id"] for d in data["datasets"]}
    for a in data["assignments"]:
        if (
            not isinstance(a, dict)
            or a.get("dataset_id") not in ids
            or not isinstance(a.get("range"), list)
            or len(a["range"]) != 2
            or a["range"][0] >= a["range"][1]
        ):
            raise ValueError("Atribuição espectral inválida.")
        if (
            not isinstance(a.get("atom_indices"), list)
            or not a["atom_indices"]
            or any(type(i) is not int or i < 0 for i in a["atom_indices"])
        ):
            raise ValueError("Átomos da atribuição inválidos.")
        if (
            not isinstance(a.get("molecule_sha256"), str)
            or len(a["molecule_sha256"]) != 64
            or not isinstance(a.get("note"), str)
        ):
            raise ValueError("Proveniência da atribuição inválida.")
    for r in data["results"]:
        if (
            not isinstance(r, dict)
            or not all(isinstance(r.get(k), str) for k in ("id", "kind", "at"))
            or not isinstance(r.get("sources"), list)
            or not isinstance(r.get("payload"), dict)
        ):
            raise ValueError("Resultado salvo inválido.")
    for event in data["events"]:
        if not isinstance(event, dict) or not all(
            isinstance(event.get(k), str) for k in ("at", "action")
        ):
            raise ValueError("Registro de operação inválido.")
    for scene in data["scenes"]:
        if (
            not isinstance(scene, dict)
            or not isinstance(scene.get("title"), str)
            or not isinstance(scene.get("caption", ""), str)
        ):
            raise ValueError("Cena inválida.")
        validate_structure(scene.get("state"))
        if not scene.get("state"):
            raise ValueError("Estado da cena ausente.")
        raw = base64.b64decode(scene.get("png_base64", ""), validate=True)
        if (
            not 24 <= len(raw) <= 6_000_000
            or not raw.startswith(b"\x89PNG\r\n\x1a\n")
            or raw[12:16] != b"IHDR"
        ):
            raise ValueError("Imagem PNG inválida ou maior que 6 MB.")
        w, h = struct.unpack(">II", raw[16:24])
        if not w or not h or w * h > 40_000_000:
            raise ValueError("Dimensões de imagem inválidas.")
    design = data.get("design")
    if design is not None:
        from .statistics import factorial

        if not isinstance(design, dict):
            raise ValueError("Planejamento inválido.")
        expected = factorial(
            design["factors"], design["replicates"], design["centers"], design["seed"]
        )
        if len(design["runs"]) != len(expected["runs"]):
            raise ValueError("Número de ensaios inválido.")
        for row, ref in zip(design["runs"], expected["runs"]):
            if (
                row["coded"] != ref["coded"]
                or row["values"] != ref["values"]
                or (
                    row.get("response") is not None
                    and not isinstance(row["response"], (float, int))
                )
            ):
                raise ValueError(
                    "Ordem, fatores ou resposta inválidos no planejamento."
                )
    case = data.get("investigation")
    if case is not None:
        from .investigations import SCENARIOS

        if (
            not isinstance(case, dict)
            or case.get("kind") not in SCENARIOS
            or not isinstance(case.get("question"), str)
            or not isinstance(case.get("unit"), str)
            or not isinstance(case.get("known"), dict)
            or not isinstance(case.get("attempts"), list)
            or not isinstance(case.get("answer"), (float, int))
            or case["answer"] == 0
            or type(case.get("revealed")) is not bool
        ):
            raise ValueError("Investigação inválida.")
        if case["dataset"]["id"] not in ids:
            raise ValueError("Dados da investigação ausentes.")
        for a in case["attempts"]:
            if not all(
                k in a
                for k in ("estimate", "relative_error_percent", "reasoning", "feedback")
            ):
                raise ValueError("Tentativa inválida.")
