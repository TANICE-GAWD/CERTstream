from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..config import CONFIG
from ..schemas import AuditReport, RegClause
from .base import Store


class SupabaseStore(Store):
    backend = "supabase"

    def __init__(self):
        from supabase import create_client  

        self.client = create_client(CONFIG.supabase_url, CONFIG.supabase_key)

    
    def upsert_clauses(self, clauses: list[RegClause], vectors: list[list[float]]) -> int:
        rows = [
            {
                "clause_id": c.clause_id,
                "title": c.title,
                "text": c.text,
                "jurisdiction": c.jurisdiction,
                "source": c.source,
                "embedding": v,
            }
            for c, v in zip(clauses, vectors)
        ]
        
        self.client.table("reg_clauses").upsert(rows, on_conflict="clause_id").execute()
        return len(rows)

    def match_clauses(
        self, query_vector: list[float], top_k: int, jurisdiction: str | None = None
    ) -> list[tuple[RegClause, float]]:
        resp = self.client.rpc(
            "match_clauses",
            {
                "query_embedding": query_vector,
                "match_count": top_k,
                "filter_jurisdiction": jurisdiction,
            },
        ).execute()
        out: list[tuple[RegClause, float]] = []
        for r in resp.data or []:
            out.append(
                (
                    RegClause(
                        clause_id=r["clause_id"],
                        title=r["title"],
                        text=r["text"],
                        jurisdiction=r["jurisdiction"],
                        source=r["source"],
                    ),
                    float(r.get("similarity", 0.0)),
                )
            )
        return out

    def count_clauses(self) -> int:
        resp = self.client.table("reg_clauses").select("clause_id", count="exact").execute()
        return resp.count or 0

    
    def insert_audit_run(self, report: AuditReport) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.client.table("audit_runs").upsert(
            {
                "audit_id": report.audit_id,
                "document_name": report.document_name,
                "persona": report.persona,
                "jurisdiction": report.jurisdiction,
                "readiness_score": report.readiness_score,
                "grade": report.grade,
                "summary": report.summary,
                "created_at": now,
            },
            on_conflict="audit_id",
        ).execute()
        if report.findings:
            self.client.table("findings").insert(
                [
                    {
                        "audit_id": report.audit_id,
                        "doc_section": f.section,
                        "claim": f.claim,
                        "clause_id": f.clause_id,
                        "clause_title": f.clause_title,
                        "verdict": f.verdict.value,
                        "severity": f.severity.value,
                        "rationale": f.rationale,
                        "evidence_quote": f.evidence_quote,
                        "recommendation": f.recommendation,
                        "persona": f.persona,
                        "confidence": f.confidence,
                        "created_at": now,
                    }
                    for f in report.findings
                ]
            ).execute()

    def readiness_trend(self) -> list[dict]:
        resp = (
            self.client.table("audit_runs")
            .select("document_name, persona, jurisdiction, readiness_score, grade, created_at")
            .order("created_at")
            .execute()
        )
        return resp.data or []

    def severity_breakdown(self) -> list[dict]:
        
        try:
            resp = self.client.rpc("severity_breakdown", {}).execute()
            return resp.data or []
        except Exception:
            resp = self.client.table("findings").select("severity").execute()
            counts: dict[str, int] = {}
            for r in resp.data or []:
                counts[r["severity"]] = counts.get(r["severity"], 0) + 1
            return [{"severity": k, "n": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
