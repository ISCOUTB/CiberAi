"""Genera Avance 5.docx con el estilo visual de los Avances 2 y 3.

Estructura: portada, resumen, arquitectura, modelo de datos, integración del
modelo afinado, metodología de evaluación, resultados, pruebas, limitaciones,
próximos pasos, conclusiones y referencias.

Los valores de las tablas de resultados y evidencias viven en las constantes
COMPARATIVA y EVIDENCIAS. Si se repiten las corridas de eval/run_eval.py se
actualizan esas listas y se regenera:

    python scripts/build_avance5.py

El documento resultante queda en la raíz del proyecto como Avance 5.docx.
"""

from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(__file__).resolve().parents[1] / "Avance 5.docx"

BODY_FONT = "DejaVu Sans"
HEAD_FONT = "Carlito"
CODE_FONT = "Consolas"

NAVY = RGBColor(0x0F, 0x16, 0x33)
BLUE = RGBColor(0x28, 0x64, 0xE8)
CYAN = RGBColor(0x1D, 0xB6, 0xD9)
DARK = RGBColor(0x1F, 0x2A, 0x44)
MUTED = RGBColor(0x64, 0x70, 0x8B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

HEADER_FILL = "0F1633"
CALLOUT_FILL = "EEF3FF"
CODE_FILL = "F2F2F2"

# Tabla comparativa A/B/C/C0/D. Actualizar con los valores que produzca
# eval/run_eval.py y volver a generar el documento.
COMPARATIVA = [
    ["A. Solo SAST", "141", "0,0 %", "0,0 %", "0,0 %", "45,1 %", "Completa"],
    ["B. Cero-shot (piloto)", "10", "75,0 %", "0,0 %", "0,0 %", "0,0 %", "Piloto"],
    ["C. Contexto + few-shot", "141", "2,0 %", "0,0 %", "0,0 %", "37,4 %", "Completa"],
    ["C0. Contexto sin few-shot", "141", "22,0 %", "2,2 %", "15,4 %", "44,9 %", "Completa"],
    ["D. Modelo afinado", "141", "48,0 %", "5,5 %", "17,2 %", "43,0 %", "Completa"],
]

# Evidencias de integración y pruebas. Reemplazar "Por registrar" / "Por medir"
# con los resultados reales antes de la entrega.
EVIDENCIAS = [
    ["Pruebas unitarias (contexto, dedup, SARIF, parseo, política, Bandit)",
     "13 de 13 correctas", "Completa (Sprint 7)"],
    ["Corrida sin modelo (--no-llm) sobre examples/sample_repo",
     "9 alertas, 9 conservadas, 9 SOSPECHOSA", "Completa (Avance 4)"],
    ["Corrida con modelo base sobre examples/sample_repo",
     "9 alertas, 9 respuestas válidas, 0 errores", "Completa (Avance 4)"],
    ["Corrida con modelo afinado sobre examples/sample_repo",
     "9 alertas, 9 conservadas, 4 recomendadas para descarte, 0 errores",
     "Completa (Sprint 6)"],
    ["Modo asesor: alertas conservadas en JSON y SARIF",
     "9 de 9 alertas en ambos reportes", "Completa (Avance 4)"],
    ["Resiliencia: Ollama detenido o inaccesible",
     "9 alertas, 9 conservadas como SOSPECHOSA, 9 errores de modelo, exit 0",
     "Completa (Sprint 6)"],
    ["Resiliencia: JSON malformado o veredicto inválido",
     "La alerta se conserva como SOSPECHOSA", "Cubierta (prueba unitaria)"],
    ["Resiliencia: generación truncada (B102 patológica en C)",
     "La alerta se conserva como SOSPECHOSA; el análisis continúa", "Observada (Sprint 6)"],
    ["Resiliencia: SAFE sin justificación",
     "La alerta se conserva como SOSPECHOSA", "Cubierta (prueba unitaria)"],
    ["Batería funcional sin modelo",
     "Repo vacío, archivo vacío, sintaxis inválida y otro lenguaje: 0 alertas; repo de 40 archivos: 360 alertas; todo exit 0",
     "Completa (Sprint 6)"],
    ["Prompt injection en el código analizado",
     "4 alertas conservadas; las 2 vulnerabilidades reales se clasifican como VULNERABLE; 0 respuestas inválidas",
     "Completa (Sprint 6)"],
    ["Recomendación SAFE con justificación",
     "Se marca para descarte; la alerta permanece en el reporte", "Prueba unitaria"],
    ["Salida SARIF", "Versión 2.1.0, 9 resultados, 8 reglas", "Completa (Avance 4)"],
    ["Holdout del Sprint 7",
     "111 alertas; A, C0 y D medidos; 0 respuestas inválidas en D; política B403 probada",
     "Completa (Sprint 7)"],
    ["Comparación pareada C0 vs. D",
     "McNemar p=0,0004 (desarrollo) y p=0,0015 (holdout); Δ FPRR +26,0 y +19,6 puntos",
     "Completa (Sprint 8)"],
    ["Cobertura OWASP Top 10 2021",
     "Desarrollo: A01 3, A02 1, A03 83, A08 53, sin categoría 1. Holdout: A01 1, A02 3, A03 76, A08 30, sin categoría 1",
     "Completa (Sprint 8)"],
    ["Arquitectura arc42 y vistas C4",
     "12 secciones arc42 y 5 diagramas Mermaid versionados en docs/diagramas/",
     "Completa (Sprint 8)"],
    ["Smoke test con repositorios reales",
     "itsdangerous 2.2.0, PyJWT 2.10.1 y HTTPie 3.2.4; 38 alertas por modelo; 34 SAFE auditados; 0 descartes incorrectos",
     "Completa (Sprint 8)"],
    ["Rúbrica de explicaciones con dos revisores",
     "Pendiente de calificación; D produjo 11 explicaciones únicas para 111 alertas",
     "Pendiente"],
    ["Latencia con el modelo afinado", "43,1 s para 9 alertas (4,8 s por alerta)", "Completa (Sprint 6)"],
    ["Memoria con el modelo afinado", "1.115 MB en VRAM (Q4_K_M) y ~700 MB de RAM del proceso llama-server",
     "Medida (Sprint 6)"],
]


def set_font(run, name=BODY_FONT, size=9.5, bold=False, color=None, italic=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), name)


