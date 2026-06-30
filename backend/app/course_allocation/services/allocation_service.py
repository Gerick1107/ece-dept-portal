from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.course_allocation.models.entities import CourseAllocation, CourseCatalogEntry, CourseCodeAlias
from app.course_allocation.services.allocation_faculty_resolver import (
    is_placeholder_name,
    resolve_allocation_faculty,
)
from app.course_allocation.services.course_identity_resolver import (
    collapse_repeated_dept_prefix,
    tokenize_course_codes,
)
from app.course_allocation.services.csv_sync import write_allocations_csv, write_catalog_csv
from app.analytics.utils.semester import semester_sort_key
from app.course_allocation.services.semester_service import scope_semesters
from app.publications.models.entities import Faculty
from app.utils.contribution_faculty_resolver import FacultyResolveFailure, FacultyResolveResult


def _active_faculty(db: Session) -> list[Faculty]:
    return list(
        db.scalars(
            select(Faculty)
            .where(Faculty.is_active.is_(True))
            .order_by(Faculty.name.asc())
        ).all()
    )


def list_allocations_view(
    db: Session,
    *,
    scope: str | None = None,
    query: str | None = None,
    ug_pg: str | None = None,
    core_elective: str | None = None,
    first_year_only: bool = False,
) -> dict:
    semesters = scope_semesters(scope)
    stmt = select(CourseAllocation)
    if semesters:
        stmt = stmt.where(CourseAllocation.semester.in_(semesters))
    if ug_pg and ug_pg.upper() != "ALL":
        stmt = stmt.where(CourseAllocation.ug_pg == ug_pg)
    if core_elective and core_elective.upper() != "ALL":
        stmt = stmt.where(CourseAllocation.core_elective == core_elective)
    if first_year_only:
        stmt = stmt.where(CourseAllocation.is_first_year.is_(True))
    if query:
        q = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                CourseAllocation.faculty_name.ilike(q),
                CourseAllocation.course_code.ilike(q),
                CourseAllocation.course_name.ilike(q),
            )
        )
    allocations = list(db.scalars(stmt).all())

    placeholders = [a for a in allocations if a.is_faculty_placeholder]
    real = [a for a in allocations if not a.is_faculty_placeholder]

    by_faculty: dict[int, list[CourseAllocation]] = {}
    unmatched: list[CourseAllocation] = []
    for row in real:
        if row.faculty_id:
            by_faculty.setdefault(row.faculty_id, []).append(row)
        else:
            unmatched.append(row)

    faculty_rows = []
    for faculty in _active_faculty(db):
        courses = sorted(
            by_faculty.get(faculty.id, []),
            key=lambda c: (semester_sort_key(c.semester), c.course_code),
        )
        # Newest semester first; stable sort keeps course_code ascending within a term.
        courses = sorted(courses, key=lambda c: semester_sort_key(c.semester), reverse=True)
        faculty_rows.append(
            {
                "faculty_id": faculty.id,
                "faculty_name": faculty.name,
                "courses": [_allocation_dict(c) for c in courses],
                "has_courses": bool(courses),
            }
        )

    faculty_rows.sort(key=lambda r: r["faculty_name"])

    all_semesters = [
        s for s in db.scalars(select(CourseAllocation.semester).distinct()).all() if s
    ]
    semester_set = sorted(set(all_semesters), key=semester_sort_key, reverse=True)
    all_academic_years = sorted(
        {ay for ay in db.scalars(select(CourseAllocation.academic_year).distinct()).all() if ay},
        reverse=True,
    )

    return {
        "faculty_rows": faculty_rows,
        "unassigned": [_allocation_dict(p) for p in placeholders],
        "unmatched": [_allocation_dict(u) for u in unmatched],
        "semesters": semester_set,
        "academic_years": all_academic_years,
    }


def _allocation_dict(row: CourseAllocation) -> dict:
    return {
        "id": row.id,
        "faculty_name": row.faculty_name,
        "faculty_id": row.faculty_id,
        "semester": row.semester,
        "academic_year": row.academic_year,
        "course_code": row.course_code,
        "course_name": row.course_name,
        "ug_pg": row.ug_pg,
        "core_elective": row.core_elective,
        "is_first_year": row.is_first_year,
        "first_year_course_name": row.first_year_course_name,
        "source": row.source,
        "is_faculty_placeholder": row.is_faculty_placeholder,
    }


