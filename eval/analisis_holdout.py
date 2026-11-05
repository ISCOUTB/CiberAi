#!/usr/bin/env python3
"""Analisis reproducible de la evaluacion holdout del Sprint 7.

Lee `eval/resultados_holdout_{A,C0,D}.json` y `eval/holdout_set.jsonl`, calcula
las metricas crudas y las de la politica de producto, intervalos de confianza
(Wilson y bootstrap agrupado por archivo), desacuerdos D/C0, diversidad de
explicaciones y la lista de falsos negativos.

Uso:
    python eval/analisis_holdout.py
    python eval/analisis_holdout.py --json eval/analisis_holdout.json

No vuelve a ejecutar el modelo: solo post-procesa resultados ya guardados.
"""

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "eval" / "holdout_set.jsonl"
CONFIGS = ["A", "C0", "D"]
PROTECCIONES = {
    "ninguna": frozenset(),
    "B403": frozenset({"B403"}),
    "B403+B311": frozenset({"B403", "B311"}),
}

# Equivalencias usadas por eval/run_eval.py y eval/build_eval_set.py.
EQUIV = {
    259: {259, 798, 257}, 798: {798, 259},
    327: {327, 328, 326, 310, 916}, 326: {326, 327}, 328: {328, 327},
    89: {89, 564, 943}, 78: {78, 77, 88}, 79: {79, 80, 116},
    94: {94, 95}, 20: {20}, 601: {601}, 918: {918}, 22: {22, 23},
    502: {502, 915}, 703: {703, 617},
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_results(cfg):
    path = ROOT / "eval" / "resultados_holdout_{}.json".format(cfg)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_set():
    with HOLDOUT.open(encoding="utf-8") as fh:
        return {row["id"]: row for row in (json.loads(line) for line in fh if line.strip())}


def wilson(k, n, z=1.96):
    """Intervalo de Wilson para una proporcion, en porcentaje."""
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, round(100 * (centro - half), 1)),
            min(100.0, round(100 * (centro + half), 1))]


def cwe_num(text):
    digits = "".join(ch for ch in str(text) if ch.isdigit())
    return int(digits) if digits else None


def cwe_match(pred, dataset):
    p, d = cwe_num(pred), cwe_num(dataset)
    if p is None or d is None:
        return False
    return d in EQUIV.get(p, {p})


def decisions(rows, protect=frozenset()):
    """Devuelve (fn, fp_descartados, conservadas_reales, conservadas_totales)."""
    fn = 0
    fp_desc = 0
    reales = 0
    total = len(rows)
    for row in rows:
        descarta = row["decision"] == "recomendada_descarte" and row["rule_id"] not in protect
        if row["truth"] == "real":
            reales += 1
            if descarta:
                fn += 1
        elif descarta:
            fp_desc += 1
    return fn, fp_desc, reales - fn, total - fn - fp_desc


def metricas(rows, protect=frozenset()):
    fn, fp_desc, kept_real, kept_total = decisions(rows, protect)
    reales = sum(1 for row in rows if row["truth"] == "real")
    fps = len(rows) - reales
    reales_conservadas = [
        row for row in rows
        if row["truth"] == "real"
        and not (row["decision"] == "recomendada_descarte" and row["rule_id"] not in protect)
    ]
    cwe_ok = sum(1 for row in reales_conservadas if cwe_match(row["cwe_pred"], row["cwe_dataset"]))
    return {
        "alertas": len(rows),
        "reales": reales,
        "falsos_positivos": fps,
        "recomendadas_descarte": fn + fp_desc,
        "conservadas": kept_total,
        "FN": fn,
        "FP_descartados": fp_desc,
        "FPRR": round(100 * fp_desc / fps, 1) if fps else 0.0,
        "FNR": round(100 * fn / reales, 1) if reales else 0.0,
        "FOR": round(100 * fn / (fn + fp_desc), 1) if (fn + fp_desc) else 0.0,
        "precision": round(100 * kept_real / kept_total, 1) if kept_total else 0.0,
        "exactitud_cwe": round(100 * cwe_ok / len(reales_conservadas), 1)
        if reales_conservadas else 0.0,
        "respuestas_invalidas": sum(1 for row in rows if not row["valido"]),
        "IC95_FPRR_wilson": wilson(fp_desc, fps),
        "IC95_FNR_wilson": wilson(fn, reales),
    }


def bootstrap(rows, protect=frozenset(), repeticiones=5000, seed=42):
    """Bootstrap agrupado por archivo: las alertas de un archivo no son independientes."""
    por_archivo = defaultdict(list)
    for row in rows:
        por_archivo[row["id"].split(":")[0]].append(row)
    archivos = sorted(por_archivo)
    rng = random.Random(seed)
    fnrs, fprrs = [], []
    for _ in range(repeticiones):
        muestra = []
        for archivo in rng.choices(archivos, k=len(archivos)):
            muestra.extend(por_archivo[archivo])
        m = metricas(muestra, protect)
        fnrs.append(m["FNR"])
        fprrs.append(m["FPRR"])

    def pct(valores, p):
        valores = sorted(valores)
        return round(valores[int(p * (len(valores) - 1))], 1)

    return {
        "repeticiones": repeticiones,
        "archivos": len(archivos),
        "IC95_FNR": [pct(fnrs, 0.025), pct(fnrs, 0.975)],
        "IC95_FPRR": [pct(fprrs, 0.025), pct(fprrs, 0.975)],
    }


