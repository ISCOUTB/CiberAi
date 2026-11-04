#!/usr/bin/env python3
"""Herramienta de auditoría cualitativa de explicaciones y cálculo de acuerdo inter-evaluador (Kappa de Cohen).

Sprint 7 - Agente de Seguridad.
Permite:
  1. Extraer una muestra aleatoria reproducible de alertas analizadas y generar
     las plantillas de calificación para 2 revisores independientes.
  2. Calcular el índice Kappa de Cohen (unweighted y lineal/cuadrático) para los
     4 criterios de la rúbrica (CWE, Vector, Corrección, Claridad).

Uso:
  python eval/rubrica_explicaciones.py generar-muestra --fuente eval/resultados_holdout_D.json --n 25 --seed 42
  python eval/rubrica_explicaciones.py calcular-acuerdo --r1 eval/rubrica/evaluador_1.csv --r2 eval/rubrica/evaluador_2.csv
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

try:
    from sklearn.metrics import cohen_kappa_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

CRITERIOS = [
    ("cwe_score", "CWE correcto", "0: Incorrecto/ausente | 1: Familia equivalente | 2: CWE exacto"),
    ("vector_score", "Vector de ataque", "0: Ausente/genérico | 1: Plausible sin detalle | 2: Concreto y consistente"),
    ("correccion_score", "Corrección", "0: Ausente/insegura | 1: Genérica | 2: Aplicable y preserva comportamiento"),
    ("claridad_score", "Claridad", "0: Incomprensible | 1: Comprensible con esfuerzo | 2: Directa y sin ambigüedad"),
]

INSTRUCCIONES_MD = """# Rúbrica de Auditoría de Explicaciones (Sprint 7)

Esta auditoría evalúa cualitativamente la calidad técnica de las explicaciones generadas
por el modelo de triage (`qwen2.5-coder-triage`).

## Procedimiento
1. Dos evaluadores califican de forma independiente y a ciegas la muestra en sus respectivos archivos CSV.
2. Cada fila corresponde a una alerta analizada con su fragmento de código y la respuesta del modelo.
3. Asigne a cada criterio un puntaje entero entre **0** y **2** según la siguiente escala:

| Criterio | 0 (Deficiente) | 1 (Aceptable / Parcial) | 2 (Excelente / Preciso) |
|---|---|---|---|
| **CWE correcto** | Incorrecto o ausente | Familia equivalente o relacionada | CWE exacto y pertinente |
| **Vector de ataque** | Ausente, ficticio o genérico | Plausible conceptualmente pero sin detalle del código | Concreto, identifica variables y flujo consistente |
| **Corrección** | Ausente, sintácticamente errónea o insegura | Recomendación genérica (ej. "validar entrada") | Código aplicable, idiomático y preserva el comportamiento |
| **Claridad** | Incomprensible, redundante o contradictoria | Comprensible con esfuerzo o ambigua | Directa, técnica, concisa y sin ambigüedad |

