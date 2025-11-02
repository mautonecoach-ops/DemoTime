# LEXO v0.1 – MVP monolítico
# Ejecutar: python main.py demo_es.lexo --lang=es
#           python main.py demo_en.lexo --lang=en
# Flags globales de control

# =========================
# IMPORTS
# =========================
from linter import EthicsLinter 
from core_helpers import append_changelog_lint
from core_helpers import build_lint_context

# Standard library
import sys
import os
import re
import json
import math
import networkx as nx
import matplotlib
import time
import random

matplotlib.use("Agg")  # evita crash por display en Replit
import matplotlib.pyplot as plt
import warnings
import argparse
import hashlib

from core_helpers import (
    begin_run, end_run,
    load_ethics_thresholds, blocker_decision,
    write_blockade_summary, append_changelog, ensure_whatif_never_mutates,
)


warnings.filterwarnings(
    "ignore",
import time
import random

# Silenciar warning de matplotlib/tight_layout
warnings.filterwarnings(
    "ignore",
    message="This figure includes Axes that are not compatible with tight_layout",
    category=UserWarning,
)

RUN_TS = time.strftime("%Y-%m-%d %H:%M:%S")
random.seed(42)

# =========================
# FLAGS DE DEBUG (on/off)
# =========================
DEBUG_MAIN = False       # prints en main()
DEBUG_ACTIONS = False    # prints en acciones (execute/Runtime)
DEBUG_MEASURE = False    # prints en métricas (Runtime.measure)
DEBUG_WHATIF = False     # silencia dentro de WHAT_IF

# =========================
# Globals y helpers ETHICS (mínimo)
# =========================
# ======= Globals (colocá esto una sola vez, cerca del tope del archivo) =======
WHATIF_LOG: list[dict] = []
WHATIF_SAVED: bool = False
NO_WHATIF_TABLE: bool = False
WHATIF_DIMS: list[str] | None = None
SORT_WHATIF_BY: str | None = None  # "trust" | "cohesion" | "equity" | None

# Globals (arriba del archivo, junto a los otros)
WHATIF_TABLE_PRINTED = False
WHATIF_TABLE_REQUESTED = False

# ===== FLAGS GLOBALES =====

MEASURE_INCLUDE_COMMUNITY = True

ETHICS = {}  # se completa desde ethics.yaml
ETHICS_LOADED = False  # para no cargar dos veces
ETHICS_ALREADY_EMITTED = False  # para no imprimir alertas duplicadas


# =========================
# FUNCIONES DE SOPORTE
# =========================
def apply_ethics_yaml_once(path="ethics.yaml"):
    global ETHICS_LOADED, ETHICS
    if ETHICS_LOADED:
        return
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if isinstance(data, dict) and data:
            ETHICS.update(data)
            
    except Exception:
        pass
    ETHICS_LOADED = True


def print_alerts(alerts):
    """
    Imprime alertas éticas una sola vez y sin duplicados de contenido.
    """
    global ETHICS_ALREADY_EMITTED
    if ETHICS_ALREADY_EMITTED:
        return
    if not alerts:
        ETHICS_ALREADY_EMITTED = True
        return
    seen = set()
    for a in alerts:
        base = a.split(" Sugerencia:")[0]
        if base in seen:
            continue
        seen.add(base)
        print(a)
    ETHICS_ALREADY_EMITTED = True


# =========================
# i18n: ES <-> EN mapeos
# =========================
TOKEN_MAP = {
    "es": {
        # comandos
        r"\bcrear_nodo\b": "CREATE_NODE",
        r"\bconectar\b": "CONNECT",
        r"\bintervenir_si\b": "INTERVENE_IF",
        r"\bcontribuir_sino\b": "CONTRIBUTE_ELSE",
        r"\blanzar_iniciativa\b": "LAUNCH_INITIATIVE",
        r"\bfortalecer_vínculos\b": "STRENGTHEN_TIES",
        r"\bfortalecer_vinculos\b": "STRENGTHEN_TIES",
        r"\bmedir_impacto\b": "MEASURE_IMPACT",
        r"\bmostrar_red\b": "SHOW_NETWORK",
        r"\bwhat_if\b": "WHAT_IF",
        r"\bque_pasa_si\b": "WHAT_IF",
        r"\baplicar\b": "APPLY",
        r"\bapply\b": "APPLY",
        r"\bcomparar\b": "COMPARE",
        r"\bcompare\b": "COMPARE",

        # entidades/tipos
        r"\bpersona\b": "PERSON",
        r"\bcomunidad\b": "COMMUNITY",
        r"\borganización\b": "ORGANIZATION",
        r"\borganizacion\b": "ORGANIZATION",
        r"\brecurso\b": "RESOURCE",

        # atributos frecuentes
        r"\bconfianza\b": "trust",
        r"\bcohesión\b": "cohesion",
        r"\bcohesion\b": "cohesion",
        r"\bequidad\b": "equity",
        r"\benergía\b": "energy",
        r"\benergia\b": "energy",
        r"\bintensidad\b": "intensity",
        r"\bcompromiso\b": "commitment",
        r"\bredistribuir_recursos\b": "REDISTRIBUTE_RESOURCES",
        r"\bcuidar_red\b": "CARE_NETWORK",
        r"\bplan_mitigación\b": "mitigation_plan",
        r"\bplan_mitigacion\b": "mitigation_plan",
        r"\brecursos\b": "resources",

        # constantes ejemplo
        r"\bALTO\b": "HIGH",
        r"\bMEDIA\b": "MEDIUM",
        r"\bALTA\b": "HIGH",
        r"\bBAJA\b": "LOW",
        r"\bBAJO\b": "LOW",

        # sintaxis de medición
        r"\ben dimensión\(": "on dimension(",
        r"\bendimensión\(": "on dimension(",  # por si queda pegado
        r"\ben\b": "IN",
        r"\bdimensión\b": "DIMENSION",
        r"\bdimension\b": "DIMENSION",
    },
    "en": {
        r"\bcreate_node\b": "CREATE_NODE",
        r"\bconnect\b": "CONNECT",
        r"\bintervene_if\b": "INTERVENE_IF",
        r"\bcontribute_else\b": "CONTRIBUTE_ELSE",
        r"\blaunch_initiative\b": "LAUNCH_INITIATIVE",
        r"\bstrengthen_ties\b": "STRENGTHEN_TIES",
        r"\bmeasure_impact\b": "MEASURE_IMPACT",
        r"\bshow_network\b": "SHOW_NETWORK",
        r"\bwhat_if\b": "WHAT_IF",
        r"\bque_pasa_si\b": "WHAT_IF",
        r"\baplicar\b": "APPLY",
        r"\bapply\b": "APPLY",
        r"\bcomparar\b": "COMPARE",
        r"\bcompare\b": "COMPARE",
        r"\bperson\b": "PERSON",
        r"\bcommunity\b": "COMMUNITY",
        r"\borganization\b": "ORGANIZATION",
        r"\bresource\b": "RESOURCE",
        r"\btrust\b": "trust",
        r"\bcohesion\b": "cohesion",
        r"\bequity\b": "equity",
        r"\benergy\b": "energy",
        r"\bintensity\b": "intensity",
        r"\bcommitment\b": "commitment",
        r"\bredistribute_resources\b": "REDISTRIBUTE_RESOURCES",
        r"\bcare_network\b": "CARE_NETWORK",
        r"\bmitigation_plan\b": "mitigation_plan",
        r"\bresources\b": "resources",
        r"\bHIGH\b": "HIGH",
        r"\bMEDIUM\b": "MEDIUM",
        r"\bLOW\b": "LOW",
        r"\bon dimension\(": "on dimension(",
    }
}

# =========================
# Utilidad: normalizar código por idioma -> tokens canónicos
# =========================
# Debe existir TOKEN_MAP con claves "es"/"en" y patrones -> tokens
COMMENT = r"//.*?$"


def strip_line_comments(s: str) -> str:
    return re.sub(COMMENT, "", s, flags=re.M)


def normalize_source(text: str, lang: str) -> str:
    s = strip_line_comments(text)
    # normalizar saltos de línea y espacios
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # aplicar mapeos de idioma (si existen)
    mapping = TOKEN_MAP.get(lang, {})
    for pat, repl in mapping.items():
        s = re.sub(pat, repl, s, flags=re.I | re.M)
    # opcional: colapsar espacios extra
    s = re.sub(r"[ \t]+", " ", s)
    return s


def lint_compare(prev_metrics, new_metrics):
    """Retorna lista de strings con alertas éticas."""
    alerts = []
    if prev_metrics and new_metrics:
        # 1) caída de confianza
        t0, t1 = prev_metrics["trust"], new_metrics["trust"]
        if t0 > 0:
            drop_pct = max(0.0, (t0 - t1) * 100.0 / t0)
            if drop_pct > ETHICS["max_trust_drop_pct"]:
                alerts.append(
                    f"[ETHICS] La confianza cayó {drop_pct:.1f}% (> {ETHICS['max_trust_drop_pct']}%). Revisar la intervención."
                )

        # 2) equidad mínima
        if new_metrics["equity"] < ETHICS["min_equity_score"]:
            alerts.append(
                f"[ETHICS] La equidad bajó a {new_metrics['equity']:.1f} (< {ETHICS['min_equity_score']}). Riesgo de concentración de recursos."
            )
    return alerts


def lint_compare_v2(prev_snap, new_snap, prev_m, new_m):
    alerts = []

    # --- Reglas incrementales (comparan antes vs después) ---
    # 1) Caída fuerte en algún vínculo
    for e, prev_t in prev_snap["edges"].items():
        new_t = new_snap["edges"].get(e, prev_t)
        if prev_t - new_t > ETHICS["max_edge_trust_drop"]:
            u, v = e
            alerts.append(
                f"[ETHICS] El vínculo {u}–{v} perdió {prev_t-new_t:.1f} pts (> {ETHICS['max_edge_trust_drop']}). "
                f"Sugerencia: cuidar_red('{u}' o '{v}', intensity=ALTA).")

    # 2) Aumento de inequidad (gini)
    if prev_snap["gini"] > 0:
        inc_pct = (new_snap["gini"] -
                   prev_snap["gini"]) * 100.0 / prev_snap["gini"]
        if inc_pct > ETHICS["max_gini_increase_pct"]:
            alerts.append(
                f"[ETHICS] La inequidad de recursos subió {inc_pct:.1f}% (> {ETHICS['max_gini_increase_pct']}). "
                f"Sugerencia: redistribuir_recursos(..., fraction=0.1–0.3, min_left=2)."
            )

    # --- Reglas absolutas (estado actual) ---
    # 3) Confianza promedio mínima
    if new_m["trust"] < ETHICS["min_avg_trust"]:
        alerts.append(
            f"[ETHICS] La confianza promedio es {new_m['trust']:.1f} (< {ETHICS['min_avg_trust']}). "
            f"Sugerencia: fortalecer_vínculos(target='comunidad', intensidad=MEDIA/ALTA) o lanzar_iniciativa."
        )

    # 4) Nodos con confianza muy baja
    low_nodes = [
        n for n, t in new_snap["node_trust"].items()
        if t < ETHICS["low_node_trust"]
    ]
    if low_nodes:
        sample = ", ".join(list(low_nodes)[:3])
        alerts.append(
            f"[ETHICS] Nodos con confianza muy baja (<{ETHICS['low_node_trust']}): {sample}..."
            f" Sugerencia: cuidar_red(target), mentorías o pequeñas victorias visibles."
        )

    # 5) Vínculos con confianza muy baja
    low_edges = [(u, v) for (u, v), t in new_snap["edges"].items()
                 if t < ETHICS["low_edge_trust"]]
    if low_edges:
        u, v = low_edges[0]
        alerts.append(
            f"[ETHICS] Hay vínculos con confianza muy baja (<{ETHICS['low_edge_trust']}), ej. {u}–{v}. "
            f"Sugerencia: cuidar_red('{u}' o '{v}', intensity=MEDIA/ALTA).")

    # 6) Nodos aislados / grado insuficiente
    isolated = [
        n for n, d in new_snap["degrees"].items()
        if d < ETHICS["min_node_degree"]
    ]
    if isolated:
        sample = ", ".join(list(isolated)[:3])
        alerts.append(
            f"[ETHICS] Nodos aislados o casi aislados: {sample}..."
            f" Sugerencia: conectar(nodo, 'Barrio Sur') o introducir puentes.")

    # 7) Recursos por debajo del mínimo
    starved = [
        n for n, r in new_snap["res_by_node"].items()
        if r < ETHICS["min_resources_per_node"]
    ]
    if starved:
        sample = ", ".join(list(starved)[:3])
        alerts.append(
            f"[ETHICS] Nodos con recursos insuficientes (<{ETHICS['min_resources_per_node']}): {sample}..."
            f" Sugerencia: redistribuir_recursos(dador, '{starved[0]}', fraction=0.1–0.3)."
        )

    # 8) Concentración excesiva (antimonopolio de recursos)
    if new_snap["top_share"] > ETHICS["max_resource_share"]:
        alerts.append(
            f"[ETHICS] Un nodo concentra {new_snap['top_share']*100:.1f}% de los recursos (> {ETHICS['max_resource_share']*100:.0f}%). "
            f"Sugerencia: redistribuir_recursos(dador_rico, receptor_con_menos, fraction=0.15–0.30)."
        )

    # 9) Reglas v0.1
    alerts += lint_compare(prev_m, new_m)
    return alerts


import json, csv, os


def save_report_json(final_m, alerts, whatifs, path=None):
    # Usa el mismo RUN_ID para trazabilidad conjunta
    if path is None:
        path = f"run_{RUN_ID}.json"

    payload = {
        "run_ts": RUN_ID,
        "final_metrics": final_m,
        "ethics_alerts": alerts,
        "what_if": whatifs,
        "artifacts": {
            "network_png": f"network_{RUN_ID}.png",
            "whatif_json": f"whatif_{RUN_ID}.json",
            "whatif_csv": f"whatif_{RUN_ID}.csv"
        }
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[OK] Reporte JSON guardado en {path}")
    except Exception as e:
        print(f"[WARN] No se pudo guardar {path}: {e}")


def save_report_csv(metrics, alerts=None, path="report.csv"):
    with open(path, "w", newline="", encoding="utf-8") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["trust", "cohesion", "equity"])
        writer.writerow(
            [metrics["trust"], metrics["cohesion"], metrics["equity"]])
        if alerts:
            writer.writerow([])
            writer.writerow(["ALERTS"])
            for a in alerts:
                writer.writerow([a])
    print(f"[OK] Reporte CSV actualizado en {path}")


def save_whatif_json(path="whatif.json"):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(WHATIF_LOG, f, ensure_ascii=False, indent=2)
        print(f"[OK] WHAT_IF JSON guardado en {path}")
    except Exception as e:
        print(f"[WARN] No se pudo guardar {path}: {e}")


def save_whatif_csv(path: str = "whatif.csv") -> None:
    try:
        import csv
        # Columnas dinámicas según lo que haya en los deltas
        dims = set()
        for item in WHATIF_LOG:
            dims.update(item.get("deltas", {}).keys())
        ordered = ["trust", "cohesion", "equity"] + sorted(
            d for d in dims if d not in ("trust", "cohesion", "equity"))

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["title"] + ordered)
            for item in WHATIF_LOG:
                row = [item.get("title", "(sin título)")]
                d = item.get("deltas", {})
                row += [d.get(k, "") for k in ordered]
                writer.writerow(row)

        print(f"[OK] WHAT_IF CSV actualizado en {path}")
    except Exception as e:
        print(f"[WARN] No se pudo guardar {path}: {e}")

