from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.labs.models.entities import Lab
from app.publications.models.entities import Faculty


def list_labs(db: Session, *, faculty_id: int | None = None, query: str | None = None) -> list[Lab]:
    stmt = select(Lab).options(joinedload(Lab.faculty)).order_by(Lab.lab_name.asc())
    if faculty_id is not None:
        stmt = stmt.where(Lab.faculty_id == faculty_id)
    if query:
        q = f"%{query.strip()}%"
        stmt = stmt.where(Lab.lab_name.ilike(q))
    return list(db.scalars(stmt).unique().all())


def get_lab(db: Session, lab_id: int) -> Lab | None:
    return db.scalar(select(Lab).options(joinedload(Lab.faculty)).where(Lab.id == lab_id))


def lab_to_dict(row: Lab) -> dict:
    remaining = max(row.total_seats - row.allotted_seats, 0)
    return {
        "id": row.id,
        "lab_name": row.lab_name,
        "location": row.location,
        "faculty_id": row.faculty_id,
        "faculty_name": row.faculty.name if row.faculty else None,
        "total_seats": row.total_seats,
        "allotted_seats": row.allotted_seats,
        "remaining_seats": remaining,
        "occupancy_pct": round((row.allotted_seats / row.total_seats) * 100, 1) if row.total_seats else 0,
        "remarks": row.remarks,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _validate(data: dict, db: Session) -> None:
    if not (data.get("lab_name") or "").strip():
        raise ValueError("Lab name is required")
    if not data.get("faculty_id"):
        raise ValueError("Faculty is required")
    if not db.get(Faculty, int(data["faculty_id"])):
        raise ValueError("Selected faculty not found")
    total = int(data.get("total_seats") or 0)
    allotted = int(data.get("allotted_seats") or 0)
    if total < 0 or allotted < 0:
        raise ValueError("Seat counts cannot be negative")
    if allotted > total:
        raise ValueError("Allotted seats cannot exceed total seats")


def create_lab(db: Session, data: dict) -> Lab:
    _validate(data, db)
    row = Lab(
        lab_name=data["lab_name"].strip(),
        location=(data.get("location") or "").strip() or None,
        faculty_id=int(data["faculty_id"]),
        total_seats=int(data.get("total_seats") or 0),
        allotted_seats=int(data.get("allotted_seats") or 0),
        remarks=(data.get("remarks") or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_lab(db: Session, row: Lab, data: dict) -> Lab:
    _validate({**lab_to_dict(row), **data}, db)
    if "lab_name" in data:
        row.lab_name = data["lab_name"].strip()
    if "location" in data:
        row.location = (data.get("location") or "").strip() or None
    if "faculty_id" in data:
        row.faculty_id = int(data["faculty_id"])
    if "total_seats" in data:
        row.total_seats = int(data["total_seats"])
    if "allotted_seats" in data:
        row.allotted_seats = int(data["allotted_seats"])
    if "remarks" in data:
        row.remarks = (data.get("remarks") or "").strip() or None
    db.commit()
    db.refresh(row)
    return row


def delete_lab(db: Session, row: Lab) -> None:
    db.delete(row)
    db.commit()


def summary_stats(db: Session) -> dict:
    labs = list_labs(db)
    total_seats = sum(l.total_seats for l in labs)
    allotted = sum(l.allotted_seats for l in labs)
    return {
        "total_labs": len(labs),
        "total_seats": total_seats,
        "allotted_seats": allotted,
        "remaining_seats": max(total_seats - allotted, 0),
        "occupancy_pct": round((allotted / total_seats) * 100, 1) if total_seats else 0,
    }