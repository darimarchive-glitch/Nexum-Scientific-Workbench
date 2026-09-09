from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class CalculationResult:
    title: str
    primary_value: float
    primary_unit: str
    equation: str
    substitution: str
    steps: tuple[str, ...] = field(default_factory=tuple)
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def formatted(self) -> str:
        return f"{self.primary_value:.10g} {self.primary_unit}".strip()
