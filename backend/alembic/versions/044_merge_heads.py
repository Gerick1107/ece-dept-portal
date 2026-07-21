"""Merge publication (036-038) and moderation/labs (041-043) migration branches.

After a git merge, Alembic had three heads. ``alembic upgrade head`` failed, so the
Docker entrypoint never started Gunicorn (UI: \"Login failed\").

Revision id must stay <= 32 chars (alembic_version.version_num).
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "044_merge_heads"
down_revision: Union[str, tuple[str, ...], None] = (
    "038_sdg_ever_accepted",
    "042_labs_module",
    "043_moderation_courses",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
