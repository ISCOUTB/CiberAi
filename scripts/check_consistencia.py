"""Verifica que las cifras publicadas coincidan con los resultados crudos.

Comprueba:
- la tabla comparativa de `Avance 5.docx` contra `eval/resultados_*.json`;
- la tabla del holdout de `Avance 5.docx` contra `eval/analisis_holdout.json`;
- las tablas C0/D de `Avance 5.docx` y `docs/ANALISIS_C0_VS_D.md`
  contra `eval/analisis_c0_vs_d.json`;
- la tabla de cobertura de `Avance 5.docx`, `docs/OWASP.md` y
  `docs/BORRADOR_ANEXOS.md` contra `eval/cobertura_owasp.json`;
- las tablas del smoke test de `Avance 5.docx` y `docs/SMOKE_REPOS.md`
  contra `eval/auditoria_smoke_repos.json`;
- la tabla de la auditoría de falsos negativos de `Avance 5.docx` y
  `docs/AUDITORIA_FN.md` contra `eval/analisis_fn.json`;
- la tabla comparativa de `README.md`;
- que no queden marcadores de trabajo sin completar;
- que no reaparezcan cifras obsoletas de la corrida C anterior.

Uso:
    python scripts/check_consistencia.py
Devuelve codigo 1 si encuentra una discrepancia.
"""

import json
import re
import sys
from pathlib import Path

import docx

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

# Orden de presentacion. C0 es el control con el mismo prompt que D; si aun no
# existe su resultado, se omite sin fallar.
CONFIGS = ["A", "B", "C", "C0", "D"]

# Cifras de la corrida C previa (sin num_predict) que no deben reaparecer.
OBSOLETAS = [
    "38,5 %",
    "35 / 91",
    "85 de 91",
    "140 de las 141",
    "11 de 11",
]


def fmt(valor):
    return ("{:.1f} %".format(valor)).replace(".", ",")


def fmt_p(valor):
    return ("{:.4f}".format(valor)).replace(".", ",")


def normalizar(texto):
    return texto.replace("\u2212", "-").replace("\u2013", "-").strip()


def fmt_pts(valor):
    signo = "+" if valor > 0 else ("-" if valor < 0 else "")
    return ("{}{:.1f} pts".format(signo, abs(valor))).replace(".", ",")


def fmt_ic(intervalo):
    return ("{:.1f} a {:.1f}".format(intervalo[0], intervalo[1])).replace(".", ",")


def cargar_json(relativa):
    ruta = ROOT / relativa
    if not ruta.exists():
        raise SystemExit("Falta {}".format(ruta))
    return json.loads(ruta.read_text(encoding="utf-8"))


def celdas(fila):
    return [normalizar(c.text) for c in fila.cells]


def tabla_docx(doc, cabecera):
    esperada = [normalizar(c) for c in cabecera]
    for tabla in doc.tables:
        if celdas(tabla.rows[0]) == esperada:
            return tabla
    return None


def _separador(fila):
    return all(re.fullmatch(r":?-{2,}:?", c) for c in fila)


def filas_md(texto):
    tablas = []
    actual = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea.startswith("|") and linea.endswith("|"):
            fila = [normalizar(c) for c in linea.strip("|").split("|")]
            if _separador(fila):
                continue
            actual.append(fila)
        elif actual:
            tablas.append(actual)
            actual = []
    if actual:
        tablas.append(actual)
    return tablas


def tabla_md(texto, cabecera):
    esperada = [normalizar(c) for c in cabecera]
    for tabla in filas_md(texto):
        if tabla and tabla[0] == esperada:
            return tabla[1:]
    return None


def comparar_filas(origen, filas_doc, esperadas, errores):
    for obtenido, esperado in zip(filas_doc, esperadas):
        if obtenido != esperado:
            errores.append(
                "{}: esperado {} | documento {}".format(origen, esperado, obtenido)
            )
    if len(filas_doc) != len(esperadas):
        errores.append(
            "{}: {} filas (esperadas {})".format(origen, len(filas_doc), len(esperadas))
        )


def cargar_metricas():
    metricas = {}
    for cfg in CONFIGS:
        ruta = ROOT / "eval" / "resultados_{}.json".format(cfg)
        if not ruta.exists():
            if cfg == "C0":
                continue
            raise SystemExit("Falta {}".format(ruta))
        with ruta.open(encoding="utf-8") as fh:
            metricas[cfg] = json.load(fh)["metricas"]
    return metricas


def fila_esperada(metricas):
    filas = {}
    for cfg, m in metricas.items():
        filas[cfg] = [
            str(m["alertas"]),
            fmt(m["FPRR"]),
            fmt(m["FNR"]),
            fmt(m["FOR"]),
            fmt(m["exactitud_cwe"]),
        ]
    return filas


def config_de_celda(texto, configs):
    """Devuelve la configuracion a partir de 'A.', 'C0.' o 'D.'."""
    etiqueta = texto.strip().split(".")[0].strip()
    return etiqueta if etiqueta in configs else None


