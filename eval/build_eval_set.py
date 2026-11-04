import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]

# El split de validacion se usa para iterar. El split test esta reservado para
# Sprint 7 y se evalua una sola vez: por eso exige --confirm-holdout y escribe
# en un archivo distinto, sin pisar eval_set.jsonl.
SPLITS = {
    "validation": {
        "parquet": "validation-00000-of-00001.parquet",
        "tmp": "tmp_py",
        "out": "eval_set.jsonl",
    },
    "test": {
        "parquet": "test-00000-of-00001.parquet",
        "tmp": "tmp_py_holdout",
        "out": "holdout_set.jsonl",
    },
}

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


def cwe_match(bandit_cwe, dataset_cwe):
    b = cwe_num(bandit_cwe)
    d = cwe_num(dataset_cwe)
    if b is None or d is None:
        return False
    return d in EQUIV.get(b, {b})


def enclosing_function(path, line):
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=sorted(SPLITS), default="validation",
                    help="validation para iterar; test solo en Sprint 7")
    ap.add_argument("--confirm-holdout", action="store_true",
                    help="confirma que se abre el test reservado (evaluacion unica)")
    args = ap.parse_args()

    if args.split == "test" and not args.confirm_holdout:
        raise SystemExit(
            "El split test esta reservado para Sprint 7 y se evalua una sola vez. "
            "Si es el momento, repetir con --split test --confirm-holdout."
        )

    cfg = SPLITS[args.split]
    tmp = ROOT / "eval" / cfg["tmp"]
    out = ROOT / "eval" / cfg["out"]

    df = pd.read_parquet(ROOT / "dataset" / "data" / cfg["parquet"])
    py = df[df["language"].astype(str).str.lower() == "python"].copy()
    print("funciones Python en {}:".format(args.split), len(py))

    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("*.py"):
        f.unlink()

    mapping = {}
    for i, row in py.iterrows():
        name = "f{}.py".format(i)
        path = tmp / name
        path.write_text(str(row["code"]), encoding="utf-8", errors="replace")
        mapping[name] = i

    proc = subprocess.run([sys.executable, "-m", "bandit", "-r", str(tmp), "-f", "json", "-q"],
                          capture_output=True, text=True, timeout=600)
    data = json.loads(proc.stdout or "{}")
    alerts = data.get("results", [])
    print("alertas de Bandit:", len(alerts))

    rows = []
    counts = {"real": 0, "falso_positivo": 0}
    for a in alerts:
        fname = Path(a["filename"]).name
        idx = mapping.get(fname)
        if idx is None:
            continue
        src = py.loc[idx]
        cwe_b = "CWE-{}".format(a.get("issue_cwe", {}).get("id", 0))
        vuln = bool(src["is_vulnerable"])
        match = cwe_match(cwe_b, src["cwe_id"])
        truth = "real" if vuln else "falso_positivo"
        counts[truth] += 1
        context = a.get("code", "")
        rows.append({
            "id": "{}:{}".format(fname, a.get("line_number")),
            "file": fname,
            "line": a.get("line_number"),
            "rule_id": a.get("test_id"),
            "cwe_sast": cwe_b,
            "cwe_dataset": str(src["cwe_id"]),
            "language": "python",
            "severity": a.get("issue_severity"),
            "confidence": a.get("issue_confidence"),
            "message": a.get("issue_text"),
            "function": enclosing_function(tmp / fname, int(a.get("line_number") or 1)),
            "code": str(src["code"])[:6000],
            "context": str(context),
            "truth": truth,
            "cwe_match": match,
        })

    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    print("guardado:", out, "| registros:", len(rows))
    print("conteo:", counts)
    if rows:
        by_cwe = pd.Series([r["cwe_sast"] for r in rows]).value_counts().head(10)
        print("top CWE SAST:\n", by_cwe.to_string())


if __name__ == "__main__":
    main()
