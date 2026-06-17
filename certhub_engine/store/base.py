from __future__ import annotations

import abc

from ..schemas import AuditReport, Finding, RegClause


class Store(abc.ABC):

    backend: str = "abstract"

    
    @abc.abstractmethod
    def upsert_clauses(self, clauses: list[RegClause], vectors: list[list[float]]) -> int:
        

    @abc.abstractmethod
    def match_clauses(
        self, query_vector: list[float], top_k: int, jurisdiction: str | None = None
    ) -> list[tuple[RegClause, float]]:
        

    @abc.abstractmethod
    def count_clauses(self) -> int:
        ...

    
    @abc.abstractmethod
    def insert_audit_run(self, report: AuditReport) -> None:
        

    @abc.abstractmethod
    def readiness_trend(self) -> list[dict]:
        

    @abc.abstractmethod
    def severity_breakdown(self) -> list[dict]:
