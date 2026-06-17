from __future__ import annotations

import hashlib
import re
from functools import lru_cache

import numpy as np

from .config import CONFIG

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _l2(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


class _HashingEmbedder:
    """Hashing trick + token-bigrams.
    """

    name = "hashing"

    def __init__(self, dim: int):
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        toks = _TOKEN_RE.findall(text.lower())
        grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        v = np.zeros(self.dim, dtype=np.float32)
        for g in grams:
            h = int.from_bytes(hashlib.md5(g.encode()).digest()[:8], "little")
            v[h % self.dim] += 1.0 if (h >> 63) & 1 == 0 else -1.0
        return _l2(v)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t).tolist() for t in texts]


class _STEmbedder:
    name = "sentence-transformers"

    def __init__(self, dim: int):
        from sentence_transformers import SentenceTransformer  

        self._model = SentenceTransformer("all-MiniLM-L6-v2")
        self.dim = self._model.get_sentence_embedding_dimension()
        if self.dim != dim:
            
            raise ValueError(
                f"EMBEDDING_DIM={dim} but model emits {self.dim}. "
                f"Set EMBEDDING_DIM={self.dim} and the migration's vector({self.dim})."
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        arr = self._model.encode(texts, normalize_embeddings=True)
        return [row.tolist() for row in np.asarray(arr, dtype=np.float32)]


@lru_cache(maxsize=1)
def get_embedder():
    provider = CONFIG.embedding_provider
    if provider in ("auto", "sentence-transformers"):
        try:
            return _STEmbedder(CONFIG.embedding_dim)
        except Exception:
            if provider == "sentence-transformers":
                raise
            
    return _HashingEmbedder(CONFIG.embedding_dim)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return get_embedder().embed(texts)


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
