"""ECE/EVE mirror: link to BTP projects and allow guides outside faculty directory."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "025_ece_eve_mirror"
down_revision: Union[str, None] = "024_portal_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_NAME = "fk_ece_eve_projects_source_project_id"
_INDEX_NAME = "ix_ece_eve_projects_source_project_id"


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def _column_nullable(table: str, column: str) -> bool:
    bind = op.get_bind()
    for col in inspect(bind).get_columns(table):
        if col["name"] == column:
            return bool(col.get("nullable"))
    return False


def _has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    return index_name in {idx["name"] for idx in inspect(bind).get_indexes(table)}


def _has_foreign_key(table: str, fk_name: str) -> bool:
    bind = op.get_bind()
    return fk_name in {fk.get("name") for fk in inspect(bind).get_foreign_keys(table)}


def upgrade() -> None:
    if not _has_column("ece_eve_projects", "source_project_id"):
        op.add_column("ece_eve_projects", sa.Column("source_project_id", sa.Integer(), nullable=True))

    if not _has_foreign_key("ece_eve_projects", _FK_NAME):
        op.create_foreign_key(
            _FK_NAME,
            "ece_eve_projects",
            "projects",
            ["source_project_id"],
            ["id"],
            ondelete="CASCADE",
        )

    if not _has_index("ece_eve_projects", _INDEX_NAME):
        op.create_index(_INDEX_NAME, "ece_eve_projects", ["source_project_id"])

    if not _column_nullable("ece_eve_projects", "faculty_id"):
        op.alter_column("ece_eve_projects", "faculty_id", existing_type=sa.Integer(), nullable=True)

    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM ece_eve_projects"))
    bind.execute(
        sa.text(
            """
            INSERT INTO ece_eve_projects (
                project_title, project_type, semesters, faculty_id, guide_name, co_guide,
                course_code, course_name, admission_year, program_definition,
                program_specialization, student_roll_nos, student_names, credit,
                upload_batch_id, sdg_review_status, created_at, updated_at, source_project_id
            )
            SELECT
                project_title, project_type, semesters, faculty_id, guide_name, co_guide,
                course_code, course_name, admission_year, program_definition,
                program_specialization, student_roll_nos, student_names, credit,
                upload_batch_id, sdg_review_status, created_at, updated_at, id
            FROM projects
            WHERE UPPER(TRIM(program_specialization)) IN ('ECE', 'EVE')
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM ece_eve_projects
            WHERE faculty_id IS NULL OR source_project_id IS NULL
            """
        )
    )
    if _has_index("ece_eve_projects", _INDEX_NAME):
        op.drop_index(_INDEX_NAME, table_name="ece_eve_projects")
    if _has_foreign_key("ece_eve_projects", _FK_NAME):
        op.drop_constraint(_FK_NAME, "ece_eve_projects", type_="foreignkey")
    if _has_column("ece_eve_projects", "source_project_id"):
        op.drop_column("ece_eve_projects", "source_project_id")
    if _column_nullable("ece_eve_projects", "faculty_id"):
        op.alter_column("ece_eve_projects", "faculty_id", existing_type=sa.Integer(), nullable=False)
