"""add_gc_transactions_table

Revision ID: 28663f2f3281
Revises: c8e9f1a2b3c4
Create Date: 2026-01-24 16:21:04.129300

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28663f2f3281'
down_revision: Union[str, Sequence[str], None] = 'c8e9f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('gc_transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_id', sa.String(length=128), nullable=False),
        sa.Column('transaction_id', sa.String(length=256), nullable=False),
        sa.Column('booking_date', sa.Date(), nullable=True),
        sa.Column('value_date', sa.Date(), nullable=True),
        sa.Column('booking_datetime', sa.DateTime(), nullable=True),
        sa.Column('transaction_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('creditor_name', sa.String(length=256), nullable=True),
        sa.Column('creditor_account', sa.String(length=64), nullable=True),
        sa.Column('debtor_name', sa.String(length=256), nullable=True),
        sa.Column('debtor_account', sa.String(length=64), nullable=True),
        sa.Column('remittance_information', sa.String(length=1024), nullable=True),
        sa.Column('bank_transaction_code', sa.String(length=64), nullable=True),
        sa.Column('proprietary_bank_code', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('internal_transaction_id', sa.String(length=256), nullable=True),
        sa.Column('extracted_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['gc_bank_accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'transaction_id', name='uq_gc_transactions_account_transaction'),
        sqlite_autoincrement=True
    )
    op.create_index(op.f('ix_gc_transactions_account_id'), 'gc_transactions', ['account_id'], unique=False)
    op.create_index(op.f('ix_gc_transactions_booking_date'), 'gc_transactions', ['booking_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_gc_transactions_booking_date'), table_name='gc_transactions')
    op.drop_index(op.f('ix_gc_transactions_account_id'), table_name='gc_transactions')
    op.drop_table('gc_transactions')
