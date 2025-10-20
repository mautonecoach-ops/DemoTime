import json, re, time
from typing import List, Dict, Any

def load_rules(path="ethics_rules.yaml") -> Dict[str, Any]:
    try:
        import yaml, os
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def lint_plan(norm_source: str, ast: Any, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []

    # 1) fracción máxima en redistribuciones (heurística textual)
    max_frac = float(rules.get("max_redistribute_fraction", 0.35))
    for m in re.finditer(r"(fraction|fracci[oó]n)\s*=\s*([0-9]*\.?[0-9]+)", norm_source, re.IGNORECASE):
        frac = float(m.group(2))
        if frac > max_frac:
            violations.append({
                "code": "REDISTRIBUTE_FRACTION_EXCESS",
                "msg": f"Fracción {frac:.2f} excede máximo permitido {max_frac:.2f}.",
                "where": m.group(0)
            })

    # 2) exigir al menos un care_network si confianza inicial baja (heurístico)
    require_cn = rules.get("require_care_network_if_low_trust", None)
    if require_cn is not None:
        low_trust_decl = re.search(r"confianza:\s*([0-9]+)", norm_source)
        care_present = re.search(r"\bcare_network\b", norm_source) is not None
        if low_trust_decl:
            try:
                first_trust = float(low_trust_decl.group(1))
                if first_trust < float(require_cn) and not care_present:
                    violations.append({
                        "code": "MISSING_CARE_NETWORK",
                        "msg": f"Confianza inicial (~{first_trust:.0f}) < {require_cn}, se requiere al menos un 'care_network'.",
                        "where": "plan"
                    })
            except:
                pass

    # 3) prohibir recursos negativos explícitos
    if rules.get("forbid_negative_resources", True):
        for m in re.finditer(r"resources:\s*(-[0-9]*\.?[0-9]+)", norm_source):
            violations.append({
                "code": "NEGATIVE_RESOURCES",
                "msg": "Declaración de recursos negativos no permitida.",
                "where": m.group(0)
            })

    # 4) mínimo ético por nodo (declaraciones iniciales)
    min_res = float(rules.get("min_resource_per_node", 1.0))
    for m in re.finditer(r"resources:\s*([0-9]*\.?[0-9]+)", norm_source):
        val = float(m.group(1))
        if val < min_res:
            violations.append({
                "code": "NODE_BELOW_MIN_RESOURCE",
                "msg": f"Nodo declarado con resources={val:.2f} < mínimo ético {min_res:.2f}.",
                "where": m.group(0)
            })

    return violations

def write_lint_summary(violations: List[Dict[str, Any]], path="lint_summary.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"violations": violations}, f, ensure_ascii=False, indent=2)
# --- Wrapper simple para integrarse con main.py ---
def run_linter(ast, rules_path="ethics_rules.yaml", norm_source=None):
    """
    Carga reglas, corre lint_plan y persiste lint_summary.json.
    Acepta ast (oblig.), y opcionalmente norm_source si tu lint_plan lo usa.
    """
    try:
        rules = load_rules(rules_path) if 'load_rules' in globals() else {}
    except Exception:
        rules = {}

    # Soporta las dos firmas posibles de lint_plan (con o sin norm_source)
    try:
        violations = lint_plan(norm_source, ast, rules)  # firma (norm, ast, rules)
    except TypeError:
        violations = lint_plan(ast, rules)               # firma (ast, rules)

    if 'write_lint_summary' in globals():
        write_lint_summary(violations, "lint_summary.json")
    else:
        # fallback mínimo
        import json, time
        with open("lint_summary.json", "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "violations": violations,
                       "count": len(violations)}, f, ensure_ascii=False, indent=2)

    if violations:
        print(f"[LINTER] ⚠️ {len(violations)} advertencias/violaciones:")
        for v in violations:
            if isinstance(v, dict) and "msg" in v:
                print("  -", v["msg"])
            else:
                print("  -", v)
    else:
        print("[LINTER] ✅ Sin violaciones.")
    return violations
