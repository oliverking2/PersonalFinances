"""add jobs table

Revision ID: 55b6582091bd
Revises: 3649be6e9b64
Create Date: 2026-01-24 21:26:54.794285

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '55b6582091bd'
down_revision: Union[str, Sequence[str], None] = '3649be6e9b64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("dagster_run_id", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_jobs_entity", "jobs", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_jobs_user_status", "jobs", ["user_id", "status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_jobs_user_status", table_name="jobs")
    op.drop_index("idx_jobs_entity", table_name="jobs")
    op.drop_table("jobs")
