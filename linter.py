import re, json, time
from typing import Any, Dict, List, Tuple

# Alias de tipo prolijo
Violation = Dict[str, Any]

def v(code: str, msg: str, **meta: Any) -> Violation:
    return {"code": code, "msg": msg, **meta}

def _write_lint_summary(violations: List[Violation], path: str = "lint_summary.json") -> None:
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(violations),
        "violations": violations,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def load_rules(path="ethics_rules.yaml") -> Dict[str, Any]:
    try:
        import yaml, os
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def _parse_nodes_from_source(norm_source: str) -> Tuple[List[float], List[float]]:
    """
    Extrae listas de confianzas y recursos iniciales a partir de líneas tipo:
      crear_nodo comunidad("Barrio Sur") { confianza: 45, resources: 30 }
      crear_nodo persona("Ayla")  { confianza: 40, resources: 1 }
    """
    trusts: List[float] = []
    resources: List[float] = []
    if not norm_source:
        return trusts, resources

    node_re = re.compile(
        r'crear_nodo\s+(?:comunidad|persona)\s*\(\s*".*?"\s*\)\s*\{\s*([^}]*)\}',
        re.IGNORECASE
    )
    kv_re = re.compile(r'([a-zA-Z_áéíóúñ]+)\s*:\s*([0-9]*\.?[0-9]+)', re.IGNORECASE)

    for m in node_re.finditer(norm_source):
        body = m.group(1)
        kvs = dict((k.lower(), float(v)) for k, v in kv_re.findall(body))
        if "confianza" in kvs:
            trusts.append(kvs["confianza"])
        if "resources" in kvs:
            resources.append(kvs["resources"])
    return trusts, resources

def _max_share(values: List[float]) -> float:
    s = sum(values)
    return (max(values) / s) if (values and s > 0) else 0.0

