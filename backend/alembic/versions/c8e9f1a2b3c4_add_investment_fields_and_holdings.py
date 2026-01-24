"""add investment fields and holdings table

Revision ID: c8e9f1a2b3c4
Revises: b7d8e9f0a1b2
Create Date: 2026-01-24 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8e9f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "b7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add investment account fields and holdings table."""
    # Add account_type column with default 'bank' for existing accounts
    op.add_column(
        "accounts",
        sa.Column("account_type", sa.String(20), nullable=False, server_default="bank"),
    )

    # Add investment-specific fields
    op.add_column("accounts", sa.Column("total_value", sa.Numeric(18, 2), nullable=True))
    op.add_column("accounts", sa.Column("unrealised_pnl", sa.Numeric(18, 2), nullable=True))

    # Create holdings table for investment positions
    op.create_table(
        "holdings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("isin", sa.String(12), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("average_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("current_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("current_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("unrealised_pnl", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for holdings table
    op.create_index("idx_holdings_account_id", "holdings", ["account_id"])
    op.create_index(
        "idx_holdings_account_ticker", "holdings", ["account_id", "ticker"], unique=True
    )


def downgrade() -> None:
    """Remove investment fields and holdings table."""
    # Drop holdings table and indexes
    op.drop_index("idx_holdings_account_ticker", table_name="holdings")
    op.drop_index("idx_holdings_account_id", table_name="holdings")
    op.drop_table("holdings")

    # Remove investment fields from accounts
    op.drop_column("accounts", "unrealised_pnl")
    op.drop_column("accounts", "total_value")
    op.drop_column("accounts", "account_type")
