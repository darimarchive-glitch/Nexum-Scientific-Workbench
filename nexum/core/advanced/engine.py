from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Callable
import copy
import math
import time


@dataclass(frozen=True)
class SolverSpec:
    """Scientific contract for one computational model.

    `equations` are documentation, never executable shortcuts. The solver is
    always called with the user's current inputs.
    """
    key: str
    name: str
    model: str
    equations: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    validity: tuple[str, ...] = ()
    solver: Callable[..., Any] | None = None


@dataclass
class CalculationTrace:
    solver_key: str
    model: str
    started_utc: str
    elapsed_ms: float
    inputs: dict[str, Any]
    equations: list[str]
    assumptions: list[str]
    validity: list[str]
    diagnostics: dict[str, Any] = field(default_factory=dict)
    result: Any = None

    def as_dict(self):
        return asdict(self)


def _jsonish(value: Any) -> Any:
    """Convert common numerical containers without silently changing values."""
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
    except Exception:
        pass
    if hasattr(value, "__dataclass_fields__"):
        return {k: _jsonish(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _jsonish(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonish(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return value
    return value


def _extract_diagnostics(result: Any) -> dict[str, Any]:
    raw = _jsonish(result)
    diag: dict[str, Any] = {}
    if isinstance(raw, dict):
        keys = (
            "converged", "success", "message", "iterations", "nfev", "njev",
            "residual_norm", "charge_residual", "rr_residual",
            "fugacity_residual_norm", "linear_invariant_max_error",
            "min_concentration", "condition_number", "rmse", "chi2", "dof",
            "reduced_chi2", "solver", "mass_balance_residual_norm",
        )
        for k in keys:
            if k in raw:
                diag[k] = raw[k]
    return diag


class ScientificEngine:
    """Registry + execution layer for auditable scientific computation.

    The engine intentionally has no concept of a preset result. A preset may
    fill the input dictionary in the UI, but `solve()` deep-copies those exact
    current values and invokes the numerical solver every time.
    """
    def __init__(self):
        self._specs: dict[str, SolverSpec] = {}

    def register(self, spec: SolverSpec):
        if not spec.key or spec.solver is None:
            raise ValueError("SolverSpec precisa de key e solver.")
        if spec.key in self._specs:
            raise ValueError(f"Solver já registrado: {spec.key}")
        self._specs[spec.key] = spec
        return self

    def keys(self):
        return tuple(sorted(self._specs))

    def spec(self, key: str) -> SolverSpec:
        try:
            return self._specs[key]
        except KeyError as exc:
            raise KeyError(f"Modelo científico desconhecido: {key}") from exc

    def solve(self, key: str, /, **inputs) -> CalculationTrace:
        spec = self.spec(key)
        # Deep-copy is deliberate: the trace is a reproducible record of the
        # values actually submitted, not references to mutable UI state.
        submitted = copy.deepcopy(inputs)
        started = datetime.now(timezone.utc).isoformat()
        tic = time.perf_counter()
        result = spec.solver(**copy.deepcopy(submitted))
        elapsed = (time.perf_counter() - tic) * 1000.0
        return CalculationTrace(
            solver_key=spec.key,
            model=spec.model,
            started_utc=started,
            elapsed_ms=elapsed,
            inputs=_jsonish(submitted),
            equations=list(spec.equations),
            assumptions=list(spec.assumptions),
            validity=list(spec.validity),
            diagnostics=_extract_diagnostics(result),
            result=_jsonish(result),
        )


def default_engine() -> ScientificEngine:
    """Build the v6.5 advanced backend registry.

    Imports are local so light-weight parts of Nexum can still start if an
    optional scientific dependency is being diagnosed by the installer.
    """
    from .equilibrium import solve_polyprotic_acid, ideal_reaction_equilibrium, formation_speciation_ideal
    from .eos import peng_robinson_pure, peng_robinson_mixture, isothermal_flash_pr
    from .kinetics import mass_action_network
    from .electrochem import butler_volmer, cottrell_current, polarized_electrode
    from .metrology import gum_propagation, monte_carlo_propagation, weighted_linear_regression
    from .spectroscopy import multicomponent_beer

    b = ScientificEngine()
    b.register(SolverSpec(
        "polyprotic-acid", "Especiação ácido-base poliprótica", "Equilíbrio por atividades + balanço de carga",
        ("K_a=a_H a_{A^-}/a_{HA}", "Σ z_i c_i = 0", "I=1/2 Σ c_i z_i²"),
        ("Kw e constantes fornecidas devem corresponder à temperatura/estado padrão usados.",),
        ("Davies/Debye–Hückel são aproximações de solução diluída; o motor informa a faixa."), solve_polyprotic_acid))
    b.register(SolverSpec(
        "formation-speciation", "Especiação por constantes de formação", "Balanços de componentes + lei de ação das massas",
        ("c_s=β_s∏c_j^νsj", "b_j=c_j+Σ_s ν_sj c_s"),
        ("Modelo ideal em concentração; β e concentrações devem usar convenção compatível.",),
        ("Não inclui precipitação nem coeficientes de atividade nesta função; use um modelo específico quando necessário."), formation_speciation_ideal))
    b.register(SolverSpec(
        "reaction-equilibrium", "Equilíbrio multirreacional ideal", "Minimização de Gibbs sob não-negatividade",
        ("Δ_rG=RT(lnQ-lnK)", "n=n0+νᵀξ"),
        ("T e P/V fixos conforme fase selecionada.",),
        ("Ideal; não substitui fugacidades/atividades em sistemas não ideais."), ideal_reaction_equilibrium))
    b.register(SolverSpec(
        "pr-pure", "Peng–Robinson puro", "Equação de estado cúbica de Peng–Robinson",
        ("Z³-(1-B)Z²+(A-3B²-2B)Z-(AB-B²-B³)=0",),
        ("Tc, Pc e fator acêntrico devem corresponder ao componente e unidade declarada."),
        ("Uma EOS cúbica é modelo; proximidade crítica e associação forte exigem cautela."), peng_robinson_pure))
    b.register(SolverSpec(
        "pr-mixture", "Peng–Robinson mistura", "PR + regras de mistura quadráticas",
        ("a=Σ_iΣ_j y_i y_j√(a_i a_j)(1-k_ij)", "b=Σ_i y_i b_i"),
        ("kij=0 se não informado; isso é uma hipótese, não um dado universal."),
        ("Resultados dependem fortemente de parâmetros críticos, ω e kij."), peng_robinson_mixture))
    b.register(SolverSpec(
        "pr-flash", "Flash TP por Peng–Robinson", "Rachford–Rice + igualdade de fugacidades",
        ("z_i=(1-β)x_i+βy_i", "f_i^L=f_i^V", "K_i=φ_i^L/φ_i^V"),
        ("Inicialização por Wilson; iteração de coeficientes de fugacidade."),
        ("Não executa teste completo de estabilidade de plano tangente; diagnóstico explicita a convergência."), isothermal_flash_pr))
    b.register(SolverSpec(
        "mass-action-network", "Rede cinética de ação das massas", "Integração de ODEs estequiométricas",
        ("dc/dt=N(r_f-r_r)",),
        ("Volume e parâmetros cinéticos conforme modelo informado.",),
        ("A lei de ação das massas não infere mecanismo: o mecanismo é entrada do usuário."), mass_action_network))
    b.register(SolverSpec(
        "butler-volmer", "Butler–Volmer", "Cinética de transferência de carga",
        ("j=j0[exp(α_a nFη/RT)-exp(-α_c nFη/RT)]",),
        ("j0, α e área eletroquímica são parâmetros experimentais/modelados."),
        ("Não inclui automaticamente transporte de massa, dupla camada ou queda ôhmica."), butler_volmer))
    b.register(SolverSpec(
        "polarized-electrode", "Eletrodo polarizado", "Inversão de Butler–Volmer + iR",
        ("j=j_BV(η)", "E_aplicado=E_eq+η+IR_s"),
        ("Convenção de sinal: corrente anódica positiva."),
        ("Modelo lumped; transporte de massa deve ser tratado separadamente."), polarized_electrode))
    b.register(SolverSpec(
        "cottrell", "Cottrell", "Difusão transiente planar semi-infinita",
        ("I=nFAc√D/√(πt)",),
        ("Degrau de potencial, eletrodo planar, solução não agitada e reação limitada por transporte."),
        ("Convecção e geometria finita invalidam a cauda ideal em tempos longos."), cottrell_current))
    b.register(SolverSpec(
        "gum", "Propagação GUM", "Linearização por coeficientes de sensibilidade",
        ("u_c²=cᵀUc",),
        ("Incertezas-padrão e covariâncias devem representar as grandezas de entrada."),
        ("Para forte não linearidade/assimetria, compare com Monte Carlo."), gum_propagation))
    b.register(SolverSpec(
        "monte-carlo", "Propagação Monte Carlo", "Amostragem multivariada",
        ("Y=f(X)",),
        ("Entradas são modeladas por normal multivariada nesta implementação."),
        ("Outras distribuições exigem outro gerador; intervalo é empírico por quantis."), monte_carlo_propagation))
    b.register(SolverSpec(
        "weighted-regression", "Regressão linear ponderada", "Mínimos quadrados ponderados",
        ("β=(XᵀWX)⁻¹XᵀWy",),
        ("σ_y conhecido/fornecido; erros em x não são tratados."),
        ("Se x também tiver incerteza relevante, use regressão ortogonal/ODR."), weighted_linear_regression))
    b.register(SolverSpec(
        "multicomponent-beer", "Beer–Lambert multicomponente", "LS/NNLS espectral",
        ("A(λ)=bE(λ)c",),
        ("Espectros de referência e caminho óptico fornecidos pelo usuário."),
        ("Número de condição alto indica problema mal condicionado/colinearidade espectral."), multicomponent_beer))
    return b
