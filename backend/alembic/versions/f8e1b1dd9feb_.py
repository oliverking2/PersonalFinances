"""empty message

Revision ID: f8e1b1dd9feb
Revises: 810506e8a1dd, ddd49c1cf114
Create Date: 2025-12-01 22:15:23.503432

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8e1b1dd9feb"
down_revision: Union[str, Sequence[str], None] = ("810506e8a1dd", "ddd49c1cf114")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