def revisar_docx(filas, errores):
    ruta = ROOT / "Avance 5.docx"
    if not ruta.exists():
        errores.append("Avance 5.docx no existe")
        return
    doc = docx.Document(str(ruta))
    tabla = None
    for t in doc.tables:
        cabecera = [c.text.strip() for c in t.rows[0].cells]
        if cabecera[:6] == ["Configuración", "Alertas", "FPRR", "FNR", "FOR", "Exactitud CWE"]:
            tabla = t
            break
    if tabla is None:
        errores.append("Avance 5.docx: no se encontro la tabla comparativa")
        return
    vistos = set()
    for fila in tabla.rows[1:]:
        celdas = [c.text.strip() for c in fila.cells]
        cfg = config_de_celda(celdas[0], filas)
        if cfg is None:
            errores.append("Avance 5.docx: fila con configuracion desconocida '{}'".format(celdas[0]))
            continue
        vistos.add(cfg)
        esperado = filas[cfg]
        obtenido = celdas[1:6]
        if esperado != obtenido:
            errores.append(
                "Avance 5.docx {}: esperado {} | documento {}".format(cfg, esperado, obtenido)
            )
        estados = {"A": "Completa", "B": "Piloto", "C": "Completa", "C0": "Completa", "D": "Completa"}
        if celdas[6] != estados[cfg]:
            errores.append(
                "Avance 5.docx {}: estado '{}' (esperado '{}')".format(cfg, celdas[6], estados[cfg])
            )
    faltan = set(filas) - vistos
    if faltan:
        errores.append("Avance 5.docx: faltan configuraciones {}".format(sorted(faltan)))


def revisar_docx_holdout(errores):
    """Compara la tabla del holdout con el resumen derivado de los JSON crudos."""
    ruta_resumen = ROOT / "eval" / "analisis_holdout.json"
    ruta_docx = ROOT / "Avance 5.docx"
    if not ruta_resumen.exists():
        errores.append("Falta eval/analisis_holdout.json")
        return
    if not ruta_docx.exists():
        return
    resumen = json.loads(ruta_resumen.read_text(encoding="utf-8"))
    esperadas = {
        "A": resumen["configuraciones"]["A"],
        "C0": resumen["configuraciones"]["C0"],
        "D": resumen["configuraciones"]["D"],
        "D + política B403": resumen["politica"]["B403"],
        "D + B403 y B311": resumen["politica"]["B403+B311"],
    }

    def resolver(etiqueta):
        if etiqueta in esperadas:
            return etiqueta
        for clave in ("A", "C0", "D"):
            if etiqueta.startswith(clave + "."):
                return clave
        return None

    doc = docx.Document(str(ruta_docx))
    tabla = None
    for t in doc.tables:
        cabecera = [c.text.strip() for c in t.rows[0].cells]
        if cabecera == ["Configuración", "Alertas", "FPRR", "FNR", "FOR", "Precisión", "CWE"]:
            tabla = t
            break
    if tabla is None:
        errores.append("Avance 5.docx: no se encontro la tabla del holdout")
        return

    for fila in tabla.rows[1:]:
        celdas = [c.text.strip() for c in fila.cells]
        etiqueta = celdas[0]
        clave = resolver(etiqueta)
        if clave is None:
            errores.append("Avance 5.docx: fila de holdout desconocida '{}'".format(etiqueta))
            continue
        m = esperadas[clave]
        esperado = [
            str(m["alertas"]),
            fmt(m["FPRR"]),
            fmt(m["FNR"]),
            fmt(m["FOR"]),
            fmt(m["precision"]),
            fmt(m["exactitud_cwe"]),
        ]
        if celdas[1:7] != esperado:
            errores.append(
                "Avance 5.docx holdout {}: esperado {} | documento {}".format(
                    etiqueta, esperado, celdas[1:7]
                )
            )
    if len(tabla.rows) - 1 != len(esperadas):
        errores.append(
            "Avance 5.docx holdout: {} filas (esperadas {})".format(
                len(tabla.rows) - 1, len(esperadas)
            )
        )


def revisar_docx_c0_vs_d(errores):
    """Compara las dos tablas C0/D del docx con el analisis pareado."""
    ruta = ROOT / "Avance 5.docx"
    if not ruta.exists():
        return
    datos = cargar_json("eval/analisis_c0_vs_d.json")["conjuntos"]
    doc = docx.Document(str(ruta))

    tabla = tabla_docx(doc, ["Conjunto", "FPRR C0", "FPRR D", "FNR C0", "FNR D", "McNemar p"])
    if tabla is None:
        errores.append("Avance 5.docx: no se encontro la tabla C0 vs D")
    else:
        filas = 0
        for fila in tabla.rows[1:]:
            c = celdas(fila)
            clave = _clave_conjunto(c[0])
            if clave is None:
                errores.append("Avance 5.docx C0/D: conjunto desconocido '{}'".format(c[0]))
                continue
            filas += 1
            esperado = _fila_c0_d(datos[clave])
            if c[1:] != esperado:
                errores.append(
                    "Avance 5.docx C0/D {}: esperado {} | documento {}".format(
                        clave, esperado, c[1:]
                    )
                )
        if filas != 2:
            errores.append("Avance 5.docx C0/D: {} filas (esperadas 2)".format(filas))

    cabecera = ["Conjunto", "Δ FPRR (D−C0)", "IC95", "Δ FNR (D−C0)", "IC95"]
    tabla = tabla_docx(doc, cabecera)
    if tabla is None:
        errores.append("Avance 5.docx: no se encontro la tabla de diferencias C0/D")
        return
    filas = 0
    for fila in tabla.rows[1:]:
        c = celdas(fila)
        clave = _clave_conjunto(c[0])
        if clave is None:
            errores.append("Avance 5.docx ΔC0/D: conjunto desconocido '{}'".format(c[0]))
            continue
        filas += 1
        esperado = _fila_dif(datos[clave])
        if c[1:] != esperado:
            errores.append(
                "Avance 5.docx ΔC0/D {}: esperado {} | documento {}".format(
                    clave, esperado, c[1:]
                )
            )
    if filas != 2:
        errores.append("Avance 5.docx ΔC0/D: {} filas (esperadas 2)".format(filas))


