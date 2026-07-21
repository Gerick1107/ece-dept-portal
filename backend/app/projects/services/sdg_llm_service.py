from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.utils.embedding_device import resolve_embedding_device

logger = logging.getLogger(__name__)

SDG_REFERENCE = [
    (1, "No Poverty", "End poverty in all its forms everywhere."),
    (2, "Zero Hunger", "End hunger, achieve food security and improved nutrition, and promote sustainable agriculture."),
    (3, "Good Health and Well-being", "Ensure healthy lives and promote well-being for all at all ages."),
    (4, "Quality Education", "Ensure inclusive and equitable quality education and lifelong learning opportunities for all."),
    (5, "Gender Equality", "Achieve gender equality and empower all women and girls."),
    (6, "Clean Water and Sanitation", "Ensure availability and sustainable management of water and sanitation for all."),
    (7, "Affordable and Clean Energy", "Ensure access to affordable, reliable, sustainable, and modern energy for all."),
    (8, "Decent Work and Economic Growth", "Promote sustained, inclusive and sustainable economic growth, full and productive employment."),
    (9, "Industry, Innovation and Infrastructure", "Build resilient infrastructure, promote inclusive industrialization and foster innovation."),
    (10, "Reduced Inequalities", "Reduce inequality within and among countries."),
    (11, "Sustainable Cities and Communities", "Make cities and human settlements inclusive, safe, resilient and sustainable."),
    (12, "Responsible Consumption and Production", "Ensure sustainable consumption and production patterns."),
    (13, "Climate Action", "Take urgent action to combat climate change and its impacts."),
    (14, "Life Below Water", "Conserve and sustainably use oceans, seas and marine resources."),
    (15, "Life on Land", "Protect, restore and promote sustainable use of terrestrial ecosystems and halt biodiversity loss."),
    (16, "Peace, Justice and Strong Institutions", "Promote peaceful and inclusive societies, justice for all and effective institutions."),
    (17, "Partnerships for the Goals", "Strengthen the means of implementation and revitalize the global partnership for sustainable development."),
]


def _load_sentence_transformer(model_name: str, device: str) -> SentenceTransformer:
    try:
        return SentenceTransformer(model_name, device=device)
    except Exception:
        # Misconfigured EMBEDDING_DEVICE=cuda (e.g. CPU-only torch in Docker)
        # must not break SDG tagging — fall back to CPU.
        if device != "cpu":
            logger.warning(
                "SDG embedding model failed on device '%s'; falling back to CPU.",
                device,
            )
            return SentenceTransformer(model_name, device="cpu")
        raise


@lru_cache(maxsize=1)
def _embedder() -> SentenceTransformer:
    settings = get_settings()
    device = resolve_embedding_device(getattr(settings, "embedding_device", "auto"))
    logger.info(
        "Loading SDG embedding model '%s' on device '%s'",
        settings.sdg_embedding_model,
        device,
    )
    return _load_sentence_transformer(settings.sdg_embedding_model, device)


@lru_cache(maxsize=1)
def _sdg_embeddings() -> np.ndarray:
    model = _embedder()
    corpus = [f"SDG {n}: {name}. {desc}" for n, name, desc in SDG_REFERENCE]
    vectors = model.encode(corpus, convert_to_numpy=True, normalize_embeddings=True)
    return np.asarray(vectors, dtype=np.float32)


SDG_CONFIDENCE_THRESHOLD = 0.5


def warm_up_sdg_embedder() -> None:
    """Pre-load the SDG embedding model so first tag requests don't time out."""
    try:
        _ = _sdg_embeddings()
        logger.info("SDG embedding model warmed up successfully")
    except Exception:
        logger.exception(
            "SDG embedding warmup failed — auto-tag and regenerate will fail until the model loads"
        )


def score_all_project_sdgs(project_title: str, project_type: str, project_abstract: str | None = None) -> list[dict]:
    """Return confidence scores for all 17 SDGs."""
    model = _embedder()
    text_parts = [f"Project type: {project_type}", f"Project title: {project_title}"]
    if project_abstract and project_abstract.strip():
        text_parts.append(f"Project abstract: {project_abstract.strip()}")
    query = "\n".join(text_parts)
    query_vec = model.encode(query, convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
    scores = _sdg_embeddings() @ query_vec
    return [
        {
            "sdg_number": SDG_REFERENCE[i][0],
            "confidence": float(max(0.0, min(1.0, scores[i]))),
        }
        for i in range(len(SDG_REFERENCE))
    ]


def suggest_project_sdgs(project_title: str, project_type: str, project_abstract: str | None = None) -> list[dict]:
    """SDGs at or above the auto-assignment threshold (≥50%)."""
    return [
        item
        for item in score_all_project_sdgs(project_title, project_type, project_abstract)
        if item["confidence"] >= SDG_CONFIDENCE_THRESHOLD
    ]
