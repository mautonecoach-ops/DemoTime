# LEXO v0.1 – MVP monolítico
# Ejecutar: python main.py demo_es.lexo --lang=es
#           python main.py demo_en.lexo --lang=en
# Flags globales de control

# =========================
# IMPORTS
# =========================
# Standard library
import sys
import os
import re
import json
import math
import networkx as nx
import matplotlib
matplotlib.use("Agg")  # evita crash por display en Replit
import matplotlib.pyplot as plt
import warnings
import argparse
import hashlib

parser = argparse.ArgumentParser()
parser.add_argument("file", help="Archivo fuente .lexo")
parser.add_argument("--lang", default="es", help="Idioma")
args = parser.parse_args()

warnings.filterwarnings(
    "ignore",
    message="This figure includes Axes that are not compatible with tight_layout",
    category=UserWarning
)
# =========================
# Globals y helpers ETHICS (mínimo)
# =========================
ETHICS = {}                 # se completa desde ethics.yaml
ETHICS_LOADED = False       # para no cargar dos veces
ETHICS_ALREADY_EMITTED = False # para no imprimir alertas duplicadas
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
                alerts.append(f"[ETHICS] La confianza cayó {drop_pct:.1f}% (> {ETHICS['max_trust_drop_pct']}%). Revisar la intervención.")

        # 2) equidad mínima
        if new_metrics["equity"] < ETHICS["min_equity_score"]:
            alerts.append(f"[ETHICS] La equidad bajó a {new_metrics['equity']:.1f} (< {ETHICS['min_equity_score']}). Riesgo de concentración de recursos.")
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
                f"Sugerencia: cuidar_red('{u}' o '{v}', intensity=ALTA)."
            )

    # 2) Aumento de inequidad (gini)
    if prev_snap["gini"] > 0:
        inc_pct = (new_snap["gini"] - prev_snap["gini"]) * 100.0 / prev_snap["gini"]
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
    low_nodes = [n for n, t in new_snap["node_trust"].items() if t < ETHICS["low_node_trust"]]
    if low_nodes:
        sample = ", ".join(list(low_nodes)[:3])
        alerts.append(
            f"[ETHICS] Nodos con confianza muy baja (<{ETHICS['low_node_trust']}): {sample}..."
            f" Sugerencia: cuidar_red(target), mentorías o pequeñas victorias visibles."
        )

    # 5) Vínculos con confianza muy baja
    low_edges = [(u, v) for (u, v), t in new_snap["edges"].items() if t < ETHICS["low_edge_trust"]]
    if low_edges:
        u, v = low_edges[0]
        alerts.append(
            f"[ETHICS] Hay vínculos con confianza muy baja (<{ETHICS['low_edge_trust']}), ej. {u}–{v}. "
            f"Sugerencia: cuidar_red('{u}' o '{v}', intensity=MEDIA/ALTA)."
        )

    # 6) Nodos aislados / grado insuficiente
    isolated = [n for n, d in new_snap["degrees"].items() if d < ETHICS["min_node_degree"]]
    if isolated:
        sample = ", ".join(list(isolated)[:3])
        alerts.append(
            f"[ETHICS] Nodos aislados o casi aislados: {sample}..."
            f" Sugerencia: conectar(nodo, 'Barrio Sur') o introducir puentes."
        )

    # 7) Recursos por debajo del mínimo
    starved = [n for n, r in new_snap["res_by_node"].items() if r < ETHICS["min_resources_per_node"]]
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

def save_report_json(metrics, alerts, path="report.json"):
    data = {"metrics": metrics, "alerts": alerts}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Reporte JSON guardado en {path}")

def save_report_csv(metrics, alerts=None, path="report.csv"):
    with open(path, "w", newline="", encoding="utf-8") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["trust", "cohesion", "equity"])
        writer.writerow([metrics["trust"], metrics["cohesion"], metrics["equity"]])
        if alerts:
            writer.writerow([])
            writer.writerow(["ALERTS"])
            for a in alerts:
                writer.writerow([a])
    print(f"[OK] Reporte CSV actualizado en {path}")

def evaluate_ethics(rt, start_snap, final_snap, start_metrics, final_metrics):
    """
    Wrapper del linter ético v2: compara estado inicial vs final y devuelve lista de alertas.
    """
    # Asume que tenés lint_compare_v2(prev_snap, new_snap, prev_m, new_m) ya definido.
    return lint_compare_v2(start_snap, final_snap, start_metrics, final_metrics)

