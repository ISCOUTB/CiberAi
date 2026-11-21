from typing import Any, Dict, List

from ..models import Finding
from ..owasp import nombre as owasp_nombre

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
LEVEL = {"alta": "error", "media": "warning", "baja": "note"}


def _owasp(f: Finding) -> str:
    return f.owasp or "sin_categoria"


def _tags(f: Finding) -> List[str]:
    # SARIF usa `properties.tags` para la clasificacion; el prefijo `OWASP-`
    # permite filtrar por categoria en cualquier visor sin perder el CWE.
    tags = ["security", "owasp-top10-2021", "OWASP-{}".format(_owasp(f))]
    if f.cwe:
        tags.append(f.cwe)
    return tags


def to_sarif(findings: List[Finding], target: str) -> Dict[str, Any]:
    rules: Dict[str, Dict[str, Any]] = {}
    results: List[Dict[str, Any]] = []
    for f in findings:
        if f.rule_id not in rules:
            rules[f.rule_id] = {
                "id": f.rule_id or "BANDIT",
                "name": f.rule_id or "BANDIT",
                "shortDescription": {"text": "{} ({})".format(f.cwe, owasp_nombre(_owasp(f)))},
                "properties": {
                    "cwe": f.cwe,
                    "owasp": _owasp(f),
                    "tags": _tags(f),
                },
            }
        results.append({
            "ruleId": f.rule_id or "BANDIT",
            "level": LEVEL.get(f.severity, "warning"),
            "message": {"text": f.message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.file},
                    "region": {"startLine": f.line, "endLine": max(f.line, f.end_line)},
                }
            }],
            "partialFingerprints": {"findingId": f.finding_id},
            "properties": {
                "cwe": f.cwe,
                "owasp": _owasp(f),
                "severity": f.severity,
                "confidence": f.confidence,
                "function": f.function,
            },
        })
    return {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "agente-seguridad",
                    "informationUri": "https://owasp.org/Top10/",
                    "rules": list(rules.values()),
                }
            },
            "originalUriBaseIds": {"SRCROOT": {"uri": target}},
            "results": results,
        }],
    }
