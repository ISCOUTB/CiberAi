"""Evalua la deteccion directa del modelo, sin alertas de herramientas SAST.

Cada fila de ``eval/audit_eval_set.jsonl`` contiene solo codigo y la verdad del
dataset. El modelo debe devolver VULNERABLE/SAFE por si mismo. Las metricas son
las de un detector binario:

- TP/FN sobre las vulnerables (recall y FNR);
- FP/TN sobre las seguras (FPR);
- precision, F1 y exactitud del CWE entre los verdaderos positivos.

Una respuesta invalida cuenta como negativa (el producto no crea hallazgo) y se
reporta aparte en ``respuestas_invalidas``.

Uso:
    python eval/run_audit_eval.py --model qwen2.5-coder-triage
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agente" / "src"))

from agente_seguridad.llm.code_audit import SYSTEM, build_prompt, parse_audit_response
from agente_seguridad.llm.ollama_client import OllamaClient, OllamaError

EVAL_SET = ROOT / "eval" / "audit_eval_set.jsonl"

EQUIV = {
    259: {259, 798, 257}, 798: {798, 259},
    327: {327, 328, 326, 310, 916}, 326: {326, 327}, 328: {328, 327},
    89: {89, 564, 943}, 78: {78, 77, 88}, 79: {79, 80, 116},
    94: {94, 95}, 20: {20}, 601: {601}, 918: {918}, 22: {22, 23},
    502: {502, 915}, 703: {703, 617},
}


def cwe_num(text):
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None


def cwe_match(pred, truth):
    p, t = cwe_num(pred), cwe_num(truth)
    return p is not None and t is not None and t in EQUIV.get(p, {p})


def metrics(results):
    vuln = [r for r in results if r["truth"] == "vulnerable"]
    safe = [r for r in results if r["truth"] == "safe"]
    tp = [r for r in vuln if r["veredicto"] == "VULNERABLE"]
    fn = [r for r in vuln if r["veredicto"] != "VULNERABLE"]
    fp = [r for r in safe if r["veredicto"] == "VULNERABLE"]
    tn = [r for r in safe if r["veredicto"] != "VULNERABLE"]
    precision = 100.0 * len(tp) / (len(tp) + len(fp)) if (tp or fp) else 0.0
    recall = 100.0 * len(tp) / len(vuln) if vuln else 0.0
    fpr = 100.0 * len(fp) / len(safe) if safe else 0.0
    fnr = 100.0 * len(fn) / len(vuln) if vuln else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    cwe_ok = sum(1 for r in tp if cwe_match(r["cwe_pred"], r["cwe_dataset"]))
    return {
        "total": len(results),
        "vulnerables": len(vuln),
        "seguras": len(safe),
        "TP": len(tp),
        "FN": len(fn),
        "FP": len(fp),
        "TN": len(tn),
        "precision": round(precision, 1),
        "recall": round(recall, 1),
        "F1": round(f1, 1),
        "FPR": round(fpr, 1),
        "FNR": round(fnr, 1),
        "exactitud_cwe": round(100.0 * cwe_ok / len(tp), 1) if tp else 0.0,
        "respuestas_invalidas": sum(1 for r in results if not r["valido"]),
    }


def model_slug(model):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5-coder:1.5b")
    ap.add_argument("--url", default="http://localhost:11434")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--eval-set", type=Path, default=EVAL_SET)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    rows = [json.loads(line) for line in
            args.eval_set.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    if args.out:
        out_path = args.out
    else:
        out_path = ROOT / "eval" / "resultados_audit_{}.json".format(model_slug(args.model))

    client = OllamaClient(base_url=args.url, model=args.model, timeout=args.timeout)
    if not client.is_available():
        raise SystemExit("Ollama no responde en {}. Levanta el servidor primero.".format(args.url))

    print("Evaluando auditoria LLM sobre {} fragmentos con {} (dataset: {})".format(
        len(rows), args.model, args.eval_set.name))

    results = []
    for index, row in enumerate(rows, 1):
        try:
            raw = client.generate(build_prompt(row["code"], row["language"]), system=SYSTEM)
            parsed = parse_audit_response(raw)
        except OllamaError as exc:
            parsed = None
            error = str(exc)
        else:
            error = ""
        if parsed is None:
            verdict, predicted_cwe, valid = "INVALIDO", "Ninguno", False
            explanation = error or "respuesta no valida"
        else:
            verdict = parsed["veredicto"]
            predicted_cwe = parsed["cwe"]
            valid = True
            explanation = parsed["explicacion"]
        results.append({
            "id": row["id"],
            "truth": row["truth"],
            "cwe_dataset": row["cwe_dataset"],
            "veredicto": verdict,
            "cwe_pred": predicted_cwe,
            "valido": valid,
            "explicacion": explanation,
        })
        if index % 10 == 0 or index == len(rows):
            out_path.write_text(json.dumps({
                "model": args.model,
                "eval_set": args.eval_set.name,
                "metricas": metrics(results),
                "detalle": results,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            print("  {}/{}".format(index, len(rows)))

    m = metrics(results)
    out_path.write_text(json.dumps({
        "model": args.model,
        "eval_set": args.eval_set.name,
        "metricas": m,
        "detalle": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=2))
    print("guardado:", out_path)


if __name__ == "__main__":
    main()
