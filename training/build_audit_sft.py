"""Genera SFT para que el modelo detecte vulnerabilidades directamente en el codigo.

A diferencia de ``build_bandit_sft.py``, aqui no hay alerta de Bandit: el prompt
solo contiene el fragmento de codigo, igual que en el modo ``--scanner llm`` del
producto. El objetivo es el mismo JSON que ya usa el triage
(veredicto, cwe, severidad, explicacion, vector_ataque, correccion), sin
``finding_id``.

Solo usa ``train_80`` para entrenar y ``val_total`` para validar. El test/holdout
no se toca: se verifica por hash que ningun fragmento coincida con
``eval/holdout_set.jsonl``. Para entrenar tambien se prohibe ``eval/eval_set.jsonl``
(el conjunto de desarrollo del triage).

Uso:
    python dataset/scripts/download_dataset.py
    python dataset/scripts/build_splits.py
    python training/build_audit_sft.py
    python training/build_audit_sft.py --languages all --ratio 2.0
"""

import argparse
import ast
import hashlib
import json
import random
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

SYSTEM = (
    "Eres un analista de seguridad de software. Analizas un fragmento de codigo y decides "
    "si contiene una vulnerabilidad real (VULNERABLE) o si es seguro (SAFE). Responde SOLO "
    "con un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, vector_ataque, correccion."
)

SNIPPET_RE = re.compile(r"<code_snippet>\n?(.*?)</code_snippet>", re.S)

CWE_NOMBRE = {
    "CWE-20": "validacion de entradas",
    "CWE-22": "path traversal",
    "CWE-78": "inyeccion de comandos",
    "CWE-79": "cross-site scripting",
    "CWE-89": "inyeccion SQL",
    "CWE-94": "inyeccion de codigo",
    "CWE-119": "desbordamiento de bufer",
    "CWE-125": "lectura fuera de limites",
    "CWE-190": "desbordamiento de entero",
    "CWE-200": "exposicion de informacion",
    "CWE-264": "permisos inseguros",
    "CWE-269": "gestion de privilegios",
    "CWE-276": "permisos por defecto inseguros",
    "CWE-284": "control de acceso",
    "CWE-287": "autenticacion debil",
    "CWE-310": "criptografia insegura",
    "CWE-327": "criptografia debil",
    "CWE-330": "aleatoriedad debil",
    "CWE-352": "CSRF",
    "CWE-362": "condicion de carrera",
    "CWE-399": "gestion de recursos",
    "CWE-401": "fuga de memoria",
    "CWE-416": "uso despues de liberar",
    "CWE-434": "carga de archivos sin restriccion",
    "CWE-476": "desreferencia de puntero nulo",
    "CWE-502": "deserializacion insegura",
    "CWE-601": "open redirect",
    "CWE-787": "escritura fuera de limites",
    "CWE-798": "credenciales embebidas",
    "CWE-918": "SSRF",
}

EXPLICACION_VULN = [
    "El fragmento en {language} contiene un patron asociado a {cwe} ({name}) sin una mitigacion visible.",
    "Se identifica el patron de {cwe} ({name}) en el codigo {language}; el dato peligroso no aparece validado.",
    "El codigo {language} presenta {name}, clasificado como {cwe}, en un punto alcanzable por entrada no confiable.",
    "Hay evidencia del defecto {cwe} ({name}) en este fragmento {language}; no se observa el control que lo neutralice.",
    "El fragmento {language} usa una construccion vulnerable a {name} ({cwe}) y no muestra sanitizacion suficiente.",
]
EXPLICACION_SAFE = [
    "El fragmento {language} no presenta un patron vulnerable; no se identifica una entrada no confiable que llegue a un punto peligroso.",
    "Revisado el codigo {language}, el uso observado no materializa una vulnerabilidad en este contexto.",
    "No hay evidencia de explotacion en el fragmento {language}: el flujo peligroso no esta presente.",
    "El fragmento {language} no contiene el defecto etiquetado; el patron observado no es explotable en este contexto.",
]
VECTOR_VULN = [
    "Un atacante que controle la entrada que llega a este fragmento puede explotar {name} ({cwe}).",
    "La explotacion consiste en introducir datos hostiles que alcancen el punto vulnerable de {cwe}.",
    "Si el origen del dato es externo, el patron {name} permite activar el comportamiento propio de {cwe}.",
]
CORRECCION_VULN = [
    "Validar y sanear la entrada antes de usarla y sustituir el patron por la variante segura de {cwe}.",
    "Aplicar la mitigacion estandar de {name}: validacion, parametrizacion o API segura.",
    "Romper el flujo hacia el punto vulnerable y restringir la entrada a valores permitidos.",
]
SAFE_NA = "N/A"


