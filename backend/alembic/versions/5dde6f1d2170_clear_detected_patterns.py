"""clear_detected_patterns

Revision ID: 5dde6f1d2170
Revises: 556b7afac9dd
Create Date: 2026-01-31 20:27:05.598990

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dde6f1d2170'
down_revision: Union[str, Sequence[str], None] = '556b7afac9dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Delete all detected patterns for fresh start with improved algorithm.

    This clears auto-detected patterns so they can be re-detected with:
    - Improved confidence calculation
    - Fuzzy merchant matching
    Manual patterns (source='manual') are preserved.
    """
    # Delete pattern-transaction links for detected patterns first (FK constraint)
    op.execute("""
        DELETE FROM recurring_pattern_transactions
        WHERE pattern_id IN (
            SELECT id FROM recurring_patterns WHERE source = 'detected'
        )
    """)

    # Delete all auto-detected patterns (preserves manual patterns)
    op.execute("DELETE FROM recurring_patterns WHERE source = 'detected'")


def downgrade() -> None:
    """No rollback - patterns will be re-detected on next Dagster run."""
    pass
