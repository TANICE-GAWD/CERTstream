from __future__ import annotations

import os
import sys
import tempfile


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))




os.environ["STORE_BACKEND"] = "local"
os.environ["EMBEDDING_PROVIDER"] = "hashing"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["AI_GATEWAY_API_KEY"] = ""
os.environ["ANTHROPIC_BASE_URL"] = ""
os.environ.setdefault("LOCAL_DB_PATH", os.path.join(tempfile.mkdtemp(), "test.db"))


from certhub_engine.corpus import ingest_corpus  
from certhub_engine.pipeline import run_audit  
from certhub_engine.store import get_store  

WEAK = "data/techdocs/vitaltrack_weak.md"
STRONG = "data/techdocs/vitaltrack_strong.md"


def _setup():
    n = ingest_corpus()
    assert n > 0, "corpus failed to ingest"


def test_corpus_ingests():
    _setup()
    assert get_store().count_clauses() > 0


def test_no_hallucinated_citations():
    _setup()
    store = get_store()
    
    for persona in ("notified_body", "fda"):
        report = run_audit(WEAK, persona_key=persona, save=False)
        for f in report.findings:
            
            hits = store.match_clauses(
                [0.0] * 384, top_k=999  
            )
            ids = {c.clause_id for c, _ in hits}
            assert f.clause_id in ids, f"hallucinated citation: {f.clause_id}"


def test_score_discriminates():
    _setup()
    weak = run_audit(WEAK, persona_key="notified_body", save=False)
    strong = run_audit(STRONG, persona_key="notified_body", save=False)
    assert strong.readiness_score > weak.readiness_score, (
        f"score did not discriminate: weak={weak.readiness_score} "
        f"strong={strong.readiness_score}"
    )


def test_dataset_persists():
    _setup()
    report = run_audit(WEAK, persona_key="notified_body", save=True)
    trend = get_store().readiness_trend()
    assert any(r["document_name"] == "vitaltrack_weak.md" for r in trend)
    assert len(report.findings) > 0


def test_jurisdiction_packs_differ():
    _setup()
    nb = run_audit(WEAK, persona_key="notified_body", save=False)
    fda = run_audit(WEAK, persona_key="fda", save=False)
    nb_clauses = {f.clause_id for f in nb.findings}
    fda_clauses = {f.clause_id for f in fda.findings}
    
    assert nb_clauses != fda_clauses, "personas produced identical citations"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("\nAll checks passed.")
