from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    key: str
    name: str
    jurisdiction: str        
    system_prompt: str


from .notified_body import NOTIFIED_BODY  
from .fda import FDA  

PERSONAS: dict[str, Persona] = {
    NOTIFIED_BODY.key: NOTIFIED_BODY,
    FDA.key: FDA,
}

__all__ = ["Persona", "PERSONAS", "NOTIFIED_BODY", "FDA"]
