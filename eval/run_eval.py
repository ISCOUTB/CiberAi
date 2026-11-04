import argparse
import json
import re
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
EVAL_SET = ROOT / "eval" / "eval_set.jsonl"

SYSTEM = (
    "Eres un analista de seguridad de software. Analizas un fragmento de codigo y decides "
    "si contiene una vulnerabilidad real (VULNERABLE) o si es seguro (SAFE). Responde SOLO "
    "con un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, vector_ataque, correccion."
)

FEW_SHOT = """Ejemplo 1:
Codigo: query = "SELECT * FROM users WHERE id = " + user_id
Respuesta: {"veredicto":"VULNERABLE","cwe":"CWE-89","severidad":"Alta","explicacion":"La consulta concatena entrada del usuario, permitiendo inyeccion SQL.","vector_ataque":"El atacante altera la consulta SQL.","correccion":"Usar consultas parametrizadas."}

Ejemplo 2:
Codigo: def test_suma(): assert suma(2, 2) == 4
Respuesta: {"veredicto":"SAFE","cwe":"Ninguno","severidad":"Info","explicacion":"El assert se usa como verificacion en pruebas y no procesa entrada externa.","vector_ataque":"N/A","correccion":"N/A"}

Ejemplo 3:
Codigo: subprocess.call("ls", shell=True)
Respuesta: {"veredicto":"SAFE","cwe":"Ninguno","severidad":"Info","explicacion":"El comando es constante y no incluye entrada del usuario; no hay inyeccion.","vector_ataque":"N/A","correccion":"N/A"}
"""

CWE_EQUIV = {
    259: {259, 798, 257}, 798: {798, 259}, 327: {327, 328, 326, 310}, 326: {326, 327},
    89: {89, 564, 943}, 78: {78, 77, 88}, 79: {79, 80, 116}, 94: {94, 95},
    502: {502, 915}, 703: {703, 617}, 20: {20}, 601: {601}, 918: {918}, 22: {22, 23},
}


def cwe_num(text):
    m = re.search(r"(\d+)", str(text))
    return int(m.group(1)) if m else None


def cwe_match(pred, truth):
    p, t = cwe_num(pred), cwe_num(truth)
    return p is not None and t is not None and t in CWE_EQUIV.get(p, {p})


# Plantilla de la alerta. Se formatea solo sobre si misma: FEW_SHOT contiene
# llaves de JSON y no debe pasar por str.format (si se concatenara antes, las
# llaves se interpretarian como campos y el prompt fallaria con KeyError).
TEMPLATE_ALERTA = (
    "Alerta del SAST (triage):\n- Regla: {rule_id}\n- CWE reportado: {cwe_sast}\n"
    "- Severidad: {severity}\n- Confianza: {confidence}\n- Funcion: {function}\n"
    "- Mensaje: {message}\n\nCodigo fuente:\n<code>\n{code}\n</code>\n\nDevuelve el JSON."
)


def prompt_b(row):
    return "Codigo fuente:\n<code>\n{}\n</code>\n\nDevuelve el JSON.".format(row["code"])


def prompt_c(row):
    return FEW_SHOT + "\n" + TEMPLATE_ALERTA.format(**row)


def prompt_d(row):
    # Mismo formato con el que se entreno el adaptador: alerta del SAST y codigo,
    # sin ejemplos few-shot. La diferencia con C es solo el modelo.
    return TEMPLATE_ALERTA.format(**row)


