from __future__ import annotations

import re
from pathlib import Path

from .embeddings import embed_texts
from .schemas import RegClause
from .store import get_store

_BLOCK_RE = re.compile(r"^###\s+(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*$")
_DEFAULT_CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"


def parse_corpus_file(path: Path) -> list[RegClause]:
    clauses: list[RegClause] = []
    cur: dict | None = None
    body: list[str] = []
    source = ""

    def flush():
        nonlocal cur, body, source
        if cur is not None:
            text = "\n".join(body).strip()
            clauses.append(
                RegClause(
                    clause_id=cur["id"],
                    title=cur["title"],
                    text=text,
                    jurisdiction=cur["jurisdiction"],
                    source=source or "public",
                )
            )
        cur, body, source = None, [], ""

    for line in path.read_text(encoding="utf-8").splitlines():
        m = _BLOCK_RE.match(line)
        if m:
            flush()
            cur = {"id": m.group(1).strip(), "jurisdiction": m.group(2).strip(),
                   "title": m.group(3).strip()}
        elif line.upper().startswith("SOURCE:"):
            source = line.split(":", 1)[1].strip()
        elif cur is not None:
            body.append(line)
    flush()
    return clauses


def load_corpus(corpus_dir: str | Path | None = None) -> list[RegClause]:
    d = Path(corpus_dir) if corpus_dir else _DEFAULT_CORPUS_DIR
    clauses: list[RegClause] = []
    for f in sorted(d.glob("*.md")):
        clauses.extend(parse_corpus_file(f))
    return clauses


def ingest_corpus(corpus_dir: str | Path | None = None) -> int:
    
    clauses = load_corpus(corpus_dir)
    if not clauses:
        return 0
    vectors = embed_texts([f"{c.title}\n{c.text}" for c in clauses])
    return get_store().upsert_clauses(clauses, vectors)
