"""recurring_patterns_redesign

Revision ID: 0c3f43741db0
Revises: 204b49cb0781
Create Date: 2026-01-31 16:55:14.566964

Redesigns recurring_patterns for opt-in model:
- Renames display_name -> name, merchant_pattern -> merchant_contains
- Adds source, amount_tolerance_pct, match_count, detection_reason, ai_metadata
- Updates status: detected->pending, confirmed/manual->active, dismissed->deleted
- Adds unique constraint on transaction links
"""
from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0c3f43741db0'
down_revision: Union[str, Sequence[str], None] = '204b49cb0781'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =========================================================================
    # Step 1: Add new columns as NULLABLE first (for data migration)
    # =========================================================================

    # recurring_patterns - add new columns
    op.add_column('recurring_patterns', sa.Column('name', sa.String(length=100), nullable=True))
    op.add_column('recurring_patterns', sa.Column('last_matched_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recurring_patterns', sa.Column('end_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recurring_patterns', sa.Column('source', sa.String(length=20), nullable=True))
    op.add_column('recurring_patterns', sa.Column('merchant_contains', sa.String(length=256), nullable=True))
    op.add_column('recurring_patterns', sa.Column('amount_tolerance_pct', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('recurring_patterns', sa.Column('advanced_rules', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))
    op.add_column('recurring_patterns', sa.Column('match_count', sa.Integer(), nullable=True))
    op.add_column('recurring_patterns', sa.Column('detection_reason', sa.String(length=500), nullable=True))
    op.add_column('recurring_patterns', sa.Column('ai_metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))

    # recurring_pattern_transactions - add new columns
    op.add_column('recurring_pattern_transactions', sa.Column('matched_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recurring_pattern_transactions', sa.Column('is_manual', sa.Boolean(), nullable=True))

    # =========================================================================
    # Step 2: Migrate data from old columns to new columns
    # =========================================================================

    # Migrate recurring_patterns data
    op.execute("""
        UPDATE recurring_patterns
        SET name = COALESCE(display_name, merchant_pattern, 'Unknown'),
            source = CASE
                WHEN status = 'manual' THEN 'manual'
                ELSE 'detected'
            END,
            merchant_contains = merchant_pattern,
            amount_tolerance_pct = COALESCE(
                CASE
                    WHEN amount_variance IS NOT NULL AND amount_variance > 0 AND expected_amount != 0
                    THEN LEAST((amount_variance / ABS(expected_amount)) * 100, 99.99)
                    ELSE 10.0
                END,
                10.0
            ),
            last_matched_date = last_occurrence_date,
            match_count = COALESCE(occurrence_count, 0)
    """)

    # Update status values: detected->pending, confirmed->active, manual->active
    op.execute("""
        UPDATE recurring_patterns
        SET status = CASE
            WHEN status = 'detected' THEN 'pending'
            WHEN status = 'confirmed' THEN 'active'
            WHEN status = 'manual' THEN 'active'
            ELSE status
        END
        WHERE status IN ('detected', 'confirmed', 'manual')
    """)

    # Delete dismissed patterns (they can be re-detected later)
    op.execute("DELETE FROM recurring_patterns WHERE status = 'dismissed'")

    # Migrate recurring_pattern_transactions data
    now_iso = datetime.now(UTC).isoformat()
    op.execute(f"""
        UPDATE recurring_pattern_transactions
        SET matched_at = created_at,
            is_manual = false
        WHERE matched_at IS NULL
    """)

    # =========================================================================
    # Step 3: Make required columns NOT NULL
    # =========================================================================

    op.alter_column('recurring_patterns', 'name', nullable=False)
    op.alter_column('recurring_patterns', 'source', nullable=False)
    op.alter_column('recurring_patterns', 'amount_tolerance_pct', nullable=False)
    op.alter_column('recurring_patterns', 'match_count', nullable=False)

    op.alter_column('recurring_pattern_transactions', 'matched_at', nullable=False)
    op.alter_column('recurring_pattern_transactions', 'is_manual', nullable=False)

    # Make confidence_score and occurrence_count nullable (they're only for detected)
    op.alter_column('recurring_patterns', 'confidence_score',
               existing_type=sa.NUMERIC(precision=3, scale=2),
               nullable=True,
               existing_server_default=sa.text('0.5'))
    op.alter_column('recurring_patterns', 'occurrence_count',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('0'))

    # =========================================================================
    # Step 4: Update indexes
    # =========================================================================

    # Update index on recurring_patterns (change unique=True to unique=False, use new column)
    op.drop_index('idx_recurring_patterns_user_merchant', table_name='recurring_patterns')
    op.create_index('idx_recurring_patterns_user_merchant', 'recurring_patterns', ['user_id', 'merchant_contains', 'account_id'], unique=False)

    # Clean up duplicate transaction links before adding unique constraint
    # Keep only the most recent link for each transaction
    op.execute("""
        DELETE FROM recurring_pattern_transactions
        WHERE id NOT IN (
            SELECT DISTINCT ON (transaction_id) id
            FROM recurring_pattern_transactions
            ORDER BY transaction_id, matched_at DESC
        )
    """)

    # Update indexes on recurring_pattern_transactions for unique transaction constraint
    op.drop_index('idx_pattern_transaction_unique', table_name='recurring_pattern_transactions')
    op.drop_index('idx_pattern_transactions_transaction', table_name='recurring_pattern_transactions')
    op.create_index('idx_pattern_transactions_transaction_unique', 'recurring_pattern_transactions', ['transaction_id'], unique=True)

    # =========================================================================
    # Step 5: Drop old columns
    # =========================================================================

    op.drop_column('recurring_patterns', 'amount_variance')
    op.drop_column('recurring_patterns', 'last_occurrence_date')
    op.drop_column('recurring_patterns', 'display_name')
    op.drop_column('recurring_patterns', 'merchant_pattern')

    op.drop_column('recurring_pattern_transactions', 'created_at')
    op.drop_column('recurring_pattern_transactions', 'date_match')
    op.drop_column('recurring_pattern_transactions', 'amount_match')


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('recurring_patterns', sa.Column('merchant_pattern', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.add_column('recurring_patterns', sa.Column('display_name', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.add_column('recurring_patterns', sa.Column('last_occurrence_date', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('recurring_patterns', sa.Column('amount_variance', sa.NUMERIC(precision=5, scale=2), server_default=sa.text("'0'::numeric"), autoincrement=False, nullable=False))
    op.drop_index('idx_recurring_patterns_user_merchant', table_name='recurring_patterns')
    op.create_index(op.f('idx_recurring_patterns_user_merchant'), 'recurring_patterns', ['user_id', 'merchant_pattern', 'account_id'], unique=True)
    op.alter_column('recurring_patterns', 'occurrence_count',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('0'))
    op.alter_column('recurring_patterns', 'confidence_score',
               existing_type=sa.NUMERIC(precision=3, scale=2),
               nullable=False,
               existing_server_default=sa.text('0.5'))
    op.drop_column('recurring_patterns', 'ai_metadata')
    op.drop_column('recurring_patterns', 'detection_reason')
    op.drop_column('recurring_patterns', 'match_count')
    op.drop_column('recurring_patterns', 'advanced_rules')
    op.drop_column('recurring_patterns', 'amount_tolerance_pct')
    op.drop_column('recurring_patterns', 'merchant_contains')
    op.drop_column('recurring_patterns', 'source')
    op.drop_column('recurring_patterns', 'end_date')
    op.drop_column('recurring_patterns', 'last_matched_date')
    op.drop_column('recurring_patterns', 'name')
    op.add_column('recurring_pattern_transactions', sa.Column('amount_match', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False))
    op.add_column('recurring_pattern_transactions', sa.Column('date_match', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False))
    op.add_column('recurring_pattern_transactions', sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False))
    op.drop_index('idx_pattern_transactions_transaction_unique', table_name='recurring_pattern_transactions')
    op.create_index(op.f('idx_pattern_transactions_transaction'), 'recurring_pattern_transactions', ['transaction_id'], unique=False)
    op.create_index(op.f('idx_pattern_transaction_unique'), 'recurring_pattern_transactions', ['pattern_id', 'transaction_id'], unique=True)
    op.drop_column('recurring_pattern_transactions', 'is_manual')
    op.drop_column('recurring_pattern_transactions', 'matched_at')
    # ### end Alembic commands ###