# =========================
# Parser súper simple para el MVP
# - reconoce bloques por llaves
# - reconoce las sentencias clave por prefix
# =========================
_bool_like = {"true": True, "false": False, "TRUE": True, "FALSE": False}
_ident_like = {"ALTO": "HIGH", "MEDIA": "MEDIUM", "BAJA": "LOW", "ALTA": "HIGH",
               "HIGH":"HIGH","MEDIUM":"MEDIUM","LOW":"LOW"}

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
        if len(p) >= 2 and ((p[0] == '"' and p[-1] == '"') or (p[0] == "'" and p[-1] == "'")):
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
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
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

def parse_properties(block_text: str):
    """
    Recibe el contenido de un bloque {...} (o un fragmento similar)
    y devuelve dict con pares clave:valor.
    Soporta:
      - clave: número | "cadena" | 'cadena' | [lista] | identificador
      - comas opcionales al final de línea
    """
    # Si viene con llaves por error, recortalas
    bt = block_text.strip()
    if bt.startswith("{") and bt.endswith("}"):
        bt = bt[1:-1]

    props = {}
    # dividir por líneas o ';' o comas exteriores simples
    # estrategia simple: separar por nuevas líneas o comas top-level
    # (como las propiedades no tienen sub-bloques, alcanza)
    # también aceptamos formato "clave: valor, clave2: valor2"
    # → reemplazar saltos por comas para unificar
    bt_norm = bt.replace("\n", ",")
    # partir por comas y luego recomponer pares con ':'
    for chunk in [c.strip() for c in bt_norm.split(",") if c.strip()]:
        if ":" not in chunk:
            continue
        k, v = chunk.split(":", 1)
        key = k.strip()
        val = _parse_value(v)
        props[key] = val
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
        if i+1 < n and src[i] == "/" and src[i+1] == "/":
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
    "max_trust_drop_pct": 10.0,   # alerta si cae >10% la confianza promedio
    "min_equity_score": 60.0,     # alerta si la equidad baja de 60/100
}
ETHICS.update({
    "max_edge_trust_drop": 20.0,     # alerta si algún vínculo cae >20 pts
    "max_gini_increase_pct": 10.0,   # alerta si la inequidad (gini) sube >10%
    "min_avg_trust": 60.0,          # alerta si la confianza promedio cae por debajo
    "low_node_trust": 55.0,         # si algún nodo queda con confianza muy baja
    "low_edge_trust": 50.0,         # si algún vínculo queda con confianza muy baja
    "min_node_degree": 1,           # nodos aislados o con grado 0/1 llaman la atención
    "min_resources_per_node": 2.0,  # umbral mínimo de recursos por nodo
    "max_resource_share": 0.50,     # si un solo nodo concentra >40% de los recursos
})

WS = r"[ \t]*"
IDENT = r"[A-Za-zÁÉÍÓÚáéíóúÑñ_][A-Za-z0-9ÁÉÍÓÚáéíóúÑñ_\- ]*"

def startswith_token(src: str, i: int, token: str) -> bool:
    if not src.startswith(token, i):
        return False
    # límite por la izquierda
    if i > 0 and (src[i-1].isalnum() or src[i-1] == "_"):
        return False
    # límite por la derecha
    j = i + len(token)
    if j < len(src) and (src[j].isalnum() or src[j] == "_"):
        return False
    return True

