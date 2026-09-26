"""Acyclic steady-state mass flows. kg/h, °C, kJ/(kg·K), kJ/h."""

import copy
import math

KINDS = {
    "feed": "Alimentação",
    "mix": "Misturador",
    "split": "Divisor",
    "heater": "Aquecedor/resfriador",
    "convert": "Conversão mássica A → B",
}


def stream(flow, composition, temperature=25, cp=4.18):
    flow = float(flow)
    temperature = float(temperature)
    cp = float(cp)
    c = {str(k): float(v) for k, v in composition.items()}
    if (
        not c
        or not all(math.isfinite(v) and v >= 0 for v in c.values())
        or not math.isclose(sum(c.values()), 1, abs_tol=1e-8)
    ):
        raise ValueError("Frações mássicas devem ser não negativas e somar 1.")
    if (
        not all(map(math.isfinite, [flow, temperature, cp]))
        or flow <= 0
        or cp <= 0
        or temperature <= -273.15
    ):
        raise ValueError("Vazão e cp positivos; temperatura acima do zero absoluto.")
    return {
        "flow_kg_h": flow,
        "fractions": c,
        "temperature_c": temperature,
        "cp_kj_kg_k": cp,
    }


def simulate(nodes):
    if not 1 <= len(nodes) <= 50:
        raise ValueError("Use de 1 a 50 operações.")
    outputs = {}
    balances = []
    ids = set()
    for node in nodes:
        name = node["id"]
        kind = node["kind"]
        p = node.get("parameters", {})
        inputs = node.get("inputs", [])
        if not name or name in ids or ":" in name:
            raise ValueError("Nome de operação vazio, repetido ou com dois-pontos.")
        ids.add(name)
        if any(key not in outputs for key in inputs):
            raise ValueError(
                "Conecte apenas saídas anteriores; reciclos não são suportados."
            )
        ss = [outputs[key] for key in inputs]
        heat = 0.0
        if kind == "feed":
            if ss:
                raise ValueError("Alimentação não recebe entradas.")
            out = stream(
                p["flow"], p["composition"], p.get("temperature", 25), p.get("cp", 4.18)
            )
            feed = out["flow_kg_h"]
        elif kind == "mix":
            if len(ss) < 2:
                raise ValueError("Misturador exige pelo menos duas entradas.")
            feed = sum(s["flow_kg_h"] for s in ss)
            fractions = {
                k: sum(s["flow_kg_h"] * s["fractions"].get(k, 0) for s in ss) / feed
                for k in set().union(*(s["fractions"] for s in ss))
            }
            cap = sum(s["flow_kg_h"] * s["cp_kj_kg_k"] for s in ss)
            out = stream(
                feed,
                fractions,
                sum(s["flow_kg_h"] * s["cp_kj_kg_k"] * s["temperature_c"] for s in ss)
                / cap,
                cap / feed,
            )
        elif kind in ("split", "heater", "convert"):
            if len(ss) != 1:
                raise ValueError("Operação exige uma entrada.")
            out = copy.deepcopy(ss[0])
            feed = out["flow_kg_h"]
            if kind == "split":
                f = float(p["fraction"])
                if not 0 < f < 1:
                    raise ValueError("Fração do divisor deve estar entre 0 e 1.")
                other = copy.deepcopy(out)
                out["flow_kg_h"] *= f
                other["flow_kg_h"] *= 1 - f
                outputs[name + ":rest"] = other
            elif kind == "heater":
                target = float(p["temperature"])
                if not math.isfinite(target) or target <= -273.15:
                    raise ValueError("Temperatura inválida.")
                heat = feed * out["cp_kj_kg_k"] * (target - out["temperature_c"])
                out["temperature_c"] = target
            else:
                a = p["reactant"]
                b = p["product"]
                conversion = float(p["conversion"])
                if a == b or a not in out["fractions"] or not 0 <= conversion <= 1:
                    raise ValueError("Componentes ou conversão inválidos.")
                delta = out["fractions"][a] * conversion
                out["fractions"][a] -= delta
                out["fractions"][b] = out["fractions"].get(b, 0) + delta
        else:
            raise ValueError("Operação desconhecida.")
        outputs[name] = out
        balances.append(
            {
                "id": name,
                "kind": kind,
                "input_kg_h": feed,
                "output_kg_h": out["flow_kg_h"]
                + outputs.get(name + ":rest", {}).get("flow_kg_h", 0),
                "heat_kj_h": heat,
            }
        )
    # A stream cannot be consumed twice: use an explicit splitter instead.
    consumed = [i for n in nodes for i in n.get("inputs", [])]
    if len(consumed) != len(set(consumed)):
        raise ValueError("Uma saída foi consumida duas vezes; acrescente um divisor.")
    return {
        "streams": outputs,
        "balances": balances,
        "terminal_streams": [k for k in outputs if k not in consumed],
        "method": "Regime estacionário, frações mássicas, cp constante por corrente; mistura adiabática. Conversão A→B com rendimento mássico 1:1, isotérmica, sem cinética/estequiometria molar ou calor de reação. Sem equilíbrio de fases e sem reciclos.",
    }
