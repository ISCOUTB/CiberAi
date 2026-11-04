import ast
from pathlib import Path
from typing import Optional, Tuple


def _enclosing_function(tree: ast.AST, line: int) -> Optional[ast.AST]:
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", 0) or start
            if start <= line <= end:
                if best is None or start >= getattr(best, "lineno", 0):
                    best = node
    return best


def extract_context(path: str, line: int, fallback: int = 20, max_chars: int = 8000) -> Tuple[str, str]:
    p = Path(path)
    try:
        source = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", "<archivo>"

    try:
        tree = ast.parse(source)
    except SyntaxError:
        lines = source.splitlines()
        start = max(1, line - fallback)
        end = min(len(lines), line + fallback)
        return "\n".join(lines[start - 1:end]), "<sin_ast>"

    node = _enclosing_function(tree, line)
    if node is None:
        lines = source.splitlines()
        start = max(1, line - fallback)
        end = min(len(lines), line + fallback)
        return "\n".join(lines[start - 1:end]), "<modulo>"

    name = getattr(node, "name", "<anonimo>")
    segment = ast.get_source_segment(source, node) or ""
    if len(segment) > max_chars:
        segment = segment[:max_chars] + "\n# ... (truncado)"
    return segment, name