def extract_block(src: str, start_idx: int):
    """
    Extrae el texto de un bloque {...} desde src[start_idx] == '{'
    Retorna (contenido_sin_llaves, indice_despues_del_bloque)
    """
    assert src[start_idx] == "{", "extract_block: se esperaba '{'"
    i = start_idx
    depth = 0
    i += 1  # saltamos la primera '{'
    start_content = i
    while i < len(src):
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            if depth == 0:
                # bloque cierra aquí
                content = src[start_content:i]
                return content, i + 1  # posición después de la '}' final
            else:
                depth -= 1
        i += 1
    raise ValueError("extract_block: bloque '{...}' sin cierre")
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
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    # permitir espacios/comentarios simples
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r'^\s*"([^"]+)"\s*,\s*"([^"]+)"\s*$', s)
    if not m:
        raise ValueError(f"CONNECT: argumentos inválidos → {s!r}")
    return m.group(1), m.group(2)

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
            if len(name_text) < 2 or name_text[0] not in "\"'" or name_text[-1] not in "\"'":
                raise ValueError("CREATE_NODE name must be quoted")
            node_name = name_text[1:-1]
            i = after_paren

            i = skip_ws_and_comments(src, i)
            # bloque de props
            brace_pos = src.find("{", i)
            if brace_pos == -1:
                raise ValueError("Expected properties block { ... } after CREATE_NODE name")
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
                ctx = src[max(0, i-40):min(n, i+80)]
                raise ValueError(f"Expected '(' after CONNECT at pos {i}. Context: {ctx!r}")

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
            m = re.match(rf"STRENGTHEN_TIES{WS}\({WS}\"([^\"]+)\"{WS}\){WS}", src[i:], flags=re.S)
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
                raise ValueError("LAUNCH_INITIATIVE expects a quoted initiative name")
            # leemos "...":
            j = i + 1
            quote = src[i]
            while j < n and src[j] != quote:
                j += 1
            if j >= n:
                raise ValueError("Unclosed initiative name")
            iname = src[i+1:j]
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

            ast.actions.append(("IF", cond_text.strip(), then_block, else_block))
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
                raise ValueError("Expected '(' after MEASURE_IMPACT target type")
            name_text, after_paren = extract_parens(src, i)
            name_text = name_text.strip()
            if len(name_text) < 2 or name_text[0] not in "\"'" or name_text[-1] not in "\"'":
                raise ValueError("MEASURE_IMPACT target name must be quoted")
            target_name = name_text[1:-1]
            i = after_paren

            # permitir IN/EN
            i = skip_ws_and_comments(src, i)
            if startswith_token(src, i, "IN") or startswith_token(src, i, "EN"):
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
                U = src.upper().replace("Ó", "O").replace("Í","I").replace("É","E").replace("Á","A").replace("Ú","U")
                dim_pos = U.find("DIMENSION", i)
                if dim_pos == -1:
                    raise ValueError("Expected DIMENSION(...) in MEASURE_IMPACT")
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

            ast.actions.append(("MEASURE_IMPACT", target_type, target_name, dims))
            continue

        # ---------------------- SHOW_NETWORK ----------------
        if startswith_token(src, i, "SHOW_NETWORK"):
            i += len("SHOW_NETWORK")
            ast.actions.append(("SHOW_NETWORK",))
            continue

        # Si no matcheó nada, avanzar 1 char para no quedar en loop infinito
        i += 1
    
    return ast
with open(args.file, "r", encoding="utf-8") as f:
    source = f.read()

norm = normalize_source(source, args.lang)   # <- DEBE existir esta función y devolver str
ast = parse_program(norm)
if ast is None:
    print("[ERROR] parse_program devolvió None. Revisá el 'return ast' al final y la indentación.")
    sys.exit(1)

# =========================
# RUNTIME / EJECUCIÓN
# =========================
    # Mapa simple de intensidades → incrementos
_INT_MAP = {
        "ALTA":  (10,  6),  # (bump_trust_node, bump_conf_edge)
        "MEDIA": ( 6,  4),
        "BAJA":  ( 3,  2),
    }

