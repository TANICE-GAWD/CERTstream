from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import numpy as np

from ..config import CONFIG
from ..schemas import AuditReport, Finding, RegClause, Verdict
from .base import Store


class LocalStore(Store):
    backend = "local"

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or CONFIG.local_db_path
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS reg_clauses (
                clause_id    TEXT PRIMARY KEY,
                title        TEXT NOT NULL,
                text         TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                source       TEXT NOT NULL,
                embedding    TEXT NOT NULL   -- JSON float array
            );
            CREATE TABLE IF NOT EXISTS audit_runs (
                audit_id        TEXT PRIMARY KEY,
                document_name   TEXT NOT NULL,
                persona         TEXT NOT NULL,
                jurisdiction    TEXT NOT NULL,
                readiness_score REAL NOT NULL,
                grade           TEXT NOT NULL,
                summary         TEXT,
                created_at      TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS findings (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id       TEXT NOT NULL REFERENCES audit_runs(audit_id),
                doc_section    TEXT NOT NULL,
                claim          TEXT NOT NULL,
                clause_id      TEXT NOT NULL,
                clause_title   TEXT,
                verdict        TEXT NOT NULL,
                severity       TEXT NOT NULL,
                rationale      TEXT,
                evidence_quote TEXT,
                recommendation TEXT,
                persona        TEXT NOT NULL,
                confidence     REAL,
                created_at     TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    
    def upsert_clauses(self, clauses: list[RegClause], vectors: list[list[float]]) -> int:
        rows = [
            (c.clause_id, c.title, c.text, c.jurisdiction, c.source, json.dumps(v))
            for c, v in zip(clauses, vectors)
        ]
        self._conn.executemany(
            """INSERT INTO reg_clauses
                 (clause_id, title, text, jurisdiction, source, embedding)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(clause_id) DO UPDATE SET
                 title=excluded.title, text=excluded.text,
                 jurisdiction=excluded.jurisdiction, source=excluded.source,
                 embedding=excluded.embedding""",
            rows,
        )
        self._conn.commit()
        return len(rows)

    def match_clauses(
        self, query_vector: list[float], top_k: int, jurisdiction: str | None = None
    ) -> list[tuple[RegClause, float]]:
        sql = "SELECT * FROM reg_clauses"
        params: list = []
        if jurisdiction:
            sql += " WHERE jurisdiction = ?"
            params.append(jurisdiction)
        rows = self._conn.execute(sql, params).fetchall()
        if not rows:
            return []
        mat = np.array([json.loads(r["embedding"]) for r in rows], dtype=np.float32)
        q = np.array(query_vector, dtype=np.float32)
        
        sims = mat @ q
        order = np.argsort(-sims)[:top_k]
        out: list[tuple[RegClause, float]] = []
        for i in order:
            r = rows[i]
            out.append(
                (
                    RegClause(
                        clause_id=r["clause_id"],
                        title=r["title"],
                        text=r["text"],
                        jurisdiction=r["jurisdiction"],
                        source=r["source"],
                    ),
                    float(sims[i]),
                )
            )
        return out

    def count_clauses(self) -> int:
        return self._conn.execute("SELECT COUNT(*) AS n FROM reg_clauses").fetchone()["n"]

    
    def insert_audit_run(self, report: AuditReport) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO audit_runs
                 (audit_id, document_name, persona, jurisdiction,
                  readiness_score, grade, summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.audit_id,
                report.document_name,
                report.persona,
                report.jurisdiction,
                report.readiness_score,
                report.grade,
                report.summary,
                now,
            ),
        )
        self._conn.executemany(
            """INSERT INTO findings
                 (audit_id, doc_section, claim, clause_id, clause_title,
                  verdict, severity, rationale, evidence_quote, recommendation,
                  persona, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    report.audit_id,
                    f.section,
                    f.claim,
                    f.clause_id,
                    f.clause_title,
                    f.verdict.value,
                    f.severity.value,
                    f.rationale,
                    f.evidence_quote,
                    f.recommendation,
                    f.persona,
                    f.confidence,
                    now,
                )
                for f in report.findings
            ],
        )
        self._conn.commit()

    def readiness_trend(self) -> list[dict]:
        rows = self._conn.execute(
            """SELECT document_name, persona, jurisdiction, readiness_score,
                      grade, created_at
               FROM audit_runs ORDER BY created_at"""
        ).fetchall()
        return [dict(r) for r in rows]

    def severity_breakdown(self) -> list[dict]:
        rows = self._conn.execute(
            """SELECT severity, COUNT(*) AS n FROM findings
               GROUP BY severity ORDER BY n DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
