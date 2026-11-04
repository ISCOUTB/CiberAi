import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..context import extract_context
from ..models import SEVERITY_MAP, Finding, ToolRun, utcnow


def bandit_version() -> str:
    try:
        out = subprocess.run(
            [sys.executable, "-m", "bandit", "--version"],
            capture_output=True, text=True, timeout=60,
        )
        text = (out.stdout or "") + (out.stderr or "")
        for token in text.replace("\n", " ").split():
            if token and token[0].isdigit() and "." in token:
                return token
    except Exception:
        pass
    return "desconocida"


def _cwe_of(result: Dict[str, Any]) -> str:
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


def run_bandit(target: Path) -> List[Finding]:
    target = target.resolve()
    cmd = [sys.executable, "-m", "bandit", "-r", str(target), "-f", "json", "-q"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    payload = (proc.stdout or "").strip()
    if not payload:
        raise RuntimeError("Bandit no devolvio JSON. stderr: " + (proc.stderr or "")[:500])
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Salida invalida de Bandit: {}".format(exc))

    findings: List[Finding] = []
    for item in data.get("results", []):
        raw_path = item.get("filename", "")
        try:
            rel = str(Path(raw_path).resolve().relative_to(target)).replace("\\", "/")
        except Exception:
            rel = raw_path.replace("\\", "/")
        line = int(item.get("line_number") or 1)
        end_line = int(item.get("end_col_offset") or line)
        code = item.get("code") or ""
        snippet, function = extract_context(str(Path(raw_path).resolve()), line)
        findings.append(Finding(
            finding_id="",
            rule_id=str(item.get("test_id") or ""),
            cwe=_cwe_of(item),
            severity=SEVERITY_MAP.get(str(item.get("issue_severity")), "media"),
            confidence=str(item.get("issue_confidence", "")),
            message=str(item.get("issue_text", "")).strip(),
            file=rel,
            line=line,
            end_line=end_line,
            code=code,
            function=function,
            fingerprint="",
            context=snippet,
        ))
    return findings


def run_tool(target: Path) -> ToolRun:
    started = utcnow()
    version = bandit_version()
    findings = run_bandit(target)
    return ToolRun(tool="bandit", version=version, started=started, finished=utcnow(), findings=findings)
