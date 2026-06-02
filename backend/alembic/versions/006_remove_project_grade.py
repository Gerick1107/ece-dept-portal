"""Remove project grade column

Revision ID: 006
Revises: 005
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("projects")}
    if "grade" in columns:
        index_names = {idx["name"] for idx in inspector.get_indexes("projects")}
        if "ix_projects_grade" in index_names:
            op.drop_index("ix_projects_grade", table_name="projects")
        op.drop_column("projects", "grade")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("projects")}
    if "grade" not in columns:
        op.add_column("projects", sa.Column("grade", sa.String(length=16), nullable=True))
        op.create_index("ix_projects_grade", "projects", ["grade"], unique=False)
