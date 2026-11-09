"""Banco de casos sinteticos etiquetados a nivel de alerta.

Cada archivo de ``eval/sinteticas/casos`` contiene una unica alerta de Bandit
cuya verdad se declara en ``eval/sinteticas/casos.jsonl``: ``real`` si la alerta
corresponde a una vulnerabilidad explotable en el contexto del caso, o
``falso_positivo`` si la construccion es segura pese a que la regla la marque.

El banco usa el camino real del producto: ``run_bandit`` construye el hallazgo,
``triage.build_prompt`` y ``triage.SYSTEM`` arman el prompt, y
``triage.parse_response`` aplica la politica por defecto (``B403`` nunca se
recomienda para descarte). Los dos modelos ven exactamente el mismo prompt y la
misma temperatura.

No toca el holdout: los casos son nuevos y no salen de ``eval/holdout_set.jsonl``.

Escribe:
    eval/banco_sintetico.json
    docs/BANCO_SINTETICO.md

Uso:
    python eval/banco_sintetico.py --validar
    python eval/banco_sintetico.py
"""

import argparse
import json
import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
CASOS_DIR = ROOT / "eval" / "sinteticas" / "casos"
METADATA = ROOT / "eval" / "sinteticas" / "casos.jsonl"

sys.path.insert(0, str(ROOT / "agente" / "src"))

from agente_seguridad.dedup import deduplicate, with_ids  # noqa: E402
from agente_seguridad.llm.ollama_client import OllamaClient, OllamaError  # noqa: E402
from agente_seguridad.owasp import etiqueta as owasp_etiqueta  # noqa: E402
from agente_seguridad.sast.bandit_runner import run_bandit  # noqa: E402
from agente_seguridad.triage import SYSTEM, build_prompt, parse_response  # noqa: E402


def cargar_casos():
    casos = []
    with METADATA.open(encoding="utf-8") as fh:
        for numero, linea in enumerate(fh, 1):
            linea = linea.strip()
            if not linea:
                continue
            caso = json.loads(linea)
            caso["owasp"] = owasp_etiqueta(caso["cwe"])
            ruta = CASOS_DIR / caso["archivo"]
            if not ruta.exists():
                raise SystemExit("Caso {}: falta {}".format(caso["id"], ruta))
            casos.append(caso)
    return casos


def validar_modelos(url, modelos):
    try:
        resp = requests.get(url.rstrip("/") + "/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit("Ollama no responde en {}: {}".format(url, exc))
    disponibles = {m.get("name", "") for m in resp.json().get("models", [])}
    faltan = []
    for modelo in modelos:
        if not any(nombre == modelo or nombre.split(":")[0] == modelo for nombre in disponibles):
            faltan.append(modelo)
    if faltan:
        raise SystemExit("Modelos no disponibles en Ollama: {}. Hay: {}".format(
            ", ".join(faltan), ", ".join(sorted(disponibles))))


def emparejar(casos):
    """Ejecuta Bandit una vez y empareja cada caso con su alerta esperada."""
    findings = with_ids(deduplicate(run_bandit(CASOS_DIR)))
    por_archivo = {}
    for f in findings:
        por_archivo.setdefault(Path(f.file).name, []).append(f)

    pares = []
    errores = []
    ignoradas = Counter()
    for caso in casos:
        encontrados = por_archivo.get(caso["archivo"], [])
        esperados = [f for f in encontrados if f.rule_id == caso["regla"]]
        for f in encontrados:
            if f.rule_id != caso["regla"]:
                ignoradas["{} en {}".format(f.rule_id, caso["id"])] += 1
        if len(esperados) != 1:
            errores.append("{}: se esperaba 1 alerta {} y hay {}".format(
                caso["id"], caso["regla"], len(esperados)))
            continue
        finding = esperados[0]
        if finding.cwe != caso["cwe"]:
            errores.append("{}: CWE esperado {} y Bandit reporta {}".format(
                caso["id"], caso["cwe"], finding.cwe))
            continue
        pares.append((caso, finding))
    return pares, errores, ignoradas


def wilson(k, n, z=1.96):
    """Intervalo de Wilson para una proporcion, en porcentaje (mismo metodo que holdout)."""
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    media = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(100.0 * max(0.0, centro - media), 1),
            round(100.0 * min(1.0, centro + media), 1)]


