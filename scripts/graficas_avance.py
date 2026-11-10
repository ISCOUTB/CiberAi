"""Genera las gráficas para Avance 5 / memoria final.

Lee los resultados de eval/ y escribe imágenes en reportes/:

    - grafica_comparativa_desarrollo.png
    - grafica_comparativa_holdout.png
    - grafica_banco_sintetico.png
    - grafica_auditoria_repos.png
    - grafica_cobertura_owasp.png
    - grafica_casi_duplicados.png

Uso:
    python scripts/graficas_avance.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reportes"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NAVY = "#0F1633"
BLUE = "#2864E8"
CYAN = "#1DB6D9"
MUTED = "#64708B"
LIGHT = "#E3E8F4"
RED = "#E85C5C"
GREEN = "#2DA44E"


def metricas(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))["metricas"]


def save(fig, nombre):
    path = OUT_DIR / nombre
    fig.savefig(path, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print("guardado:", path)


def comparativa(metricas_dict, titulo, nombre, ylabel="Porcentaje"):
    """Barras agrupadas FPRR/FNR para varias configuraciones."""
    configs = list(metricas_dict.keys())
    fprr = [metricas_dict[c]["FPRR"] for c in configs]
    fnr = [metricas_dict[c]["FNR"] for c in configs]

    x = np.arange(len(configs))
    ancho = 0.35

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    rects1 = ax.bar(x - ancho / 2, fprr, ancho, label="FPRR", color=BLUE)
    rects2 = ax.bar(x + ancho / 2, fnr, ancho, label="FNR", color=CYAN)

    ax.set_ylabel(ylabel, color=NAVY, fontsize=9)
    ax.set_title(titulo, color=NAVY, fontsize=10, loc="left")
    ax.set_xticks(x)
    ax.set_xticklabels(configs, color=NAVY, fontsize=9)
    ax.set_ylim(0, max(max(fprr), max(fnr), 10) * 1.15)
    ax.axhline(5, color=RED, linestyle="--", linewidth=1.2, label="Meta FNR ≤ 5 %")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.grid(True, axis="y", color=LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#C9D2E3")
    ax.tick_params(colors=MUTED, labelsize=8)

    for rect in rects1 + rects2:
        height = rect.get_height()
        if height > 0:
            ax.annotate("{:.1f}".format(height),
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7, color=NAVY)

    fig.tight_layout()
    save(fig, nombre)


def grafica_comparativa_desarrollo():
    datos = {
        "A": metricas(ROOT / "eval" / "resultados_A.json"),
        "C": metricas(ROOT / "eval" / "resultados_C.json"),
        "C0": metricas(ROOT / "eval" / "resultados_C0.json"),
        "D": metricas(ROOT / "eval" / "resultados_D.json"),
    }
    comparativa(
        datos,
        "Comparativa de configuraciones — conjunto de desarrollo (n=141)",
        "grafica_comparativa_desarrollo.png",
    )


def grafica_comparativa_holdout():
    datos = {
        "A": metricas(ROOT / "eval" / "resultados_holdout_A.json"),
        "C0": metricas(ROOT / "eval" / "resultados_holdout_C0.json"),
        "D": metricas(ROOT / "eval" / "resultados_holdout_D.json"),
    }
    comparativa(
        datos,
        "Comparativa de configuraciones — holdout (n=111)",
        "grafica_comparativa_holdout.png",
    )


def grafica_banco_sintetico():
    data = json.loads((ROOT / "eval" / "banco_sintetico.json").read_text(encoding="utf-8"))
    m_base = data["metricas"]["base"]
    m_d = data["metricas"]["d"]

    configs = ["Base", "D"]
    fprr = [m_base["FPRR"], m_d["FPRR"]]
    fnr = [m_base["FNR"], m_d["FNR"]]

    x = np.arange(len(configs))
    ancho = 0.35

    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.bar(x - ancho / 2, fprr, ancho, label="FPRR", color=BLUE)
    ax.bar(x + ancho / 2, fnr, ancho, label="FNR", color=CYAN)

    ax.set_ylabel("Porcentaje", color=NAVY, fontsize=9)
    ax.set_title("Banco sintético — 26 alertas, 14 reales / 12 FP", color=NAVY, fontsize=10, loc="left")
    ax.set_xticks(x)
    ax.set_xticklabels(configs, color=NAVY, fontsize=9)
    ax.set_ylim(0, max(max(fprr), max(fnr), 10) * 1.15)
    ax.axhline(5, color=RED, linestyle="--", linewidth=1.2, label="Meta FNR ≤ 5 %")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.grid(True, axis="y", color=LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#C9D2E3")
    ax.tick_params(colors=MUTED, labelsize=8)

    for i, (v1, v2) in enumerate(zip(fprr, fnr)):
        ax.annotate("{:.1f}".format(v1), xy=(i - ancho / 2, v1), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=7, color=NAVY)
        ax.annotate("{:.1f}".format(v2), xy=(i + ancho / 2, v2), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=7, color=NAVY)

    fig.tight_layout()
    save(fig, "grafica_banco_sintetico.png")


def grafica_auditoria_repos():
    data = json.loads((ROOT / "eval" / "auditoria_repos_metricas.json").read_text(encoding="utf-8"))
    m = data["metricas"]

    configs = ["Auditoría repos\nreales"]
    fprr = [m["FPRR"]]
    fnr = [m["FNR"]]

    x = np.arange(len(configs))
    ancho = 0.35

    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    ax.bar(x - ancho / 2, fprr, ancho, label="FPRR", color=GREEN)
    ax.bar(x + ancho / 2, fnr, ancho, label="FNR", color=CYAN)

    ax.set_ylabel("Porcentaje", color=NAVY, fontsize=9)
    ax.set_title("Auditoría manual de repos reales — 38 alertas", color=NAVY, fontsize=10, loc="left")
    ax.set_xticks(x)
    ax.set_xticklabels(configs, color=NAVY, fontsize=9)
    ax.set_ylim(0, 115)
    ax.axhline(5, color=RED, linestyle="--", linewidth=1.2, label="Meta FNR ≤ 5 %")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.grid(True, axis="y", color=LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#C9D2E3")
    ax.tick_params(colors=MUTED, labelsize=8)

    ax.annotate("{:.1f}".format(fprr[0]), xy=(x[0] - ancho / 2, fprr[0]), xytext=(0, 3),
                textcoords="offset points", ha="center", fontsize=7, color=NAVY)
    ax.annotate("{:.1f}".format(fnr[0]), xy=(x[0] + ancho / 2, fnr[0]), xytext=(0, 3),
                textcoords="offset points", ha="center", fontsize=7, color=NAVY)

    fig.tight_layout()
    save(fig, "grafica_auditoria_repos.png")


def grafica_cobertura_owasp():
    data = json.loads((ROOT / "eval" / "cobertura_owasp.json").read_text(encoding="utf-8"))
    cats = ["A01", "A02", "A03", "A08", "sin_categoria"]
    labels = ["A01", "A02", "A03", "A08", "Sin\ncategoría"]
    dev = [data["conjuntos"]["desarrollo"]["por_categoria"].get(c, 0) for c in cats]
    hold = [data["conjuntos"]["holdout"]["por_categoria"].get(c, 0) for c in cats]

    x = np.arange(len(labels))
    ancho = 0.35

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar(x - ancho / 2, dev, ancho, label="Desarrollo", color=BLUE)
    ax.bar(x + ancho / 2, hold, ancho, label="Holdout", color=CYAN)

    ax.set_ylabel("Alertas", color=NAVY, fontsize=9)
    ax.set_title("Cobertura OWASP Top 10 2021 por categoría", color=NAVY, fontsize=10, loc="left")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=NAVY, fontsize=9)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.grid(True, axis="y", color=LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#C9D2E3")
    ax.tick_params(colors=MUTED, labelsize=8)

    for i, (v1, v2) in enumerate(zip(dev, hold)):
        if v1:
            ax.annotate(str(v1), xy=(i - ancho / 2, v1), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=7, color=NAVY)
        if v2:
            ax.annotate(str(v2), xy=(i + ancho / 2, v2), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=7, color=NAVY)

    fig.tight_layout()
    save(fig, "grafica_cobertura_owasp.png")


def grafica_casi_duplicados():
    data = json.loads((ROOT / "eval" / "casi_duplicados.json").read_text(encoding="utf-8"))
    hist = data["resumen"]["histograma_max_total"]
    bins = list(hist.keys())
    vals = list(hist.values())

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    bars = ax.bar(bins, vals, color=BLUE, edgecolor=NAVY, linewidth=0.5)

    # Resaltar los bins sobre el umbral 0.8
    for bar, b in zip(bars, bins):
        if b in ("0.8-0.9", "0.9-1.0"):
            bar.set_color(CYAN)

    ax.set_xlabel("Similitud máxima de una función del holdout con train/val", color=NAVY, fontsize=9)
    ax.set_ylabel("Funciones del holdout", color=NAVY, fontsize=9)
    ax.set_title("Distribución de similitud train/val → holdout (n=111)", color=NAVY, fontsize=10, loc="left")
    ax.grid(True, axis="y", color=LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#C9D2E3")
    ax.tick_params(colors=MUTED, labelsize=8)

    for bar in bars:
        height = bar.get_height()
        if height:
            ax.annotate(str(int(height)),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7, color=NAVY)

    pct = data["resumen"]["porcentaje_sobre_umbral"]
    ax.axvline(x=3.5, color=RED, linestyle="--", linewidth=1.2)
    ax.text(3.6, max(vals) * 0.9, " umbral 0,8\n {} % ≥ umbral".format(pct),
            color=RED, fontsize=8, va="top")

    fig.tight_layout()
    save(fig, "grafica_casi_duplicados.png")


def main():
    grafica_comparativa_desarrollo()
    grafica_comparativa_holdout()
    grafica_banco_sintetico()
    grafica_auditoria_repos()
    grafica_cobertura_owasp()
    grafica_casi_duplicados()
    print("\nTodas las gráficas generadas en", OUT_DIR)


if __name__ == "__main__":
    main()
