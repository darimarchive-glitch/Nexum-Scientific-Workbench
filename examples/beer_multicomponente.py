"""Execute na raiz: .venv/bin/python -m examples.beer_multicomponente"""
from nexum.core.engine import default_engine


def main():
    engine = default_engine()
    trace = engine.solve(
        "multicomponent-beer",
        absorbance=[0.12, 0.21, 0.15],
        epsilon_matrix=[[100, 10], [10, 100], [50, 50]],
        path_cm=1.0,
    )
    print("Concentrações (mol/L):", trace.result["concentrations_m"])
    print("Diagnósticos:", trace.diagnostics)
    print("Modelos registrados:", engine.keys())


if __name__ == "__main__":
    main()