def revisar_md_c0_vs_d(errores):
    """Compara las tablas del analisis C0/D en Markdown."""
    ruta = ROOT / "docs" / "ANALISIS_C0_VS_D.md"
    if not ruta.exists():
        errores.append("Falta docs/ANALISIS_C0_VS_D.md")
        return
    texto = ruta.read_text(encoding="utf-8")
    datos = cargar_json("eval/analisis_c0_vs_d.json")["conjuntos"]

    cabecera = ["Conjunto", "Configuración", "Alertas", "FPRR", "FNR",
                "Exactitud de la decisión"]
    filas = tabla_md(texto, cabecera)
    if filas is None:
        errores.append("docs/ANALISIS_C0_VS_D.md: falta la tabla global")
    else:
        esperadas = []
        for nombre in ("Desarrollo", "Holdout"):
            clave = _clave_conjunto(nombre)
            for cfg in ("C0", "D"):
                m = datos[clave][cfg]
                esperadas.append([
                    nombre, cfg, str(datos[clave]["alertas"]), fmt(m["FPRR"]), fmt(m["FNR"]),
                    fmt(m["exactitud_decision"]),
                ])
        comparar_filas("docs/ANALISIS_C0_VS_D.md global", filas, esperadas, errores)

    cabecera = ["Conjunto", "Ambos conservan", "Ambos descartan", "Solo D descarta",
                "Solo C0 descarta"]
    filas = tabla_md(texto, cabecera)
    if filas is None:
        errores.append("docs/ANALISIS_C0_VS_D.md: falta la tabla de acuerdo")
    else:
        esperadas = []
        for nombre in ("Desarrollo", "Holdout"):
            esperadas.append([nombre] + _fila_acuerdo(datos[_clave_conjunto(nombre)]))
        comparar_filas("docs/ANALISIS_C0_VS_D.md acuerdo", filas, esperadas, errores)

    cabecera = ["Conjunto", "Δ FPRR (D − C0)", "IC95", "Δ FNR (D − C0)", "IC95"]
    filas = tabla_md(texto, cabecera)
    if filas is None:
        errores.append("docs/ANALISIS_C0_VS_D.md: falta la tabla de diferencias")
    else:
        esperadas = []
        for nombre in ("Desarrollo", "Holdout"):
            esperadas.append([nombre] + _fila_dif(datos[_clave_conjunto(nombre)]))
        comparar_filas("docs/ANALISIS_C0_VS_D.md diferencias", filas, esperadas, errores)

    holdout = datos["holdout"]
    cabecera = ["Configuración", "Explicaciones únicas", "Moda", "Vectores únicos",
                "Correcciones únicas"]
    filas = tabla_md(texto, cabecera)
    if filas is None:
        errores.append("docs/ANALISIS_C0_VS_D.md: falta la tabla de diversidad")
    else:
        esperadas = []
        for cfg in ("C0", "D"):
            d = holdout["diversidad"][cfg]
            esperadas.append([
                cfg,
                str(d["explicacion"]["unicos"]),
                str(d["explicacion"]["moda"]),
                str(d["vector_ataque"]["unicos"]),
                str(d["correccion"]["unicos"]),
            ])
        comparar_filas("docs/ANALISIS_C0_VS_D.md diversidad", filas, esperadas, errores)

    cabecera = ["Conjunto", "C0 copia el CWE del SAST", "D copia el CWE del SAST",
                "Exactitud CWE C0", "Exactitud CWE D"]
    filas = tabla_md(texto, cabecera)
    if filas is None:
        errores.append("docs/ANALISIS_C0_VS_D.md: falta la tabla de CWE")
    else:
        esperadas = []
        for nombre in ("Desarrollo", "Holdout"):
            r = datos[_clave_conjunto(nombre)]
            n = r["alertas"]
            esperadas.append([
                nombre,
                "{} de {}".format(r["cwe_copiado_del_sast"]["C0"], n),
                "{} de {}".format(r["cwe_copiado_del_sast"]["D"], n),
                fmt(r["C0"]["exactitud_cwe"]),
                fmt(r["D"]["exactitud_cwe"]),
            ])
        comparar_filas("docs/ANALISIS_C0_VS_D.md CWE", filas, esperadas, errores)


def _fila_c0_d(r):
    return [
        fmt(r["C0"]["FPRR"]),
        fmt(r["D"]["FPRR"]),
        fmt(r["C0"]["FNR"]),
        fmt(r["D"]["FNR"]),
        fmt_p(r["mcnemar"]["p_exacto_bilateral"]),
    ]


def _fila_dif(r):
    d = r["diferencias"]
    return [
        fmt_pts(d["FPRR"]["puntual_D_menos_C0"]),
        fmt_ic(d["FPRR"]["IC95"]),
        fmt_pts(d["FNR"]["puntual_D_menos_C0"]),
        fmt_ic(d["FNR"]["IC95"]),
    ]


