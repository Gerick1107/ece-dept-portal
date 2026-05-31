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
from app.projects.services.sdg_llm_service import suggest_project_sdgs

logger = logging.getLogger(__name__)

_queue: Queue[int] = Queue()
_worker_lock = threading.Lock()
_worker_started = False


def sdg_llm_enabled() -> bool:
    return get_settings().enable_sdg_llm


def _process_project(project_id: int) -> None:
    if not sdg_llm_enabled():
        return
    settings = get_settings()
    db: Session = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if project is None:
            return
        suggestions = suggest_project_sdgs(project.project_title, project.project_type)
        if suggestions:
            apply_sdg_suggestions(db, project, suggestions)
    except Exception as exc:
        logger.warning("SDG auto-tag failed for project %s: %s", project_id, exc)
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


def enqueue_sdg_tags(project_ids: list[int]) -> int:
    if not project_ids or not sdg_llm_enabled():
        return 0
    _ensure_worker()
    for pid in project_ids:
        _queue.put(pid)
    return len(project_ids)


def tag_project_now(db: Session, project: Project) -> None:
    """Synchronous SDG tag (manual regenerate). No-op when LLM disabled."""
    if not sdg_llm_enabled():
        raise ValueError(
            "AI SDG tagging is disabled. Select SDGs manually and click Save edited SDGs."
        )
    suggestions = suggest_project_sdgs(project.project_title, project.project_type)
    if not suggestions:
        raise ValueError("No SDGs returned from model")
    apply_sdg_suggestions(db, project, suggestions)
