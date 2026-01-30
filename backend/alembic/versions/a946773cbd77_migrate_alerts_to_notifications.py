"""migrate_alerts_to_notifications

Revision ID: a946773cbd77
Revises: a6e1054b28c3
Create Date: 2026-01-30 11:00:00.000000

Migrate existing SpendingAlert records to the new Notification model,
then drop the spending_alerts table.
"""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a946773cbd77"
down_revision: str | None = "a6e1054b28c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - migrate alerts to notifications and drop spending_alerts."""
    conn = op.get_bind()

    # Get all spending alerts with their budget and tag info
    alerts = conn.execute(
        sa.text("""
            SELECT
                sa.id,
                sa.user_id,
                sa.budget_id,
                sa.alert_type,
                sa.status,
                sa.period_key,
                sa.budget_amount,
                sa.spent_amount,
                sa.message,
                sa.created_at,
                sa.acknowledged_at,
                t.name as tag_name
            FROM spending_alerts sa
            JOIN budgets b ON sa.budget_id = b.id
            JOIN tags t ON b.tag_id = t.id
        """)
    ).fetchall()

    # Insert notifications for each alert
    for alert in alerts:
        # Calculate percentage
        percentage = (
            int(alert.spent_amount / alert.budget_amount * 100) if alert.budget_amount > 0 else 0
        )

        # Map alert type to notification type
        notification_type = alert.alert_type  # budget_warning or budget_exceeded

        # Determine title based on type
        if notification_type == "budget_exceeded":
            title = "Budget Exceeded"
            message = (
                alert.message
                or f"Your {alert.tag_name} budget has been exceeded ({percentage}% spent)."
            )
        else:
            title = "Budget Warning"
            message = alert.message or f"Your {alert.tag_name} budget is at {percentage}%."

        # Determine read status from alert status
        is_read = alert.status == "acknowledged"

        # Build extra_data
        extra_data = {
            "budget_id": str(alert.budget_id),
            "tag_name": alert.tag_name,
            "period_key": alert.period_key,
            "budget_amount": float(alert.budget_amount),
            "spent_amount": float(alert.spent_amount),
            "percentage": percentage,
            "migrated_from_alert": str(alert.id),
        }

        # Insert notification
        conn.execute(
            sa.text("""
                INSERT INTO notifications (
                    id, user_id, notification_type, title, message, read, extra_data,
                    created_at, read_at
                ) VALUES (
                    :id, :user_id, :notification_type, :title, :message, :read, :extra_data,
                    :created_at, :read_at
                )
            """),
            {
                "id": str(uuid4()),
                "user_id": str(alert.user_id),
                "notification_type": notification_type,
                "title": title,
                "message": message[:500],
                "read": is_read,
                "extra_data": json.dumps(extra_data),
                "created_at": alert.created_at,
                "read_at": alert.acknowledged_at,
            },
        )

    # Drop the spending_alerts table
    op.drop_index("idx_spending_alerts_unique", table_name="spending_alerts")
    op.drop_index("idx_spending_alerts_status", table_name="spending_alerts")
    op.drop_index("idx_spending_alerts_user_id", table_name="spending_alerts")
    op.drop_table("spending_alerts")


def downgrade() -> None:
    """Downgrade schema - recreate spending_alerts table.

    Note: Data cannot be fully restored from notifications due to structural differences.
    This recreates the table structure but migrated data is lost.
    """
    op.create_table(
        "spending_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("alert_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("period_key", sa.String(20), nullable=False),
        sa.Column("budget_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("spent_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_spending_alerts_user_id", "spending_alerts", ["user_id"])
    op.create_index("idx_spending_alerts_status", "spending_alerts", ["status"])
    op.create_index(
        "idx_spending_alerts_unique",
        "spending_alerts",
        ["user_id", "budget_id", "alert_type", "period_key"],
        unique=True,
    )

    # Remove migrated notifications (optional cleanup)
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            DELETE FROM notifications
            WHERE extra_data->>'migrated_from_alert' IS NOT NULL
        """)
    )
