"""Offline reproducible projects shipped as code, available in frozen builds."""

from .project import fresh
from .investigations import create
from .statistics import factorial

NAMES = [
    "UV-Vis: concentração desconhecida",
    "Cinética de primeira ordem",
    "Titulação de ácido forte",
    "Planejamento fatorial de rendimento",
    "Mistura, aquecimento e divisão",
    "Qualidade de uma série de amostras",
]


def example(index):
    d = fresh(NAMES[index])
    d["notes"] = (
        "Projeto didático. Todos os dados deste exemplo são simulados. Registre hipóteses, método, unidades e limitações antes de concluir."
    )
    if index < 3:
        case = create(["calibration", "kinetics", "titration"][index], 42, 0.005)
        d["investigation"] = case
        d["datasets"] = [case["dataset"]]
        d["notes"] += (
            "\n\n" + case["question"] + "\nDados conhecidos: " + str(case["known"])
        )
        if index == 2:
            d["pipeline"] = [{"op": "derivative", "parameters": {}}]
    elif index == 3:
        design = factorial(
            [
                {"name": "Temperatura (°C)", "low": 30, "high": 70},
                {"name": "Concentração (mol/L)", "low": 0.1, "high": 0.5},
            ],
            2,
            3,
            42,
        )
        for r in design["runs"]:
            a, b = r["coded"]
            r["response"] = 50 + 12 * a + 5 * b + 3 * a * b
        d["design"] = design
        d["notes"] += (
            "\nRespostas: y = 50 + 12 A + 5 B + 3 AB, sem ruído; A e B codificados."
        )
    elif index == 4:
        d["process"] = [
            {
                "id": "Água",
                "kind": "feed",
                "parameters": {
                    "flow": 100,
                    "composition": {"água": 1},
                    "temperature": 20,
                    "cp": 4.18,
                },
            },
            {
                "id": "Solução",
                "kind": "feed",
                "parameters": {
                    "flow": 50,
                    "composition": {"água": 0.8, "soluto": 0.2},
                    "temperature": 40,
                    "cp": 4.0,
                },
            },
            {"id": "Mistura", "kind": "mix", "inputs": ["Água", "Solução"]},
            {
                "id": "Aquecimento",
                "kind": "heater",
                "inputs": ["Mistura"],
                "parameters": {"temperature": 60},
            },
            {
                "id": "Divisão",
                "kind": "split",
                "inputs": ["Aquecimento"],
                "parameters": {"fraction": 0.6},
            },
        ]
    else:
        case = create("calibration")
        ds = case["dataset"]
        ds.update(
            name="Material de controle",
            x=list(range(1, 13)),
            y=[10.1, 10.0, 9.9, 10.2, 10.0, 10.1, 9.8, 10.0, 10.1, 10.2, 10.7, 10.1],
            xunit="Ensaio",
            yunit="mg/L",
        )
        ds["source"] = {
            "method": "Série didática definida explicitamente: 12 medições fictícias, alvo 10 e sigma 0,2 mg/L."
        }
        d["datasets"] = [ds]
        d["notes"] += "\nReferência: alvo 10 mg/L, σ=0,2 mg/L; o ensaio 11 excede +3σ."
    return d
