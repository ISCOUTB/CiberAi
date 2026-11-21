import hashlib
from dataclasses import replace
from typing import List, Tuple

from .models import Finding


def dedup_key(finding: Finding) -> Tuple[str, str, str, str, int]:
    # La regla forma parte de la identidad: dos hallazgos pueden compartir CWE
    # y ubicacion y aun asi ser problemas distintos.
    return (finding.rule_id, finding.cwe, finding.file, finding.function, finding.line)


def deduplicate(findings: List[Finding]) -> List[Finding]:
    seen = {}
    order: List[str] = []
    for finding in findings:
        key = dedup_key(finding)
        ident = "|".join(str(k) for k in key)
        if ident in seen:
            continue
        seen[ident] = finding
        order.append(ident)
    return [seen[i] for i in order]


def fingerprint(finding: Finding) -> str:
    # Huella estable: regla + CWE + ubicacion + contexto normalizado.
    # Normalizar el contexto evita que un cambio de espacios genere una huella
    # distinta para el mismo fragmento de codigo.
    context = " ".join(str(finding.context or finding.code or "").split())
    raw = "|".join([finding.rule_id, finding.cwe, finding.file, finding.function,
                    str(finding.line), context])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def with_ids(findings: List[Finding]) -> List[Finding]:
    out = []
    for finding in findings:
        digest = fingerprint(finding)
        finding_id = digest[:16]
        triage = dict(finding.triage) if finding.triage else None
        if triage is not None:
            triage["finding_id"] = finding_id
        out.append(replace(finding, fingerprint=digest, finding_id=finding_id,
                           triage=triage))
    return out
