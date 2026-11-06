"""Compara el modelo base (C0) contra el modelo afinado (D), emparejado por alerta.

C0 y D comparten prompt, conjunto, temperatura y limite de generacion; la unica
diferencia es la etiqueta del modelo servido por Ollama. Por eso el par C0/D es
la comparacion que aisla el efecto del ajuste fino.

Lee:
    eval/resultados_C0.json          (desarrollo)
    eval/resultados_D.json           (desarrollo)
    eval/resultados_holdout_C0.json  (holdout)
    eval/resultados_holdout_D.json   (holdout)

Escribe:
    eval/analisis_c0_vs_d.json

Uso:
    python eval/analisis_c0_vs_d.py
"""

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

CONJUNTOS = {
    "desarrollo": ("resultados_C0.json", "resultados_D.json"),
    "holdout": ("resultados_holdout_C0.json", "resultados_holdout_D.json"),
}


def cargar(nombre):
    with (ROOT / "eval" / nombre).open(encoding="utf-8") as fh:
        return json.load(fh)


def archivo(fila):
    return fila["id"].split(":")[0]


def confusion(filas):
    """Matriz de confusion del modo asesor sobre la decision de descarte."""
    tp = fp = tn = fn = 0
    for f in filas:
        descarta = f["decision"] == "recomendada_descarte"
        real = f["truth"] == "real"
        if descarta and real:
            fn += 1
        elif descarta and not real:
            tp += 1
        elif not descarta and real:
            tn += 1
        else:
            fp += 1
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn}


def tasa(num, den):
    return round(100.0 * num / den, 1) if den else 0.0