def evaluate_ethics(rt, start_snap, final_snap, start_metrics, final_metrics):
    """
    Wrapper del linter ético v2: compara estado inicial vs final y devuelve lista de alertas.
    """
    # Asume que tenés lint_compare_v2(prev_snap, new_snap, prev_m, new_m) ya definido.
    return lint_compare_v2(start_snap, final_snap, start_metrics,
                           final_metrics)


# =========================
# Parser súper simple para el MVP
# - reconoce bloques por llaves
# - reconoce las sentencias clave por prefix
# =========================
_bool_like = {"true": True, "false": False, "TRUE": True, "FALSE": False}
_ident_like = {
    "ALTO": "HIGH",
    "MEDIA": "MEDIUM",
    "BAJA": "LOW",
    "ALTA": "HIGH",
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW"
}


def _parse_number(tok: str):
    try:
        if "." in tok:
            return float(tok)
        return int(tok)
    except:
        return None


def _parse_list(text: str):
    # lista simple: ["a","b"] o [1,2,3] o [ a , b ]
    inner = text.strip()[1:-1]  # sin [ ]
    if inner.strip() == "":
        return []
    items = []
    # separar por comas, tolerando espacios
    parts = [p.strip() for p in inner.split(",")]
    for p in parts:
        if len(p) >= 2 and ((p[0] == '"' and p[-1] == '"') or
                            (p[0] == "'" and p[-1] == "'")):
            items.append(p[1:-1])
        else:
            num = _parse_number(p)
            if num is not None:
                items.append(num)
            elif p in _bool_like:
                items.append(_bool_like[p])
            else:
                items.append(p)  # identificador libre
    return items


def _parse_value(raw: str):
    s = raw.strip()
    # cadena
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or
                        (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]
    # lista
    if s.startswith("[") and s.endswith("]"):
        return _parse_list(s)
    # número
    num = _parse_number(s)
    if num is not None:
        return num
    # booleano
    if s in _bool_like:
        return _bool_like[s]
    # identificador (ALTO/MEDIA/BAJA/HIGH/…)
    if s in _ident_like:
        return _ident_like[s]
    return s  # fallback


def parse_properties(block_text: str) -> dict:
    """
    Parsea 'key: value, key2: value2' dentro de un bloque {...}
    Soporta:
      - strings con comillas simples o dobles (con escapes)
      - listas [ ... ] con elementos heterogéneos
      - números, true/false, null
      - enums/identificadores sin comillas (p.ej. ALTA, MEDIA)
      - comentarios // hasta fin de línea
      - comas finales y espacios/saltos de línea
    Devuelve dict con valores en tipos nativos cuando aplica.
    """
    s = block_text.strip()
    i, n = 0, len(s)
    props = {}

    def skip_ws_and_comments(k: int) -> int:
        nonlocal s, n
        while k < n:
            # espacios/blancos
            while k < n and s[k] in " \t\r\n":
                k += 1
            # comentario //
            if k + 1 < n and s[k] == '/' and s[k + 1] == '/':
                k += 2
                while k < n and s[k] != '\n':
                    k += 1
                continue
            break
        return k

    def parse_string(k: int) -> tuple[str, int]:
        quote = s[k]
        assert quote in ("'", '"')
        k += 1
        buf = []
        while k < n:
            ch = s[k]
            if ch == '\\' and k + 1 < n:
                # escape
                nxt = s[k + 1]
                if nxt in ['\\', '"', "'"]:
                    buf.append(nxt)
                    k += 2
                    continue
                # escapes comunes \n \t \r
                if nxt == 'n':
                    buf.append('\n')
                    k += 2
                    continue
                if nxt == 't':
                    buf.append('\t')
                    k += 2
                    continue
                if nxt == 'r':
                    buf.append('\r')
                    k += 2
                    continue
                # por defecto, conserva el char escapado
                buf.append(nxt)
                k += 2
                continue
            if ch == quote:
                k += 1
                return ''.join(buf), k
            buf.append(ch)
            k += 1
        # si no cerró, retorna lo acumulado
        return ''.join(buf), k

    def parse_number_bool_null(k: int):
        # intenta número
        j = k
        has_dot = False
        if j < n and s[j] in "+-":
            j += 1
        while j < n and (s[j].isdigit() or s[j] == '.'):
            if s[j] == '.':
                if has_dot: break
                has_dot = True
            j += 1
        token = s[k:j]
        if token and any(ch.isdigit() for ch in token):
            try:
                if '.' in token:
                    return float(token), j
                else:
                    return int(token), j
            except ValueError:
                pass
        # intenta true/false/null (case-insensitive)
        idt, j2 = parse_identifier(k)
        low = idt.lower()
        if low == "true": return True, j2
        if low == "false": return False, j2
        if low == "null": return None, j2
        # si no, devuelve el identificador tal cual (enum/label)
        return idt, j2

    def parse_identifier(k: int) -> tuple[str, int]:
        j = k
        # Identificador flexible hasta separador de valor (coma, fin de lista/objeto)
        while j < n and s[j] not in ",]\n\r\t}":
            # cortamos si vemos inicio de comentario
            if j + 1 < n and s[j] == '/' and s[j + 1] == '/':
                break
            j += 1
        token = s[k:j].strip()
        return token, j

    def parse_value(k: int):
        k = skip_ws_and_comments(k)
        if k >= n:
            return None, k
        ch = s[k]
        # string
        if ch in ("'", '"'):
            return parse_string(k)
        # lista
        if ch == '[':
            lst = []
            k += 1
            while True:
                k = skip_ws_and_comments(k)
                if k >= n:
                    break
                if s[k] == ']':
                    k += 1
                    break
                val, k = parse_value(k)
                lst.append(val)
                k = skip_ws_and_comments(k)
                if k < n and s[k] == ',':
                    k += 1
                    continue
                # permite coma final opcional
                k = skip_ws_and_comments(k)
                if k < n and s[k] == ']':
                    k += 1
                    break
            return lst, k
        # número / boolean / null / identificador
        return parse_number_bool_null(k)

    def parse_key(k: int) -> tuple[str, int]:
        k = skip_ws_and_comments(k)
        if k >= n:
            return "", k
        if s[k] in ('"', "'"):
            key, k = parse_string(k)
            return key.strip(), k
        # hasta ':'
        j = k
        while j < n and s[j] != ':':
            # corta si aparece comentario
            if j + 1 < n and s[j] == '/' and s[j + 1] == '/':
                break
            j += 1
        key = s[k:j].strip()
        return key, j

    # bucle principal: key:value [, key:value]*
    while True:
        i = skip_ws_and_comments(i)
        if i >= n or s[i] == '}':
            break
        key, i = parse_key(i)
        if not key:
            # sin clave, intenta avanzar para no quedar pegado
            i += 1
            continue
        i = skip_ws_and_comments(i)
        if i < n and s[i] == ':':
            i += 1
        i = skip_ws_and_comments(i)
        val, i = parse_value(i)
        props[key] = val
        i = skip_ws_and_comments(i)
        if i < n and s[i] == ',':
            i += 1
            continue
        # permite fin de objeto implícito
        i = skip_ws_and_comments(i)
        if i < n and s[i] == '}':
            break

    return props


