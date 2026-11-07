"""Audita los falsos negativos de C0 y D y recalcula FNR/FPRR a nivel de alerta.

La etiqueta del conjunto es a nivel de fragmento: un fragmento marcado como
vulnerable convierte en "real" cualquier alerta de Bandit sobre el, aunque la
linea senalada sea otra. Este script cruza esas alertas con la adjudicacion
manual de eval/auditoria_fn.json y produce una lectura de sensibilidad.

Uso:
    python eval/auditar_fn.py
"""

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

CONJUNTOS = {
    "desarrollo": {
        "set": "eval/eval_set.jsonl",
        "resultados": {"C0": "eval/resultados_C0.json", "D": "eval/resultados_D.json"},
    },
    "holdout": {
        "set": "eval/holdout_set.jsonl",
        "resultados": {
            "C0": "eval/resultados_holdout_C0.json",
            "D": "eval/resultados_holdout_D.json",
        },
    },
}

POLITICA_B403 = {"B403"}


def load_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def comprobar_evidencia(caso, row):
    """Comprueba que el veredicto manual concuerda con una senal objetiva."""
    code = row["code"]
    if caso["regla"] == "B403":
        tiene_sink = bool(re.search(r"pickle\.loads?\s*\(", code))
        return tiene_sink == (caso["veredicto"] == "real")
    if caso["regla"] == "B404":
        tiene_sink = "shell=True" in code and "subprocess" in code
        return tiene_sink == (caso["veredicto"] == "real")
    if caso["regla"] == "B311":
        contexto_seguridad = bool(
            re.search(r"token|secret|key|passw|nonce|session|csrf|salt", code, re.I)
        )
        return contexto_seguridad == (caso["veredicto"] == "real")
    return True


def evaluar(detalle, total_reales, total_fp):
    descartes = [r for r in detalle if r["decision"] == "recomendada_descarte"]
    fn = [r for r in detalle if r["truth"] == "real" and r["decision"] == "recomendada_descarte"]
    return {
        "descartes": len(descartes),
        "fn_brutos": fn,
        "_reales": total_reales,
        "_fp": total_fp,
    }


def metricas(descartes, fn_reales, total_reales, total_fp):
    return {
        "FNR": round(100.0 * fn_reales / total_reales, 1) if total_reales else 0.0,
        "FPRR": round(100.0 * (descartes - fn_reales) / total_fp, 1) if total_fp else 0.0,
        "precision_descarte": round(100.0 * (descartes - fn_reales) / descartes, 1)
        if descartes
        else 0.0,
    }


def main():
    auditoria = load_json(ROOT / "eval" / "auditoria_fn.json")
    casos = {(c["split"], c["id"]): c for c in auditoria["casos"]}

    salida = {
        "generado_por": "eval/auditar_fn.py",
        "fuente_adjudicacion": "eval/auditoria_fn.json",
        "criterio": auditoria["criterio"],
        "conjuntos": {},
    }

    for nombre, cfg in CONJUNTOS.items():
        rows = {r["id"]: r for r in load_jsonl(ROOT / cfg["set"])}
        total_reales = sum(1 for r in rows.values() if r["truth"] == "real")
        total_fp = sum(1 for r in rows.values() if r["truth"] == "falso_positivo")
        bloque = {"alertas": len(rows), "reales": total_reales, "falsos_positivos": total_fp}

        for modelo, ruta in cfg["resultados"].items():
            detalle = load_json(ROOT / ruta)["detalle"]
            assert len(detalle) == len(rows), "el detalle no cubre todas las alertas"
            base = evaluar(detalle, total_reales, total_fp)
            fn = base["fn_brutos"]

            faltan = [r["id"] for r in fn if (nombre, r["id"]) not in casos]
            if faltan:
                raise SystemExit("faltan casos en auditoria_fn.json: {}".format(faltan))

            for r in fn:
                caso = casos[(nombre, r["id"])]
                if not comprobar_evidencia(caso, rows[r["id"]]):
                    raise SystemExit(
                        "la evidencia de {} contradice el veredicto {}".format(
                            r["id"], caso["veredicto"]
                        )
                    )
                if caso["regla"] != r["rule_id"]:
                    raise SystemExit("regla inconsistente en {}".format(r["id"]))

            fn_reales = sum(
                1 for r in fn if casos[(nombre, r["id"])]["veredicto"] == "real"
            )
            fn_ruido = len(fn) - fn_reales
            antes = metricas(base["descartes"], fn_reales, total_reales, total_fp)
            bruto = {
                "FNR": round(100.0 * len(fn) / total_reales, 1),
                "FPRR": round(100.0 * (base["descartes"] - len(fn)) / total_fp, 1),
                "precision_descarte": round(
                    100.0 * (base["descartes"] - len(fn)) / base["descartes"], 1
                ) if base["descartes"] else 0.0,
            }

            # Politica: las reglas protegidas nunca recomiendan descarte.
            detalle_pol = [
                dict(r, decision="conservada")
                if r["decision"] == "recomendada_descarte" and r["rule_id"] in POLITICA_B403
                else r
                for r in detalle
            ]
            pol = evaluar(detalle_pol, total_reales, total_fp)
            fn_pol = [
                r for r in detalle_pol
                if r["truth"] == "real" and r["decision"] == "recomendada_descarte"
            ]
            fn_pol_reales = sum(
                1 for r in fn_pol if casos[(nombre, r["id"])]["veredicto"] == "real"
            )
            con_politica = metricas(
                pol["descartes"], fn_pol_reales, total_reales, total_fp
            )

            bloque[modelo] = {
                "fn_brutos": len(fn),
                "fn_reales": fn_reales,
                "fn_ruido": fn_ruido,
                "fn_ids": [r["id"] for r in fn],
                "fn_ruido_ids": [
                    r["id"]
                    for r in fn
                    if casos[(nombre, r["id"])]["veredicto"] != "real"
                ],
                "bruto": bruto,
                "ajustado": antes,
                "con_politica_b403": con_politica,
            }

        salida["conjuntos"][nombre] = bloque

    destino = ROOT / "eval" / "analisis_fn.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")

    print("Auditoria de falsos negativos")
    print("=" * 78)
    for nombre, bloque in salida["conjuntos"].items():
        print("\n{}: {} alertas ({} reales, {} FP)".format(
            nombre.capitalize(), bloque["alertas"], bloque["reales"], bloque["falsos_positivos"]
        ))
        print("  {:<4} {:>7} {:>7} {:>7} {:>9} {:>9} {:>11}".format(
            "mod", "FN", "reales", "ruido", "FNR bruto", "FNR aj.", "FPRR aj."
        ))
        for modelo in ("C0", "D"):
            m = bloque[modelo]
            print("  {:<4} {:>7} {:>7} {:>7} {:>8.1f}% {:>8.1f}% {:>10.1f}%".format(
                modelo, m["fn_brutos"], m["fn_reales"], m["fn_ruido"],
                m["bruto"]["FNR"], m["ajustado"]["FNR"], m["ajustado"]["FPRR"],
            ))
            print("       ruido: {}".format(", ".join(m["fn_ruido_ids"]) or "-"))
            print("       con politica B403: FNR {:.1f}% | FPRR {:.1f}% | precision {:.1f}%".format(
                m["con_politica_b403"]["FNR"], m["con_politica_b403"]["FPRR"],
                m["con_politica_b403"]["precision_descarte"],
            ))
    print("\nGuardado: eval/analisis_fn.json")


if __name__ == "__main__":
    main()
