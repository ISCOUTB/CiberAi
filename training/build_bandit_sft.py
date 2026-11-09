"""Genera el conjunto SFT con alertas reales de Bandit en formato de produccion.

A diferencia de training/prepare_sft.py, que inventaba una alerta sintetica y la
colocaba al final del codigo, aqui:

- la alerta proviene de ejecutar Bandit de verdad sobre el fragmento (regla,
  CWE, severidad, confianza y mensaje reales, en el mismo formato crudo que usa
  el arnes de evaluacion);
- el prompt usa el formato de produccion (alerta primero, codigo despues), el
  mismo que eval/run_eval.py::prompt_d;
- todos los ejemplos tienen alerta: no hay ejemplos sin alerta;
- el objetivo no contiene finding_id y usa plantillas variadas para la
  explicacion, para no convertir la respuesta en una sola frase memorizada;
- el balance entre VULNERABLE y SAFE se controla con --ratio sobre las clases;
- con --criterio-patron (activo por defecto), el veredicto se adjudica a nivel
  de alerta con el mismo criterio de la auditoria de falsos negativos: B403 sin
  pickle.load/loads, B404 sin shell=True y B311 sin contexto de seguridad se
  etiquetan SAFE aunque el fragmento este marcado como vulnerable.

Solo usa el split de entrenamiento (train_80) y el de validacion (val_total).
El test/holdout no se toca: se verifica por hash que ningun fragmento de
entrenamiento coincida con eval/eval_set.jsonl ni con eval/holdout_set.jsonl.
El split de validacion ES el conjunto de desarrollo, asi que comparte
fragmentos con eval_set.jsonl por construccion (igual que el pipeline
anterior); aun asi se prohibe cualquier coincidencia con el holdout.

Uso:
    python training/build_bandit_sft.py
    python training/build_bandit_sft.py --ratio 2.0 --seed 42
"""

import argparse
import ast
import hashlib
import json
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

SYSTEM = (
    "Eres un analista de seguridad de software. Analizas un fragmento de codigo y decides "
    "si contiene una vulnerabilidad real (VULNERABLE) o si es seguro (SAFE). Responde SOLO "
    "con un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, vector_ataque, correccion."
)

# Formato identico a eval/run_eval.py::TEMPLATE_ALERTA (prompt_d).
TEMPLATE_ALERTA = (
    "Alerta del SAST (triage):\n- Regla: {rule_id}\n- CWE reportado: {cwe_sast}\n"
    "- Severidad: {severity}\n- Confianza: {confidence}\n- Funcion: {function}\n"
    "- Mensaje: {message}\n\nCodigo fuente:\n<code>\n{code}\n</code>\n\nDevuelve el JSON."
)

SNIPPET_RE = re.compile(r"<code_snippet>\n?(.*?)</code_snippet>", re.S)

# Equivalencias CWE como en eval/build_eval_set.py: si el CWE del dataset no
# esta en la clase de equivalencia del CWE del SAST, el objetivo usa el del
# SAST, para no enseñar pares absurdos (p. ej. B105 hardcoded password con
# etiqueta CWE-79 heredada del fragmento).
EQUIV = {
    259: {259, 798, 257}, 798: {798, 259},
    327: {327, 328, 326, 310, 916}, 326: {326, 327}, 328: {328, 327},
    89: {89, 564, 943}, 78: {78, 77, 88}, 79: {79, 80, 116},
    94: {94, 95}, 20: {20}, 601: {601}, 918: {918}, 22: {22, 23},
    502: {502, 915}, 703: {703, 617},
}


def cwe_num(text):
    m = re.search(r"(\d+)", str(text))
    return int(m.group(1)) if m else None


def cwe_objetivo(fila):
    """CWE que aprende el modelo: el del dataset si es compatible, si no el del SAST."""
    b, d = cwe_num(fila["cwe_sast"]), cwe_num(fila["cwe_dataset"])
    if b is not None and d is not None and d in EQUIV.get(b, {b}):
        return fila["cwe_dataset"]
    return fila["cwe_sast"]

