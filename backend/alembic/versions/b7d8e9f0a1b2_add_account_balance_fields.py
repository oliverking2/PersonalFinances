"""add account balance fields

Revision ID: b7d8e9f0a1b2
Revises: a1b2c3d4e5f6
Create Date: 2026-01-24 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add balance fields to accounts table and backfill from gc_balances."""
    # Add new columns
    op.add_column("accounts", sa.Column("balance_amount", sa.Numeric(18, 2), nullable=True))
    op.add_column("accounts", sa.Column("balance_currency", sa.String(3), nullable=True))
    op.add_column("accounts", sa.Column("balance_type", sa.String(50), nullable=True))
    op.add_column(
        "accounts", sa.Column("balance_updated_at", sa.DateTime(timezone=True), nullable=True)
    )

    # Backfill from gc_balances (get latest balance per account)
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE accounts
            SET
                balance_amount = b.balance_amount,
                balance_currency = b.balance_currency,
                balance_type = b.balance_type,
                balance_updated_at = b.last_change_date
            FROM (
                SELECT DISTINCT ON (account_id)
                    account_id,
                    balance_amount,
                    balance_currency,
                    balance_type,
                    last_change_date
                FROM gc_balances
                ORDER BY account_id, last_change_date DESC NULLS LAST
            ) b
            WHERE accounts.provider_id = b.account_id
            """
        )
    )


def downgrade() -> None:
    """Remove balance fields from accounts table."""
    op.drop_column("accounts", "balance_updated_at")
    op.drop_column("accounts", "balance_type")
    op.drop_column("accounts", "balance_currency")
    op.drop_column("accounts", "balance_amount")
