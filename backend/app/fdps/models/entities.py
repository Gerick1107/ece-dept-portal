from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FacultyFdp(Base):
    __tablename__ = "faculty_fdps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    faculty_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exact_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    program: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    no_of_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    no_of_attendees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
