from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SEVERITY_MAP = {"LOW": "baja", "MEDIUM": "media", "HIGH": "alta"}
VERDICTS = {"VULNERABLE", "SAFE", "SOSPECHOSA"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Finding:
    finding_id: str
    rule_id: str
    cwe: str
    severity: str
    confidence: str
    message: str
    file: str
    line: int
    end_line: int
    code: str
    function: str
    fingerprint: str
    owasp: str = ""
    context: Optional[str] = None
    triage: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolRun:
    tool: str
    version: str
    started: str
    finished: str
    findings: List[Finding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "version": self.version,
            "started": self.started,
            "finished": self.finished,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class Scan:
    scan_id: str
    target: str
    created: str
    tool_runs: List[ToolRun] = field(default_factory=list)

    @property
    def findings(self) -> List[Finding]:
        out: List[Finding] = []
        for run in self.tool_runs:
            out.extend(run.findings)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "target": self.target,
            "created": self.created,
            "tool_runs": [r.to_dict() for r in self.tool_runs],
        }


@dataclass
class TriageResult:
    finding_id: str
    veredicto: str
    cwe: str
    severidad: str
    explicacion: str
    vector_ataque: str
    correccion: str
    origen: str
    valido: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
