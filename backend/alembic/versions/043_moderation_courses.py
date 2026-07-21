from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "043_moderation_courses"
down_revision: Union[str, None] = "041_moderation_module"  # ← set to your actual latest head
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("moderation_courses"):
        op.create_table(
            "moderation_courses",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("course_code", sa.String(50), nullable=False),
            sa.Column("course_name", sa.String(200), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("course_code", name="uq_moderation_courses_code"),
        )
        op.create_index("ix_moderation_courses_course_code", "moderation_courses", ["course_code"])

    # Old moderation_question_papers had course_code/course_name/exam_type directly.
    # Drop and recreate against the new course_id/faculty_name/year/semester shape.
    if _has_table("moderation_question_papers"):
        op.drop_table("moderation_question_papers")

    op.create_table(
        "moderation_question_papers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("moderation_courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("faculty_name", sa.String(200), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("semester", sa.String(16), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_question_papers_course_id", "moderation_question_papers", ["course_id"])
    op.create_index("ix_moderation_question_papers_faculty_name", "moderation_question_papers", ["faculty_name"])
    op.create_index("ix_moderation_question_papers_year", "moderation_question_papers", ["year"])


def downgrade() -> None:
    if _has_table("moderation_question_papers"):
        op.drop_table("moderation_question_papers")
    if _has_table("moderation_courses"):
        op.drop_table("moderation_courses")