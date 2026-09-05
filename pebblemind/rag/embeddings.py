"""Embedding backends for RAG: sentence-transformers, Ollama, zero-dep hash.

HashEmbedding is the zero-dependency default that lets RAG work on any Mac
with just numpy: deterministic hashed word-ngram vectors, L2-normalized so
cosine similarity works. Quality is below bge-small, but add/search works
offline with no downloads.
"""
import hashlib
import logging
import re
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class HashEmbedding:
    """Deterministic zero-dependency embedding model (numpy only)."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _text_to_vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = re.findall(r"\b\w+\b", text.lower())
        # unigrams + bigrams for a bit of phrase signal
        grams = list(tokens) + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]
        if not grams:
            return vec
        for g in grams:
            h = int(hashlib.md5(g.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
            vec[(h >> 16) % self.dim] += 0.5
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        """Encode texts -> (n, dim) float32 array (mirrors ST API)."""
        if isinstance(texts, str):
            texts = [texts]
        return np.stack([self._text_to_vector(t) for t in texts]).astype(np.float32)


class OllamaEmbedding:
    """Embeddings via Ollama /api/embed (e.g. nomic-embed-text)."""

    def __init__(self, model: str = "nomic-embed-text", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self._dim = None

    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        from ..core.backends import ollama_embed

        if isinstance(texts, str):
            texts = [texts]
        arr = ollama_embed(texts, model=self.model, host=self.host)
        self._dim = arr.shape[1]
        return arr