def mcnemar_exacto(b, c):
    """p bilateral exacto de McNemar para discordancias b y c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cola = sum(math.comb(n, i) for i in range(k + 1)) / (2.0 ** n)
    return round(min(1.0, 2.0 * cola), 4)


def emparejar(c0, d):
    por_id_c0 = {f["id"]: f for f in c0["detalle"]}
    por_id_d = {f["id"]: f for f in d["detalle"]}
    ids = [f["id"] for f in d["detalle"]]
    faltan = [i for i in ids if i not in por_id_c0]
    if faltan:
        raise SystemExit("C0 no tiene {} alertas de D: {}".format(len(faltan), faltan[:3]))
    return [(por_id_c0[i], por_id_d[i]) for i in ids]


def diversidad(filas, campo):
    valores = [f.get(campo) for f in filas]
    valores = [v for v in valores if v]
    if not valores:
        return {"unicos": 0, "moda": 0, "total": 0}
    cuenta = Counter(valores)
    return {"unicos": len(cuenta), "moda": cuenta.most_common(1)[0][1], "total": len(valores)}


def resumir_conjunto(nombre, c0, d):
    pares = emparejar(c0, d)
    res = {"archivos_resultado": list(CONJUNTOS[nombre]), "alertas": len(pares)}

    for etiqueta, filas in (("C0", [p[0] for p in pares]), ("D", [p[1] for p in pares])):
        cm = confusion(filas)
        reales = sum(1 for f in filas if f["truth"] == "real")
        falsos = len(filas) - reales
        res[etiqueta] = {
            "modelo": (c0 if etiqueta == "C0" else d)["model"],
            "confusion": cm,
            "reales": reales,
            "falsos_positivos": falsos,
            "FPRR": tasa(cm["TP"], falsos),
            "FNR": tasa(cm["FN"], reales),
            "exactitud_decision": tasa(cm["TP"] + cm["TN"], len(filas)),
            "exactitud_cwe": (c0 if etiqueta == "C0" else d)["metricas"]["exactitud_cwe"],
            "respuestas_invalidas": (c0 if etiqueta == "C0" else d)["metricas"]["respuestas_invalidas"],
        }

    solo_d, solo_c0, ambas_descartan, ambos_conservan = [], [], [], []
    for f0, fd in pares:
        d0 = f0["decision"] == "recomendada_descarte"
        dd = fd["decision"] == "recomendada_descarte"
        if dd and not d0:
            solo_d.append(fd)
        elif d0 and not dd:
            solo_c0.append(fd)
        elif d0 and dd:
            ambas_descartan.append(fd)
        else:
            ambos_conservan.append(fd)

    def cuenta(filas):
        reales = sum(1 for f in filas if f["truth"] == "real")
        return {"total": len(filas), "reales": reales, "falsos_positivos": len(filas) - reales}

    res["acuerdo"] = {
        "ambos_conservan": cuenta(ambos_conservan),
        "ambos_descartan": cuenta(ambas_descartan),
        "solo_D_descarta": cuenta(solo_d),
        "solo_C0_descarta": cuenta(solo_c0),
    }
    res["mcnemar"] = {
        "b_solo_D": len(solo_d),
        "c_solo_C0": len(solo_c0),
        "p_exacto_bilateral": mcnemar_exacto(len(solo_d), len(solo_c0)),
    }

    # Intercambio marginal: descartes extra de D y errores extra que introduce.
    extra_tp = sum(1 for f in solo_d if f["truth"] != "real")
    extra_fn = sum(1 for f in solo_d if f["truth"] == "real")
    recuperados = sum(1 for f in solo_c0 if f["truth"] != "real")
    recuperados_reales = sum(1 for f in solo_c0 if f["truth"] == "real")
    res["intercambio"] = {
        "descartes_extra_D": len(solo_d),
        "falsos_positivos_extra": extra_tp,
        "reales_perdidas_extra": extra_fn,
        "descartes_extra_C0": len(solo_c0),
        "falsos_positivos_que_C0_descarta_y_D_no": recuperados,
        "reales_que_C0_descarta_y_D_no": recuperados_reales,
        "descartes_netos_D": len(solo_d) - len(solo_c0),
        "falsos_positivos_netos": extra_tp - recuperados,
        "reales_perdidas_netas": extra_fn - recuperados_reales,
        "ratio_fp_por_real_bruto": round(extra_tp / extra_fn, 2) if extra_fn else None,
        "ratio_fp_por_real_neto": (
            round((extra_tp - recuperados) / (extra_fn - recuperados_reales), 2)
            if (extra_fn - recuperados_reales) else None
        ),
    }

    # Desacuerdo por regla, para ver si el efecto del ajuste se concentra.
    por_regla = defaultdict(lambda: {"total": 0, "solo_D": 0, "solo_C0": 0,
                                     "solo_D_reales": 0, "solo_C0_reales": 0})
    for f0, fd in pares:
        r = por_regla[fd["rule_id"]]
        r["total"] += 1
        d0 = f0["decision"] == "recomendada_descarte"
        dd = fd["decision"] == "recomendada_descarte"
        if dd != d0:
            clave = "solo_D" if dd else "solo_C0"
            r[clave] += 1
            if fd["truth"] == "real":
                r[clave + "_reales"] += 1
    res["por_regla"] = {
        k: v for k, v in sorted(por_regla.items(), key=lambda kv: -(kv[1]["solo_D"] + kv[1]["solo_C0"]))
    }

    # Diversidad de explicaciones y coherencia del CWE.
    res["diversidad"] = {
        "C0": {c: diversidad([p[0] for p in pares], c)
               for c in ("explicacion", "vector_ataque", "correccion")},
        "D": {c: diversidad([p[1] for p in pares], c)
              for c in ("explicacion", "vector_ataque", "correccion")},
    }
    copia_cwe = {
        etiqueta: sum(1 for f in filas if f.get("cwe_pred") == f.get("cwe_sast"))
        for etiqueta, filas in (("C0", [p[0] for p in pares]), ("D", [p[1] for p in pares]))
    }
    res["cwe_copiado_del_sast"] = copia_cwe

    # Diferencia de FPRR/FNR con bootstrap agrupado por archivo (pares completos).
    res["diferencias"] = bootstrap_diferencias(pares)
    return res


def bootstrap_diferencias(pares, iteraciones=2000, semilla=20261103):
    """IC95 de FPRR(D)-FPRR(C0) y FNR(D)-FNR(C0) remuestreando archivos."""
    import random

    azar = random.Random(semilla)
    por_archivo = defaultdict(list)
    for f0, fd in pares:
        por_archivo[archivo(fd)].append((f0, fd))
    nombres = sorted(por_archivo)
    difs = {"FPRR": [], "FNR": []}
    for _ in range(iteraciones):
        muestra = []
        for _ in nombres:
            muestra.extend(por_archivo[azar.choice(nombres)])
        for metrica, condicion in (("FPRR", "fp"), ("FNR", "fn")):
            valores = {}
            for etiqueta, idx in (("C0", 0), ("D", 1)):
                filas = [p[idx] for p in muestra]
                if condicion == "fp":
                    den = sum(1 for f in filas if f["truth"] != "real")
                    num = sum(1 for f in filas
                              if f["truth"] != "real" and f["decision"] == "recomendada_descarte")
                else:
                    den = sum(1 for f in filas if f["truth"] == "real")
                    num = sum(1 for f in filas
                              if f["truth"] == "real" and f["decision"] == "recomendada_descarte")
                valores[etiqueta] = 100.0 * num / den if den else 0.0
            difs[metrica].append(valores["D"] - valores["C0"])
    res = {}
    for metrica, lista in difs.items():
        lista.sort()
        res[metrica] = {
            "puntual_D_menos_C0": round(
                tasa_pares(pares, metrica, 1) - tasa_pares(pares, metrica, 0), 1),
            "media_bootstrap": round(sum(lista) / len(lista), 1),
            "IC95": [round(lista[int(0.025 * len(lista))], 1),
                     round(lista[int(0.975 * len(lista)) - 1], 1)],
            "archivos": len(nombres),
        }
    return res


def tasa_pares(pares, metrica, idx):
    filas = [p[idx] for p in pares]
    if metrica == "FPRR":
        den = sum(1 for f in filas if f["truth"] != "real")
        num = sum(1 for f in filas
                  if f["truth"] != "real" and f["decision"] == "recomendada_descarte")
    else:
        den = sum(1 for f in filas if f["truth"] == "real")
        num = sum(1 for f in filas
                  if f["truth"] == "real" and f["decision"] == "recomendada_descarte")
    return 100.0 * num / den if den else 0.0


def main():
    resumen = {"generado_por": "eval/analisis_c0_vs_d.py", "conjuntos": {}}
    for nombre, (rc0, rd) in CONJUNTOS.items():
        c0 = cargar(rc0)
        d = cargar(rd)
        resumen["conjuntos"][nombre] = resumir_conjunto(nombre, c0, d)

    salida = ROOT / "eval" / "analisis_c0_vs_d.json"
    salida.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    for nombre, r in resumen["conjuntos"].items():
        print("\n== {} ==".format(nombre.upper()))
        for cfg in ("C0", "D"):
            m = r[cfg]
            print(" {} {:<24} FPRR {:>5.1f} %  FNR {:>4.1f} %  exactitud {:>5.1f} %".format(
                cfg, m["modelo"], m["FPRR"], m["FNR"], m["exactitud_decision"]))
        a = r["acuerdo"]
        print(" ambos conservan {} | ambos descartan {} | solo D {} | solo C0 {}".format(
            a["ambos_conservan"]["total"], a["ambos_descartan"]["total"],
            a["solo_D_descarta"]["total"], a["solo_C0_descarta"]["total"]))
        print(" solo D descarta: {} reales, {} FP | McNemar p={}".format(
            a["solo_D_descarta"]["reales"], a["solo_D_descarta"]["falsos_positivos"],
            r["mcnemar"]["p_exacto_bilateral"]))
        for m, v in r["diferencias"].items():
            print(" delta {} D-C0 = {:+.1f} pts  IC95 {} (bootstrap {} archivos, media {:+.1f})".format(
                m, v["puntual_D_menos_C0"], v["IC95"], v["archivos"], v["media_bootstrap"]))
    print("\nguardado:", salida)


if __name__ == "__main__":
    main()
