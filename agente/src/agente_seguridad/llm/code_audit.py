"""Auditoria directa de codigo con el modelo, sin alerta de una herramienta SAST.

Este modulo implementa el modo "modelo primero": el LLM lee fragmentos de codigo
Python y decide por si mismo si contienen una vulnerabilidad. Los fragmentos se
construyen a partir de las funciones del archivo, de modo que el prompt se parece
al corpus de entrenamiento (``<code_snippet>``) y no a una alerta de Bandit.

La categoria OWASP no se toma de la respuesta del modelo: se calcula con
``owasp.etiqueta`` a partir del CWE que el modelo declara. Un CWE ausente o no
numerico invalida la respuesta; no se inventa un hallazgo sin CWE.
"""

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

from ..models import Finding, ToolRun, utcnow
from ..owasp import etiqueta as owasp_etiqueta
from ..owasp import normalizar
from .ollama_client import OllamaClient, OllamaError

TOOL_NAME = "llm-audit"
TOOL_VERSION = "1.0"
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
             "env", ".tox", ".mypy_cache", ".pytest_cache", "build", "dist",
             "site-packages", "reportes"}
SUPPORTED_SUFFIXES = {".py"}
DEFAULT_MAX_CHARS = 6000

SYSTEM = (
    "Eres un analista de seguridad de software. Analizas un fragmento de codigo y decides "
    "si contiene una vulnerabilidad real (VULNERABLE) o si es seguro (SAFE). Responde SOLO "
    "con un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, vector_ataque, correccion."
)

TEMPLATE = (
    "Analiza el siguiente fragmento de codigo en {language}.\n\n"
    "<code_snippet>\n{code}\n</code_snippet>\n"
)

VALID_VERDICTS = {"VULNERABLE", "SAFE"}
VALID_SEVERITIES = {"Alta", "Media", "Baja", "Info"}


@dataclass
class CodeChunk:
    file: str
    line: int
    end_line: int
    function: str
    language: str
    code: str


def build_prompt(code: str, language: str = "Python") -> str:
    return TEMPLATE.format(language=language, code=code)