def call(prompt, model, url, timeout=180):
    # num_predict acota la generacion igual que el cliente del producto. Sin el
    # limite, una alerta patologica puede agotar el timeout de 180 s y dejar el
    # runner de Ollama generando despues de que el cliente abandona.
    payload = {"model": model, "prompt": prompt, "system": SYSTEM, "stream": False,
               "format": "json", "options": {"temperature": 0, "num_predict": 512}}
    r = requests.post(url.rstrip("/") + "/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "")


def parse(raw, row, never_discard=None):
    if never_discard is None:
        never_discard = set()
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip()
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        text = text[s:e + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"veredicto": "SOSPECHOSA", "cwe": "Ninguno", "valido": False}
    verdict = str(data.get("veredicto", "")).upper()
    if verdict not in {"VULNERABLE", "SAFE"}:
        return {"veredicto": "SOSPECHOSA", "cwe": "Ninguno", "valido": False}

    if verdict == "SAFE" and row.get("rule_id") in never_discard:
        verdict = "SOSPECHOSA"

    return {
        "veredicto": verdict,
        "cwe": str(data.get("cwe", "Ninguno")),
        "valido": True,
        "severidad": str(data.get("severidad", "Media")),
        "explicacion": str(data.get("explicacion", "")).strip(),
        "vector_ataque": str(data.get("vector_ataque", "N/A")).strip(),
        "correccion": str(data.get("correccion", "N/A")).strip(),
    }


def metrics(results):
    reals = [r for r in results if r["truth"] == "real"]
    fps = [r for r in results if r["truth"] == "falso_positivo"]
    discarded = [r for r in results if r["veredicto"] == "SAFE"]
    kept = [r for r in results if r["veredicto"] != "SAFE"]
    for r in results:
        r["decision"] = "recomendada_descarte" if r["veredicto"] == "SAFE" else "conservada"
    fp_disc = sum(1 for r in fps if r["decision"] == "recomendada_descarte")
    real_disc = sum(1 for r in reals if r["decision"] == "recomendada_descarte")
    real_kept = [r for r in reals if r["decision"] == "conservada"]
    cwe_ok = sum(1 for r in real_kept if cwe_match(r["cwe_pred"], r["cwe_dataset"]))
    invalid = sum(1 for r in results if not r["valido"])
    # FNR: denominador = alertas reales. FOR: denominador = predicciones negativas
    # (FN + VN). Son metricas distintas y se reportan por separado.
    fnr = 100.0 * real_disc / len(reals) if reals else 0.0
    for_rate = 100.0 * real_disc / (real_disc + fp_disc) if (real_disc + fp_disc) else 0.0
    fprr = 100.0 * fp_disc / len(fps) if fps else 0.0
    precision = 100.0 * len(real_kept) / len(kept) if kept else 0.0
    return {
        "alertas": len(results),
        "reales": len(reals),
        "falsos_positivos": len(fps),
        "conservadas": len(kept),
        "recomendadas_descarte": len(discarded),
        "FPRR": round(fprr, 1),
        "FNR": round(fnr, 1),
        "FOR": round(for_rate, 1),
        "precision": round(precision, 1),
        "exactitud_cwe": round(100.0 * cwe_ok / len(real_kept), 1) if real_kept else 0.0,
        "respuestas_invalidas": invalid,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", choices=["A", "B", "C", "C0", "D"], required=True)
    ap.add_argument("--model", default="qwen2.5-coder:1.5b")
    ap.add_argument("--url", default="http://localhost:11434")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--never-discard", nargs="*", default=[],
                    help="Reglas del SAST que nunca deben ser recomendadas para descarte")
    ap.add_argument("--eval-set", type=Path, default=None,
                    help="Ruta al archivo jsonl de evaluacion (por defecto eval/eval_set.jsonl)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Ruta al archivo JSON de resultados de salida")
    args = ap.parse_args()

    eval_set_path = args.eval_set if args.eval_set is not None else EVAL_SET
    rows = [json.loads(l) for l in eval_set_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        rows = rows[:args.limit]

    if args.out:
        out_path = args.out
    elif eval_set_path.name == "holdout_set.jsonl":
        out_path = ROOT / "eval" / "resultados_holdout_{}.json".format(args.config)
    else:
        out_path = ROOT / "eval" / "resultados_{}.json".format(args.config)

    print("Evaluando configuracion {} sobre {} alertas con {} (dataset: {})".format(
        args.config, len(rows), args.model, eval_set_path.name
    ))

    if args.config == "A":
        results = [{"id": r["id"], "rule_id": r["rule_id"], "cwe_sast": r["cwe_sast"],
                    "cwe_dataset": r["cwe_dataset"], "truth": r["truth"],
                    "veredicto": "VULNERABLE", "cwe_pred": r["cwe_sast"], "valido": True,
                    "explicacion": "Alerta SAST asumida como positiva",
                    "vector_ataque": "N/A", "correccion": "N/A"}
                   for r in rows]
        m = metrics(results)
        out_path.write_text(json.dumps({"config": "A", "model": "Bandit 1.8.6 (sin agente)",
                                        "metricas": m, "detalle": results}, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(json.dumps(m, ensure_ascii=False, indent=2))
        print("guardado:", out_path)
        return

    results = []
    for i, row in enumerate(rows, 1):
        if args.config == "B":
            p = prompt_b(row)
        elif args.config in ("D", "C0"):
            # C0: modelo base con el mismo prompt que D (sin few-shot). Aisla
            # el efecto del ajuste fino del efecto de los ejemplos del prompt.
            p = prompt_d(row)
        else:
            p = prompt_c(row)
        try:
            raw = call(p, args.model, args.url)
            parsed = parse(raw, row, never_discard=set(args.never_discard))
        except Exception as exc:
            parsed = {"veredicto": "SOSPECHOSA", "cwe": "Ninguno", "valido": False, "error": str(exc),
                      "explicacion": "", "vector_ataque": "N/A", "correccion": "N/A"}
        results.append({
            "id": row["id"], "rule_id": row["rule_id"], "cwe_sast": row["cwe_sast"],
            "cwe_dataset": row["cwe_dataset"], "truth": row["truth"],
            "veredicto": parsed["veredicto"], "cwe_pred": parsed["cwe"], "valido": parsed["valido"],
            "explicacion": parsed.get("explicacion", ""),
            "vector_ataque": parsed.get("vector_ataque", "N/A"),
            "correccion": parsed.get("correccion", "N/A"),
        })
        if i % 10 == 0 or i == len(rows):
            out_path.write_text(json.dumps({"config": args.config, "model": args.model,
                                            "metricas": metrics(results), "detalle": results},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
            print("  {}/{}".format(i, len(rows)))

    m = metrics(results)
    out_path.write_text(json.dumps({"config": args.config, "model": args.model,
                                    "metricas": m, "detalle": results}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=2))
    print("guardado:", out_path)


if __name__ == "__main__":
    main()
