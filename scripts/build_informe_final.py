"""Genera docs/INFORME_FINAL.md uniendo y renumerando los borradores.

Uso:
    python scripts/build_informe_final.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "INFORME_FINAL.md"

FILES = [
    ("Introducción", DOCS / "BORRADOR_INTRODUCCION.md", 1),
    ("Estado del arte", DOCS / "BORRADOR_ESTADO_ARTE.md", 2),
    ("Metodología", DOCS / "BORRADOR_METODOLOGIA.md", 3),
    ("Resultados y discusión", DOCS / "BORRADOR_DISCUSION.md", 4),
    ("Conclusiones", DOCS / "BORRADOR_CONCLUSIONES.md", 5),
]

ANEXOS = DOCS / "BORRADOR_ANEXOS.md"

NAVY = "#0F1633"
BLUE = "#2864E8"
CYAN = "#1DB6D9"


def clean_borrador(text, chapter_num):
    """Quita título de borrador y cita, renombra encabezados."""
    lines = text.splitlines()
    # Quitar primera línea # Borrador ...
    if lines and lines[0].startswith("# Borrador"):
        lines = lines[1:]
    # Quitar bloque de cita
    while lines and lines[0].strip() == "":
        lines = lines[1:]
    if lines and lines[0].startswith(">"):
        while lines and (lines[0].startswith(">") or lines[0].strip() == ""):
            lines = lines[1:]
    # Renombrar encabezados del capítulo
    text = "\n".join(lines)
    # Patrones tipo ## 5.1, ### 5.1.1, ## 7.1, ## 8.1, etc.
    # Reemplazar el número del capítulo por el nuevo
    old_prefix = None
    for m in re.finditer(r"^(#{1,3})\s+(\d+)\.(\d+)", text, re.MULTILINE):
        old_prefix = int(m.group(2))
        break
    if old_prefix is not None:
        text = re.sub(
            r"^(#{1,3})\s+" + str(old_prefix) + r"\.(\d+(?:\.\d+)?)",
            r"\1 " + str(chapter_num) + r".\2",
            text,
            flags=re.MULTILINE,
        )
    return text.strip()


def make_toc(text):
    """Genera tabla de contenidos a partir de encabezados # y ##, ignorando bloques de código."""
    toc = ["## Tabla de contenidos\n"]
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("# ") and not line.startswith("# Borrador"):
            title = line[2:].strip()
            anchor = re.sub(r"[^\w\s-]", "", title).strip().lower().replace(" ", "-")
            toc.append(f"- [{title}](#{anchor})\n")
        elif line.startswith("## "):
            title = line[3:].strip()
            anchor = re.sub(r"[^\w\s-]", "", title).strip().lower().replace(" ", "-")
            toc.append(f"  - [{title}](#{anchor})\n")
    return "".join(toc)