def skip_ws_and_comments(src, i):
    n = len(src)
    while i < n:
        c = src[i]
        # espacios
        if c.isspace():
            i += 1
            continue
        # comentarios tipo //
        if i + 1 < n and src[i] == "/" and src[i + 1] == "/":
            i += 2
            while i < n and src[i] != "\n":
                i += 1
            continue
        # comentarios tipo #
        if c == "#":
            while i < n and src[i] != "\n":
                i += 1
            continue
        break
    return i


# Debe existir TOKEN_MAP con claves "es"/"en" y patrones -> tokens
COMMENT = r"//.*?$"


def load_ethics_from_yaml(path="ethics.yaml"):
    try:
        import yaml  # asegurate de tener PyYAML
    except ImportError:
        return None
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception as e:
        print(f"[WARN] No se pudo leer {path}: {e}")
        return None


class Node:

    def __init__(self, kind, name, props=None):
        self.kind = kind  # PERSON / COMMUNITY / ORGANIZATION / RESOURCE
        self.name = name
        self.props = props or {}

    def __repr__(self):
        return f"<{self.kind}:{self.name} {self.props}>"


class AST:

    def __init__(self):
        self.decls = []
        self.actions = []


# parsing helpers
ETHICS = {
    "max_trust_drop_pct": 10.0,  # alerta si cae >10% la confianza promedio
    "min_equity_score": 60.0,  # alerta si la equidad baja de 60/100
}
ETHICS.update({
    "max_edge_trust_drop": 20.0,  # alerta si algún vínculo cae >20 pts
    "max_gini_increase_pct": 10.0,  # alerta si la inequidad (gini) sube >10%
    "min_avg_trust": 60.0,  # alerta si la confianza promedio cae por debajo
    "low_node_trust": 55.0,  # si algún nodo queda con confianza muy baja
    "low_edge_trust": 50.0,  # si algún vínculo queda con confianza muy baja
    "min_node_degree": 1,  # nodos aislados o con grado 0/1 llaman la atención
    "min_resources_per_node": 2.0,  # umbral mínimo de recursos por nodo
    "max_resource_share":
    0.50,  # si un solo nodo concentra >40% de los recursos
})

WS = r"[ \t]*"
IDENT = r"[A-Za-zÁÉÍÓÚáéíóúÑñ_][A-Za-z0-9ÁÉÍÓÚáéíóúÑñ_\- ]*"


def startswith_token(src: str, i: int, token: str) -> bool:
    if not src.startswith(token, i):
        return src[i:].upper().startswith(token.upper())
    # límite por la izquierda
    if i > 0 and (src[i - 1].isalnum() or src[i - 1] == "_"):
        return False
    # límite por la derecha
    j = i + len(token)
    if j < len(src) and (src[j].isalnum() or src[j] == "_"):
        return False
    return True


def extract_block(src: str, start_idx: int):
    """
    Extrae el bloque {...} empezando EXACTAMENTE en start_idx apuntando a '{'.
    Devuelve (block_text, end_index), donde:
      - block_text es el contenido interno SIN las llaves externas
      - end_index es el índice del primer carácter DESPUÉS de la '}' que cierra el bloque
    Soporta:
      * Anidación de llaves
      * Strings '...' y "..." con escapes
      * Comentarios // línea y /* bloque */
    """
    n = len(src)
    if start_idx < 0 or start_idx >= n:
        raise ValueError("extract_block: start_idx fuera de rango")
    if src[start_idx] != "{":
        raise ValueError("extract_block: se esperaba '{'")

    i = start_idx + 1
    depth = 1
    block_start = i

    in_string = False
    quote_char = None  # "'" o '"'
    escape = False

    while i < n:
        ch = src[i]

        # Dentro de string: solo salimos al cerrar comillas que no estén escapadas
        if in_string:
            if escape:
                escape = False
                i += 1
                continue
            if ch == "\\":
                escape = True
                i += 1
                continue
            if ch == quote_char:
                in_string = False
                quote_char = None
                i += 1
                continue
            i += 1
            continue

        # Fuera de string: manejar comentarios
        if ch == "/":
            # comentario de línea //
            if i + 1 < n and src[i + 1] == "/":
                i += 2
                while i < n and src[i] not in ("\n", "\r"):
                    i += 1
                continue
            # comentario de bloque /* ... */
            if i + 1 < n and src[i + 1] == "*":
                i += 2
                while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                    i += 1
                if i + 1 >= n:
                    raise ValueError(
                        "extract_block: comentario de bloque sin cierre '*/'")
                i += 2
                continue

        # Abrir string
        if ch == "'" or ch == '"':
            in_string = True
            quote_char = ch
            escape = False
            i += 1
            continue

        # Manejar llaves
        if ch == "{":
            depth += 1
            i += 1
            continue
        if ch == "}":
            depth -= 1
            i += 1
            if depth == 0:
                # bloque completo
                block_text = src[block_start:i - 1]  # sin la llave de cierre
                end_index = i  # siguiente carácter tras la '}'
                return block_text, end_index
            continue

        # Avanzar en cualquier otro caso
        i += 1

    # Si salimos del while sin retornar, faltó '}' de cierre
    raise ValueError(
        "extract_block: no se encontró la '}' de cierre para el bloque que inicia en índice %d"
        % start_idx)


def extract_bracketed(src: str, start_idx: int, open_ch="[", close_ch="]"):
    """
    Extrae el contenido entre open_ch/close_ch empezando EXACTO en start_idx.
    Maneja anidación, strings y comentarios como extract_block.
    Devuelve (contenido_sin_bordes, end_index) donde end_index es el índice
    del primer char *después* del cierre.
    """
    n = len(src)
    if start_idx < 0 or start_idx >= n:
        raise ValueError("extract_bracketed: start_idx fuera de rango")
    if src[start_idx] != open_ch:
        raise ValueError(f"extract_bracketed: se esperaba '{open_ch}'")

    i = start_idx + 1
    depth = 1
    out = []
    in_string = False
    quote = None
    escape = False

    def skip_line_comment(i):
        while i < n and src[i] not in ("\n", "\r"):
            i += 1
        return i

    def skip_block_comment(i):
        # salta hasta '*/'
        i += 2
        while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
            i += 1
        if i + 1 >= n:
            raise ValueError(
                "extract_bracketed: comentario de bloque sin cierre '*/'")
        return i + 2

    while i < n:
        ch = src[i]

        if in_string:
            if escape:
                escape = False
                out.append(ch)
                i += 1
                continue
            if ch == "\\":
                escape = True
                out.append(ch)
                i += 1
                continue
            if ch == quote:
                in_string = False
                quote = None
                i += 1
                continue
            out.append(ch)
            i += 1
            continue

        # comentarios
        if ch == "/" and i + 1 < n:
            nxt = src[i + 1]
            if nxt == "/":
                i = skip_line_comment(i + 2)
                continue
            if nxt == "*":
                i = skip_block_comment(i)
                continue

        # strings
        if ch in ("'", '"'):
            in_string = True
            quote = ch
            i += 1
            continue

        # anidación
        if ch == open_ch:
            depth += 1
            out.append(ch)
            i += 1
            continue
        if ch == close_ch:
            depth -= 1
            i += 1
            if depth == 0:
                # devolvemos el contenido SIN los corchetes
                return "".join(out), i
            out.append(ch)
            continue

        out.append(ch)
        i += 1

    raise ValueError(
        f"extract_bracketed: no se encontró '{close_ch}' de cierre")


def extract_parens(src: str, start_idx: int):
    """
    Extrae el texto de un paréntesis balanceado (...) desde src[start_idx] == '('
    Retorna (contenido_sin_paréntesis, indice_despues_del_cierre)
    """
    assert src[start_idx] == "(", "extract_parens: se esperaba '('"
    i = start_idx + 1
    depth = 0
    start_content = i
    while i < len(src):
        c = src[i]
        if c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                content = src[start_content:i]
                return content, i + 1
            else:
                depth -= 1
        i += 1
    raise ValueError("extract_parens: paréntesis '(...)' sin cierre")


import unicodedata, re


def parse_two_quoted_args(arg_text: str):
    """Recibe el contenido dentro de CONNECT(...) y devuelve dos strings (a, b)."""
    # normalizar unicode y comillas curvas → rectas
    s = unicodedata.normalize("NFKC", arg_text).strip()
    s = s.replace("“", '"').replace("”", '"').replace("’",
                                                      "'").replace("‘", "'")
    # permitir espacios/comentarios simples
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r'^\s*"([^"]+)"\s*,\s*"([^"]+)"\s*$', s)
    if not m:
        raise ValueError(f"CONNECT: argumentos inválidos → {s!r}")
    return m.group(1), m.group(2)


def _compute_pct_deltas(base_m: dict, new_m: dict, dims: list[str]) -> dict:
    """Devuelve dict dim -> %delta (o None si base==0)."""
    pct = {}
    for k in dims:
        b = float(base_m.get(k, 0.0))
        n = float(new_m.get(k, 0.0))
        dv = n - b
        pct[k] = (dv / b * 100.0) if b > 0 else None
    return pct


def print_whatif_table(log: list[dict], dims: list[str] | None):
    """Muestra una tabla alineada con deltas y %."""
    if not log:
        return
    dims = dims or ["trust", "cohesion", "equity"]

    title_w = max(5, max(len(x.get("title", "")) for x in log))
    col_w = 20

    header = "title".ljust(title_w)
    for k in dims:
        header += "  " + k.ljust(col_w)
    print(header)
    print("-" * (len(header)))

    for item in log:
        line = item.get("title", "").ljust(title_w)
        d = item.get("deltas", {})
        p = item.get("pct", {})
        for k in dims:
            dv = float(d.get(k, 0.0))
            pv = p.get(k, None)
            cell = f"{dv:+0.2f}"
            cell += " (—)" if pv is None else f" ({pv:+0.2f}%)"
            line += "  " + cell.ljust(col_w)
        print(line)


