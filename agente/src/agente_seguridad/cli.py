import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .dedup import deduplicate, with_ids
from .llm.code_audit import DEFAULT_MAX_CHARS, run_llm_audit
from .llm.ollama_client import OllamaClient
from .models import Scan
from .report import console, write_outputs
from .sast.bandit_runner import run_tool as run_bandit_tool
from .sast.owasp_runner import run_owasp_tool
from .sast.report_loader import load_tool_runs
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
    scan.add_argument("--scanner", choices=["both", "bandit", "owasp", "llm", "all"],
                      default="both",
                      help="Motores: both (Bandit+OWASP, por defecto), bandit, owasp, "
                           "llm (solo auditoria del modelo) o all (LLM primero y luego SAST)")
    scan.add_argument("--from-report", metavar="ARCHIVO",
                      help="Cargar hallazgos de un reporte JSON/SARIF existente en lugar de ejecutar el SAST")
    scan.add_argument("--audit-max-chars", type=int, default=DEFAULT_MAX_CHARS,
                      help="Tamano maximo de cada fragmento para la auditoria LLM")
    scan.add_argument("--audit-max-chunks", type=int, default=0,
                      help="Limite de fragmentos para la auditoria LLM (0 = todos)")
    scan.add_argument("--max-alerts", type=int, default=0, help="Limite de alertas a triagear (0 = todas)")
    scan.add_argument("--never-discard", nargs="*", default=sorted(DEFAULT_NEVER_DISCARD),
                      help="Reglas del SAST que nunca deben ser recomendadas para descarte (por defecto: B403)")
    scan.add_argument("--quiet", action="store_true", help="No imprimir el detalle en consola")
    scan.add_argument("--no-color", action="store_true",
                      help="Desactiva los colores ANSI en la salida de consola")
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

    llm_audit = args.scanner in ("llm", "all")
    if llm_audit and args.no_llm:
        print("Error: --scanner {} requiere el modelo; quita --no-llm.".format(args.scanner),
              file=sys.stderr)
        return 2

    client = None
    if not args.no_llm:
        client = OllamaClient(base_url=args.ollama_url, model=args.model)
        if not client.is_available():
            if llm_audit:
                print("Error: Ollama no responde en {}; la auditoria LLM lo necesita.".format(
                    args.ollama_url), file=sys.stderr)
                return 4
            print("Aviso: Ollama no responde en {}. Se aplicara la politica conservadora.".format(args.ollama_url))

    if args.from_report:
        print("Cargando hallazgos desde {}...".format(args.from_report))
        try:
            scan.tool_runs.extend(load_tool_runs(Path(args.from_report), target=target))
        except ValueError as exc:
            print("Error al cargar el reporte: {}".format(exc), file=sys.stderr)
            return 4
    else:
        llm_audit = args.scanner in ("llm", "all")
        if llm_audit and args.no_llm:
            print("Error: --scanner {} requiere el modelo; quita --no-llm.".format(args.scanner),
                  file=sys.stderr)
            return 2

        # El modo "modelo primero" se ejecuta antes que Bandit y el escaner OWASP:
        # el LLM lee el codigo sin conocer las alertas de las herramientas.
        if llm_audit:
            print("Ejecutando auditoria LLM (modelo primero) sobre {}...".format(target))
            try:
                tool_run = run_llm_audit(target, client, max_chars=args.audit_max_chars,
                                         max_chunks=args.audit_max_chunks)
            except Exception as exc:
                print("Error al ejecutar la auditoria LLM: {}".format(exc), file=sys.stderr)
                return 4
            raw = len(tool_run.findings)
            tool_run.findings = deduplicate(with_ids(tool_run.findings))
            print("Hallazgos de llm-audit: {} (tras deduplicar: {})".format(raw, len(tool_run.findings)))
            scan.tool_runs.append(tool_run)

        runners = []
        if args.scanner in ("both", "bandit", "all"):
            runners.append(("Bandit", run_bandit_tool))
        if args.scanner in ("both", "owasp", "all"):
            runners.append(("OWASP", run_owasp_tool))

        for label, runner in runners:
            print("Ejecutando {} sobre {}...".format(label, target))
            try:
                tool_run = runner(target)
            except Exception as exc:
                print("Error al ejecutar {}: {}".format(label, exc), file=sys.stderr)
                continue
            raw = len(tool_run.findings)
            tool_run.findings = deduplicate(with_ids(tool_run.findings))
            print("Alertas de {}: {} (tras deduplicar: {})".format(label, raw, len(tool_run.findings)))
            scan.tool_runs.append(tool_run)

    if not scan.tool_runs:
        return 3

    findings = scan.findings

    if args.max_alerts:
        remaining = args.max_alerts
        for tool_run in scan.tool_runs:
            tool_run.findings = tool_run.findings[:max(0, remaining)]
            remaining -= len(tool_run.findings)
        findings = scan.findings

    never_discard = set(args.never_discard) if args.never_discard else set()
    errors = triage_findings(findings, client, never_discard=never_discard)
    if errors:
        print("Aviso: {} alertas sin respuesta valida del modelo (se conservan como SOSPECHOSA).".format(errors))

    out_dir = Path(args.out)
    paths = write_outputs(scan, out_dir)
    if not args.quiet:
        print(console(scan, no_color=args.no_color))
    print("\nReporte JSON: {}".format(paths["json"]))
    print("Reporte SARIF: {}".format(paths["sarif"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