def norm_hash(code):
    return hashlib.sha256("".join(str(code).split()).encode("utf-8")).hexdigest()


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def extract_code(prompt):
    match = SNIPPET_RE.search(prompt)
    return match.group(1) if match else None


def is_python(code):
    """Filtra etiquetas de lenguaje ruidosas del dataset (p. ej. Go marcado Python)."""
    try:
        ast.parse(textwrap.dedent(code))
        return True
    except (SyntaxError, ValueError):
        return False


def target_for(row, rng):
    meta = row["meta"]
    previous = json.loads(row["target"])
    language = meta["language"]
    vulnerable = bool(meta["is_vulnerable"])
    cwe = str(previous.get("cwe") or meta.get("cwe") or "Ninguno")
    if vulnerable and cwe == "Ninguno":
        return None
    name = CWE_NOMBRE.get(cwe, cwe)
    if vulnerable:
        severity = str(previous.get("severidad") or "Media").capitalize()
        if severity not in {"Alta", "Media", "Baja", "Info"}:
            severity = "Media"
        correction = str(previous.get("correccion") or "").strip()
        if not correction or correction == "N/A":
            correction = rng.choice(CORRECCION_VULN).format(cwe=cwe, name=name)
        target = {
            "veredicto": "VULNERABLE",
            "cwe": cwe,
            "severidad": severity,
            "explicacion": rng.choice(EXPLICACION_VULN).format(
                language=language, cwe=cwe, name=name),
            "vector_ataque": rng.choice(VECTOR_VULN).format(cwe=cwe, name=name),
            "correccion": correction,
        }
    else:
        target = {
            "veredicto": "SAFE",
            "cwe": "Ninguno",
            "severidad": "Info",
            "explicacion": rng.choice(EXPLICACION_SAFE).format(
                language=language, cwe=cwe, name=name),
            "vector_ataque": SAFE_NA,
            "correccion": SAFE_NA,
        }
    return target


def example_for(row, prompt, target):
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)},
        ],
        "meta": {
            "language": row["meta"]["language"],
            "vulnerable": target["veredicto"] == "VULNERABLE",
            "cwe": target["cwe"],
            "hash": row["meta"]["hash"],
            "source": row["meta"].get("source", ""),
            "task": "audit",
        },
    }


def balance(examples, ratio, rng):
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


def load_split(path, languages, min_chars, max_chars, forbidden, rng, require_parse=True):
    stats = Counter()
    examples = []
    seen = set()
    if not Path(path).exists():
        raise SystemExit(
            "No existe {}. Ejecuta dataset/scripts/download_dataset.py y "
            "dataset/scripts/build_splits.py.".format(path)
        )
    for row in load_jsonl(path):
        stats["filas"] += 1
        language = str(row["meta"].get("language", ""))
        if languages is not None and language.lower() not in languages:
            stats["descartadas_lenguaje"] += 1
            continue
        code = extract_code(row.get("prompt", ""))
        if code is None:
            stats["descartadas_sin_code"] += 1
            continue
        if len(code) < min_chars or len(code) > max_chars:
            stats["descartadas_longitud"] += 1
            continue
        if require_parse and language.lower() == "python" and not is_python(code):
            stats["descartadas_sintaxis"] += 1
            continue
        digest = norm_hash(code)
        if digest in forbidden:
            stats["descartadas_fuga"] += 1
            continue
        if digest in seen:
            stats["descartadas_duplicado"] += 1
            continue
        seen.add(digest)
        target = target_for(row, rng)
        if target is None:
            stats["descartadas_sin_cwe"] += 1
            continue
        examples.append(example_for(row, row["prompt"], target))
    stats["antes_balance_vuln"] = sum(1 for e in examples if e["meta"]["vulnerable"])
    stats["antes_balance_safe"] = sum(1 for e in examples if not e["meta"]["vulnerable"])
    return examples, stats


def mix_triage(examples, path, fraction, rng, stats):
    if fraction <= 0 or not Path(path).exists():
        stats["triage_mezclados"] = 0
        return examples
    triage = load_jsonl(path)
    count = min(len(triage), int(len(examples) * fraction))
    if count <= 0:
        stats["triage_mezclados"] = 0
        return examples
    mixed = rng.sample(triage, count)
    for example in mixed:
        example.setdefault("meta", {})["task"] = "triage"
    out = examples + mixed
    rng.shuffle(out)
    stats["triage_mezclados"] = count
    return out


