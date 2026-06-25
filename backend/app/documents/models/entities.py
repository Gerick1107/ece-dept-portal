from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

DOCUMENT_TYPE_SENATE = "senate"
DOCUMENT_TYPE_ECE_FACULTY_MEET = "ece_faculty_meet"
DOCUMENT_TYPE_AAC = "aac"
DOCUMENT_TYPE_UGC = "ugc"
DOCUMENT_TYPE_PGC = "pgc"
DOCUMENT_TYPE_ALL = "__all__"

ALL_DOCUMENT_TYPES = (
    DOCUMENT_TYPE_SENATE,
    DOCUMENT_TYPE_ECE_FACULTY_MEET,
    DOCUMENT_TYPE_AAC,
    DOCUMENT_TYPE_UGC,
    DOCUMENT_TYPE_PGC,
)

DOCUMENT_TYPE_LABELS: dict[str, str] = {
    DOCUMENT_TYPE_SENATE: "Senate",
    DOCUMENT_TYPE_ECE_FACULTY_MEET: "ECE Faculty",
    DOCUMENT_TYPE_AAC: "AAC",
    DOCUMENT_TYPE_UGC: "UGC",
    DOCUMENT_TYPE_PGC: "PGC",
}


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    meeting_title: Mapped[str] = mapped_column(String(512), nullable=False)
    meeting_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    files: Mapped[list["MeetingFile"]] = relationship(
        "MeetingFile", back_populates="meeting", cascade="all, delete-orphan"
    )


class MeetingFile(Base):
    __tablename__ = "meeting_files"
    __table_args__ = (UniqueConstraint("meeting_id", "file_role", name="uq_meeting_file_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_role: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    meeting: Mapped[Meeting] = relationship("Meeting", back_populates="files")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="meeting_file", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_file_id: Mapped[int] = mapped_column(
        ForeignKey("meeting_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    meeting_file: Mapped[MeetingFile] = relationship("MeetingFile", back_populates="chunks")


class DocumentQueryLog(Base):
    __tablename__ = "document_query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    document_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
