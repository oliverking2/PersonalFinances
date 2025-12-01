"""remove transactions

Revision ID: 88fa944cb564
Revises: 50caa30626e4
Create Date: 2025-12-01 22:11:49.264397

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "88fa944cb564"
down_revision: Union[str, Sequence[str], None] = "50caa30626e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
