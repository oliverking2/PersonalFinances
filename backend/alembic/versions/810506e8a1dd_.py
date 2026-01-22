"""empty message

Revision ID: 810506e8a1dd
Revises: 88fa944cb564
Create Date: 2025-12-01 22:12:28.378885

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "810506e8a1dd"
down_revision: Union[str, Sequence[str], None] = "88fa944cb564"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
