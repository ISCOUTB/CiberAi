"""Verifica que las cifras publicadas coincidan con los resultados crudos.

Comprueba:
- la tabla comparativa de `Avance 5.docx` contra `eval/resultados_*.json`;
- la tabla del holdout de `Avance 5.docx` contra `eval/analisis_holdout.json`;
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
