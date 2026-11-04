"""Smoke test: 10 casos del eval_set corriendo el agente con Qwen2.5-Coder-Instruct real.

Genera las respuestas del modelo (misma plantilla del agente de triage) sobre los
10 ejemplos elegidos y calcula metricas (FPRR, FOR, Exactitud CWE, respuestas invalidas).

Uso:
    python eval/run_smoke.py --limit 10 --model Qwen/Qwen2.5-Coder-1.5B-Instruct \
        --out eval/resultados_smoke.json
"""

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_eval  # noqa: E402  (compartir parse/metrics/prompts)

sys.stdout.reconfigure(encoding="utf-8")

AGENT_SYSTEM = (
    "Eres un analista de seguridad de software. Recibes una alerta de un analizador "
    "estatico (Bandit) y el codigo afectado. Decide si la alerta corresponde a una "
    "vulnerabilidad real (VULNERABLE) o a un falso positivo (SAFE). Responde SOLO con "
    "un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, "
    "vector_ataque, correccion."
)

AGENT_TEMPLATE = """Alerta del SAST:
- Regla: {rule_id}
- CWE: {cwe_sast}
- Severidad reportada: {severity}
- Confianza: {confidence}
- Archivo: {file}
- Linea: {line}
- Funcion: {function}
- Mensaje: {message}

Codigo afectado:
<code>
{context}
</code>

Devuelve el JSON con:
- veredicto: "VULNERABLE" o "SAFE"
- cwe: identificador CWE (o "Ninguno" si es SAFE)
- severidad: "Alta", "Media", "Baja" o "Info"
- explicacion: por que la alerta es real o un falso positivo
- vector_ataque: como se explota (o "N/A" si es SAFE)
- correccion: correccion recomendada (o "N/A" si es SAFE)
"""


def build_prompt(row):
    return AGENT_TEMPLATE.format(
        rule_id=row["rule_id"],
        cwe_sast=row["cwe_sast"],
        severity=row["severity"],
        confidence=row["confidence"],
        file=row.get("file") or "",
        line=row.get("line") or 0,
        function=row.get("function") or "",
        message=row.get("message") or "",
        context=row.get("context") or row.get("code") or "",
    )


def generate(model, tokenizer, prompt, system, max_new_tokens=512):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    enc = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt"
    )
    input_ids = enc["input_ids"]
    attention_mask = enc["attention_mask"]
    out = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=max_new_tokens,
        do_sample=False,
    )
    prompt_len = input_ids.shape[1]
    raw = tokenizer.decode(out[0][prompt_len:], skip_special_tokens=True)
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
    ap.add_argument("--out", default="eval/resultados_smoke.json")
    ap.add_argument("--max-new-tokens", type=int, default=512)
    args = ap.parse_args()

    rows = [
        json.loads(l)
        for l in (Path(__file__).resolve().parents[1] / "eval" / "eval_set.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if l.strip()
    ][: args.limit]

    print("cargando modelo:", args.model)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True)
    model.eval()
    model.to(torch.device("cpu"))

    results = []
    for i, row in enumerate(rows, 1):
        prompt = build_prompt(row)
        try:
            raw = generate(model, tokenizer, prompt, AGENT_SYSTEM, args.max_new_tokens)
            parsed = run_eval.parse(raw, row)
        except Exception as exc:
            parsed = {"veredicto": "SOSPECHOSA", "cwe": "Ninguno", "valido": False, "error": str(exc)}
        results.append({
            "id": row["id"],
            "rule_id": row["rule_id"],
            "cwe_sast": row["cwe_sast"],
            "cwe_dataset": row["cwe_dataset"],
            "truth": row["truth"],
            "veredicto": parsed["veredicto"],
            "cwe_pred": parsed["cwe"],
            "valido": parsed["valido"],
        })
        print("{}/{} -> {} | pred: {} | truth: {}".format(i, len(rows), parsed, parsed.get("cwe"), row["truth"]))
        if i % 5 == 0 or i == len(rows):
            out = Path(__file__).resolve().parents[1] / "eval" / "resultados_smoke.json"
            out.write_text(json.dumps({
                "config": "SMOKE-LOCAL",
                "model": args.model,
                "metricas": run_eval.metrics(results),
                "detalle": results,
            }, ensure_ascii=False, indent=2), encoding="utf-8")

    out = Path(__file__).resolve().parents[1] / "eval" / "resultados_smoke.json"
    out.write_text(json.dumps({
        "config": "SMOKE-LOCAL",
        "model": args.model,
        "metricas": run_eval.metrics(results),
        "detalle": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("metricas:", json.dumps(run_eval.metrics(results), ensure_ascii=False, indent=2))
    print("guardado:", out)


if __name__ == "__main__":
    main()
