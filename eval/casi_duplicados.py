"""Mide casi-duplicados entre train/val y el holdout a nivel de función Python.

El dataset original eliminó duplicados exactos por hash normalizado, pero no midió
similitud difusa. Este script compara funciones Python de los splits finales contra
las funciones que produjeron las alertas del holdout, usando similitud de secuencias
de tokens.

Salida:
    eval/casi_duplicados.json
    docs/CASI_DUPLICADOS.md

Uso:
    python eval/casi_duplicados.py
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]


def extraer_codigo_splits(linea):
    """El código en train_80.jsonl/val_total.jsonl está dentro de <code_snippet>."""
    m = re.search(r"<code_snippet>\n(.*?)\n</code_snippet>", linea["prompt"], re.DOTALL)
    return m.group(1) if m else ""


def tokenizar(code):
    """Tokeniza Python de forma robusta sin depender de que el código sea ejecutable."""
    return re.findall(r"[A-Za-z_]\w*|[0-9]+|[^A-Za-z0-9_\s]", code)


def normalizar_espacios(code):
    return "".join(str(code).split())


def cargar_funciones(ruta, extractor):
    funciones = []
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            row = json.loads(linea)
            lang = row.get("language", row.get("meta", {}).get("language", "")).lower()
            if lang != "python":
                continue
            code = extractor(row)
            norm = normalizar_espacios(code)
            if not norm:
                continue
            funciones.append({
                "id": row.get("id", row.get("meta", {}).get("hash", "")),
                "code": code,
                "norm": norm,
                "tokens": tokenizar(norm),
            })
    return funciones


def similitud(a, b):
    if not a["tokens"] or not b["tokens"]:
        return 0.0
    return SequenceMatcher(None, a["tokens"], b["tokens"]).ratio()


def analizar(holdout, train, val, umbral=0.8):
    resultados = []
    for h in holdout:
        max_train = 0.0
        max_val = 0.0
        mejor_train = None
        mejor_val = None
        for t in train:
            s = similitud(h, t)
            if s > max_train:
                max_train = s
                mejor_train = t
        for v in val:
            s = similitud(h, v)
            if s > max_val:
                max_val = s
                mejor_val = v
        resultados.append({
            "holdout_id": h["id"],
            "max_train": round(max_train, 3),
            "max_val": round(max_val, 3),
            "max_total": round(max(max_train, max_val), 3),
            "mejor_train_id": mejor_train["id"] if mejor_train else None,
            "mejor_val_id": mejor_val["id"] if mejor_val else None,
        })
    return resultados


def histograma(valores, bins):
    hist = {f"{b[0]}-{b[1]}": 0 for b in bins}
    for v in valores:
        for lo, hi in bins:
            if lo <= v <= hi:
                hist[f"{lo}-{hi}"] += 1
                break
    return hist


def resumen(resultados, umbral):
    totales = [r["max_total"] for r in resultados]
    sobre_umbral = [r for r in resultados if r["max_total"] >= umbral]
    return {
        "holdout_funciones": len(resultados),
        "sobre_umbral": len(sobre_umbral),
        "porcentaje_sobre_umbral": round(100.0 * len(sobre_umbral) / len(resultados), 1) if resultados else 0.0,
        "maximo": round(max(totales), 3) if totales else 0.0,
        "mediana": round(median(totales), 3) if totales else 0.0,
        "histograma_max_total": histograma(totales, [(0.0, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]),
    }


def truncar(code, n=80):
    linea = code.replace("\n", " ").strip()
    return (linea[:n] + "…") if len(linea) > n else linea


def markdown(datos):
    res = datos["resumen"]
    lineas = [
        "# Casi-duplicados entre train/val y holdout",
        "",
        "Generado por `eval/casi_duplicados.py` el {}.".format(datos["fecha"]),
        "",
        "## 1. Qué se midió",
        "",
        "El dataset original eliminó duplicados exactos por hash normalizado "
        "(`dataset/scripts/build_splits.py`), pero no midió similitud difusa. "
        "Este análisis compara cada función Python del holdout contra todas las "
        "funciones Python de `train_80` y `val_total`, usando similitud de secuencias "
        "de tokens sobre el código normalizado.",
        "",
        "- Train (`dataset/splits/train_80.jsonl`): {} funciones Python.".format(datos["train"]),
        "- Validación (`dataset/splits/val_total.jsonl`): {} funciones Python.".format(datos["val"]),
        "- Holdout (`eval/holdout_set.jsonl`): {} funciones Python.".format(datos["holdout"]),
        "",
        "Umbral de alerta: **{}**.".format(datos["umbral"]),
        "",
        "## 2. Resultados",
        "",
        "| Métrica | Valor |",
        "|---|---:|",
        "| Funciones holdout analizadas | {} |".format(res["holdout_funciones"]),
        "| Funciones con vecino ≥ {} | {} |".format(datos["umbral"], res["sobre_umbral"]),
        "| Porcentaje con vecino ≥ {} | {} % |".format(datos["umbral"], res["porcentaje_sobre_umbral"]),
        "| Máxima similitud | {} |".format(res["maximo"]),
        "| Mediana de la máxima similitud | {} |".format(res["mediana"]),
        "",
        "Distribución de la máxima similitud por función holdout:",
        "",
        "| Rango | Funciones | % |",
        "|---|---:|---:|",
    ]
    total = res["holdout_funciones"]
    for rango, cant in res["histograma_max_total"].items():
        pct = round(100.0 * cant / total, 1) if total else 0.0
        lineas.append("| {} | {} | {} % |".format(rango, cant, pct))
    lineas += [
        "",
        "## 3. Interpretación",
        "",
        "- Los duplicados exactos ya fueron eliminados en `build_splits.py`; este análisis "
        "mide funciones que no son idénticas pero que podrían compartir el mismo patrón "
        "o provenir del mismo proyecto.",
        "- Un porcentaje alto de vecinos ≥ {} no demuestra fuga, pero sí debilita la "
        "validez externa: el modelo pudo haber visto variantes muy similares durante el "
        "entrenamiento.".format(datos["umbral"]),
        "- La partición es aleatoria por función y el dataset no incluye identificador de "
        "repositorio, así que no se puede descartar que funciones del mismo proyecto "
        "caigan en train y en test.",
        "",
        "## 4. Pares más similares",
        "",
        "| Holdout | Similitud | Vecino en | ID vecino | Código holdout | Código vecino |",
        "|---|---:|---|---|---|---|",
    ]
    for p in datos["top_pares"]:
        lineas.append("| {} | {} | {} | {} | {} | {} |".format(
            p["holdout_id"], p["similitud"], p["conjunto"], p["vecino_id"],
            truncar(p["holdout_code"]), truncar(p["vecino_code"])))
    lineas += [
        "",
        "## 5. Reproducción",
        "",
        "```powershell",
        "python eval/casi_duplicados.py",
        "```",
        "",
    ]
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(description="Casi-duplicados train/val vs holdout")
    parser.add_argument("--umbral", type=float, default=0.8)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--out", default=str(ROOT / "eval" / "casi_duplicados.json"))
    parser.add_argument("--md", default=str(ROOT / "docs" / "CASI_DUPLICADOS.md"))
    args = parser.parse_args()

    train = cargar_funciones(ROOT / "dataset" / "splits" / "train_80.jsonl", extraer_codigo_splits)
    val = cargar_funciones(ROOT / "dataset" / "splits" / "val_total.jsonl", extraer_codigo_splits)
    holdout = cargar_funciones(ROOT / "eval" / "holdout_set.jsonl", lambda r: r.get("code", ""))

    print("Train Python:", len(train))
    print("Val Python:", len(val))
    print("Holdout Python:", len(holdout))

    resultados = analizar(holdout, train, val, umbral=args.umbral)
    res = resumen(resultados, args.umbral)

    # Construir top pares con el código completo para el informe
    top = sorted(resultados, key=lambda x: x["max_total"], reverse=True)[:args.top]
    train_por_id = {f["id"]: f for f in train}
    val_por_id = {f["id"]: f for f in val}
    top_pares = []
    for r in top:
        if r["max_train"] >= r["max_val"] and r["mejor_train_id"]:
            vecino = train_por_id[r["mejor_train_id"]]
            top_pares.append({
                "holdout_id": r["holdout_id"], "similitud": r["max_train"],
                "conjunto": "train", "vecino_id": vecino["id"],
                "holdout_code": next(h["code"] for h in holdout if h["id"] == r["holdout_id"]),
                "vecino_code": vecino["code"],
            })
        elif r["mejor_val_id"]:
            vecino = val_por_id[r["mejor_val_id"]]
            top_pares.append({
                "holdout_id": r["holdout_id"], "similitud": r["max_val"],
                "conjunto": "val", "vecino_id": vecino["id"],
                "holdout_code": next(h["code"] for h in holdout if h["id"] == r["holdout_id"]),
                "vecino_code": vecino["code"],
            })

    datos = {
        "generado_por": "eval/casi_duplicados.py",
        "fecha": date.today().isoformat(),
        "umbral": args.umbral,
        "train": len(train),
        "val": len(val),
        "holdout": len(holdout),
        "resumen": res,
        "resultados": resultados,
        "top_pares": top_pares,
    }

    out = Path(args.out)
    out.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    md = Path(args.md)
    md.write_text(markdown(datos), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print("guardado:", out)
    print("guardado:", md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