def _fila_acuerdo(r):
    def cuenta(x):
        reales = "{} real".format(x["reales"]) if x["reales"] == 1 else \
            "{} reales".format(x["reales"])
        return "{} ({}, {} FP)".format(x["total"], reales, x["falsos_positivos"])

    return [cuenta(r["acuerdo"][k]) for k in
            ("ambos_conservan", "ambos_descartan", "solo_D_descarta", "solo_C0_descarta")]


def _clave_conjunto(texto):
    t = texto.lower()
    if t.startswith("desarrollo"):
        return "desarrollo"
    if t.startswith("holdout"):
        return "holdout"
    return None


CATEGORIAS_OWASP = ["A01", "A02", "A03", "A04", "A05",
                    "A06", "A07", "A08", "A09", "A10"]


def _fila_owasp(datos, clave):
    por = datos["conjuntos"][clave]["por_categoria"]
    return [str(por.get(cat, 0)) for cat in CATEGORIAS_OWASP] + [
        str(por.get("sin_categoria", 0))]


def _esperado_owasp(datos):
    etiquetas = CATEGORIAS_OWASP + ["—"]
    desarrollo = _fila_owasp(datos, "desarrollo")
    holdout = _fila_owasp(datos, "holdout")
    filas = []
    for i, etiqueta in enumerate(etiquetas):
        nombre = datos["categorias"].get(etiqueta, "Fuera del Top 10 2021")
        filas.append([etiqueta, nombre, desarrollo[i], holdout[i]])
    return filas


def revisar_owasp(errores):
    """Compara la matriz de cobertura del docx y de los borradores."""
    datos = cargar_json("eval/cobertura_owasp.json")
    esperadas = _esperado_owasp(datos)
    vistos = 0

    ruta_docx = ROOT / "Avance 5.docx"
    if ruta_docx.exists():
        doc = docx.Document(str(ruta_docx))
        tabla = tabla_docx(doc, ["Categoría", "Nombre", "Desarrollo (141)",
                                 "Holdout (111)"])
        if tabla is None:
            errores.append("Avance 5.docx: no se encontro la tabla OWASP")
        else:
            filas = [celdas(f) for f in tabla.rows[1:]]
            comparar_filas("Avance 5.docx OWASP", filas, esperadas, errores)
            vistos += 1

    for nombre in ("OWASP.md", "BORRADOR_ANEXOS.md"):
        ruta = ROOT / "docs" / nombre
        if not ruta.exists():
            errores.append("Falta docs/{}".format(nombre))
            continue
        texto = ruta.read_text(encoding="utf-8")
        filas = tabla_md(texto, ["Categoría", "Nombre", "Desarrollo (141)",
                                 "Holdout (111)"])
        if filas is None:
            errores.append("docs/{}: no se encontro la tabla OWASP".format(nombre))
            continue
        comparar_filas("docs/{} OWASP".format(nombre), filas, esperadas, errores)
        vistos += 1

    if vistos != 3:
        errores.append("OWASP: se validaron {} de 3 tablas".format(vistos))

    # Tabla por regla de docs/OWASP.md.
    ruta = ROOT / "docs" / "OWASP.md"
    if not ruta.exists():
        return
    reglas_d = datos["conjuntos"]["desarrollo"]["por_regla"]
    reglas_h = datos["conjuntos"]["holdout"]["por_regla"]
    filas = tabla_md(ruta.read_text(encoding="utf-8"),
                     ["Regla", "CWE del SAST", "Categoría", "Desarrollo", "Holdout"])
    if filas is None:
        errores.append("docs/OWASP.md: no se encontro la tabla por regla")
        return
    for c in filas:
        regla = c[0]
        claves = set(reglas_d.get(regla, {})) | set(reglas_h.get(regla, {}))
        if len(claves) != 1:
            errores.append("docs/OWASP.md: regla '{}' sin categoria unica".format(regla))
            continue
        categoria = claves.pop()
        categoria_doc = "sin categoría" if categoria == "sin_categoria" else categoria
        esperado = [
            regla, c[1], categoria_doc,
            str(reglas_d.get(regla, {}).get(categoria, 0)),
            str(reglas_h.get(regla, {}).get(categoria, 0)),
        ]
        if c != esperado:
            errores.append(
                "docs/OWASP.md regla {}: esperado {} | documento {}".format(
                    regla, esperado, c))


def _totales_smoke(datos, modelo):
    totales = {"total": 0, "conservadas": 0, "recomendadas_descarte": 0,
               "sospechosas": 0, "errores_modelo": 0}
    for repo in datos["repos"].values():
        for clave in totales:
            totales[clave] += repo[modelo][clave]
    return totales


def _conteo_safe(datos, modelo):
    from collections import Counter

    return Counter(s["regla"] for s in datos["safe"] if s["modelo"] == modelo)


