import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
rows = [json.loads(l) for l in (ROOT / "eval" / "eval_set.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
reals = [r for r in rows if r["truth"] == "real"]
fps = [r for r in rows if r["truth"] == "falso_positivo"]
cwe_ok = sum(1 for r in reals if r["cwe_match"])
out = {
    "config": "A",
    "model": "Bandit 1.8.6 (sin agente)",
    "metricas": {
        "alertas": len(rows),
        "reales": len(reals),
        "falsos_positivos": len(fps),
        "conservadas": len(rows),
        "recomendadas_descarte": 0,
        "FPRR": 0.0,
        "FNR": 0.0,
        "FOR": 0.0,
        "precision": round(100.0 * len(reals) / len(rows), 1) if rows else 0.0,
        "exactitud_cwe": round(100.0 * cwe_ok / len(reals), 1) if reals else 0.0,
        "respuestas_invalidas": 0,
    },
}
(ROOT / "eval" / "resultados_A.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
