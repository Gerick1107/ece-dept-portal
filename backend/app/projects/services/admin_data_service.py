from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.projects.models.entities import ProjectUpload


def list_project_uploads(db: Session, limit: int = 200) -> list[dict]:
    rows = (
        db.query(ProjectUpload)
        .order_by(ProjectUpload.uploaded_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "filename": row.filename,
            "filepath": row.filepath,
            "uploaded_by": row.uploaded_by,
            "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
            "record_count": row.record_count,
        }
        for row in rows
    ]


def purge_all_projects(db: Session) -> dict:
    """Delete all BTP/IP projects, links, upload metadata, and files on disk."""
    import shutil

    from app.config import get_settings
    from app.projects.models.entities import Project, ProjectSdg, ProjectStudent, ProjectUpload

    settings = get_settings()
    uploads_dir = Path(settings.projects_upload_dir)

    removed_files = 0
    for upload in db.query(ProjectUpload).all():
        path = Path(upload.filepath)
        if path.exists():
            try:
                path.unlink()
                removed_files += 1
            except OSError:
                pass

    db.query(ProjectSdg).delete()
    db.query(ProjectStudent).delete()
    db.query(Project).delete()
    db.query(ProjectUpload).delete()
    db.commit()

    if uploads_dir.exists():
        for child in uploads_dir.iterdir():
            try:
                if child.is_file():
                    child.unlink()
                    removed_files += 1
                elif child.is_dir():
                    shutil.rmtree(child)
            except OSError:
                pass

    return {"purged": True, "removed_files": removed_files}


def delete_project_upload(db: Session, upload_id: int) -> dict:
    row = db.query(ProjectUpload).filter(ProjectUpload.id == upload_id).first()
    if not row:
        return {"deleted": False}
    path = Path(row.filepath)
    if path.exists():
        try:
            os.remove(path)
        except OSError:
            pass
    db.delete(row)
    db.commit()
    return {"deleted": True}