# Plantillas variadas: la explicacion cambia con la regla y el veredicto para no
# repetir una sola frase (el SFT anterior tenia 164 explicaciones unicas).
EXPLICACION_VULN = [
    "La regla {rule} se dispara sobre un punto del codigo donde el patron {cwe} es alcanzable: {message}. El fragmento es vulnerable segun la etiqueta del conjunto.",
    "{message}. En este fragmento el patron {cwe} esta presente y no hay mitigacion, por lo que la alerta {rule} corresponde a una vulnerabilidad real.",
    "La alerta {rule} describe {message}. El codigo contiene el flujo tipico de {cwe} sin validacion, asi que la alerta es real.",
    "Es un verdadero positivo de {rule}: {message}. El fragmento exhibe el patron {cwe} de forma explotable.",
    "El analizador marca {rule} por {message}; leyendo el fragmento se confirma el patron {cwe} sin controles, por lo que se mantiene como VULNERABLE.",
    "Hay evidencia directa del defecto ({message}) y la funcion donde cae la linea no aplica sanitizacion: la alerta {rule} es real ({cwe}).",
]
EXPLICACION_SAFE = [
    "La regla {rule} marca {message}, pero en este fragmento el uso es inocuo: no hay entrada no confiable ni flujo que lo convierta en un problema. Es un falso positivo.",
    "{message}. Revisado el contexto, el patron de {rule} no se materializa en un riesgo: el fragmento es seguro para esta alerta.",
    "Falso positivo de {rule}: el mensaje ({message}) describe el patron, pero aqui el dato no proviene de una fuente hostil ni llega a un punto peligroso.",
    "La alerta {rule} se limita al patron sintactico ({message}); el contexto del fragmento no contiene la vulnerabilidad, asi que se recomienda descarte.",
    "{message}. Sin flujo de datos no confiable en el fragmento, la advertencia de {rule} queda como falso positivo.",
    "Es ruido tipico de {rule}: el aviso ({message}) corresponde a un uso legitimo del patron y el fragmento no es vulnerable.",
]
VECTOR_VULN = [
    "Un atacante que controle la entrada que alimenta este flujo puede explotar el patron {cwe} para comprometer la aplicacion.",
    "Explotacion estandar de {cwe}: entrada no confiable que llega al punto marcado por {rule} y ejecuta la accion peligrosa.",
    "Mediante datos hostiles que alcanzan la linea marcada por {rule}, un atacante activa el comportamiento propio de {cwe}.",
    "Si el origen del dato es externo, el patron {cwe} permite manipular la ejecucion en el punto que indica {rule}.",
]
CORRECCION_VULN = [
    "Validar y sanear la entrada antes de usarla en este punto; evitar el patron {cwe} o sustituirlo por la variante segura.",
    "Romper el flujo hacia el punto marcado por {rule}: validar el origen del dato y aplicar la correccion habitual para {cwe}.",
    "Sustituir el patron {cwe} por la alternativa segura recomendada por la regla {rule} y restringir la entrada a valores permitidos.",
    "Aplicar la mitigacion estandar de {cwe} (validacion de entradas, API segura o parametrizacion) en la linea marcada por {rule}.",
]
SAFE_NA = "N/A"


def norm_hash(code):
    """Mismo hash normalizado que dataset/scripts/build_splits.py."""
    return hashlib.sha256("".join(str(code).split()).encode("utf-8")).hexdigest()


def extract_code(prompt):
    m = SNIPPET_RE.search(prompt)
    return m.group(1) if m else None


def enclosing_function(code, line):
    """Nombre de la funcion o clase que contiene la linea (como build_eval_set)."""
    try:
        tree = ast.parse(code)
    except Exception:
        return ""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", 0) or start
            if start <= line <= end and (best is None or start >= best.lineno):
                best = node
    return getattr(best, "name", "")