def dashboard_summary(db: Session, semester: str) -> dict:
    rows = list(
        db.scalars(select(CourseAllocation).where(CourseAllocation.semester == semester)).all()
    )
    real = [r for r in rows if not r.is_faculty_placeholder and r.faculty_id]
    faculty_ids = {r.faculty_id for r in real}
    return {
        "semester": semester,
        "faculty_teaching": len(faculty_ids),
        "total_courses": len(rows),
        "ug_courses": sum(1 for r in rows if r.ug_pg == "UG"),
        "pg_courses": sum(1 for r in rows if r.ug_pg == "PG"),
        "ug_pg_courses": sum(1 for r in rows if r.ug_pg == "UG/PG"),
        "core_courses": sum(1 for r in rows if r.core_elective == "Core"),
        "elective_courses": sum(1 for r in rows if r.core_elective == "Elective"),
        "first_year_courses": sum(1 for r in rows if r.is_first_year),
        "unassigned": sum(1 for r in rows if r.is_faculty_placeholder),
    }


def faculty_history(db: Session, faculty_id: int) -> dict | None:
    faculty = db.get(Faculty, faculty_id)
    if not faculty:
        return None
    rows = list(
        db.scalars(
            select(CourseAllocation).where(
                CourseAllocation.faculty_id == faculty_id,
                CourseAllocation.is_faculty_placeholder.is_(False),
            )
        ).all()
    )
    rows.sort(key=lambda r: (semester_sort_key(r.semester), r.course_code))
    # Full history table shows newest semester first; ties keep course_code ascending
    # (stable sort preserves the secondary ordering established above).
    history_rows = sorted(rows, key=lambda r: semester_sort_key(r.semester), reverse=True)
    history = [_allocation_dict(r) for r in history_rows]

    course_counts: dict[str, dict] = {}
    for r in rows:
        key = str(r.course_catalog_id) if r.course_catalog_id else r.course_code
        entry = course_counts.setdefault(
            key,
            {
                "course_code": r.course_code,
                "course_name": r.course_name,
                "times_taught": 0,
                "semesters": [],
                "most_recent_semester": r.semester,
            },
        )
        entry["times_taught"] += 1
        entry["semesters"].append(r.semester)
        if semester_sort_key(r.semester) >= semester_sort_key(entry["most_recent_semester"]):
            entry["most_recent_semester"] = r.semester

    first_year: dict[str, int] = {}
    for r in rows:
        if r.is_first_year:
            label = r.first_year_course_name or r.course_name
            first_year[label] = first_year.get(label, 0) + 1

    by_semester: dict[str, int] = {}
    ug_pg = {"UG": 0, "PG": 0, "UG/PG": 0}
    core_elective = {"Core": 0, "Elective": 0, "Core/Elective": 0}
    for r in rows:
        by_semester[r.semester] = by_semester.get(r.semester, 0) + 1
        if r.ug_pg in ug_pg:
            ug_pg[r.ug_pg] += 1
        if r.core_elective in core_elective:
            core_elective[r.core_elective] += 1

    for entry in course_counts.values():
        entry["semesters"] = sorted(entry["semesters"], key=semester_sort_key)

    return {
        "faculty": {"id": faculty.id, "name": faculty.name},
        "history": history,
        "course_counts": list(course_counts.values()),
        "first_year_counts": [{"name": k, "count": v} for k, v in sorted(first_year.items())],
        "analytics": {
            "courses_per_semester": [
                {"semester": k, "count": v}
                for k, v in sorted(by_semester.items(), key=lambda x: semester_sort_key(x[0]))
            ],
            "ug_pg_split": ug_pg,
            "core_elective_split": core_elective,
        },
    }


def _build_catalog_lookup(db: Session) -> tuple[dict[str, CourseCatalogEntry], dict[str, CourseCatalogEntry]]:
    """Map variant codes and individual code tokens to canonical catalog entries."""
    variant_to_course: dict[str, CourseCatalogEntry] = {}
    token_to_course: dict[str, CourseCatalogEntry] = {}
    for entry in db.scalars(select(CourseCatalogEntry)).all():
        variant_to_course[entry.course_code.strip().upper()] = entry
        for tok in tokenize_course_codes(entry.course_code):
            token_to_course[tok] = entry
    for alias in db.scalars(select(CourseCodeAlias)).all():
        catalog_entry = db.get(CourseCatalogEntry, alias.course_id)
        if not catalog_entry:
            continue
        variant_to_course[alias.variant_code.strip().upper()] = catalog_entry
        for tok in tokenize_course_codes(alias.variant_code):
            token_to_course.setdefault(tok, catalog_entry)
    return variant_to_course, token_to_course