class Runtime:
    def __init__(self):
        self.graph = nx.Graph()

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
        if x in ("BAJA", "LOW"):  return "BAJA"
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
        ndata.setdefault("trust", float(props.get("trust", props.get("confianza", 50.0))))
        ndata.setdefault("resources", float(props.get("resources", props.get("recursos", 0.0))))

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
        return {"ALTA": (10,6), "MEDIA": (6,4), "BAJA": (3,2)}.get(norm, (6,4))
    # --- Acciones con efecto real ---

    def strengthen_ties(self, target, props):
            print(f"[DEBUG] strengthen_ties → target={target}, props={props}")
            if not self.graph.has_node(target): return
            norm = self._norm_intensity(props.get("intensidad") or props.get("intensity"))
            bump_node, bump_edge = self._int_bumps(norm)

        # subir confianza del nodo
            node_conf = self.graph.nodes[target].get("confianza", self.graph.nodes[target].get("trust", 50))
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
        print(f"[DEBUG] care_network → target={target}, intensity={intensity}, plan={mitigation_plan}")
        if not self.graph.has_node(target): return
        norm = self._norm_intensity(intensity)
        bump_node, bump_edge = self._int_bumps(norm)

        # subir confianza del nodo
        node_conf = self.graph.nodes[target].get("confianza", self.graph.nodes[target].get("trust", 50))
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


    def redistribute_resources(self, giver, receiver, fraction=0.2, min_left=2.0):
        if not (self.graph.has_node(giver) and self.graph.has_node(receiver)):
            return
        g = self._get_node_resources(giver)
        r = self._get_node_resources(receiver)
        fraction = float(fraction); min_left = float(min_left)

        if g <= min_left:
            print(f"[DEBUG] redistribute_resources → SIN MOVIMIENTO (g={g}, min_left={min_left})")
            return

        move = max(0.0, min(g - min_left, g * fraction))
        if move <= 0:
            print(f"[DEBUG] redistribute_resources → SIN MOVIMIENTO (g={g}, fraction={fraction})")
            return

        self._set_node_resources(giver, g - move)
        self._set_node_resources(receiver, r + move)
        print(f"[DEBUG] redistribute_resources → moved={move:.2f}, {giver}:{g - move:.2f} → {receiver}:{r + move:.2f}")


    def launch_initiative(self, target: str, inc: int = 15):
        """
        Sube confianza de la comunidad objetivo (o nodo objetivo si existiera con ese nombre).
        """
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
        trust = sum(trusts)/len(trusts) if trusts else 0.0

        # Cohesion: clustering/transitividad (0..1) → 0..100
        try:
            coh = nx.transitivity(self.graph)  # global clustering
            cohesion = 100.0 * float(coh)
        except Exception:
            cohesion = 0.0

        # Equity: 100*(1 - Gini) sobre resources de PERSON + COMMUNITY
        resc = []
        for n, d in self.graph.nodes(data=True):
            if d.get("kind") == "PERSON":       # ← filtra solo personas
                resc.append(self._get_node_resources(n))

        equity = 0.0
        if resc:
            xs = sorted(float(x) for x in resc)
            s = sum(xs)
            if s > 0:
                n = len(xs)
                # Gini robusto
                cum = 0.0
                for i, x in enumerate(xs, start=1):
                    cum += i * x
                gini = (2*cum)/(n*s) - (n+1)/n
                gini = max(0.0, min(1.0, gini))
                equity = 100.0 * (1.0 - gini)
        print("[DEBUG] measure.trusts =", [round(self._get_node_trust(n),1) for n in self.graph.nodes()])
        print("[DEBUG] measure.resources =", [round(self._get_node_resources(n),2) for n in self.graph.nodes()])

        return {"trust": round(trust, 2), "cohesion": round(cohesion, 2), "equity": round(equity, 2)}


    def show_network(self, path="network.png", title=None):
        import matplotlib.pyplot as plt
        plt.figure(figsize=(6,6))
        pos = nx.spring_layout(self.graph, seed=42)
        nx.draw(self.graph, pos, with_labels=True, node_size=800, node_color="lightblue", font_size=8)

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
    def gini(values):
        vals = [float(x) for x in values if float(x) >= 0]
        if not vals:
         return 0.0
        vals = sorted(vals)
        n = len(vals)
        cum = 0.0
        for i, x in enumerate(vals, 1):
            cum += i * x
        s = sum(vals)
        if s == 0:
            return 0.0
        return (2 * cum) / (n * s) - (n + 1) / n


# =========================
# EJECUCIÓN DEL AST
# =========================
final_metrics = None

