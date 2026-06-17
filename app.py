
"""CertHub Submission-Readiness Engine — CLI.

Usage:
    python app.py init-corpus
    python app.py audit data/techdocs/vitaltrack_weak.md --persona notified_body
    python app.py compare            
    python app.py dataset            

If `streamlit` is installed:  streamlit run app.py
"""
from __future__ import annotations

import argparse
import sys

from certhub_engine.config import CONFIG


def cmd_init_corpus(args) -> int:
    from certhub_engine.corpus import ingest_corpus
    from certhub_engine.store import get_store

    n = ingest_corpus(args.corpus_dir)
    total = get_store().count_clauses()
    print(f"[init-corpus] ingested {n} clause(s); store now holds {total}.")
    print(f"[config] {CONFIG.summary()}")
    return 0 if total else 1


def _print_report(report) -> None:
    from certhub_engine.report import render_markdown

    print(render_markdown(report))
    print("\n" + "-" * 72)


def cmd_audit(args) -> int:
    from certhub_engine.pipeline import run_audit
    from certhub_engine.store import get_store

    if get_store().count_clauses() == 0:
        print("[audit] corpus is empty — run `python app.py init-corpus` first.")
        return 1
    report = run_audit(args.techdoc, persona_key=args.persona, save=not args.no_save)
    _print_report(report)
    return 0


def cmd_compare(args) -> int:
    from certhub_engine.pipeline import run_audit
    from certhub_engine.store import get_store

    if get_store().count_clauses() == 0:
        print("[compare] corpus empty — run `python app.py init-corpus` first.")
        return 1

    docs = [
        ("data/techdocs/vitaltrack_weak.md", "WEAK"),
        ("data/techdocs/vitaltrack_strong.md", "STRONG"),
    ]
    personas = ["notified_body", "fda"]
    print(f"[config] {CONFIG.summary()}\n")
    rows = []
    for path, label in docs:
        for persona in personas:
            r = run_audit(path, persona_key=persona, save=not args.no_save)
            rows.append((label, persona, r.readiness_score, r.grade, len(r.findings)))

    print(f"{'doc':<8}{'persona':<16}{'score':>7}  {'grade':<12}{'findings':>9}")
    print("-" * 56)
    for label, persona, score, grade, n in rows:
        print(f"{label:<8}{persona:<16}{score:>7}  {grade:<12}{n:>9}")

    weak = next(s for l, p, s, *_ in rows if l == "WEAK" and p == "notified_body")
    strong = next(s for l, p, s, *_ in rows if l == "STRONG" and p == "notified_body")
    print("-" * 56)
    verdict = "PASS" if strong > weak else "FAIL"
    print(f"[discrimination] NB strong({strong}) > weak({weak}) ? {verdict}")
    return 0 if strong > weak else 2


def cmd_dataset(args) -> int:
    from certhub_engine.dataset import readiness_trend, severity_breakdown

    trend = readiness_trend()
    breakdown = severity_breakdown()
    print(f"[config] {CONFIG.summary()}\n")
    print(f"=== Accumulated certification-outcomes dataset ({len(trend)} run(s)) ===")
    print(f"{'document':<28}{'persona':<16}{'score':>7}  grade")
    for r in trend:
        print(f"{r['document_name']:<28}{r['persona']:<16}{r['readiness_score']:>7}  {r['grade']}")
    print("\n=== Findings by severity (across all runs) ===")
    for r in breakdown:
        print(f"  {r['severity']:<14}{r['n']}")
    if not trend:
        print("(empty — run `audit` or `compare` first)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CertHub Submission-Readiness Engine")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("init-corpus", help="embed + upsert the regulatory corpus")
    pi.add_argument("--corpus-dir", default=None)
    pi.set_defaults(func=cmd_init_corpus)

    pa = sub.add_parser("audit", help="audit one TechDoc")
    pa.add_argument("techdoc")
    pa.add_argument("--persona", default="notified_body", choices=["notified_body", "fda"])
    pa.add_argument("--no-save", action="store_true", help="don't persist to the dataset")
    pa.set_defaults(func=cmd_audit)

    pc = sub.add_parser("compare", help="weak vs strong, both personas")
    pc.add_argument("--no-save", action="store_true")
    pc.set_defaults(func=cmd_compare)

    pd = sub.add_parser("dataset", help="show accumulated outcomes (the moat)")
    pd.set_defaults(func=cmd_dataset)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)



def _streamlit_app() -> None:  
    import streamlit as st

    from certhub_engine.dataset import readiness_trend, severity_breakdown
    from certhub_engine.pipeline import run_audit
    from certhub_engine.report import render_markdown
    from certhub_engine.store import get_store

    st.set_page_config(page_title="CertHub Submission-Readiness Engine", layout="wide")
    st.title("CertHub — Submission-Readiness Engine")
    st.caption(CONFIG.summary())

    if get_store().count_clauses() == 0:
        if st.button("Initialise regulatory corpus"):
            from certhub_engine.corpus import ingest_corpus

            n = ingest_corpus()
            st.success(f"Ingested {n} clauses.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        techdoc = st.selectbox(
            "TechDoc",
            ["data/techdocs/vitaltrack_weak.md", "data/techdocs/vitaltrack_strong.md"],
        )
    with col2:
        persona = st.selectbox("Persona", ["notified_body", "fda"])

    if st.button("Run audit", type="primary"):
        report = run_audit(techdoc, persona_key=persona)
        st.metric("Readiness score", f"{report.readiness_score} / 100", report.grade)
        st.markdown(render_markdown(report))

    st.divider()
    st.subheader("Accumulated certification-outcomes dataset (the moat)")
    st.dataframe(readiness_trend())
    st.dataframe(severity_breakdown())


def _running_under_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx  

        return get_script_run_ctx() is not None
    except Exception:
        return False


if _running_under_streamlit():  
    _streamlit_app()
elif __name__ == "__main__":
    sys.exit(main())