def _resolve_catalog_for_allocation(
    row: CourseAllocation,
    variant_to_course: dict[str, CourseCatalogEntry],
    token_to_course: dict[str, CourseCatalogEntry],
    db: Session,
) -> CourseCatalogEntry | None:
    if row.course_catalog_id:
        return db.get(CourseCatalogEntry, row.course_catalog_id)
    code_key = collapse_repeated_dept_prefix(row.course_code).upper()
    entry = variant_to_course.get(code_key)
    if entry:
        return entry
    for tok in tokenize_course_codes(row.course_code):
        entry = token_to_course.get(tok)
        if entry:
            return entry
    return None


def _course_group_id(
    row: CourseAllocation,
    variant_to_course: dict[str, CourseCatalogEntry],
    token_to_course: dict[str, CourseCatalogEntry],
    db: Session,
) -> str:
    entry = _resolve_catalog_for_allocation(row, variant_to_course, token_to_course, db)
    if entry:
        return f"catalog:{entry.id}"
    return f"code:{collapse_repeated_dept_prefix(row.course_code).upper()}"


def list_courses_view(
    db: Session,
    *,
    scope: str | None = None,
    query: str | None = None,
    ug_pg: str | None = None,
    core_elective: str | None = None,
    first_year_only: bool = False,
) -> dict:
    semesters = scope_semesters(scope)
    stmt = select(CourseAllocation).where(CourseAllocation.is_faculty_placeholder.is_(False))
    if semesters:
        stmt = stmt.where(CourseAllocation.semester.in_(semesters))
    if ug_pg and ug_pg.upper() != "ALL":
        stmt = stmt.where(CourseAllocation.ug_pg == ug_pg)
    if core_elective and core_elective.upper() != "ALL":
        stmt = stmt.where(CourseAllocation.core_elective == core_elective)
    if first_year_only:
        stmt = stmt.where(CourseAllocation.is_first_year.is_(True))
    allocations = list(db.scalars(stmt).all())

    variant_to_course, token_to_course = _build_catalog_lookup(db)

    if query:
        q = query.strip().lower()
        allocations = [
            a
            for a in allocations
            if q in (a.course_code or "").lower()
            or q in (a.course_name or "").lower()
            or q in (a.faculty_name or "").lower()
        ]

    by_course: dict[str, list[CourseAllocation]] = {}
    course_meta: dict[str, dict] = {}
    for row in allocations:
        group_id = _course_group_id(row, variant_to_course, token_to_course, db)
        by_course.setdefault(group_id, []).append(row)
        if group_id not in course_meta:
            catalog_entry = _resolve_catalog_for_allocation(row, variant_to_course, token_to_course, db)
            course_meta[group_id] = {
                "course_catalog_id": catalog_entry.id if catalog_entry else None,
                "course_code": catalog_entry.course_code if catalog_entry else row.course_code,
                "course_name": catalog_entry.course_name if catalog_entry else row.course_name,
            }

    course_rows = []
    for group_id, rows in by_course.items():
        meta = course_meta[group_id]
        sorted_rows = sorted(
            rows, key=lambda r: (semester_sort_key(r.semester), r.faculty_name or "", r.course_code)
        )
        # Newest semester first; stable sort keeps faculty/course ordering within a term.
        sorted_rows = sorted(sorted_rows, key=lambda r: semester_sort_key(r.semester), reverse=True)
        course_rows.append(
            {
                "course_key": group_id,
                "course_catalog_id": meta["course_catalog_id"],
                "course_code": meta["course_code"],
                "course_name": meta["course_name"],
                "allocations": [_allocation_dict(r) for r in sorted_rows],
                "has_allocations": bool(sorted_rows),
            }
        )

    course_rows.sort(key=lambda r: (r["course_code"], r["course_name"]))

    all_semesters = [
        s for s in db.scalars(select(CourseAllocation.semester).distinct()).all() if s
    ]
    semester_set = sorted(set(all_semesters), key=semester_sort_key, reverse=True)
    all_academic_years = sorted(
        {ay for ay in db.scalars(select(CourseAllocation.academic_year).distinct()).all() if ay},
        reverse=True,
    )

    return {
        "course_rows": course_rows,
        "semesters": semester_set,
        "academic_years": all_academic_years,
    }