def parse_program(src: str):
    src = strip_line_comments(src)
    i = 0
    n = len(src)
    ast = AST()
    while i < n:
        # 1) SIEMPRE: saltar espacios y comentarios al comienzo de cada iteración
        i = skip_ws_and_comments(src, i)
        if i >= n:
            break
        # ------------ CREATE_NODE / crear_nodo ------------
        if startswith_token(src, i, "CREATE_NODE"):
            i += len("CREATE_NODE")
            i = skip_ws_and_comments(src, i)

            # Esperamos: TYPE("Name") { ... }
            # TYPE
            # leemos identificador de tipo hasta '('
            j = i
            while j < n and (src[j].isalpha() or src[j] == "_"):
                j += 1
            type_name = src[i:j].strip()
            i = skip_ws_and_comments(src, j)

            if i >= n or src[i] != "(":
                raise ValueError("Expected '(' after CREATE_NODE type")
            name_text, after_paren = extract_parens(src, i)
            # name_text debería ser "Nombre"
            name_text = name_text.strip()
            if len(name_text) < 2 or name_text[0] not in "\"'" or name_text[
                    -1] not in "\"'":
                raise ValueError("CREATE_NODE name must be quoted")
            node_name = name_text[1:-1]
            i = after_paren

            i = skip_ws_and_comments(src, i)
            # bloque de props
            brace_pos = src.find("{", i)
            if brace_pos == -1:
                raise ValueError(
                    "Expected properties block { ... } after CREATE_NODE name")
            props_text, end_block = extract_block(src, brace_pos)
            props = parse_properties(props_text)
            i = end_block

            ast.decls.append(("CREATE_NODE", type_name, node_name, props))
            continue  # ← DENTRO del while

        # ------------------- CONNECT -----------------------
        if startswith_token(src, i, "CONNECT"):
            i += len("CONNECT")
            i = skip_ws_and_comments(src, i)
            if i >= n or src[i] != "(":
                ctx = src[max(0, i - 40):min(n, i + 80)]
                raise ValueError(
                    f"Expected '(' after CONNECT at pos {i}. Context: {ctx!r}")

            arg_text, after_paren = extract_parens(src, i)
            a, b = parse_two_quoted_args(arg_text)
            i = after_paren

            i = skip_ws_and_comments(src, i)
            brace_pos = src.find("{", i)
            if brace_pos == -1:
                props = {}
            else:
                props_text, end_block = extract_block(src, brace_pos)
                props = parse_properties(props_text)
                i = end_block

            ast.actions.append(("CONNECT", a, b, props))
            continue  # ← DENTRO del while

        # ----------------- STRENGTHEN_TIES -----------------
        # STRENGTHEN_TIES("Ayla") { ... }
        if startswith_token(src, i, "STRENGTHEN_TIES"):
            m = re.match(rf"STRENGTHEN_TIES{WS}\({WS}\"([^\"]+)\"{WS}\){WS}",
                         src[i:],
                         flags=re.S)
            if not m:
                raise ValueError("STRENGTHEN_TIES target must be quoted")
            target = m.group(1)
            i += m.end()

            # salto a '{' y extraigo bloque
            i = skip_ws_and_comments(src, i)
            brace = src.find("{", i)
            if brace == -1:
                raise ValueError("Expected '{' after STRENGTHEN_TIES")
            block, endb = extract_block(src, brace)
            props = parse_properties(block)
            ast.actions.append(("STRENGTHEN_TIES", target, props))
            i = endb
            continue

        # ----------------- LAUNCH_INITIATIVE ----------------
        if startswith_token(src, i, "LAUNCH_INITIATIVE"):
            i += len("LAUNCH_INITIATIVE")
            i = skip_ws_and_comments(src, i)
            # nombre entre comillas
            if i >= n or src[i] not in "\"'":
                raise ValueError(
                    "LAUNCH_INITIATIVE expects a quoted initiative name")
            # leemos "...":
            j = i + 1
            quote = src[i]
            while j < n and src[j] != quote:
                j += 1
            if j >= n:
                raise ValueError("Unclosed initiative name")
            iname = src[i + 1:j]
            i = j + 1

            i = skip_ws_and_comments(src, i)
            brace_pos = src.find("{", i)
            props = {}
            if brace_pos != -1:
                props_text, end_block = extract_block(src, brace_pos)
                props = parse_properties(props_text)
                i = end_block

            ast.actions.append(("LAUNCH_INITIATIVE", iname, props))
            continue

        # --------------- REDISTRIBUTE_RESOURCES -------------
        if startswith_token(src, i, "REDISTRIBUTE_RESOURCES"):
            i += len("REDISTRIBUTE_RESOURCES")
            i = skip_ws_and_comments(src, i)
            if i >= n or src[i] != "(":
                raise ValueError("Expected '(' after REDISTRIBUTE_RESOURCES")
            arg_text, after_paren = extract_parens(src, i)
            # "giver","receiver"
            a, b = parse_two_quoted_args(arg_text)
            i = after_paren

            i = skip_ws_and_comments(src, i)
            props = {}
            brace_pos = src.find("{", i)
            if brace_pos != -1:
                props_text, end_block = extract_block(src, brace_pos)
                props = parse_properties(props_text)
                i = end_block

            ast.actions.append(("REDISTRIBUTE_RESOURCES", a, b, props))
            continue

        # -------------------- CARE_NETWORK ------------------
        if startswith_token(src, i, "CARE_NETWORK"):
            i += len("CARE_NETWORK")
            i = skip_ws_and_comments(src, i)
            if i >= n or src[i] != "(":
                raise ValueError("Expected '(' after CARE_NETWORK")
            arg_text, after_paren = extract_parens(src, i)
            s = arg_text.strip()
            if len(s) < 2 or s[0] not in "\"'" or s[-1] not in "\"'":
                raise ValueError("CARE_NETWORK target must be quoted")
            target = s[1:-1]
            i = after_paren

            i = skip_ws_and_comments(src, i)
            props = {}
            brace_pos = src.find("{", i)
            if brace_pos != -1:
                props_text, end_block = extract_block(src, brace_pos)
                props = parse_properties(props_text)
                i = end_block

            ast.actions.append(("CARE_NETWORK", target, props))
            continue

        # -------------------- INTERVENE_IF ------------------
        if startswith_token(src, i, "INTERVENE_IF"):
            i += len("INTERVENE_IF")
            i = skip_ws_and_comments(src, i)
            if i >= n or src[i] != "(":
                raise ValueError("Expected '(' after INTERVENE_IF")
            cond_text, after_paren = extract_parens(src, i)
            i = after_paren

            i = skip_ws_and_comments(src, i)
            brace_pos = src.find("{", i)
            if brace_pos == -1:
                raise ValueError("Expected block after INTERVENE_IF")
            then_block, end_then = extract_block(src, brace_pos)
            i = end_then

            i = skip_ws_and_comments(src, i)
            else_pos = src.find("CONTRIBUTE_ELSE", i)
            if else_pos == -1:
                raise ValueError("Expected CONTRIBUTE_ELSE")
            i = else_pos + len("CONTRIBUTE_ELSE")

            i = skip_ws_and_comments(src, i)
            brace_pos2 = src.find("{", i)
            if brace_pos2 == -1:
                raise ValueError("Expected block after CONTRIBUTE_ELSE")
            else_block, end_else = extract_block(src, brace_pos2)
            i = end_else

            ast.actions.append(
                ("IF", cond_text.strip(), then_block, else_block))
            continue

        # -------------------- MEASURE_IMPACT ----------------
        if startswith_token(src, i, "MEASURE_IMPACT"):
            i += len("MEASURE_IMPACT")
            i = skip_ws_and_comments(src, i)
            # MEASURE_IMPACT COMMUNITY("X") IN DIMENSION("a","b","c")
            # Simplificación: buscamos DIMENSION(...) después del target
            # target tipo y nombre entre paréntesis
            # leemos tipo
            j = i
            while j < n and (src[j].isalpha() or src[j] == "_"):
                j += 1
            target_type = src[i:j].strip()
            i = skip_ws_and_comments(src, j)
            if i >= n or src[i] != "(":
                raise ValueError(
                    "Expected '(' after MEASURE_IMPACT target type")
            name_text, after_paren = extract_parens(src, i)
            name_text = name_text.strip()
            if len(name_text) < 2 or name_text[0] not in "\"'" or name_text[
                    -1] not in "\"'":
                raise ValueError("MEASURE_IMPACT target name must be quoted")
            target_name = name_text[1:-1]
            i = after_paren

            # permitir IN/EN
            i = skip_ws_and_comments(src, i)
            if startswith_token(src, i, "IN") or startswith_token(
                    src, i, "EN"):
                # avanza por IN/EN
                if startswith_token(src, i, "IN"):
                    i += len("IN")
                else:
                    i += len("EN")
                i = skip_ws_and_comments(src, i)

            # buscar DIMENSION de forma robusta (ignorar tildes / case)
            # primero intento exacto como antes
            dim_pos = src.find("DIMENSION", i)
            if dim_pos == -1:
                # fallback: comparar en mayúsculas y quitar posibles tildes
                U = src.upper().replace("Ó", "O").replace("Í", "I").replace(
                    "É", "E").replace("Á", "A").replace("Ú", "U")
                dim_pos = U.find("DIMENSION", i)
                if dim_pos == -1:
                    raise ValueError(
                        "Expected DIMENSION(...) in MEASURE_IMPACT")
            i = dim_pos + len("DIMENSION")

            i = skip_ws_and_comments(src, i)
            if i >= n or src[i] != "(":
                raise ValueError("Expected '(' after DIMENSION")
            dim_text, after_dim = extract_parens(src, i)
            # dim_text: "trust","cohesion","equity" (o sus equivalentes ES que token_map convertirá)
            dims = []
            for part in dim_text.split(","):
                p = part.strip()
                if len(p) >= 2 and p[0] in "\"'" and p[-1] in "\"'":
                    dims.append(p[1:-1])
            i = after_dim

            ast.actions.append(
                ("MEASURE_IMPACT", target_type, target_name, dims))
            continue

        # ---------------------- SHOW_NETWORK ----------------
        if startswith_token(src, i, "SHOW_NETWORK"):
            i += len("SHOW_NETWORK")
            ast.actions.append(("SHOW_NETWORK", ))
            continue

        # WHAT_IF "Nombre" { APPLY { ... } COMPARE: [ ... ] }
        if startswith_token(src, i, "WHAT_IF"):
            # Header (título opcional)
            m = re.match(rf"{WS}WHAT_IF{WS}(\"([^\"]*)\")?{WS}",
                         src[i:],
                         flags=re.S | re.I)
            if not m:
                raise ValueError("Syntax error in WHAT_IF header")
            i += m.end()
            title = (m.group(2) or "").strip()

            def _parse_what_if_body(body: str):
                j = 0
                # -- APPLY --
                m_apply = re.search(rf"{WS}APPLY{WS}",
                                    body[j:],
                                    flags=re.S | re.I)
                if not m_apply:
                    raise ValueError("Expected APPLY in WHAT_IF")
                j += m_apply.end()
                # bloque { ... } de APPLY
                j = skip_ws_and_comments(body, j)
                brace_pos = body.find("{", j)
                if brace_pos == -1:
                    raise ValueError("Expected '{' after APPLY")
                apply_block, end_apply = extract_block(body, brace_pos)
                j = end_apply
                # -- COMPARE: [ ... ]
                j = skip_ws_and_comments(body, j)
                m_cmp = re.search(rf"{WS}COMPARE{WS}:{WS}\[(.*?)\]",
                                  body[j:],
                                  flags=re.S | re.I)
                if not m_cmp:
                    raise ValueError("Expected COMPARE: [ ... ] in WHAT_IF")
                list_text = m_cmp.group(1)
                # dims
                raw_dims = [
                    x.strip() for x in re.split(r"[,\n]", list_text)
                    if x.strip()
                ]
                dims = []
                for d in raw_dims:
                    d = d.strip().strip("\"'").lower()
                    if d in ("trust", "cohesion", "equity"):
                        dims.append(d)
                return apply_block, dims

            # ¿Hay llave externa?
            i = skip_ws_and_comments(src, i)
            if i < len(src) and src[i] == "{":
                body, end_body = extract_block(src, i)
                i = end_body
                apply_block, dims = _parse_what_if_body(body)
            else:
                # Forma sin llave externa: … WHAT_IF … APPLY { … } COMPARE: [ … ]
                # Parseamos directamente sobre src a partir de i
                k = i
                # localizar APPLY
                m_apply = re.match(rf"{WS}APPLY{WS}",
                                   src[k:],
                                   flags=re.S | re.I)
                if not m_apply:
                    raise ValueError("Expected APPLY in WHAT_IF")
                k += m_apply.end()
                k = skip_ws_and_comments(src, k)
                brace_pos = src.find("{", k)
                if brace_pos == -1:
                    raise ValueError("Expected '{' after APPLY")
                apply_block, end_apply = extract_block(src, brace_pos)
                k = end_apply
                # COMPARE
                k = skip_ws_and_comments(src, k)
                m_cmp = re.match(rf"{WS}COMPARE{WS}:{WS}\[(.*?)\]",
                                 src[k:],
                                 flags=re.S | re.I)
                if not m_cmp:
                    raise ValueError("Expected COMPARE: [ ... ] in WHAT_IF")
                list_text = m_cmp.group(1)
                k += m_cmp.end()
                raw_dims = [
                    x.strip() for x in re.split(r"[,\n]", list_text)
                    if x.strip()
                ]
                dims = []
                for d in raw_dims:
                    d = d.strip().strip("\"'").lower()
                    if d in ("trust", "cohesion", "equity"):
                        dims.append(d)
                i = k  # avanzamos el cursor principal

            ast.actions.append(("WHAT_IF", title, apply_block, dims))
            continue

            # SHOW_WHAT_IF_TABLE [ "trust","equity" ]  (lista opcional)
        if startswith_token(src, i, "SHOW_WHAT_IF_TABLE"):
            i += len("SHOW_WHAT_IF_TABLE")
            i = skip_ws_and_comments(src, i)
            dims = ["trust", "cohesion", "equity"]
            if i < n and src[i] == "[":
                inner_text, j = extract_bracketed(src, i, "[", "]")
                raw = [
                    x.strip() for x in re.split(r"[,\n]", inner_text)
                    if x.strip()
                ]
                dims = []
                for d in raw:
                    d = d.strip().strip("\"'").lower()
                    if d in ("trust", "cohesion", "equity"):
                        dims.append(d)
                i = j
            ast.actions.append(("SHOW_WHAT_IF_TABLE", dims))

            # Si no matcheó nada, avanzar 1 char para no quedar en loop infinito
        i += 1
    return ast


