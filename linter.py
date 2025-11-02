# linter.py — v0.4
from dataclasses import dataclass, field
from typing import Any, Dict, List

import yaml


@dataclass
class Violation:
    rule_id: str
    severity: str  # "block" | "warn"
    message: str
    remediation: str | None = None


@dataclass
class LintReport:
    phase: str  # "pre" | "post"
    violations: List[Violation] = field(default_factory=list)

    @property
    def should_block(self) -> bool:
        return any(v.severity == "block" for v in self.violations)


class EthicsLinter:
    def __init__(self, rules_path: str):
        with open(rules_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.rules = self.config.get("rules", [])

    def run_pre(self, ctx: Dict[str, Any]) -> LintReport:
        return self._run_for_phase("pre", ctx)

    def run_post(self, ctx: Dict[str, Any]) -> LintReport:
        return self._run_for_phase("post", ctx)

    def _run_for_phase(self, phase: str, ctx: Dict[str, Any]) -> LintReport:
        report = LintReport(phase=phase)
        for rule in self.rules:
            when = (rule.get("when") or "both").lower()
            if when not in ("pre", "post", "both"):
                continue
            if when != phase and when != "both":
                continue

            cond = rule.get("condition", {})
            ctype = (cond.get("type") or "").lower()
            params = cond.get("params", {})
            ok, detail = self._eval_condition(ctype, params, ctx)
            if not ok:
                report.violations.append(
                    Violation(
                        rule_id=rule.get("id", "UNKNOWN"),
                        severity=(rule.get("severity") or "warn").lower(),
                        message=self._format_message(rule, detail),
                        remediation=rule.get("remediation"),
                    )
                )
        return report

    def _format_message(self, rule: Dict[str, Any], detail: str) -> str:
        name = rule.get("name", rule.get("id", "Regla"))
        desc = rule.get("description", "")
        if detail:
            return f"{name}: {desc} — {detail}"
        return f"{name}: {desc}"

    # === Evaluadores de condiciones ===
    def _eval_condition(self, ctype: str, params: Dict[str, Any], ctx: Dict[str, Any]):
        if ctype == "metric_drop_percent":
            return self._check_metric_drop_percent(params, ctx)
        if ctype == "min_links_per_node":
            return self._check_min_links_per_node(params, ctx)
        if ctype == "required_subnetwork":
            return self._check_required_subnetwork(params, ctx)
        if ctype == "expr":
            return self._check_expr(params, ctx)
        return True, f"Tipo de condición desconocido: {ctype} (ignorada)"

    def _check_metric_drop_percent(self, p: Dict[str, Any], ctx: Dict[str, Any]):
        metric = p.get("metric")
        max_drop = float(p.get("max_drop_percent", 0))
        baseline_src = (p.get("baseline_source") or "previous").lower()
        # ctx: {"metrics": {"previous": {"equity": 62}, "plan": {"equity": 55}}}
        prev = ctx.get("metrics", {}).get("previous", {}) or {}
        plan = ctx.get("metrics", {}).get("plan", {}) or {}
        if metric not in prev or metric not in plan:
            return True, f"Métrica {metric} no disponible en contexto (prev/plan)."
        prev_val = float(prev[metric])
        plan_val = float(plan[metric])
        if prev_val <= 0:
            return True, "Baseline cero/no válida; no se evalúa caída porcentual."
        drop = ((prev_val - plan_val) / prev_val) * 100.0
        if drop > max_drop:
            return (
                False,
                f"Caída {drop:.2f}% > {max_drop:.2f}% (prev={prev_val:.2f}, plan={plan_val:.2f}).",
            )
        return True, f"Caída {drop:.2f}% dentro de umbral (≤ {max_drop:.2f}%)."

    def _check_min_links_per_node(self, p: Dict[str, Any], ctx: Dict[str, Any]):
        min_deg = int(p.get("min_degree", 1))
        ignore_types = set((p.get("ignore_types") or []))
        # ctx["graph"] = {"nodes": [{"id":..., "type":...}], "edges": [{"u":..., "v":..., "tags": [...]}]}
        g = ctx.get("graph", {})
        nodes = g.get("nodes", [])
        edges = g.get("edges", [])
        deg = {n["id"]: 0 for n in nodes if n.get("type") not in ignore_types}
        for e in edges:
            u, v = e.get("u"), e.get("v")
            if u in deg:
                deg[u] += 1
            if v in deg:
                deg[v] += 1
        bad = [nid for nid, d in deg.items() if d < min_deg]
        if bad:
            return False, f"Nodos con grado < {min_deg}: {bad}"
        return True, "Todos los nodos cumplen el grado mínimo."

    def _check_required_subnetwork(self, p: Dict[str, Any], ctx: Dict[str, Any]):
        tag = p.get("tag")
        min_edges = int(p.get("min_edges", 1))
        g = ctx.get("graph", {})
        edges = g.get("edges", [])
        count = 0
        for e in edges:
            tags = set(e.get("tags") or [])
            if tag in tags:
                count += 1
        if count < min_edges:
            return (
                False,
                f"Se requieren ≥{min_edges} vínculos con tag '{tag}', encontrados: {count}.",
            )
        return True, f"Subred '{tag}' válida con {count} vínculos."

    def _check_expr(self, p: Dict[str, Any], ctx: Dict[str, Any]):
        # Espacio para expresiones avanzadas (opcional v0.4)
        return True, "expr no evaluada (placeholder)."
