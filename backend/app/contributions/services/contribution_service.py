from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from app.contributions.models.entities import CONTRIBUTION_MODELS
from app.publications.models.entities import Faculty


def _mysql_nulls_last(column, *, descending: bool = False):
    """MySQL-compatible NULLS LAST ordering."""
    sort_key = case((column.is_(None), 1), else_=0)
    return [sort_key, column.desc() if descending else column.asc()]


def _base_stmt(model, *, faculty_id: int | None = None, resource: str = ""):
    order_parts = _mysql_nulls_last(model.faculty_id)
    order_parts.append(model.faculty_name.asc())
    if resource == "phd-students" and hasattr(model, "as_of_year"):
        order_parts.extend(_mysql_nulls_last(model.as_of_year, descending=True))
    elif hasattr(model, "exact_year"):
        order_parts.extend(_mysql_nulls_last(model.exact_year, descending=True))
    order_parts.append(model.id.asc())
    stmt = select(model).order_by(*order_parts)
    if faculty_id is not None:
        stmt = stmt.where(model.faculty_id == faculty_id)
    return stmt


def _apply_common_filters(
    stmt,
    model,
    resource: str,
    *,
    query: str | None,
    year: str | None,
    exact_year: int | None,
    faculty_id: int | None,
    unmatched_only: bool,
):
    if unmatched_only:
        stmt = stmt.where(model.faculty_id.is_(None))
    if year and hasattr(model, "year"):
        stmt = stmt.where(model.year == year.strip())
    if exact_year is not None:
        if resource == "phd-students" and hasattr(model, "as_of_year"):
            stmt = stmt.where(model.as_of_year == exact_year)
        elif hasattr(model, "exact_year"):
            stmt = stmt.where(model.exact_year == exact_year)
    if faculty_id is not None:
        stmt = stmt.where(model.faculty_id == faculty_id)
    if query:
        q = f"%{query.strip()}%"
        search_fields = _search_fields(resource)
        if search_fields:
            stmt = stmt.where(or_(*[getattr(model, f).ilike(q) for f in search_fields]))
    return stmt


def _search_fields(resource: str) -> list[str]:
    mapping = {
        "memberships": ["faculty_name", "society_name", "grade_position"],
        "resource-person-events": ["faculty_name", "program_name", "organized_by", "location"],
        "mooc-development": ["faculty_name", "course_name", "platform", "remarks"],
        "department-fdp-events": ["faculty_name", "program_name", "co_speakers"],
        "student-project-support": ["faculty_name", "event_name", "place"],
        "collaborations": ["faculty_name", "collaboration_type", "company_place", "outcomes"],
        "faculty-services": ["faculty_name", "role_title", "organization", "description"],
        "phd-students": ["faculty_name"],
    }
    return mapping.get(resource, ["faculty_name"])


def _apply_extra_filters(stmt, model, resource: str, extra_filter: str | None):
    token = (extra_filter or "").strip()
    if not token or token.upper() == "ALL":
        return stmt
    if resource == "mooc-development":
        if token.upper() == "NPTEL SWAYAM":
            return stmt.where(model.platform.ilike("%NPTEL%"))
        if token.upper() == "OTHER":
            return stmt.where(~model.platform.ilike("%NPTEL%"))
    if resource == "collaborations":
        return stmt.where(model.collaboration_type == token)
    if resource == "faculty-services":
        if token.upper() in ("INSTITUTE", "EXTERNAL"):
            return stmt.where(model.scope == token.title())
    return stmt


def list_contributions(
    db: Session,
    resource: str,
    *,
    query: str | None = None,
    year: str | None = None,
    exact_year: int | None = None,
    faculty_id: int | None = None,
    extra_filter: str | None = None,
    unmatched_only: bool = False,
) -> list:
    model = CONTRIBUTION_MODELS[resource]
    stmt = _base_stmt(model, resource=resource)
    stmt = _apply_common_filters(
        stmt,
        model,
        resource,
        query=query,
        year=year,
        exact_year=exact_year,
        faculty_id=faculty_id,
        unmatched_only=unmatched_only,
    )
    stmt = _apply_extra_filters(stmt, model, resource, extra_filter)
    return list(db.scalars(stmt).all())


def list_distinct_years(db: Session, resource: str) -> list[str]:
    model = CONTRIBUTION_MODELS[resource]
    if not hasattr(model, "year"):
        return []
    rows = db.scalars(select(model.year).distinct().order_by(model.year.desc())).all()
    return [r for r in rows if r]


def list_distinct_exact_years(db: Session, resource: str) -> list[int]:
    model = CONTRIBUTION_MODELS[resource]
    if resource == "phd-students" and hasattr(model, "as_of_year"):
        rows = db.scalars(
            select(model.as_of_year)
            .where(model.as_of_year.isnot(None))
            .distinct()
            .order_by(model.as_of_year.desc())
        ).all()
        return [int(r) for r in rows if r is not None]
    if not hasattr(model, "exact_year"):
        return []
    rows = db.scalars(
        select(model.exact_year)
        .where(model.exact_year.isnot(None))
        .distinct()
        .order_by(model.exact_year.desc())
    ).all()
    return [int(r) for r in rows if r is not None]


