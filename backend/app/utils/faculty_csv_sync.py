"""Re-runnable CSV ↔ DB sync for faculty_awards and faculty contribution tables."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_ASSETS

T = TypeVar("T")


def _parse_optional_int(value: str | None) -> int | None:
    raw = (value or "").strip()
    if not raw or raw == "###":
        return None
    return int(raw) if raw.isdigit() else None


def _csv_ids(rows: list[dict[str, str]]) -> set[int]:
    ids: set[int] = set()
    for row in rows:
        raw = (row.get("id") or "").strip()
        if raw.isdigit():
            ids.add(int(raw))
    return ids


def _delete_csv_removed_rows(db: Session, model, csv_ids: set[int]) -> None:
    """Remove DB rows whose id fell within the CSV id range but are no longer in the file."""
    if not csv_ids:
        return
    max_id = max(csv_ids)
    rows = db.scalars(select(model.id).where(model.id <= max_id)).all()
    for row_id in rows:
        if row_id not in csv_ids:
            row = db.get(model, row_id)
            if row:
                db.delete(row)


def sync_csv_rows(
    db: Session,
    csv_path: Path,
    *,
    model,
    natural_key: Callable[[dict[str, str]], tuple | None],
    find_existing: Callable[[Session, tuple], T | None],
    find_by_id: Callable[[Session, int], T | None],
    build_row: Callable[[dict[str, str]], T],
    apply_row: Callable[[T, dict[str, str]], bool],
) -> None:
    if not csv_path.exists():
        return

    rows: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    csv_ids = _csv_ids(rows)
    _delete_csv_removed_rows(db, model, csv_ids)

    for row in rows:
        key = natural_key(row)
        if not key:
            continue
        row_id = _parse_optional_int(row.get("id"))
        existing = find_by_id(db, row_id) if row_id else None
        if not existing:
            existing = find_existing(db, key)
        if existing:
            apply_row(existing, row)
            continue
        db.add(build_row(row))
    db.commit()


def sync_faculty_awards_csv(db: Session, csv_path: Path | None = None) -> None:
    from app.awards.models.entities import FacultyAward

    path = csv_path or (DATA_ASSETS / "faculty_awards.csv")

    def natural_key(row: dict[str, str]) -> tuple | None:
        faculty_name = (row.get("faculty_name") or "").strip()
        year = (row.get("year") or "").strip()
        award = (row.get("award") or "").strip()
        if not faculty_name or not year or not award:
            return None
        return (faculty_name, year, award)

    def find_existing(db: Session, key: tuple) -> FacultyAward | None:
        faculty_name, year, award = key
        return db.scalar(
            select(FacultyAward).where(
                FacultyAward.faculty_name == faculty_name,
                FacultyAward.year == year,
                FacultyAward.award == award,
            )
        )

    def find_by_id(db: Session, row_id: int) -> FacultyAward | None:
        return db.get(FacultyAward, row_id)

    def build_row(row: dict[str, str]) -> FacultyAward:
        row_id = _parse_optional_int(row.get("id"))
        entity = FacultyAward(
            faculty_name=row["faculty_name"].strip(),
            year=row["year"].strip(),
            award=row["award"].strip(),
            exact_year=_parse_optional_int(row.get("exact_year")),
            awarded_by=(row.get("awarded_by") or "").strip() or None,
        )
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing: FacultyAward, row: dict[str, str]) -> bool:
        changed = False
        exact_year = _parse_optional_int(row.get("exact_year"))
        awarded_by = (row.get("awarded_by") or "").strip() or None
        if exact_year is not None and existing.exact_year != exact_year:
            existing.exact_year = exact_year
            changed = True
        if awarded_by and existing.awarded_by != awarded_by:
            existing.awarded_by = awarded_by
            changed = True
        return changed

    sync_csv_rows(
        db,
        path,
        model=FacultyAward,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )


def _sync_contribution_csv(
    db: Session,
    *,
    csv_filename: str,
    model,
    key_fields: tuple[str, ...],
    natural_key_fn: Callable[[dict[str, str]], tuple | None],
    build_fields: Callable[[dict[str, str]], dict],
    apply_fields: Callable[[object, dict[str, str]], bool],
) -> None:
    from app.utils.contribution_faculty_resolver import resolve_faculty_id

    path = DATA_ASSETS / csv_filename

    def find_existing(db: Session, key: tuple):
        clauses = [getattr(model, field) == val for field, val in zip(key_fields, key)]
        return db.scalar(select(model).where(*clauses))

    def find_by_id(db: Session, row_id: int):
        return db.get(model, row_id)

    def build_row(row: dict[str, str]):
        row_id = _parse_optional_int(row.get("id"))
        fields = build_fields(row)
        faculty_name = row["faculty_name"].strip()
        resolved = resolve_faculty_id(db, faculty_name)
        faculty_id = resolved.faculty_id if hasattr(resolved, "faculty_id") else None
        entity = model(
            faculty_name=faculty_name,
            faculty_id=faculty_id,
            year=(row.get("year") or "").strip() or None,
            exact_year=_parse_optional_int(row.get("exact_year")),
            **fields,
        )
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing, row: dict[str, str]) -> bool:
        changed = apply_fields(existing, row)
        resolved = resolve_faculty_id(db, row["faculty_name"].strip())
        faculty_id = resolved.faculty_id if hasattr(resolved, "faculty_id") else None
        if existing.faculty_id != faculty_id:
            existing.faculty_id = faculty_id
            changed = True
        yr = (row.get("year") or "").strip() or None
        if existing.year != yr:
            existing.year = yr
            changed = True
        exact_year = _parse_optional_int(row.get("exact_year"))
        if exact_year is not None and existing.exact_year != exact_year:
            existing.exact_year = exact_year
            changed = True
        return changed

    def natural_key(row: dict[str, str]) -> tuple | None:
        return natural_key_fn(row)

    sync_csv_rows(
        db,
        path,
        model=model,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )


def sync_faculty_memberships_csv(db: Session) -> None:
    from app.contributions.models.entities import FacultyMembership

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        sn = (row.get("society_name") or "").strip()
        gp = (row.get("grade_position") or "").strip()
        if not fn or not sn:
            return None
        return (fn, sn, gp)

    def build_fields(row: dict[str, str]) -> dict:
        return {
            "society_name": row["society_name"].strip(),
            "grade_position": row["grade_position"].strip(),
        }

    def apply_fields(existing, row: dict[str, str]) -> bool:
        return False

    _sync_contribution_csv(
        db,
        csv_filename="faculty_memberships.csv",
        model=FacultyMembership,
        key_fields=("faculty_name", "society_name", "grade_position"),
        natural_key_fn=natural_key,
        build_fields=build_fields,
        apply_fields=apply_fields,
    )


def sync_faculty_resource_person_events_csv(db: Session) -> None:
    from app.contributions.models.entities import FacultyResourcePersonEvent

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        pn = (row.get("program_name") or "").strip()
        ed = (row.get("event_date") or "").strip()
        if not fn or not pn:
            return None
        return (fn, pn, ed)

    def build_fields(row: dict[str, str]) -> dict:
        return {
            "program_name": row["program_name"].strip(),
            "event_date": row["event_date"].strip(),
            "location": row["location"].strip(),
            "organized_by": row["organized_by"].strip(),
        }

    def apply_fields(existing, row: dict[str, str]) -> bool:
        changed = False
        for attr in ("location", "organized_by"):
            val = row[attr].strip()
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        return changed

    _sync_contribution_csv(
        db,
        csv_filename="faculty_resource_person_events.csv",
        model=FacultyResourcePersonEvent,
        key_fields=("faculty_name", "program_name", "event_date"),
        natural_key_fn=natural_key,
        build_fields=build_fields,
        apply_fields=apply_fields,
    )


def sync_faculty_mooc_development_csv(db: Session) -> None:
    from app.contributions.models.entities import FacultyMoocDevelopment

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        cn = (row.get("course_name") or "").strip()
        if not fn or not cn:
            return None
        return (fn, cn)

    def build_fields(row: dict[str, str]) -> dict:
        return {
            "course_name": row["course_name"].strip(),
            "platform": row["platform"].strip(),
            "remarks": (row.get("remarks") or "").strip() or None,
        }

    def apply_fields(existing, row: dict[str, str]) -> bool:
        changed = False
        for attr in ("platform", "remarks"):
            val = (row.get(attr) or "").strip() or None
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        return changed

    _sync_contribution_csv(
        db,
        csv_filename="faculty_mooc_development.csv",
        model=FacultyMoocDevelopment,
        key_fields=("faculty_name", "course_name"),
        natural_key_fn=natural_key,
        build_fields=build_fields,
        apply_fields=apply_fields,
    )


def sync_department_fdp_events_csv(db: Session) -> None:
    from app.contributions.models.entities import DepartmentFdpEvent

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        pn = (row.get("program_name") or "").strip()
        ed = (row.get("event_date") or "").strip()
        if not fn or not pn:
            return None
        return (fn, pn, ed)

    def build_fields(row: dict[str, str]) -> dict:
        return {
            "program_name": row["program_name"].strip(),
            "event_date": row["event_date"].strip(),
            "duration": row["duration"].strip(),
            "speaker_affiliation": (row.get("speaker_affiliation") or "").strip() or None,
            "co_speakers": (row.get("co_speakers") or "").strip() or None,
            "no_of_attendees": _parse_optional_int(row.get("no_of_attendees")),
        }

    def apply_fields(existing, row: dict[str, str]) -> bool:
        changed = False
        for attr in ("duration", "speaker_affiliation", "co_speakers"):
            val = (row.get(attr) or "").strip() or None
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        attendees = _parse_optional_int(row.get("no_of_attendees"))
        if attendees is not None and existing.no_of_attendees != attendees:
            existing.no_of_attendees = attendees
            changed = True
        return changed

    _sync_contribution_csv(
        db,
        csv_filename="department_fdp_events.csv",
        model=DepartmentFdpEvent,
        key_fields=("faculty_name", "program_name", "event_date"),
        natural_key_fn=natural_key,
        build_fields=build_fields,
        apply_fields=apply_fields,
    )


def sync_faculty_student_project_support_csv(db: Session) -> None:
    from app.contributions.models.entities import FacultyStudentProjectSupport

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        en = (row.get("event_name") or "").strip()
        ed = (row.get("event_date") or "").strip()
        if not fn or not en:
            return None
        return (fn, en, ed)

    def build_fields(row: dict[str, str]) -> dict:
        return {
            "event_name": row["event_name"].strip(),
            "event_date": row["event_date"].strip(),
            "place": row["place"].strip(),
            "website_link": (row.get("website_link") or "").strip() or None,
        }

    def apply_fields(existing, row: dict[str, str]) -> bool:
        changed = False
        for attr in ("place", "website_link"):
            val = (row.get(attr) or "").strip() or None
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        return changed

    _sync_contribution_csv(
        db,
        csv_filename="faculty_student_project_support.csv",
        model=FacultyStudentProjectSupport,
        key_fields=("faculty_name", "event_name", "event_date"),
        natural_key_fn=natural_key,
        build_fields=build_fields,
        apply_fields=apply_fields,
    )


def sync_faculty_collaborations_csv(db: Session) -> None:
    from app.contributions.models.entities import FacultyCollaboration

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        ct = (row.get("collaboration_type") or "").strip()
        cp = (row.get("company_place") or "").strip()
        if not fn or not ct:
            return None
        return (fn, ct, cp)

    def build_fields(row: dict[str, str]) -> dict:
        return {
            "collaboration_type": row["collaboration_type"].strip(),
            "company_place": row["company_place"].strip(),
            "duration": row["duration"].strip(),
            "outcomes": row["outcomes"].strip(),
        }

    def apply_fields(existing, row: dict[str, str]) -> bool:
        changed = False
        for attr in ("duration", "outcomes"):
            val = row[attr].strip()
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        return changed

    _sync_contribution_csv(
        db,
        csv_filename="faculty_collaborations.csv",
        model=FacultyCollaboration,
        key_fields=("faculty_name", "collaboration_type", "company_place"),
        natural_key_fn=natural_key,
        build_fields=build_fields,
        apply_fields=apply_fields,
    )


def sync_faculty_services_csv(db: Session) -> None:
    from app.contributions.models.entities import FacultyService

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        yr = (row.get("year") or "").strip()
        role = (row.get("role_title") or "").strip()
        scope = (row.get("scope") or "").strip()
        if not fn or not role:
            return None
        return (fn, yr, role, scope)

    def build_fields(row: dict[str, str]) -> dict:
        return {
            "scope": row["scope"].strip(),
            "role_title": row["role_title"].strip(),
            "organization": (row.get("organization") or "").strip() or None,
            "start_date": (row.get("start_date") or "").strip() or None,
            "end_date": (row.get("end_date") or "").strip() or None,
            "duration_text": (row.get("duration_text") or "").strip() or None,
            "description": (row.get("description") or "").strip() or None,
        }

    def apply_fields(existing, row: dict[str, str]) -> bool:
        changed = False
        for attr in ("organization", "start_date", "end_date", "duration_text", "description"):
            val = (row.get(attr) or "").strip() or None
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        return changed

    _sync_contribution_csv(
        db,
        csv_filename="faculty_services.csv",
        model=FacultyService,
        key_fields=("faculty_name", "year", "role_title", "scope"),
        natural_key_fn=natural_key,
        build_fields=build_fields,
        apply_fields=apply_fields,
    )


def sync_phd_students_csv(db: Session) -> None:
    from app.contributions.models.entities import PhdStudent
    from app.utils.contribution_faculty_resolver import resolve_faculty_id

    path = DATA_ASSETS / "phd_students.csv"

    def natural_key(row: dict[str, str]) -> tuple | None:
        fn = (row.get("faculty_name") or "").strip()
        ay = (row.get("as_of_year") or "").strip()
        if not fn:
            return None
        return (fn, ay)

    def find_existing(db: Session, key: tuple):
        fn, ay = key
        stmt = select(PhdStudent).where(PhdStudent.faculty_name == fn)
        if ay.isdigit():
            stmt = stmt.where(PhdStudent.as_of_year == int(ay))
        else:
            stmt = stmt.where(PhdStudent.as_of_year.is_(None))
        return db.scalar(stmt)

    def find_by_id(db: Session, row_id: int):
        return db.get(PhdStudent, row_id)

    def build_row(row: dict[str, str]) -> PhdStudent:
        row_id = _parse_optional_int(row.get("id"))
        faculty_name = row["faculty_name"].strip()
        resolved = resolve_faculty_id(db, faculty_name)
        faculty_id = resolved.faculty_id if hasattr(resolved, "faculty_id") else None
        entity = PhdStudent(
            faculty_name=faculty_name,
            faculty_id=faculty_id,
            as_of_year=_parse_optional_int(row.get("as_of_year")),
            students_graduated=int((row.get("students_graduated") or "0").strip() or 0),
            ongoing_phd_students=int((row.get("ongoing_phd_students") or "0").strip() or 0),
        )
        if row_id is not None:
            entity.id = row_id
        return entity

    def apply_row(existing: PhdStudent, row: dict[str, str]) -> bool:
        changed = False
        for attr, key in (
            ("as_of_year", "as_of_year"),
            ("students_graduated", "students_graduated"),
            ("ongoing_phd_students", "ongoing_phd_students"),
        ):
            if key == "as_of_year":
                val = _parse_optional_int(row.get(key))
            else:
                val = int((row.get(key) or "0").strip() or 0)
            if getattr(existing, attr) != val:
                setattr(existing, attr, val)
                changed = True
        resolved = resolve_faculty_id(db, row["faculty_name"].strip())
        faculty_id = resolved.faculty_id if hasattr(resolved, "faculty_id") else None
        if existing.faculty_id != faculty_id:
            existing.faculty_id = faculty_id
            changed = True
        return changed

    sync_csv_rows(
        db,
        path,
        model=PhdStudent,
        natural_key=natural_key,
        find_existing=find_existing,
        find_by_id=find_by_id,
        build_row=build_row,
        apply_row=apply_row,
    )


CONTRIBUTION_SYNC_MAP = {
    "memberships": sync_faculty_memberships_csv,
    "resource-person-events": sync_faculty_resource_person_events_csv,
    "mooc-development": sync_faculty_mooc_development_csv,
    "department-fdp-events": sync_department_fdp_events_csv,
    "student-project-support": sync_faculty_student_project_support_csv,
    "collaborations": sync_faculty_collaborations_csv,
    "faculty-services": sync_faculty_services_csv,
    "phd-students": sync_phd_students_csv,
}


def sync_contribution_csv(db: Session, resource: str) -> None:
    fn = CONTRIBUTION_SYNC_MAP.get(resource)
    if fn:
        fn(db)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _dt_str(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def write_faculty_services_csv(db: Session) -> None:
    from app.contributions.models.entities import FacultyService

    rows_db = list(db.scalars(select(FacultyService).order_by(FacultyService.id)).all())
    fieldnames = [
        "id",
        "faculty_name",
        "year",
        "exact_year",
        "scope",
        "role_title",
        "organization",
        "start_date",
        "end_date",
        "duration_text",
        "description",
        "created_at",
        "updated_at",
    ]
    data = [
        {
            "id": str(r.id),
            "faculty_name": r.faculty_name,
            "year": r.year or "",
            "exact_year": str(r.exact_year) if r.exact_year is not None else "",
            "scope": r.scope,
            "role_title": r.role_title,
            "organization": r.organization or "",
            "start_date": r.start_date or "",
            "end_date": r.end_date or "",
            "duration_text": r.duration_text or "",
            "description": r.description or "",
            "created_at": _dt_str(r.created_at),
            "updated_at": _dt_str(r.updated_at),
        }
        for r in rows_db
    ]
    _write_csv(DATA_ASSETS / "faculty_services.csv", fieldnames, data)


def write_phd_students_csv(db: Session) -> None:
    from app.contributions.models.entities import PhdStudent

    rows_db = list(db.scalars(select(PhdStudent).order_by(PhdStudent.id)).all())
    fieldnames = [
        "id",
        "faculty_name",
        "as_of_year",
        "students_graduated",
        "ongoing_phd_students",
        "created_at",
        "updated_at",
    ]
    data = [
        {
            "id": str(r.id),
            "faculty_name": r.faculty_name,
            "as_of_year": str(r.as_of_year) if r.as_of_year is not None else "",
            "students_graduated": str(r.students_graduated),
            "ongoing_phd_students": str(r.ongoing_phd_students),
            "created_at": _dt_str(r.created_at),
            "updated_at": _dt_str(r.updated_at),
        }
        for r in rows_db
    ]
    _write_csv(DATA_ASSETS / "phd_students.csv", fieldnames, data)


CONTRIBUTION_WRITE_MAP = {
    "faculty-services": write_faculty_services_csv,
    "phd-students": write_phd_students_csv,
}


def write_contribution_csv(db: Session, resource: str) -> None:
    fn = CONTRIBUTION_WRITE_MAP.get(resource)
    if fn:
        fn(db)
