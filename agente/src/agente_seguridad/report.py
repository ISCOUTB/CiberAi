import json
import os
import re
import shutil
import sys
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


class _Colors:
    """Códigos ANSI; se desactivan si no hay TTY o si NO_COLOR está definido."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


def _use_color(no_color: bool) -> bool:
    if no_color or os.environ.get("NO_COLOR"):
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _color(text: str, codes: str, no_color: bool = False) -> str:
    if no_color or not _use_color(no_color=False):
        return text
    return codes + text + _Colors.RESET


def _verdict_style(verdict: str, no_color: bool = False) -> str:
    v = str(verdict).upper()
    if v == "VULNERABLE":
        return _color(v, _Colors.BOLD + _Colors.RED, no_color=no_color)
    if v == "SAFE":
        return _color(v, _Colors.BOLD + _Colors.GREEN, no_color=no_color)
    if v == "SOSPECHOSA":
        return _color(v, _Colors.BOLD + _Colors.YELLOW, no_color=no_color)
    return _color(v, _Colors.BOLD + _Colors.DIM, no_color=no_color)


def _severity_style(severity: str, no_color: bool = False) -> str:
    s = str(severity).lower()
    if s in ("critica", "critico", "critical", "alta", "high"):
        return _color(severity, _Colors.RED, no_color=no_color)
    if s in ("media", "medium"):
        return _color(severity, _Colors.YELLOW, no_color=no_color)
    if s in ("baja", "low"):
        return _color(severity, _Colors.GREEN, no_color=no_color)
    return severity


def _term_width(min_width: int = 80) -> int:
    try:
        cols, _ = shutil.get_terminal_size(fallback=(min_width, 24))
        return max(cols, min_width)
    except Exception:
        return min_width


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _visible_len(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def _pad(text: str, width: int) -> str:
    pad = width - _visible_len(text)
    return text + (" " * pad if pad > 0 else "")


def _wrap(text: str, width: int, indent: int = 0) -> List[str]:
    """Divide un texto en líneas sin cortar palabras."""
    if width <= indent + 1:
        width = indent + 40
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= width - indent:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def console(scan: Scan, limit: int = 40, no_color: bool = False) -> str:
    data = summary(scan)
    use_color = _use_color(no_color=no_color)
    C = _Colors
    w = _term_width()

    def c(text: str, *codes: str) -> str:
        if not use_color:
            return text
        return "".join(codes) + text + C.RESET

    def bar(char: str = "─", length: int = None) -> str:
        length = length or w
        return char * length


    title_plain = "REPORTE DE SEGURIDAD - CIBERAI"
    title_colored = c(title_plain.center(w - 2), C.BOLD + C.CYAN)
    header = [
        c("╭" + bar("─", w - 2) + "╮", C.CYAN),
        c("│", C.CYAN) + title_colored + c("│", C.CYAN),
        c("╰" + bar("─", w - 2) + "╯", C.CYAN),
    ]

    summary_lines = [
        c(" RESUMEN ", C.BOLD),
        "",
        "  Escaneo:  {}  →  {}".format(c(scan.scan_id, C.YELLOW), scan.target),
        "  Archivos: {}  |  Total alertas: {}".format(
            c(str(data["archivos"]), C.YELLOW), c(str(data["total"]), C.BOLD + C.WHITE)),
        "",
        "  Conservadas: {}  |  Recomendadas descarte: {}  |  Sospechosas: {}  |  Errores modelo: {}".format(
            c(str(data["conservadas"]), C.GREEN),
            c(str(data["recomendadas_descarte"]), C.GREEN),
            c(str(data["sospechosas"]), C.YELLOW if data["sospechosas"] else C.GREEN),
            c(str(data["errores_modelo"]), C.RED if data["errores_modelo"] else C.GREEN)),
        "",
        "  Herramientas:  {}".format(
            ", ".join("{}={}".format(c(k, C.CYAN), c(str(v), C.WHITE)) for k, v in data["por_herramienta"].items())
            or c("sin alertas", C.DIM)),
        "  OWASP Top 10 2021:  {}".format(
            ", ".join("{}={}".format(c(k, C.CYAN), c(str(v), C.WHITE)) for k, v in data["por_owasp"].items())
            or c("sin alertas", C.DIM)),
    ]

    if data["errores_modelo"]:
        summary_lines.append("")
        summary_lines.append(
            c("  ⚠  {} alerta(s) se marcaron SOSPECHOSA porque el modelo no respondió.".format(
                data["errores_modelo"]), C.YELLOW))

    findings_header = [
        "",
        c(" HALLAZGOS ", C.BOLD),
        "",
    ]

    ordered = sorted(scan.findings, key=lambda f: (_verdict(f) == "SAFE", f.file, f.line))
    if not ordered:
        body = [c("  No se encontraron alertas.", C.DIM)]
    else:
        # Calcular anchos para alinear columnas de forma cómoda.
        max_func = max((len(str(f.function)) for f in ordered), default=0)
        max_cwe = max((len(str(f.cwe)) for f in ordered), default=0)
        max_owasp = max((len(str(f.owasp or "sin_cat")) for f in ordered), default=0)
        max_file = max((len(str(f.file)) for f in ordered), default=0)

        body: List[str] = []
        for i, finding in enumerate(ordered[:limit], 1):
            triage = finding.triage or {}
            verdict = triage.get("veredicto", "SIN_TRIAGE")
            explanation = str(triage.get("explicacion", "")).strip().replace("\n", " ")

            owasp = finding.owasp or "sin_categoria"
            func = str(finding.function) if finding.function else "<global>"
            loc = "{}:{}".format(finding.file, finding.line)

            v_styled = _pad(_verdict_style(verdict, no_color=not use_color), 11)
            cwe_styled = _pad(c(str(finding.cwe), C.CYAN), max_cwe + 2)
            owasp_styled = _pad(c(owasp, C.MAGENTA), max_owasp + 2)
            loc_styled = _pad(c(loc, C.WHITE), max_file + 4)
            sev_styled = _pad(_severity_style(finding.severity, no_color=not use_color), 8)
            func_styled = c(func, C.DIM)

            line1 = "  #{:<2} {} {} {} {} {} {}".format(
                i, v_styled, cwe_styled, owasp_styled, loc_styled, sev_styled, func_styled)
            body.append(line1)
            if explanation:
                wrapped = _wrap(explanation, w - 8)
                for part in wrapped:
                    body.append("        " + part)
            body.append("")

        if len(ordered) > limit:
            body.append(c("  ... y {} hallazgos más (ver reporte.json)".format(len(ordered) - limit), C.DIM))

    footer = [
        "",
        c(" Modo asesor: un veredicto SAFE solo recomienda descartar; la alerta permanece en el reporte. ", C.DIM),
    ]

    return "\n".join(header + summary_lines + findings_header + body + footer)
