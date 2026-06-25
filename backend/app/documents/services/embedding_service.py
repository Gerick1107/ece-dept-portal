"""Sentence-transformer embeddings for document-chunk retrieval."""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings

_DEFAULT_RAG_MODEL = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _embedder() -> SentenceTransformer:
    settings = get_settings()
    model_name = getattr(settings, "rag_embedding_model", None) or _DEFAULT_RAG_MODEL
    return SentenceTransformer(model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _embedder()
    vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return [row.astype(np.float32).tolist() for row in np.asarray(vectors)]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def embedding_to_json(vector: list[float]) -> str:
    return json.dumps(vector, separators=(",", ":"))


def embedding_from_json(payload: str | None) -> np.ndarray | None:
    if not payload:
        return None
    try:
        data = json.loads(payload)
        return np.asarray(data, dtype=np.float32)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def cosine_similarity(query_vec: np.ndarray, doc_vec: np.ndarray) -> float:
    return float(np.dot(query_vec, doc_vec))
