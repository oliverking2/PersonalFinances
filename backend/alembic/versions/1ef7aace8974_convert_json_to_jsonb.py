"""convert_json_to_jsonb

Revision ID: 1ef7aace8974
Revises: 1570934fc13b
Create Date: 2026-01-25 09:59:42.017936

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1ef7aace8974'
down_revision: Union[str, Sequence[str], None] = '1570934fc13b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Convert JSON to JSONB for better PostgreSQL performance and indexing
    op.alter_column(
        "gc_institutions",
        "countries",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
        postgresql_using="countries::jsonb",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "gc_institutions",
        "countries",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=True,
        postgresql_using="countries::json",
    )