def revisar_smoke(errores):
    """Compara las tablas del smoke test del docx y de docs/SMOKE_REPOS.md."""
    datos = cargar_json("eval/auditoria_smoke_repos.json")
    docx_ruta = ROOT / "Avance 5.docx"
    doc = docx.Document(str(docx_ruta)) if docx_ruta.exists() else None

    # Repositorios y numero de alertas.
    cabecera = ["Repositorio", "Etiqueta", "Commit", "Subdirectorio", "Alertas"]
    filas_docx = []
    if doc is not None:
        tabla = tabla_docx(doc, cabecera)
        if tabla is None:
            errores.append("Avance 5.docx: no se encontro la tabla de repositorios")
        else:
            filas_docx = [celdas(f) for f in tabla.rows[1:]]
    ruta_md = ROOT / "docs" / "SMOKE_REPOS.md"
    filas_md_repos = []
    if not ruta_md.exists():
        errores.append("Falta docs/SMOKE_REPOS.md")
    else:
        filas_md_repos = tabla_md(ruta_md.read_text(encoding="utf-8"), cabecera) or []

    for origen, filas in (("Avance 5.docx", filas_docx),
                          ("docs/SMOKE_REPOS.md", filas_md_repos)):
        if not filas:
            continue
        for c in filas:
            repo = next((k for k in datos["repos"] if k in c[0].lower()), None)
            if repo is None:
                errores.append("{}: repositorio desconocido '{}'".format(origen, c[0]))
                continue
            esperado = str(datos["repos"][repo]["base"]["total"])
            if c[4] != esperado:
                errores.append(
                    "{} {}: alertas {} (esperadas {})".format(origen, c[0], c[4], esperado))

    # Totales por modelo.
    cabecera = ["Modelo", "Alertas", "Conservadas", "SAFE", "SOSPECHOSA", "Errores"]
    esperadas = []
    for modelo, etiqueta in (("base", "Base (qwen2.5-coder:1.5b)"),
                             ("d", "D (qwen2.5-coder-triage)")):
        r = _totales_smoke(datos, modelo)
        esperadas.append([
            etiqueta, str(r["total"]), str(r["conservadas"]),
            str(r["recomendadas_descarte"]), str(r["sospechosas"]),
            str(r["errores_modelo"]),
        ])
    if doc is not None:
        tabla = tabla_docx(doc, cabecera)
        if tabla is None:
            errores.append("Avance 5.docx: no se encontro la tabla de totales del smoke")
        else:
            comparar_filas("Avance 5.docx smoke totales",
                           [celdas(f) for f in tabla.rows[1:]], esperadas, errores)

    # Resultados por repositorio en Markdown.
    cabecera = ["Repo", "Modelo", "Alertas", "Conservadas", "SAFE", "SOSPECHOSA",
                "Errores"]
    filas = tabla_md(ruta_md.read_text(encoding="utf-8"), cabecera) if ruta_md.exists() else None
    if not filas:
        errores.append("docs/SMOKE_REPOS.md: no se encontro la tabla de resultados")
    else:
        for c in filas:
            if c[0] not in datos["repos"]:
                errores.append("docs/SMOKE_REPOS.md: repo desconocido '{}'".format(c[0]))
                continue
            modelo = "base" if c[1] == "base" else ("d" if c[1] == "D" else None)
            if modelo is None:
                errores.append("docs/SMOKE_REPOS.md: modelo desconocido '{}'".format(c[1]))
                continue
            r = datos["repos"][c[0]][modelo]
            esperado = [
                c[0], c[1], str(r["total"]), str(r["conservadas"]),
                str(r["recomendadas_descarte"]), str(r["sospechosas"]),
                str(r["errores_modelo"]),
            ]
            if c != esperado:
                errores.append(
                    "docs/SMOKE_REPOS.md resultado {} {}: esperado {} | documento {}".format(
                        c[0], c[1], esperado, c))

    # Auditoria manual: SAFE de D por regla.
    conteo = _conteo_safe(datos, "d")
    cabecera = ["Regla", "SAFE de D", "Qué es", "Veredicto"]
    if doc is not None:
        tabla = tabla_docx(doc, cabecera)
        if tabla is None:
            errores.append("Avance 5.docx: no se encontro la tabla de auditoria")
        else:
            vistos = set()
            for fila in tabla.rows[1:]:
                c = celdas(fila)
                regla = c[0]
                vistos.add(regla)
                if c[1] != str(conteo.get(regla, 0)):
                    errores.append(
                        "Avance 5.docx auditoria {}: {} SAFE (esperadas {})".format(
                            regla, c[1], conteo.get(regla, 0)))
                if c[3] != "Falso positivo correcto":
                    errores.append(
                        "Avance 5.docx auditoria {}: veredicto '{}'".format(regla, c[3]))
            if vistos != set(conteo):
                errores.append(
                    "Avance 5.docx auditoria: reglas {} (esperadas {})".format(
                        sorted(vistos), sorted(conteo)))

    filas = tabla_md(ruta_md.read_text(encoding="utf-8"),
                     ["Regla", "Alertas SAFE", "Qué es", "Veredicto"]) if ruta_md.exists() else None
    if not filas:
        errores.append("docs/SMOKE_REPOS.md: no se encontro la tabla de auditoria")
    else:
        vistos = set()
        for c in filas:
            regla = c[0]
            vistos.add(regla)
            if c[1] != str(conteo.get(regla, 0)):
                errores.append(
                    "docs/SMOKE_REPOS.md auditoria {}: {} SAFE (esperadas {})".format(
                        regla, c[1], conteo.get(regla, 0)))
        if vistos != set(conteo):
            errores.append(
                "docs/SMOKE_REPOS.md auditoria: reglas {} (esperadas {})".format(
                    sorted(vistos), sorted(conteo)))


def _num(valor, decimales=1):
    if valor is None:
        return "n/a"
    return ("{:." + str(decimales) + "f}").format(valor).replace(".", ",")


