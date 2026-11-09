"""Auditoría manual de las alertas de D sobre repositorios reales.

Carga eval/corrida_repos_reales.json, extrae las 38 alertas, carga el contexto
real del archivo fuente y genera:

    eval/auditoria_repos.jsonl   # plantilla para etiquetar
    docs/AUDITORIA_REPOS.md      # informe de auditoría (después de etiquetar)

Uso:
    python eval/auditoria_repos.py --preparar     # genera la plantilla
    # edita eval/auditoria_repos.jsonl a mano con etiqueta y justificación
    python eval/auditoria_repos.py --calcular     # genera el informe
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
REPOS = ROOT / "eval" / "repos_reales"
CORRIDA = ROOT / "eval" / "corrida_repos_reales.json"
AUDITORIA = ROOT / "eval" / "auditoria_repos.jsonl"
MD = ROOT / "docs" / "AUDITORIA_REPOS.md"


def cargar_lineas(ruta, linea, radio=8):
    """Devuelve radio líneas antes y después de la línea (1-based)."""
    if not ruta.exists():
        return "[archivo no encontrado]"
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    idx = linea - 1
    inicio = max(0, idx - radio)
    fin = min(len(lineas), idx + radio + 1)
    return "\n".join(
        "{:4} {}".format(i + 1, (">>" if i == idx else "  ") + lineas[i])
        for i in range(inicio, fin)
    )


def preparar():
    corrida = json.loads(CORRIDA.read_text(encoding="utf-8"))
    plantilla = []
    orden = 0
    for h in corrida["hallazgos"]:
        orden += 1
        repo = h["repo"]
        info = corrida["repos"][repo]
        archivo = h["archivo"]
        linea = h["linea"]
        ruta = REPOS / repo / info["subdir"] / archivo
        contexto = cargar_lineas(ruta, linea, radio=8)
        plantilla.append({
            "orden": orden,
            "id": "{}:{}".format(archivo, linea),
            "repo": repo,
            "tag": info["tag"],
            "archivo": archivo,
            "linea": linea,
            "regla": h["regla"],
            "cwe": h["cwe"],
            "owasp": h["owasp"],
            "severidad": h["severidad"],
            "mensaje": h["mensaje"] if "mensaje" in h else "",
            "d_veredicto": h["d"]["veredicto"],
            "contexto": contexto,
            "etiqueta": "",          # 'real' o 'falso_positivo'
            "justificacion": "",
            "auditor": "",
        })
    AUDITORIA.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in plantilla) + "\n",
        encoding="utf-8",
    )
    print("Plantilla guardada:", AUDITORIA)
    print("Alertas:", len(plantilla))
    return 0


def calcular():
    if not AUDITORIA.exists():
        print("Falta", AUDITORIA, "; ejecuta primero --preparar")
        return 1
    filas = []
    with AUDITORIA.open(encoding="utf-8") as fh:
        for linea in fh:
            if linea.strip():
                filas.append(json.loads(linea))
    pendientes = [f for f in filas if f["etiqueta"] not in ("real", "falso_positivo")]
    if pendientes:
        print("Aún faltan etiquetas:", len(pendientes))
        for f in pendientes[:5]:
            print(" -", f["id"])
        return 1

    # Métricas: positivo = alerta real
    tp = sum(1 for f in filas if f["etiqueta"] == "falso_positivo" and f["d_veredicto"] == "SAFE")
    fp = sum(1 for f in filas if f["etiqueta"] == "real" and f["d_veredicto"] == "SAFE")
    tn = sum(1 for f in filas if f["etiqueta"] == "real" and f["d_veredicto"] != "SAFE")
    fn = sum(1 for f in filas if f["etiqueta"] == "falso_positivo" and f["d_veredicto"] != "SAFE")

    safe_total = sum(1 for f in filas if f["d_veredicto"] == "SAFE")
    real_total = sum(1 for f in filas if f["etiqueta"] == "real")
    fp_total = sum(1 for f in filas if f["etiqueta"] == "falso_positivo")

    metricas = {
        "alertas_auditadas": len(filas),
        "safe_auditados": safe_total,
        "reales": real_total,
        "falsos_positivos": fp_total,
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "FPRR": round(100.0 * tp / fp_total, 1) if fp_total else 0.0,
        "FNR": round(100.0 * fn / real_total, 1) if real_total else 0.0,
        "precision_descartes": round(100.0 * tp / (tp + fp), 1) if (tp + fp) else 0.0,
        "exactitud": round(100.0 * (tp + tn) / len(filas), 1) if filas else 0.0,
    }

    datos = {
        "generado_por": "eval/auditoria_repos.py",
        "metricas": metricas,
        "alertas": filas,
    }
    (ROOT / "eval" / "auditoria_repos_metricas.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    MD.write_text(markdown(datos), encoding="utf-8")
    print(json.dumps(metricas, ensure_ascii=False, indent=2))
    print("Informe:", MD)
    return 0


def truncar(texto, n=90):
    t = texto.replace("\n", " ").strip()
    return (t[:n] + "…") if len(t) > n else t


def markdown(datos):
    m = datos["metricas"]
    lineas = [
        "# Auditoría manual de alertas en repositorios reales",
        "",
        "Auditoría de las alertas que D recomendó descartar (`SAFE`) y de las que conservó",
        "(`VULNERABLE`) sobre `itsdangerous`, `pyjwt` y `httpie`. Cada alerta se etiquetó",
        "como `real` (merece conservarse) o `falso_positivo` (se puede descartar).",
        "",
        "## Resumen",
        "",
        "| Métrica | Valor |",
        "|---|---:|",
        f"| Alertas auditadas | {m['alertas_auditadas']} |",
        f"| SAFE auditados | {m['safe_auditados']} |",
        f"| Reales | {m['reales']} |",
        f"| Falsos positivos | {m['falsos_positivos']} |",
        f"| FPRR (FP descartados / total FP) | {m['FPRR']} % |",
        f"| FNR (reales descartados / total reales) | {m['FNR']} % |",
        f"| Precisión de los descartes | {m['precision_descartes']} % |",
        f"| Exactitud | {m['exactitud']} % |",
        "",
        "## Matriz de decisión",
        "",
        "|  | D recomienda descarte (SAFE) | D conserva (VULNERABLE) |",
        "|---|---:|---:|",
        f"| Falso positivo real | {m['TP']} | {m['FN']} |",
        f"| Alerta real | {m['FP']} | {m['TN']} |",
        "",
        "## Límites",
        "",
        "- Muestra pequeña (38 alertas) y un solo anotador.",
        "- Los repos se eligieron por ser conocidos y estar pinneados por commit; no son",
        "  una muestra aleatoria de proyectos Python.",
        "- La etiqueta depende del contexto del caso; la justificación de cada fila está en",
        "  `eval/auditoria_repos.jsonl`.",
        "",
        "## Detalle por alerta",
        "",
        "| # | Repo | Regla | Severidad | D | Etiqueta | Justificación |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in datos["alertas"]:
        lineas.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            f["orden"], f["repo"], f["regla"], f["severidad"],
            f["d_veredicto"], f["etiqueta"], truncar(f["justificacion"])))
    lineas += [
        "",
        "## Reproducción",
        "",
        "```powershell",
        "python eval/auditoria_repos.py --preparar",
        "# editar eval/auditoria_repos.jsonl",
        "python eval/auditoria_repos.py --calcular",
        "```",
        "",
    ]
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preparar", action="store_true")
    parser.add_argument("--calcular", action="store_true")
    args = parser.parse_args()
    if args.preparar:
        return preparar()
    if args.calcular:
        return calcular()
    print("Usa --preparar o --calcular")
    return 1


if __name__ == "__main__":
    sys.exit(main())
