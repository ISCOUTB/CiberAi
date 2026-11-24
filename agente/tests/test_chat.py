import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

AGENTE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENTE))
sys.path.insert(0, str(AGENTE / "src"))

import chat


class ChatTests(unittest.TestCase):
    def test_tokenize_windows_paths_and_quotes(self):
        self.assertEqual(
            chat.tokenize(r"scan agente\examples\sample_repo --scanner owasp"),
            ["scan", r"agente\examples\sample_repo", "--scanner", "owasp"],
        )
        self.assertEqual(
            chat.tokenize('scan "C:\\Program Files\\repo"'),
            ["scan", "C:\\Program Files\\repo"],
        )

    def test_build_scan_args_adds_defaults(self):
        session = chat.Session(runner=lambda argv: 0)
        args = session.build_scan_args(["agente/examples/sample_repo", "--no-llm"])
        self.assertEqual(args[:2], ["scan", "agente/examples/sample_repo"])
        self.assertIn("--scanner", args)
        self.assertIn("both", args)
        self.assertNotIn("--model", args)
        self.assertIn("--out", args)
        self.assertEqual(session.last_out, Path("reportes"))

    def test_build_scan_args_respects_overrides_and_reuses_target(self):
        session = chat.Session(runner=lambda argv: 0)
        args = session.build_scan_args([
            ".", "--scanner", "owasp", "--model", "m", "--out", "tmp",
        ])
        self.assertEqual(args.count("--scanner"), 1)
        self.assertIn("owasp", args)
        self.assertIn("m", args)
        self.assertIn("tmp", args)
        again = session.build_scan_args([])
        self.assertEqual(again[1], ".")

    def test_scan_and_report_commands(self):
        calls = []

        def fake_runner(argv):
            calls.append(argv)
            return 0

        session = chat.Session(runner=fake_runner)
        with tempfile.TemporaryDirectory() as tmp:
            session.out = Path(tmp)
            chat.handle_line(session, "scan agente/examples/sample_repo --no-llm", io.StringIO().write)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], "agente/examples/sample_repo")

            payload = {
                "scan": {"scan_id": "abc", "target": "demo"},
                "resumen": {
                    "total": 2, "conservadas": 2, "recomendadas_descarte": 0,
                    "sospechosas": 2, "errores_modelo": 2,
                    "por_herramienta": {"bandit": 2}, "por_owasp": {"A03": 2},
                },
            }
            (session.out / "reporte.json").write_text(
                json.dumps(payload), encoding="utf-8")

            out = io.StringIO()
            chat.handle_line(session, "report", out.write)
            self.assertIn("abc", out.getvalue())
            self.assertIn("Herramientas: bandit=2", out.getvalue())
            self.assertIn("OWASP Top 10 2021: A03=2", out.getvalue())

    def test_settings_help_and_exit(self):
        session = chat.Session(runner=lambda argv: 0)
        out = io.StringIO()
        self.assertTrue(chat.handle_line(session, "help", out.write))
        self.assertIn("scan <ruta>", out.getvalue())

        out = io.StringIO()
        chat.handle_line(session, "scanner owasp", out.write)
        self.assertEqual(session.scanner, "owasp")
        chat.handle_line(session, "model qwen2.5-coder:1.5b", out.write)
        self.assertEqual(session.model, "qwen2.5-coder:1.5b")
        chat.handle_line(session, "scanner nope", out.write)
        self.assertEqual(session.scanner, "owasp")

        out = io.StringIO()
        self.assertTrue(chat.handle_line(session, "nope", out.write))
        self.assertIn("no reconocido", out.getvalue())

        out = io.StringIO()
        self.assertFalse(chat.handle_line(session, "exit", out.write))


if __name__ == "__main__":
    unittest.main()
