"""Add account settings fields

Revision ID: e9f0a1b2c3d4
Revises: d8aca9a4c2ae
Create Date: 2026-01-25 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d8aca9a4c2ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category and min_balance fields to accounts table."""
    op.add_column("accounts", sa.Column("category", sa.String(30), nullable=True))
    op.add_column("accounts", sa.Column("min_balance", sa.Numeric(18, 2), nullable=True))


def downgrade() -> None:
    """Remove category and min_balance fields from accounts table."""
    op.drop_column("accounts", "min_balance")
    op.drop_column("accounts", "category")
