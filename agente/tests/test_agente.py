import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agente_seguridad.context import extract_context
from agente_seguridad.dedup import deduplicate, with_ids
from agente_seguridad.llm.ollama_client import OllamaClient
from agente_seguridad.models import Finding
from agente_seguridad.report import summary
from agente_seguridad.sast.bandit_runner import run_bandit
from agente_seguridad.sast.sarif import to_sarif
from agente_seguridad.triage import parse_response, triage_findings

SAMPLE = ROOT / "examples" / "sample_repo" / "vuln.py"


def make_finding(**kw):
    base = dict(finding_id="", rule_id="B608", cwe="CWE-89", severity="media",
                confidence="MEDIUM", message="sql", file="a.py", line=10, end_line=10,
                code="x", function="f", fingerprint="")
    base.update(kw)
    return Finding(**base)


class ContextTests(unittest.TestCase):
    def test_extract_enclosing_function(self):
        snippet, name = extract_context(str(SAMPLE), 9)
        self.assertEqual(name, "login")
        self.assertIn("admin123", snippet)

    def test_fallback_outside_function(self):
        snippet, name = extract_context(str(SAMPLE), 1)
        self.assertIn(name, {"<sin_ast>", "<modulo>"})
        self.assertTrue(snippet)


class DedupTests(unittest.TestCase):
    def test_same_key_collapses(self):
        items = with_ids([make_finding(), make_finding(), make_finding(line=11)])
        self.assertEqual(len(deduplicate(items)), 2)

    def test_ids_are_deterministic(self):
        a = with_ids([make_finding()])[0]
        b = with_ids([make_finding()])[0]
        self.assertEqual(a.finding_id, b.finding_id)
        self.assertEqual(len(a.finding_id), 16)


class SarifTests(unittest.TestCase):
    def test_structure(self):
        f = with_ids([make_finding()])[0]
        doc = to_sarif([f], "C:/repo")
        self.assertEqual(doc["version"], "2.1.0")
        result = doc["runs"][0]["results"][0]
        self.assertEqual(result["ruleId"], "B608")
        self.assertEqual(result["locations"][0]["physicalLocation"]["region"]["startLine"], 10)


class TriageTests(unittest.TestCase):
    def test_valid_json(self):
        raw = '{"veredicto":"VULNERABLE","cwe":"CWE-89","severidad":"Alta","explicacion":"x","vector_ataque":"y","correccion":"z"}'
        result = parse_response(raw, make_finding())
        self.assertTrue(result.valido)
        self.assertEqual(result.veredicto, "VULNERABLE")

    def test_invalid_verdict_is_suspicious(self):
        result = parse_response('{"veredicto":"TAL VEZ"}', make_finding())
        self.assertFalse(result.valido)
        self.assertEqual(result.veredicto, "SOSPECHOSA")

    def test_bad_json_is_suspicious(self):
        result = parse_response("no es json", make_finding())
        self.assertEqual(result.veredicto, "SOSPECHOSA")

    def test_no_client_keeps_alerts(self):
        findings = with_ids([make_finding()])
        triage_findings(findings, None)
        self.assertEqual(findings[0].triage["veredicto"], "SOSPECHOSA")
        self.assertEqual(summary(type("S", (), {"findings": findings}))["conservadas"], 1)

    def test_safe_is_kept_and_only_recommended(self):
        findings = with_ids([make_finding()])
        findings[0].triage = {"veredicto": "SAFE", "explicacion": "falso positivo"}
        data = summary(type("S", (), {"findings": findings}))
        self.assertEqual(data["conservadas"], 1)
        self.assertEqual(data["recomendadas_descarte"], 1)

    def test_never_discard_rule_overrides_safe(self):
        raw = '{"veredicto":"SAFE","cwe":"Ninguno","severidad":"Info","explicacion":"solo importa","vector_ataque":"N/A","correccion":"N/A"}'
        finding = make_finding(rule_id="B403", cwe="CWE-502")
        result = parse_response(raw, finding)
        self.assertTrue(result.valido)
        self.assertEqual(result.veredicto, "SOSPECHOSA")
        self.assertEqual(result.origen, "politica_seguridad")
        self.assertIn("B403", result.explicacion)


class OllamaClientTests(unittest.TestCase):
    def test_generation_is_bounded(self):
        class FakeResponse:
            status_code = 200

            def json(self):
                return {"response": "{}"}

        with patch("agente_seguridad.llm.ollama_client.requests.post",
                   return_value=FakeResponse()) as post:
            OllamaClient(model="m").generate("prompt", system="sistema")

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["options"]["temperature"], 0)
        self.assertEqual(payload["options"]["num_predict"], 512)


class BanditTests(unittest.TestCase):
    def test_scan_sample(self):
        findings = run_bandit(SAMPLE.parent)
        self.assertGreaterEqual(len(findings), 4)
        rules = {f.rule_id for f in findings}
        self.assertTrue({"B105", "B608", "B303", "B301"} & rules)


if __name__ == "__main__":
    unittest.main()
