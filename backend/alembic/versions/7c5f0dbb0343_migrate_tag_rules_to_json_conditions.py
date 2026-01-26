"""migrate_tag_rules_to_json_conditions

Revision ID: 7c5f0dbb0343
Revises: 6bc206b77d47
Create Date: 2026-01-26 19:45:12.040283

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '7c5f0dbb0343'
down_revision: Union[str, Sequence[str], None] = '6bc206b77d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate tag_rules from individual columns to JSONB conditions."""
    # 1. Add the new conditions column
    op.add_column('tag_rules', sa.Column('conditions', JSONB(), nullable=False, server_default='{}'))

    # 2. Migrate existing data to JSON
    # Build JSON object from existing columns, excluding nulls
    op.execute("""
        UPDATE tag_rules
        SET conditions = (
            SELECT jsonb_strip_nulls(jsonb_build_object(
                'merchant_contains', merchant_contains,
                'merchant_exact', merchant_exact,
                'description_contains', description_contains,
                'min_amount', min_amount,
                'max_amount', max_amount,
                'merchant_not_contains', merchant_not_contains,
                'description_not_contains', description_not_contains
            ))
        )
    """)

    # 3. Drop the old columns (keep account_id as it's a proper FK)
    op.drop_column('tag_rules', 'merchant_contains')
    op.drop_column('tag_rules', 'merchant_exact')
    op.drop_column('tag_rules', 'description_contains')
    op.drop_column('tag_rules', 'min_amount')
    op.drop_column('tag_rules', 'max_amount')
    op.drop_column('tag_rules', 'merchant_not_contains')
    op.drop_column('tag_rules', 'description_not_contains')

    # 4. Remove the server default now that existing rows are migrated
    op.alter_column('tag_rules', 'conditions', server_default=None)


def downgrade() -> None:
    """Restore individual columns from JSONB conditions."""
    # 1. Re-add the individual columns
    op.add_column('tag_rules', sa.Column('merchant_contains', sa.String(200), nullable=True))
    op.add_column('tag_rules', sa.Column('merchant_exact', sa.String(200), nullable=True))
    op.add_column('tag_rules', sa.Column('description_contains', sa.String(200), nullable=True))
    op.add_column('tag_rules', sa.Column('min_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('tag_rules', sa.Column('max_amount', sa.Numeric(18, 2), nullable=True))
    op.add_column('tag_rules', sa.Column('merchant_not_contains', sa.String(200), nullable=True))
    op.add_column('tag_rules', sa.Column('description_not_contains', sa.String(200), nullable=True))

    # 2. Migrate data back from JSON
    op.execute("""
        UPDATE tag_rules
        SET
            merchant_contains = conditions->>'merchant_contains',
            merchant_exact = conditions->>'merchant_exact',
            description_contains = conditions->>'description_contains',
            min_amount = (conditions->>'min_amount')::numeric(18,2),
            max_amount = (conditions->>'max_amount')::numeric(18,2),
            merchant_not_contains = conditions->>'merchant_not_contains',
            description_not_contains = conditions->>'description_not_contains'
    """)

    # 3. Drop the conditions column
    op.drop_column('tag_rules', 'conditions')
