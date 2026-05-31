"""BTP/IP projects module schema

Revision ID: 004
Revises: 003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SDG_ROWS = [
    (1, "No Poverty", "End poverty in all its forms everywhere."),
    (2, "Zero Hunger", "End hunger, achieve food security and improved nutrition."),
    (3, "Good Health and Well-being", "Ensure healthy lives and promote well-being for all."),
    (4, "Quality Education", "Ensure inclusive and equitable quality education."),
    (5, "Gender Equality", "Achieve gender equality and empower all women and girls."),
    (6, "Clean Water and Sanitation", "Ensure availability and sustainable management of water."),
    (7, "Affordable and Clean Energy", "Ensure access to affordable, reliable, sustainable energy."),
    (8, "Decent Work and Economic Growth", "Promote sustained, inclusive economic growth."),
    (9, "Industry, Innovation and Infrastructure", "Build resilient infrastructure and foster innovation."),
    (10, "Reduced Inequalities", "Reduce inequality within and among countries."),
    (11, "Sustainable Cities and Communities", "Make cities inclusive, safe, resilient and sustainable."),
    (12, "Responsible Consumption and Production", "Ensure sustainable consumption and production patterns."),
    (13, "Climate Action", "Take urgent action to combat climate change and its impacts."),
    (14, "Life Below Water", "Conserve and sustainably use oceans, seas and marine resources."),
    (15, "Life on Land", "Protect, restore and promote sustainable use of terrestrial ecosystems."),
    (16, "Peace, Justice and Strong Institutions", "Promote peaceful and inclusive societies."),
    (17, "Partnerships for the Goals", "Strengthen means of implementation and global partnership."),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "sdgs" in existing:
        count = bind.execute(sa.text("SELECT COUNT(*) FROM sdgs")).scalar() or 0
        if count == 0:
            sdg_table = sa.table(
                "sdgs",
                sa.column("sdg_number", sa.Integer),
                sa.column("sdg_name", sa.String),
                sa.column("description", sa.Text),
            )
            op.bulk_insert(
                sdg_table,
                [{"sdg_number": n, "sdg_name": name, "description": desc} for n, name, desc in SDG_ROWS],
            )
        return

    op.create_table(
        "sdgs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sdg_number", sa.Integer(), nullable=False),
        sa.Column("sdg_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sdg_number", name="uq_sdgs_sdg_number"),
    )
    op.create_index(op.f("ix_sdgs_sdg_number"), "sdgs", ["sdg_number"], unique=True)

    op.create_table(
        "project_uploads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("filepath", sa.String(length=1024), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_title", sa.String(length=1024), nullable=False),
        sa.Column("project_type", sa.String(length=16), nullable=False),
        sa.Column("semester", sa.String(length=128), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=False),
        sa.Column("co_guide", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="Pending"),
        sa.Column("credit", sa.String(length=32), nullable=True),
        sa.Column("grade", sa.String(length=16), nullable=True),
        sa.Column("upload_batch_id", sa.Integer(), nullable=True),
        sa.Column("sdg_review_status", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["upload_batch_id"], ["project_uploads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_faculty_id"), "projects", ["faculty_id"], unique=False)
    op.create_index(op.f("ix_projects_project_type"), "projects", ["project_type"], unique=False)
    op.create_index(op.f("ix_projects_semester"), "projects", ["semester"], unique=False)
    op.create_index(op.f("ix_projects_status"), "projects", ["status"], unique=False)
    op.create_index(op.f("ix_projects_grade"), "projects", ["grade"], unique=False)

    op.create_table(
        "project_students",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("student_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_students_project_id"), "project_students", ["project_id"], unique=False)

    op.create_table(
        "project_sdgs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("sdg_id", sa.Integer(), nullable=False),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sdg_id"], ["sdgs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "sdg_id", name="uq_project_sdgs_project_sdg"),
    )
    op.create_index(op.f("ix_project_sdgs_project_id"), "project_sdgs", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_sdgs_sdg_id"), "project_sdgs", ["sdg_id"], unique=False)

    sdg_table = sa.table(
        "sdgs",
        sa.column("sdg_number", sa.Integer),
        sa.column("sdg_name", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        sdg_table,
        [{"sdg_number": n, "sdg_name": name, "description": desc} for n, name, desc in SDG_ROWS],
    )


def downgrade() -> None:
    op.drop_table("project_sdgs")
    op.drop_table("project_students")
    op.drop_table("projects")
    op.drop_table("project_uploads")
    op.drop_table("sdgs")