def metricas(registros, clave):
    reales = [r for r in registros if r["etiqueta"] == "real"]
    fps = [r for r in registros if r["etiqueta"] == "falso_positivo"]
    decisiones = [r["modelos"][clave]["veredicto"] for r in registros]
    real_desc = sum(1 for r in reales if r["modelos"][clave]["veredicto"] == "SAFE")
    fp_desc = sum(1 for r in fps if r["modelos"][clave]["veredicto"] == "SAFE")
    real_keep = len(reales) - real_desc
    fp_keep = len(fps) - fp_desc
    kept = len(registros) - decisiones.count("SAFE")
    return {
        "alertas": len(registros),
        "reales": len(reales),
        "falsos_positivos": len(fps),
        "confusion": {"TP": real_keep, "FN": real_desc, "TN": fp_desc, "FP": fp_keep},
        "conservadas": kept,
        "recomendadas_descarte": decisiones.count("SAFE"),
        "sospechosas": decisiones.count("SOSPECHOSA"),
        "FPRR": round(100.0 * fp_desc / len(fps), 1) if fps else 0.0,
        "FNR": round(100.0 * real_desc / len(reales), 1) if reales else 0.0,
        "exactitud_decision": round(100.0 * (real_keep + fp_desc) / len(registros), 1),
        "precision_descartes": round(100.0 * fp_desc / (fp_desc + real_desc), 1)
        if (fp_desc + real_desc) else None,
        "respuestas_invalidas": sum(1 for r in registros if not r["modelos"][clave]["valido"]),
        "IC95_wilson": {
            "FPRR": wilson(fp_desc, len(fps)),
            "FNR": wilson(real_desc, len(reales)),
            "exactitud_decision": wilson(real_keep + fp_desc, len(registros)),
            "precision_descartes": wilson(fp_desc, fp_desc + real_desc),
        },
    }


def comparar(base, d):
    def delta(a, b):
        if a is None or b is None:
            return {"base": a, "d": b, "delta_pts": None, "relativo_pct": None}
        return {
            "base": a,
            "d": b,
            "delta_pts": round(b - a, 1),
            "relativo_pct": round(100.0 * (b - a) / a, 1) if a else None,
        }
    return {
        "FPRR": delta(base["FPRR"], d["FPRR"]),
        "FNR": delta(base["FNR"], d["FNR"]),
        "exactitud_decision": delta(base["exactitud_decision"], d["exactitud_decision"]),
        "precision_descartes": delta(base["precision_descartes"], d["precision_descartes"]),
    }


def por_regla(registros):
    agrupado = {}
    for r in registros:
        clave = r["regla"]
        fila = agrupado.setdefault(clave, {
            "regla": clave, "cwe": r["cwe"], "owasp": r["owasp"],
            "reales": 0, "falsos_positivos": 0, "base_safe": 0, "d_safe": 0,
        })
        if r["etiqueta"] == "real":
            fila["reales"] += 1
        else:
            fila["falsos_positivos"] += 1
        fila["base_safe"] += r["modelos"]["base"]["veredicto"] == "SAFE"
        fila["d_safe"] += r["modelos"]["d"]["veredicto"] == "SAFE"
    return [agrupado[k] for k in sorted(agrupado)]


def fmt(valor):
    return ("{:.1f}".format(valor)).replace(".", ",")


def fmt_delta(valor):
    if valor is None:
        return "n/a"
    return ("{:+}".format(valor)).replace(".", ",")


def fmt_pct(valor, sufijo=" %"):
    return "n/a" if valor is None else fmt(valor) + sufijo


def fmt_ic(intervalo):
    if intervalo is None:
        return "n/a"
    return "{}–{} %".format(fmt(intervalo[0]), fmt(intervalo[1]))


def analisis_atajo(registros):
    """Comprueba si D decide solo por la severidad que reporta Bandit."""
    aciertos = 0
    discrepancias = []
    for r in registros:
        prediccion = "SAFE" if r.get("severidad_sast") == "baja" else "VULNERABLE"
        real = r["modelos"]["d"]["veredicto"]
        if real == prediccion:
            aciertos += 1
        else:
            discrepancias.append({
                "id": r["id"], "regla": r["regla"],
                "severidad_sast": r.get("severidad_sast"), "d": real,
            })
    return {
        "regla": "SAFE si la severidad del SAST es baja; VULNERABLE en otro caso",
        "coincidencias": aciertos,
        "total": len(registros),
        "porcentaje": round(100.0 * aciertos / len(registros), 1) if registros else 0.0,
        "discrepancias": discrepancias,
    }


