"""add_notifications_table

Revision ID: a6e1054b28c3
Revises: 96cd0af14534
Create Date: 2026-01-30 10:00:00.000000

Add notifications table for unified in-app notifications supporting
budget warnings, export completions, and sync status.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6e1054b28c3"
down_revision: str | None = "96cd0af14534"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extra_data", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notifications_user_id", "notifications", ["user_id"])
    op.create_index("idx_notifications_user_read", "notifications", ["user_id", "read"])
    op.create_index("idx_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_notifications_created_at", table_name="notifications")
    op.drop_index("idx_notifications_user_read", table_name="notifications")
    op.drop_index("idx_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