# =========================
# RUNTIME / EJECUCIÓN
# =========================
# Mapa simple de intensidades → incrementos
_INT_MAP = {
    "ALTA": (10, 6),  # (bump_trust_node, bump_conf_edge)
    "MEDIA": (6, 4),
    "BAJA": (3, 2),
}


class Runtime:

    def __init__(self):
        self.graph = nx.Graph()

    def clone(self):
        import copy
        new = Runtime()
        new.graph = nx.Graph()
        # Copia profunda de nodos
        for n, d in self.graph.nodes(data=True):
            new.graph.add_node(n, **copy.deepcopy(d))
        # Copia profunda de aristas
        for u, v, d in self.graph.edges(data=True):
            new.graph.add_edge(u, v, **copy.deepcopy(d))
        return new

    def _get_node_trust(self, n):
        d = self.graph.nodes[n]
        v = d.get("confianza", d.get("trust"))
        if v is None:
            return 50.0
        try:
            return float(v)
        except Exception:
            return 50.0

    def _get_node_resources(self, n):
        d = self.graph.nodes[n]
        # aceptar resources, recurso, recursos
        v = d.get("resources", d.get("recurso", d.get("recursos")))
        if v is None:
            return 0.0
        try:
            return float(v)
        except Exception:
            return 0.0

    def _set_node_trust(self, n, val):
        val = float(max(0, min(100, val)))
        self.graph.nodes[n]["confianza"] = val
        self.graph.nodes[n]["trust"] = val

    def _set_node_resources(self, n, val):
        val = float(max(0.0, val))
        self.graph.nodes[n]["resources"] = val
        self.graph.nodes[n]["recurso"] = val
        self.graph.nodes[n]["recursos"] = val

    def _norm_intensity(self, x):
        if not x: return "MEDIA"
        x = str(x).upper().strip()
        # aceptar ambas familias
        if x in ("ALTA", "HIGH"): return "ALTA"
        if x in ("BAJA", "LOW"): return "BAJA"
        return "MEDIA"  # MEDIA/MEDIUM por default

    # ---------- utilidades seguras ----------
    def ensure_node(self, kind: str, name: str, props: dict):
        if not self.graph.has_node(name):
            self.graph.add_node(name, kind=kind.upper())
        # merge “suave”: solo setea si no existe; para forzar, usa .update
        ndata = self.graph.nodes[name]
        for k, v in props.items():
            ndata[k] = v
        # defaults razonables
        ndata.setdefault(
            "trust", float(props.get("trust", props.get("confianza", 50.0))))
        ndata.setdefault(
            "resources",
            float(props.get("resources", props.get("recursos", 0.0))))

    def _edge_trust(self, u, v, default=50.0):
        if self.graph.has_edge(u, v):
            return float(self.graph[u][v].get("trust", default))
        return default

    def _set_edge_trust(self, u, v, value):
        if not self.graph.has_edge(u, v):
            self.graph.add_edge(u, v)
        self.graph[u][v]["trust"] = float(max(0.0, min(100.0, value)))

    def _bump_node_trust(self, node, delta):
        if self.graph.has_node(node):
            t = float(self.graph.nodes[node].get("trust", 50.0)) + float(delta)
            self.graph.nodes[node]["trust"] = max(0.0, min(100.0, t))

    # --- Helpers internos ---

    def _clamp(self, v, lo=0, hi=100):
        return max(lo, min(hi, v))

    def _int_bumps(self, norm):
        return {
            "ALTA": (10, 6),
            "MEDIA": (6, 4),
            "BAJA": (3, 2)
        }.get(norm, (6, 4))

    # --- Acciones con efecto real ---

    def strengthen_ties(self, target, props):
        if DEBUG_ACTIONS:
            print(f"[DEBUG] strengthen_ties → target={target}, props={props}")

        if not self.graph.has_node(target): return
        norm = self._norm_intensity(
            props.get("intensidad") or props.get("intensity"))
        bump_node, bump_edge = self._int_bumps(norm)

        # subir confianza del nodo
        node_conf = self.graph.nodes[target].get(
            "confianza", self.graph.nodes[target].get("trust", 50))
        node_conf = max(0, min(100, node_conf + bump_node))
        self.graph.nodes[target]["confianza"] = node_conf
        self.graph.nodes[target]["trust"] = node_conf

        # subir confianza de aristas incidentes
        for u, v, d in self.graph.edges(target, data=True):
            conf = float(d.get("confianza", d.get("trust", 50)))
            conf = max(0, min(100, conf + bump_edge))
            d["confianza"] = conf
            d["trust"] = conf

    def care_network(self, target, intensity="MEDIA", mitigation_plan=None):
        if DEBUG_ACTIONS:
            print(
                f"[DEBUG] care_network → target={target}, intensity={intensity}, plan={mitigation_plan}"
            )
        if not self.graph.has_node(target): return
        norm = self._norm_intensity(intensity)
        bump_node, bump_edge = self._int_bumps(norm)

        # subir confianza del nodo
        node_conf = self.graph.nodes[target].get(
            "confianza", self.graph.nodes[target].get("trust", 50))
        node_conf = max(0, min(100, node_conf + bump_node))
        self.graph.nodes[target]["confianza"] = node_conf
        self.graph.nodes[target]["trust"] = node_conf

        # reforzar SOLO vínculos muy bajos
        for u, v, d in self.graph.edges(target, data=True):
            conf = float(d.get("confianza", d.get("trust", 50)))
            if conf < 50:
                conf = max(0, min(100, conf + max(4, bump_edge)))
                d["confianza"] = conf
                d["trust"] = conf

        if mitigation_plan:
            plans = self.graph.nodes[target].get("mitigation_plans", [])
            plans.append(str(mitigation_plan))
            self.graph.nodes[target]["mitigation_plans"] = plans

    def redistribute_resources(self,
                               giver,
                               receiver,
                               fraction=0.2,
                               min_left=2.0):
        if not (self.graph.has_node(giver) and self.graph.has_node(receiver)):
            return
        g = self._get_node_resources(giver)
        r = self._get_node_resources(receiver)
        fraction = float(fraction)
        min_left = float(min_left)

        if g <= min_left:
            if DEBUG_ACTIONS:
                print(
                    f"[DEBUG] redistribute_resources → SIN MOVIMIENTO (g={g}, min_left={min_left})"
                )
            return

        move = max(0.0, min(g - min_left, g * fraction))
        if move <= 0:
            if DEBUG_ACTIONS:
                print(
                    f"[DEBUG] redistribute_resources → SIN MOVIMIENTO (g={g}, fraction={fraction})"
                )
            return

        self._set_node_resources(giver, g - move)
        self._set_node_resources(receiver, r + move)
        if DEBUG_ACTIONS:
            print(
                f"[DEBUG] redistribute_resources → moved={move:.2f}, {giver}:{g - move:.2f} → {receiver}:{r + move:.2f}"
            )

    def launch_initiative(self, target: str, inc: int = 15):
        """
        Sube confianza de la comunidad objetivo (o nodo objetivo si existiera con ese nombre).
        """
        if DEBUG_ACTIONS:
            print(f"[DEBUG] launch_initiative → target={target}, inc={inc}")
        if not self.graph.has_node(target):
            return
        node = self.graph.nodes[target]
        cur = node.get("confianza", node.get("trust", 50))
        node["confianza"] = self._clamp(cur + int(inc))
        node["trust"] = node["confianza"]

    # ---------- acciones del DSL ----------
    def connect(self, a, b, props=None):
        props = props or {}
        if not (self.graph.has_node(a) and self.graph.has_node(b)):
            return
        self.graph.add_edge(a, b)
        d = self.graph.edges[a, b]
        # confianza de la arista
        conf = props.get("confianza", props.get("trust", 50))
        try:
            conf = float(conf)
        except Exception:
            conf = 50.0
        d["confianza"] = conf
        d["trust"] = conf
        # intensidad (guardamos ambas por compatibilidad)
        inten = props.get("intensidad", props.get("intensity", "MEDIA"))
        d["intensidad"] = inten
        d["intensity"] = inten

