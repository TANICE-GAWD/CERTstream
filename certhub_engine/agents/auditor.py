"""Persona-driven auditor: (section + retrieved clauses) -> validated findings.

Claude path (key set): structured output via output_config.format, so every
finding is schema-validated. Works against the direct Anthropic API or the
Vercel AI Gateway (Anthropic-compatible endpoint). Heuristic path (no key):
deterministic analysis so the pipeline runs offline.

Both paths run through the SAME anti-hallucination guard: a finding citing a
clause id not in the retrieved set for that section is dropped.
"""
from __future__ import annotations

import json

from ..config import CONFIG
from ..ingest import Section
from ..retrieval import RetrievedClause
from ..schemas import FINDINGS_JSON_SCHEMA, Finding, Severity, Verdict
from .personas import Persona

_MAX_TOKENS = 4000


def _format_clauses(clauses: list[RetrievedClause]) -> str:
    if not clauses:
        return "(none retrieved)"
    parts = []
    for rc in clauses:
        c = rc.clause
        parts.append("- clause_id: " + c.clause_id)
        parts.append("  title: " + c.title)
        parts.append("  text: " + c.text)
    return "\n".join(parts)


def _user_prompt(section: Section, clauses: list[RetrievedClause]) -> str:
    parts = [
        "RETRIEVED CLAUSES (cite only these clause_ids):",
        _format_clauses(clauses),
        "",
        "TECHDOC SECTION UNDER REVIEW:",
        "## " + section.title,
        section.body,
        "",
        "Assess this section against the retrieved clauses and return findings.",
    ]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Claude path
# --------------------------------------------------------------------------- #
def _audit_with_claude(persona: Persona, section: Section, clauses: list[RetrievedClause]) -> list[Finding]:
    import anthropic

    # Extra retries help on free-tier gateways with strict per-minute limits.
    client = anthropic.Anthropic(api_key=CONFIG.llm_key, base_url=CONFIG.llm_base_url, max_retries=5)
    resp = client.messages.create(
        model=CONFIG.model,
        max_tokens=_MAX_TOKENS,
        system=persona.system_prompt,
        messages=[{"role": "user", "content": _user_prompt(section, clauses)}],
        output_config={"format": {"type": "json_schema", "schema": FINDINGS_JSON_SCHEMA}},
    )
    if resp.stop_reason == "refusal":
        return []
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    data = json.loads(text)
    out: list[Finding] = []
    for raw in data.get("findings", []):
        raw["persona"] = persona.key
        raw.setdefault("section", section.title)
        out.append(Finding(**raw))
    return out


# --------------------------------------------------------------------------- #
# Heuristic path (offline fallback)
# --------------------------------------------------------------------------- #
_WEAKNESS_MARKERS = (
    "tbd", "to be completed", "not yet", "n/a", "todo", "pending",
    "no formal", "informal", "not performed", "will be", "future",
)


def _audit_heuristic(persona: Persona, section: Section, clauses: list[RetrievedClause]) -> list[Finding]:
    if not clauses:
        return []
    body = section.body.lower()
    top = clauses[0].clause
    short_body = section.body.strip().replace("\n", " ")[:160]
    weak_hits = [m for m in _WEAKNESS_MARKERS if m in body]
    word_count = len(body.split())

    if weak_hits:
        rationale = "Section contains placeholder/deferred language (" + ", ".join(weak_hits) + "); required evidence for " + top.clause_id + " is not actually documented."
        rec = "Provide complete, dated objective evidence addressing " + top.title + " rather than deferred statements."
        return [Finding(section=section.title, claim=short_body or section.title, clause_id=top.clause_id, clause_title=top.title, verdict=Verdict.insufficient_evidence, severity=Severity.major, rationale=rationale, evidence_quote=short_body, recommendation=rec, persona=persona.key, confidence=0.66)]

    if word_count < 40:
        rationale = "Section is too sparse (" + str(word_count) + " words) to demonstrate conformity with " + top.clause_id + "."
        rec = "Expand to fully address " + top.title + "."
        return [Finding(section=section.title, claim=short_body or section.title, clause_id=top.clause_id, clause_title=top.title, verdict=Verdict.insufficient_evidence, severity=Severity.minor, rationale=rationale, evidence_quote=short_body, recommendation=rec, persona=persona.key, confidence=0.55)]

    rationale = "Section provides substantive content mapping to " + top.clause_id + "; spot-check only (heuristic)."
    return [Finding(section=section.title, claim=short_body or section.title, clause_id=top.clause_id, clause_title=top.title, verdict=Verdict.conformant, severity=Severity.observation, rationale=rationale, evidence_quote=short_body, recommendation="Confirm traceability to objective evidence.", persona=persona.key, confidence=0.5)]


# --------------------------------------------------------------------------- #
# Public entry point + anti-hallucination guard
# --------------------------------------------------------------------------- #
# PERMANENT errors (401/403) trip a circuit breaker (disable Claude for the run).
# TRANSIENT errors (429/5xx/network) fall back to the heuristic for that section
# only; the next section retries (the SDK backs off on 429). Warned once.
_claude_disabled = False
_warned_transient = False


def _concise_error(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    msg = None
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
    msg = (msg or str(exc)).split("\n")[0][:240]
    return (str(status) + ": " + msg) if status else msg


def _is_permanent(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) in (401, 403)


def reset_claude_circuit() -> None:
    """Re-enable the Claude path (e.g. between test cases or after config change)."""
    global _claude_disabled, _warned_transient
    _claude_disabled = False
    _warned_transient = False


def audit_section(persona: Persona, section: Section, clauses: list[RetrievedClause]) -> list[Finding]:
    global _claude_disabled, _warned_transient
    if CONFIG.has_claude and not _claude_disabled:
        try:
            findings = _audit_with_claude(persona, section, clauses)
        except Exception as exc:
            if _is_permanent(exc):
                _claude_disabled = True
                print("[auditor] Claude path disabled for this run (auth/model-access): " + _concise_error(exc))
            elif not _warned_transient:
                _warned_transient = True
                print("[auditor] transient Claude error (e.g. rate limit); this section uses heuristic: " + _concise_error(exc))
            findings = _audit_heuristic(persona, section, clauses)
    else:
        findings = _audit_heuristic(persona, section, clauses)

    retrieved_ids = {rc.clause.clause_id for rc in clauses}
    clause_titles = {rc.clause.clause_id: rc.clause.title for rc in clauses}
    guarded: list[Finding] = []
    for f in findings:
        if f.clause_id in retrieved_ids:
            if not f.clause_title:
                f.clause_title = clause_titles.get(f.clause_id, "")
            guarded.append(f)
        else:
            print("[guard] dropped finding citing non-retrieved clause '" + f.clause_id + "' in section '" + section.title + "'")
    return guarded
