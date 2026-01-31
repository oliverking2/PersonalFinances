"""add_planned_transactions_user_enabled_index

Revision ID: 556b7afac9dd
Revises: 0c3f43741db0
Create Date: 2026-01-31 19:02:30.668872

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '556b7afac9dd'
down_revision: Union[str, Sequence[str], None] = '0c3f43741db0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add composite index for frequent query pattern (user_id, enabled)
    op.create_index(
        "idx_planned_transactions_user_enabled",
        "planned_transactions",
        ["user_id", "enabled"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_planned_transactions_user_enabled", table_name="planned_transactions")
