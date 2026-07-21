from __future__ import annotations

import logging
import threading
import time
from queue import Empty, Queue

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import SessionLocal
from app.projects.models.entities import Project
from app.projects.services.project_service import apply_sdg_suggestions
from app.projects.services.sdg_llm_service import score_all_project_sdgs

logger = logging.getLogger(__name__)

_queue: Queue[int] = Queue()
_worker_lock = threading.Lock()
_worker_started = False


def sdg_llm_enabled() -> bool:
    return get_settings().enable_sdg_llm


def _friendly_sdg_error(exc: BaseException) -> str:
    msg = str(exc).strip() or exc.__class__.__name__
    lower = msg.lower()
    if "out of memory" in lower or "oom" in lower or "cuda out of memory" in lower:
        return (
            "SDG tagging ran out of memory. Set EMBEDDING_DEVICE=cpu, "
            "reduce gunicorn workers, or use a smaller SDG_EMBEDDING_MODEL."
        )
    if any(
        token in lower
        for token in (
            "huggingface",
            "hf.co",
            "connection",
            "timed out",
            "name or service not known",
            "max retries",
            "failed to resolve",
            "offline",
        )
    ):
        return (
            "Could not download or load the SDG embedding model. "
            "Ensure the server can reach Hugging Face or pre-cache the model "
            f"(current model: {get_settings().sdg_embedding_model}). Detail: {msg}"
        )
    return f"SDG tagging failed: {msg}"


def _process_project(project_id: int) -> None:
    if not sdg_llm_enabled():
        return
    settings = get_settings()
    db: Session = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if project is None:
            return
        all_scores = score_all_project_sdgs(project.project_title, project.project_type)
        if all_scores:
            apply_sdg_suggestions(db, project, all_scores)
            logger.info("SDG auto-tag completed for project %s", project_id)
        else:
            logger.warning("SDG auto-tag returned no scores for project %s", project_id)
    except Exception as exc:
        logger.exception("SDG auto-tag failed for project %s: %s", project_id, _friendly_sdg_error(exc))
    finally:
        db.close()
        if sdg_llm_enabled():
            time.sleep(settings.sdg_request_delay_seconds)


def _worker_loop() -> None:
    while True:
        try:
            project_id = _queue.get(timeout=2.0)
        except Empty:
            continue
        try:
            _process_project(project_id)
        finally:
            _queue.task_done()


def _ensure_worker() -> None:
    global _worker_started
    if not sdg_llm_enabled():
        return
    with _worker_lock:
        if _worker_started:
            return
        thread = threading.Thread(target=_worker_loop, daemon=True, name="sdg-tag-worker")
        thread.start()
        _worker_started = True
        logger.info("SDG auto-tag worker started")


def ensure_sdg_worker() -> None:
    """Start the background SDG tagging worker if LLM tagging is enabled."""
    _ensure_worker()


def enqueue_sdg_tags(project_ids: list[int]) -> int:
    if not project_ids:
        return 0
    if not sdg_llm_enabled():
        logger.warning(
            "SDG auto-tag skipped for %s project(s): ENABLE_SDG_LLM is false",
            len(project_ids),
        )
        return 0
    _ensure_worker()
    for pid in project_ids:
        _queue.put(pid)
    logger.info("Queued SDG auto-tag for %s project(s)", len(project_ids))
    return len(project_ids)


def tag_project_now(db: Session, project: Project) -> None:
    """Synchronous SDG tag (manual regenerate). Raises ValueError with a clear message on failure."""
    if not sdg_llm_enabled():
        raise ValueError(
            "AI SDG tagging is disabled. Select SDGs manually and click Save edited SDGs."
        )
    try:
        all_scores = score_all_project_sdgs(project.project_title, project.project_type)
    except Exception as exc:
        logger.exception("SDG regenerate failed for project %s", project.id)
        raise ValueError(_friendly_sdg_error(exc)) from exc
    if not all_scores:
        raise ValueError("No SDGs returned from model")
    apply_sdg_suggestions(db, project, all_scores)