def write_split(name, path_in, args, forbidden, outdir, rng):
    languages = None
    if args.languages.lower() != "all":
        languages = {item.strip().lower() for item in args.languages.split(",") if item.strip()}
    examples, stats = load_split(path_in, languages, args.min_chars, args.max_chars,
                                 forbidden, rng, require_parse=not args.no_require_parse)
    if not examples:
        raise SystemExit("No quedaron ejemplos en {} con los filtros actuales.".format(path_in))
    stats["antes_balance_total"] = len(examples)
    examples = balance(examples, args.ratio, rng)
    if args.limit and len(examples) > args.limit:
        examples = rng.sample(examples, args.limit)
    stats["despues_balance_vuln"] = sum(1 for e in examples if e["meta"]["vulnerable"])
    stats["despues_balance_safe"] = sum(1 for e in examples if not e["meta"]["vulnerable"])
    triage_path = args.triage_train if name == "train" else args.triage_val
    examples = mix_triage(examples, triage_path, args.triage_frac, rng, stats)
    stats["ejemplos"] = len(examples)
    stats["lenguajes"] = dict(Counter(e["meta"]["language"] for e in examples))
    stats["cwe_top"] = dict(Counter(e["meta"]["cwe"] for e in examples
                                    if e["meta"]["vulnerable"]).most_common(10))
    destination = outdir / (name + "_audit.jsonl")
    with destination.open("w", encoding="utf-8", newline="\n") as fh:
        for example in examples:
            fh.write(json.dumps(example, ensure_ascii=False) + "\n")
    print("{}: {} ejemplos (VULN {} / SAFE {}) | triage mezclado {} | {}".format(
        name, len(examples), stats["despues_balance_vuln"],
        stats["despues_balance_safe"], stats["triage_mezclados"], destination))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=str(ROOT / "dataset" / "splits" / "train_80.jsonl"))
    ap.add_argument("--val", default=str(ROOT / "dataset" / "splits" / "val_total.jsonl"))
    ap.add_argument("--outdir", default=str(ROOT / "training" / "data"))
    ap.add_argument("--languages", default="Python",
                    help="Lista separada por comas o 'all' (por defecto: Python)")
    ap.add_argument("--ratio", type=float, default=2.0,
                    help="Tope clase mayoritaria : minoritaria (2.0 = 2:1)")
    ap.add_argument("--limit", type=int, default=0,
                    help="Maximo de ejemplos por split despues del balance (0 = todos)")
    ap.add_argument("--min-chars", type=int, default=40)
    ap.add_argument("--max-chars", type=int, default=8000)
    ap.add_argument("--no-require-parse", action="store_true",
                    help="No descartar fragmentos Python que no parsean (el dataset tiene etiquetas ruidosas)")
    ap.add_argument("--triage-train", default=str(ROOT / "training" / "data" / "train_sft_real.jsonl"))
    ap.add_argument("--triage-val", default=str(ROOT / "training" / "data" / "val_sft_real.jsonl"))
    ap.add_argument("--triage-frac", type=float, default=0.5,
                    help="Ejemplos de triage a mezclar por cada ejemplo de auditoria (0 = no mezclar)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    hashes_eval = set()
    hashes_holdout = set()
    eval_path = ROOT / "eval" / "eval_set.jsonl"
    holdout_path = ROOT / "eval" / "holdout_set.jsonl"
    if eval_path.exists():
        hashes_eval = {norm_hash(row["code"]) for row in load_jsonl(eval_path)}
    if holdout_path.exists():
        hashes_holdout = {norm_hash(row["code"]) for row in load_jsonl(holdout_path)}

    stats = {}
    stats["train"] = write_split("train", args.train, args,
                                 hashes_eval | hashes_holdout, outdir, rng)
    stats["val"] = write_split("val", args.val, args, hashes_holdout, outdir, rng)
    stats["config"] = {
        "languages": args.languages,
        "ratio": args.ratio,
        "limit": args.limit,
        "min_chars": args.min_chars,
        "max_chars": args.max_chars,
        "require_parse": not args.no_require_parse,
        "triage_frac": args.triage_frac,
        "hashes_eval": len(hashes_eval),
        "hashes_holdout": len(hashes_holdout),
    }
    destination = outdir / "audit_sft_stats.json"
    destination.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print("estadisticas:", destination)


if __name__ == "__main__":
    main()
