from __future__ import annotations

from functools import lru_cache

from ..config import CONFIG
from .base import Store


@lru_cache(maxsize=1)
def get_store() -> Store:
    if CONFIG.use_supabase:
        from .supabase_store import SupabaseStore

        return SupabaseStore()
    from .local_store import LocalStore

    return LocalStore()


__all__ = ["Store", "get_store"]
