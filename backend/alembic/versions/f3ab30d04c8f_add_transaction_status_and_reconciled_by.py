"""add transaction status and reconciled_by

Revision ID: f3ab30d04c8f
Revises: fdf5795bce3e
Create Date: 2026-01-31 21:38:38.016421

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3ab30d04c8f'
down_revision: Union[str, Sequence[str], None] = 'fdf5795bce3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add status column as nullable first
    op.add_column('transactions', sa.Column('status', sa.String(length=50), nullable=True))

    # Set all existing transactions to 'active'
    op.execute("UPDATE transactions SET status = 'active'")

    # Now make it NOT NULL
    op.alter_column('transactions', 'status', nullable=False)

    # Add reconciled_by_id FK
    op.add_column('transactions', sa.Column('reconciled_by_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_transactions_reconciled_by',
        'transactions',
        'transactions',
        ['reconciled_by_id'],
        ['id']
    )

    # Backfill: Find and reconcile duplicate pending/booked transaction pairs
    # A pending transaction is reconciled when a booked transaction exists with:
    # - Same account, same amount, booking date within 5 days
    op.execute("""
        WITH duplicate_pairs AS (
            -- Find pending gc_transactions that have a matching booked gc_transaction
            SELECT DISTINCT ON (pending.transaction_id)
                pending.transaction_id AS pending_provider_id,
                booked.transaction_id AS booked_provider_id
            FROM gc_transactions pending
            JOIN gc_transactions booked ON
                pending.account_id = booked.account_id
                AND pending.transaction_amount = booked.transaction_amount
                AND pending.status = 'pending'
                AND booked.status = 'booked'
                AND pending.transaction_id != booked.transaction_id
                AND ABS(pending.booking_date - booked.booking_date) <= 5
        ),
        to_reconcile AS (
            -- Map to unified transaction IDs
            SELECT
                pending_txn.id AS pending_id,
                booked_txn.id AS booked_id
            FROM duplicate_pairs dp
            JOIN transactions pending_txn ON pending_txn.provider_id = dp.pending_provider_id
            JOIN transactions booked_txn ON booked_txn.provider_id = dp.booked_provider_id
            WHERE pending_txn.status = 'active'
        )
        UPDATE transactions
        SET status = 'reconciled', reconciled_by_id = to_reconcile.booked_id
        FROM to_reconcile
        WHERE transactions.id = to_reconcile.pending_id
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_transactions_reconciled_by', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'reconciled_by_id')
    op.drop_column('transactions', 'status')
