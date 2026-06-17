
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Graded like a real non-conformity report."""

    critical = "critical"          
    major = "major"                
    minor = "minor"                
    observation = "observation"    



SEVERITY_WEIGHT = {
    Severity.critical: 1.0,
    Severity.major: 0.6,
    Severity.minor: 0.25,
    Severity.observation: 0.05,
}


class Verdict(str, Enum):
    conformant = "conformant"
    non_conformant = "non_conformant"
    insufficient_evidence = "insufficient_evidence"
    not_applicable = "not_applicable"


class Finding(BaseModel):
    """One labeled audit row, cited to a real regulatory clause."""

    section: str = Field(..., description="TechDoc section the finding refers to")
    claim: str = Field(..., description="The documented claim/state being assessed")
    clause_id: str = Field(..., description="Regulatory clause id, e.g. MDR-ANNEX-II-1.1")
    clause_title: str = Field(default="", description="Human-readable clause title")
    verdict: Verdict
    severity: Severity
    rationale: str = Field(..., description="Why the auditor reached this verdict")
    evidence_quote: str = Field(
        default="", description="Short quote from the TechDoc grounding the verdict"
    )
    recommendation: str = Field(default="", description="What to fix / add")
    persona: str = Field(default="", description="Which auditor persona produced this")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class RegClause(BaseModel):
    clause_id: str
    title: str
    text: str
    jurisdiction: str          
    source: str                


class AuditReport(BaseModel):
    audit_id: str
    document_name: str
    persona: str
    jurisdiction: str
    readiness_score: float
    grade: str
    findings: list[Finding]
    summary: str = ""





FINDINGS_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "section": {"type": "string"},
                    "claim": {"type": "string"},
                    "clause_id": {"type": "string"},
                    "clause_title": {"type": "string"},
                    "verdict": {
                        "type": "string",
                        "enum": [v.value for v in Verdict],
                    },
                    "severity": {
                        "type": "string",
                        "enum": [s.value for s in Severity],
                    },
                    "rationale": {"type": "string"},
                    "evidence_quote": {"type": "string"},
                    "recommendation": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "section",
                    "claim",
                    "clause_id",
                    "clause_title",
                    "verdict",
                    "severity",
                    "rationale",
                    "evidence_quote",
                    "recommendation",
                    "confidence",
                ],
            },
        }
    },
    "required": ["findings"],
}
