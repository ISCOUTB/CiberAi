import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente_seguridad.models import Scan, ToolRun, utcnow
from agente_seguridad.report import write_outputs
from agente_seguridad.sast.report_loader import load_tool_runs


def make_finding(cwe="CWE-89"):
    from agente_seguridad.models import Finding
    return Finding(
        finding_id="abc",
        rule_id="B608",
        cwe=cwe,
        severity="media",
        confidence="HIGH",
        message="test",
        file="a.py",
        line=10,
        end_line=10,
        code="x",
        function="f",
        fingerprint="fp",
        owasp="A03",
        context="",
    )


class ReportLoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_report(self):
        finding = make_finding()
        scan = Scan(
            scan_id="t",
            target=str(ROOT),
            created=utcnow(),
            tool_runs=[
                ToolRun(tool="owasp", version="1.0", started=utcnow(), finished=utcnow(), findings=[finding])
            ],
        )
        write_outputs(scan, self.out)

    def test_load_own_json_report(self):
        self._write_report()
        runs = load_tool_runs(self.out / "reporte.json", target=ROOT)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].tool, "owasp")
        finding = runs[0].findings[0]
        self.assertEqual(finding.rule_id, "B608")
        self.assertEqual(finding.cwe, "CWE-89")
        self.assertEqual(finding.owasp, "A03")
        self.assertEqual(finding.line, 10)

    def test_load_sarif(self):
        self._write_report()
        runs = load_tool_runs(self.out / "hallazgos.sarif", target=ROOT)
        finding = runs[0].findings[0]
        self.assertEqual(finding.rule_id, "B608")
        self.assertEqual(finding.cwe, "CWE-89")
        self.assertEqual(finding.owasp, "A03")

    def test_load_bandit_json(self):
        raw = {
            "results": [{
                "filename": "a.py",
                "line_number": 9,
                "test_id": "B608",
                "issue_cwe": {"id": 89},
                "issue_severity": "MEDIUM",
                "issue_confidence": "MEDIUM",
                "issue_text": "sql",
                "code": "x",
            }]
        }
        path = self.out / "bandit.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        runs = load_tool_runs(path, target=self.out)
        self.assertEqual(runs[0].tool, "bandit")
        self.assertEqual(runs[0].findings[0].cwe, "CWE-89")


if __name__ == "__main__":
    unittest.main()
