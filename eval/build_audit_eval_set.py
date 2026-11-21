"""Construye un conjunto de evaluacion para la auditoria directa del modelo.

Usa ``dataset/splits/val_total.jsonl`` (desarrollo), nunca el test/holdout. Cada
fila contiene solo el codigo y la verdad del dataset, sin alerta de Bandit, para
medir si el modelo detecta la vulnerabilidad por si mismo.

Uso:
    python dataset/scripts/download_dataset.py
    python dataset/scripts/build_splits.py
    python eval/build_audit_eval_set.py --per-class 300
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
SNIPPET_RE = re.compile(r"<code_snippet>\n?(.*?)</code_snippet>", re.S)


def norm_hash(code):
    return hashlib.sha256("".join(str(code).split()).encode("utf-8")).hexdigest()


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def extract_code(prompt):
    match = SNIPPET_RE.search(prompt)
    return match.group(1) if match else None


def is_python(code):
    try:
        ast.parse(textwrap.dedent(code))
        return True
    except (SyntaxError, ValueError):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default=str(ROOT / "dataset" / "splits" / "val_total.jsonl"),
                    help="Split de desarrollo (nunca el test/holdout)")
    ap.add_argument("--out", default=str(ROOT / "eval" / "audit_eval_set.jsonl"))
    ap.add_argument("--languages", default="Python",
                    help="Lista separada por comas o 'all'")
    ap.add_argument("--per-class", type=int, default=300,
                    help="Maximo de ejemplos por clase (vulnerable / safe)")
    ap.add_argument("--min-chars", type=int, default=40)
    ap.add_argument("--max-chars", type=int, default=8000)
    ap.add_argument("--no-require-parse", action="store_true",
                    help="No descartar fragmentos Python que no parsean")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    split_path = Path(args.split)
    if "holdout" in split_path.name.lower():
        raise SystemExit("El holdout esta reservado; este script solo usa desarrollo.")
    if not split_path.exists():
        raise SystemExit(
            "No existe {}. Ejecuta dataset/scripts/download_dataset.py y "
            "dataset/scripts/build_splits.py.".format(split_path)
        )

    languages = None
    if args.languages.lower() != "all":
        languages = {item.strip().lower() for item in args.languages.split(",") if item.strip()}

    rng = random.Random(args.seed)
    vuln, safe = [], []
    seen = set()
    stats = Counter()
    for row in load_jsonl(split_path):
        stats["filas"] += 1
        language = str(row["meta"].get("language", ""))
        if languages is not None and language.lower() not in languages:
            stats["descartadas_lenguaje"] += 1
            continue
        code = extract_code(row.get("prompt", ""))
        if code is None or len(code) < args.min_chars or len(code) > args.max_chars:
            stats["descartadas_longitud"] += 1
            continue
        if not args.no_require_parse and language.lower() == "python" and not is_python(code):
            stats["descartadas_sintaxis"] += 1
            continue
        digest = norm_hash(code)
        if digest in seen:
            stats["descartadas_duplicado"] += 1
            continue
        seen.add(digest)
        target = json.loads(row["target"])
        item = {
            "id": digest[:16],
            "code": code,
            "language": language,
            "truth": "vulnerable" if row["meta"]["is_vulnerable"] else "safe",
            "cwe_dataset": target.get("cwe", "Ninguno"),
            "severity": target.get("severidad", "Info"),
            "source": row["meta"].get("source", ""),
        }
        (vuln if item["truth"] == "vulnerable" else safe).append(item)

    if args.per_class:
        vuln = rng.sample(vuln, min(len(vuln), args.per_class))
        safe = rng.sample(safe, min(len(safe), args.per_class))
    rows = vuln + safe
    rng.shuffle(rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("filas leidas: {} | descartes: lenguaje {}, longitud {}, sintaxis {}, duplicado {}".format(
        stats["filas"], stats["descartadas_lenguaje"], stats["descartadas_longitud"],
        stats["descartadas_sintaxis"], stats["descartadas_duplicado"]))
    print("conjunto: {} (vulnerable {} / safe {}) -> {}".format(
        len(rows), len(vuln), len(safe), out))
    print("cwe vulnerable:", dict(Counter(r["cwe_dataset"] for r in vuln).most_common(10)))


if __name__ == "__main__":
    main()