def _clean_json(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return text


def parse_audit_response(raw: str) -> Optional[dict]:
    """Convierte la respuesta del modelo en un dict validado o ``None``.

    Solo devuelve un dict cuando el veredicto es valido y, si es VULNERABLE,
    cuando el CWE se puede normalizar. ``None`` significa que el fragmento no
    produce hallazgo (respuesta invalida o SAFE sin datos utilizables).
    """
    try:
        data = json.loads(_clean_json(raw))
    except json.JSONDecodeError:
        return None

    verdict = str(data.get("veredicto", "")).strip().upper()
    if verdict not in VALID_VERDICTS:
        return None

    explanation = str(data.get("explicacion", "")).strip()
    vector = str(data.get("vector_ataque", "N/A")).strip() or "N/A"
    correction = str(data.get("correccion", "N/A")).strip() or "N/A"

    if verdict == "SAFE":
        return {
            "veredicto": "SAFE",
            "cwe": "Ninguno",
            "severidad": "Info",
            "explicacion": explanation or "El fragmento no presenta un patron vulnerable.",
            "vector_ataque": "N/A",
            "correccion": "N/A",
            "valido": True,
        }

    cwe = normalizar(data.get("cwe"))
    if cwe is None:
        return None

    severity = str(data.get("severidad", "")).strip().capitalize()
    if severity not in VALID_SEVERITIES:
        severity = "Media"

    return {
        "veredicto": "VULNERABLE",
        "cwe": cwe,
        "severidad": severity,
        "explicacion": explanation or "El fragmento presenta un patron asociado a {}.".format(cwe),
        "vector_ataque": vector,
        "correccion": correction,
        "valido": True,
    }


def classify_code(client: OllamaClient, code: str, language: str = "Python") -> Optional[dict]:
    raw = client.generate(build_prompt(code, language), system=SYSTEM)
    return parse_audit_response(raw)


def _rel(path: Path, target: Path) -> str:
    if target.is_file():
        return path.name
    try:
        return path.relative_to(target).as_posix()
    except ValueError:
        return path.name


def _iter_python_files(target: Path) -> Iterable[Path]:
    if target.is_file():
        if target.suffix.lower() in SUPPORTED_SUFFIXES:
            yield target
        return
    for path in sorted(target.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def _windows(code: str, start_line: int, max_chars: int, overlap: int = 5) -> Iterator[CodeChunk]:
    """Divide un fragmento largo en ventanas de lineas con solapamiento."""
    lines = code.splitlines()
    if not lines:
        return
    start = start_line
    index = 0
    while index < len(lines):
        buffer: List[str] = []
        size = 0
        while index < len(lines):
            line = lines[index]
            extra = len(line) + 1
            if buffer and size + extra > max_chars:
                break
            buffer.append(line)
            size += extra
            index += 1
        if buffer:
            yield CodeChunk(
                file="", line=start, end_line=start + len(buffer) - 1,
                function="", language="Python", code="\n".join(buffer),
            )
        if index >= len(lines):
            break
        # Retroceder como maximo len(buffer)-1 lineas garantiza que la ventana
        # siguiente consume al menos una linea nueva; si no, una linea enorme
        # podria dejar index sin avanzar y provocar un bucle infinito.
        backtrack = min(overlap, max(0, len(buffer) - 1))
        keep = buffer[-backtrack:] if backtrack else []
        start = start + len(buffer) - len(keep)
        index -= len(keep)


def _function_chunks(source: str, max_chars: int) -> Iterator[CodeChunk]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        yield CodeChunk(file="", line=1, end_line=max(1, source.count("\n") + 1),
                        function="<sin_ast>", language="Python",
                        code=source[:max_chars])
        return

    functions = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    functions.sort(key=lambda node: (getattr(node, "lineno", 1),
                                     -getattr(node, "end_lineno", 1) or -1))

    selected = []
    spans = []
    for node in functions:
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start) or start
        if any(a <= start and end <= b for a, b in spans):
            continue
        spans.append((start, end))
        selected.append((start, end, getattr(node, "name", "<anonimo>"), node))

    selected.sort(key=lambda item: item[0])
    for start, end, name, node in selected:
        segment = ast.get_source_segment(source, node) or ""
        for chunk in _windows(segment, start, max_chars):
            chunk.function = name
            yield chunk

    source_lines = source.splitlines()
    covered = [False] * (len(source_lines) + 2)
    for start, end, _, _ in selected:
        for line in range(max(1, start), min(len(source_lines), end) + 1):
            covered[line] = True

    module_lines = []
    for number, text in enumerate(source_lines, 1):
        if not covered[number]:
            module_lines.append((number, text))
    if module_lines:
        first_line = module_lines[0][0]
        text = "\n".join(line for _, line in module_lines)
        meaningful = [line for _, line in module_lines
                      if line.strip() and not line.lstrip().startswith(("class ", "def ", "async def ", "@"))]
        if meaningful:
            for chunk in _windows(text, first_line, max_chars):
                chunk.function = "<modulo>"
                yield chunk


def iter_chunks(target: Path, max_chars: int = DEFAULT_MAX_CHARS) -> Iterator[CodeChunk]:
    for path in _iter_python_files(target):
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = _rel(path, target)
        for chunk in _function_chunks(source, max_chars):
            chunk.file = rel
            yield chunk


def _finding(chunk: CodeChunk, data: dict) -> Finding:
    cwe = data["cwe"]
    explanation = data["explicacion"]
    severity = data["severidad"]
    return Finding(
        finding_id="", rule_id="LLM-{}".format(cwe), cwe=cwe,
        severity=severity.lower(), confidence="MEDIUM",
        message="El modelo detecta {}: {}".format(cwe, explanation[:200]),
        file=chunk.file, line=chunk.line, end_line=chunk.end_line,
        code=chunk.code.strip()[:500], function=chunk.function or "<modulo>",
        fingerprint="", owasp=owasp_etiqueta(cwe), context=chunk.code,
        triage={
            "finding_id": "",
            "veredicto": "VULNERABLE",
            "cwe": cwe,
            "severidad": severity,
            "explicacion": explanation,
            "vector_ataque": data["vector_ataque"],
            "correccion": data["correccion"],
            "origen": "llm_audit",
            "valido": True,
        },
    )


def run_llm_audit(target: Path, client: OllamaClient, max_chars: int = DEFAULT_MAX_CHARS,
                  max_chunks: int = 0) -> ToolRun:
    """Recorre el codigo y construye hallazgos solo con las respuestas VULNERABLE."""
    target = Path(target)
    started = utcnow()
    findings: List[Finding] = []
    analyzed = errors = 0
    for chunk in iter_chunks(target, max_chars=max_chars):
        if max_chunks and analyzed >= max_chunks:
            break
        analyzed += 1
        try:
            data = classify_code(client, chunk.code, chunk.language)
        except OllamaError:
            errors += 1
            continue
        if data is None:
            errors += 1
            continue
        if data["veredicto"] != "VULNERABLE":
            continue
        findings.append(_finding(chunk, data))
        if analyzed % 25 == 0:
            print("  ... {} fragmentos analizados por el modelo".format(analyzed))

    print("Auditoria LLM: {} fragmentos | {} hallazgos | {} respuestas invalidas".format(
        analyzed, len(findings), errors))
    return ToolRun(tool=TOOL_NAME, version=TOOL_VERSION, started=started,
                   finished=utcnow(), findings=findings)
