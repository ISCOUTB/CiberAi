"""Resume el smoke test con repositorios reales y lista las recomendaciones SAFE.

Lee los reportes generados por `agente/run.py scan` en una carpeta con el
formato `out_<modelo>_<repo>/reporte.json`, donde `<modelo>` es `base` o `d`.
No decide si un SAFE es correcto: prepara la lista para la auditoria manual.

Uso:
    python eval/auditar_smoke_repos.py --root C:\\ruta\\smoke
    python eval/auditar_smoke_repos.py --root C:\\ruta\\smoke --json eval/auditoria_smoke.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def cargar(root):
    datos = {}
    for reporte in sorted(Path(root).glob("out_*_*/reporte.json")):
        partes = reporte.parent.name.split("_", 2)
        if len(partes) != 3:
            continue
        _, modelo, repo = partes
        if modelo not in ("base", "d"):
            continue
        payload = json.loads(reporte.read_text(encoding="utf-8"))
        hallazgos = payload["scan"]["tool_runs"][0]["findings"]
        datos.setdefault(repo, {})[modelo] = {
            "resumen": payload["resumen"],
            "hallazgos": hallazgos,
        }
    return datos


def safe_candidates(hallazgos):
    for f in hallazgos:
        triage = f.get("triage") or {}
        if triage.get("veredicto") == "SAFE":
            yield {
                "id": f["finding_id"],
                "regla": f["rule_id"],
                "cwe": f["cwe"],
                "severidad": f["severity"],
                "archivo": f["file"],
                "linea": f["line"],
                "funcion": f.get("function"),
                "justificacion": triage.get("explicacion", ""),
                "correccion": triage.get("correccion", ""),
            }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Carpeta con out_base_*/ y out_d_*/")
    ap.add_argument("--json", help="Ruta opcional para guardar el resumen")
    args = ap.parse_args()

    datos = cargar(args.root)
    salida = {"repos": {}, "safe": []}

    print("| Repo | Modelo | Alertas | Conservadas | SAFE | SOSPECHOSA | Errores |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for repo, modelos in sorted(datos.items()):
        for modelo in ("base", "d"):
            if modelo not in modelos:
                continue
            r = modelos[modelo]["resumen"]
            print("| {} | {} | {} | {} | {} | {} | {} |".format(
                repo, modelo, r["total"], r["conservadas"],
                r["recomendadas_descarte"], r["sospechosas"], r["errores_modelo"]))
            salida["repos"].setdefault(repo, {})[modelo] = r
            for cand in safe_candidates(modelos[modelo]["hallazgos"]):
                cand.update({"repo": repo, "modelo": modelo})
                salida["safe"].append(cand)

    print("\n## Recomendaciones SAFE (candidatas a descarte)\n")
    print("| Repo | Modelo | Regla | CWE | Archivo:linea | Justificacion |")
    print("|---|---|---|---|---|---|")
    for c in salida["safe"]:
        just = " ".join(str(c["justificacion"]).split())[:110]
        print("| {} | {} | {} | {} | {}:{} | {} |".format(
            c["repo"], c["modelo"], c["regla"], c["cwe"],
            c["archivo"], c["linea"], just))

    if args.json:
        Path(args.json).write_text(
            json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\nguardado:", args.json)


if __name__ == "__main__":
    main()