def courses_dashboard_summary(db: Session, semester: str) -> dict:
    rows = list(
        db.scalars(
            select(CourseAllocation).where(
                CourseAllocation.semester == semester,
                CourseAllocation.is_faculty_placeholder.is_(False),
            )
        ).all()
    )
    variant_to_course, token_to_course = _build_catalog_lookup(db)
    course_groups: set[str] = set()
    faculty_ids: set[int] = set()
    for r in rows:
        course_groups.add(_course_group_id(r, variant_to_course, token_to_course, db))
        if r.faculty_id:
            faculty_ids.add(r.faculty_id)
    return {
        "semester": semester,
        "total_courses": len(course_groups),
        "faculty_involved": len(faculty_ids),
        "ug_courses": sum(1 for r in rows if r.ug_pg == "UG"),
        "pg_courses": sum(1 for r in rows if r.ug_pg == "PG"),
        "ug_pg_courses": sum(1 for r in rows if r.ug_pg == "UG/PG"),
        "core_courses": sum(1 for r in rows if r.core_elective == "Core"),
        "elective_courses": sum(1 for r in rows if r.core_elective == "Elective"),
        "first_year_courses": sum(1 for r in rows if r.is_first_year),
    }


def course_history(db: Session, course_catalog_id: int) -> dict | None:
    entry = db.get(CourseCatalogEntry, course_catalog_id)
    if not entry:
        return None

    variant_to_course, token_to_course = _build_catalog_lookup(db)
    all_rows = list(
        db.scalars(
            select(CourseAllocation).where(CourseAllocation.is_faculty_placeholder.is_(False))
        ).all()
    )
    rows = [
        r
        for r in all_rows
        if _resolve_catalog_for_allocation(r, variant_to_course, token_to_course, db)
        and _resolve_catalog_for_allocation(r, variant_to_course, token_to_course, db).id == entry.id
    ]
    rows.sort(key=lambda r: (semester_sort_key(r.semester), r.faculty_name or "", r.course_code))
    # Full history table shows newest semester first; ties keep the secondary
    # ordering above (stable sort preserves faculty_name / course_code ordering).
    history_rows = sorted(rows, key=lambda r: semester_sort_key(r.semester), reverse=True)
    history = [_allocation_dict(r) for r in history_rows]

    faculty_counts: dict[str, dict] = {}
    for r in rows:
        key = str(r.faculty_id) if r.faculty_id else r.faculty_name
        fentry = faculty_counts.setdefault(
            key,
            {
                "faculty_id": r.faculty_id,
                "faculty_name": r.faculty_name,
                "times_taught": 0,
                "semesters": [],
                "most_recent_semester": r.semester,
            },
        )
        fentry["times_taught"] += 1
        fentry["semesters"].append(r.semester)
        if semester_sort_key(r.semester) >= semester_sort_key(fentry["most_recent_semester"]):
            fentry["most_recent_semester"] = r.semester

    for fentry in faculty_counts.values():
        fentry["semesters"] = sorted(fentry["semesters"], key=semester_sort_key)

    by_semester: dict[str, int] = {}
    ug_pg = {"UG": 0, "PG": 0, "UG/PG": 0}
    core_elective = {"Core": 0, "Elective": 0, "Core/Elective": 0}
    for r in rows:
        by_semester[r.semester] = by_semester.get(r.semester, 0) + 1
        if r.ug_pg in ug_pg:
            ug_pg[r.ug_pg] += 1
        if r.core_elective in core_elective:
            core_elective[r.core_elective] += 1

    return {
        "course": {
            "id": entry.id,
            "course_code": entry.course_code,
            "course_name": entry.course_name,
        },
        "history": history,
        "faculty_counts": list(faculty_counts.values()),
        "analytics": {
            "instances_per_semester": [
                {"semester": k, "count": v}
                for k, v in sorted(by_semester.items(), key=lambda x: semester_sort_key(x[0]))
            ],
            "ug_pg_split": ug_pg,
            "core_elective_split": core_elective,
        },
    }


def get_allocation(db: Session, row_id: int) -> CourseAllocation | None:
    return db.get(CourseAllocation, row_id)