def _num_pct(valor):
    return "n/a" if valor is None else _num(valor) + " %"


def _num_delta(valor):
    if valor is None:
        return "n/a"
    return ("{:+." + "1f}").format(valor).replace(".", ",")


def _fmt_ic_check(intervalo):
    if intervalo is None:
        return "n/a"
    return normalizar("{}–{} %".format(_num(intervalo[0]), _num(intervalo[1])))


def _filas_banco_metricas(datos):
    base = datos["metricas"]["base"]
    d = datos["metricas"]["d"]
    comp = datos["comparacion"]
    filas = []
    for etiqueta, clave in (
        ("FPRR (FP recomendados para descarte)", "FPRR"),
        ("FNR (reales recomendadas para descarte)", "FNR"),
        ("Exactitud de decisión", "exactitud_decision"),
        ("Precisión de los descartes", "precision_descartes"),
    ):
        filas.append([
            etiqueta, _num_pct(base[clave]), _num_pct(d[clave]),
            _num_delta(comp[clave]["delta_pts"]),
            _num_pct(comp[clave]["relativo_pct"]),
        ])
    return filas


def revisar_banco(errores):
    """Compara las tablas del banco sintético con eval/banco_sintetico.json."""
    datos = cargar_json("eval/banco_sintetico.json")
    ruta = ROOT / "docs" / "BANCO_SINTETICO.md"
    if not ruta.exists():
        errores.append("Falta docs/BANCO_SINTETICO.md")
        return
    texto = ruta.read_text(encoding="utf-8")

    filas = tabla_md(texto, ["Métrica", "Base", "D", "Δ puntos", "Relativo"])
    if filas is None:
        errores.append("docs/BANCO_SINTETICO.md: no se encontro la tabla de metricas")
    else:
        comparar_filas("docs/BANCO_SINTETICO.md metricas",
                       filas, _filas_banco_metricas(datos), errores)

    filas = tabla_md(texto, ["Modelo", "TP", "FN", "TN", "FP", "Inválidas"])
    esperadas = []
    for nombre, clave in (("Base", "base"), ("D", "d")):
        m = datos["metricas"][clave]
        c = m["confusion"]
        esperadas.append([
            nombre, str(c["TP"]), str(c["FN"]), str(c["TN"]), str(c["FP"]),
            str(m["respuestas_invalidas"]),
        ])
    if filas is None:
        errores.append("docs/BANCO_SINTETICO.md: no se encontro la matriz de decision")
    else:
        comparar_filas("docs/BANCO_SINTETICO.md confusion", filas, esperadas, errores)

    filas = tabla_md(texto, ["Métrica", "Base", "IC95 base", "D", "IC95 D"])
    esperadas = []
    for etiqueta, clave in (
        ("FPRR", "FPRR"),
        ("FNR", "FNR"),
        ("Exactitud de decisión", "exactitud_decision"),
        ("Precisión de los descartes", "precision_descartes"),
    ):
        base = datos["metricas"]["base"]
        d = datos["metricas"]["d"]
        esperadas.append([
            etiqueta, _num_pct(base[clave]), _fmt_ic_check(base["IC95_wilson"][clave]),
            _num_pct(d[clave]), _fmt_ic_check(d["IC95_wilson"][clave]),
        ])
    if filas is None:
        errores.append("docs/BANCO_SINTETICO.md: no se encontro la tabla de IC95 Wilson")
    else:
        comparar_filas("docs/BANCO_SINTETICO.md IC95", filas, esperadas, errores)

    filas = tabla_md(texto, ["Regla", "CWE", "OWASP", "Reales", "FP",
                             "SAFE base", "SAFE D"])
    esperadas = [
        [r["regla"], r["cwe"], r["owasp"], str(r["reales"]),
         str(r["falsos_positivos"]), str(r["base_safe"]), str(r["d_safe"])]
        for r in datos["reglas"]
    ]
    if filas is None:
        errores.append("docs/BANCO_SINTETICO.md: no se encontro la tabla por regla")
    else:
        comparar_filas("docs/BANCO_SINTETICO.md reglas", filas, esperadas, errores)

    atajo = datos["atajo_severidad"]
    frase = "{}/{} casos ({} %)".format(
        atajo["coincidencias"], atajo["total"], _num(atajo["porcentaje"]))
    if frase not in texto:
        errores.append(
            "docs/BANCO_SINTETICO.md: falta el atajo de severidad '{}'".format(frase))

    filas = tabla_md(texto, ["ID", "Regla", "Severidad SAST", "Veredicto D"])
    esperadas = [
        [r["id"], r["regla"], r.get("severidad_sast", "?"),
         r["modelos"]["d"]["veredicto"]]
        for r in datos["registros"]
    ]
    if filas is None:
        errores.append("docs/BANCO_SINTETICO.md: no se encontro el detalle por caso")
    else:
        comparar_filas("docs/BANCO_SINTETICO.md atajo", filas, esperadas, errores)

    # README: misma tabla de metricas, con etiquetas ligeramente distintas.
    filas = tabla_md((ROOT / "README.md").read_text(encoding="utf-8"),
                     ["Métrica", "Base", "D", "IC95 de D"])
    esperadas = _filas_banco_metricas(datos)
    ics_d = [_fmt_ic_check(datos["metricas"]["d"]["IC95_wilson"][c])
             for c in ("FPRR", "FNR", "exactitud_decision", "precision_descartes")]
    if filas is None:
        errores.append("README.md: no se encontro la tabla del banco sintetico")
    else:
        if len(filas) != len(esperadas):
            errores.append("README.md banco: {} filas (esperadas {})".format(
                len(filas), len(esperadas)))
        for obtenido, esperado, ic in zip(filas, esperadas, ics_d):
            if obtenido[1] != esperado[1] or obtenido[2] != esperado[2] or obtenido[3] != ic:
                errores.append(
                    "README.md banco '{}': esperado {} {} | documento {}".format(
                        esperado[0], esperado[1:3], ic, obtenido[1:4]))


