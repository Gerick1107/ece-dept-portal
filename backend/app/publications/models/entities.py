from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Faculty(Base):
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    scholar_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    join_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    leave_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    profile_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    total_citations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    h_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    i10_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    publication_links: Mapped[list[PublicationFaculty]] = relationship(
        "PublicationFaculty",
        back_populates="faculty",
        cascade="all, delete-orphan",
    )
    scrape_logs: Mapped[list[ScrapeLog]] = relationship(
        "ScrapeLog",
        back_populates="faculty",
        cascade="all, delete-orphan",
    )


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    journal_or_conference: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    publisher: Mapped[str | None] = mapped_column(String(512), nullable=True)
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    publication_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    scholar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_iiitd_publication: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    faculty_links: Mapped[list[PublicationFaculty]] = relationship(
        "PublicationFaculty",
        back_populates="publication",
        cascade="all, delete-orphan",
    )


class PublicationFaculty(Base):
    __tablename__ = "publication_faculty"
    __table_args__ = (
        UniqueConstraint("publication_id", "faculty_id", name="uq_publication_faculty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    publication: Mapped[Publication] = relationship("Publication", back_populates="faculty_links")
    faculty: Mapped[Faculty] = relationship("Faculty", back_populates="publication_links")


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    new_publications_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)

    faculty: Mapped[Faculty] = relationship("Faculty", back_populates="scrape_logs")


class BlockedPublication(Base):
    __tablename__ = "blocked_publications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="manual_deletion")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublicationAuditLog(Base):
    __tablename__ = "publication_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    publication_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
