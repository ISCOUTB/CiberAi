"""Mide latencia por alerta sin escribir resultados de evaluacion.

No modifica eval/resultados_*.json: solo llama al modelo y descarta la salida.
Uso:
    python eval/bench_latency.py --config D --model qwen2.5-coder-triage --limit 10
    python eval/bench_latency.py --config C --model qwen2.5-coder:1.5b --limit 10
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_eval as r  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", choices=["C", "D"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--url", default="http://localhost:11434")
    args = ap.parse_args()

    rows = [json.loads(l) for l in (ROOT / "eval" / "eval_set.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = rows[: args.limit]
    prompt = r.prompt_d if args.config == "D" else r.prompt_c

    times, valid = [], 0
    start_all = time.perf_counter()
    for i, row in enumerate(rows, 1):
        t0 = time.perf_counter()
        raw = r.call(prompt(row), args.model, args.url)
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
        valid += r.parse(raw, row)["valido"]
        print("  {}/{} {:.1f} s".format(i, len(rows), elapsed))
    total = time.perf_counter() - start_all

    print(json.dumps({
        "config": args.config,
        "model": args.model,
        "alertas": len(rows),
        "validas": valid,
        "total_s": round(total, 1),
        "media_s": round(statistics.mean(times), 1),
        "mediana_s": round(statistics.median(times), 1),
        "min_s": round(min(times), 1),
        "max_s": round(max(times), 1),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
