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


class Affiliation(Base):
    __tablename__ = "affiliations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    faculty_links: Mapped[list[FacultyAffiliation]] = relationship(
        "FacultyAffiliation",
        back_populates="affiliation",
        cascade="all, delete-orphan",
    )


class FacultyAffiliation(Base):
    __tablename__ = "faculty_affiliations"
    __table_args__ = (UniqueConstraint("faculty_id", "affiliation_id", name="uq_faculty_affiliation"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), index=True)
    affiliation_id: Mapped[int] = mapped_column(ForeignKey("affiliations.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    faculty: Mapped[Faculty] = relationship("Faculty", back_populates="affiliation_links")
    affiliation: Mapped[Affiliation] = relationship("Affiliation", back_populates="faculty_links")


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
    affiliation_links: Mapped[list[FacultyAffiliation]] = relationship(
        "FacultyAffiliation",
        back_populates="faculty",
        cascade="all, delete-orphan",
    )


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    publisher: Mapped[str | None] = mapped_column(String(512), nullable=True)
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    link: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    publication_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pages: Mapped[str | None] = mapped_column(String(100), nullable=True)
    conference: Mapped[str | None] = mapped_column(Text, nullable=True)
    journal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    book: Mapped[str | None] = mapped_column(Text, nullable=True)
    volume: Mapped[str | None] = mapped_column(String(50), nullable=True)
    issue: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_patent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    inventors: Mapped[str | None] = mapped_column(Text, nullable=True)
    patent_office: Mapped[str | None] = mapped_column(String(100), nullable=True)
    patent_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    application_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scholar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON blob of admin-defined custom columns, keyed by column key (e.g. {"issn": "1234-5678"}).
    custom_fields: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class PublicationCustomColumn(Base):
    """Admin-defined extra column (e.g. ISSN) fetched from publisher links / Crossref
    during syncs and backfills. Values are stored in ``publications.custom_fields``."""

    __tablename__ = "publication_custom_columns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Comma-separated HTML meta-tag names to try on publisher pages (e.g. "citation_issn,prism.issn").
    source_keys: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional Crossref field to fall back to (e.g. "ISSN", "ISBN", "DOI", "volume").
    crossref_field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    use_llm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PublicationAuditLog(Base):
    __tablename__ = "publication_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    publication_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
