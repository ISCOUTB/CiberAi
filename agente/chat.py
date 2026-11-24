"""Interfaz interactiva de terminal para la CLI del agente.

Uso:
    python agente/chat.py

Los comandos ``scan`` reutilizan exactamente el mismo codigo que
``python agente/run.py scan ...``; esta capa solo evita tener que repetir el
comando completo y permite consultar el ultimo reporte sin salir.
"""

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Callable, List, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agente_seguridad import __version__
from agente_seguridad.cli import main as cli_main

SCANNERS = ("both", "bandit", "owasp", "llm", "all")

HELP = """Comandos disponibles:
  scan <ruta> [flags]   Escanea una ruta (aniade --scanner/--model/--out si faltan)
  rescan                Repite el ultimo escaneo
  report                Muestra el resumen del ultimo reporte.json
  open                  Muestra las rutas del ultimo JSON y SARIF
  scanner [nombre]      Muestra o cambia el escaner por defecto
  model [nombre]        Muestra o cambia el modelo por defecto
  out [directorio]      Muestra o cambia el directorio de salida
  help                  Muestra esta ayuda
  clear                 Limpia la pantalla
  exit                  Sale de la interfaz

Escaneres: both (por defecto), bandit, owasp, llm, all.
Ejemplos:
  scan agente/examples/sample_repo --scanner owasp --no-llm
  scan . --scanner llm --audit-max-chunks 5
  report

Nota: el agente es asesor. Un SAFE solo recomienda descartar; nunca elimina
la alerta del reporte."""


def tokenize(line: str) -> List[str]:
    """Divide una linea respetando comillas y barras invertidas de Windows."""
    parts = shlex.split(line, posix=False)
    cleaned = []
    for part in parts:
        if len(part) >= 2 and part[0] == part[-1] and part[0] in ("'", '"'):
            part = part[1:-1]
        cleaned.append(part)
    return cleaned


def out_from_args(args: List[str]) -> Path:
    if "--out" in args:
        index = args.index("--out")
        if index + 1 < len(args):
            return Path(args[index + 1])
    for arg in args:
        if arg.startswith("--out="):
            return Path(arg.split("=", 1)[1])
    return Path("reportes")


def format_report(session: "Session") -> str:
    path = (session.last_out or session.out) / "reporte.json"
    if not path.is_file():
        return "No hay reporte todavia. Ejecuta `scan <ruta>` primero."

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "No se pudo leer {}: {}".format(path, exc)

    summary = data.get("resumen") or {}
    scan = data.get("scan") or {}
    lines = [
        "Reporte: {}".format(path),
        "Escaneo: {} -> {}".format(scan.get("scan_id", "?"), scan.get("target", "?")),
        "Hallazgos: {total} | conservadas: {conservadas} | recomendadas para descarte: "
        "{recomendadas_descarte} | sospechosas: {sospechosas} | errores modelo: {errores_modelo}".format(
            total=summary.get("total", 0),
            conservadas=summary.get("conservadas", 0),
            recomendadas_descarte=summary.get("recomendadas_descarte", 0),
            sospechosas=summary.get("sospechosas", 0),
            errores_modelo=summary.get("errores_modelo", 0),
        ),
    ]
    por_herramienta = summary.get("por_herramienta") or {}
    if por_herramienta:
        lines.append("Herramientas: " + ", ".join(
            "{}={}".format(k, v) for k, v in sorted(por_herramienta.items())))
    por_owasp = summary.get("por_owasp") or {}
    if por_owasp:
        lines.append("OWASP Top 10 2021: " + ", ".join(
            "{}={}".format(k, v) for k, v in por_owasp.items()))
    lines.append("SARIF: {}".format((session.last_out or session.out) / "hallazgos.sarif"))
    return "\n".join(lines)


class Session:
    def __init__(self, runner: Callable[[List[str]], int] = cli_main):
        self.runner = runner
        self.model = "qwen2.5-coder:1.5b"
        self.scanner = "both"
        self.out = Path("reportes")
        self.last_target: Optional[str] = None
        self.last_args: List[str] = []
        self.last_out: Optional[Path] = None

    def build_scan_args(self, tokens: List[str]) -> Optional[List[str]]:
        if tokens and not tokens[0].startswith("-"):
            target, rest = tokens[0], tokens[1:]
        elif self.last_target:
            target, rest = self.last_target, tokens
        else:
            return None

        args = ["scan", target]
        if "--scanner" not in rest and not any(a.startswith("--scanner=") for a in rest):
            args += ["--scanner", self.scanner]
        if ("--model" not in rest and "--no-llm" not in rest
                and not any(a.startswith("--model=") for a in rest)):
            args += ["--model", self.model]
        if "--out" not in rest and not any(a.startswith("--out=") for a in rest):
            args += ["--out", str(self.out)]
        args += rest

        self.last_target = target
        self.last_args = args
        self.last_out = out_from_args(args)
        return args

    def run(self, args: List[str], emit: Callable[[str], None]) -> None:
        try:
            code = self.runner(args)
        except Exception as exc:
            emit("Error: {}".format(exc))
            return
        if code:
            emit("El escaneo termino con codigo {}.".format(code))


def handle_line(session: Session, line: str,
                emit: Callable[[str], None] = print) -> bool:
    """Procesa una linea. Devuelve False cuando se solicita salir."""
    tokens = tokenize(line.strip())
    if not tokens:
        return True

    command = tokens[0].lower()
    args = tokens[1:]

    if command in ("exit", "quit", "salir"):
        emit("Hasta luego.")
        return False
    if command in ("help", "?", "ayuda"):
        emit(HELP)
    elif command in ("clear", "cls"):
        emit("\n" * 40)
    elif command == "scanner":
        if not args:
            emit("Escaner actual: {}".format(session.scanner))
        elif args[0] in SCANNERS:
            session.scanner = args[0]
            emit("Escaner: {}".format(session.scanner))
        else:
            emit("Escaner desconocido. Opciones: {}".format(", ".join(SCANNERS)))
    elif command == "model":
        if not args:
            emit("Modelo actual: {}".format(session.model))
        else:
            session.model = args[0]
            emit("Modelo: {}".format(session.model))
    elif command == "out":
        if not args:
            emit("Salida actual: {}".format(session.out))
        else:
            session.out = Path(args[0])
            emit("Salida: {}".format(session.out))
    elif command == "scan":
        scan_args = session.build_scan_args(args)
        if scan_args is None:
            emit("Uso: scan <ruta> [flags]. Ejemplo: scan agente/examples/sample_repo")
        else:
            session.run(scan_args, emit)
    elif command == "rescan":
        if not session.last_args:
            emit("Todavia no hay un escaneo anterior.")
        else:
            emit("Repitiendo: {}".format(" ".join(str(a) for a in session.last_args)))
            session.run(session.last_args, emit)
    elif command in ("report", "resumen"):
        emit(format_report(session))
    elif command in ("open", "paths"):
        base = session.last_out or session.out
        emit("JSON: {}".format(base / "reporte.json"))
        emit("SARIF: {}".format(base / "hallazgos.sarif"))
    else:
        emit("Comando no reconocido: {}. Escribe `help` para ver las opciones.".format(command))
    return True


def main() -> int:
    session = Session()
    print("Analizador de codigo - interfaz interactiva v{}".format(__version__))
    print("Escribe `help` para ver los comandos. Modo asesor: SAFE nunca elimina alertas.")
    while True:
        try:
            line = input("agente> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not handle_line(session, line):
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
