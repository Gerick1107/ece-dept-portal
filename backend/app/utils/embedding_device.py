"""Pick CPU or CUDA for sentence-transformer embedding models."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_embedding_device(configured: str | None = None) -> str:
    """Return ``cuda`` when available and not forced to CPU, else ``cpu``."""
    pref = (configured or "auto").strip().lower()
    if pref in ("cpu", "cuda"):
        return pref
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            logger.info("Embedding device: cuda (%s)", name)
            return "cuda"
    except Exception:
        pass
    logger.info("Embedding device: cpu")
    return "cpu"
