"""rename tables

Revision ID: 9a45116053dd
Revises: 28e8b4ad51ce
Create Date: 2025-12-01 22:20:23.286156

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9a45116053dd"
down_revision: Union[str, Sequence[str], None] = "28e8b4ad51ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename tables to add gc_ prefix
    op.rename_table("requisition_links", "gc_requisition_links")
    op.rename_table("bank_accounts", "gc_bank_accounts")
    op.rename_table("balances", "gc_balances")


def downgrade() -> None:
    """Downgrade schema."""
    # Rename tables back to original names
    op.rename_table("gc_balances", "balances")
    op.rename_table("gc_bank_accounts", "bank_accounts")
    op.rename_table("gc_requisition_links", "requisition_links")
