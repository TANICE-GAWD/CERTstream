

from __future__ import annotations

from .schemas import Finding, SEVERITY_WEIGHT, Verdict


_ADVERSE = {Verdict.non_conformant, Verdict.insufficient_evidence}


def compute_readiness(findings: list[Finding], sections_assessed: int) -> float:

    if sections_assessed <= 0:
        return 0.0
    penalty = 0.0
    for f in findings:
        if f.verdict in _ADVERSE:
            penalty += SEVERITY_WEIGHT[f.severity] * f.confidence
    raw = 1.0 - (penalty / sections_assessed)
    return round(max(0.0, min(1.0, raw)) * 100.0, 1)


def grade(score: float) -> str:
    if score >= 85:
        return "READY"
    if score >= 70:
        return "MINOR GAPS"
    if score >= 50:
        return "MAJOR GAPS"
    return "NOT READY"