def run_bandit(tmpdir):
    """Ejecuta Bandit una sola vez sobre el directorio y devuelve las alertas."""
    proc = subprocess.run(
        [sys.executable, "-m", "bandit", "-r", str(tmpdir), "-f", "json", "-q"],
        capture_output=True, text=True, timeout=1200,
    )
    data = json.loads(proc.stdout or "{}")
    return data.get("results", [])


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def adjudicar(fila):
    """Veredicto a nivel de alerta con el criterio de la auditoria de FN.

    La etiqueta del dataset es a nivel de fragmento: un fragmento vulnerable
    convierte en VULNERABLE cualquier alerta sobre el. La auditoria mostro que
    eso mete ruido (B403 de un pickle.dump, B311 de un randint en una demo).
    Con el mismo criterio de patron de docs/AUDITORIA_FN.md, la alerta solo es
    VULNERABLE si la linea senalada corresponde al defecto.
    """
    if not fila["vuln"]:
        return "SAFE"
    code = fila["code"]
    if fila["rule_id"] == "B403":
        return "VULNERABLE" if re.search(r"pickle\.loads?\s*\(", code) else "SAFE"
    if fila["rule_id"] == "B404":
        return "VULNERABLE" if "shell=True" in code else "SAFE"
    if fila["rule_id"] == "B311":
        return "VULNERABLE" if re.search(
            r"token|secret|key|passw|nonce|session|csrf|salt", code, re.I) else "SAFE"
    return "VULNERABLE"


def build_rows(split_path, tmpdir, max_chars):
    """Escribe los fragmentos Python a disco, corre Bandit y arma las filas SFT."""
    src = [r for r in load_jsonl(split_path) if r["meta"]["language"] == "Python"]
    print("{}: {} filas Python".format(Path(split_path).name, len(src)))

    tmpdir.mkdir(parents=True, exist_ok=True)
    for f in tmpdir.glob("*.py"):
        f.unlink()

    mapping = {}
    for i, row in enumerate(src):
        code = extract_code(row["prompt"])
        if code is None or len(code) > max_chars:
            continue
        fname = "t{}.py".format(i)
        (tmpdir / fname).write_text(code, encoding="utf-8")
        mapping[fname] = row

    print("fragmentos escritos:", len(mapping))
    alerts = run_bandit(tmpdir)
    print("alertas de Bandit:", len(alerts))

    filas = []
    for a in alerts:
        row = mapping.get(Path(a["filename"]).name)
        if row is None:
            continue
        meta = row["meta"]
        target_prev = json.loads(row["target"])
        code = extract_code(row["prompt"])
        line = int(a.get("line_number") or 1)
        rule = a.get("test_id")
        cwe_sast = "CWE-{}".format(a.get("issue_cwe", {}).get("id", 0))
        vuln = bool(meta["is_vulnerable"])
        filas.append({
            "code": code,
            "hash": meta["hash"],
            "rule_id": rule,
            "cwe_sast": cwe_sast,
            "severity": a.get("issue_severity"),
            "confidence": a.get("issue_confidence"),
            "message": a.get("issue_text"),
            "function": enclosing_function(code, line),
            "vuln": vuln,
            "cwe_dataset": meta["cwe"],
            "severidad_target": target_prev.get("severidad", "Media"),
        })
    return filas


def make_example(fila, rng, criterio_patron=True):
    """Construye el ejemplo chat en formato de produccion, sin finding_id."""
    rng.seed(hash((fila["hash"], fila["rule_id"])) & 0xFFFFFFFF)
    rule, cwe_s, msg = fila["rule_id"], fila["cwe_sast"], fila["message"]
    vulnerable = fila["vuln"] if not criterio_patron else adjudicar(fila) == "VULNERABLE"
    if vulnerable:
        cwe = cwe_objetivo(fila)
        target = {
            "veredicto": "VULNERABLE",
            "cwe": cwe,
            "severidad": fila["severidad_target"],
            "explicacion": rng.choice(EXPLICACION_VULN).format(rule=rule, cwe=cwe, message=msg),
            "vector_ataque": rng.choice(VECTOR_VULN).format(rule=rule, cwe=cwe),
            "correccion": rng.choice(CORRECCION_VULN).format(rule=rule, cwe=cwe),
        }
    else:
        target = {
            "veredicto": "SAFE",
            "cwe": "Ninguno",
            "severidad": "Info",
            "explicacion": rng.choice(EXPLICACION_SAFE).format(rule=rule, message=msg),
            "vector_ataque": SAFE_NA,
            "correccion": SAFE_NA,
        }
    prompt = TEMPLATE_ALERTA.format(
        rule_id=rule, cwe_sast=cwe_s, severity=fila["severity"],
        confidence=fila["confidence"], function=fila["function"],
        message=msg, code=fila["code"],
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)},
        ],
        "meta": {"language": "Python", "vulnerable": vulnerable, "alert": True},
    }


