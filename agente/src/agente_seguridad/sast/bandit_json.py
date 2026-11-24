"""Conversion de la salida JSON de Bandit a los objetos del producto.

Se usa tanto cuando el SAST se ejecuta en local como cuando se importa una
salida JSON existente con ``--from-report``. Este modulo solo interpreta el
formato de datos: no importa ni ejecuta el paquete ``bandit``.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..context import extract_context
from ..models import SEVERITY_MAP, Finding
from ..owasp import etiqueta as owasp_etiqueta


def cwe_of(result: Dict[str, Any]) -> str:
    cwe = result.get("issue_cwe")
    if isinstance(cwe, dict) and cwe.get("id"):
        return "CWE-{}".format(cwe["id"])
    if isinstance(cwe, (list, tuple)) and cwe:
        return "CWE-{}".format(cwe[0])
    raw = result.get("cwe")
    if isinstance(raw, dict) and raw.get("id"):
        return "CWE-{}".format(raw["id"])
    text = str(result.get("test_name", ""))
    return text if text else "CWE-000"


def _relative(path: Path, root: Optional[Path]) -> str:
    if root:
        try:
            return str(path.resolve().relative_to(root)).replace("\\", "/")
        except (ValueError, OSError):
            pass
    return str(path).replace("\\", "/")


def findings_from_results(results: List[Dict[str, Any]], root: Optional[Path] = None,
                          with_context: bool = True) -> List[Finding]:
    """Convierte la lista ``results`` de Bandit en hallazgos del producto."""
    root = root.resolve() if root else None
    findings: List[Finding] = []
    for item in results:
        raw_path = str(item.get("filename") or "")
        path = Path(raw_path)
        if root and not path.is_absolute():
            path = root / path
        rel = _relative(path, root)
        line = int(item.get("line_number") or 1)
        end_line = int(item.get("end_col_offset") or line)
        snippet, function = extract_context(str(path.resolve()), line) if (with_context and raw_path) else ("", "<archivo>")
        cwe = cwe_of(item)
        findings.append(Finding(
            finding_id="",
            rule_id=str(item.get("test_id") or ""),
            cwe=cwe,
            severity=SEVERITY_MAP.get(str(item.get("issue_severity")), "media"),
            confidence=str(item.get("issue_confidence", "")),
            message=str(item.get("issue_text", "")).strip(),
            file=rel,
            line=line,
            end_line=end_line,
            code=str(item.get("code") or ""),
            function=function,
            fingerprint="",
            owasp=owasp_etiqueta(cwe),
            context=snippet,
        ))
    return findings
