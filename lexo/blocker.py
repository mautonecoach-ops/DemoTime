# lexo/blocker.py - Blocker v0.2 (robusto)
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

MetricDict = Dict[str, float]

def _clamp_0_100(x: float) -> float:
    if x < 0: return 0.0
    if x > 100: return 100.0
    return x

@dataclass
class BlockerPolicy:
    """
    Política de decisión:
    - min: umbrales mínimos por métrica (0–100).
    - weights: pesos por métrica (suman 1.0 idealmente; si no, se normalizan).
    - require_fail_count: bloquear si fallan >= N métricas.
    - score_threshold: bloquear si score ponderado < este umbral (0–100). None = desactivado.
    """
    min: Dict[str, float] = field(default_factory=lambda: {
        "trust": 50.0, "cohesion": 30.0, "equity": 50.0
    })
    weights: Dict[str, float] = field(default_factory=lambda: {
        "trust": 1.0/3, "cohesion": 1.0/3, "equity": 1.0/3
    })
    require_fail_count: int = 1
    score_threshold: float | None = None  # p.ej., 60.0 para exigir un score mínimo

@dataclass
class BlockerConfig:
    policy: BlockerPolicy = field(default_factory=BlockerPolicy)
    dry_run: bool = False  # si True, nunca bloquea; sólo avisa

@dataclass
class Blocker:
    config: BlockerConfig = field(default_factory=BlockerConfig)

    def evaluate(self, metrics: MetricDict) -> Tuple[bool, List[str]]:
        """
        metrics: {"trust": float, "cohesion": float, "equity": float} en 0–100
        return: (block, reasons)
        """
        reasons: List[str] = []
        pol = self.config.policy

        # 1) Normalizar entradas: faltantes → 0; clamp 0–100
        vals: Dict[str, float] = {}
        for k in ("trust", "cohesion", "equity"):
            v = float(metrics.get(k, 0.0))
            v = _clamp_0_100(v)
            if k not in metrics:
                reasons.append(f"{k} no provisto → asumido 0.0")
            vals[k] = v

        # 2) Chequeos por umbral mínimo
        fails: List[str] = []
        for k, v in vals.items():
            min_k = float(pol.min.get(k, 0.0))
            if v < min_k:
                fails.append(f"{k} {v:.1f} < min {min_k:.1f}")

        # 3) Score ponderado (cuánto “pasa” respecto a su mínimo)
        # pass_ratio_k = 1.0 si v >= min; lineal hasta 0.0 si v = 0
        # Score = suma(peso_k * pass_ratio_k) * 100
        # Normalizamos pesos si no suman 1.0
        wsum = sum(max(0.0, pol.weights.get(k, 0.0)) for k in ("trust", "cohesion", "equity"))
        if wsum <= 0:
            # fallback: pesos uniformes
            weights = {k: 1.0/3 for k in ("trust", "cohesion", "equity")}
        else:
            weights = {k: max(0.0, pol.weights.get(k, 0.0)) / wsum for k in ("trust", "cohesion", "equity")}

        def pass_ratio(k: str, v: float) -> float:
            min_k = float(pol.min.get(k, 0.0))
            if min_k <= 0:
                # Evitar división por cero: si no hay mínimo, consideramos 1.0 si v>0; 0 si v=0
                return 1.0 if v > 0 else 0.0
            return max(0.0, min(1.0, v / min_k))

        score = 100.0 * sum(weights[k] * pass_ratio(k, vals[k]) for k in ("trust", "cohesion", "equity"))

        # 4) Regla compuesta
        should_block = False
        if len(fails) >= pol.require_fail_count:
            reasons.extend(fails)
            reasons.append(f"fallas ≥ {pol.require_fail_count}")
            should_block = True

        if pol.score_threshold is not None and score < pol.score_threshold:
            reasons.append(f"score {score:.1f} < umbral {pol.score_threshold:.1f}")
            should_block = True

        # 5) dry_run: no bloquear, sólo avisar
        if self.config.dry_run and should_block:
            reasons.append("dry_run=True (solo aviso, no bloqueo)")
            return (False, reasons)

        return (should_block, reasons)
