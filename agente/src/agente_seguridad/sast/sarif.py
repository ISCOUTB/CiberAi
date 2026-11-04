from typing import Any, Dict, List

from ..models import Finding

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
LEVEL = {"alta": "error", "media": "warning", "baja": "note"}


def to_sarif(findings: List[Finding], target: str) -> Dict[str, Any]:
    rules: Dict[str, Dict[str, Any]] = {}
    results: List[Dict[str, Any]] = []
    for f in findings:
        if f.rule_id not in rules:
            rules[f.rule_id] = {
                "id": f.rule_id or "BANDIT",
                "name": f.rule_id or "BANDIT",
                "shortDescription": {"text": f.cwe},
                "properties": {"cwe": f.cwe},
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
                    "name": "bandit",
                    "informationUri": "https://bandit.readthedocs.io",
                    "rules": list(rules.values()),
                }
            },
            "originalUriBaseIds": {"SRCROOT": {"uri": target}},
            "results": results,
        }],
    }