def balance(examples, ratio, rng):
    """Recorta la clase mayoritaria a ratio veces la minoritaria."""
    vuln = [e for e in examples if e["meta"]["vulnerable"]]
    safe = [e for e in examples if not e["meta"]["vulnerable"]]
    if not vuln or not safe:
        return examples
    cap = int(min(len(vuln), len(safe)) * ratio)
    if len(vuln) > cap:
        vuln = rng.sample(vuln, cap)
    if len(safe) > cap:
        safe = rng.sample(safe, cap)
    out = vuln + safe
    rng.shuffle(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=str(ROOT / "dataset" / "splits" / "train_80.jsonl"))
    ap.add_argument("--val", default=str(ROOT / "dataset" / "splits" / "val_total.jsonl"))
    ap.add_argument("--outdir", default=str(ROOT / "training" / "data"))
    ap.add_argument("--tmp", default=str(ROOT / "training" / "tmp_bandit"))
    ap.add_argument("--ratio", type=float, default=2.0,
                    help="tope clase mayoritaria : minoritaria (2.0 = 2:1)")
    ap.add_argument("--max-chars", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-criterio-patron", action="store_true",
                    help="etiquetar con la verdad del fragmento, sin el criterio de la auditoria")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    outdir, tmp = Path(args.outdir), Path(args.tmp)
    outdir.mkdir(parents=True, exist_ok=True)

    # Guardarrailes de fuga. El holdout esta cerrado para ambos splits. El
    # conjunto de desarrollo (eval_set) esta construido sobre val_total, asi que
    # solo se prohibe para el split de entrenamiento; para val es el propio
    # conjunto de validacion, como en el pipeline anterior.
    hashes_eval = set()
    hashes_holdout = set()
    p = ROOT / "eval" / "eval_set.jsonl"
    if p.exists():
        hashes_eval = {norm_hash(r["code"]) for r in load_jsonl(p)}
    p = ROOT / "eval" / "holdout_set.jsonl"
    if p.exists():
        hashes_holdout = {norm_hash(r["code"]) for r in load_jsonl(p)}

    stats = {}
    for name, split, prohibidos in (
        ("train_sft_real", args.train, hashes_eval | hashes_holdout),
        ("val_sft_real", args.val, hashes_holdout),
    ):
        subtmp = tmp / name
        filas = build_rows(split, subtmp, args.max_chars)
        fugas = [f for f in filas if f["hash"] in prohibidos]
        if fugas:
            raise SystemExit(
                "fuga detectada: {} fragmentos de {} estan en un conjunto prohibido".format(
                    len(fugas), name)
            )
        criterio = not args.no_criterio_patron
        ejemplos = [make_example(f, rng, criterio) for f in filas]
        reclasificadas = sum(
            1 for f, e in zip(filas, ejemplos)
            if f["vuln"] and not e["meta"]["vulnerable"]
        )
        antes = Counter(e["meta"]["vulnerable"] for e in ejemplos)
        ejemplos = balance(ejemplos, args.ratio, rng)
        despues = Counter(e["meta"]["vulnerable"] for e in ejemplos)

        destino = outdir / (name + ".jsonl")
        with destino.open("w", encoding="utf-8", newline="\n") as fh:
            for e in ejemplos:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")

        reglas = Counter(f["rule_id"] for f in filas)
        explicaciones = len({json.loads(e["messages"][2]["content"])["explicacion"] for e in ejemplos})
        stats[name] = {
            "alertas_bandit": len(filas),
            "criterio_patron": criterio,
            "reclasificadas_safe": reclasificadas,
            "antes_balance": dict(antes),
            "despues_balance": dict(despues),
            "ejemplos": len(ejemplos),
            "reglas_top": dict(reglas.most_common(10)),
            "explicaciones_unicas": explicaciones,
        }
        print("{}: {} ejemplos (VULN {} / SAFE {}) | reclasificadas SAFE {} | reglas top {} | explicaciones unicas {}".format(
            name, len(ejemplos), despues.get(True, 0), despues.get(False, 0),
            reclasificadas, reglas.most_common(5), explicaciones))

    (outdir / "bandit_sft_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print("estadisticas:", outdir / "bandit_sft_stats.json")


if __name__ == "__main__":
    main()
