"""init v2

Revision ID: 78c333d567f6
Revises: 4badb0accb9e
Create Date: 2025-12-01 21:51:23.827043

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "78c333d567f6"
down_revision: Union[str, Sequence[str], None] = "4badb0accb9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