def execute(rt: Runtime, ast: AST, finalize: bool = True):
    # 1) Declaraciones
    for kind, type_name, name, props in ast.decls:
        if kind == "CREATE_NODE":
            rt.ensure_node(type_name.upper(), name, props)

    # 2) Snapshot/métricas INICIALES (para este nivel)
    start_m    = rt.measure()
    start_snap = snapshot_state(rt)
    
    # 3) Acciones
    for act in ast.actions:
        tag = act[0]

        if tag == "CONNECT":
            _, a, b, props = act
            rt.connect(a, b, props)
            continue

        if tag == "STRENGTHEN_TIES":
            _, target, props = act
            rt.strengthen_ties(target, dict(props))
            continue

        if tag == "LAUNCH_INITIATIVE":
            _, iname, props = act
            target = props.get("target") or props.get("community") or props.get("COMMUNITY")
            inc = int(props.get("trust_boost", 15))
            if target:
                rt.launch_initiative(target, inc=inc)
            else:
                for n, d in rt.graph.nodes(data=True):
                    if d.get("kind") == "COMMUNITY":
                        rt.launch_initiative(n, inc=inc)
            continue

        if tag == "REDISTRIBUTE_RESOURCES":
            _, giver, receiver, props = act
            p = dict(props)
            rt.redistribute_resources(
                giver, receiver,
                fraction=float(props.get("fraction", props.get("fraccion", 0.2))),
                min_left=float(props.get("min_left", props.get("minimo", 2.0)))
            )
            continue

        if tag == "CARE_NETWORK":
            _, target, props = act
            rt.care_network(
                target,
                intensity=(props.get("intensity") or props.get("intensidad") or "MEDIA"),
                mitigation_plan=props.get("mitigation_plan") or props.get("plan_mitigacion")
            )
            continue

        if tag == "IF":
            _, cond, then_code, else_code = act
            if eval_condition(rt, cond):
                ast_sub = parse_program(then_code)
                execute(rt, ast_sub, finalize=False)  # ⬅️ nivel interno
            else:
                ast_sub = parse_program(else_code)
                execute(rt, ast_sub, finalize=False)  # ⬅️ nivel interno
            continue

        if tag == "MEASURE_IMPACT":
            _, target_type, target_name, dims = act
            metrics = rt.measure()
            sel = {k: metrics[k] for k in dims if k in metrics}
            print(">> Impacto:", json.dumps(sel, ensure_ascii=False))
            rt.final_metrics = metrics            # ⬅️ GUARDAR AQUÍ
            continue


        if tag == "SHOW_NETWORK":
            rt.show_network(title="LEXO v0.1 – Red")
            continue

    # 4) Linter final-only + reportes (SOLO si finalize=True)
    if finalize:
        final_m    = rt.measure()
        final_snap = snapshot_state(rt)
        alerts = evaluate_ethics(rt, start_snap, final_snap, start_m, final_m)
        print_alerts(alerts)
        save_report_json(final_m, alerts, path="report.json")
        save_report_csv(final_m, alerts, path="report.csv")

# main.py
from core_helpers import (
    begin_run, end_run,
    load_ethics_thresholds, blocker_decision,
    write_blockade_summary, append_changelog,
    ensure_whatif_never_mutates,
)

def execute_final(rt, run_id, save_network=True):
    # 1) recuperar métricas finales del runtime
    final_metrics = getattr(rt, "final_metrics", None)

    # 2) validar que existan métricas
    if final_metrics is None:
        print("[EXEC_FINAL] No hay métricas finales; abortando.")
        return ("BLOCKED", [("metrics", 0, "present")])

    # 3) (placeholder) asegurar que WHAT_IF no muta estado real
    ensure_whatif_never_mutates(rt)

    # 4) cargar umbrales y decidir
    thresholds = load_ethics_thresholds("ethics.yaml")
    print("[ETHICS] Umbrales cargados:", thresholds)
    fails = blocker_decision(final_metrics, thresholds)

    # 5) persistir artefactos de cierre
    write_blockade_summary(run_id, final_metrics, thresholds, fails)
    append_changelog("BLOCKED" if fails else "OK", final_metrics, fails, "CHANGELOG.md")

    # 6) devolver estado para que main() haga sys.exit(0/1)
    if fails:
        print("🚫 BLOQUEADO por ética/umbrales.")
        return ("BLOCKED", fails)
    else:
        print("✅ OK (cumple umbrales éticos).")
        return ("OK", [])




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
    txt = txt.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")

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
    op   = m.group(4)
    value = float(m.group(5))

    # 6) Obtener valor actual
    if attr == "trust":
        cur = float(rt.graph.nodes.get(name, {}).get("trust", 50.0))
    else:
        cur = float(rt.measure()[attr])

    # 7) Evaluar
    if op == "<":   return cur < value
    if op == "<=":  return cur <= value
    if op == ">":   return cur > value
    if op == ">=":  return cur >= value
    if op == "==":  return abs(cur - value) < 1e-9
    if op == "!=":  return abs(cur - value) > 1e-9
    print(f"[WARN] Operador no reconocido: {op} → False")
    return False

