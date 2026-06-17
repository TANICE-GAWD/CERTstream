
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

_GATEWAY_URL = "https://ai-gateway.vercel.sh"

_VERSION_RE = re.compile(r"-(\d+)-(\d+)$")


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str = _get("ANTHROPIC_API_KEY")
    ai_gateway_api_key: str = _get("AI_GATEWAY_API_KEY")
    anthropic_base_url: str = _get("ANTHROPIC_BASE_URL")  
    anthropic_model: str = _get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    supabase_url: str = _get("SUPABASE_URL")
    supabase_key: str = _get("SUPABASE_KEY")

    embedding_provider: str = _get("EMBEDDING_PROVIDER", "auto")
    embedding_dim: int = int(_get("EMBEDDING_DIM", "384") or "384")

    store_backend: str = _get("STORE_BACKEND", "auto")
    local_db_path: str = _get("LOCAL_DB_PATH", "certhub_local.db")
    top_k: int = int(_get("TOP_K", "6") or "6")

    
    @property
    def llm_key(self) -> str:
        return self.anthropic_api_key or self.ai_gateway_api_key

    @property
    def using_gateway(self) -> bool:
        if self.anthropic_base_url:
            return "ai-gateway.vercel.sh" in self.anthropic_base_url
        return bool(self.ai_gateway_api_key and not self.anthropic_api_key)

    @property
    def llm_base_url(self) -> str | None:
        if self.anthropic_base_url:
            return self.anthropic_base_url
        if self.using_gateway:
            return _GATEWAY_URL
        return None  

    @property
    def model(self) -> str:

        m = self.anthropic_model
        if self.using_gateway and "/" not in m:
            return "anthropic/" + _VERSION_RE.sub(r"-\1.\2", m)
        return m

    
    @property
    def has_claude(self) -> bool:
        return bool(self.llm_key)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def use_supabase(self) -> bool:
        if self.store_backend == "supabase":
            return True
        if self.store_backend == "local":
            return False
        return self.has_supabase  

    def summary(self) -> str:
        if self.has_claude:
            via = "gateway" if self.using_gateway else "anthropic"
            auditor = f"claude:{self.model}@{via}"
        else:
            auditor = "heuristic-mock"
        return (
            f"store={'supabase' if self.use_supabase else 'local'} "
            f"auditor={auditor} "
            f"embeddings={self.embedding_provider} dim={self.embedding_dim}"
        )


CONFIG = Config()