def lint_plan(norm_source: str, ast: Any, rules: Dict[str, Any]) -> List[Violation]:
    violations: List[Violation] = []
    if norm_source is None:
        norm_source = ""

    # Parseo simple de confianzas/recursos iniciales
    trusts, resources = _parse_nodes_from_source(norm_source)

    # 1) fracción máxima en redistribuciones (heurística textual)
    try:
        max_frac = float(rules.get("max_redistribute_fraction", 0.35))
        for m in re.finditer(r"(fraction|fracci[oó]n)\s*=\s*([0-9]*\.?[0-9]+)", norm_source, re.IGNORECASE):
            frac = float(m.group(2))
            if frac > max_frac:
                violations.append(v(
                    "REDISTRIBUTE_FRACTION_EXCESS",
                    f"Fracción {frac:.2f} excede máximo permitido {max_frac:.2f}.",
                    where=m.group(0),
                    frac=frac,
                    max_allowed=max_frac,
                ))
    except Exception:
        pass

    # 2) exigir al menos un care_network si confianza inicial baja (heurístico)
    try:
        require_cn = rules.get("require_care_network_if_low_trust", None)
        if require_cn is not None:
            low_trust_decl = re.search(r"confianza:\s*([0-9]+)", norm_source)
            care_present = re.search(r"\bcare_network\b", norm_source) is not None
            if low_trust_decl:
                first_trust = float(low_trust_decl.group(1))
                if first_trust < float(require_cn) and not care_present:
                    violations.append(v(
                        "MISSING_CARE_NETWORK",
                        f"Confianza inicial (~{first_trust:.0f}) < {require_cn}, se requiere al menos un 'care_network'.",
                        where="plan",
                        first_trust=first_trust,
                        min_required=float(require_cn),
                    ))
    except Exception:
        pass

    # 3) prohibir recursos negativos explícitos
    try:
        if rules.get("forbid_negative_resources", True):
            for m in re.finditer(r"resources:\s*(-[0-9]*\.?[0-9]+)", norm_source):
                violations.append(v(
                    "NEGATIVE_RESOURCES",
                    "Declaración de recursos negativos no permitida.",
                    where=m.group(0),
                ))
    except Exception:
        pass

    # 4) mínimo ético por nodo (declaraciones iniciales)
    try:
        min_res = float(rules.get("min_resource_per_node", 1.0))
        for m in re.finditer(r"resources:\s*([0-9]*\.?[0-9]+)", norm_source):
            val = float(m.group(1))
            if val < min_res:
                violations.append(v(
                    "NODE_BELOW_MIN_RESOURCE",
                    f"Nodo declarado con resources={val:.2f} < mínimo ético {min_res:.2f}.",
                    where=m.group(0),
                    value=val,
                    min_required=min_res,
                ))
    except Exception:
        pass

    # 5) Confianza promedio mínima
    try:
        min_avg_trust = float(rules.get("min_avg_trust", 0))
        if trusts:
            avg_trust = sum(trusts) / len(trusts)
            if avg_trust < min_avg_trust:
                violations.append(v(
                    "LOW_AVG_TRUST",
                    f"Confianza promedio inicial {avg_trust:.1f} < mínimo {min_avg_trust:.1f}.",
                    avg_trust=avg_trust,
                    min_required=min_avg_trust,
                ))
    except Exception:
        pass

    # 6) Nodos con confianza muy baja
    try:
        low_node_trust = float(rules.get("low_node_trust", 0))
        very_low = [t for t in trusts if t < low_node_trust]
        if very_low:
            violations.append(v(
                "LOW_NODE_TRUST_COUNT",
                f"{len(very_low)} nodo(s) con confianza < {low_node_trust:.0f}.",
                count=len(very_low),
                threshold=low_node_trust,
            ))
    except Exception:
        pass

    # 7) Concentración de recursos
    try:
        max_conc = float(rules.get("max_resource_concentration", 1.0))
        if resources:
            share = _max_share(resources)
            if share > max_conc:
                violations.append(v(
                    "HIGH_RESOURCE_CONCENTRATION",
                    f"Concentración inicial de recursos {share*100:.1f}% > {max_conc*100:.0f}%.",
                    share=share,
                    max_allowed=max_conc,
                ))
    except Exception:
        pass
    # 8) exigir al menos un launch_initiative si hay baja confianza
    try:
        req_init = rules.get("require_initiative_if_low_trust", None)
        if req_init is not None:
            # ¿hay algún nodo con confianza < umbral?
            low_trust_any = re.search(r"confianza:\s*([0-9]+)", norm_source)
            has_initiative = re.search(r"\b(launch_initiative|lanzar_iniciativa)\b", norm_source, re.IGNORECASE) is not None
            if low_trust_any:
                trusts_declared = [float(x) for x in re.findall(r"confianza:\s*([0-9]+)", norm_source)]
                if trusts_declared and min(trusts_declared) < float(req_init) and not has_initiative:
                    violations.append({
                        "code": "MISSING_INITIATIVE_LOW_TRUST",
                        "msg": f"Confianzas iniciales bajas (<{req_init}) y no hay 'launch_initiative'.",
                        "where": "plan"
                    })
    except Exception:
        pass

    # 9) exigir al menos N strengthen_ties si hay baja confianza
    try:
        req_strengthen = int(rules.get("min_strengthen_actions_if_low_trust", 0))
        if req_strengthen > 0:
            trusts_declared = [float(x) for x in re.findall(r"confianza:\s*([0-9]+)", norm_source)]
            strengthen_count = len(re.findall(r"\b(strengthen_ties|fortalecer_vínculos)\b", norm_source, re.IGNORECASE))
            if trusts_declared and min(trusts_declared) < float(rules.get("require_initiative_if_low_trust", 999)):
                if strengthen_count < req_strengthen:
                    violations.append({
                        "code": "INSUFFICIENT_STRENGTHEN_TIES",
                        "msg": f"Se requieren ≥{req_strengthen} strengthen_ties por baja confianza; encontrados {strengthen_count}.",
                        "where": "plan"
                    })
    except Exception:
        pass

    return violations

# --- Wrapper simple para integrarse con main.py ---
def run_linter(ast, rules_path: str = "ethics_rules.yaml", norm_source: str | None = None) -> List[Violation]:
    rules = load_rules(rules_path)
    violations = lint_plan(norm_source or "", ast, rules)

    # Fallback por si vinieran strings (no debería ocurrir ya)
    if violations and isinstance(violations[0], str):  # type: ignore[index]
        violations = [{"code": "GENERIC", "msg": m} for m in violations]  # type: ignore[assignment]

    _write_lint_summary(violations)
    if violations:
        print(f"[LINTER] ⚠️ {len(violations)} violación(es):")
        for it in violations:
            print("  -", it.get("msg", str(it)))
    else:
        print("[LINTER] ✅ Sin violaciones.")
    return violations
