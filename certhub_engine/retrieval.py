from __future__ import annotations

from dataclasses import dataclass

from .config import CONFIG
from .embeddings import embed_text
from .schemas import RegClause
from .store import get_store


@dataclass
class RetrievedClause:
    clause: RegClause
    similarity: float


def retrieve_for_text(
    text: str, top_k: int | None = None, jurisdiction: str | None = None
) -> list[RetrievedClause]:
    store = get_store()
    qv = embed_text(text)
    hits = store.match_clauses(qv, top_k or CONFIG.top_k, jurisdiction=jurisdiction)
    return [RetrievedClause(clause=c, similarity=s) for c, s in hits]