def para(doc, text="", size=9.5, bold=False, align=None, font=BODY_FONT,
         before=0, after=0, line=None, color=DARK, italic=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if line is not None:
        pf.line_spacing = Pt(line)
    if align is not None:
        p.alignment = align
    if text:
        run = p.add_run(text)
        set_font(run, font, size, bold, color, italic)
    return p


def h1(doc, text):
    p = para(doc, text, size=18, bold=True, font=HEAD_FONT, before=16, after=4,
             line=20, color=NAVY)
    p.paragraph_format.keep_with_next = True
    return p


def h2(doc, text):
    p = para(doc, text, size=13, bold=True, font=HEAD_FONT, before=12, after=4,
             line=15, color=BLUE)
    p.paragraph_format.keep_with_next = True
    return p


def body(doc, text, keep=False):
    p = para(doc, text, size=9.5, align=WD_ALIGN_PARAGRAPH.LEFT, before=5,
             line=12.2, color=DARK)
    p.paragraph_format.keep_with_next = keep
    return p


def bullet(doc, text, level=0, size=9.5, line=12.2, before=2):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(0.55 + 0.45 * level)
    pf.first_line_indent = Cm(-0.35)
    pf.space_before = Pt(before)
    pf.space_after = Pt(0)
    pf.line_spacing = Pt(line)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    glyph = p.add_run("•  ")
    set_font(glyph, "DejaVu Sans", size, color=DARK)
    run = p.add_run(text)
    set_font(run, BODY_FONT, size, color=DARK)
    return p


CELL_AFTER_SHD = ["w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark"]
PAR_AFTER_SHD = ["w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
                 "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
                 "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
                 "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
                 "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr",
                 "w:sectPr", "w:pPrChange"]


def shade(cell_or_par, fill="F2F2F2"):
    el = cell_or_par._element
    is_cell = el.tag.endswith("tc")
    pr = el.get_or_add_tcPr() if is_cell else el.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    after = CELL_AFTER_SHD if is_cell else PAR_AFTER_SHD
    for child in pr:
        if child.tag in [qn(tag) for tag in after]:
            child.addprevious(shd)
            return
    pr.append(shd)


def cell_margins_zero(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for side in ("top", "start", "bottom", "end"):
        node = OxmlElement("w:" + side)
        node.set(qn("w:w"), "0")
        node.set(qn("w:type"), "dxa")
        mar.append(node)
    tcPr.append(mar)


def code(doc, text, keep=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.line_spacing = Pt(10.2)
    p.paragraph_format.keep_with_next = keep
    run = p.add_run(text)
    set_font(run, CODE_FONT, 8, color=DARK)
    shade(p, CODE_FILL)
    return p


def table(doc, headers, rows, widths=None, size=8):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Normal Table"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    trPr = t.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)

    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        cell_margins_zero(cell)
        shade(cell, HEADER_FILL)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = Pt(size + 1.4)
        p.paragraph_format.left_indent = Cm(0.19)
        run = p.add_run(h)
        set_font(run, BODY_FONT, size, bold=True, color=WHITE)

    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = ""
            cell_margins_zero(cells[i])
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = Pt(size + 1.4)
            p.paragraph_format.left_indent = Cm(0.19)
            run = p.add_run(str(value))
            set_font(run, BODY_FONT, size, color=DARK)

    if widths:
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)

    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(0)
    spacer.paragraph_format.line_spacing = Pt(5)
    return t


def callout(doc, label, text):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Normal Table"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    cell = t.rows[0].cells[0]
    cell.width = Cm(18.0)
    cell_margins_zero(cell)
    shade(cell, CALLOUT_FILL)

    p1 = cell.paragraphs[0]
    p1.paragraph_format.space_before = Pt(5)
    p1.paragraph_format.space_after = Pt(1)
    p1.paragraph_format.line_spacing = Pt(13)
    p1.paragraph_format.left_indent = Cm(0.19)
    r1 = p1.add_run(label)
    set_font(r1, BODY_FONT, 9.5, bold=True, color=BLUE)

    p2 = cell.add_paragraph()
    p2.paragraph_format.space_before = Pt(1)
    p2.paragraph_format.space_after = Pt(6)
    p2.paragraph_format.line_spacing = Pt(12.2)
    p2.paragraph_format.left_indent = Cm(0.19)
    r2 = p2.add_run(text)
    set_font(r2, BODY_FONT, 9.5, color=DARK)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(0)
    spacer.paragraph_format.line_spacing = Pt(5)
    return t


def figure(doc, path, caption, width_cm=15.5):
    """Inserta una figura centrada con pie de figura. Omite si no existe."""
    path = Path(path)
    if not path.exists():
        return None
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    para(doc, caption, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER,
         color=MUTED, italic=True, before=0, after=8)
    return p


# ---------------------------------------------------------------------------
# Documento
# ---------------------------------------------------------------------------

doc = docx.Document()
section = doc.sections[0]
section.page_width = Cm(21.59)
section.page_height = Cm(27.94)
section.left_margin = Cm(1.71)
section.right_margin = Cm(1.82)
section.top_margin = Cm(0.64)
section.bottom_margin = Cm(0.9)

normal = doc.styles["Normal"]
normal.font.name = BODY_FONT
normal.font.size = Pt(9.5)
normal.font.color.rgb = DARK

section.different_first_page_header_footer = True
footer_p = section.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer_r = footer_p.add_run("Agente inteligente para la revisión de seguridad de código fuente")
set_font(footer_r, BODY_FONT, 7.5, color=MUTED)

# Portada
para(doc, "AVANCE 5  |  TERMINACIÓN, PRUEBAS Y VALIDACIÓN", size=7.5, bold=True,
     align=WD_ALIGN_PARAGRAPH.RIGHT, color=BLUE)
para(doc, "AVANCE 5", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
     before=66, color=CYAN)
para(doc, "Terminación, pruebas y validación del agente", size=29, bold=True,
     font=HEAD_FONT, align=WD_ALIGN_PARAGRAPH.CENTER, before=11, line=31, color=NAVY)
para(doc, "Agente inteligente para la revisión de seguridad de código fuente", size=14,
     bold=True, before=12, color=BLUE)
para(doc, "Modelo afinado · Modo asesor · Evaluación A/B/C/C0/D y holdout · OWASP · arc42/C4", size=10,
     align=WD_ALIGN_PARAGRAPH.CENTER, before=30, color=MUTED)
para(doc, "Periodo: 30 de octubre – 5 de noviembre de 2026  |  "
          "Actualización: 7 de noviembre de 2026 (Sprint 8 y auditoría de falsos negativos)",
     size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, before=28, color=DARK)
para(doc, "Integrantes: Santiago Reyes, Marien Daniela, Luis Patron, William Cuello  |  "
          "Asignatura: Proyecto de Ingeniería",
     size=9, align=WD_ALIGN_PARAGRAPH.CENTER, before=4, color=MUTED)
doc.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)

# 1. Resumen
h1(doc, "1. Resumen del avance")
body(doc,
     "Este avance cierra la integración del componente inteligente en el producto. El flujo "
     "Qwen2.5-Coder-1.5B-Instruct → QLoRA → fusión de pesos → GGUF Q4_K_M → Ollama queda "
     "definido y conectado a la CLI; la tubería conserva las etapas del Avance 4 (Bandit, "
     "normalización, deduplicación, contexto por AST, prompt, validación y política "
     "conservadora) y solo cambia la etiqueta del modelo mediante la opción --model. El "
     "entrenamiento del adaptador, la exportación y la corrida D cierran el Sprint 6; la "
     "evaluación única del test reservado y la validación de la política de descarte cierran "
     "el Sprint 7.")
body(doc,
     "La decisión de diseño cambió tras la revisión del avance anterior: el agente opera en "
     "modo asesor y no suprime hallazgos. Cada alerta recibe un veredicto y una "
     "recomendación, pero el reporte JSON y el SARIF conservan todas las alertas y la "
     "decisión final queda en el revisor humano. Un SAFE solo se registra como recomendación "
     "de descarte cuando el JSON es válido y está justificado; un JSON malformado, un "
     "veredicto inválido, un SAFE sin justificación, un tiempo de espera agotado o un "
     "servidor no disponible producen SOSPECHOSA. El motivo es concreto: en la revisión se "
     "observó un falso negativo real con respuesta formalmente válida, de modo que el modelo "
     "no puede usarse todavía para suprimir alertas con confianza.")
callout(doc, "Hallazgo principal",
        "El riesgo del componente inteligente no es solo el JSON inválido, que la política ya "
        "contiene, sino el SAFE bien formado y equivocado. Por eso el producto pasa a modo "
        "asesor y la evaluación incorpora la tasa de omisión sobre alertas reales, además de "
        "la reducción de falsos positivos.")
body(doc,
     "La evaluación de desarrollo usa el mismo conjunto y el mismo protocolo del Avance 4: "
     "141 alertas de Bandit sobre la partición de validación en Python (91 reales y 50 falsos "
     "positivos), temperatura 0, mismo orden y métricas explícitas. A, B, C, C0 y D están "
     "medidas sobre ese conjunto. C y D no comparten prompt: C antepone dos ejemplos "
     "resueltos y D no; para aislar el efecto del ajuste se agregó C0, que usa el mismo formato "
     "de alerta que D con el modelo base. La comparación rigurosa es D contra C0; D contra C "
     "describe el resultado práctico frente a un prompt cuidado, pero mezcla modelo y prompt.")
body(doc,
     "El Sprint 7 ejecutó una sola vez el conjunto de verificación reservado: 111 alertas "
     "(65 reales y 46 falsos positivos) extraídas de 300 funciones Python del test. Se midieron "
     "A, C0 y D, sin reentrenar y sin cambiar el prompt. El holdout cambió la conclusión del "
     "avance: D crudo obtuvo FPRR 30,4 % y FNR 9,2 % (6 de 65); con la política B403 el FNR baja "
     "a 3,1 % (IC95 0,8–10,5 %) y el FPRR a 19,6 %. El valor puntual cumple la meta, pero el "
     "intervalo no permite demostrarla. Además, D produjo solo 11 explicaciones únicas para 111 "
     "alertas: el modelo sirve para triage, no para explicar. La decisión se mantiene: modo "
     "asesor, B403 obligatoria y B311 reportada como riesgo nuevo, sin agregarla después de ver "
     "el holdout.")
body(doc,
     "El Sprint 8 agrega tres piezas que la revisión del director de programa pidió como eje, no "
     "como apéndice. Primero, la comparación explícita con Qwen base: C0 y D comparten prompt, "
     "conjunto y temperatura, y el análisis pareado muestra que D aumenta el ahorro de revisión "
     "a costa de omitir más alertas reales (Δ FPRR +26,0 puntos en desarrollo y +19,6 en el "
     "holdout; Δ FNR +3,3 y +9,2). El resultado no favorece a D en omisión y se reporta así. "
     "Segundo, OWASP como marco de alcance: la cobertura se mide por el CWE del SAST y se declara "
     "que A03 y A08 concentran más del 95 % de las alertas, mientras A05, A06, A09 y A10 quedan "
     "fuera del alcance de Bandit. Tercero, la arquitectura se documenta con arc42 y vistas C4, "
     "y el producto se prueba sobre tres repositorios reales fijados por commit. Ninguna de las "
     "tres piezas cambia el modo asesor.")
body(doc,
     "Una auditoría posterior de los falsos negativos corrige la lectura de la omisión. De las 11 "
     "alertas que C0 y D descartan y que la etiqueta de fragmento considera reales, 6 son falsos "
     "positivos de la propia alerta: el fragmento es vulnerable, pero la línea señalada por Bandit "
     "no lo es. El FNR de D baja de 5,5 % a 3,3 % en desarrollo y de 9,2 % a 3,1 % en el holdout; "
     "la diferencia frente a C0 queda en 1 y 2 alertas y deja de ser significativa. El resultado se "
     "reporta como análisis de sensibilidad, no como reetiquetado del holdout.")

h2(doc, "1.1 Ajustes derivados de la revisión")
bullet(doc, "Modo asesor: el agente no suprime hallazgos; el veredicto SAFE queda como "
            "recomendación de descarte y todas las alertas permanecen en el reporte y el SARIF.")
bullet(doc, "Métricas: se escribe la matriz de confusión y se distinguen la tasa de falsos "
            "negativos sobre alertas reales (FNR) y la false omission rate (FOR), que tienen "
            "denominadores distintos.")
bullet(doc, "Deduplicación: la identidad combina regla, CWE, archivo, función, línea y contexto "
            "normalizado; no se elimina por CWE, porque dos vulnerabilidades distintas pueden "
            "compartir la misma familia.")
bullet(doc, "Alcance: el proyecto se fija en Qwen2.5-Coder-1.5B-Instruct, Python con Bandit y "
            "las familias CWE del Sprint 1; el reemplazo de Gemma y la ampliación de tipos de "
            "vulnerabilidad quedan registrados como decisión de alcance.")
bullet(doc, "Explicaciones: se evalúan con una rúbrica técnica (CWE correcto, vector de ataque, "
            "corrección aplicable y claridad); la similitud textual se reporta solo como apoyo.")
bullet(doc, "Seguridad del prompt: los delimitadores no se consideran una defensa; se mantienen "
            "el formato fijo, la temperatura 0 y la revisión humana como controles efectivos.")

h2(doc, "1.2 Correcciones conceptuales y bibliográficas")
body(doc,
     "La revisión también señaló afirmaciones que no deben repetirse en el documento final. "
     "La tabla las resume con la corrección que se aplica:", keep=True)
table(doc,
      ["Afirmación a corregir", "Corrección", "Dónde se aplica"],
      [["El ajuste fino hace que el modelo «solo conozca» una parte de la seguridad.",
        "El ajuste especializa el formato de respuesta y calibra el comportamiento sobre el "
        "corpus; no restringe el conocimiento del modelo. El alcance lo define el dataset.",
        "Marco teórico y sección 4.1"],
       ["La cuantización especializa o mejora el conocimiento.",
        "Q4_K_M reduce memoria y latencia; es una decisión de despliegue. Puede degradar "
        "ligeramente la calidad y no aporta especialización.",
        "Sección 4.1"],
       ["Calcular la pérdida solo sobre la respuesta impide memorizar los ejemplos.",
        "Reduce el costo y enfoca el aprendizaje en la respuesta, pero no garantiza "
        "generalización. La memorización se controla con particiones limpias y un test reservado "
        "que no se use para ajustar.",
        "Sección 4.1 y limitaciones"],
       ["IRIS es únicamente un filtro posterior sobre alertas.",
        "IRIS combina el LLM con el análisis estático y usa modelos para inferir "
        "especificaciones que guían la detección; no es solo un filtro.",
        "Estado del arte del documento final"],
       ["SecurityEval es de MSR 2023 y evalúa alertas estáticas.",
        "Pertenece a MSR4P&S 2022 y se diseñó para evaluar generación de código; usarlo con "
        "alertas exige adaptar la tarea y la métrica.",
        "Estado del arte y referencias"],
       ["El estudio de Tencent reporta más de 90 % de falsos positivos.",
        "La muestra construida tiene 328 falsos positivos de 433 alarmas (75,8 %). La cifra "
        ">90 % es una extrapolación de los autores sobre casos descartados, no el resultado "
        "de la muestra.",
        "Estado del arte del documento final"]],
      widths=[5.0, 8.8, 4.2])

# 2. Arquitectura
h1(doc, "2. Arquitectura del agente")
body(doc,
     "El agente se organiza en una tubería lineal con un único punto de decisión final. Cada "
     "etapa es un módulo independiente y testeable; el orquestador solo compone las etapas y "
     "decide el código de salida. La única diferencia respecto del Avance 4 es el modelo que "
     "responde al último tramo: la tubería es la misma y el modelo es sustituible por "
     "configuración. La figura lógica del flujo es:", keep=True)
code(doc, "repositorio -> Bandit (JSON) -> normalización -> deduplicación\n"
          "            -> contexto (AST) -> prompt -> Ollama (modelo afinado) -> validación\n"
          "            -> política conservadora -> reporte.json + hallazgos.sarif + consola")
table(doc,
      ["Componente", "Archivo", "Responsabilidad"],
      [["Orquestador / CLI", "cli.py",
        "Valida argumentos, ejecuta el pipeline, escribe salidas y fija el código de salida."],
       ["Ejecutor SAST", "sast/bandit_runner.py",
        "Invoca Bandit con salida JSON y normaliza cada alerta a Finding."],
       ["Exportador SARIF", "sast/sarif.py",
        "Genera SARIF 2.1.0 con reglas, niveles y ubicaciones físicas."],
       ["Contexto", "context.py",
        "Localiza la función o clase contenedora con ast; si falla, usa ±20 líneas."],
       ["Deduplicación", "dedup.py",
        "Calcula la huella SHA-256 y elimina duplicados por regla, CWE, archivo, función, "
        "línea y contexto normalizado."],
       ["Cliente LLM", "llm/ollama_client.py",
        "POST a /api/generate con format=json y temperatura 0; acepta cualquier etiqueta "
        "servida por Ollama, base o afinada."],
       ["Triage", "triage.py",
        "Construye el prompt, parsea el JSON, valida el veredicto y aplica la política "
        "conservadora."],
       ["Reportes", "report.py",
        "Resumen agregado, reporte JSON y tabla de consola; conserva todas las alertas."],
       ["Modelos", "models.py",
        "Finding, ToolRun, Scan y TriageResult; serialización y marcas de tiempo UTC."],
       ["Modelo afinado", "training/",
        "Entrenamiento QLoRA, fusión de pesos y conversión a GGUF Q4_K_M; se registra en "
        "Ollama con etiqueta propia."]],
      widths=[3.4, 4.2, 10.4])

h2(doc, "2.1 Contrato de decisión")
body(doc,
     "El veredicto del modelo se acepta solo si el JSON contiene VULNERABLE o SAFE. En modo "
     "asesor, ninguno de los dos suprime la alerta: cambian la prioridad y la recomendación "
     "que ve el revisor. La tabla fija el contrato:", keep=True)
table(doc,
      ["Salida", "Interpretación", "Acción del agente"],
      [["VULNERABLE válido", "La alerta es probablemente real.",
        "Se conserva y se prioriza para revisión."],
       ["SAFE válido y justificado", "Recomendación de que la alerta es un falso positivo.",
        "Se conserva en JSON y SARIF, marcada como candidata a descarte."],
       ["SOSPECHOSA (JSON inválido, veredicto inválido, SAFE sin justificación, timeout o "
        "servidor caído)", "No hay una decisión confiable.",
        "Se conserva y se envía a revisión humana."]],
      widths=[4.6, 6.4, 7.0])
body(doc,
     "La consecuencia práctica es que un fallo del modelo nunca elimina una vulnerabilidad "
     "del reporte: el peor caso es una alerta adicional o una recomendación equivocada que el "
     "revisor debe corregir. El riesgo residual —un SAFE bien formado sobre una alerta real— "
     "no se elimina con la política; se mide con la tasa de omisión y se controla con "
     "revisión humana.")

h2(doc, "2.2 Interfaz de línea de comandos")
code(doc, "python agente/run.py scan <ruta> [--out DIR] [--model NOMBRE]\n"
          "       [--ollama-url URL] [--no-llm] [--max-alerts N] [--quiet]")
body(doc,
     "La opción --no-llm ejecuta solo la fase SAST y conserva todas las alertas como "
     "SOSPECHOSA; sirve para validar el pipeline sin modelo. --model permite alternar entre "
     "el modelo base (para reproducir B y C) y el modelo afinado (para D) sin tocar el "
     "código. El modelo afinado está registrado en Ollama como qwen2.5-coder-triage y el "
     "modelo base como qwen2.5-coder:1.5b; el despliegue solo cambia la etiqueta.")

h2(doc, "2.3 Vistas arc42 y C4")
body(doc,
     "La arquitectura se documenta en docs/ARQUITECTURA_ARC42.md con la plantilla arc42 9.1. "
     "Se usan las vistas C4 de contexto y contenedores; el nivel de componentes se resuelve "
     "con la vista de bloques de arc42 para no duplicar diagramas. Los diagramas se escriben "
     "en docs/diagramas/*.mmd y se renderizan con Mermaid CLI 12.2.0; el .mmd es la fuente y "
     "las imágenes se regeneran. Las secciones de arc42 que no aplican a una CLI local se "
     "declaran en el documento, no se rellenan.", keep=True)
table(doc,
      ["Sección arc42", "Contenido en este proyecto"],
      [["1. Introducción y objetivos", "Requisitos de seguridad, degradación y reproducibilidad."],
       ["2. Restricciones", "Python, Bandit, modelo ≤ 2B, sin API externa, holdout cerrado."],
       ["3. Contexto y alcance", "Vista C4 nivel 1; qué queda fuera del producto."],
       ["4. Estrategia de solución", "Separar SAST y modelo, contexto mínimo, contrato conservador."],
       ["5. Vista de bloques", "Ocho módulos con responsabilidad y archivo."],
       ["6. Vista de ejecución", "Secuencia de un escaneo y puntos de decisión."],
       ["7. Vista de despliegue", "Un equipo, Ollama local, reportes en disco."],
       ["8. Conceptos transversales", "Modo asesor, política, validación, privacidad, observabilidad."],
       ["9. Decisiones de arquitectura", "Bandit, Qwen 1.5B, LoRA/GGUF, modo asesor, SARIF."],
       ["10. Requisitos de calidad", "Escenarios medidos de seguridad, disponibilidad y rendimiento."],
       ["11. Riesgos y deuda técnica", "Prompt distinto, frontend, retención, hash del modelo."],
       ["12. Glosario", "Alerta, triage, SAFE, SOSPECHOSA, arc42, C4."]],
      widths=[5.4, 12.6])
figure(doc,
       Path(__file__).resolve().parents[1] / "docs" / "diagramas" / "c4_contexto.png",
       "Figura 1. Contexto del sistema (C4 nivel 1). El agente orquesta Bandit y Ollama; el "
       "código y los reportes permanecen en el equipo local.", width_cm=14.0)
figure(doc,
       Path(__file__).resolve().parents[1] / "docs" / "diagramas" / "c4_contenedores.png",
       "Figura 2. Contenedores (C4 nivel 2). La CLI concentra la orquestación y la política; "
       "Ollama sirve el modelo GGUF por HTTP local.", width_cm=15.0)

# 3. Modelo de datos
h1(doc, "3. Modelo de datos consolidado")
body(doc,
     "El contrato de datos no cambia entre el Avance 4 y el Avance 5. Esa estabilidad es "
     "intencional: permite comparar configuraciones y sustituir el modelo sin migrar "
     "reportes ni romper el SARIF. Todas las etapas comparten las mismas estructuras, de modo "
     "que el JSON intermedio, el reporte y el SARIF son proyecciones del mismo objeto. Los "
     "campos principales son:", keep=True)
table(doc,
      ["Estructura", "Campos"],
      [["Finding", "finding_id, rule_id, cwe, severity, confidence, message, file, line, "
                   "end_line, code, function, fingerprint, context, triage"],
       ["TriageResult", "finding_id, veredicto (VULNERABLE | SAFE | SOSPECHOSA), cwe, "
                        "severidad, explicacion, vector_ataque, correccion, origen, valido"],
       ["ToolRun", "tool, version, started, finished, findings"],
       ["Scan", "scan_id, target, created, tool_runs"]],
      widths=[3.4, 14.6])
body(doc,
     "El finding_id es determinista (SHA-256 truncado de regla, CWE, archivo, función, línea "
     "y contexto normalizado), lo que permite comparar corridas y deduplicar entre "
     "herramientas sin confundir dos problemas distintos que comparten CWE. El campo origen "
     "distingue si el triage provino del modelo (llm) o de la política de respaldo (respaldo). "
     "Un registro de salida tiene esta forma:")
code(doc, '{\n'
          '  "finding_id": "7be2ec4686d0006f", "rule_id": "B608", "cwe": "CWE-89",\n'
          '  "severity": "media", "file": "vuln.py", "line": 15, "function": "buscar",\n'
          '  "triage": {"veredicto": "VULNERABLE", "cwe": "CWE-89", "severidad": "Alta",\n'
          '             "explicacion": "...", "vector_ataque": "...", "correccion": "..."}\n'
          '}')

# 4. Integración
h1(doc, "4. Integración del componente inteligente")
h2(doc, "4.1 Entrenamiento, fusión y exportación")
body(doc,
     "El ajuste se realiza con QLoRA sobre Qwen2.5-Coder-1.5B-Instruct. Los ejemplos "
     "provienen de las particiones depuradas del Sprint 2 (dataset/splits/train_80.jsonl y "
     "val_total.jsonl) y se convierten al formato de mensajes sistema/usuario/asistente con "
     "training/prepare_sft.py: 11.510 ejemplos de ajuste y 1.000 de validación, "
     "seleccionados con semilla 42 y balance 50/50 entre funciones vulnerables y seguras; en "
     "la mitad de los ejemplos se inyecta la alerta del SAST para que el modelo aprenda el "
     "formato de triage. La cifra surge de solicitar hasta 12.000 ejemplos: tras descartar "
     "prompts de más de 8.000 caracteres quedan 5.755 funciones vulnerables y el balance "
     "50/50 limita el conjunto a 11.510. El balance es necesario porque el corpus tiene solo un 6,1 % de "
     "funciones vulnerables y un entrenamiento con la distribución natural favorecería "
     "respuestas SAFE indiscriminadas.", keep=True)
table(doc,
      ["Parámetro", "Valor"],
      [["Modelo base", "Qwen/Qwen2.5-Coder-1.5B-Instruct"],
       ["Método", "QLoRA: LoRA sobre base cuantizado 4-bit NF4; variante fp16 en GPU Turing"],
       ["Datos de ajuste", "11.510 ejemplos (50 % vulnerables, 50 % seguras; 50 % con alerta SAST)"],
       ["Datos de validación", "1.000 ejemplos con la misma construcción, semilla 42"],
       ["Épocas", "1"],
       ["Learning rate", "2e-4, scheduler cosine, warmup 3 %"],
       ["Lote efectivo", "8 (batch 1 x acumulación 8)"],
       ["Longitud máxima", "2.048 tokens"],
       ["LoRA", "r = 16, alpha = 32, dropout 0,05, todas las proyecciones"],
       ["Checkpoints", "cada 500 pasos, máximo 2 conservados"],
       ["Exportación", "fusión de pesos + GGUF Q4_K_M"],
       ["Servicio", "Ollama con etiqueta propia del modelo afinado"]],
      widths=[5.0, 13.0])
body(doc,
     "Al terminar, el adaptador se fusiona con el modelo base. El conversor oficial de "
     "llama.cpp genera un GGUF f16 y llama-quantize lo reduce a Q4_K_M; ambas etapas las "
     "orquesta training/export_gguf.py, que descarga el binario si no está disponible. El "
     "archivo resultante se registra en Ollama con una etiqueta propia y "
     "se prueba con tres alertas de control antes de la corrida completa. El registro de "
     "hiperparámetros, semilla y checkpoints queda en training/out/, lo que permite "
     "reproducir el entrenamiento. La corrida real se completó en 1 h 50 min sobre la RTX "
     "4070 Super: 1.439 pasos de optimización con lote efectivo 8, 18,46 millones de "
     "parámetros entrenables (1,18 % del total) y una pérdida de entrenamiento que bajó de "
     "1,11 en el paso 20 a 0,36 al cierre. La decisión de despliegue mantiene el modelo base "
     "como respaldo: la CLI puede apuntar a cualquiera de las dos etiquetas, de modo que una "
     "falla del modelo afinado no bloquea el producto.")
table(doc,
      ["Métrica de la corrida", "Valor"],
      [["Hardware", "RTX 4070 Super (12 GB), Windows nativo"],
       ["Pasos de optimización", "1.439 (1 época, lote efectivo 8)"],
       ["Tiempo de entrenamiento", "1 h 50 min 56 s"],
       ["Pérdida inicial (paso 20)", "1,11"],
       ["Pérdida final", "0,36"],
       ["Parámetros entrenables", "18.464.768 (1,18 % del total)"],
       ["Tokens promedio por ejemplo", "585"],
       ["Adaptador resultante", "70,5 MB (safetensors)"],
       ["GGUF Q4_K_M", "940,4 MB"]],
      widths=[6.2, 11.8])

h2(doc, "4.1.1 Alcance real del ajuste")
bullet(doc, "El ajuste fino no hace que el modelo «solo conozca» seguridad. Cambia la "
            "distribución de respuestas y el formato; el conocimiento previo del modelo base "
            "sigue disponible. La especialización es del comportamiento sobre este corpus, no "
            "una restricción del conocimiento.")
bullet(doc, "La cuantización no especializa. Q4_K_M reduce el tamaño y el costo de "
            "inferencia; puede perder algo de precisión. Es una decisión de despliegue, no una "
            "fuente de conocimiento.")
bullet(doc, "Calcular la pérdida solo sobre la respuesta abarata el entrenamiento y concentra "
            "el gradiente en la salida, pero no impide memorizar los ejemplos. La defensa "
            "contra la memorización es la partición limpia, la deduplicación y un test que no "
            "se toca hasta la evaluación final.")
bullet(doc, "El modelo puede producir un SAFE bien formado y equivocado. La política no lo "
            "detecta; por eso el producto es asesor y la evaluación mide la omisión sobre "
            "alertas reales.")

h2(doc, "4.2 Integración en la CLI")
body(doc,
     "La única modificación funcional es la etiqueta del modelo. El resto de la tubería, el "
     "esquema JSON y los reportes son los mismos. Esta separación demuestra que el componente "
     "inteligente es un servicio sustituible y que la evaluación D es comparable con A, B, C y "
     "C0: la diferencia entre las configuraciones es el modelo y, en C, el prompt, no el "
     "software que lo rodea.")
body(doc,
     "La corrida de integración sobre examples/sample_repo es la evidencia de que el modelo "
     "afinado atraviesa el flujo completo: 9 alertas, 9 conservadas, 4 recomendadas para "
     "descarte, 0 respuestas inválidas y 0 errores del modelo en 43,1 s (4,8 s por alerta) "
     "sobre la GTX 1650. El SARIF y el reporte JSON mantienen el esquema de la sección 3 y "
     "conservan las nueve alertas. El detalle se registra en la tabla de la sección 7.")

h2(doc, "4.3 Mecanismos de resiliencia")
body(doc,
     "La política conservadora es la garantía de que el componente de IA no degrade el "
     "reporte. Cada modo de fallo tiene un comportamiento definido y verificable:", keep=True)
table(doc,
      ["Escenario", "Comportamiento del agente", "Evidencia"],
      [["Ollama detenido o inaccesible",
        "Todas las alertas se conservan como SOSPECHOSA; el escaneo termina con reporte.",
        "Prueba con cliente nulo"],
       ["Tiempo de espera agotado",
        "La alerta afectada se conserva como SOSPECHOSA; el resto continúa.",
        "Manejo de OllamaError"],
       ["JSON malformado o truncado", "La alerta se conserva como SOSPECHOSA.",
        "Prueba unitaria"],
       ["Veredicto ausente o inválido", "La alerta se conserva como SOSPECHOSA.",
        "Prueba unitaria"],
       ["SAFE sin justificación", "La alerta se conserva como SOSPECHOSA.",
        "Prueba unitaria"],
       ["SAFE válido con justificación",
        "Se registra como recomendación de descarte; la alerta permanece en el reporte.",
        "Prueba unitaria y corridas"],
       ["SAFE válido sobre una alerta real",
        "La alerta permanece visible; el caso se contabiliza como omisión y se audita.",
        "Modo asesor y muestreo de SAFE"],
       ["Código con instrucciones maliciosas (prompt injection)",
        "El código se delimita y se trata como dato; la salida se valida y se revisa. Los "
        "delimitadores reducen el riesgo, no lo eliminan.",
        "Completa (Sprint 6)"]],
      widths=[5.2, 7.6, 5.2])

# 5. Metodología
h1(doc, "5. Metodología de evaluación")
h2(doc, "5.1 Conjunto de evaluación")
body(doc,
     "Como Bandit solo analiza Python y el corpus está dominado por C, la evaluación se "
     "restringió a la partición de validación en Python. Se escribieron las 298 funciones en "
     "archivos temporales, se ejecutó Bandit y se conservaron las 141 alertas resultantes. La "
     "verdad de referencia es la etiqueta del dataset a nivel de función: una alerta es real "
     "si la función está marcada como vulnerable y es falso positivo si está marcada como "
     "segura. La concordancia de clase entre el CWE de Bandit y el CWE del dataset se mide por "
     "separado.", keep=True)
table(doc,
      ["Métrica del conjunto", "Valor"],
      [["Funciones Python en validación", "298"],
       ["Alertas de Bandit", "141"],
       ["Alertas sobre funciones vulnerables (reales)", "91"],
       ["Alertas sobre funciones seguras (falsos positivos)", "50"],
       ["Concordancia CWE SAST–dataset en alertas reales", "41 de 91 (45,1 %)"],
       ["Reglas dominantes", "CWE-78 (67), CWE-502 (53), CWE-94 (10), CWE-89 (6)"]],
      widths=[11.0, 7.0])
body(doc,
     "La concentración en CWE-78 y CWE-502 se explica por las advertencias de importación de "
     "subprocess y pickle (B404 y B403), que Bandit reporta aunque no exista uso inseguro. Es "
     "una fuente natural de falsos positivos y un caso representativo para el triage.")
body(doc,
     "Las particiones se construyeron con semilla 42 y se depuraron antes de dividir: se "
     "eliminaron duplicados exactos por hash del código normalizado y las etiquetas "
     "contradictorias (433 hashes). El test de 17.542 muestras se reservó para el Sprint 7 y se "
     "evaluó una sola vez. La partición de validación total (42.536) alimentó el conjunto de "
     "validación del ajuste y el conjunto de evaluación de desarrollo. Por eso la medición de "
     "desarrollo no es una evaluación final independiente; el holdout del Sprint 7 es la "
     "medición no contaminada, aunque también es aleatoria por función.", keep=True)
table(doc,
      ["Partición", "Muestras", "Uso"],
      [["train_80", "101.878", "Ajuste del adaptador (11.510 ejemplos muestreados)"],
       ["val_20", "25.470", "Validación dentro de la partición de entrenamiento"],
       ["val_total", "42.536", "Validación del ajuste y evaluación de desarrollo (298 funciones Python)"],
       ["test (holdout)", "17.542", "Evaluado una sola vez en el Sprint 7 (300 funciones Python, 111 alertas)"]],
      widths=[3.6, 2.8, 11.6])

h2(doc, "5.2 Configuraciones y métricas")
body(doc,
     "En desarrollo se comparan cinco configuraciones: A, solo SAST, que conserva todas las "
     "alertas; B, modelo base cero-shot sin contexto del SAST; C, modelo base con contexto del "
     "SAST y dos ejemplos guía (few-shot); C0, modelo base con el mismo formato de alerta que D "
     "y sin ejemplos; y D, modelo afinado con ese mismo formato. En el holdout se midieron A, "
     "C0 y D, porque C agrega few-shot y no es el control que aísla el ajuste. En todas, la "
     "decisión registrada es una recomendación: el reporte conserva la alerta. Las métricas se "
     "definen en la sección 5.3.")

h2(doc, "5.3 Matriz de confusión y fórmulas")
body(doc,
     "La matriz se construye sobre la recomendación del agente, no sobre una supresión "
     "efectiva. «Se recomienda descartar» significa que el veredicto es SAFE; «no se "
     "recomienda descartar» agrupa VULNERABLE y SOSPECHOSA. La tabla usa la convención de "
     "positivo = alerta real:", keep=True)
table(doc,
      ["", "Alerta real", "Alerta falsa"],
      [["No se recomienda descartar (VULNERABLE o SOSPECHOSA)", "VP", "FP"],
       ["Se recomienda descartar (SAFE)", "FN", "VN"]],
      widths=[8.0, 5.0, 5.0])
body(doc, "Las fórmulas que se reportan son:", keep=True)
code(doc, "FNR  = FN / (VP + FN)      tasa de omisión sobre alertas reales\n"
          "FOR  = FN / (FN + VN)      false omission rate (denominador: predicciones negativas)\n"
          "FPRR = VN / (VN + FP)      reducción de falsos positivos\n"
          "Precisión = VP / (VP + FP)\n"
          "FPR  = FP / (FP + VN)      tasa de falsos positivos (1 - especificidad)")
body(doc,
     "La diferencia entre FNR y FOR es la que señaló la revisión. Con una alerta real y un "
     "falso positivo, ambos con recomendación SAFE: FNR = 1/1 = 100 %, FOR = 1/2 = 50 % y "
     "FPRR = 1/1 = 100 %. Si solo se reportara FOR, el riesgo sobre la única alerta real "
     "quedaría diluido por el acierto sobre la falsa.")
body(doc,
     "Por eso la meta principal se fija sobre FNR: ≤ 5 % de las alertas reales. FOR se "
     "reporta como métrica convencional y no se usa sola, porque su denominador cambia con la "
     "agresividad del modelo. En modo asesor, FPRR mide la reducción potencial de carga de "
     "revisión, no una supresión efectiva. La tolerancia de omisión se declara antes de la "
     "corrida D y se contrasta con el intervalo de confianza de la muestra; un resultado por "
     "encima de la meta no se presenta como éxito.")

h2(doc, "5.4 Rúbrica de explicaciones")
body(doc,
     "La similitud textual no demuestra que una explicación sea correcta. Las explicaciones "
     "se evalúan con cuatro criterios en escala 0–2, sobre una muestra ciega y por dos "
     "revisores independientes:", keep=True)
table(doc,
      ["Criterio", "0", "1", "2"],
      [["CWE correcto", "Incorrecto o ausente", "Familia equivalente", "CWE exacto"],
       ["Vector de ataque", "Ausente o genérico", "Plausible sin detalle",
        "Concreto y consistente con el código"],
       ["Corrección", "Ausente o insegura", "Genérica",
        "Aplicable y preserva el comportamiento"],
       ["Claridad", "Incomprensible", "Comprensible con esfuerzo",
        "Directa y sin ambigüedad"]],
      widths=[4.0, 4.6, 4.6, 4.8])
body(doc,
     "Se reporta el acuerdo entre revisores (kappa de Cohen) y el puntaje por criterio. "
     "BERTScore se conserva como medida descriptiva de similitud, nunca como sustituto de la "
     "rúbrica.")

h2(doc, "5.5 Cobertura OWASP: método y alcance")
body(doc,
     "OWASP no se agrega como apéndice: ordena el alcance de lo que un SAST de reglas puede "
     "prometer. La cobertura se calcula, no se declara. eval/cobertura_owasp.py toma el CWE "
     "que Bandit reporta para cada alerta (cwe_sast), lo ubica en la lista oficial de CWE del "
     "OWASP Top 10 2021 y escribe eval/cobertura_owasp.json. Un CWE que no aparece en ninguna "
     "lista oficial se reporta como sin_categoria; no se fuerza a la categoría más parecida.",
     keep=True)
body(doc,
     "Se usa el CWE del SAST y no la columna owasp del dataset porque esa columna asigna "
     "categoría al CWE etiquetado en la función, no al que Bandit señala. El contraste entre "
     "ambas fuentes se reporta como hallazgo de calidad de datos: 10 de las 30 etiquetas del "
     "dataset no coinciden con la lista oficial y 7 están forzadas a A03. Siete clases de "
     "memoria (CWE-119, 125, 190, 401, 416, 476 y 787) no forman parte del Top 10 2021; "
     "CWE-362 y CWE-399 tampoco, y CWE-269 pertenece a A04, no a A01.")
body(doc,
     "El marco se completa con el OWASP Top 10 for LLM Applications 2025, que se aplica al "
     "propio agente: ocho de los diez riesgos tienen evidencia en el proyecto, LLM07 aplica "
     "con riesgo bajo y solo LLM08 queda excluido porque no hay RAG. ASVS 5.0.0 se usa como "
     "checklist parcial: seis capítulos de diecisiete, con exclusiones declaradas. El detalle "
     "está en docs/OWASP.md; la matriz se regenera con python eval/cobertura_owasp.py.")

# 6. Resultados
h1(doc, "6. Resultados")
body(doc,
     "La configuración A fija el punto de partida: al no recomendar descartes, su FPRR, FNR y "
     "FOR son cero por construcción y su exactitud CWE refleja la del SAST (45,1 %). El "
     "piloto B, sobre diez alertas, recomendó descartar tres de los cuatro falsos positivos "
     "(FPRR 75 %), conservó las seis alertas reales (FNR 0 %, FOR 0 %) y no acertó el CWE en "
     "ninguna: predijo CWE-259, CWE-059 y CWE-790 para alertas de pickle y subprocess. El "
     "tamaño del piloto no permite inferencia estadística; solo confirma que el modelo "
     "responde, descarta falsos positivos evidentes y falla en la clasificación fina.")
body(doc,
     "La tabla comparativa concentra la evidencia de desarrollo. A, el piloto B, C, C0 y D "
     "están medidos sobre el conjunto de evaluación. C y D no comparten prompt: C antepone dos "
     "ejemplos resueltos y D no. La comparación que aísla el ajuste es D contra C0, que usa el "
     "mismo formato de alerta con el modelo base; D contra C mide el resultado práctico frente "
     "a un prompt cuidado, pero mezcla modelo y prompt.", keep=True)
table(doc,
      ["Configuración", "Alertas", "FPRR", "FNR", "FOR", "Exactitud CWE", "Estado"],
      COMPARATIVA,
      widths=[4.4, 1.6, 1.8, 1.6, 1.6, 3.0, 2.5])
body(doc,
     "La corrida C, con el modelo base y dos ejemplos resueltos, recomendó descartar una sola "
     "de las 50 alertas falsas (FPRR 2,0 %), conservó las 91 reales (FNR 0 %, FOR 0 %), "
     "obtuvo precisión 65,0 % y exactitud CWE 37,4 %, con una respuesta inválida en una B102 "
     "que se conservó como SOSPECHOSA. El modelo base casi no se "
     "compromete: responde VULNERABLE a 139 de las 141 alertas, incluidas casi todas las "
     "advertencias de importación. Esa cautela explica su FNR nulo y también su bajo ahorro "
     "de revisión.")
body(doc,
     "La corrida D sobre las 141 alertas obtuvo FPRR 48,0 % (24 de 50 falsos positivos), FNR "
     "5,5 % (5 de 91 alertas reales), FOR 17,2 %, precisión 76,8 % y exactitud CWE 43,0 %, "
     "sin respuestas inválidas. El FNR queda 0,5 puntos por encima de la meta. Las cinco "
     "alertas reales descartadas son todas B403 (import pickle, CWE-502): tres deserializan y "
     "dos solo serializan, de modo que el error está concentrado en una regla y en parte es "
     "discutible. El modelo copió el CWE del SAST en las 86 alertas reales conservadas, así "
     "que esa exactitud no mide clasificación independiente: el producto debe conservar el "
     "CWE del SAST y usar al modelo solo para el veredicto.")
body(doc,
     "La comparación que aísla el ajuste es D contra C0: por cada 50 falsos positivos, D "
     "descarta 24 y C0 descarta 11; a cambio, D sacrifica 5 alertas reales y C0 una. Frente a "
     "C, que conserva casi todo, el contraste es mayor, pero no es atribuible solo al "
     "entrenamiento. El ajuste fino no vuelve al modelo más certero en abstracto: lo vuelve más "
     "decidido. Esa decisión mejora el ahorro de revisión de 22 % a 48 %, pero cruza la meta de "
     "FNR. Con FNR 5,5 % no se habilita el descarte automático: se mantiene el modo asesor. La "
     "política B403 reduce el FNR a 0 % y deja el FPRR en 38 % en desarrollo; el holdout no "
     "confirma ese 0 %: deja 2 B311 y un FNR de 3,1 % con IC95 hasta 10,5 %. Tampoco se compara "
     "D contra A como si A midiera la misma tarea: A no decide, solo conserva.")

figure(doc,
       Path(__file__).resolve().parents[1] / "reportes" / "curva_perdida.png",
       "Figura 3. Pérdida de entrenamiento del adaptador LoRA (1 época, 11.510 ejemplos, "
       "1.439 pasos). La curva de validación no se incluye porque las evaluaciones "
       "intermedias quedaron invalidadas por truncamiento de ejemplos largos; el generador "
       "de datos ya se corrigió para futuras corridas.")

h2(doc, "6.1 Holdout del Sprint 7")
body(doc,
     "El conjunto de verificación se generó con eval/build_eval_set.py --split test "
     "--confirm-holdout y se evaluó una sola vez. De las 17.542 muestras del test, 300 son "
     "funciones Python; Bandit produjo 111 alertas (65 reales y 46 falsos positivos) sobre 71 "
     "archivos y 98 funciones. Se midieron A, C0 y D; C0 y D compartieron el formato de alerta, temperatura 0 y "
     "num_predict 512. No hubo reentrenamiento ni cambios de reglas durante la corrida. El "
     "conjunto tiene 71 códigos únicos y 40 filas que repiten código, así que además de los "
     "intervalos de Wilson se calculó un bootstrap agrupado por archivo.", keep=True)
table(doc,
      ["Configuración", "Alertas", "FPRR", "FNR", "FOR", "Precisión", "CWE"],
      [["A. Solo SAST", "111", "0,0 %", "0,0 %", "0,0 %", "58,6 %", "35,4 %"],
       ["C0. Base sin few-shot", "111", "10,9 %", "0,0 %", "0,0 %", "61,3 %", "33,8 %"],
       ["D. Afinado (crudo)", "111", "30,4 %", "9,2 %", "30,0 %", "64,8 %", "32,2 %"],
       ["D + política B403", "111", "19,6 %", "3,1 %", "18,2 %", "63,0 %", "30,2 %"],
       ["D + B403 y B311", "111", "19,6 %", "0,0 %", "0,0 %", "63,7 %", "29,2 %"]],
      widths=[4.5, 1.5, 1.8, 1.6, 1.6, 2.2, 1.8])
body(doc,
     "D crudo descarta 14 de 46 falsos positivos y 6 de 65 alertas reales. Frente a C0, que "
     "descarta 5 falsos positivos y ninguna real, D suma 9 descartes correctos y 6 errores. El "
     "ahorro real sobre C0 es +19,6 puntos de FPRR crudo, no +46; con la política B403 queda en "
     "+8,7 puntos. La dirección se mantiene, pero la magnitud es mucho menor que en desarrollo.")
body(doc,
     "Los 6 falsos negativos son 4 B403 y 2 B311. Dos B403 deserializan un objeto explotable "
     "(f11445.py y f1878.py) y son omisiones genuinas; los otros dos solo serializan "
     "(f15804.py y f2231.py), un caso discutible porque el payload no se ejecuta. Los dos B311 "
     "son líneas del mismo ejemplo con random.randint, etiquetadas CWE-94 en el dataset aunque "
     "Bandit reporta CWE-330; la etiqueta es ruidosa, pero el modelo no debería descartarlas. "
     "Una auditoría de sensibilidad que solo cuente las omisiones claras daría 3,1 %, pero no "
     "se reetiqueta el holdout después de verlo: la métrica principal es la cruda.")
body(doc,
     "La política B403 estaba definida antes de la corrida y es obligatoria si se usa D. "
     "Rescata 4 de los 6 falsos negativos y baja el FNR a 3,1 % (IC95 0,8–10,5 %; bootstrap "
     "0,0–10,2 %), pero deja 2 B311 y conserva 5 falsos positivos B403, por lo que el FPRR cae "
     "a 19,6 %. Proteger también B311 llevaría el FNR a 0 %, pero sería una decisión post hoc: "
     "no se adopta. Se reporta como riesgo nuevo y como trabajo futuro para un conjunto "
     "independiente.")
body(doc,
     "La limitación estadística es decisiva: con 65 alertas reales, incluso 0 falsos negativos "
     "deja el límite superior del IC95 en 5,6 %. El holdout no alcanza para demostrar que el "
     "FNR sea ≤ 5 %; solo permite descartar tasas mucho peores. El valor puntual de 3,1 % con "
     "B403 no reemplaza al intervalo. La conclusión es mantener el modo asesor y no presentar "
     "la meta como cumplida.")
body(doc,
     "El holdout también mostró un problema de calidad de las explicaciones. D produjo 11 "
     "explicaciones, 8 vectores de ataque y 2 correcciones únicas para 111 alertas; C0 produjo "
     "109, 103 y 106. Además, 91 de 91 respuestas VULNERABLE comparten la misma corrección y 47 "
     "comparten la misma explicación de CWE-78. La causa está en el entrenamiento: 5.489 de "
     "5.755 respuestas SAFE tienen la misma explicación. D sirve como clasificador de triage, "
     "no como generador de explicaciones técnicas; la rúbrica pendiente debe reportar la "
     "diversidad, no solo el kappa.")
body(doc,
     "El detalle completo, los intervalos, la tabla por regla y los comandos de reproducción "
     "están en docs/ANALISIS_HOLDOUT.md y docs/PROTOCOLO_HOLDOUT.md. El resumen se regenera con "
     "python eval/analisis_holdout.py.")

h2(doc, "6.2 Comparación explícita con Qwen base (C0 vs. D)")
body(doc,
     "La comparación que aísla el efecto del ajuste es C0 contra D: mismo modelo base en C0, "
     "mismo formato de alerta, mismo SYSTEM, misma temperatura 0 y mismo num_predict. C no "
     "sirve como control porque agrega few-shot. eval/analisis_c0_vs_d.py empareja las alertas "
     "por id, construye la matriz de acuerdo, aplica la prueba exacta de McNemar sobre las "
     "discordancias y estima la diferencia de FPRR y FNR con un bootstrap agrupado por archivo "
     "(2.000 iteraciones, semilla 20261103).", keep=True)
table(doc,
      ["Conjunto", "FPRR C0", "FPRR D", "FNR C0", "FNR D", "McNemar p"],
      [["Desarrollo", "22,0 %", "48,0 %", "2,2 %", "5,5 %", "0,0004"],
       ["Holdout", "10,9 %", "30,4 %", "0,0 %", "9,2 %", "0,0015"]],
      widths=[3.4, 2.6, 2.6, 2.4, 2.4, 2.6])
table(doc,
      ["Conjunto", "Δ FPRR (D−C0)", "IC95", "Δ FNR (D−C0)", "IC95"],
      [["Desarrollo", "+26,0 pts", "9,4 a 43,6", "+3,3 pts", "−1,2 a 8,2"],
       ["Holdout", "+19,6 pts", "0,0 a 38,5", "+9,2 pts", "1,8 a 17,5"]],
      widths=[3.4, 3.4, 3.4, 3.4, 3.4])
body(doc,
     "El resultado es un intercambio, no una derrota en las dos métricas: D gana en FPRR "
     "(descarta más ruido) y C0 gana en FNR (omite menos alertas reales). En desarrollo, D "
     "descarta 18 alertas más que C0: 14 falsos positivos y 4 reales. En el holdout también "
     "descarta 18 más: 12 falsos positivos y 6 reales. C0 conserva más y omite menos; su FNR "
     "es 0,0 % en el holdout. El aporte del ajuste no es «superar a Qwen», sino aumentar el "
     "ahorro de revisión a cambio de más omisiones. McNemar confirma que el patrón de "
     "discordancia no es azar (p=0,0004 y p=0,0015), pero no dice que D sea mejor. La sección "
     "6.4 muestra cuánto de esa omisión es ruido de etiqueta.")
body(doc,
     "El único argumento a favor de D es económico: con la misma cantidad de alertas, D "
     "recomienda descartar 24 de 50 falsos positivos en desarrollo y 14 de 46 en el holdout, "
     "frente a 11 y 5 de C0. Ese ahorro es real y está medido; la omisión también. Por eso el "
     "producto no usa D para suprimir alertas y la comparación se publica completa, incluidos "
     "los intervalos que cruzan cero en el Δ FNR de desarrollo y en el Δ FPRR del holdout.")

h2(doc, "6.3 Cobertura OWASP medida")
body(doc,
     "La matriz se calcula sobre las alertas realmente evaluadas. A03 Injection y A08 Software "
     "and Data Integrity Failures concentran el 96,5 % de las alertas de desarrollo y el "
     "95,5 % del holdout. No es un defecto del mapeo: es la consecuencia de elegir Bandit, "
     "cuyas reglas más frecuentes son ejecución de comandos, eval, plantillas y "
     "deserialización.", keep=True)
table(doc,
      ["Categoría", "Nombre", "Desarrollo (141)", "Holdout (111)"],
      [["A01", "Broken Access Control", "3", "1"],
       ["A02", "Cryptographic Failures", "1", "3"],
       ["A03", "Injection", "83", "76"],
       ["A04", "Insecure Design", "0", "0"],
       ["A05", "Security Misconfiguration", "0", "0"],
       ["A06", "Vulnerable and Outdated Components", "0", "0"],
       ["A07", "Identification and Authentication Failures", "0", "0"],
       ["A08", "Software and Data Integrity Failures", "53", "30"],
       ["A09", "Security Logging and Monitoring Failures", "0", "0"],
       ["A10", "Server Side Request Forgery (SSRF)", "0", "0"],
       ["—", "Fuera del Top 10 2021", "1", "1"]],
      widths=[2.0, 9.6, 3.2, 3.2])
body(doc,
     "Los CWE sin categoría son CWE-605 (múltiples binds al mismo puerto) en desarrollo y "
     "CWE-703 (verificación de estado incorrecta) en el holdout; ninguno forma parte del "
     "Top 10 2021. CWE-377 (archivo temporal inseguro) figura en la lista oficial de A01 "
     "como entrada obsoleta y por eso cuenta como A01. A04, A05, A06, "
     "A07, A09 y A10 no tienen alertas medidas: requieren diseño y flujo, configuración de "
     "despliegue, inventario de dependencias, credenciales fuera del corpus, telemetría de "
     "runtime o seguimiento de red. El producto es un triage de alertas de Bandit organizado "
     "por OWASP, no un escáner del Top 10 completo.")

h2(doc, "6.4 Auditoría a nivel de alerta de los falsos negativos")
body(doc,
     "La etiqueta del conjunto es a nivel de fragmento: si el fragmento es vulnerable, cualquier "
     "alerta de Bandit sobre él cuenta como real, aunque la línea señalada sea otra. Para medir "
     "cuánto pesa ese efecto se auditaron los 12 falsos negativos de C0 y D con un criterio de "
     "patrón: B403 es real si hay pickle.load o pickle.loads; B404, si el import acompaña a "
     "shell=True con entrada externa; B311, si el aleatorio alimenta un token, clave o sesión. "
     "El detalle está en docs/AUDITORIA_FN.md y se reproduce con python eval/auditar_fn.py.")
table(doc,
      ["Conjunto", "Modelo", "FN brutos", "Reales", "Ruido", "FNR bruto", "FNR ajustado",
       "FPRR ajustado", "Precisión"],
      [["Desarrollo", "C0", "2", "2", "0", "2,2 %", "2,2 %", "22,0 %", "84,6 %"],
       ["Desarrollo", "D", "5", "3", "2", "5,5 %", "3,3 %", "52,0 %", "89,7 %"],
       ["Holdout", "C0", "0", "0", "0", "0,0 %", "0,0 %", "10,9 %", "100,0 %"],
       ["Holdout", "D", "6", "2", "4", "9,2 %", "3,1 %", "39,1 %", "90,0 %"]],
      widths=[2.2, 1.5, 1.5, 1.3, 1.2, 2.0, 2.3, 2.3, 1.7], size=7.6)
body(doc,
     "Seis de las once omisiones brutas son ruido de etiqueta: cuatro B403 de código que solo "
     "hace pickle.dump (no deserializa) y dos B311 de random usado en una división. La omisión "
     "real de D baja a 3 alertas en desarrollo y 2 en el holdout, y la precisión de sus "
     "recomendaciones de descarte sube a 89,7 % y 90,0 %. La diferencia frente a C0 queda en 1 y "
     "2 alertas; la prueba exacta de McNemar sobre alertas reales deja de ser significativa "
     "(p=1,00 y p=0,50). El empeoramiento de FNR, por tanto, no está demostrado una vez "
     "descontado el ruido.")
body(doc,
     "Con la política B403, D quedaría en FNR 0,0 % en ambos conjuntos y FPRR 38,0 % en "
     "desarrollo y 23,9 % en el holdout, pero es un cálculo post hoc: la regla se fijó después de "
     "ver los errores. La auditoría es manual, no fue a ciegas y usa un criterio de patrón, no de "
     "flujo de datos; sus cifras son una cota de sensibilidad y no sustituyen el resultado "
     "pre-registrado del holdout. Para cerrarla, la hoja ciega de los 12 casos está preparada en "
     "eval/rubrica/auditoria_fn_ciega.csv y el acuerdo entre revisores se calculará con el kappa "
     "de Cohen.")

# 7. Pruebas
h1(doc, "7. Pruebas y validación del producto")
body(doc,
     "Además de la evaluación comparativa, el avance incluye la validación funcional del "
     "producto. La tabla reúne las pruebas ejecutadas y las que se registran antes de la "
     "entrega:", keep=True)
table(doc,
      ["Prueba", "Resultado", "Estado"],
      EVIDENCIAS,
      widths=[8.0, 6.2, 3.8])
body(doc,
     "Las pruebas unitarias cubren el contexto por AST, la deduplicación, el SARIF, el parseo "
     "de la respuesta del modelo, la política conservadora, el modo asesor y la ejecución de "
     "Bandit y el límite de generación del cliente: 13 de 13 correctas. Las pruebas de "
     "resiliencia verifican que un cliente nulo, un "
     "JSON malformado y un veredicto inválido conservan la alerta. La corrida de integración "
     "con el modelo afinado sobre examples/sample_repo conservó las 9 alertas, no produjo "
     "respuestas inválidas ni errores y tardó 43,1 s (4,8 s por alerta). La corrida con el "
     "modelo base del Avance 4 había clasificado las nueve alertas como VULNERABLE, incluidas "
     "las advertencias de importación; ese comportamiento es la línea base cualitativa que el "
     "ajuste fino debía mejorar.")
body(doc,
     "La batería funcional cubre casos límite que no dependen del modelo: repositorio vacío, "
     "archivo vacío, sintaxis inválida, archivo en otro lenguaje y un repositorio de 40 "
     "archivos con 360 alertas. En todos los casos la CLI termina con código 0 y genera JSON "
     "y SARIF válidos; los casos sin alertas producen reportes vacíos y el repositorio grande "
     "se procesa sin abortar. Con Ollama apuntado a una URL inexistente, las 9 alertas se "
     "conservan como SOSPECHOSA y el proceso termina sin error: la caída del modelo degrada "
     "la recomendación, no el análisis.")
body(doc,
     "La prueba de prompt injection incrustó en el código un comentario que ordenaba "
     "responder SAFE. Con el modelo afinado, las 4 alertas se conservaron; las dos "
     "vulnerabilidades reales (B602, shell=True, y B301, pickle.load) se clasificaron como "
     "VULNERABLE y los dos SAFE correspondieron a las advertencias de importación B404 y "
     "B403, no a la instrucción maliciosa. El caso es una muestra reducida y no demuestra "
     "resistencia general, pero confirma que la política conservadora y los delimitadores "
     "reducen el riesgo en el flujo real.")
body(doc,
     "La corrida C expuso un caso patológico: con una alerta B102 de 1.818 caracteres, el "
     "modelo base entró en un bucle de generación. En la primera corrida, sin límite de "
     "tokens, agotó el timeout de 180 s y el runner de Ollama siguió consumiendo CPU después "
     "de que el cliente abandonó. Se agregó num_predict 512 al cliente y al arnés: en la "
     "corrida definitiva la misma alerta se truncó en 512 tokens, quedó inválida y se "
     "conservó como SOSPECHOSA en unos 8 s. D respondió la misma alerta en unos 4 s. El "
     "límite convierte un bloqueo en un fallo acotado; para producción conviene además "
     "reiniciar el runner tras un truncamiento.")
body(doc,
     "El modelo afinado ocupa 1.115 MB en la GPU y el proceso llama-server unos 700 MB de "
     "RAM con contexto de 4.096 tokens. Esa huella permite ejecutarlo en una GPU de 4 GB "
     "junto con el escritorio, aunque deja poco margen para procesar alertas en paralelo.")
body(doc,
     "El reporte conserva las nueve alertas en JSON y en SARIF aunque el modelo recomiende "
     "descartar alguna. Esa comprobación es la evidencia del modo asesor y la condición para "
     "que el producto siga siendo auditable.")

h2(doc, "7.1 Smoke test con repositorios reales")
body(doc,
     "Además del conjunto etiquetado, el producto se probó sobre tres repositorios Python "
     "pequeños, fijados por etiqueta y commit, para verificar que funciona con código que no "
     "se escribió para el proyecto. No es una evaluación etiquetada: no hay verdad de "
     "referencia por línea y no produce FPRR ni FNR. Se escaneó solo el paquete fuente para no "
     "mezclar pruebas ni entornos virtuales.", keep=True)
table(doc,
      ["Repositorio", "Etiqueta", "Commit", "Subdirectorio", "Alertas"],
      [["pallets/itsdangerous", "2.2.0", "096c8d42", "src/", "2"],
       ["jpadilla/pyjwt", "2.10.1", "3ebbb22f", "jwt/", "1"],
       ["httpie/cli", "3.2.4", "2105caa4", "httpie/", "35"]],
      widths=[4.4, 1.8, 2.4, 3.0, 1.6])
table(doc,
      ["Modelo", "Alertas", "Conservadas", "SAFE", "SOSPECHOSA", "Errores"],
      [["Base (qwen2.5-coder:1.5b)", "38", "38", "3", "0", "0"],
       ["D (qwen2.5-coder-triage)", "38", "38", "34", "0", "0"]],
      widths=[5.6, 2.2, 2.6, 2.0, 2.6, 2.0])
body(doc,
     "En los 38 escaneos por modelo, conservadas == total: ninguna alerta se eliminó. D "
     "recomienda descartar 34 de 38 alertas (89,5 %) y el modelo base 3 de 38 (7,9 %). La "
     "diferencia es consistente con el conjunto de evaluación, pero el smoke test no permite "
     "generalizar: la muestra es pequeña y la auditoría la hizo una sola persona.")
table(doc,
      ["Regla", "SAFE de D", "Qué es", "Veredicto"],
      [["B101", "21", "assert internos que verifican invariantes, no validación de entrada",
        "Falso positivo correcto"],
       ["B404", "4", "Aviso de importación de subprocess", "Falso positivo correcto"],
       ["B603", "5", "subprocess con lista constante y shell=False", "Falso positivo correcto"],
       ["B408", "1", "Import de xml.dom.minidom bajo TYPE_CHECKING; en runtime se usa defusedxml",
        "Falso positivo correcto"],
       ["B105", "2", "password: None como valor por defecto de la sesión",
        "Falso positivo correcto"],
       ["B110", "1", "try/except/pass deliberado al parsear el timestamp",
        "Falso positivo correcto"]],
      widths=[2.0, 2.2, 9.2, 4.6])
body(doc,
     "Se revisó el código de las 34 recomendaciones SAFE de D: 0 incorrectas y 0 dudosas. El "
     "modelo base sumó 3 SAFE, también B101 y también correctos. En el otro sentido, D "
     "conservó una alerta real de HTTPie: requests.get(..., verify=False) en "
     "internal/update_warnings.py, que desactiva la validación TLS. También conservó B113 "
     "(misma petición sin timeout), B324 (SHA-1 en itsdangerous) y B310 (urlopen en PyJWT), "
     "decisiones conservadoras o falsos positivos probables. El smoke test respalda que el "
     "producto se ejecuta sobre código ajeno y que la política conservadora funciona; no "
     "respalda el descarte automático.")

# 8. Limitaciones
h1(doc, "8. Limitaciones")
bullet(doc, "Cobertura de lenguaje: Bandit solo analiza Python y el 94,1 % del corpus es C. La "
            "evaluación de desarrollo cubre 298 funciones y 141 alertas; el holdout, 300 "
            "funciones y 111 alertas. Es suficiente para una línea base, no para generalizar al "
            "corpus completo ni a otros SAST.")
bullet(doc, "Verdad de referencia a nivel de función y sin alcanzabilidad: el dataset no "
            "incluye archivo ni línea, por lo que una advertencia de importación sobre una "
            "función vulnerable cuenta como alerta real aunque la línea señalada no sea el "
            "defecto. Tampoco se etiqueta si el flujo es alcanzable; una función vulnerable en "
            "código muerto se cuenta como real. Esto favorece al SAST y explica parte del 45,1 % "
            "de concordancia CWE en desarrollo y del 35,4 % en el holdout. La auditoría de la "
             "sección 6.4 cuantifica el efecto: 6 de los 11 falsos negativos brutos son "
             "alertas sobre líneas que no son el defecto.")
bullet(doc, "Independencia de la partición: la evaluación de desarrollo usa val_total, la misma "
            "partición que alimentó la validación del ajuste. El holdout usa el test y se "
            "ejecutó una sola vez, pero el split sigue siendo aleatorio por función y el "
            "dataset no incluye identificador de proyecto. La comparación exacta de hashes "
            "normalizados contra train y validación dio 0 coincidencias; los casi-duplicados "
            "quedan pendientes y la partición agrupada no es posible con los metadatos "
            "actuales.")
bullet(doc, "Falsos negativos bien formados: un SAFE con JSON válido y justificación puede ser "
            "incorrecto. En el holdout D descartó 6 de 65 alertas reales según la etiqueta de "
            "fragmento (9,2 %); la auditoría a nivel de alerta reduce la omisión real a 2 (3,1 %). "
            "La política B403 rescata 4 de las 6 brutas y deja 2 B311, que la auditoría identifica "
            "como ruido. El modo asesor evita que desaparezcan del reporte, pero la calidad "
            "depende de la revisión humana y de la tasa de omisión medida.")
bullet(doc, "Potencia del holdout: con 65 alertas reales, incluso 0 falsos negativos deja el "
            "límite superior del IC95 en 5,6 %. No se puede demostrar estadísticamente un FNR "
            "≤ 5 % con este tamaño. El bootstrap agrupado por archivo es más conservador que "
            "Wilson y también debe citarse.")
bullet(doc, "Sesgo del ajuste: el adaptador se entrena sobre una muestra balanceada de 11.510 "
            "ejemplos; el desempeño sobre la distribución natural del corpus puede ser "
            "distinto. Además, la pérdida solo sobre la respuesta no garantiza que el modelo "
            "generalice ni que no memorice ejemplos.")
bullet(doc, "Cuantización: Q4_K_M reduce recursos, no especializa. Falta medir su efecto en la "
            "calidad de las explicaciones y en la tasa de omisión frente al modelo fusionado "
            "sin cuantizar.")
bullet(doc, "Explicaciones: BERTScore requiere referencias humanas y mide similitud, no "
            "corrección técnica. La rúbrica de la sección 5.4 es la medida principal y aún no "
            "se aplica. El holdout ya mostró que D produce 11 explicaciones y 2 correcciones "
            "únicas para 111 alertas; 91 de 91 VULNERABLE comparten la misma corrección. La "
            "falta de diversidad es un resultado, no un detalle pendiente.")
bullet(doc, "Rendimiento: la corrida de integración del modelo afinado midió 4,8 s por alerta "
            "en la GTX 1650 (43,1 s para 9 alertas); el banco de 10 alertas dio 4,9 s de media "
            "incluyendo la carga del modelo y 4,1 s de mediana. C promedió ~4,3 s por alerta, "
            "salvo una B102 que se trunca y se conserva como SOSPECHOSA. El modelo ocupa 1.115 "
            "MB de VRAM y unos 700 MB de RAM, de modo que en 4 GB cabe una instancia pero no "
            "hay margen cómodo para paralelizar. Para repositorios grandes hacen falta "
            "batching y una política de concurrencia medida.")
bullet(doc, "Prompt injection: el código analizado es entrada no confiable. La prueba con un "
            "comentario malicioso no logró que el modelo marcara SAFE las dos vulnerabilidades "
            "reales, pero es un solo caso: no demuestra resistencia general. Los delimitadores "
            "y el formato JSON reducen el riesgo; la política conservadora evita que un SAFE "
            "elimine la alerta.")
bullet(doc, "Llamadas externas: la promesa de que el código no sale de la máquina debe "
            "reconciliarse con las funciones que descargan repositorios o consultan "
            "dependencias. Hay que documentar qué sale, hacia dónde y con qué control, o "
            "restringir el producto al análisis estrictamente local.")
bullet(doc, "Cobertura OWASP: A03 y A08 concentran más del 95 % de las alertas y seis "
            "categorías no tienen ninguna. El producto no cubre el Top 10 2021; cubre A01, "
            "A02, A03 y A08 con distinto grado de evidencia. El mapeo del dataset tiene 10 "
            "discrepancias de 30 etiquetas y 7 CWE forzados a A03. Presentar la matriz como "
            "certificación de cumplimiento sería falso.")
bullet(doc, "Prompt de evaluación y prompt de producto: las métricas se midieron con el "
            "prompt de eval/run_eval.py, que coincide con el de entrenamiento; la CLI usa un "
            "SYSTEM y un TEMPLATE más detallados en triage.py. C0 y D comparten prompt, así "
            "que la comparación no se ve afectada, pero el FPRR y el FNR reportados no "
            "describen exactamente el comportamiento del producto. Alinear ambos prompts "
            "exige un conjunto nuevo, no el holdout cerrado.")
bullet(doc, "Smoke test con repositorios: 38 alertas por modelo, tres repos y auditoría de "
            "una sola persona. Los 34 SAFE de D fueron correctos en esta muestra, pero no "
            "demuestran que el descarte automático sea seguro. Los reportes completos no se "
            "versionan porque incluyen rutas absolutas y marcas de tiempo.")

# 9. Próximos pasos
h1(doc, "9. Próximos pasos")
bullet(doc, "Cerrar la rúbrica de explicaciones con dos revisores y reportar el kappa junto con "
            "la diversidad de salidas. El holdout ya mostró que D produce 11 explicaciones "
            "únicas para 111 alertas; la rúbrica debe interpretarse a la luz de ese resultado.")
bullet(doc, "Medir casi-duplicados entre entrenamiento y holdout con similitud difusa, porque "
            "la comparación exacta de hashes dio 0 coincidencias pero no descarta variantes. "
            "Documentar la limitación si no se consiguen metadatos de repositorio.")
bullet(doc, "Mantener el holdout cerrado: no se reutiliza para ajustar prompts, hiperparámetros "
            "ni reglas. Cualquier cambio posterior exige un conjunto nuevo, no otra corrida "
            "sobre estas 111 alertas.")
bullet(doc, "Cerrar la auditoría de falsos negativos con una segunda revisión a ciegas de los 12 "
            "casos, para que deje de ser análisis de sensibilidad y pase a ser una medida "
            "principal con acuerdo entre revisores.")
bullet(doc, "Reentrenar con alertas reales de Bandit en el formato de producción, en lugar de "
            "alertas sintéticas y de ejemplos sin alerta. El diagnóstico está en la memoria: el "
            "modelo nunca vio B403 durante el ajuste y el objetivo de entrenamiento es una "
            "plantilla. La validación debe hacerse sobre un conjunto nuevo, no sobre el holdout "
            "cerrado.")
bullet(doc, "Reportar B403 como política obligatoria y B311 como riesgo nuevo. No agregar B311 "
            "con los mismos datos que la sugirieron; validarla en un conjunto independiente.")
bullet(doc, "Explorar una regla B403 basada en el punto de uso —no descartar por el import, "
            "sino por la ausencia de un pickle.load alcanzable—, que requiere análisis de flujo.")
bullet(doc, "Medir el efecto de la cuantización comparando Q4_K_M contra el modelo fusionado en "
            "f16, para separar el efecto del ajuste del de la exportación.")
bullet(doc, "Ampliar la batería de prompt injection con más patrones y documentar la política "
            "de llamadas externas y de descarga de repositorios.")
bullet(doc, "Alinear el prompt de evaluación con el prompt del producto y medir el efecto en un "
            "conjunto nuevo; no reutilizar el holdout. Mientras tanto, declarar la diferencia "
            "en la memoria y no presentar las métricas como si describieran la CLI exacta.")
bullet(doc, "Corregir el frontend para rotular los SAFE como «recomendadas para descarte» y "
            "distinguir SOSPECHOSA; el contrato del reporte ya conserva todas las alertas.")
bullet(doc, "Fijar el modelo base por revisión y verificar los hashes al desplegar; hoy el "
            "entrenamiento carga Qwen/Qwen2.5-Coder-1.5B-Instruct por nombre, sin revisión.")
bullet(doc, "Integrar las secciones de entrenamiento, resultados, discusión y conclusiones en "
            "la memoria final; unificar referencias y preparar el ensayo de demostración y el "
            "paquete de entrega.")

# 10. Conclusión
h1(doc, "10. Conclusiones")
body(doc,
     "El Sprint 7 deja el componente inteligente integrado y medido en dos conjuntos. En "
     "desarrollo, D frente a C0 sube el FPRR de 22,0 % a 48,0 % y el FNR de 2,2 % a 5,5 %. En "
     "el holdout, D crudo obtiene FPRR 30,4 % y FNR 9,2 %; con la política B403, FPRR 19,6 % y "
     "FNR 3,1 % (IC95 0,8–10,5 %). El modelo afinado no es más «inteligente» en abstracto: es "
     "más decidido, y esa decisión es la que hay que controlar. La conclusión más importante no "
     "es técnica sino de producto: el agente se mantiene en modo asesor porque un SAFE "
     "formalmente válido puede ser un falso negativo real, y el holdout no permite demostrar "
     "que el FNR sea ≤ 5 %.")
body(doc,
     "La comparación con Qwen base muestra un intercambio: C0 conserva más alertas y D elimina más "
     "ruido. La auditoría a nivel de alerta reduce la ventaja de C0 en FNR a 1 y 2 alertas y la "
     "deja sin significación; el ahorro de revisión de D, en cambio, se mantiene. Ese resultado se "
     "publica completo porque el objetivo del proyecto no era demostrar superioridad, sino medir un "
     "triage local con un control adecuado. OWASP cumple la misma función: no mejora las "
     "métricas, pero hace visible que el producto cubre A01–A03 y A08 y no el Top 10 completo. "
     "La arquitectura arc42/C4 y el smoke test con repositorios reales cierran la entrega con "
     "evidencia de diseño y de funcionamiento sobre código ajeno, sin cambiar el modo asesor.")
body(doc,
     "El trabajo que resta es de validación y documentación, no de arquitectura: cerrar la "
     "rúbrica de explicaciones —condicionada por el colapso de D a 11 plantillas—, medir "
     "casi-duplicados, integrar la memoria con las cifras del holdout y preparar la defensa. "
     "B403 queda como política obligatoria; B311 se reporta como riesgo nuevo y no se agrega "
     "después de ver el holdout. Con FNR crudo 9,2 % y FNR ajustado 3,1 %, el producto no "
     "habilita descarte automático: el ahorro de revisión es real, la omisión queda concentrada "
     "en B403 y la alerta siempre permanece visible para el analista.")

# 11. Referencias
h1(doc, "11. Referencias")
for ref in [
    "ayshajavd. Code Security Vulnerability Dataset. Hugging Face. "
    "https://huggingface.co/datasets/ayshajavd/code-security-vulnerability-dataset",
    "Bandit. Herramienta de análisis estático de seguridad para Python. "
    "https://bandit.readthedocs.io",
    "Bhandari, G., Naseer, A., y Moonen, L. (2021). CVEfixes: automated collection of "
    "vulnerabilities and their fixes from open-source software. PROMISE 2021. "
    "https://doi.org/10.1145/3475960.3475985",
    "Brown, S. (2018). The C4 Model for Visualising Software Architecture. https://c4model.com",
    "Chen, Y. et al. (2023). DiverseVul: A New Vulnerable Source Code Dataset for Deep "
    "Learning Based Vulnerability Detection. RAID 2023. https://arxiv.org/abs/2304.00409",
    "Dettmers, T. et al. (2023). QLoRA: Efficient Finetuning of Quantized LLMs. "
    "https://arxiv.org/abs/2305.14314",
    "Ding, Y. et al. (2025). Vulnerability Detection with Code Language Models: How Far Are "
    "We? ICSE 2025. https://arxiv.org/abs/2403.18624",
    "Du, X. et al. (2026). Reducing False Positives in Static Bug Detection with LLMs: An "
    "Empirical Study in Industry. ICSE 2026 SEIP. https://doi.org/10.1145/3786583.3786910",
    "Hu, E. J. et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models. "
    "https://arxiv.org/abs/2106.09685",
    "Hui, B. et al. (2024). Qwen2.5-Coder Technical Report. https://arxiv.org/abs/2409.12186",
    "Li, H. et al. (2025). IRIS: LLM-Assisted Static Analysis for Detecting Security "
    "Vulnerabilities. ICLR 2025. https://arxiv.org/abs/2405.17238",
    "llama.cpp. Inferencia de modelos en formato GGUF. https://github.com/ggml-org/llama.cpp",
    "MITRE. Common Weakness Enumeration (CWE). https://cwe.mitre.org",
    "Ollama. Ejecución local de modelos de lenguaje. https://ollama.com",
    "OWASP. (2021). OWASP Top 10:2021. https://owasp.org/Top10/2021/",
    "OWASP. (2025). OWASP Top 10 for LLM Applications 2025. https://genai.owasp.org/llm-top-10/",
    "OWASP. (2025). Application Security Verification Standard 5.0.0. https://asvs.owasp.org/",
    "Siddiq, M. L., y Santos, J. C. (2022). SecurityEval dataset: mining vulnerability "
    "examples to evaluate machine learning-based code generation techniques. MSR4P&S 2022. "
    "https://doi.org/10.1145/3549035.3561184",
    "Starke, G., y Hruschka, P. (2023). arc42: Template for Architecture Communication and "
    "Documentation, versión 9.1. https://arc42.org",
    "Zhang, T. et al. (2020). BERTScore: Evaluating Text Generation with BERT. ICLR 2020. "
    "https://arxiv.org/abs/1904.09675",
]:
    bullet(doc, ref, size=9.2, line=10.8, before=0.6)

doc.save(OUT)
print("guardado:", OUT)
print("parrafos:", len(doc.paragraphs), "| tablas:", len(doc.tables))
