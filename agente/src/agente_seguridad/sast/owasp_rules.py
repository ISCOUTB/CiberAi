"""Catalogo de reglas del escaner OWASP propio.

Cada regla declara el CWE que detecta. La categoria OWASP no se declara aqui:
se deriva del CWE con ``owasp.py``, igual que en las alertas de Bandit.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    rule_id: str
    cwe: str
    severity: str
    confidence: str
    title: str


RULES = {
    "OW-22": Rule("OW-22", "CWE-22", "alta", "MEDIUM", "Path traversal"),
    "OW-78": Rule("OW-78", "CWE-78", "alta", "HIGH", "Command injection"),
    "OW-79": Rule("OW-79", "CWE-79", "alta", "MEDIUM", "Cross-site scripting"),
    "OW-89": Rule("OW-89", "CWE-89", "alta", "HIGH", "SQL injection"),
    "OW-94": Rule("OW-94", "CWE-94", "alta", "HIGH", "Code injection"),
    "OW-200": Rule("OW-200", "CWE-200", "media", "MEDIUM", "Exposicion de informacion"),
    "OW-264": Rule("OW-264", "CWE-264", "media", "MEDIUM", "Permisos de archivo inseguros"),
    "OW-269": Rule("OW-269", "CWE-269", "media", "MEDIUM", "Gestion de privilegios insegura"),
    "OW-276": Rule("OW-276", "CWE-276", "media", "MEDIUM", "Permisos por defecto inseguros"),
    "OW-284": Rule("OW-284", "CWE-284", "alta", "LOW", "Control de acceso ausente"),
    "OW-287": Rule("OW-287", "CWE-287", "alta", "HIGH", "Autenticacion con secreto embebido"),
    "OW-310": Rule("OW-310", "CWE-310", "media", "MEDIUM", "Protocolo criptografico obsoleto"),
    "OW-327": Rule("OW-327", "CWE-327", "alta", "HIGH", "Criptografia debil"),
    "OW-330": Rule("OW-330", "CWE-330", "media", "MEDIUM", "Aleatoriedad debil"),
    "OW-352": Rule("OW-352", "CWE-352", "media", "HIGH", "Proteccion CSRF deshabilitada"),
    "OW-377": Rule("OW-377", "CWE-377", "media", "MEDIUM", "Archivo temporal inseguro"),
    "OW-434": Rule("OW-434", "CWE-434", "alta", "MEDIUM", "Carga de archivos sin restriccion"),
    "OW-502": Rule("OW-502", "CWE-502", "alta", "HIGH", "Deserializacion insegura"),
    "OW-601": Rule("OW-601", "CWE-601", "media", "MEDIUM", "Open redirect"),
    "OW-798": Rule("OW-798", "CWE-798", "alta", "HIGH", "Credenciales embebidas"),
    "OW-918": Rule("OW-918", "CWE-918", "alta", "MEDIUM", "Server-side request forgery"),
}
