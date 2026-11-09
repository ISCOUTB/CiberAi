"""Corre el agente sobre repositorios reales pinneados con los dos modelos.

No es una evaluacion etiquetada: no hay verdad de referencia por linea, asi que
no produce FPRR ni FNR. Sirve para comprobar que el producto funciona sobre
codigo ajeno, medir cuantas alertas recomienda descartar cada modelo y auditar
el acuerdo. Es la version reproducible del smoke test de `docs/SMOKE_REPOS.md`,
con desglose OWASP y de severidad.

Los repos se clonan shallow en `eval/repos_reales/` (ignorada por git). Solo se
escanea el subdirectorio fuente, no pruebas ni documentacion.

Escribe:
    eval/corrida_repos_reales.json
    docs/CORRIDA_REPOS_REALES.md

Uso:
    python eval/corrida_repos_reales.py
    python eval/corrida_repos_reales.py --refrescar
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
REPOS_DIR = ROOT / "eval" / "repos_reales"

sys.path.insert(0, str(ROOT / "agente" / "src"))

from agente_seguridad.dedup import deduplicate, with_ids  # noqa: E402
from agente_seguridad.llm.ollama_client import OllamaClient, OllamaError  # noqa: E402
from agente_seguridad.sast.bandit_runner import run_bandit  # noqa: E402
from agente_seguridad.triage import SYSTEM, build_prompt, parse_response  # noqa: E402

REPOS = {
    "itsdangerous": {
        "url": "https://github.com/pallets/itsdangerous",
        "tag": "2.2.0",
        "commit": "096c8d42545d3b68ea21a4f890fb2b2d8979c0bd",
        "subdir": "src",
    },
    "pyjwt": {
        "url": "https://github.com/jpadilla/pyjwt",
        "tag": "2.10.1",
        "commit": "3ebbb22f30f2b1b41727b269a08b427e9a85d6bb",
        "subdir": "jwt",
    },
    "httpie": {
        "url": "https://github.com/httpie/cli",
        "tag": "3.2.4",
        "commit": "2105caa49bae87c5809c274e407619a0de2639d1",
        "subdir": "httpie",
    },
}


def validar_modelos(url, modelos):
    try:
        resp = requests.get(url.rstrip("/") + "/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit("Ollama no responde en {}: {}".format(url, exc))
    disponibles = {m.get("name", "") for m in resp.json().get("models", [])}
    faltan = [m for m in modelos
              if not any(n == m or n.split(":")[0] == m for n in disponibles)]
    if faltan:
        raise SystemExit("Modelos no disponibles en Ollama: {}. Hay: {}".format(
            ", ".join(faltan), ", ".join(sorted(disponibles))))


def preparar_repo(nombre, info, refrescar):
    destino = REPOS_DIR / nombre
    if refrescar and destino.exists():
        import shutil
        shutil.rmtree(destino)
    if not (destino / ".git").exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        print("clonando {} {} ...".format(nombre, info["tag"]), flush=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", info["tag"],
             info["url"], str(destino)],
            check=True, capture_output=True, text=True, timeout=900,
        )
    head = subprocess.run(["git", "-C", str(destino), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    if head != info["commit"]:
        raise SystemExit(
            "{}: HEAD {} no coincide con el commit fijado {}. Usa --refrescar.".format(
                nombre, head, info["commit"]))
    return destino / info["subdir"]


def fmt(valor):
    return ("{:.1f}".format(valor)).replace(".", ",")


def markdown(datos):
    total = datos["totales"]
    lineas = [
        "# Corrida sobre repositorios reales",
        "",
        "Generado por `eval/corrida_repos_reales.py` el {}.".format(datos["fecha"]),
        "",
        "Prueba de humo reproducible, no una evaluación etiquetada: no hay verdad "
        "de referencia por línea, así que **no produce FPRR ni FNR**. Mide cuántas "
        "alertas recomienda descartar cada modelo y cuánto coinciden.",
        "",
        "## 1. Repositorios",
        "",
        "| Repo | Etiqueta | Commit | Subdirectorio | Alertas |",
        "|---|---|---|---|---:|",
    ]
    for nombre, info in datos["repos"].items():
        lineas.append("| `{}` | {} | `{}` | `{}` | {} |".format(
            nombre, info["tag"], info["commit"], info["subdir"], info["alertas"]))
    lineas += [
        "",
        "## 2. Resultados",
        "",
        "| Modelo | Alertas | SAFE | Conservadas | SOSPECHOSA | Errores | % SAFE |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for clave, etiqueta in (("base", "Base"), ("d", "D")):
        m = total[clave]
        lineas.append("| {} | {} | {} | {} | {} | {} | {} % |".format(
            etiqueta, m["alertas"], m["SAFE"], m["conservadas"], m["SOSPECHOSA"],
            m["errores_modelo"], fmt(100.0 * m["SAFE"] / m["alertas"])))
    lineas += [
        "",
        "| Repo | Alertas | SAFE base | SAFE D | Acuerdo |",
        "|---|---:|---:|---:|---:|",
    ]
    for nombre, info in datos["repos"].items():
        lineas.append("| `{}` | {} | {} | {} | {}/{} |".format(
            nombre, info["alertas"], info["base"]["SAFE"], info["d"]["SAFE"],
            info["acuerdo"]["coincidencias"], info["alertas"]))
    lineas += [
        "",
        "## 3. Cobertura OWASP",
        "",
        "| Categoría | Alertas | SAFE base | SAFE D |",
        "|---|---:|---:|---:|",
    ]
    for categoria, valores in datos["por_owasp"].items():
        lineas.append("| {} | {} | {} | {} |".format(
            categoria, valores["alertas"], valores["base_safe"], valores["d_safe"]))
    lineas += [
        "",
        "## 4. Decisión de D por severidad del SAST",
        "",
        "| Severidad | Alertas | SAFE base | SAFE D | % SAFE D |",
        "|---|---:|---:|---:|---:|",
    ]
    for severidad, valores in datos["por_severidad"].items():
        lineas.append("| {} | {} | {} | {} | {} % |".format(
            severidad, valores["alertas"], valores["base_safe"], valores["d_safe"],
            fmt(100.0 * valores["d_safe"] / valores["alertas"])))
    lineas += [
        "",
        "## 5. Discrepancias entre modelos",
        "",
    ]
    if datos["discrepancias"]:
        lineas += [
            "| Repo | Regla | Severidad | Archivo:Línea | Base | D |",
            "|---|---|---|---|---|---|",
        ]
        for d in datos["discrepancias"]:
            lineas.append("| `{}` | {} | {} | `{}:{}` | {} | {} |".format(
                d["repo"], d["regla"], d["severidad"], d["archivo"], d["linea"],
                d["base"], d["d"]))
    else:
        lineas.append("Los dos modelos coinciden en todas las alertas.")
    lineas += [
        "",
        "## 6. Lectura",
        "",
        "- Ninguna alerta se elimina: `conservadas == alertas` en los dos modelos. "
        "Un `SAFE` es una recomendación para revisión humana.",
        "- La corrida no etiqueta aciertos. Los porcentajes de SAFE miden ahorro "
        "potencial de revisión, no corrección. Para corrección está el banco "
        "sintético etiquetado y la auditoría manual de `docs/SMOKE_REPOS.md`.",
        "- Si D recomienda descartar casi todas las alertas de severidad baja y "
        "ninguna de severidad media o alta, la decisión puede explicarse por la "
        "severidad que reporta Bandit y no por el contexto del código. El banco "
        "sintético mide esa hipótesis de forma directa.",
        "- Los repos están pinneados por commit. El escaneo se limita al paquete "
        "fuente para no mezclar pruebas, documentación ni entornos virtuales.",
        "",
    ]
    return "\n".join(lineas)


def main():
    parser = argparse.ArgumentParser(description="Corrida del agente sobre repos reales")
    parser.add_argument("--base", default="qwen2.5-coder:1.5b")
    parser.add_argument("--d", default="qwen2.5-coder-triage")
    parser.add_argument("--url", default="http://localhost:11434")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--refrescar", action="store_true",
                        help="Borra y vuelve a clonar los repos")
    parser.add_argument("--out", default=str(ROOT / "eval" / "corrida_repos_reales.json"))
    parser.add_argument("--md", default=str(ROOT / "docs" / "CORRIDA_REPOS_REALES.md"))
    args = parser.parse_args()

    validar_modelos(args.url, [args.base, args.d])
    clientes = {
        "base": OllamaClient(base_url=args.url, model=args.base, timeout=args.timeout),
        "d": OllamaClient(base_url=args.url, model=args.d, timeout=args.timeout),
    }

    salida = {
        "generado_por": "eval/corrida_repos_reales.py",
        "fecha": date.today().isoformat(),
        "modelos": {"base": args.base, "d": args.d},
        "prompt": "triage.build_prompt + triage.SYSTEM (producto)",
        "repos": {},
        "por_owasp": {},
        "por_severidad": {},
        "discrepancias": [],
    }

    total_findings = []
    for nombre, info in REPOS.items():
        print("\n== {} {} ==".format(nombre, info["tag"]), flush=True)
        subdir = preparar_repo(nombre, info, args.refrescar)
        findings = with_ids(deduplicate(run_bandit(subdir)))
        print("alertas: {}".format(len(findings)), flush=True)
        for indice, finding in enumerate(findings, 1):
            for clave, cliente in clientes.items():
                try:
                    raw = cliente.generate(build_prompt(finding), system=SYSTEM)
                    resultado = parse_response(raw, finding)
                    finding.triage = resultado.to_dict()
                except OllamaError as exc:
                    finding.triage = {
                        "veredicto": "SOSPECHOSA", "cwe": finding.cwe,
                        "severidad": finding.severity, "valido": False,
                        "origen": "error", "explicacion": str(exc),
                    }
                # El objeto Finding se reutiliza; se guarda una copia por modelo.
                if clave == "base":
                    base_triage = dict(finding.triage)
                else:
                    d_triage = dict(finding.triage)
            total_findings.append((nombre, finding, base_triage, d_triage))
            print("[{}/{}] {} {} -> base={} d={}".format(
                indice, len(findings), finding.rule_id, "{}/{}".format(
                    Path(finding.file).name, finding.line),
                base_triage["veredicto"], d_triage["veredicto"]), flush=True)

        # Recalcula los conteos con las copias por modelo.
        base_count = Counter()
        d_count = Counter()
        errores = {"base": 0, "d": 0}
        for repo, finding, bt, dt in total_findings:
            if repo != nombre:
                continue
            base_count[bt["veredicto"]] += 1
            d_count[dt["veredicto"]] += 1
            errores["base"] += bt.get("origen") in ("respaldo", "error")
            errores["d"] += dt.get("origen") in ("respaldo", "error")
        salida["repos"][nombre] = {
            "tag": info["tag"],
            "commit": info["commit"],
            "subdir": info["subdir"],
            "alertas": len(findings),
            "base": {
                "alertas": len(findings), "SAFE": base_count["SAFE"],
                "SOSPECHOSA": base_count["SOSPECHOSA"],
                "VULNERABLE": base_count["VULNERABLE"],
                "conservadas": len(findings), "errores_modelo": errores["base"],
            },
            "d": {
                "alertas": len(findings), "SAFE": d_count["SAFE"],
                "SOSPECHOSA": d_count["SOSPECHOSA"],
                "VULNERABLE": d_count["VULNERABLE"],
                "conservadas": len(findings), "errores_modelo": errores["d"],
            },
            "acuerdo": {
                "coincidencias": sum(1 for repo, f, bt, dt in total_findings
                                     if repo == nombre and bt["veredicto"] == dt["veredicto"]),
                "total": len(findings),
            },
        }

    # Totales y desgloses.
    totales = {}
    for clave in ("base", "d"):
        acumulado = Counter()
        for repo in salida["repos"].values():
            for campo in ("alertas", "SAFE", "SOSPECHOSA", "VULNERABLE",
                          "conservadas", "errores_modelo"):
                acumulado[campo] += repo[clave][campo]
        totales[clave] = dict(acumulado)
    salida["totales"] = totales

    for repo, finding, bt, dt in total_findings:
        ow = finding.owasp or "sin_categoria"
        fila = salida["por_owasp"].setdefault(
            ow, {"alertas": 0, "base_safe": 0, "d_safe": 0})
        fila["alertas"] += 1
        fila["base_safe"] += bt["veredicto"] == "SAFE"
        fila["d_safe"] += dt["veredicto"] == "SAFE"
        sev = finding.severity
        fila_sev = salida["por_severidad"].setdefault(
            sev, {"alertas": 0, "base_safe": 0, "d_safe": 0})
        fila_sev["alertas"] += 1
        fila_sev["base_safe"] += bt["veredicto"] == "SAFE"
        fila_sev["d_safe"] += dt["veredicto"] == "SAFE"
        if bt["veredicto"] != dt["veredicto"]:
            salida["discrepancias"].append({
                "repo": repo, "regla": finding.rule_id, "severidad": finding.severity,
                "archivo": finding.file, "linea": finding.line,
                "base": bt["veredicto"], "d": dt["veredicto"],
            })

    salida["hallazgos"] = [
        {
            "repo": repo, "regla": f.rule_id, "cwe": f.cwe,
            "owasp": f.owasp or "sin_categoria", "severidad": f.severity,
            "archivo": f.file, "linea": f.line,
            "base": {"veredicto": bt["veredicto"], "cwe": bt.get("cwe"),
                     "valido": bt.get("valido"), "origen": bt.get("origen")},
            "d": {"veredicto": dt["veredicto"], "cwe": dt.get("cwe"),
                  "valido": dt.get("valido"), "origen": dt.get("origen")},
        }
        for repo, f, bt, dt in total_findings
    ]
    # Orden estable para el JSON y el Markdown.
    salida["por_owasp"] = dict(sorted(salida["por_owasp"].items()))
    salida["por_severidad"] = dict(sorted(salida["por_severidad"].items()))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    md = Path(args.md)
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(markdown(salida), encoding="utf-8")

    print("\nTotales base: {}".format(totales["base"]))
    print("Totales D:    {}".format(totales["d"]))
    print("guardado:", out)
    print("guardado:", md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
