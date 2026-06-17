from __future__ import annotations

import hashlib
from pathlib import Path

from .agents.auditor import audit_section
from .agents.personas import PERSONAS, Persona
from .config import CONFIG
from .dataset import persist
from .ingest import parse_techdoc
from .retrieval import retrieve_for_text
from .schemas import AuditReport, Finding
from .scoring import compute_readiness, grade


def _audit_id(document_name: str, persona_key: str) -> str:
    h = hashlib.sha1(f"{document_name}:{persona_key}".encode()).hexdigest()[:10]
    return f"run_{persona_key}_{h}"


def run_audit(
    techdoc_path: str | Path,
    persona_key: str = "notified_body",
    top_k: int | None = None,
    save: bool = True,
) -> AuditReport:
    if persona_key not in PERSONAS:
        raise ValueError(f"Unknown persona '{persona_key}'. Options: {list(PERSONAS)}")
    persona: Persona = PERSONAS[persona_key]

    sections = parse_techdoc(techdoc_path)
    if not sections:
        raise ValueError(f"No readable sections found in {techdoc_path}")


    all_findings: list[Finding] = []
    for section in sections:
        clauses = retrieve_for_text(
            section.text, top_k=top_k, jurisdiction=persona.jurisdiction
        )
        all_findings.extend(audit_section(persona, section, clauses))

    score = compute_readiness(all_findings, sections_assessed=len(sections))
    document_name = Path(techdoc_path).name

    n_adverse = sum(1 for f in all_findings if f.verdict.value in ("non_conformant", "insufficient_evidence"))
    summary = (
        f"Assessed {len(sections)} section(s); {len(all_findings)} finding(s), "
        f"{n_adverse} adverse. Auditor={'Claude:' + CONFIG.model if CONFIG.has_claude else 'heuristic'}."
    )

    report = AuditReport(
        audit_id=_audit_id(document_name, persona_key),
        document_name=document_name,
        persona=persona.name,
        jurisdiction=persona.jurisdiction,
        readiness_score=score,
        grade=grade(score),
        findings=all_findings,
        summary=summary,
    )
    if save:
        persist(report)
    return report