def revisar_corrida(errores):
    """Compara las tablas de la corrida real con eval/corrida_repos_reales.json."""
    datos = cargar_json("eval/corrida_repos_reales.json")
    ruta = ROOT / "docs" / "CORRIDA_REPOS_REALES.md"
    if not ruta.exists():
        errores.append("Falta docs/CORRIDA_REPOS_REALES.md")
        return
    texto = ruta.read_text(encoding="utf-8")

    filas = tabla_md(texto, ["Repo", "Etiqueta", "Commit", "Subdirectorio", "Alertas"])
    esperadas = [
        ["`{}`".format(nombre), info["tag"], "`{}`".format(info["commit"]),
         "`{}`".format(info["subdir"]), str(info["alertas"])]
        for nombre, info in datos["repos"].items()
    ]
    if filas is None:
        errores.append("docs/CORRIDA_REPOS_REALES.md: no se encontro la tabla de repos")
    else:
        comparar_filas("docs/CORRIDA_REPOS_REALES.md repos", filas, esperadas, errores)

    filas = tabla_md(texto, ["Modelo", "Alertas", "SAFE", "Conservadas",
                             "SOSPECHOSA", "Errores", "% SAFE"])
    esperadas = []
    for nombre, clave in (("Base", "base"), ("D", "d")):
        m = datos["totales"][clave]
        esperadas.append([
            nombre, str(m["alertas"]), str(m["SAFE"]), str(m["conservadas"]),
            str(m["SOSPECHOSA"]), str(m["errores_modelo"]),
            _num_pct(100.0 * m["SAFE"] / m["alertas"]),
        ])
    if filas is None:
        errores.append("docs/CORRIDA_REPOS_REALES.md: no se encontro la tabla de totales")
    else:
        comparar_filas("docs/CORRIDA_REPOS_REALES.md totales", filas, esperadas, errores)

    filas = tabla_md(texto, ["Categoría", "Alertas", "SAFE base", "SAFE D"])
    esperadas = [
        [categoria, str(v["alertas"]), str(v["base_safe"]), str(v["d_safe"])]
        for categoria, v in datos["por_owasp"].items()
    ]
    if filas is None:
        errores.append("docs/CORRIDA_REPOS_REALES.md: no se encontro la tabla OWASP")
    else:
        comparar_filas("docs/CORRIDA_REPOS_REALES.md owasp", filas, esperadas, errores)

    filas = tabla_md(texto, ["Severidad", "Alertas", "SAFE base", "SAFE D", "% SAFE D"])
    esperadas = [
        [sev, str(v["alertas"]), str(v["base_safe"]), str(v["d_safe"]),
         _num_pct(100.0 * v["d_safe"] / v["alertas"])]
        for sev, v in datos["por_severidad"].items()
    ]
    if filas is None:
        errores.append("docs/CORRIDA_REPOS_REALES.md: no se encontro la tabla de severidad")
    else:
        comparar_filas("docs/CORRIDA_REPOS_REALES.md severidad", filas, esperadas, errores)


