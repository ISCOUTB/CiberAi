"""Carga hallazgos desde un reporte existente, sin ejecutar ningun SAST.

Formatos admitidos:
  * ``reporte.json`` generado por esta CLI (``scan.tool_runs[].findings``);
  * ``hallazgos.sarif`` generado por esta CLI (SARIF 2.1.0);
  * salida JSON de Bandit (``{"results": [...]}``);
  * una lista de hallazgos, sola o bajo la clave ``findings``.

Cuando se pasa un directorio ``target`` y el archivo senalado por el hallazgo
existe, se recupera el contexto del codigo para que el triage pueda usar el LLM.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..context import extract_context
from ..models import Finding, ToolRun, utcnow
from ..owasp import etiqueta as owasp_etiqueta, normalizar
from .bandit_json import findings_from_results

LEVEL_TO_SEVERITY = {"error": "alta", "warning": "media", "note": "baja"}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _cwe(value: Any) -> str:
    if not value:
        return ""
    return normalizar(value) or str(value).strip()


def _finding_from_dict(raw: Dict[str, Any], root: Optional[Path] = None) -> Finding:
    cwe = _cwe(raw.get("cwe"))
    file = str(raw.get("file") or "")
    line = _as_int(raw.get("line"), 1)
    context = str(raw.get("context") or "")
    function = str(raw.get("function") or "")

    if root and root.is_dir() and file and not context:
        path = Path(file)
        if not path.is_absolute():
            path = root / path
        if path.is_file():
            snippet, name = extract_context(str(path.resolve()), line)
            context = snippet
            function = function or name

    return Finding(
        finding_id=str(raw.get("finding_id") or ""),
        rule_id=str(raw.get("rule_id") or raw.get("ruleId") or ""),
        cwe=cwe,
        severity=str(raw.get("severity") or "media").lower(),
        confidence=str(raw.get("confidence") or ""),
        message=str(raw.get("message") or ""),
        file=file,
        line=line,
        end_line=_as_int(raw.get("end_line"), line),
        code=str(raw.get("code") or ""),
        function=function,
        fingerprint=str(raw.get("fingerprint") or ""),
        owasp=str(raw.get("owasp") or owasp_etiqueta(cwe)),
        context=context,
    )


def _single_run(findings: List[Finding], tool: str = "reporte") -> List[ToolRun]:
    return [ToolRun(tool=tool, version="desconocida", started=utcnow(),
                    finished=utcnow(), findings=findings)]


def _runs_from_report(doc: Dict[str, Any], root: Optional[Path]) -> List[ToolRun]:
    source = doc.get("scan") or doc
    runs: List[ToolRun] = []
    for raw in source.get("tool_runs") or []:
        findings = [_finding_from_dict(item, root) for item in raw.get("findings") or []]
        runs.append(ToolRun(
            tool=str(raw.get("tool") or "reporte"),
            version=str(raw.get("version") or "desconocida"),
            started=str(raw.get("started") or utcnow()),
            finished=str(raw.get("finished") or utcnow()),
            findings=findings,
        ))
    return runs


def _runs_from_sarif(doc: Dict[str, Any], root: Optional[Path]) -> List[ToolRun]:
    runs: List[ToolRun] = []
    for run in doc.get("runs") or []:
        driver = (run.get("tool") or {}).get("driver") or {}
        rules = {str(rule.get("id") or ""): rule for rule in driver.get("rules") or []}
        findings: List[Finding] = []
        for result in run.get("results") or []:
            props = result.get("properties") or {}
            rule = rules.get(str(result.get("ruleId") or "")) or {}
            rule_props = rule.get("properties") or {}
            location = ((result.get("locations") or [{}])[0].get("physicalLocation") or {})
            region = location.get("region") or {}
            cwe = _cwe(props.get("cwe") or rule_props.get("cwe"))
            findings.append(_finding_from_dict({
                "finding_id": (result.get("partialFingerprints") or {}).get("findingId", ""),
                "rule_id": result.get("ruleId", ""),
                "cwe": cwe,
                "severity": props.get("severity") or LEVEL_TO_SEVERITY.get(
                    str(result.get("level") or ""), "media"),
                "confidence": props.get("confidence", ""),
                "message": (result.get("message") or {}).get("text", ""),
                "file": (location.get("artifactLocation") or {}).get("uri", ""),
                "line": region.get("startLine", 1),
                "end_line": region.get("endLine", region.get("startLine", 1)),
                "function": props.get("function", ""),
                "owasp": props.get("owasp") or rule_props.get("owasp") or owasp_etiqueta(cwe),
            }, root))
        runs.append(ToolRun(
            tool=str(driver.get("name") or "sarif"),
            version=str(driver.get("version") or "desconocida"),
            started=utcnow(),
            finished=utcnow(),
            findings=findings,
        ))
    return runs


def load_tool_runs(path: Path, target: Optional[Path] = None) -> List[ToolRun]:
    """Lee un reporte y devuelve sus ejecuciones de herramienta.

    Lanza ``ValueError`` si el archivo no existe, no es JSON valido o su
    formato no es reconocido.
    """
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("No existe el archivo de reporte: {}".format(path))
    except OSError as exc:
        raise ValueError("No se pudo leer {}: {}".format(path, exc))
    except json.JSONDecodeError as exc:
        raise ValueError("JSON invalido en {}: {}".format(path, exc))

    root = target.resolve() if target else path.parent.resolve()
    if not root.is_dir():
        root = root.parent
    if isinstance(data, dict):
        if "scan" in data or "tool_runs" in data:
            return _runs_from_report(data, root)
        if "runs" in data:
            return _runs_from_sarif(data, root)
        if "results" in data:
            return _single_run(findings_from_results(data["results"], root=root), tool="bandit")
        if "findings" in data:
            items = data["findings"]
        else:
            raise ValueError("Formato de reporte no reconocido: {}".format(path))
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("Formato de reporte no reconocido: {}".format(path))

    return _single_run([_finding_from_dict(item, root) for item in items if isinstance(item, dict)])