def main():
    parts = []

    # Portada
    parts.append("# Agente inteligente para la revisión de seguridad de código fuente\n")
    parts.append(
        "## Trabajo de Fin de Grado — Memoria final\n\n"
        "**Integrantes:** Santiago Reyes, Marien Daniela, Luis Patron, William Cuello  \n"
        "**Asignatura:** Proyecto de Ingeniería  \n"
        "**Fecha:** 9 de noviembre de 2026  \n"
        "**Rama:** `feature/sprint-7`  \n\n"
        "---\n\n"
    )

    # Resumen
    parts.append(
        "## Resumen\n\n"
        "Este proyecto implementa un agente local de triage para alertas de Bandit sobre "
        "código Python, usando un Qwen2.5-Coder-1.5B afinado con QLoRA y cuantizado a Q4_K_M. "
        "El agente opera en modo asesor: recomienda descartar alertas que parecen falsos "
        "positivos, pero nunca las elimina del reporte. Sobre el conjunto de desarrollo, el "
        "modelo afinado (D) alcanza FPRR 48,0 % y FNR 5,5 %; en el holdout, FPRR 30,4 % y "
        "FNR 9,2 %. Con la política B403 obligatoria el FNR del holdout baja a 3,1 %, pero el "
        "intervalo de confianza superior (10,5 %) impide demostrar que se cumple la meta de "
        "≤ 5 %. Un banco sintético de 26 alertas y una auditoría manual sobre tres repositorios "
        "reales complementan la evidencia: el banco muestra que D decide principalmente por la "
        "severidad del SAST, mientras que la auditoría de repos reales es favorable (FPRR 100 %, "
        "FNR 0 %) pero no generalizable. El análisis de casi-duplicados encuentra que el 70,3 % "
        "de las funciones del holdout tienen un vecino ≥ 0,8 en train/val, lo que debilita la "
        "independencia de la partición. La contribución principal no es el ahorro de revisión, "
        "sino la comparación rigurosa que permite saber cuándo es aceptable y cuándo no: en esta "
        "versión, el descarte automático queda fuera de alcance.\n\n"
        "**Palabras clave:** análisis estático de seguridad, SAST, triage, modelos de lenguaje, "
        "fine-tuning, QLoRA, Bandit, Python, OWASP.\n\n"
        "---\n\n"
    )

    # Cuerpo
    body_text = ""
    for title, path, num in FILES:
        text = path.read_text(encoding="utf-8")
        cleaned = clean_borrador(text, num)
        body_text += f"\n\n# {num}. {title}\n\n{cleaned}\n"

    # Anexos
    anexos_text = ANEXOS.read_text(encoding="utf-8")
    anexos_clean = clean_borrador(anexos_text, None)
    body_text += f"\n\n# Anexos\n\n{anexos_clean}\n"

    # Insertar figuras en el cuerpo
    figs = {
        "## 3.3 Ajuste QLoRA": [
            "![Curva de pérdida](reportes/curva_perdida.png)",
            "*Figura 1. Pérdida de entrenamiento del adaptador LoRA (1 época, 11.510 ejemplos). "
            "La curva de validación no se incluye porque las evaluaciones intermedias quedaron "
            "invalidadas por truncamiento de ejemplos largos.*",
        ],
        "## 4.1 El intercambio entre ahorro y omisión": [
            "![Comparativa desarrollo](reportes/grafica_comparativa_desarrollo.png)",
            "*Figura 2. Comparativa de FPRR y FNR en desarrollo.*",
        ],
        "## 4.4 Validez de la partición y del holdout": [
            "![Comparativa holdout](reportes/grafica_comparativa_holdout.png)",
            "*Figura 3. Comparativa de FPRR y FNR en el holdout.*",
            "",
            "![Casi-duplicados](reportes/grafica_casi_duplicados.png)",
            "*Figura 7. Similitud máxima entre funciones del holdout y train/val.*",
        ],
        "## 3.9 Marco OWASP y cobertura declarada": [
            "![Cobertura OWASP](reportes/grafica_cobertura_owasp.png)",
            "*Figura 4. Cobertura OWASP Top 10 2021 por categoría.*",
        ],
        "## 4.12 Evidencia posterior: banco sintético y repositorios reales": [
            "![Banco sintético](reportes/grafica_banco_sintetico.png)",
            "*Figura 5. Banco sintético: FPRR y FNR base vs D.*",
            "",
            "![Auditoría repos](reportes/grafica_auditoria_repos.png)",
            "*Figura 6. Auditoría manual de repos reales.*",
        ],
    }

    lines = body_text.splitlines()
    new_lines = []
    for line in lines:
        new_lines.append(line)
        for heading, fig_lines in figs.items():
            # Match heading ignoring trailing spaces
            if line.strip() == heading.strip():
                new_lines.append("")
                new_lines.extend(fig_lines)
                new_lines.append("")
    body_text = "\n".join(new_lines)

    # TOC
    toc = make_toc(body_text)

    parts.append(toc)
    parts.append("\n---\n")
    parts.append(body_text)

    OUT.write_text("".join(parts), encoding="utf-8")
    print("guardado:", OUT)
    print("caracteres:", len("".join(parts)))


if __name__ == "__main__":
    main()
