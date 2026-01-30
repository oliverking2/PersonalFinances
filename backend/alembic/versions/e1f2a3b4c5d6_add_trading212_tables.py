"""add_trading212_tables

Revision ID: e1f2a3b4c5d6
Revises: d46e81d06c21
Create Date: 2026-01-28 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd46e81d06c21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create Trading 212 API keys table
    op.create_table(
        't212_api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('friendly_name', sa.String(length=128), nullable=False),
        sa.Column('t212_account_id', sa.String(length=50), nullable=True),
        sa.Column('currency_code', sa.String(length=3), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_t212_api_keys_user_id', 't212_api_keys', ['user_id'])
    op.create_index('idx_t212_api_keys_status', 't212_api_keys', ['status'])

    # Create Trading 212 cash balances table
    op.create_table(
        't212_cash_balances',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.UUID(), nullable=False),
        sa.Column('free', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('blocked', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('invested', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('pie_cash', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('ppl', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('result', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('total', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['t212_api_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_t212_cash_balances_api_key_id', 't212_cash_balances', ['api_key_id'])
    op.create_index('idx_t212_cash_balances_fetched_at', 't212_cash_balances', ['fetched_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_t212_cash_balances_fetched_at', 't212_cash_balances')
    op.drop_index('idx_t212_cash_balances_api_key_id', 't212_cash_balances')
    op.drop_table('t212_cash_balances')
    op.drop_index('idx_t212_api_keys_status', 't212_api_keys')
    op.drop_index('idx_t212_api_keys_user_id', 't212_api_keys')
    op.drop_table('t212_api_keys')
