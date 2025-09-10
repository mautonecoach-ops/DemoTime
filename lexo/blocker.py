# lexo/blocker.py
# Blocker v0.1 — implementación mínima, segura y explicada.

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class BlockerConfig:
    """
    Parámetros de seguridad para decidir si se bloquea la ejecución.
    - min_trust: umbral mínimo de confianza.
    - min_cohesion: umbral mínimo de cohesión.
    - min_equity: umbral mínimo de equidad de recursos.
    - dry_run: si True, nunca bloquea realmente (solo avisa).
    """
    min_trust: float = 50.0
    min_cohesion: float = 30.0
    min_equity: float = 50.0
    dry_run: bool = False

@dataclass
class Blocker:
    """
    El Blocker evalúa métricas de contexto (trust/cohesion/equity) y decide:
    - block = True/False
    - reasons = lista de motivos
    """
    config: BlockerConfig = field(default_factory=BlockerConfig)

    def evaluate(self, metrics: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Recibe un dict con métricas (ej: {"trust": 62.5, "cohesion": 28.0, "equity": 55.0})
        Devuelve (block, reasons)
        """
        reasons: List[str] = []

        trust = float(metrics.get("trust", 0.0))
        cohesion = float(metrics.get("cohesion", 0.0))
        equity = float(metrics.get("equity", 0.0))

        if trust < self.config.min_trust:
            reasons.append(f"trust {trust:.1f} < min {self.config.min_trust:.1f}")
        if cohesion < self.config.min_cohesion:
            reasons.append(f"cohesion {cohesion:.1f} < min {self.config.min_cohesion:.1f}")
        if equity < self.config.min_equity:
            reasons.append(f"equity {equity:.1f} < min {self.config.min_equity:.1f}")

        should_block = len(reasons) > 0

        # Modo seguro: si dry_run=True, avisamos pero no bloqueamos realmente
        if self.config.dry_run and should_block:
            reasons.append("dry_run=True (solo aviso, no bloqueo)")

        return (False if self.config.dry_run else should_block, reasons)
