"""drop_category_from_recurring_patterns

Revision ID: e77ce7f14b11
Revises: c3d4e5f6a7b8
Create Date: 2026-01-27 22:14:27.874475

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e77ce7f14b11'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('recurring_patterns', 'category')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('recurring_patterns', sa.Column('category', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
