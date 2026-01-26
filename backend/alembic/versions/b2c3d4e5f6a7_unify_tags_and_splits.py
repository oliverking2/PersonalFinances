"""unify_tags_and_splits

Revision ID: b2c3d4e5f6a7
Revises: ffc2a525c2dd
Create Date: 2026-01-26 21:00:00.000000

This migration unifies the tags and splits models:
- All tagging is done via transaction_splits (default 100% amount)
- Adds is_auto and rule_id to transaction_splits for auto-tagging
- Migrates existing transaction_tags to transaction_splits
- Drops the transaction_tags table
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "ffc2a525c2dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate from separate tags/splits to unified splits-only model."""
    # Step 1: Add is_auto and rule_id columns to transaction_splits
    op.add_column(
        "transaction_splits",
        sa.Column("is_auto", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "transaction_splits",
        sa.Column(
            "rule_id",
            sa.UUID(),
            sa.ForeignKey("tag_rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Step 2: Migrate data from transaction_tags to transaction_splits
    # For each transaction_tag, create a split with 100% of the transaction amount
    op.execute(
        """
        INSERT INTO transaction_splits (id, transaction_id, tag_id, amount, is_auto, rule_id, created_at)
        SELECT
            gen_random_uuid(),
            tt.transaction_id,
            tt.tag_id,
            ABS(t.amount),  -- Always store positive amount
            tt.is_auto,
            tt.rule_id,
            tt.created_at
        FROM transaction_tags tt
        JOIN transactions t ON t.id = tt.transaction_id
        -- Only migrate if there's no existing split for this transaction/tag combo
        WHERE NOT EXISTS (
            SELECT 1 FROM transaction_splits ts
            WHERE ts.transaction_id = tt.transaction_id
            AND ts.tag_id = tt.tag_id
        )
        """
    )

    # Step 3: Drop the transaction_tags table
    op.drop_table("transaction_tags")

    # Step 4: Add index for rule_id lookups
    op.create_index(
        "idx_transaction_splits_rule_id",
        "transaction_splits",
        ["rule_id"],
    )


def downgrade() -> None:
    """Revert to separate tags/splits model."""
    # Step 1: Recreate transaction_tags table
    op.create_table(
        "transaction_tags",
        sa.Column("transaction_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("is_auto", sa.Boolean(), nullable=False, default=False),
        sa.Column("rule_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("transaction_id", "tag_id"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["tag_rules.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_transaction_tags_tag_id", "transaction_tags", ["tag_id"])

    # Step 2: Migrate data back (take the first split per transaction as the "tag")
    # This is lossy - we lose split amounts, but preserve the tag associations
    op.execute(
        """
        INSERT INTO transaction_tags (transaction_id, tag_id, is_auto, rule_id, created_at)
        SELECT DISTINCT ON (transaction_id)
            transaction_id,
            tag_id,
            is_auto,
            rule_id,
            created_at
        FROM transaction_splits
        ORDER BY transaction_id, created_at ASC
        """
    )

    # Step 3: Drop new columns from transaction_splits
    op.drop_index("idx_transaction_splits_rule_id", table_name="transaction_splits")
    op.drop_column("transaction_splits", "rule_id")
    op.drop_column("transaction_splits", "is_auto")
