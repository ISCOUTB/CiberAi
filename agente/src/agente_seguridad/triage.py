import json
import re
from typing import Optional

from .llm.ollama_client import OllamaClient, OllamaError
from .models import Finding, TriageResult

SYSTEM = (
    "Eres un analista de seguridad de software. Recibes una alerta de un analizador "
    "estatico (Bandit) y el codigo afectado. Decide si la alerta corresponde a una "
    "vulnerabilidad real (VULNERABLE) o a un falso positivo (SAFE). Responde SOLO con "
    "un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, "
    "vector_ataque, correccion."
)

TEMPLATE = """Alerta del SAST:
- Regla: {rule_id}
- CWE: {cwe}
- Severidad reportada: {severity}
- Confianza: {confidence}
- Archivo: {file}
- Linea: {line}
- Funcion: {function}
- Mensaje: {message}

Codigo afectado:
<code>
{context}
</code>

Devuelve el JSON con:
- veredicto: "VULNERABLE" o "SAFE"
- cwe: identificador CWE (o "Ninguno" si es SAFE)
- severidad: "Alta", "Media", "Baja" o "Info"
- explicacion: por que la alerta es real o un falso positivo
- vector_ataque: como se explota (o "N/A" si es SAFE)
- correccion: correccion recomendada (o "N/A" si es SAFE)
"""

VALID_VERDICTS = {"VULNERABLE", "SAFE"}
VALID_SEVERITIES = {"Alta", "Media", "Baja", "Info"}

# Reglas del SAST de alto riesgo empirico donde el modelo tiende a subestimar el
# riesgo al no poder verificar el flujo completo (p. ej., B403 'import pickle').
# Por politica de seguridad, nunca se recomienda descarte automatico para estas reglas.
DEFAULT_NEVER_DISCARD = {"B403"}


def build_prompt(finding: Finding) -> str:
    return TEMPLATE.format(
        rule_id=finding.rule_id,
        cwe=finding.cwe,
        severity=finding.severity,
        confidence=finding.confidence,
        file=finding.file,
        line=finding.line,
        function=finding.function,
        message=finding.message,
        context=finding.context or finding.code,
    )


def _clean_json(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return text


def parse_response(raw: str, finding: Finding, never_discard: Optional[set] = None) -> TriageResult:
    if never_discard is None:
        never_discard = DEFAULT_NEVER_DISCARD

    try:
        data = json.loads(_clean_json(raw))
    except json.JSONDecodeError:
        return suspicious(finding, "respuesta no es JSON valido")

    verdict = str(data.get("veredicto", "")).strip().upper()
    if verdict not in VALID_VERDICTS:
        return suspicious(finding, "veredicto ausente o invalido")
    if verdict == "SAFE" and not str(data.get("explicacion", "")).strip():
        return suspicious(finding, "SAFE sin justificacion")

    # Politica de seguridad: interceptar recomendaciones de descarte en reglas criticas
    if verdict == "SAFE" and finding.rule_id in never_discard:
        return TriageResult(
            finding_id=finding.finding_id,
            veredicto="SOSPECHOSA",
            cwe=finding.cwe,
            severidad=finding.severity.capitalize(),
            explicacion=(
                "Regla {} protegida por politica de seguridad: el modelo sugirio SAFE "
                "('{}'), pero se conserva para revision humana por alto riesgo de omision."
            ).format(finding.rule_id, str(data.get("explicacion", "")).strip()),
            vector_ataque=str(data.get("vector_ataque", "N/A")).strip(),
            correccion=str(data.get("correccion", "Revisar manualmente el uso.")).strip(),
            origen="politica_seguridad",
            valido=True,
        )

    severity = str(data.get("severidad", "")).strip().capitalize()
    if severity not in VALID_SEVERITIES:
        severity = "Media" if verdict == "VULNERABLE" else "Info"

    return TriageResult(
        finding_id=finding.finding_id,
        veredicto=verdict,
        cwe=str(data.get("cwe") or (finding.cwe if verdict == "VULNERABLE" else "Ninguno")),
        severidad=severity,
        explicacion=str(data.get("explicacion", "")).strip(),
        vector_ataque=str(data.get("vector_ataque", "N/A")).strip(),
        correccion=str(data.get("correccion", "N/A")).strip(),
        origen="llm",
        valido=True,
    )


def suspicious(finding: Finding, reason: str) -> TriageResult:
    return TriageResult(
        finding_id=finding.finding_id,
        veredicto="SOSPECHOSA",
        cwe=finding.cwe,
        severidad=finding.severity.capitalize(),
        explicacion="No se pudo validar la respuesta del modelo: {}. La alerta se conserva.".format(reason),
        vector_ataque="N/A",
        correccion="Revisar manualmente.",
        origen="respaldo",
        valido=False,
    )


def triage_findings(findings, client: Optional[OllamaClient], never_discard: Optional[set] = None) -> int:
    if never_discard is None:
        never_discard = DEFAULT_NEVER_DISCARD
    if client is not None and not client.is_available():
        client = None
    errors = 0
    for finding in findings:
        if client is None:
            finding.triage = suspicious(finding, "modelo no disponible").to_dict()
            errors += 1
            continue
        try:
            raw = client.generate(build_prompt(finding), system=SYSTEM)
            result = parse_response(raw, finding, never_discard=never_discard)
        except OllamaError as exc:
            result = suspicious(finding, str(exc))
            errors += 1
        if not result.valido:
            errors += 1
        finding.triage = result.to_dict()
    return errors
