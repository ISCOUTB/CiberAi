import argparse
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

SYSTEM = (
    "Eres un analista de seguridad de software. Analizas un fragmento de codigo y decides "
    "si contiene una vulnerabilidad real (VULNERABLE) o si es seguro (SAFE). Responde SOLO "
    "con un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, vector_ataque, correccion."
)

RULE_BY_CWE = {
    "CWE-89": "B608", "CWE-78": "B602", "CWE-502": "B301", "CWE-327": "B303",
    "CWE-328": "B303", "CWE-259": "B105", "CWE-798": "B105", "CWE-22": "B108",
    "CWE-94": "B102", "CWE-79": "B308", "CWE-20": "B500", "CWE-601": "B310",
    "CWE-918": "B310", "CWE-703": "B101", "CWE-377": "B306", "CWE-330": "B311",
}
FP_POOL = ["CWE-89", "CWE-78", "CWE-502", "CWE-327", "CWE-259", "CWE-22", "CWE-94", "CWE-79"]


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def alert_block(cwe, severity, rule):
    return (
        "\n\nAlerta del SAST (triage):\n"
        "- Regla: {}\n- CWE reportado: {}\n- Severidad: {}\n"
        "- Confianza: MEDIUM\n- Mensaje: Patron asociado a {} detectado.\n"
    ).format(rule, cwe, severity, cwe)


def to_example(row, alert, rng):
    meta = row["meta"]
    target = json.loads(row["target"])
    user = row["prompt"]
    if alert:
        if meta["is_vulnerable"]:
            cwe = meta["cwe"] if meta["cwe"] != "Ninguno" else rng.choice(FP_POOL)
            severity = target.get("severidad", "Media")
        else:
            cwe = rng.choice(FP_POOL)
            severity = rng.choice(["Baja", "Media", "Alta"])
        rule = RULE_BY_CWE.get(cwe, "B000")
        user += alert_block(cwe, severity, rule)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": row["target"]},
        ],
        "meta": {"language": meta["language"], "vulnerable": meta["is_vulnerable"], "alert": alert},
    }


def sample(rows, limit, rng):
    vuln = [r for r in rows if r["meta"]["is_vulnerable"]]
    safe = [r for r in rows if not r["meta"]["is_vulnerable"]]
    n = min(limit // 2, len(vuln), len(safe))
    chosen = rng.sample(vuln, n) + rng.sample(safe, n)
    rng.shuffle(chosen)
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=str(ROOT / "dataset" / "splits" / "train_80.jsonl"))
    ap.add_argument("--val", default=str(ROOT / "dataset" / "splits" / "val_total.jsonl"))
    ap.add_argument("--outdir", default=str(ROOT / "training" / "data"))
    ap.add_argument("--limit", type=int, default=12000)
    ap.add_argument("--val-limit", type=int, default=1000)
    ap.add_argument("--alert-frac", type=float, default=0.5)
    ap.add_argument("--max-chars", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    def load(path):
        rows = [r for r in read_jsonl(path) if len(r["prompt"]) <= args.max_chars]
        return rows

    train_rows = load(args.train)
    val_rows = load(args.val)
    print("disponibles: train {} | val {}".format(len(train_rows), len(val_rows)))

    train_sel = sample(train_rows, args.limit, rng)
    val_sel = sample(val_rows, args.val_limit, rng)
    print("seleccionados: train {} | val {}".format(len(train_sel), len(val_sel)))

    for name, rows in [("train_sft.jsonl", train_sel), ("val_sft.jsonl", val_sel)]:
        path = outdir / name
        total_chars = 0
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                with_alert = rng.random() < args.alert_frac
                ex = to_example(row, with_alert, rng)
                text = "".join(m["content"] for m in ex["messages"])
                total_chars += len(text)
                fh.write(json.dumps(ex, ensure_ascii=False) + "\n")
        print("{}: {} ejemplos | ~{} tokens promedio (est. chars/4)".format(
            name, len(rows), int(total_chars / max(len(rows), 1) / 4)))


if __name__ == "__main__":
    main()
