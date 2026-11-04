from pathlib import Path

import docx
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(r"C:\Games\u\proyecto ing\Avance 4.docx")
BODY_FONT = "DejaVu Sans"
HEAD_FONT = "Carlito"


def set_font(run, name=BODY_FONT, size=9.5, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)


def para(doc, text="", size=9.5, bold=False, align=None, font=BODY_FONT,
         before=0, after=0, line=1.18, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if align is not None:
        p.alignment = align
    if text:
        run = p.add_run(text)
        set_font(run, font, size, bold, color)
    return p


def h1(doc, text):
    p = para(doc, text, size=18, bold=True, font=HEAD_FONT, before=18, after=4, line=1.0)
    p.paragraph_format.keep_with_next = True
    return p


def h2(doc, text):
    p = para(doc, text, size=13, bold=True, font=HEAD_FONT, before=12, after=3, line=1.0)
    p.paragraph_format.keep_with_next = True
    return p


def body(doc, text, keep=False):
    p = para(doc, text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=6)
    p.paragraph_format.keep_with_next = keep
    return p


def bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    set_font(run, BODY_FONT, 9.5)
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


def code(doc, text, keep=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_with_next = keep
    run = p.add_run(text)
    set_font(run, "Consolas", 8)
    shade(p)
    return p


def table(doc, headers, rows, widths=None, size=8.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    trPr = t.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(h)
        set_font(run, BODY_FONT, size, bold=True)
        shade(cell, "E7E6E6")
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run(str(value))
            set_font(run, BODY_FONT, size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


doc = docx.Document()
section = doc.sections[0]
section.page_width = Cm(21.59)
section.page_height = Cm(27.94)
section.left_margin = Cm(1.71)
section.right_margin = Cm(1.82)
section.top_margin = Cm(0.64)
section.bottom_margin = Cm(0.64)

normal = doc.styles["Normal"]
normal.font.name = BODY_FONT
normal.font.size = Pt(9.5)

para(doc, "AVANCE 4  |  ARQUITECTURA, INTEGRACIÓN Y EVALUACIÓN", size=7.5, bold=True,
     align=WD_ALIGN_PARAGRAPH.RIGHT)
para(doc, "AVANCE 4", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, before=66)
para(doc, "Arquitectura, integración y evaluación del agente", size=29, bold=True,
     font=HEAD_FONT, align=WD_ALIGN_PARAGRAPH.CENTER, before=11, line=1.0)
para(doc, "Agente inteligente para la revisión de seguridad de código fuente", size=14, bold=True,
     before=12)
para(doc, "Arquitectura · Modelo de datos · Evaluación A/B/C del triage", size=10,
     align=WD_ALIGN_PARAGRAPH.CENTER, before=30)
para(doc, "Periodo: 23 – 26 de octubre de 2026  |  Actualización: 26 de octubre de 2026 (Sprint 4)",
     size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, before=28)
para(doc, "Integrantes: Santiago Reyes, Marien Daniela, Luis Patron, William Cuello  |  "
          "Asignatura: Proyecto de Ingeniería", size=9, align=WD_ALIGN_PARAGRAPH.CENTER, before=4)
doc.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)

h1(doc, "1. Resumen del avance")
body(doc,
     "Este avance consolida el agente de triage como una herramienta ejecutable. La CLI implementada "
     "ejecuta Bandit sobre un repositorio, normaliza cada alerta a un modelo de datos común, exporta "
     "SARIF 2.1.0, deduplica hallazgos, extrae la función contenedora mediante el árbol de sintaxis "
     "abstracta, consulta a un modelo local servido por Ollama y aplica una política conservadora de "
     "decisión: solo se descarta una alerta cuando el modelo responde SAFE con formato válido; ante "
     "cualquier error o respuesta inválida, la alerta se conserva como SOSPECHOSA.")
body(doc,
     "La tubería quedó verificada con diez pruebas unitarias y dos corridas de extremo a extremo sobre "
     "un repositorio de muestra: una sin modelo (9 alertas conservadas) y otra con Qwen2.5-Coder-1.5B "
     "(9 respuestas válidas, 0 errores). Para la evaluación se construyó un conjunto de 141 alertas "
     "reales de Bandit sobre las 298 funciones Python de la partición de validación: 91 corresponden a "
     "funciones vulnerables y 50 a funciones seguras (falsos positivos del SAST). La configuración A "
     "(solo SAST) conserva el 100 % de las alertas, por lo que no reduce falsos positivos y acierta el "
     "CWE en el 45,1 % de las alertas reales. La configuración B se ejecutó solo como piloto de cinco "
     "alertas por límite de tiempo del modelo local; la corrida completa de B y C queda como tarea de "
     "cierre del Sprint 4 en el Sprint 5.")
body(doc,
     "El resultado principal es que la arquitectura y el contrato de datos ya están cerrados y son "
     "reproducibles; la medición definitiva de FPRR, FOR y exactitud CWE requiere completar las "
     "corridas B y C sobre las 141 alertas.")

h1(doc, "2. Arquitectura del agente")
body(doc,
     "El agente se organiza en una tubería lineal con un único punto de decisión final. Cada etapa es "
     "un módulo independiente y testeable; el orquestador solo compone las etapas y decide el código de "
     "salida. La figura lógica del flujo es:")
code(doc, "repositorio -> Bandit (JSON) -> normalización -> deduplicación\n"
          "            -> contexto (AST) -> prompt -> Ollama (Qwen) -> validación\n"
          "            -> política conservadora -> reporte.json + hallazgos.sarif + consola", keep=True)
table(doc,
      ["Componente", "Archivo", "Responsabilidad"],
      [["Orquestador / CLI", "cli.py", "Valida argumentos, ejecuta el pipeline, escribe salidas y fija el código de salida."],
       ["Ejecutor SAST", "sast/bandit_runner.py", "Invoca Bandit con salida JSON y normaliza cada alerta a Finding."],
       ["Exportador SARIF", "sast/sarif.py", "Genera SARIF 2.1.0 con reglas, niveles y ubicaciones físicas."],
       ["Contexto", "context.py", "Localiza la función o clase contenedora con ast; si falla, usa ±20 líneas."],
       ["Deduplicación", "dedup.py", "Calcula fingerprint SHA-256 y elimina duplicados por (CWE, archivo, función, línea)."],
       ["Cliente LLM", "llm/ollama_client.py", "POST a /api/generate con format=json y temperatura 0."],
       ["Triage", "triage.py", "Construye el prompt, parsea el JSON, valida el veredicto y aplica la política conservadora."],
       ["Reportes", "report.py", "Resumen agregado, reporte JSON y tabla de consola."],
       ["Modelos", "models.py", "Finding, ToolRun, Scan y TriageResult; serialización y marcas de tiempo UTC."]],
      widths=[3.4, 4.2, 10.4])

h2(doc, "2.1 Contrato de decisión")
body(doc,
     "El veredicto del modelo se acepta solo si el JSON contiene un veredicto VULNERABLE o SAFE. Un "
     "veredicto SAFE descarta la alerta únicamente con justificación; un veredicto inválido, un JSON "
     "malformado, un tiempo de espera agotado o un servidor no disponible producen SOSPECHOSA y la "
     "alerta se conserva. De este modo, un fallo del modelo nunca elimina una vulnerabilidad real: el "
     "peor caso es una alerta adicional para revisión humana.")

h2(doc, "2.2 Interfaz de línea de comandos")
code(doc, "python agente/run.py scan <ruta> [--out DIR] [--model NOMBRE]\n"
          "       [--ollama-url URL] [--no-llm] [--max-alerts N] [--quiet]")
body(doc,
     "La opción --no-llm ejecuta solo la fase SAST y conserva todas las alertas como SOSPECHOSA; sirve "
     "para validar el pipeline sin modelo. --model permite cambiar entre el modelo base y el modelo "
     "afinado en formato GGUF sin modificar el código, que es el requisito de despliegue del Sprint 5.")

h1(doc, "3. Modelo de datos consolidado")
body(doc,
     "Todas las etapas comparten las mismas estructuras, de modo que el JSON intermedio, el reporte y "
     "el SARIF son proyecciones del mismo objeto. Los campos principales son:", keep=True)
table(doc,
      ["Estructura", "Campos"],
      [["Finding", "finding_id, rule_id, cwe, severity, confidence, message, file, line, end_line, "
                   "code, context, function, fingerprint, triage"],
       ["TriageResult", "veredicto (VULNERABLE | SAFE | SOSPECHOSA), cwe, severidad, explicacion, "
                        "vector_ataque, correccion, valido"],
       ["ToolRun", "tool, version, command, started_at, finished_at, findings_count, findings"],
       ["Scan", "scan_id, target, started_at, finished_at, tool_runs, findings"]],
      widths=[3.4, 14.6])
body(doc,
     "El finding_id es determinista (SHA-256 truncado de regla, CWE, archivo, función y línea), lo que "
     "permite comparar corridas y deduplicar entre herramientas. Un registro de salida tiene esta forma:")
code(doc, '{\n'
          '  "finding_id": "7be2ec4686d0006f", "rule_id": "B608", "cwe": "CWE-89",\n'
          '  "severity": "media", "file": "vuln.py", "line": 15, "function": "buscar",\n'
          '  "triage": {"veredicto": "VULNERABLE", "cwe": "CWE-89", "severidad": "Alta",\n'
          '             "explicacion": "...", "vector_ataque": "...", "correccion": "..."}\n'
          '}')

h1(doc, "4. Evidencias de integración")
body(doc,
     "Las siguientes evidencias provienen de corridas ejecutadas sobre agente/examples/sample_repo, un "
     "archivo con contraseña embebida, SQL por formato de cadena, MD5, pickle, subprocess con shell y "
     "assert:", keep=True)
table(doc,
      ["Evidencia", "Resultado"],
      [["Pruebas unitarias (contexto, dedup, SARIF, parseo, política, Bandit)", "10 de 10 correctas"],
       ["Corrida sin modelo (--no-llm)", "9 alertas, 9 conservadas, 0 descartadas, 9 SOSPECHOSA"],
       ["Corrida con Qwen2.5-Coder-1.5B", "9 alertas, 9 respuestas válidas, 0 errores de modelo"],
       ["Salida SARIF", "Versión 2.1.0, 9 resultados, 8 reglas"],
       ["Salida JSON", "1 tool_run, 9 findings, resumen por CWE y severidad"],
       ["Latencia observada", "≈14 s por alerta en CPU, incluida la carga inicial del modelo"]],
      widths=[9.0, 9.0])
body(doc,
     "La corrida con el modelo base clasificó las nueve alertas como VULNERABLE, incluidas las "
     "advertencias de importación de pickle y subprocess. Es el comportamiento esperado de un modelo "
     "sin ajuste: responde con formato correcto pero no discrimina falsos positivos. Este resultado es "
     "la línea base cualitativa que el fine-tuning debe mejorar, y motivó la inclusión de ejemplos SAFE "
     "en la configuración C.")

h1(doc, "5. Metodología de evaluación")
h2(doc, "5.1 Conjunto de evaluación")
body(doc,
     "Como Bandit solo analiza Python y el corpus está dominado por C, la evaluación se restringió a la "
     "partición de validación en Python. Se escribieron las 298 funciones en archivos temporales, se "
     "ejecutó Bandit y se conservaron las 141 alertas resultantes. La verdad de referencia es la "
     "etiqueta del dataset a nivel de función: una alerta es real si la función está marcada como "
     "vulnerable y es falso positivo si está marcada como segura. La concordancia de clase entre el CWE "
     "de Bandit y el CWE del dataset se mide por separado.", keep=True)
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
     "subprocess y pickle (B404 y B403), que Bandit reporta aunque no exista uso inseguro. Es una "
     "fuente natural de falsos positivos y un caso representativo para el triage.")

h2(doc, "5.2 Configuraciones y métricas")
body(doc,
     "Se comparan cuatro configuraciones: A, solo SAST, que conserva todas las alertas; B, modelo "
     "cero-shot sin contexto del SAST; C, modelo con contexto del SAST y tres ejemplos guía "
     "(few-shot); y D, modelo afinado, que se incorpora en el Sprint 5. Las métricas se definen así:")
bullet(doc, "FPRR (falsos positivos reducidos): porcentaje de alertas falsas que el agente descarta. "
            "Mide el beneficio del triage.")
bullet(doc, "FOR (falsos omitidos reales): porcentaje de alertas reales que el agente descarta. Mide el "
            "riesgo de perder vulnerabilidades y debe mantenerse en cero o cerca de cero.")
bullet(doc, "Exactitud CWE: porcentaje de alertas reales conservadas cuyo CWE predicho coincide con el "
            "CWE del dataset, admitiendo equivalencias entre familias (por ejemplo, CWE-259 y CWE-798).")
body(doc,
     "El protocolo es determinista: temperatura 0, semilla y prompt fijos, y el mismo orden de alertas "
     "para todas las configuraciones. Los resultados se guardan por alerta para permitir auditoría.")

h1(doc, "6. Resultados")
table(doc,
      ["Configuración", "Alertas", "FPRR", "FOR", "Exactitud CWE", "Estado"],
      [["A. Solo SAST", "141", "0,0 %", "0,0 %", "45,1 %", "Completa"],
       ["B. Cero-shot (piloto)", "5", "100,0 %", "0,0 %", "0,0 %", "Piloto"],
       ["C. Contexto + few-shot", "141", "—", "—", "—", "Pendiente"],
       ["D. Modelo afinado", "141", "—", "—", "—", "Sprint 5"]],
      widths=[4.6, 2.2, 2.4, 2.2, 3.2, 3.4])
body(doc,
     "La configuración A fija el punto de partida: al no descartar nada, su FPRR y su FOR son cero por "
     "construcción y su exactitud CWE refleja la del SAST (45,1 %). En el piloto B, el modelo descartó "
     "las dos alertas falsas del lote (FPRR 100 %) y conservó las tres reales (FOR 0 %), pero no acertó "
     "el CWE en ninguna: predijo CWE-259 y CWE-059 para alertas de pickle y CWE-790 para una de "
     "subprocess. El tamaño de cinco alertas no permite inferencia estadística; solo confirma que el "
     "modelo responde, descarta falsos positivos evidentes y falla en la clasificación fina.")
body(doc,
     "La corrida completa de B y C sobre las 141 alertas quedó programada y reproducible "
     "(eval/run_eval.py), pero no se completó dentro de la ventana de este avance: el modelo local "
     "tarda alrededor de catorce segundos por alerta en CPU, de modo que cada configuración requiere "
     "cerca de treinta y tres minutos. Se decidió no presentar cifras parciales como definitivas. La "
     "tabla se cerrará en la primera semana del Sprint 5, antes de iniciar el ajuste fino, para que la "
     "comparación D use exactamente el mismo conjunto.")

h1(doc, "7. Limitaciones")
bullet(doc, "Cobertura de lenguaje: Bandit solo analiza Python y el 94,1 % del corpus es C. La "
            "evaluación cubre 298 funciones y 141 alertas, suficiente para la línea base pero no para "
            "generalizar al corpus completo.")
bullet(doc, "Verdad de referencia a nivel de función: el dataset no incluye archivo ni línea, por lo "
            "que una advertencia de importación sobre una función vulnerable cuenta como alerta real "
            "aunque la línea señalada no sea el defecto. Esto favorece al SAST y explica parte del "
            "45,1 % de concordancia CWE.")
bullet(doc, "Tamaño y alcance del piloto: B se midió sobre cinco alertas; no hay intervalos de "
            "confianza ni análisis por regla. C y D aún no tienen resultados.")
bullet(doc, "Rendimiento: catorce segundos por alerta en CPU no es viable para repositorios grandes; "
            "se evaluará batching, paralelismo y una versión cuantizada del modelo.")
bullet(doc, "Demostración en vivo: los ensayos de demo del Sprint 4 no se realizaron; se reprograman "
            "para el Sprint 6, cuando exista el modelo afinado y el flujo de extremo a extremo estable.")

h1(doc, "8. Próximos pasos")
bullet(doc, "Completar las corridas B y C sobre las 141 alertas y publicar la tabla definitiva A/B/C.")
bullet(doc, "Ajustar Qwen2.5-Coder-1.5B con QLoRA sobre train_80 (101.878 ejemplos, ponderación de "
            "clases por el 6,1 % de vulnerables detectado en el Sprint 2) y validar sobre val_total.")
bullet(doc, "Exportar el adaptador a GGUF y evaluarlo como configuración D con el mismo protocolo.")
bullet(doc, "Medir latencia y consumo de memoria por configuración y definir el modo de despliegue.")
bullet(doc, "Preparar el guion de demo en vivo para el Sprint 6 y el paquete de entrega.")

h1(doc, "9. Conclusión")
body(doc,
     "El Sprint 4 deja cerrada la arquitectura del agente, el modelo de datos y la integración con el "
     "SAST y con Ollama, con evidencia reproducible de funcionamiento y una política de decisión que "
     "prioriza no perder vulnerabilidades. La evaluación cuantitativa queda parcial: A está medida "
     "sobre 141 alertas y B solo como piloto, mientras que C y D se completarán en el Sprint 5. El "
     "hallazgo más útil para el proyecto es que el modelo base responde con formato válido pero no "
     "discrimina bien la clase de vulnerabilidad, lo que confirma que el ajuste fino es necesario y "
     "que la métrica de exactitud CWE debe seguirse con el mismo rigor que FPRR y FOR.")

doc.save(OUT)
print("guardado:", OUT)
print("parrafos:", len(doc.paragraphs), "| tablas:", len(doc.tables))
