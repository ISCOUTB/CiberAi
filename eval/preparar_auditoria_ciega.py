"""Genera la hoja ciega para la segunda revision de la auditoria de falsos negativos.

La hoja no incluye el veredicto del modelo ni la etiqueta del conjunto, para que
el segundo revisor clasifique cada alerta de forma independiente. El orden se
mezcla con una semilla fija para que no queden agrupados por conjunto ni por
modelo.

Uso:
    python eval/preparar_auditoria_ciega.py
Escribe:
    eval/rubrica/auditoria_fn_ciega.csv
"""

import csv
import json
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

CONJUNTOS = {
    "desarrollo": "eval/eval_set.jsonl",
    "holdout": "eval/holdout_set.jsonl",
}

# Lineas de codigo que aportan la evidencia relevante para cada regla.
PATRONES = {
    "B403": ("pickle",),
    "B404": ("subprocess", "shell=True"),
    "B311": ("random",),
}


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def evidencia(row, regla):
    """Devuelve las lineas del fragmento que el revisor necesita para decidir."""
    claves = PATRONES.get(regla, ())
    lineas = row["code"].splitlines()
    seleccion = []
    for numero, linea in enumerate(lineas, 1):
        if any(clave in linea for clave in claves):
            seleccion.append("{:>4}: {}".format(numero, linea.rstrip()))
    if not seleccion:
        # Sin coincidencia, se muestran las primeras lineas del fragmento.
        seleccion = [
            "{:>4}: {}".format(numero, linea.rstrip())
            for numero, linea in enumerate(lineas[:12], 1)
        ]
    return "\n".join(seleccion)


def main():
    auditoria = json.loads(
        (ROOT / "eval" / "auditoria_fn.json").read_text(encoding="utf-8")
    )
    sets = {nombre: load_jsonl(ROOT / ruta) for nombre, ruta in CONJUNTOS.items()}
    por_id = {
        (nombre, row["id"]): row for nombre, rows in sets.items() for row in rows
    }

    filas = []
    for caso in auditoria["casos"]:
        row = por_id[(caso["split"], caso["id"])]
        filas.append(
            {
                "split": caso["split"],
                "id": caso["id"],
                "regla": caso["regla"],
                "linea": row["line"],
                "cwe_sast": row["cwe_sast"],
                "evidencia": evidencia(row, caso["regla"]),
                "veredicto": "",
                "motivo": "",
            }
        )

    random.Random(20261107).shuffle(filas)

    destino = ROOT / "eval" / "rubrica" / "auditoria_fn_ciega.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "split",
                "id",
                "regla",
                "linea",
                "cwe_sast",
                "evidencia",
                "veredicto",
                "motivo",
            ],
        )
        writer.writeheader()
        writer.writerows(filas)

    print("Casos: {}".format(len(filas)))
    print("Hoja ciega: eval/rubrica/auditoria_fn_ciega.csv")
    print("Valores admitidos en 'veredicto': real | falso_positivo")


if __name__ == "__main__":
    main()
