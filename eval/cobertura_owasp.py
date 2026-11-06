"""Mide la cobertura OWASP Top 10 2021 de las alertas evaluadas.

No estima: cuenta. Lee los conjuntos realmente evaluados
(`eval/eval_set.jsonl` y `eval/holdout_set.jsonl`), toma el CWE que Bandit
reporta para cada regla (`cwe_sast`) y lo ubica en la lista oficial de CWE de
cada categoria del OWASP Top 10 2021.

Dos decisiones importantes:

1. Se usa el CWE del SAST, no la columna `owasp` del dataset. Esa columna
   asigna categoria al CWE etiquetado en el corpus, no al que Bandit reporta, y
   ademas tiene discrepancias con las listas oficiales. El script las cuenta por
   separado para que queden documentadas.

2. Un CWE que no aparece en ninguna lista oficial se reporta como `sin_categoria`
   en lugar de forzarlo a la categoria mas parecida. El Top 10 2021 no cubre las
   clases de memoria ni de gestion de recursos, y decir lo contrario seria una
   afirmacion falsa sobre la norma.

Escribe `eval/cobertura_owasp.json` y tablas en Markdown por consola.

Uso:
    python eval/cobertura_owasp.py
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
CONJUNTOS = {"desarrollo": "eval_set.jsonl", "holdout": "holdout_set.jsonl"}

CATEGORIAS = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Vulnerable and Outdated Components",
    "A07": "Identification and Authentication Failures",
    "A08": "Software and Data Integrity Failures",
    "A09": "Security Logging and Monitoring Failures",
    "A10": "Server Side Request Forgery (SSRF)",
}

# Subconjunto documentado de las listas oficiales del Top 10 2021: incluye los
# CWE que aparecen en el dataset del proyecto y los que pueden emitir las reglas
# de Bandit evaluadas. No pretende ser la lista completa de cada categoria; un
# CWE ausente de este mapa se contrasta contra las listas oficiales antes de
# clasificarlo. A04 se verifico contra la pagina oficial el 4 de noviembre de
# 2026; el resto de las listas se tomo de la misma fuente.
CWE_A_OWASP = {
    # A01 Broken Access Control
    "CWE-22": "A01", "CWE-200": "A01", "CWE-264": "A01", "CWE-276": "A01",
    "CWE-284": "A01", "CWE-352": "A01", "CWE-601": "A01",
    # A02 Cryptographic Failures
    "CWE-310": "A02", "CWE-327": "A02", "CWE-330": "A02",
    # A03 Injection
    "CWE-20": "A03", "CWE-78": "A03", "CWE-79": "A03", "CWE-89": "A03",
    "CWE-94": "A03",
    # A04 Insecure Design
    "CWE-269": "A04", "CWE-311": "A04", "CWE-434": "A04", "CWE-602": "A04",
    # A05 Security Misconfiguration: ninguna regla evaluada cae aqui.
    # A06 Vulnerable and Outdated Components: requiere escaneo de dependencias.
    # A07 Identification and Authentication Failures
    "CWE-259": "A07", "CWE-287": "A07", "CWE-306": "A07", "CWE-798": "A07",
    # A08 Software and Data Integrity Failures
    "CWE-502": "A08",
    # A09 Security Logging and Monitoring Failures
    "CWE-117": "A09", "CWE-223": "A09", "CWE-532": "A09", "CWE-778": "A09",
    # A10 Server Side Request Forgery
    "CWE-918": "A10",
}

# Mapeo publicado en dataset/README.md para sus 30 etiquetas. Se conserva tal
# cual para poder contrastarlo con CWE_A_OWASP.
ETIQUETAS_DATASET = {
    "CWE-20": "A03", "CWE-22": "A01", "CWE-78": "A03", "CWE-79": "A03",
    "CWE-89": "A03", "CWE-94": "A03", "CWE-119": "A03", "CWE-125": "A03",
    "CWE-190": "A03", "CWE-200": "A01", "CWE-264": "A01", "CWE-269": "A01",
    "CWE-276": "A01", "CWE-284": "A01", "CWE-287": "A07", "CWE-310": "A02",
    "CWE-327": "A02", "CWE-330": "A02", "CWE-352": "A01", "CWE-362": "A04",
    "CWE-399": "A04", "CWE-401": "A03", "CWE-416": "A03", "CWE-434": "A04",
    "CWE-476": "A03", "CWE-502": "A08", "CWE-601": "A01", "CWE-787": "A03",
    "CWE-798": "A07", "CWE-918": "A10",
}


def cwe(valor):
    """Normaliza 'CWE-78' o '78' a 'CWE-78'; devuelve None si no aplica."""
    if not valor:
        return None
    m = re.search(r"(\d+)", str(valor))
    return "CWE-{}".format(m.group(1)) if m else None


def cargar(nombre):
    ruta = ROOT / "eval" / nombre
    with ruta.open(encoding="utf-8") as fh:
        return [json.loads(linea) for linea in fh if linea.strip()]


def cobertura(rows):
    por_categoria = Counter()
    por_regla = defaultdict(Counter)
    sin_categoria = Counter()
    for r in rows:
        regla = r["rule_id"]
        c = cwe(r.get("cwe_sast"))
        cat = CWE_A_OWASP.get(c)
        if cat:
            por_categoria[cat] += 1
            por_regla[regla][cat] += 1
        else:
            por_categoria["sin_categoria"] += 1
            sin_categoria[c or "sin CWE"] += 1
            por_regla[regla]["sin_categoria"] += 1
    return por_categoria, por_regla, sin_categoria


def main():
    resumen = {"categorias": CATEGORIAS, "conjuntos": {}}

    for nombre, archivo in CONJUNTOS.items():
        rows = cargar(archivo)
        por_categoria, por_regla, sin_categoria = cobertura(rows)
        resumen["conjuntos"][nombre] = {
            "alertas": len(rows),
            "por_categoria": dict(por_categoria),
            "por_regla": {k: dict(v) for k, v in sorted(por_regla.items())},
            "sin_categoria": dict(sin_categoria),
        }

    # Contraste entre el mapeo del dataset y las listas oficiales.
    discrepancias = []
    for etiqueta, declarada in ETIQUETAS_DATASET.items():
        oficial = CWE_A_OWASP.get(etiqueta)
        if oficial != declarada:
            discrepancias.append({
                "cwe": etiqueta,
                "dataset": declarada,
                "oficial": oficial or "sin_categoria",
            })
    resumen["mapeo_dataset"] = {
        "etiquetas": len(ETIQUETAS_DATASET),
        "coinciden": len(ETIQUETAS_DATASET) - len(discrepancias),
        "discrepancias": discrepancias,
        "forzadas_a_A03": sum(1 for d in discrepancias if d["dataset"] == "A03"),
    }

    # Categorias alcanzables por Bandit en este proyecto, con evidencia medida.
    medidas = set()
    for datos in resumen["conjuntos"].values():
        medidas.update(k for k in datos["por_categoria"] if k != "sin_categoria")
    resumen["alcanzables_por_bandit"] = {
        "medidas_en_la_evaluacion": sorted(medidas),
        "no_medidas": [c for c in CATEGORIAS if c not in medidas],
    }

    salida = ROOT / "eval" / "cobertura_owasp.json"
    salida.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

    print("## Cobertura por categoria\n")
    print("| Categoria | Nombre | Desarrollo | Holdout |")
    print("|---|---|---:|---:|")
    for cat, titulo in CATEGORIAS.items():
        d = resumen["conjuntos"]["desarrollo"]["por_categoria"].get(cat, 0)
        h = resumen["conjuntos"]["holdout"]["por_categoria"].get(cat, 0)
        print("| {} | {} | {} | {} |".format(cat, titulo, d, h))
    print("| sin_categoria | Fuera del Top 10 2021 | {} | {} |".format(
        resumen["conjuntos"]["desarrollo"]["por_categoria"].get("sin_categoria", 0),
        resumen["conjuntos"]["holdout"]["por_categoria"].get("sin_categoria", 0)))

    print("\n## Reglas y categoria\n")
    print("| Regla | Desarrollo | Holdout |")
    print("|---|---|---|")
    reglas = sorted(set(resumen["conjuntos"]["desarrollo"]["por_regla"])
                    | set(resumen["conjuntos"]["holdout"]["por_regla"]))
    for regla in reglas:
        d = resumen["conjuntos"]["desarrollo"]["por_regla"].get(regla, {})
        h = resumen["conjuntos"]["holdout"]["por_regla"].get(regla, {})
        fmt = lambda x: ", ".join("{}:{}".format(k, v) for k, v in sorted(x.items())) or "0"
        print("| {} | {} | {} |".format(regla, fmt(d), fmt(h)))

    print("\n## Discrepancias del mapeo del dataset\n")
    print("{} de {} etiquetas no coinciden con la lista oficial; {} estan forzadas a A03.".format(
        resumen["mapeo_dataset"]["discrepancias"].__len__(),
        resumen["mapeo_dataset"]["etiquetas"],
        resumen["mapeo_dataset"]["forzadas_a_A03"]))
    for d in discrepancias:
        print(" - {}: dataset {} -> oficial {}".format(d["cwe"], d["dataset"], d["oficial"]))

    print("\n## Categorias sin alertas medidas\n")
    print(", ".join(resumen["alcanzables_por_bandit"]["no_medidas"]))
    print("\nguardado:", salida)


if __name__ == "__main__":
    main()
