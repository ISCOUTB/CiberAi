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
from agente_seguridad.owasp import categoria, etiqueta, nombre, normalizar
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

    def test_owasp_property_and_tags(self):
        f = with_ids([make_finding(cwe="CWE-78", owasp="A03")])[0]
        doc = to_sarif([f], "C:/repo")
        rule = doc["runs"][0]["tool"]["driver"]["rules"][0]
        result = doc["runs"][0]["results"][0]
        self.assertEqual(result["properties"]["owasp"], "A03")
        self.assertEqual(rule["properties"]["owasp"], "A03")
        self.assertIn("OWASP-A03", rule["properties"]["tags"])
        self.assertIn("CWE-78", rule["properties"]["tags"])

    def test_missing_owasp_is_sin_categoria(self):
        f = with_ids([make_finding(cwe="CWE-703")])[0]
        doc = to_sarif([f], "C:/repo")
        self.assertEqual(doc["runs"][0]["results"][0]["properties"]["owasp"], "sin_categoria")
        self.assertIn("OWASP-sin_categoria",
                      doc["runs"][0]["tool"]["driver"]["rules"][0]["properties"]["tags"])


class OwaspTests(unittest.TestCase):
    def test_normaliza_formas_de_cwe(self):
        self.assertEqual(normalizar("CWE-89"), "CWE-89")
        self.assertEqual(normalizar("89"), "CWE-89")
        self.assertEqual(normalizar(" cwe-78 "), "CWE-78")
        self.assertIsNone(normalizar("Ninguno"))
        self.assertIsNone(normalizar(None))

    def test_mapeo_oficial(self):
        self.assertEqual(categoria("CWE-89"), "A03")
        self.assertEqual(categoria("CWE-502"), "A08")
        self.assertEqual(categoria("CWE-377"), "A01")  # miembro obsoleto de A01
        self.assertIsNone(categoria("CWE-703"))

    def test_etiqueta_fuera_del_top_10(self):
        self.assertEqual(etiqueta("CWE-703"), "sin_categoria")
        self.assertEqual(etiqueta("CWE-89"), "A03")

    def test_nombre_legible(self):
        self.assertEqual(nombre("A03"), "Injection")
        self.assertEqual(nombre("sin_categoria"), "Fuera del Top 10 2021")

    def test_reporte_agrupa_por_owasp(self):
        findings = with_ids([
            make_finding(cwe="CWE-89", owasp="A03"),
            make_finding(line=11, cwe="CWE-78", owasp="A03"),
            make_finding(line=12, cwe="CWE-703", owasp="sin_categoria"),
        ])
        data = summary(type("S", (), {"findings": findings}))
        self.assertEqual(data["por_owasp"], {"A03": 2, "sin_categoria": 1})
        self.assertEqual(data["owasp_nombres"]["A03"], "Injection")
        self.assertEqual(data["owasp_nombres"]["sin_categoria"], "Fuera del Top 10 2021")

    def test_reporte_sin_campo_usa_sin_categoria(self):
        f = with_ids([make_finding(cwe="CWE-703")])[0]
        f.owasp = ""
        data = summary(type("S", (), {"findings": [f]}))
        self.assertEqual(data["por_owasp"], {"sin_categoria": 1})


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

    def test_owasp_derivado_del_cwe_del_sast(self):
        findings = run_bandit(SAMPLE.parent)
        por_regla = {f.rule_id: f.owasp for f in findings}
        self.assertEqual(por_regla["B608"], "A03")  # CWE-89 Injection
        self.assertEqual(por_regla["B301"], "A08")  # CWE-502 deserializacion
        self.assertEqual(por_regla["B324"], "A02")  # CWE-327 criptografia debil
        self.assertEqual(por_regla["B105"], "A07")  # CWE-259 credencial embebida
        self.assertEqual(por_regla["B101"], "sin_categoria")  # CWE-703 fuera del Top 10


if __name__ == "__main__":
    unittest.main()
