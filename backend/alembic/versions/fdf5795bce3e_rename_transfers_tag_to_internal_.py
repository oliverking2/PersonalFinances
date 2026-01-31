"""rename transfers tag to internal transfers

Revision ID: fdf5795bce3e
Revises: 5dde6f1d2170
Create Date: 2026-01-31 20:59:01.014574

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdf5795bce3e'
down_revision: Union[str, Sequence[str], None] = '5dde6f1d2170'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename 'Transfers' tag to 'Internal Transfers' for clarity."""
    op.execute("""
        UPDATE tags
        SET name = 'Internal Transfers'
        WHERE name = 'Transfers'
    """)


def downgrade() -> None:
    """Revert 'Internal Transfers' back to 'Transfers'."""
    op.execute("""
        UPDATE tags
        SET name = 'Transfers'
        WHERE name = 'Internal Transfers'
    """)
