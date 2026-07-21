from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lab_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    allotted_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    faculty: Mapped["Faculty"] = relationship("Faculty", foreign_keys=[faculty_id], lazy="joined")


from app.publications.models.entities import Faculty  # noqa: E402, F401