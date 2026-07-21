from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "041_moderation_module"
down_revision: Union[str, None] = "035_publication_custom_columns"  # ← set to your actual latest head
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "moderation_question_papers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_code", sa.String(50), nullable=False),
        sa.Column("course_name", sa.String(200), nullable=True),
        sa.Column("semester", sa.String(32), nullable=False),
        sa.Column("exam_type", sa.String(32), nullable=False, server_default="EndSem"),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_question_papers_course_code", "moderation_question_papers", ["course_code"])
    op.create_index("ix_moderation_question_papers_semester", "moderation_question_papers", ["semester"])

    op.create_table(
        "moderation_grade_criteria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_code", sa.String(50), nullable=False),
        sa.Column("semester", sa.String(32), nullable=False),
        sa.Column("grade_letter", sa.String(5), nullable=False),
        sa.Column("min_marks", sa.Float(), nullable=False),
        sa.Column("max_marks", sa.Float(), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_grade_criteria_course_code", "moderation_grade_criteria", ["course_code"])
    op.create_index("ix_moderation_grade_criteria_semester", "moderation_grade_criteria", ["semester"])


def downgrade() -> None:
    op.drop_table("moderation_grade_criteria")
    op.drop_table("moderation_question_papers")