# ---------- métricas y visual (dejas tus versiones si ya existen) ----------

    def measure(self):
        # Trust: promedio de confianza nodal
        trusts = [self._get_node_trust(n) for n in self.graph.nodes()]
        trust = sum(trusts) / len(
            trusts) if trusts else 0.0  # <--- ESTA LÍNEA FALTABA

        # Cohesion: clustering/transitividad (0..1) → 0..100
        try:
            coh = nx.transitivity(self.graph)  # global clustering
            cohesion = 100.0 * float(coh)
        except Exception:
            cohesion = 0.0

        # Equity: 100*(1 - Gini) sobre resources
        resc = [self._get_node_resources(n) for n in self.graph.nodes()]
        equity = 0.0
        if resc:
            xs = sorted(float(x) for x in resc)
            s = sum(xs)
            if s > 0:
                n = len(xs)
                cum = 0.0
                for i, x in enumerate(xs, start=1):
                    cum += i * x
                gini = (2 * cum) / (n * s) - (n + 1) / n
                gini = max(0.0, min(1.0, gini))
                equity = 100.0 * (1.0 - gini)

        return {
            "trust": round(trust, 2),
            "cohesion": round(cohesion, 2),
            "equity": round(equity, 2)
        }

    def show_network(self, path="network.png", title=None):
        import matplotlib.pyplot as plt
        plt.figure(figsize=(6, 6))
        pos = nx.spring_layout(self.graph, seed=42)
        nx.draw(self.graph,
                pos,
                with_labels=True,
                node_size=800,
                node_color="lightblue",
                font_size=8)

        if title:
            plt.title(title)

        try:
            plt.tight_layout()
        except Exception:
            pass

        plt.savefig(path)
        print(f"[OK] Gráfico guardado en {path}")
        plt.close()

        # Si estás en Replit, mostrará la imagen en la pestaña de archivos.


# -------------------------
def gini(xs):
    """
    Gini en [0,1] para una lista de números no negativos.
    Robusto a ceros y listas vacías.
    """
    if not xs:
        return 0.0
    try:
        xs = [float(x) for x in xs if x is not None]
    except Exception:
        xs = [float(x) for x in xs]
    n = len(xs)
    if n == 0:
        return 0.0
    xs.sort()
    s = sum(xs)
    if s <= 0:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs, start=1):
        cum += i * x
    g = (2.0 * cum) / (n * s) - (n + 1.0) / n
    # clamp por estabilidad numérica
    if g < 0.0: g = 0.0
    if g > 1.0: g = 1.0
    return g


# ———— PRE-LINTER v0.4 (hook) ————
from linter import EthicsLinter
from core_helpers import build_lint_context

def _ast_to_ir_for_linter(ast) -> dict:
    """
    Conversión mínima y tolerante del AST a IR para el linter.
    Si ya tenés un builder/serializer propio, usalo y reemplazá esta función.
    """
    ir = {"nodes": [], "relations": []}
    try:
        for kind, type_name, name, props in getattr(ast, "decls", []):
            if kind == "CREATE_NODE":
                ir["nodes"].append({
                    "name": name,
                    "type": type_name,
                    **(props or {})
                })
            elif kind in ("CREATE_EDGE", "CONNECT", "LINK"):
                # Ajustá si tu AST usa otra tupla/estructura para relaciones
                src = props.get("source") if props else None
                tgt = props.get("target") if props else None
                tags = props.get("tags") if props else []
                if src and tgt:
                    ir["relations"].append({"source": src, "target": tgt, "tags": tags})
    except Exception:
        # Fallback tolerante: si algo falla, el linter seguirá pudiendo evaluar reglas de métricas
        pass
    return ir

def _print_lint_report(report):
    if not report.violations:
        print(f"[LINTER][{report.phase}] ✅ Sin violaciones.")
        return
    print(f"[LINTER][{report.phase}] ⚠️  Violaciones encontradas:")
    for v in report.violations:
        print(f"  - ({v.severity.upper()}) {v.rule_id}: {v.message}")
        if v.remediation:
            print(f"      → Sugerencia: {v.remediation}")

def _persist_blockade_summary(report):
    import json, time
    payload = {
        "phase": report.phase,
        "blocked": True,
        "violations": [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "message": v.message,
                "remediation": v.remediation,
            } for v in report.violations
        ],
        "ts": int(time.time()),
        "version": "v0.4",
    }
    with open("blockade_summary.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("[LINTER] 🛑 Bloqueo ético — se guardó blockade_summary.json")
# ———— FIN PRE-LINTER v0.4 ————


# =========================
# EJECUCIÓN DEL AST
# =========================
final_metrics = None

def execute(rt: Runtime,
            ast: AST,
            finalize: bool = True,
            run_id: str | None = None):
    global WHATIF_LOG, WHATIF_SAVED, NO_WHATIF_TABLE, WHATIF_DIMS, SORT_WHATIF_BY

    # 1) Declaraciones iniciales
    for kind, type_name, name, props in ast.decls:
        if kind == "CREATE_NODE":
            rt.ensure_node(type_name.upper(), name, props)

    # 2) Snapshot inicial
    start_m = rt.measure()
    start_snap = snapshot_state(rt)
    
    # 3) Acciones
    for act in ast.actions:
        tag = act[0]

        if tag == "CONNECT":
            _, a, b, props = act
            rt.connect(a, b, props)

        elif tag == "STRENGTHEN_TIES":
            _, target, props = act
            p = canonicalize_props(dict(props))
            rt.strengthen_ties(target, p)

        elif tag == "REDISTRIBUTE_RESOURCES":
            _, giver, receiver, props = act
            p = canonicalize_props(dict(props))
            rt.redistribute_resources(giver,
                                      receiver,
                                      fraction=float(p.get("fraction", 0.2)),
                                      min_left=float(p.get("min_left", 2.0)))

        elif tag == "CARE_NETWORK":
            _, target, props = act
            p = canonicalize_props(dict(props))
            rt.care_network(target,
                            intensity=(p.get("intensity") or "MEDIA"),
                            mitigation_plan=p.get("mitigation_plan"))

        elif tag == "LAUNCH_INITIATIVE":
            _, iname, props = act
            target = props.get("target") or props.get(
                "community") or props.get("COMMUNITY")
            inc = int(props.get("trust_boost", 15))
            if target:
                rt.launch_initiative(target, inc=inc)
            else:
                for n, d in rt.graph.nodes(data=True):
                    if d.get("kind") == "COMMUNITY":
                        rt.launch_initiative(n, inc=inc)

        elif tag == "IF":
            _, cond, then_code, else_code = act
            if eval_condition(rt, cond):
                ast_sub = parse_program(then_code)
                execute(rt, ast_sub, finalize=False)
            else:
                ast_sub = parse_program(else_code)
                execute(rt, ast_sub, finalize=False)

        elif tag == "WHAT_IF":
            # act = ("WHAT_IF", title, apply_code, dims)
            _, title, apply_code, dims = act

            # 1) Baseline (sin tocar rt real)
            base_m = rt.measure()

            # 2) Clonar, aplicar y medir
            rt2 = rt.clone()
            ast2 = parse_program(apply_code)
            execute(rt2, ast2,
                    finalize=False)  # sin linter ni reportes en ensayo
            new_m = rt2.measure()

            # 3) Deltas y % (con signos)
            dims = dims or ["trust", "cohesion", "equity"]
            deltas = {
                k: round(new_m.get(k, 0.0) - base_m.get(k, 0.0), 2)
                for k in dims
            }
            pct = _compute_pct_deltas(base_m, new_m, dims)
            pretty = ", ".join(
                f"{k}: {deltas[k]:+0.2f} " +
                (f"({pct[k]:+0.2f}%)" if pct[k] is not None else "(+0.00%)")
                for k in dims)
            title_safe = title or "(sin título)"
            print(f'?? WHAT_IF "{title_safe}" → {pretty}')

            # 4) Guardar en memoria para tabla y exportes
            base_title = title_safe
            existing = {item["title"] for item in WHATIF_LOG}
            t = base_title
            n = 2
            while t in existing:
                t = f"{base_title} #{n}"
                n += 1

            WHATIF_LOG.append({
                "title": t,
                "deltas": deltas,
                "pct": pct,
                "base": base_m,
                "new": new_m
            })
            continue

        elif tag == "MEASURE_IMPACT":
            _, target_type, target_name, dims = act
            metrics = rt.measure()
            sel = {k: metrics[k] for k in dims if k in metrics}
            print(">> Impacto:", json.dumps(sel, ensure_ascii=False))

            rt.final_metrics = metrics            # ⬅️ GUARDAR AQUÍ
            continue

        elif tag == "SHOW_NETWORK":
            rt.show_network(title="LEXO v0.1 – Red")

        elif tag == "SHOW_WHAT_IF_TABLE":
            _, dims = act
            global WHATIF_TABLE_REQUESTED, WHATIF_TABLE_PRINTED
            WHATIF_TABLE_REQUESTED = True
            if not NO_WHATIF_TABLE and not WHATIF_TABLE_PRINTED:
                print_whatif_table(WHATIF_LOG, dims)
                WHATIF_TABLE_PRINTED = True
            continue

    # 4) Finalización
    # 4) Linter final-only + reportes (SOLO si finalize=True)
    if finalize:
        final_m = rt.measure()
        final_snap = snapshot_state(rt)
        alerts = evaluate_ethics(rt, start_snap, final_snap, start_m, final_m)
        print_alerts(alerts)

        # -------- PLUS: desglose de recursos por nodo y % ----------
        resources_by_node = {}
        total_resources = 0.0
        for n, d in rt.graph.nodes(data=True):
            r = float(d.get("resources", d.get("recursos", 0.0)))
            r = round(r, 2)
            resources_by_node[n] = r
            total_resources += r
        total_resources = round(total_resources, 2)

        resources_pct = {
            n: (round((r / total_resources) *
                      100.0, 2) if total_resources > 0 else 0.0)
            for n, r in resources_by_node.items()
        }

        # Porcentajes sólo de nodos comunidad (si existen)
        community_pct = {}
        for n, d in rt.graph.nodes(data=True):
            kind = str(d.get("kind", "")).upper()
            if kind == "COMMUNITY":
                community_pct[n] = resources_pct.get(n, 0.0)

        # -------- Persistencia: JSON “run_*” con TODO adentro ----------
        payload = {
            "run_ts": RUN_TS,
            "run_id": run_id,
            "final_metrics": final_m,
            "ethics_alerts": alerts,
            "what_if": WHATIF_LOG,  # escenarios simulados
            "resources": {
                "total": total_resources,
                "by_node": resources_by_node,
                "percentages": resources_pct,
                "community_percentages": community_pct,
            },
        }

        # Nombre de archivo coherente (si hay run_id usamos prefijo “run_”)
        out_json = f"run_{run_id}.json" if run_id else "report.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[OK] Reporte JSON guardado en {out_json}")

        # CSV de métricas (si ya tenías esta función, la dejamos)
        save_report_csv(final_m, alerts, path="report.csv")