def por_regla(rows):
    tabla = defaultdict(lambda: {"alertas": 0, "reales": 0, "FN": 0,
                                 "falsos_positivos": 0, "FP_descartados": 0})
    for row in rows:
        item = tabla[row["rule_id"]]
        item["alertas"] += 1
        if row["truth"] == "real":
            item["reales"] += 1
            item["FN"] += row["decision"] == "recomendada_descarte"
        else:
            item["falsos_positivos"] += 1
            item["FP_descartados"] += row["decision"] == "recomendada_descarte"
    return dict(sorted(tabla.items(),
                       key=lambda kv: (-(kv[1]["FN"] + kv[1]["FP_descartados"]), kv[0])))


def diversidad(rows):
    return {
        campo: {
            "unicos": len({row[campo] for row in rows}),
            "moda": Counter(row[campo] for row in rows).most_common(1)[0][1],
        }
        for campo in ("explicacion", "vector_ataque", "correccion")
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path,
                    default=ROOT / "eval" / "analisis_holdout.json",
                    help="ruta del resumen JSON (por defecto eval/analisis_holdout.json)")
    args = ap.parse_args()

    holdout = load_set()
    resultados = {cfg: load_results(cfg) for cfg in CONFIGS}
    detalles = {cfg: data["detalle"] for cfg, data in resultados.items()}

    resumen = {
        "set": {
            "archivo": "eval/holdout_set.jsonl",
            "sha256": sha256(HOLDOUT),
            "alertas": len(holdout),
            "codigos_unicos": len({row["code"] for row in holdout.values()}),
            "filas_duplicadas": len(holdout) - len({row["code"] for row in holdout.values()}),
            "archivos": len({row["file"] for row in holdout.values()}),
            "funciones": len({(row["file"], row["function"]) for row in holdout.values()}),
            "reales": sum(1 for row in holdout.values() if row["truth"] == "real"),
            "falsos_positivos": sum(1 for row in holdout.values() if row["truth"] != "real"),
        },
        "resultados_sha256": {
            cfg: sha256(ROOT / "eval" / "resultados_holdout_{}.json".format(cfg))
            for cfg in CONFIGS
        },
        "configuraciones": {cfg: metricas(detalles[cfg]) for cfg in CONFIGS},
        "politica": {
            nombre: metricas(detalles["D"], protect)
            for nombre, protect in PROTECCIONES.items()
        },
        "bootstrap": {
            "D_crudo": bootstrap(detalles["D"]),
            "D_B403": bootstrap(detalles["D"], PROTECCIONES["B403"]),
        },
        "por_regla_D": por_regla(detalles["D"]),
        "falsos_negativos_D": [
            {
                "id": row["id"],
                "rule_id": row["rule_id"],
                "cwe_sast": row["cwe_sast"],
                "cwe_dataset": row["cwe_dataset"],
                "mensaje": holdout[row["id"]]["message"],
            }
            for row in detalles["D"]
            if row["truth"] == "real" and row["decision"] == "recomendada_descarte"
        ],
        "diversidad": {cfg: diversidad(detalles[cfg]) for cfg in ("C0", "D")},
    }

    # Desacuerdos D vs C0: casos en los que una descarta y la otra conserva.
    c0 = {row["id"]: row for row in detalles["C0"]}
    d = {row["id"]: row for row in detalles["D"]}
    solo_d = [i for i in d if d[i]["decision"] == "recomendada_descarte"
              and c0[i]["decision"] != "recomendada_descarte"]
    solo_c0 = [i for i in d if d[i]["decision"] != "recomendada_descarte"
               and c0[i]["decision"] == "recomendada_descarte"]
    resumen["desacuerdos_D_vs_C0"] = {
        "solo_D": {
            "total": len(solo_d),
            "reales": sum(1 for i in solo_d if d[i]["truth"] == "real"),
            "falsos_positivos": sum(1 for i in solo_d if d[i]["truth"] != "real"),
        },
        "solo_C0": {
            "total": len(solo_c0),
            "reales": sum(1 for i in solo_c0 if d[i]["truth"] == "real"),
            "falsos_positivos": sum(1 for i in solo_c0 if d[i]["truth"] != "real"),
        },
    }

    args.json.write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")

    print("Holdout:", resumen["set"])
    for cfg in CONFIGS:
        m = resumen["configuraciones"][cfg]
        print("{:>2}: FPRR {:5.1f} % {} | FNR {:4.1f} % {} | FOR {:4.1f} % | CWE {:4.1f} %".format(
            cfg, m["FPRR"], m["IC95_FPRR_wilson"], m["FNR"],
            m["IC95_FNR_wilson"], m["FOR"], m["exactitud_cwe"]))
    for nombre, m in resumen["politica"].items():
        print("D + {:>10}: FPRR {:5.1f} % | FNR {:4.1f} % {} | FN {}".format(
            nombre, m["FPRR"], m["FNR"], m["IC95_FNR_wilson"], m["FN"]))
    print("Bootstrap D crudo:", resumen["bootstrap"]["D_crudo"]["IC95_FNR"],
          resumen["bootstrap"]["D_crudo"]["IC95_FPRR"])
    print("Bootstrap D+B403:", resumen["bootstrap"]["D_B403"]["IC95_FNR"],
          resumen["bootstrap"]["D_B403"]["IC95_FPRR"])
    print("Guardado:", args.json)


if __name__ == "__main__":
    main()
