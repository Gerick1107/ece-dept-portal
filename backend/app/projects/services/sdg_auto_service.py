from __future__ import annotations

from sqlalchemy.orm import Session

from app.projects.models.entities import Project
from app.projects.services.sdg_queue import enqueue_sdg_tags, sdg_llm_enabled


def queue_auto_tag_project(db: Session, project: Project) -> None:
    """Queue background SDG tagging when LLM integration is enabled."""
    if sdg_llm_enabled():
        enqueue_sdg_tags([project.id])
