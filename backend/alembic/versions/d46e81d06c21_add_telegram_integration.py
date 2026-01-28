"""add_telegram_integration

Revision ID: d46e81d06c21
Revises: a2b3c4d5e6f7
Create Date: 2026-01-28 20:50:47.213215

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd46e81d06c21'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create telegram polling cursor table
    op.create_table(
        'telegram_polling_cursor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('last_update_id', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create telegram link codes table for account linking
    op.create_table(
        'telegram_link_codes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=8), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('idx_telegram_link_codes_code', 'telegram_link_codes', ['code'])
    op.create_index('idx_telegram_link_codes_user_id', 'telegram_link_codes', ['user_id'])

    # Add telegram_chat_id to users for notifications and 2FA
    op.add_column('users', sa.Column('telegram_chat_id', sa.String(length=50), nullable=True))
    op.create_unique_constraint('uq_users_telegram_chat_id', 'users', ['telegram_chat_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_users_telegram_chat_id', 'users', type_='unique')
    op.drop_column('users', 'telegram_chat_id')
    op.drop_index('idx_telegram_link_codes_user_id', 'telegram_link_codes')
    op.drop_index('idx_telegram_link_codes_code', 'telegram_link_codes')
    op.drop_table('telegram_link_codes')
    op.drop_table('telegram_polling_cursor')
