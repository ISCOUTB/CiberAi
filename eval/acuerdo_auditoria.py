"""Calcula el acuerdo entre la adjudicacion original y la revision ciega.

Uso:
    python eval/acuerdo_auditoria.py
Lee:
    eval/auditoria_fn.json
    eval/rubrica/auditoria_fn_ciega.csv  (con la columna 'veredicto' completa)
Escribe:
    eval/acuerdo_auditoria.json
Falla si la hoja ciega tiene casos sin calificar o valores no admitidos.
"""

import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
VALIDOS = {"real", "falso_positivo"}


def kappa(pares):
    """Kappa de Cohen para dos jueces binarios."""
    n = len(pares)
    if not n:
        return 0.0
    acuerdos = sum(1 for a, b in pares if a == b)
    po = acuerdos / n
    # Distribucion marginal de cada juez.
    p_a_real = sum(1 for a, _ in pares if a == "real") / n
    p_b_real = sum(1 for _, b in pares if b == "real") / n
    pe = p_a_real * p_b_real + (1 - p_a_real) * (1 - p_b_real)
    return 1.0 if pe == 1.0 else (po - pe) / (1 - pe)


def main():
    original = json.loads(
        (ROOT / "eval" / "auditoria_fn.json").read_text(encoding="utf-8")
    )
    original = {(c["split"], c["id"]): c["veredicto"] for c in original["casos"]}

    ruta = ROOT / "eval" / "rubrica" / "auditoria_fn_ciega.csv"
    with open(ruta, encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))

    faltan = [f["id"] for f in filas if f["veredicto"].strip() not in VALIDOS]
    if faltan:
        raise SystemExit("casos sin calificar o con valor invalido: {}".format(faltan))

    pares, discrepancias = [], []
    for fila in filas:
        clave = (fila["split"], fila["id"])
        if clave not in original:
            raise SystemExit("la hoja ciega contiene un caso no auditado: {}".format(clave))
        a, b = original[clave], fila["veredicto"].strip()
        pares.append((a, b))
        if a != b:
            discrepancias.append(
                {
                    "split": fila["split"],
                    "id": fila["id"],
                    "regla": fila["regla"],
                    "original": a,
                    "revisor": b,
                    "motivo_revisor": fila["motivo"].strip(),
                }
            )

    acuerdos = sum(1 for a, b in pares if a == b)
    salida = {
        "generado_por": "eval/acuerdo_auditoria.py",
        "casos": len(pares),
        "acuerdos": acuerdos,
        "acuerdo_observado": round(100.0 * acuerdos / len(pares), 1),
        "kappa": round(kappa(pares), 3),
        "discrepancias": discrepancias,
    }
    destino = ROOT / "eval" / "acuerdo_auditoria.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")

    print("Casos: {} | acuerdos: {} ({:.1f} %)".format(
        len(pares), acuerdos, salida["acuerdo_observado"]
    ))
    print("Kappa de Cohen: {:.3f}".format(salida["kappa"]))
    for d in discrepancias:
        print("  discrepancia: {} {} ({} -> {})".format(
            d["split"], d["id"], d["original"], d["revisor"]
        ))
    print("Guardado: eval/acuerdo_auditoria.json")


if __name__ == "__main__":
    main()
