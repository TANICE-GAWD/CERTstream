from __future__ import annotations

import abc

from ..schemas import AuditReport, Finding, RegClause  


class Store(abc.ABC):
    """Backend interface: regulatory corpus (RAG) + outcomes dataset (moat)."""

    backend: str = "abstract"

    
    @abc.abstractmethod
    def upsert_clauses(self, clauses: list[RegClause], vectors: list[list[float]]) -> int:
        """Insert/replace regulatory clauses with their embeddings. Returns count."""
        raise NotImplementedError

    @abc.abstractmethod
    def match_clauses(
        self, query_vector: list[float], top_k: int, jurisdiction: str | None = None
    ) -> list[tuple[RegClause, float]]:
        """Return top-k (clause, similarity) by vector similarity, optionally filtered."""
        raise NotImplementedError

    @abc.abstractmethod
    def count_clauses(self) -> int:
        """Number of clauses currently stored."""
        raise NotImplementedError

    
    @abc.abstractmethod
    def insert_audit_run(self, report: AuditReport) -> None:
        """Persist one audit_runs row + its child findings rows."""
        raise NotImplementedError

    @abc.abstractmethod
    def readiness_trend(self) -> list[dict]:
        """Aggregate query over accumulated runs (demonstrates the dataset)."""
        raise NotImplementedError

    @abc.abstractmethod
    def severity_breakdown(self) -> list[dict]:
        """Counts of findings by severity across all runs."""
        raise NotImplementedError
