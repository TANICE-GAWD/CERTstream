"""Render a non-conformity report + ranked remediation checklist (markdown)."""
from __future__ import annotations

from .schemas import AuditReport, Finding, SEVERITY_WEIGHT, Severity, Verdict

_SEVERITY_ORDER = {Severity.critical: 0, Severity.major: 1, Severity.minor: 2, Severity.observation: 3}
_ADVERSE = {Verdict.non_conformant, Verdict.insufficient_evidence}


def _rank(findings: list[Finding]) -> list[Finding]:
    
    return sorted(
        findings,
        key=lambda f: (_SEVERITY_ORDER[f.severity], -SEVERITY_WEIGHT[f.severity] * f.confidence),
    )


def remediation_checklist(findings: list[Finding]) -> list[Finding]:
    """Adverse findings, ranked by what most increases readiness if fixed."""
    return _rank([f for f in findings if f.verdict in _ADVERSE])


def render_markdown(report: AuditReport) -> str:
    lines: list[str] = []
    lines.append(f"
    lines.append("")
    lines.append(f"- **Persona:** {report.persona} ({report.jurisdiction})")
    lines.append(f"- **Readiness score:** {report.readiness_score} / 100  →  **{report.grade}**")
    lines.append(f"- **Audit id:** `{report.audit_id}`")
    lines.append(f"- **Findings:** {len(report.findings)}")
    if report.summary:
        lines.append("")
        lines.append(report.summary)

    
    ranked = _rank(report.findings)
    lines.append("")
    lines.append("
    if not ranked:
        lines.append("_No findings._")
    for i, f in enumerate(ranked, 1):
        lines.append("")
        lines.append(
            f"
            f"— {f.verdict.value} ({f.clause_id})"
        )
        lines.append(f"- **Clause:** {f.clause_title or f.clause_id}")
        lines.append(f"- **Rationale:** {f.rationale}")
        if f.evidence_quote:
            lines.append(f'- **Evidence:** "{f.evidence_quote}"')
        if f.recommendation:
            lines.append(f"- **Fix:** {f.recommendation}")
        lines.append(f"- **Confidence:** {f.confidence:.2f}")

    
    checklist = remediation_checklist(report.findings)
    lines.append("")
    lines.append("
    if not checklist:
        lines.append("_Nothing blocking — looks submission-ready._")
    for i, f in enumerate(checklist, 1):
        lines.append(
            f"{i}. **[{f.severity.value}]** {f.section} — "
            f"{f.recommendation or f.rationale} _(→ {f.clause_id})_"
        )

    return "\n".join(lines)