## Cálculo de Acuerdo
Al completar ambas hojas, ejecute:
```powershell
python eval/rubrica_explicaciones.py calcular-acuerdo --r1 eval/rubrica/evaluador_1.csv --r2 eval/rubrica/evaluador_2.csv
```
"""


def cohen_kappa_pure_python(y1, y2, weights=None):
    """Calcula Kappa de Cohen sin dependencias externas."""
    if len(y1) != len(y2) or len(y1) == 0:
        return 0.0
    categories = sorted(list(set(y1) | set(y2)))
    cat_to_idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    if k <= 1:
        return 1.0

    # Matriz de confusión
    matrix = [[0] * k for _ in range(k)]
    for a, b in zip(y1, y2):
        matrix[cat_to_idx[a]][cat_to_idx[b]] += 1
    n = float(len(y1))

    # Pesos
    if weights == "quadratic":
        w = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    elif weights == "linear":
        w = [[abs(i - j) / float(k - 1) for j in range(k)] for i in range(k)]
    else:
        w = [[0 if i == j else 1 for j in range(k)] for i in range(k)]

    # Marginales
    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[i][j] for i in range(k)) for j in range(k)]

    # Acuerdo observado y esperado
    po = sum(w[i][j] * matrix[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w[i][j] * row_sums[i] * col_sums[j] for i in range(k) for j in range(k)) / (n * n)

    if pe == 0:
        return 1.0
    return 1.0 - (po / pe)


def compute_kappa(y1, y2, weights=None):
    if SKLEARN_AVAILABLE:
        try:
            return cohen_kappa_score(y1, y2, weights=weights)
        except Exception:
            pass
    return cohen_kappa_pure_python(y1, y2, weights=weights)


def interpretar_kappa(k):
    if k < 0.0:
        return "Sin acuerdo (< 0.00)"
    elif k <= 0.20:
        return "Acuerdo leve (0.01 - 0.20)"
    elif k <= 0.40:
        return "Acuerdo regular (0.21 - 0.40)"
    elif k <= 0.60:
        return "Acuerdo moderado (0.41 - 0.60)"
    elif k <= 0.80:
        return "Acuerdo sustancial (0.61 - 0.80)"
    else:
        return "Acuerdo casi perfecto (0.81 - 1.00)"


def cmd_generar(args):
    fuente_path = Path(args.fuente)
    if not fuente_path.exists():
        raise SystemExit(f"No existe el archivo de resultados: {fuente_path}")

    dataset_path = Path(args.dataset) if args.dataset else (
        ROOT / "eval" / "holdout_set.jsonl" if "holdout" in fuente_path.name else ROOT / "eval" / "eval_set.jsonl"
    )
    code_map = {}
    if dataset_path.exists():
        for line in dataset_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                code_map[item["id"]] = item.get("code", "")

    data = json.loads(fuente_path.read_text(encoding="utf-8"))
    detalles = data.get("detalle", [])
    if not detalles:
        raise SystemExit(f"El archivo {fuente_path} no contiene campo 'detalle'.")

    # Muestreo estratificado por veredicto y regla
    rnd = random.Random(args.seed)
    n_sample = min(args.n, len(detalles))
    muestra = rnd.sample(detalles, n_sample)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Escribir guía de instrucciones
    (out_dir / "instrucciones_rubrica.md").write_text(INSTRUCCIONES_MD, encoding="utf-8")

    columns = [
        "id", "rule_id", "cwe_sast", "cwe_pred", "veredicto_modelo",
        "explicacion", "vector_ataque", "correccion", "codigo_fuente",
        "cwe_score", "vector_score", "correccion_score", "claridad_score", "observaciones"
    ]

    for evaluador_id in [1, 2]:
        csv_file = out_dir / f"evaluador_{evaluador_id}.csv"
        with csv_file.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns)
            writer.writeheader()
            for r in muestra:
                code_snippet = code_map.get(r["id"], "")
                writer.writerow({
                    "id": r["id"],
                    "rule_id": r["rule_id"],
                    "cwe_sast": r["cwe_sast"],
                    "cwe_pred": r.get("cwe_pred", ""),
                    "veredicto_modelo": r.get("veredicto", ""),
                    "explicacion": r.get("explicacion", ""),
                    "vector_ataque": r.get("vector_ataque", "N/A"),
                    "correccion": r.get("correccion", "N/A"),
                    "codigo_fuente": code_snippet[:1500].replace("\r", ""),
                    "cwe_score": "",
                    "vector_score": "",
                    "correccion_score": "",
                    "claridad_score": "",
                    "observaciones": "",
                })
        print(f"Generada plantilla: {csv_file}")

    print(f"Muestra de {n_sample} alertas generada en: {out_dir}")
    print(f"Instrucciones en: {out_dir / 'instrucciones_rubrica.md'}")


def cmd_calcular(args):
    r1_path = Path(args.r1)
    r2_path = Path(args.r2)
    if not r1_path.exists() or not r2_path.exists():
        raise SystemExit("Debe proporcionar las rutas a ambas hojas de evaluación diligenciadas.")

    def load_scores(path):
        scores = {}
        with path.open("r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                aid = row["id"]
                scores[aid] = {
                    "cwe_score": int(row["cwe_score"]) if str(row.get("cwe_score", "")).strip().isdigit() else None,
                    "vector_score": int(row["vector_score"]) if str(row.get("vector_score", "")).strip().isdigit() else None,
                    "correccion_score": int(row["correccion_score"]) if str(row.get("correccion_score", "")).strip().isdigit() else None,
                    "claridad_score": int(row["claridad_score"]) if str(row.get("claridad_score", "")).strip().isdigit() else None,
                }
        return scores

    s1 = load_scores(r1_path)
    s2 = load_scores(r2_path)

    comunes = sorted(list(set(s1.keys()) & set(s2.keys())))
    if not comunes:
        raise SystemExit("No hay identificadores comunes entre ambas hojas de evaluación.")

    print(f"Analizando {len(comunes)} alertas calificadas por ambos revisores...\n")

    resumen = []
    detalles_criterio = {}

    for campo, nombre, desc in CRITERIOS:
        v1 = []
        v2 = []
        for cid in comunes:
            p1 = s1[cid][campo]
            p2 = s2[cid][campo]
            if p1 is not None and p2 is not None:
                v1.append(p1)
                v2.append(p2)

        if not v1:
            print(f"Aviso: Criterio '{nombre}' no tiene calificaciones válidas aún.")
            continue

        kappa_unweighted = compute_kappa(v1, v2, weights=None)
        kappa_weighted = compute_kappa(v1, v2, weights="quadratic")
        acuerdo_exacto = sum(1 for a, b in zip(v1, v2) if a == b) / len(v1) * 100.0
        media_r1 = sum(v1) / len(v1)
        media_r2 = sum(v2) / len(v2)
        media_global = (media_r1 + media_r2) / 2.0

        detalles_criterio[campo] = {
            "nombre": nombre,
            "muestra": len(v1),
            "media_evaluador_1": round(media_r1, 2),
            "media_evaluador_2": round(media_r2, 2),
            "media_global": round(media_global, 2),
            "acuerdo_exacto_pct": round(acuerdo_exacto, 1),
            "kappa_unweighted": round(kappa_unweighted, 3),
            "kappa_cuadratico": round(kappa_weighted, 3),
            "interpretacion": interpretar_kappa(kappa_weighted),
        }

        resumen.append([
            nombre,
            f"{media_global:.2f} / 2.0",
            f"{acuerdo_exacto:.1f} %",
            f"{kappa_unweighted:.3f}",
            f"{kappa_weighted:.3f}",
            interpretar_kappa(kappa_weighted),
        ])

    print("-" * 95)
    print(f"{'Criterio':<22} | {'Media':<12} | {'Acuerdo':<9} | {'Kappa':<8} | {'Kappa Ponderado':<16} | {'Interpretación'}")
    print("-" * 95)
    for r in resumen:
        print(f"{r[0]:<22} | {r[1]:<12} | {r[2]:<9} | {r[3]:<8} | {r[4]:<16} | {r[5]}")
    print("-" * 95)

    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(detalles_criterio, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nResultados guardados en: {out_p}")


def main():
    parser = argparse.ArgumentParser(description="Auditoría de explicaciones y cálculo de Kappa de Cohen")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generar-muestra", help="Extrae muestra y genera plantillas CSV para revisores")
    gen.add_argument("--fuente", default="eval/resultados_holdout_D.json", help="Ruta al JSON de resultados D")
    gen.add_argument("--dataset", default=None, help="Ruta al JSONL de alertas para extraer código fuente")
    gen.add_argument("--n", type=int, default=25, help="Tamaño de la muestra")
    gen.add_argument("--seed", type=int, default=42, help="Semilla aleatoria")
    gen.add_argument("--out-dir", default="eval/rubrica", help="Directorio de salida para las plantillas")

    calc = sub.add_parser("calcular-acuerdo", help="Calcula el acuerdo inter-evaluador a partir de los CSV diligenciados")
    calc.add_argument("--r1", default="eval/rubrica/evaluador_1.csv", help="CSV completado por Evaluador 1")
    calc.add_argument("--r2", default="eval/rubrica/evaluador_2.csv", help="CSV completado por Evaluador 2")
    calc.add_argument("--out", default="eval/rubrica/resultados_acuerdo.json", help="Ruta del JSON con métricas de acuerdo")

    args = parser.parse_args()
    if args.command == "generar-muestra":
        cmd_generar(args)
    elif args.command == "calcular-acuerdo":
        cmd_calcular(args)


if __name__ == "__main__":
    main()