def markdown(datos):
    base = datos["metricas"]["base"]
    d = datos["metricas"]["d"]
    comp = datos["comparacion"]
    lineas = [
        "# Banco de casos sintéticos etiquetados",
        "",
        "Generado por `eval/banco_sintetico.py` el {}.".format(datos["fecha"]),
        "",
        "## 1. Qué mide",
        "",
        "El banco contiene **{} alertas de Bandit**: {} reales y {} falsos positivos. "
        "Cada caso es un archivo `.py` con una sola alerta, y la etiqueta se declara a "
        "nivel de alerta en `eval/sinteticas/casos.jsonl` con su justificación. No se "
        "usa el holdout: los casos son nuevos y no participaron en el ajuste fino.".format(
            datos["alertas"], base["reales"], base["falsos_positivos"]),
        "",
        "Los dos modelos reciben el prompt del producto (`triage.build_prompt` y "
        "`triage.SYSTEM`), la misma temperatura (0) y el mismo límite de generación. "
        "La política `B403` nunca se recomienda para descarte sigue activa. Por eso "
        "las cifras miden el producto, no el arnés `prompt_d` de la evaluación C0/D.",
        "",
        "## 2. Casos por regla",
        "",
        "| Regla | CWE | OWASP | Reales | FP | SAFE base | SAFE D |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for fila in datos["reglas"]:
        lineas.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            fila["regla"], fila["cwe"], fila["owasp"], fila["reales"],
            fila["falsos_positivos"], fila["base_safe"], fila["d_safe"]))
    lineas += [
        "",
        "## 3. Resultados",
        "",
        "| Métrica | Base | D | Δ puntos | Relativo |",
        "|---|---:|---:|---:|---:|",
        "| FPRR (FP recomendados para descarte) | {} | {} | {} | {} |".format(
            fmt_pct(base["FPRR"]), fmt_pct(d["FPRR"]),
            fmt_delta(comp["FPRR"]["delta_pts"]),
            fmt_pct(comp["FPRR"]["relativo_pct"])),
        "| FNR (reales recomendadas para descarte) | {} | {} | {} | {} |".format(
            fmt_pct(base["FNR"]), fmt_pct(d["FNR"]),
            fmt_delta(comp["FNR"]["delta_pts"]),
            fmt_pct(comp["FNR"]["relativo_pct"])),
        "| Exactitud de decisión | {} | {} | {} | {} |".format(
            fmt_pct(base["exactitud_decision"]), fmt_pct(d["exactitud_decision"]),
            fmt_delta(comp["exactitud_decision"]["delta_pts"]),
            fmt_pct(comp["exactitud_decision"]["relativo_pct"])),
        "| Precisión de los descartes | {} | {} | {} | {} |".format(
            fmt_pct(base["precision_descartes"]), fmt_pct(d["precision_descartes"]),
            fmt_delta(comp["precision_descartes"]["delta_pts"]),
            fmt_pct(comp["precision_descartes"]["relativo_pct"])),
        "",
        "Matriz de decisión (positivo = alerta real):",
        "",
        "| Modelo | TP | FN | TN | FP | Inválidas |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for nombre, m in (("Base", base), ("D", d)):
        c = m["confusion"]
        lineas.append("| {} | {} | {} | {} | {} | {} |".format(
            nombre, c["TP"], c["FN"], c["TN"], c["FP"], m["respuestas_invalidas"]))
    lineas += [
        "",
        "IC95 de Wilson para cada métrica (n pequeño: los intervalos son amplios):",
        "",
        "| Métrica | Base | IC95 base | D | IC95 D |",
        "|---|---:|---:|---:|---:|",
    ]
    for etiqueta, clave in (
        ("FPRR", "FPRR"),
        ("FNR", "FNR"),
        ("Exactitud de decisión", "exactitud_decision"),
        ("Precisión de los descartes", "precision_descartes"),
    ):
        lineas.append("| {} | {} | {} | {} | {} |".format(
            etiqueta, fmt_pct(base[clave]), fmt_ic(base["IC95_wilson"][clave]),
            fmt_pct(d[clave]), fmt_ic(d["IC95_wilson"][clave])))
    lineas += [
        "",
        "## 4. Acuerdo entre modelos",
        "",
        "Los dos modelos coinciden en **{}/{} alertas ({} %)**.".format(
            datos["acuerdo"]["coincidencias"], datos["alertas"],
            fmt(100.0 * datos["acuerdo"]["coincidencias"] / datos["alertas"])),
        "",
    ]
    if datos["acuerdo"]["discrepancias"]:
        lineas += [
            "| ID | Regla | Etiqueta | Base | D |",
            "|---|---|---|---|---|",
        ]
        for fila in datos["acuerdo"]["discrepancias"]:
            lineas.append("| {} | {} | {} | {} | {} |".format(
                fila["id"], fila["regla"], fila["etiqueta"],
                fila["base"], fila["d"]))
        lineas.append("")
    lineas += [
        "## 5. Atajo de severidad",
        "",
        "La regla «SAFE si la severidad del SAST es baja; VULNERABLE en otro caso» "
        "reproduce la decisión de D en **{}/{} casos ({} %)**. {}".format(
            datos["atajo_severidad"]["coincidencias"],
            datos["atajo_severidad"]["total"],
            fmt(datos["atajo_severidad"]["porcentaje"]),
            "No hay discrepancias: en este banco D no usa el contexto del código."
            if not datos["atajo_severidad"]["discrepancias"]
            else "Discrepancias: {}.".format(datos["atajo_severidad"]["discrepancias"])),
        "",
        "| ID | Regla | Severidad SAST | Veredicto D |",
        "|---|---|---|---|",
    ]
    for r in datos["registros"]:
        lineas.append("| {} | {} | {} | {} |".format(
            r["id"], r["regla"], r.get("severidad_sast", "?"),
            r["modelos"]["d"]["veredicto"]))
    lineas += [
        "",
        "## 6. Detalle por caso",
        "",
        "| ID | Regla | OWASP | Etiqueta | Base | D |",
        "|---|---|---|---|---|---|",
    ]
    for r in datos["registros"]:
        lineas.append("| {} | {} | {} | {} | {} | {} |".format(
            r["id"], r["regla"], r["owasp"], r["etiqueta"],
            r["modelos"]["base"]["veredicto"], r["modelos"]["d"]["veredicto"]))
    lineas += [
        "",
        "## 7. Lectura y límites",
        "",
        "- FPRR mide qué proporción de los falsos positivos etiquetados se "
        "recomienda descartar; FNR, qué proporción de las alertas reales se "
        "recomienda descartar. En modo asesor, un `SAFE` es una recomendación, no "
        "una supresión.",
        "- El banco es pequeño y está construido por el autor. Sirve para detectar "
        "regresiones y comparar modelos con verdad de referencia, no para estimar "
        "el rendimiento en producción.",
        "- Varias reglas de Bandit son heurísticas: la etiqueta depende del contexto "
        "del caso. La justificación de cada caso está en `casos.jsonl` para que la "
        "clasificación sea auditable.",
        "- Reglas ignoradas por el emparejamiento (alertas no etiquetadas del mismo "
        "archivo): {}.".format(
            ", ".join("{} x{}".format(k, v) for k, v in sorted(datos["ignoradas"].items()))
            or "ninguna"),
        "",
    ]
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(description="Banco sintetico etiquetado del agente")
    parser.add_argument("--base", default="qwen2.5-coder:1.5b")
    parser.add_argument("--d", default="qwen2.5-coder-triage")
    parser.add_argument("--url", default="http://localhost:11434")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out", default=str(ROOT / "eval" / "banco_sintetico.json"))
    parser.add_argument("--md", default=str(ROOT / "docs" / "BANCO_SINTETICO.md"))
    parser.add_argument("--validar", action="store_true",
                        help="Solo ejecuta Bandit y valida el emparejamiento")
    parser.add_argument("--recalcular", action="store_true",
                        help="Recalcula metricas e informe desde el JSON guardado, sin llamar a Ollama")
    args = parser.parse_args()

    if args.recalcular:
        datos = json.loads(Path(args.out).read_text(encoding="utf-8"))
        registros = datos["registros"]
        base = metricas(registros, "base")
        d = metricas(registros, "d")
        datos["metricas"] = {"base": base, "d": d}
        datos["comparacion"] = comparar(base, d)
        Path(args.out).write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        Path(args.md).write_text(markdown(datos), encoding="utf-8")
        print("Recalculado desde", args.out)
        return 0

    casos = cargar_casos()
    pares, errores, ignoradas = emparejar(casos)
    print("Casos: {} | emparejados: {} | errores: {}".format(
        len(casos), len(pares), len(errores)))
    if ignoradas:
        print("Alertas ignoradas:", dict(ignoradas))
    for error in errores:
        print("ERROR:", error)
    if args.validar:
        return 1 if errores else 0
    if errores:
        raise SystemExit("Corrige los errores de emparejamiento antes de llamar al modelo.")

    validar_modelos(args.url, [args.base, args.d])
    clientes = {
        "base": OllamaClient(base_url=args.url, model=args.base, timeout=args.timeout),
        "d": OllamaClient(base_url=args.url, model=args.d, timeout=args.timeout),
    }

    registros = []
    for indice, (caso, finding) in enumerate(pares, 1):
        registro = {
            "id": caso["id"],
            "archivo": caso["archivo"],
            "regla": caso["regla"],
            "cwe": caso["cwe"],
            "owasp": caso["owasp"],
            "etiqueta": caso["etiqueta"],
            "justificacion": caso["justificacion"],
            "severidad_sast": finding.severity,
            "confianza_sast": finding.confidence,
            "modelos": {},
        }
        for clave, cliente in clientes.items():
            try:
                raw = cliente.generate(build_prompt(finding), system=SYSTEM)
                resultado = parse_response(raw, finding)
                registro["modelos"][clave] = {
                    "veredicto": resultado.veredicto,
                    "cwe": resultado.cwe,
                    "severidad": resultado.severidad,
                    "valido": resultado.valido,
                    "origen": resultado.origen,
                    "explicacion": resultado.explicacion,
                }
            except OllamaError as exc:
                registro["modelos"][clave] = {
                    "veredicto": "SOSPECHOSA", "cwe": finding.cwe,
                    "severidad": finding.severity, "valido": False,
                    "origen": "error", "explicacion": str(exc),
                }
        registros.append(registro)
        print("[{}/{}] {} {} -> base={} d={}".format(
            indice, len(pares), caso["id"], caso["regla"],
            registro["modelos"]["base"]["veredicto"],
            registro["modelos"]["d"]["veredicto"]), flush=True)

    base = metricas(registros, "base")
    d = metricas(registros, "d")
    discrepancias = [
        {"id": r["id"], "regla": r["regla"], "etiqueta": r["etiqueta"],
         "base": r["modelos"]["base"]["veredicto"],
         "d": r["modelos"]["d"]["veredicto"]}
        for r in registros
        if r["modelos"]["base"]["veredicto"] != r["modelos"]["d"]["veredicto"]
    ]
    datos = {
        "generado_por": "eval/banco_sintetico.py",
        "fecha": date.today().isoformat(),
        "modelos": {"base": args.base, "d": args.d},
        "prompt": "triage.build_prompt + triage.SYSTEM (producto)",
        "alertas": len(registros),
        "errores_validacion": errores,
        "ignoradas": dict(ignoradas),
        "metricas": {"base": base, "d": d},
        "comparacion": comparar(base, d),
        "acuerdo": {
            "coincidencias": len(registros) - len(discrepancias),
            "discrepancias": discrepancias,
        },
        "atajo_severidad": analisis_atajo(registros),
        "reglas": por_regla(registros),
        "registros": registros,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    md = Path(args.md)
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(markdown(datos), encoding="utf-8")
    print("\nFPRR  base {:>5} %  D {:>5} %".format(fmt(base["FPRR"]), fmt(d["FPRR"])))
    print("FNR   base {:>5} %  D {:>5} %".format(fmt(base["FNR"]), fmt(d["FNR"])))
    print("Exactitud base {:>5} %  D {:>5} %".format(
        fmt(base["exactitud_decision"]), fmt(d["exactitud_decision"])))
    print("Acuerdo: {}/{}".format(datos["acuerdo"]["coincidencias"], len(registros)))
    print("guardado:", out)
    print("guardado:", md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