def list_distinct_extra_values(db: Session, resource: str) -> list[str]:
    if resource == "mooc-development":
        model = CONTRIBUTION_MODELS[resource]
        rows = db.scalars(select(model.platform).distinct().order_by(model.platform.asc())).all()
        return [r for r in rows if r]
    if resource == "collaborations":
        model = CONTRIBUTION_MODELS[resource]
        rows = db.scalars(select(model.collaboration_type).distinct().order_by(model.collaboration_type.asc())).all()
        return [r for r in rows if r]
    if resource == "faculty-services":
        return ["Institute", "External"]
    return []


def list_faculty_with_records(db: Session, resource: str) -> list[dict]:
    model = CONTRIBUTION_MODELS[resource]
    faculty_ids = {
        r
        for r in db.scalars(select(model.faculty_id).where(model.faculty_id.isnot(None)).distinct()).all()
        if r
    }
    id_to_name = {
        f.id: f.name for f in db.scalars(select(Faculty).where(Faculty.id.in_(faculty_ids))).all()
    } if faculty_ids else {}
    out = [{"id": fid, "name": id_to_name[fid]} for fid in sorted(id_to_name)]
    return out


def get_contribution(db: Session, resource: str, row_id: int):
    model = CONTRIBUTION_MODELS[resource]
    return db.get(model, row_id)


def _set_common_fields(row, data: dict[str, Any], faculty_name: str, faculty_id: int | None):
    row.faculty_name = faculty_name
    row.faculty_id = faculty_id
    if hasattr(row, "year"):
        row.year = (data.get("year") or "").strip() or None
    if hasattr(row, "exact_year"):
        row.exact_year = data.get("exact_year")
    row.updated_at = datetime.utcnow()


def _apply_specific_fields(row, resource: str, data: dict[str, Any]):
    if resource == "memberships":
        row.society_name = data["society_name"].strip()
        row.grade_position = data["grade_position"].strip()
    elif resource == "resource-person-events":
        row.program_name = data["program_name"].strip()
        row.event_date = data["event_date"].strip()
        row.location = data["location"].strip()
        row.organized_by = data["organized_by"].strip()
    elif resource == "mooc-development":
        row.course_name = data["course_name"].strip()
        row.platform = data["platform"].strip()
        row.remarks = (data.get("remarks") or "").strip() or None
    elif resource == "department-fdp-events":
        row.program_name = data["program_name"].strip()
        row.event_date = data["event_date"].strip()
        row.duration = data["duration"].strip()
        row.speaker_affiliation = (data.get("speaker_affiliation") or "").strip() or None
        row.co_speakers = (data.get("co_speakers") or "").strip() or None
        row.no_of_attendees = data.get("no_of_attendees")
    elif resource == "student-project-support":
        row.event_name = data["event_name"].strip()
        row.event_date = data["event_date"].strip()
        row.place = data["place"].strip()
        row.website_link = (data.get("website_link") or "").strip() or None
    elif resource == "collaborations":
        row.collaboration_type = data["collaboration_type"].strip()
        row.company_place = data["company_place"].strip()
        row.duration = data["duration"].strip()
        row.outcomes = data["outcomes"].strip()
    elif resource == "faculty-services":
        row.scope = data["scope"].strip()
        row.role_title = data["role_title"].strip()
        row.organization = (data.get("organization") or "").strip() or None
        row.start_date = (data.get("start_date") or "").strip() or None
        row.end_date = (data.get("end_date") or "").strip() or None
        row.duration_text = (data.get("duration_text") or "").strip() or None
        row.description = (data.get("description") or "").strip() or None
    elif resource == "phd-students":
        row.as_of_year = data.get("as_of_year")
        row.students_graduated = int(data.get("students_graduated") or 0)
        row.ongoing_phd_students = int(data.get("ongoing_phd_students") or 0)


def create_contribution(
    db: Session,
    resource: str,
    data: dict[str, Any],
    *,
    faculty_id: int,
    faculty_name: str,
):
    model = CONTRIBUTION_MODELS[resource]
    row = model()
    _set_common_fields(row, data, faculty_name, faculty_id)
    _apply_specific_fields(row, resource, data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_contribution(
    db: Session,
    resource: str,
    row,
    data: dict[str, Any],
    *,
    faculty_id: int,
    faculty_name: str,
):
    _set_common_fields(row, data, faculty_name, faculty_id)
    _apply_specific_fields(row, resource, data)
    db.commit()
    db.refresh(row)
    return row


def delete_contribution(db: Session, row) -> None:
    db.delete(row)
    db.commit()


def resolve_faculty_for_row(db: Session, row_id: int, resource: str, faculty_id: int) -> Any:
    from app.utils.contribution_faculty_resolver import add_alias, resolve_faculty_id_required

    row = get_contribution(db, resource, row_id)
    if not row:
        raise ValueError("Record not found")
    faculty = resolve_faculty_id_required(db, faculty_id)
    row.faculty_id = faculty.id
    row.faculty_name = row.faculty_name  # keep original import spelling
    add_alias(row.faculty_name, faculty.id)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
