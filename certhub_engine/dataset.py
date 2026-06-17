from __future__ import annotations

from .schemas import AuditReport
from .store import get_store


def persist(report: AuditReport) -> None:
    get_store().insert_audit_run(report)


def readiness_trend() -> list[dict]:
    return get_store().readiness_trend()


def severity_breakdown() -> list[dict]:
    return get_store().severity_breakdown()