def revisar_auditoria_fn(errores):
    """Compara las tablas de la auditoría de falsos negativos con su JSON."""
    datos = cargar_json("eval/analisis_fn.json")["conjuntos"]
    nombres = (("desarrollo", "Desarrollo"), ("holdout", "Holdout"))

    cabecera_docx = ["Conjunto", "Modelo", "FN brutos", "Reales", "Ruido",
                     "FNR bruto", "FNR ajustado", "FPRR ajustado", "Precisión"]
    esperadas = []
    for clave, nombre in nombres:
        for cfg in ("C0", "D"):
            m = datos[clave][cfg]
            esperadas.append([
                nombre, cfg, str(m["fn_brutos"]), str(m["fn_reales"]), str(m["fn_ruido"]),
                fmt(m["bruto"]["FNR"]), fmt(m["ajustado"]["FNR"]),
                fmt(m["ajustado"]["FPRR"]), fmt(m["ajustado"]["precision_descarte"]),
            ])

    ruta_docx = ROOT / "Avance 5.docx"
    if ruta_docx.exists():
        doc = docx.Document(str(ruta_docx))
        tabla = tabla_docx(doc, cabecera_docx)
        if tabla is None:
            errores.append("Avance 5.docx: no se encontro la tabla de auditoria de FN")
        else:
            comparar_filas("Avance 5.docx auditoria FN",
                           [celdas(f) for f in tabla.rows[1:]], esperadas, errores)

    ruta_md = ROOT / "docs" / "AUDITORIA_FN.md"
    if not ruta_md.exists():
        errores.append("Falta docs/AUDITORIA_FN.md")
        return
    texto = ruta_md.read_text(encoding="utf-8")

    cabecera_md = ["Conjunto", "Modelo", "FN brutos", "FN reales", "Ruido",
                   "FNR bruto", "FNR ajustado", "FPRR bruto", "FPRR ajustado"]
    filas = tabla_md(texto, cabecera_md)
    if filas is None:
        errores.append("docs/AUDITORIA_FN.md: no se encontro la tabla corregida")
    else:
        esperadas_md = []
        for clave, nombre in nombres:
            for cfg in ("C0", "D"):
                m = datos[clave][cfg]
                esperadas_md.append([
                    nombre, cfg, str(m["fn_brutos"]), str(m["fn_reales"]),
                    str(m["fn_ruido"]), fmt(m["bruto"]["FNR"]),
                    fmt(m["ajustado"]["FNR"]), fmt(m["bruto"]["FPRR"]),
                    fmt(m["ajustado"]["FPRR"]),
                ])
        comparar_filas("docs/AUDITORIA_FN.md corregida", filas, esperadas_md, errores)

    cabecera_pol = ["Conjunto", "Modelo", "FNR", "FPRR", "Precisión del descarte"]
    filas = tabla_md(texto, cabecera_pol)
    if filas is None:
        errores.append("docs/AUDITORIA_FN.md: no se encontro la tabla de política")
    else:
        esperadas_pol = []
        for clave, nombre in nombres:
            for cfg in ("C0", "D"):
                m = datos[clave][cfg]["con_politica_b403"]
                esperadas_pol.append([
                    nombre, cfg, fmt(m["FNR"]), fmt(m["FPRR"]),
                    fmt(m["precision_descarte"]),
                ])
        comparar_filas("docs/AUDITORIA_FN.md política", filas, esperadas_pol, errores)

    ruta_readme = ROOT / "README.md"
    if ruta_readme.exists():
        cabecera_readme = ["Conjunto", "Modelo", "FN brutos", "FN reales", "Ruido",
                           "FNR bruto", "FNR ajustado", "FPRR ajustado"]
        filas = tabla_md(ruta_readme.read_text(encoding="utf-8"), cabecera_readme)
        if filas is None:
            errores.append("README.md: no se encontro la tabla de auditoria de FN")
        else:
            esperadas_readme = []
            for clave, nombre in nombres:
                for cfg in ("C0", "D"):
                    m = datos[clave][cfg]
                    esperadas_readme.append([
                        nombre, cfg, str(m["fn_brutos"]), str(m["fn_reales"]),
                        str(m["fn_ruido"]), fmt(m["bruto"]["FNR"]),
                        fmt(m["ajustado"]["FNR"]), fmt(m["ajustado"]["FPRR"]),
                    ])
            comparar_filas("README.md auditoria FN", filas, esperadas_readme, errores)


def revisar_readme(filas, errores):
    ruta = ROOT / "README.md"
    texto = ruta.read_text(encoding="utf-8")
    for cfg, (alertas, fprr, fnr, forc, cwe) in filas.items():
        # Cada fila debe contener el FPRR y el FNR esperados en la misma linea.
        patron = r"\|[^|\n]*\|[^\n]*" + re.escape(fprr) + r"[^\n]*" + re.escape(fnr)
        if not re.search(patron, texto):
            errores.append(
                "README.md: falta la fila de {} con FPRR {} y FNR {}".format(cfg, fprr, fnr)
            )


def revisar_marcadores(errores):
    rutas = [ROOT / "README.md", ROOT / "docs"]
    for ruta in rutas:
        archivos = [ruta] if ruta.is_file() else list(ruta.glob("*.md"))
        for archivo in archivos:
            texto = archivo.read_text(encoding="utf-8")
            for marcador in ["Por completar", "Por registrar", "Por medir"]:
                if marcador in texto:
                    errores.append("{}: contiene '{}'".format(archivo.name, marcador))


def revisar_obsoletas(errores):
    archivos = [ROOT / "README.md", ROOT / "AVANCE5_PENDIENTES.md"]
    archivos += list((ROOT / "docs").glob("*.md"))
    archivos += list((ROOT / "scripts").glob("build_*.py"))
    for archivo in archivos:
        texto = archivo.read_text(encoding="utf-8")
        for cifra in OBSOLETAS:
            if cifra in texto:
                errores.append("{}: cifra obsoleta '{}'".format(archivo.name, cifra))


def main():
    metricas = cargar_metricas()
    filas = fila_esperada(metricas)
    errores = []
    revisar_docx(filas, errores)
    revisar_docx_holdout(errores)
    revisar_docx_c0_vs_d(errores)
    revisar_md_c0_vs_d(errores)
    revisar_owasp(errores)
    revisar_smoke(errores)
    revisar_banco(errores)
    revisar_corrida(errores)
    revisar_auditoria_fn(errores)
    revisar_readme(filas, errores)
    revisar_marcadores(errores)
    revisar_obsoletas(errores)

    for cfg, m in metricas.items():
        print(
            "{}: n={} FPRR={} FNR={} FOR={} CWE={}".format(
                cfg,
                m["alertas"],
                fmt(m["FPRR"]),
                fmt(m["FNR"]),
                fmt(m["FOR"]),
                fmt(m["exactitud_cwe"]),
            )
        )
    if errores:
        print("\nDiscrepancias:")
        for error in errores:
            print(" -", error)
        return 1
    print("\nConsistencia OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