def gini(values):
    """
    Calcula el coeficiente de Gini de una lista de valores.
    Devuelve un número entre 0 (perfecta igualdad) y 1 (máxima desigualdad).
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(values)
    cumulative = 0
    for i, val in enumerate(sorted_vals, start=1):
        cumulative += i * val
    total = sum(sorted_vals)
    if total == 0:
        return 0.0
    return (2 * cumulative) / (n * total) - (n + 1) / n

    # Exportes WHAT_IF “de cortesía” si hay escenarios y aún no se guardaron
    global WHATIF_SAVED
    if WHATIF_LOG and not WHATIF_SAVED:
         wi_json = f"whatif_{run_id}.json" if run_id else "whatif.json"
         wi_csv = f"whatif_{run_id}.csv" if run_id else "whatif.csv"
         save_whatif_json(wi_json)
         save_whatif_csv(wi_csv)
         WHATIF_SAVED = True

def canonicalize_props(props: dict) -> dict:
    """Mapea claves ES/EN a nombres canónicos internos."""
    if not props:
        return {}
    m = {
        "intensidad": "intensity",
        "plan_mitigacion": "mitigation_plan",
        "plan_mitigación": "mitigation_plan",
        "confianza": "trust",
        "cohesión": "cohesion",
        "cohesion": "cohesion",
        "equidad": "equity",
        "recurso": "resources",
        "recursos": "resources",
        "fraccion": "fraction",
        "minimo": "min_left",
        "community": "target",  # por si viene “community” dentro de props
        "COMMUNITY": "target",
    }
    out = {}
    for k, v in props.items():
        out[m.get(k, k)] = v
    return out

def eval_block(rt: Runtime, code_block: str):
    """Evalúa un sub-bloque de acciones simple (sin IF anidados en el MVP).
    Acepta las mismas sentencias de alto nivel."""
    ast_sub = parse_program(code_block)
    execute(rt, ast_sub)


def eval_condition(rt, cond_text: str) -> bool:
    import re, unicodedata

    # 1) Normalizar unicode (tildes/espacios “raros”, comillas curvas → rectas)
    txt = unicodedata.normalize("NFKC", cond_text).strip()
    # Unificar comillas
    txt = txt.replace("“", '"').replace("”",
                                        '"').replace("’",
                                                     "'").replace("‘", "'")

    # 2) Quitar comentarios //... hasta fin de línea y colapsar espacios/saltos
    def _strip_comments(s):
        out = []
        for line in s.splitlines():
            out.append(line.split("//", 1)[0])
        return "\n".join(out)

    txt = _strip_comments(txt)
    txt = re.sub(r"\s+", " ", txt).strip()

    # 3) Normalizar ES→canon
    #    (si ya viene del tokenizer como COMMUNITY/trust igual funciona)
    repl = [
        (r"\bcomunidad\b", "COMMUNITY"),
        (r"\bconfianza\b", "trust"),
        (r"\bcohesión\b", "cohesion"),
        (r"\bcohesion\b", "cohesion"),
        (r"\bequidad\b", "equity"),
    ]
    for pat, rep in repl:
        txt = re.sub(pat, rep, txt, flags=re.IGNORECASE)

    # 4) Aceptar comillas simples o dobles y operadores comunes
    name_pat = r"['\"]([^'\"]+)['\"]"
    pattern = rf"""^\s*
        (COMMUNITY)\s*\(\s*{name_pat}\s*\)\s*
        \.\s*(trust|cohesion|equity)\s*
        (==|!=|<=|>=|<|>)\s*
        (-?\d+(?:\.\d+)?)\s*$
    """
    m = re.match(pattern, txt, flags=re.IGNORECASE | re.VERBOSE | re.DOTALL)
    if not m:
        # Debug útil para ver exactamente qué llegó
        print(f"[WARN] Condición no reconocida (False): {txt!r}")
        return False

    # 5) Extraer partes
    # kind = m.group(1)  # no lo usamos por ahora
    name = m.group(2)
    attr = m.group(3).lower()
    op = m.group(4)
    value = float(m.group(5))

    # 6) Obtener valor actual
    if attr == "trust":
        cur = float(rt.graph.nodes.get(name, {}).get("trust", 50.0))
    else:
        cur = float(rt.measure()[attr])

    # 7) Evaluar
    if op == "<": return cur < value
    if op == "<=": return cur <= value
    if op == ">": return cur > value
    if op == ">=": return cur >= value
    if op == "==": return abs(cur - value) < 1e-9
    if op == "!=": return abs(cur - value) > 1e-9
    print(f"[WARN] Operador no reconocido: {op} → False")
    return False


# --- Snapshot del estado para el linter ético v0.2 ---
def snapshot_state(rt):
    # Confianza por arista
    edges = {
        (u, v): float(d.get("trust", 50.0))
        for u, v, d in rt.graph.edges(data=True)
    }
    # Recursos por nodo
    res_by_node = {
        n: float(rt.graph.nodes[n].get("resources", 0.0))
        for n in rt.graph.nodes()
    }
    resources = list(res_by_node.values())
    total_res = sum(resources) if resources else 0.0
    top_share = (max(resources) / total_res) if total_res > 0 else 0.0
    # Confianza por nodo
    node_trust = {
        n: float(rt.graph.nodes[n].get("trust", 50.0))
        for n in rt.graph.nodes()
    }
    # Grados
    degrees = dict(rt.graph.degree())
    # Gini
    g = gini(resources) if resources else 0.0
    equity = 1.0 - g   # así lo transformás en "equidad" (a mayor desigualdad, menor equity)


    return {
        "edges": edges,
        "gini": g,
        "res_by_node": res_by_node,
        "top_share": top_share,
        "node_trust": node_trust,
        "degrees": degrees,
    }


# Importá tus propias piezas del proyecto (ajusta estos imports a tus módulos reales)
# from your_lexo_module import normalize_source, parse_program, Runtime, execute
# ^^^ Ajusta los nombres/ubicaciones de estas funciones/clases según tu repo

# Helpers centrales (ya creados en core_helpers.py)


# Si ya definiste execute_final() antes, podés borrar esta función.
# La dejo acá por si lo necesitás localmente.
# v0.4 – validación previa con el linter ético

def execute_final_post(rt, run_id, save_network=True):
    """
    Cierra la corrida post-ejecución:
    - Evalúa umbrales finales.
    - Escribe blockade_summary.json y CHANGELOG.md.
    """
    final_metrics = getattr(rt, "final_metrics", None)
    if final_metrics is None:
        print("[EXEC_FINAL] No hay métricas finales; abortando.")
        return ("BLOCKED", [("metrics", 0, "present")])

    try:
        ensure_whatif_never_mutates(rt)
    except NameError:
        pass

    thresholds = load_ethics_thresholds("ethics.yaml")
    print("[ETHICS] Umbrales cargados:", thresholds)

    fails = blocker_decision(final_metrics, thresholds)

    write_blockade_summary(run_id, final_metrics, thresholds, fails)
    append_changelog("BLOCKED" if fails else "OK", final_metrics, fails, "CHANGELOG.md")

    if fails:
        print("🚫 BLOQUEADO por ética/umbrales.")
        return ("BLOCKED", fails)
    else:
        print("✅ OK (cumple umbrales éticos).")
        return ("OK", [])

# =====================================================
# MAIN — CLI de entrada
# =====================================================
if __name__ == "__main__":
    # --- CLI ---
  
def runtime_from_snapshot(snap) -> "Runtime":
    """
    Recrea un Runtime a partir de un snapshot.
    SOPORTA:
      Nodos:
        - lista de dicts: [{"name":..., "props": {...}}] o [{"id":..., "props": {...}}]
        - dict mapeado:  {"NombreNodo": {"type": "...", ...}, ...}
      Aristas:
        - lista de tuplas: [(u, v, props)]
        - lista de dicts: [{"u":..., "v":..., "props": {...}}]
        - lista de dicts: [{"source":..., "target":..., "attrs": {...}}]
    """
    rt = Runtime()

    # --- helper para agregar aristas con API compatible ---
    def _add_edge(rt, u, v, props: dict):
        # preferí connect(u, v, props) si existe; si no, caé a add_edge(u, v, **props)
        if hasattr(rt, "connect") and callable(getattr(rt, "connect")):
            rt.connect(u, v, props or {})
        elif hasattr(rt, "add_edge") and callable(getattr(rt, "add_edge")):
            rt.add_edge(u, v, **(props or {}))
        else:
            raise RuntimeError("Runtime no expone connect(...) ni add_edge(...).")

    # --- nodos ---
    nodes = snap.get("nodes", [])
    if isinstance(nodes, dict):
        # formato: {"Nodo": {...}, ...}
        for name, data in nodes.items():
            props = dict(data or {})
            kind = (props.get("kind") or props.get("type") or "PERSON").upper()
            # evitar duplicar kind/type en props
            safe_props = {k: v for k, v in props.items() if k.lower() not in ("kind", "type")}
            rt.ensure_node(kind, name, safe_props)
    else:
        # formato: lista
        for item in nodes:
            if isinstance(item, dict):
                name = item.get("name") or item.get("id")
                props = dict(item.get("props", {}))
            else:
                # fallback tupla (name, props)
                try:
                    name, props = item
                    props = dict(props or {})
                except Exception:
                    continue
            if not name:
                continue
            kind = (props.get("kind") or props.get("type") or "PERSON").upper()
            safe_props = {k: v for k, v in props.items() if k.lower() not in ("kind", "type")}
            rt.ensure_node(kind, name, safe_props)

    # --- aristas ---
    edges = snap.get("edges", [])
    for e in edges:
        u = v = None
        props = {}
        if isinstance(e, dict):
            if "u" in e or "v" in e:                       # {"u":..., "v":..., "props": {...}}
                u, v = e.get("u"), e.get("v")
                props = dict(e.get("props", {}))
            elif "source" in e or "target" in e:           # {"source":..., "target":..., "attrs": {...}}
                u, v = e.get("source"), e.get("target")
                props = dict(e.get("attrs", {}))
        else:
            # fallback tupla (u, v, props)
            try:
                u, v, props = e
                props = dict(props or {})
            except Exception:
                continue

        if u and v:
            _add_edge(rt, u, v, props)

    return rt


# --- fin snapshot ---
# =========================
# MAIN
# =========================
def main():
    global WHATIF_LOG, WHATIF_SAVED, NO_WHATIF_TABLE, WHATIF_DIMS, SORT_WHATIF_BY

    WHATIF_LOG = []
    WHATIF_SAVED = False

    apply_ethics_yaml_once("ethics.yaml")

    import argparse, hashlib, os, json

    parser = argparse.ArgumentParser()
    parser.add_argument("file",
                        nargs="?",
                        default="demo_es.lexo",
                        help="Archivo .lexo")
    parser.add_argument("--lang", choices=["es", "en"], default="es")

    parser.add_argument("--lint-only", action="store_true",
                        help="Ejecuta solo el linter y sale 0/1.")
    parser.add_argument("--no-lint-block", action="store_true",
                        help="No bloquea ejecución aunque haya violaciones de lint.")
    parser.add_argument("--no-save-network", action="store_true",
        help="No guarda network.png/report.* en execute_final.")
    parser.add_argument("--no-ethics-block", action="store_true",
        help="Si el blocker ético devuelve BLOCKED, continúa (exit 0).")

    
    args = parser.parse_args()

    # --- LECTURA ---
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"[ERROR] No existe {args.file}. Corré: python main.py TU_ARCHIVO.lexo --lang=es")
        sys.exit(1)

    norm = normalize_source(source, args.lang)
    ast = parse_program(norm)
    print(f"[DEBUG] leyendo: {args.file}, bytes={len(source)}, sha1={hashlib.sha1(source.encode()).hexdigest()[:10]}")
    print("[DEBUG] primeras líneas:\n" + "\n".join(source.splitlines()[:6]))

    # --- LINTER PRE-EJECUCIÓN ---

    # --- LINTER PRE-EJECUCIÓN ---
  
    import re

    def _ast_to_ir_for_linter(ast, raw_source: str | None = None) -> dict:
        """
        Construye IR solo desde el source .lexo (robusto para el linter v0.4).
        - Detecta crear_nodo tipo("Nombre")
        - Detecta conectar("A","B") { ... tags: [ ... ] }
        """
        ir = {"nodes": [], "relations": []}
        seen = set()

        def add_node(name: str):
            if name and name not in seen:
                seen.add(name)
                ir["nodes"].append({"name": name})

        def add_edge(u: str, v: str, tags: list[str] | None = None):
            if u and v:
                ir["relations"].append({"source": u, "target": v, "tags": list(set(tags or []))})
                add_node(u)
                add_node(v)

        text = raw_source if isinstance(raw_source, str) else (str(raw_source) if raw_source is not None else "")

        if not isinstance(text, str):
            return ir

        # Nodos: crear_nodo Tipo("Nombre")
        for m in re.finditer(r'conectar\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)\s*\{([\s\S]*?)\}', text, flags=re.I):

            add_node(m.group(1))

        # Relaciones: conectar("A","B") { ... } + tags: [ ... ]
        for m in re.finditer(r'conectar\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)\s*\{([^}]*)\}', text, flags=re.I):
            u, v, body = m.group(1), m.group(2), m.group(3)
            tags = []
            tmatch = re.search(r'tags\s*:\s*\[([^\]]*)\]', body, flags=re.I)
            if tmatch:
                raw = tmatch.group(1)
                tags = [t.strip().strip('"').strip("'") for t in raw.split(",") if t.strip()]
            add_edge(u, v, tags)

        return ir

    def run_linter(ast, rules_path="ethics_rules.yaml", norm_source=None,
           baseline_metrics=None, planned_metrics=None, raw_source: str | None = None):
        """
        Compatibilidad v0.4: construye IR desde el source (raw_source) y ejecuta el PRE-lint.
        Devuelve un LintReport (no una lista).
        """
        # (opcional) normalizar el AST si te pasan un normalizador callable
        if callable(norm_source):
            ast = norm_source(ast)

        if baseline_metrics is None:
            baseline_metrics = {}
        if planned_metrics is None:
            planned_metrics = {}

        # IR desde el source .lexo (usa el extractor definido arriba)
        ast_ir = _ast_to_ir_for_linter(ast, raw_source=raw_source)

        # DEBUG (temporal): confirmar que el extractor ve nodos/edges y care_network
        
        care_count = sum(1 for e in ast_ir["relations"] if "care_network" in (e.get("tags") or []))
        
        linter = EthicsLinter(rules_path)
        ctx = build_lint_context(ast_ir, baseline_metrics, planned_metrics)
        report = linter.run_pre(ctx)  # ← NO llamamos a run_linter otra vez
        return report

    
    baseline_metrics = {"equity": 70, "trust": 60, "cohesion": 65}   # p.ej. {"equity": 70, "trust": 60, "cohesion": 65}
    planned_metrics  = {"equity": 60, "trust": 61, "cohesion": 64}   # p.ej. {"equity": 60, "trust": 62, "cohesion": 64}

    # Ejecutar linter (PRE)
    report = run_linter(
        ast,
        "ethics_rules.yaml",
        norm_source=None,
        baseline_metrics=baseline_metrics,
        planned_metrics=planned_metrics,
        raw_source=source,   # 👈 importante
    )
    violations = report.violations
    append_changelog_lint("OK" if not violations else "FAIL", len(violations))

    # 1) Si solo se pidió correr el linter
    if args.lint_only:
        sys.exit(0 if not violations else 1)

        # 3) Si hay violaciones pero no bloquean, se imprimen igualmente
    if violations:
        for v in violations:
            print(f"[LINT] ({v.severity.upper()}) {v.rule_id}: {v.message}")
            if getattr(v, "remediation", None):
                print(f"       → Sugerencia: {v.remediation}")

    # recién después decidís si bloqueás
    fail_on_lint = True
    if report.should_block and fail_on_lint and not args.no_lint_block: 
        print(f"[LINTER] 🛑 {len(violations)} violación(es). Abortando ejecución por política fail_on_lint.")
        sys.exit(1)
    # --- PARSEAR ---
    
    if ast is None:
        print("[ERROR] parse_program devolvió None (revisá indentación y 'return ast').")

    parser.add_argument("--no-whatif-table",
                        action="store_true",
                        help="No imprimir la tabla comparativa de WHAT_IF")
    parser.add_argument(
        "--dims",
        type=str,
        default="",
        help="Dimensiones para la tabla WHAT_IF, p.ej. 'trust,equity'")
    parser.add_argument(
        "--sort-whatif-by",
        type=str,
        default="",
        help="Ordenar tabla WHAT_IF por: trust/cohesion/equity")
    args = parser.parse_args()

    NO_WHATIF_TABLE = bool(args.no_whatif_table)
    if args.dims:
        WHATIF_DIMS = [
            x.strip().lower() for x in args.dims.split(",") if x.strip()
        ]
    else:
        WHATIF_DIMS = None
    SORT_WHATIF_BY = args.sort_whatif_by.strip().lower() or None

    if not os.path.exists(args.file):
        print(
            f"[ERROR] No existe {args.file}. Corré: python main.py TU_ARCHIVO.lexo --lang=es"
        )
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8") as f:
        source = f.read()

    if DEBUG_MAIN:
        print(
            f"[DEBUG] leyendo: {args.file}, bytes={len(source)}, sha1={hashlib.sha1(source.encode()).hexdigest()[:10]}"
        )
        print("[DEBUG] primeras líneas:\n" +
              "\n".join(source.splitlines()[:6]))

    norm = normalize_source(source, args.lang)
    ast = parse_program(norm)
    if ast is None:
        print(
            "[ERROR] parse_program devolvió None (revisá indentación y 'return ast')."
        )

        sys.exit(1)
    rt = Runtime()
    run_id = time.strftime("%Y%m%d_%H%M%S")
    execute(rt, ast, finalize=True, run_id=run_id)


    # --- RUNTIME ---
    run_id = begin_run()
    try:
        rt = Runtime()
        execute(rt, ast, finalize=True)

        # Post-ejecución (evalúa ética, persiste summary y actualiza changelog)
        status, fails = execute_final_post(rt, run_id, save_network=not args.no_save_network)

        # Respeto de --no-ethics-block
        if status == "BLOCKED" and args.no_ethics_block:
            print("⚠️  [ETHICS] Bloqueo ético anulado por --no-ethics-block (continuando).")
            exit_code = 0
        else:
            exit_code = 0 if status == "OK" else 1

        import sys
        sys.exit(exit_code)

    finally:
        end_run(run_id, ok=True)

    m = rt.measure()
    print("== MÉTRICAS FINALES ==")
    print(json.dumps(m, ensure_ascii=False, indent=2))


# main.py — integración del Blocker v0.2 (robusto, fail-fast)
from lexo.blocker import Blocker, BlockerConfig, BlockerPolicy

def get_current_metrics():
    """
    TODO: Reemplazar con métricas reales de tu runtime.
    Deben estar en [0, 100]. Si falta alguna, el Blocker la asume 0.
    """
    # Placeholder de ejemplo — ajustá para probar OK/bloqueo:
    return {"trust": 62.5, "cohesion": 28.0, "equity": 71.0}

def critical_action():
    # TODO: reemplazar por la acción realmente crítica (ejecución, efectos en sistema, etc.)
    print(">> Ejecutando acción crítica del runtime...")

if __name__ == "__main__":
    # Política robusta por defecto (más peso a cohesión + score mínimo)
    policy = BlockerPolicy(
        min={"trust": 50, "cohesion": 35, "equity": 50},
        weights={"trust": 0.3, "cohesion": 0.4, "equity": 0.3},
        require_fail_count=1,     # bloquea si al menos 1 métrica < mínimo
        score_threshold=70.0,     # y exige score ponderado ≥ 70
    )
    cfg = BlockerConfig(policy=policy, dry_run=False)  # poné True para calibrar sin bloquear
    blocker = Blocker(config=cfg)

    metrics = get_current_metrics()
    block, reasons = blocker.evaluate(metrics)

    if block:
        print("🚫 BLOQUEADO:", "; ".join(reasons))
        raise SystemExit(1)  # fail-fast: aborta la ejecución
    else:
        if reasons:
            print("⚠️  AVISO:", "; ".join(reasons))
        critical_action()

