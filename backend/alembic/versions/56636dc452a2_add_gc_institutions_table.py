"""add gc_institutions table

Revision ID: 56636dc452a2
Revises: 28663f2f3281
Create Date: 2026-01-24 18:34:30.689219

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "56636dc452a2"
down_revision: Union[str, Sequence[str], None] = "28663f2f3281"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "gc_institutions",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("bic", sa.String(length=32), nullable=True),
        sa.Column("logo", sa.String(length=512), nullable=True),
        sa.Column("countries", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("gc_institutions")
