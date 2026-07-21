"""Merge publication (036-038) and moderation/labs (041-043) migration branches.

After a git merge, Alembic had three heads:
  - 038_sdg_ever_accepted
  - 042_labs_module
  - 043_moderation_courses

``alembic upgrade head`` then fails, so Docker entrypoint never starts Gunicorn and
login proxies return a non-JSON error (UI: \"Login failed\").
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "044_merge_publication_moderation_labs"
down_revision: Union[str, tuple[str, ...], None] = (
    "038_sdg_ever_accepted",
    "042_labs_module",
    "043_moderation_courses",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema changes already live on each branch; this revision only unifies heads.
    pass


def downgrade() -> None:
    pass
