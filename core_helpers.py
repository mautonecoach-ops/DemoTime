# core_helpers.py
import os, json, csv, time, hashlib, yaml

# ---------- RUN LIFECYCLE ----------
def begin_run():
    ts = time.strftime("%Y%m%d-%H%M%S")
    return f"run_{ts}"

def end_run(run_id, ok=True):
    # lugar para hooks de cierre si los necesitás
    pass

# ---------- EXPORT HELPERS ----------
def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def append_changelog(status, metrics, fails, path="CHANGELOG.md"):
    line = f"- {time.strftime('%Y-%m-%d %H:%M:%S')} exec-final: {status} | "
    line += f"trust={metrics.get('trust',0):.2f} cohesion={metrics.get('cohesion',0):.2f} equity={metrics.get('equity',0):.2f}"
    if fails:
        detail = " ; ".join([f"{m}={v:.2f} < {r:.2f}" for (m, v, r) in fails])
        line += f" | fails: {detail}"
    line += "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)

def append_changelog_lint(status: str, count: int, path="CHANGELOG.md"):
    import time
    line = f"- {time.strftime('%Y-%m-%d %H:%M:%S')} lint-pre: {status}"
    if count:
        line += f" | {count} violación(es)"
    line += "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def write_csv_rows(path, rows, header=None):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if header and not exists:
            w.writerow(header)
        for r in rows:
            w.writerow(r)

# ---------- ETHICS / BLOCKER ----------
def load_ethics_thresholds(path="ethics.yaml"):
    if not os.path.exists(path):
        return {"min_trust": 60.0, "min_cohesion": 50.0, "min_equity": 60.0}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "min_trust": float(data.get("min_trust", 60.0)),
        "min_cohesion": float(data.get("min_cohesion", 50.0)),
        "min_equity": float(data.get("min_equity", 60.0)),
    }

def blocker_decision(metrics, thresholds):
    fails = []
    if metrics.get("trust", 0)    < thresholds["min_trust"]:    fails.append(("trust",    metrics.get("trust",0),    thresholds["min_trust"]))
    if metrics.get("cohesion", 0) < thresholds["min_cohesion"]: fails.append(("cohesion", metrics.get("cohesion",0), thresholds["min_cohesion"]))
    if metrics.get("equity", 0)   < thresholds["min_equity"]:   fails.append(("equity",   metrics.get("equity",0),   thresholds["min_equity"]))
    return fails

def write_blockade_summary(run_id, metrics, thresholds, fails):
    payload = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": metrics,
        "thresholds": thresholds,
        "status": "BLOCKED" if fails else "OK",
        "fails": [{"metric": m, "value": v, "required": r} for (m, v, r) in fails],
    }
    write_json("blockade_summary.json", payload)

# ---------- WHAT-IF (placeholder para v0.2) ----------
def ensure_whatif_never_mutates(rt):
    # Aquí podemos validar que WHAT_IF no alteró estado real (placeholder)
    return True

# core_helpers.py — extractores de contexto para el linter v0.4
from typing import Any, Dict

# Estas funciones suponen que ya parseaste el input .lexo a un AST/IR
# y que contás con métricas base (previous) y proyectadas (plan).

def build_lint_context(ast_ir: Dict[str, Any], baseline_metrics: Dict[str, float], planned_metrics: Dict[str, float]) -> Dict[str, Any]:
    graph = _graph_from_ast(ast_ir)
    ctx = {
        "graph": graph, # {nodes:[{id,type,...}], edges:[{u,v,tags:[...]}, ...]}
        "metrics": {
            "previous": baseline_metrics,
            "plan": planned_metrics,
        },
        # Lugar para extras: usuarios, flags, features
        "features": {
            "care_network_tag": "care_network",
        },
    }
    return ctx

def _graph_from_ast(ast_ir: Dict[str, Any]) -> Dict[str, Any]:
    nodes = []
    edges = []
    for n in ast_ir.get("nodes", []):
        nodes.append({
            "id": n.get("name"),
            "type": n.get("type"),
            **({k: v for k, v in n.items() if k not in ("name", "type")}),
        })
    for r in ast_ir.get("relations", []):
        edges.append({
            "u": r.get("source"),
            "v": r.get("target"),
            "tags": list(set(r.get("tags", []))),
        })
    return {"nodes": nodes, "edges": edges}