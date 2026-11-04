import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .dedup import deduplicate, with_ids
from .llm.ollama_client import OllamaClient
from .models import Scan
from .report import console, write_outputs
from .sast.bandit_runner import run_tool
from .triage import DEFAULT_NEVER_DISCARD, triage_findings


def _scan_id(target: str) -> str:
    raw = "{}|{}".format(target, datetime.now(timezone.utc).isoformat())
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agente-seguridad", description="Triage de alertas SAST con un modelo local")
    parser.add_argument("--version", action="version", version="agente-seguridad " + __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Analiza un directorio o repositorio")
    scan.add_argument("target", help="Ruta del directorio a analizar")
    scan.add_argument("--out", default="reportes", help="Directorio de salida (por defecto: reportes)")
    scan.add_argument("--model", default="qwen2.5-coder:1.5b", help="Modelo de Ollama")
    scan.add_argument("--ollama-url", default="http://localhost:11434", help="URL base de Ollama")
    scan.add_argument("--no-llm", action="store_true", help="Solo SAST, sin invocar al modelo")
    scan.add_argument("--max-alerts", type=int, default=0, help="Limite de alertas a triagear (0 = todas)")
    scan.add_argument("--never-discard", nargs="*", default=sorted(DEFAULT_NEVER_DISCARD),
                      help="Reglas del SAST que nunca deben ser recomendadas para descarte (por defecto: B403)")
    scan.add_argument("--quiet", action="store_true", help="No imprimir el detalle en consola")
    return parser


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = build_parser().parse_args(argv)
    target = Path(args.target)
    if not target.exists():
        print("Error: la ruta no existe: {}".format(target), file=sys.stderr)
        return 2

    scan = Scan(scan_id=_scan_id(str(target.resolve())), target=str(target.resolve()),
                created=datetime.now(timezone.utc).isoformat())

    print("Ejecutando Bandit sobre {}...".format(target))
    try:
        tool_run = run_tool(target)
    except Exception as exc:
        print("Error al ejecutar el SAST: {}".format(exc), file=sys.stderr)
        return 3
    scan.tool_runs.append(tool_run)

    findings = with_ids(tool_run.findings)
    findings = deduplicate(findings)
    tool_run.findings = findings
    print("Alertas del SAST: {} (tras deduplicar: {})".format(len(tool_run.findings), len(findings)))

    client = None
    if not args.no_llm:
        client = OllamaClient(base_url=args.ollama_url, model=args.model)
        if not client.is_available():
            print("Aviso: Ollama no responde en {}. Se aplicara la politica conservadora.".format(args.ollama_url))

    if args.max_alerts and len(findings) > args.max_alerts:
        findings = findings[:args.max_alerts]
        tool_run.findings = findings

    never_discard = set(args.never_discard) if args.never_discard else set()
    errors = triage_findings(findings, client, never_discard=never_discard)
    if errors:
        print("Aviso: {} alertas sin respuesta valida del modelo (se conservan como SOSPECHOSA).".format(errors))

    out_dir = Path(args.out)
    paths = write_outputs(scan, out_dir)
    if not args.quiet:
        print(console(scan))
    print("\nReporte JSON: {}".format(paths["json"]))
    print("Reporte SARIF: {}".format(paths["sarif"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
