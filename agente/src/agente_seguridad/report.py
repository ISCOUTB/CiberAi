import json
from pathlib import Path
from typing import Any, Dict, List

from .models import Finding, Scan
from .owasp import nombre as owasp_nombre
from .sast.sarif import to_sarif


def summary(scan: Scan) -> Dict[str, Any]:
    findings = scan.findings
    # Modo asesor: ninguna alerta se elimina del reporte. Un veredicto SAFE solo
    # produce una recomendacion de descarte para el revisor humano.
    recomendadas = [f for f in findings if _verdict(f) == "SAFE"]
    sospechosas = [f for f in findings if _verdict(f) == "SOSPECHOSA"]
    errores = [f for f in findings if (f.triage or {}).get("origen") == "respaldo"]
    return {
        "total": len(findings),
        "conservadas": len(findings),
        "recomendadas_descarte": len(recomendadas),
        "sospechosas": len(sospechosas),
        "errores_modelo": len(errores),
        "archivos": len({f.file for f in findings}),
        "por_herramienta": {run.tool: len(run.findings) for run in getattr(scan, "tool_runs", [])},
        "por_cwe": _count(findings, lambda f: f.cwe),
        "por_severidad": _count(findings, lambda f: f.severity),
        # Categoria OWASP Top 10 2021 derivada del CWE del SAST. Un CWE fuera
        # de las listas oficiales se cuenta como `sin_categoria`, igual que en
        # la evaluacion de cobertura.
        "por_owasp": _count(findings, lambda f: f.owasp or "sin_categoria"),
        "owasp_nombres": {k: owasp_nombre(k) for k in
                          _count(findings, lambda f: f.owasp or "sin_categoria")},
    }


def _verdict(finding: Finding) -> str:
    return str((finding.triage or {}).get("veredicto", ""))


def _count(findings: List[Finding], key) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for finding in findings:
        k = str(key(finding))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def report_dict(scan: Scan) -> Dict[str, Any]:
    return {"scan": scan.to_dict(), "resumen": summary(scan)}


def write_outputs(scan: Scan, out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "reporte.json"
    sarif_path = out_dir / "hallazgos.sarif"
    json_path.write_text(json.dumps(report_dict(scan), ensure_ascii=False, indent=2), encoding="utf-8")
    sarif_path.write_text(
        json.dumps(to_sarif(scan.findings, scan.target), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"json": str(json_path), "sarif": str(sarif_path)}


def console(scan: Scan, limit: int = 40) -> str:
    data = summary(scan)
    lines = [
        "Escaneo {}  ->  {}".format(scan.scan_id, scan.target),
        "Hallazgos: {} | conservadas: {} | recomendadas para descarte: {} | sospechosas: {} | errores modelo: {}".format(
            data["total"], data["conservadas"], data["recomendadas_descarte"],
            data["sospechosas"], data["errores_modelo"]),
        "Herramientas: {}".format(
            ", ".join("{}={}".format(k, v) for k, v in data["por_herramienta"].items())
            or "sin alertas"),
        "OWASP Top 10 2021: {}".format(
            ", ".join("{}={}".format(k, v) for k, v in data["por_owasp"].items())
            or "sin alertas"),
        "",
    ]
    ordered = sorted(scan.findings, key=lambda f: (_verdict(f) == "SAFE", f.file, f.line))
    for finding in ordered[:limit]:
        triage = finding.triage or {}
        verdict = triage.get("veredicto", "SIN_TRIAGE")
        explanation = str(triage.get("explicacion", "")).strip().replace("\n", " ")
        lines.append("{:<11} {:<12} {:<14} {} {}:{}  {}".format(
            verdict, finding.cwe, finding.owasp or "sin_categoria",
            finding.file, finding.line, finding.severity, finding.function))
        if explanation:
            lines.append("            " + explanation[:160])
    if len(ordered) > limit:
        lines.append("... {} hallazgos mas".format(len(ordered) - limit))
    return "\n".join(lines)
