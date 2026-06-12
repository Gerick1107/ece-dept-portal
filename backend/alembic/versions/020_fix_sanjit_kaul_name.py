"""Correct Sanjit Kaul middle name: Krishan -> Krishnan."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "020_fix_sanjit_kaul_name"
down_revision: Union[str, None] = "019_project_guide_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    return table in inspect(bind).get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def _replace_krishan(conn, table: str, column: str) -> None:
    if not _has_table(table) or not _has_column(table, column):
        return
    conn.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET {column} = REPLACE({column}, 'Krishan', 'Krishnan')
            WHERE {column} LIKE '%Krishan%'
            """
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    _replace_krishan(conn, "faculty", "name")
    _replace_krishan(conn, "users", "full_name")
    if _has_table("projects"):
        _replace_krishan(conn, "projects", "guide_name")
        _replace_krishan(conn, "projects", "co_guide")
    if _has_table("faculty_awards"):
        _replace_krishan(conn, "faculty_awards", "faculty_name")


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table("faculty"):
        conn.execute(
            sa.text(
                """
                UPDATE faculty
                SET name = REPLACE(name, 'Krishnan', 'Krishan')
                WHERE name LIKE '%Krishnan%' AND scholar_id = 'XGNQPRsAAAAJ'
                """
            )
        )
    conn.execute(
        sa.text(
            """
            UPDATE users
            SET full_name = REPLACE(full_name, 'Krishnan', 'Krishan')
            WHERE full_name LIKE '%Krishnan%' AND full_name LIKE '%Kaul%'
            """
        )
    )
    if _has_table("projects"):
        conn.execute(
            sa.text(
                """
                UPDATE projects
                SET guide_name = REPLACE(guide_name, 'Krishnan', 'Krishan')
                WHERE guide_name LIKE '%Krishnan%' AND guide_name LIKE '%Kaul%'
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE projects
                SET co_guide = REPLACE(co_guide, 'Krishnan', 'Krishan')
                WHERE co_guide LIKE '%Krishnan%' AND co_guide LIKE '%Kaul%'
                """
            )
        )
    if _has_table("faculty_awards"):
        conn.execute(
            sa.text(
                """
                UPDATE faculty_awards
                SET faculty_name = REPLACE(faculty_name, 'Krishnan', 'Krishan')
                WHERE faculty_name LIKE '%Krishnan%' AND faculty_name LIKE '%Kaul%'
                """
            )
        )
