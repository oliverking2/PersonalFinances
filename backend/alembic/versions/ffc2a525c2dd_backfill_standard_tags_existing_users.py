"""backfill_standard_tags_existing_users

Revision ID: ffc2a525c2dd
Revises: 7c5f0dbb0343
Create Date: 2026-01-26 20:30:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ffc2a525c2dd"
down_revision: Union[str, Sequence[str], None] = "7c5f0dbb0343"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Standard tags to seed (must match STANDARD_TAGS in operations/tags.py)
STANDARD_TAGS = [
    {"name": "Groceries", "colour": "#22c55e"},
    {"name": "Dining", "colour": "#f97316"},
    {"name": "Transport", "colour": "#3b82f6"},
    {"name": "Utilities", "colour": "#8b5cf6"},
    {"name": "Entertainment", "colour": "#ec4899"},
    {"name": "Shopping", "colour": "#14b8a6"},
    {"name": "Subscriptions", "colour": "#6366f1"},
    {"name": "Health", "colour": "#ef4444"},
    {"name": "Travel", "colour": "#0ea5e9"},
    {"name": "Income", "colour": "#10b981"},
    {"name": "Internal Transfers", "colour": "#6b7280"},
    {"name": "Fees", "colour": "#f59e0b"},
]


def upgrade() -> None:
    """Backfill standard tags for all existing users who don't have them."""
    conn = op.get_bind()

    # Get all user IDs
    users_result = conn.execute(sa.text("SELECT id FROM users"))
    user_ids = [row[0] for row in users_result]

    for user_id in user_ids:
        for tag_def in STANDARD_TAGS:
            # Check if user already has this tag (by name)
            existing = conn.execute(
                sa.text(
                    "SELECT id FROM tags WHERE user_id = :user_id AND name = :name"
                ),
                {"user_id": user_id, "name": tag_def["name"]},
            ).fetchone()

            if existing:
                # Tag exists - update it to be standard if not already
                conn.execute(
                    sa.text(
                        "UPDATE tags SET is_standard = true WHERE id = :tag_id AND is_standard = false"
                    ),
                    {"tag_id": existing[0]},
                )
            else:
                # Create the standard tag
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO tags (id, user_id, name, colour, is_standard, is_hidden, created_at, updated_at)
                        VALUES (:id, :user_id, :name, :colour, true, false, NOW(), NOW())
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "user_id": user_id,
                        "name": tag_def["name"],
                        "colour": tag_def["colour"],
                    },
                )


def downgrade() -> None:
    """Remove the is_standard flag from backfilled tags (doesn't delete them)."""
    # We don't delete tags on downgrade as users may have used them
    # Just mark them as non-standard
    op.execute("UPDATE tags SET is_standard = false WHERE is_standard = true")
