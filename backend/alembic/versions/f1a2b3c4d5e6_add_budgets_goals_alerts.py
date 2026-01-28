"""add_budgets_goals_alerts

Revision ID: f1a2b3c4d5e6
Revises: e77ce7f14b11
Create Date: 2026-01-27 12:00:00.000000

Add budgets, savings_goals, and spending_alerts tables for Phase 6 budgeting features.
"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e77ce7f14b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create budgets table
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="GBP"
        ),
        sa.Column(
            "period", sa.String(length=20), nullable=False, server_default="monthly"
        ),
        sa.Column(
            "warning_threshold",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            server_default="0.80",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_budgets_user_id", "budgets", ["user_id"], unique=False)
    op.create_index(
        "idx_budgets_user_tag", "budgets", ["user_id", "tag_id"], unique=True
    )

    # Create savings_goals table
    op.create_table(
        "savings_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("target_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "current_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="GBP"
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="active"
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_savings_goals_user_id", "savings_goals", ["user_id"], unique=False
    )
    op.create_index(
        "idx_savings_goals_status", "savings_goals", ["status"], unique=False
    )

    # Create spending_alerts table
    op.create_table(
        "spending_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("alert_type", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("period_key", sa.String(length=20), nullable=False),
        sa.Column("budget_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("spent_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_spending_alerts_user_id", "spending_alerts", ["user_id"], unique=False
    )
    op.create_index(
        "idx_spending_alerts_status", "spending_alerts", ["status"], unique=False
    )
    op.create_index(
        "idx_spending_alerts_unique",
        "spending_alerts",
        ["user_id", "budget_id", "alert_type", "period_key"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop spending_alerts table
    op.drop_index("idx_spending_alerts_unique", table_name="spending_alerts")
    op.drop_index("idx_spending_alerts_status", table_name="spending_alerts")
    op.drop_index("idx_spending_alerts_user_id", table_name="spending_alerts")
    op.drop_table("spending_alerts")

    # Drop savings_goals table
    op.drop_index("idx_savings_goals_status", table_name="savings_goals")
    op.drop_index("idx_savings_goals_user_id", table_name="savings_goals")
    op.drop_table("savings_goals")

    # Drop budgets table
    op.drop_index("idx_budgets_user_tag", table_name="budgets")
    op.drop_index("idx_budgets_user_id", table_name="budgets")
    op.drop_table("budgets")
