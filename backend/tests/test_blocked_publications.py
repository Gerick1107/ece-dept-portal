"""Tombstone / blocked-publication behavior (isolated; no live DB deletes)."""

from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
import app.database.models  # noqa: F401 — register metadata
from app.publications.models import BlockedPublication, Publication
from app.publications.schemas import PublicationCreate
from app.publications.services.publication_service import (
    create_publication,
    delete_publications,
    should_skip_scraped_article,
)
from app.publications.utils.helpers import make_source_hash


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_manual_delete_tombstones_and_blocks_resync():
    """
    Simulate: create pub → delete → Scholar/sync must not re-insert the same title/year.

    Uses an in-memory SQLite DB only; never touches the real portal database.
    """
    db = _session()
    try:
        body = PublicationCreate(
            title="Tombstone Probe Paper XYZ",
            publication_year=2024,
            authors="Test Author",
            link="https://scholar.google.com/example",
            faculty_ids=[],
        )
        pub = create_publication(db, body)
        source_hash = pub.source_hash
        assert source_hash == make_source_hash(body.title, body.publication_year)

        deleted, blocked_added = delete_publications(db, [pub.id], reason="test_tombstone")
        assert deleted == 1
        assert blocked_added == 1
        assert db.scalar(select(Publication).where(Publication.id == pub.id)) is None

        blocked = db.scalar(
            select(BlockedPublication).where(BlockedPublication.source_hash == source_hash)
        )
        assert blocked is not None
        assert blocked.reason == "test_tombstone"

        # Same title/year coming back from Scholar must be skipped.
        assert should_skip_scraped_article(
            db,
            {"link": "https://scholar.google.com/example"},
            title=body.title,
            year=body.publication_year,
        )

        # Creating again via the service must also refuse.
        try:
            create_publication(db, body)
            raise AssertionError("expected blocked create to raise")
        except ValueError as exc:
            assert "blocked" in str(exc).lower()
    finally:
        db.close()


def test_repository_link_articles_are_skipped_without_delete():
    db = _session()
    try:
        assert should_skip_scraped_article(
            db,
            {"link": "https://repository.iiitd.edu.in/xmlui/handle/123"},
            title="Repo Only Paper",
            year=2020,
        )
        # No publication row was created or deleted — skip is link-based only.
        assert db.scalar(select(Publication)) is None
        assert db.scalar(select(BlockedPublication)) is None
    finally:
        db.close()
