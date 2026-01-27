"""add_recurring_patterns

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-27 10:00:00.000000

Add recurring patterns tables for subscription/bill detection.
"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create recurring_patterns table
    op.create_table(
        "recurring_patterns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("merchant_pattern", sa.String(length=256), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("expected_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "amount_variance",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="GBP"
        ),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("anchor_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_expected_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_occurrence_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "confidence_score",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            server_default="0.5",
        ),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="detected"
        ),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
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
        "idx_recurring_patterns_user_id", "recurring_patterns", ["user_id"], unique=False
    )
    op.create_index(
        "idx_recurring_patterns_status", "recurring_patterns", ["status"], unique=False
    )
    op.create_index(
        "idx_recurring_patterns_next_date",
        "recurring_patterns",
        ["next_expected_date"],
        unique=False,
    )
    op.create_index(
        "idx_recurring_patterns_user_merchant",
        "recurring_patterns",
        ["user_id", "merchant_pattern", "account_id"],
        unique=True,
    )

    # Create recurring_pattern_transactions table
    op.create_table(
        "recurring_pattern_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pattern_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("amount_match", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("date_match", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["pattern_id"], ["recurring_patterns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_pattern_transactions_pattern",
        "recurring_pattern_transactions",
        ["pattern_id"],
        unique=False,
    )
    op.create_index(
        "idx_pattern_transactions_transaction",
        "recurring_pattern_transactions",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        "idx_pattern_transaction_unique",
        "recurring_pattern_transactions",
        ["pattern_id", "transaction_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop recurring_pattern_transactions table
    op.drop_index(
        "idx_pattern_transaction_unique", table_name="recurring_pattern_transactions"
    )
    op.drop_index(
        "idx_pattern_transactions_transaction",
        table_name="recurring_pattern_transactions",
    )
    op.drop_index(
        "idx_pattern_transactions_pattern", table_name="recurring_pattern_transactions"
    )
    op.drop_table("recurring_pattern_transactions")

    # Drop recurring_patterns table
    op.drop_index(
        "idx_recurring_patterns_user_merchant", table_name="recurring_patterns"
    )
    op.drop_index("idx_recurring_patterns_next_date", table_name="recurring_patterns")
    op.drop_index("idx_recurring_patterns_status", table_name="recurring_patterns")
    op.drop_index("idx_recurring_patterns_user_id", table_name="recurring_patterns")
    op.drop_table("recurring_patterns")