def create_allocation(db: Session, data: dict) -> CourseAllocation:
    faculty_name = (data.get("faculty_name") or "").strip()
    placeholder = data.get("is_faculty_placeholder") or is_placeholder_name(faculty_name)
    row = CourseAllocation(
        faculty_name=faculty_name,
        semester=data["semester"].strip(),
        academic_year=data["academic_year"].strip(),
        course_code=data["course_code"].strip(),
        course_name=data["course_name"].strip(),
        ug_pg=data["ug_pg"].strip(),
        core_elective=data["core_elective"].strip(),
        is_first_year=bool(data.get("is_first_year")),
        first_year_course_name=(data.get("first_year_course_name") or "").strip() or None,
        source=(data.get("source") or "new").strip(),
        is_faculty_placeholder=placeholder,
    )
    if not placeholder:
        if data.get("faculty_id"):
            row.faculty_id = int(data["faculty_id"])
        else:
            resolved = resolve_allocation_faculty(db, faculty_name)
            if isinstance(resolved, FacultyResolveResult):
                row.faculty_id = resolved.faculty_id
    db.add(row)
    db.commit()
    db.refresh(row)
    write_allocations_csv(db)
    return row


def update_allocation(db: Session, row: CourseAllocation, data: dict) -> CourseAllocation:
    faculty_name = (data.get("faculty_name") or row.faculty_name).strip()
    placeholder = data.get("is_faculty_placeholder", row.is_faculty_placeholder)
    if is_placeholder_name(faculty_name):
        placeholder = True
    row.faculty_name = faculty_name
    row.semester = data.get("semester", row.semester).strip()
    row.academic_year = data.get("academic_year", row.academic_year).strip()
    row.course_code = data.get("course_code", row.course_code).strip()
    row.course_name = data.get("course_name", row.course_name).strip()
    row.ug_pg = data.get("ug_pg", row.ug_pg).strip()
    row.core_elective = data.get("core_elective", row.core_elective).strip()
    row.is_first_year = bool(data.get("is_first_year", row.is_first_year))
    row.first_year_course_name = (data.get("first_year_course_name") or row.first_year_course_name or "").strip() or None
    row.is_faculty_placeholder = placeholder
    if placeholder:
        row.faculty_id = None
    elif data.get("faculty_id"):
        row.faculty_id = int(data["faculty_id"])
    else:
        resolved = resolve_allocation_faculty(db, faculty_name)
        row.faculty_id = resolved.faculty_id if isinstance(resolved, FacultyResolveResult) else None
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    write_allocations_csv(db)
    return row


def delete_allocation(db: Session, row: CourseAllocation) -> None:
    db.delete(row)
    db.commit()
    write_allocations_csv(db)


def resolve_allocation_faculty_row(db: Session, row_id: int, faculty_id: int) -> CourseAllocation:
    from app.course_allocation.services.allocation_faculty_resolver import add_faculty_alias

    row = get_allocation(db, row_id)
    if not row:
        raise ValueError("Allocation not found")
    faculty = db.get(Faculty, faculty_id)
    if not faculty:
        raise ValueError("Faculty not found")
    add_faculty_alias(db, row.faculty_name, faculty_id)
    row.faculty_id = faculty.id
    row.is_faculty_placeholder = False
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    write_allocations_csv(db)
    return row


def list_catalog(db: Session) -> list[CourseCatalogEntry]:
    return list(db.scalars(select(CourseCatalogEntry).order_by(CourseCatalogEntry.course_code)).all())


def update_catalog_entry(db: Session, entry: CourseCatalogEntry, data: dict) -> CourseCatalogEntry:
    old_code = entry.course_code
    entry.course_code = data.get("course_code", entry.course_code).strip()
    entry.course_name = data.get("course_name", entry.course_name).strip()
    entry.ug_pg = data.get("ug_pg", entry.ug_pg).strip()
    entry.core_elective = data.get("core_elective", entry.core_elective).strip()
    entry.is_first_year = bool(data.get("is_first_year", entry.is_first_year))
    entry.updated_at = datetime.utcnow()
    rows = list(db.scalars(select(CourseAllocation).where(CourseAllocation.course_code == old_code)).all())
    for r in rows:
        r.course_code = entry.course_code
        r.course_name = entry.course_name
        r.ug_pg = entry.ug_pg
        r.core_elective = entry.core_elective
        r.is_first_year = entry.is_first_year
    db.commit()
    db.refresh(entry)
    write_catalog_csv(db)
    write_allocations_csv(db)
    return entry