# --- Snapshot del estado para el linter ético v0.2 ---
def snapshot_state(rt):
    # Confianza por arista
    edges = {(u, v): float(d.get("trust", 50.0)) for u, v, d in rt.graph.edges(data=True)}
    # Recursos por nodo
    res_by_node = {n: float(rt.graph.nodes[n].get("resources", 0.0)) for n in rt.graph.nodes()}
    resources = list(res_by_node.values())
    total_res = sum(resources) if resources else 0.0
    top_share = (max(resources) / total_res) if total_res > 0 else 0.0
    # Confianza por nodo
    node_trust = {n: float(rt.graph.nodes[n].get("trust", 50.0)) for n in rt.graph.nodes()}
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

# --- fin snapshot ---
def print_alerts(alerts):
         """
         Imprime alertas del linter con deduplicación simple.
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
# MAIN
# =========================
def main():
    apply_ethics_yaml_once("ethics.yaml")

    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="demo_es.lexo", help="Archivo .lexo")
    parser.add_argument("--lang", choices=["es", "en"], default="es")
    args = parser.parse_args()

    import os, hashlib, json
    if not os.path.exists(args.file):
        print(f"[ERROR] No existe {args.file}. Corré: python main.py TU_ARCHIVO.lexo --lang=es")
        sys.exit(1)

    # DEBUG de archivo leído (opcional pero útil)
print(f"[DEBUG] leyendo: {args.file}, bytes={len(source)}, sha1={hashlib.sha1(source.encode()).hexdigest()[:10]}")
print("[DEBUG] primeras líneas:\n" + "\n".join(source.splitlines()[:6]))

    
ast  = parse_program(norm)
if ast is None:
        print("[ERROR] parse_program devolvió None (revisá indentación y 'return ast').")
        sys.exit(1)

rt = Runtime()
execute(rt, ast, finalize=True)

# === EXEC FINAL BLOCKER ===
def load_ethics_thresholds(path="ethics.yaml"):
    import yaml, os
    if not os.path.exists(path):
        # valores por defecto “razonables” si el archivo no existe
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
    if metrics["trust"]   < thresholds["min_trust"]:    fails.append(("trust",   metrics["trust"],   thresholds["min_trust"]))
    if metrics["cohesion"]< thresholds["min_cohesion"]: fails.append(("cohesion",metrics["cohesion"],thresholds["min_cohesion"]))
    if metrics["equity"]  < thresholds["min_equity"]:   fails.append(("equity",  metrics["equity"],  thresholds["min_equity"]))
    return fails

def write_blockade_summary(metrics, thresholds, fails, path="blockade_summary.json"):
    import json, time
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": metrics,
        "thresholds": thresholds,
        "status": "BLOCKED" if fails else "OK",
        "fails": [{"metric": m, "value": v, "required": r} for (m, v, r) in fails],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def append_changelog(status, metrics, fails, path="CHANGELOG.md"):
    import time, os
    line = f"- {time.strftime('%Y-%m-%d %H:%M:%S')} exec-final: {status} | trust={metrics['trust']:.2f} cohesion={metrics['cohesion']:.2f} equity={metrics['equity']:.2f}"
    if fails:
        detail = " ; ".join([f"{m}={v:.2f} < {r:.2f}" for (m, v, r) in fails])
        line += f" | fails: {detail}"
    line += "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
# --- ETHICS / BLOCKER ---
thresholds = load_ethics_thresholds("ethics.yaml")
print("[ETHICS] Umbrales cargados:", thresholds)

final_metrics = getattr(rt, "final_metrics", None)   # ⬅️ TRAERLAS DESDE rt

if final_metrics is None:
    print("[ETHICS] No se calcularon métricas, no se puede evaluar blocker.")
    import sys
    sys.exit(1)

fails = blocker_decision(final_metrics, thresholds)
write_blockade_summary(final_metrics, thresholds, fails, "blockade_summary.json")
append_changelog("BLOCKED" if fails else "OK", final_metrics, fails, "CHANGELOG.md")

if fails:
    print("🚫 BLOQUEADO por ética/umbrales.")
    import sys
    sys.exit(1)
else:
    print("✅ OK (cumple umbrales éticos).")


m = rt.measure()
print("== MÉTRICAS FINALES ==")
print(json.dumps(m, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

