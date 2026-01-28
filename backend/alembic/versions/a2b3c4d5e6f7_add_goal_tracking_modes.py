"""add_goal_tracking_modes

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-01-28 10:00:00.000000

Add tracking_mode, starting_balance, and target_balance columns to savings_goals.
Existing goals default to 'manual' tracking mode.
"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tracking mode fields to savings_goals."""
    # Add tracking_mode column with default 'manual' for existing goals
    op.add_column(
        "savings_goals",
        sa.Column(
            "tracking_mode",
            sa.String(length=20),
            nullable=False,
            server_default="manual",
        ),
    )

    # Add starting_balance for delta mode (snapshot of account balance at goal creation)
    op.add_column(
        "savings_goals",
        sa.Column("starting_balance", sa.Numeric(precision=18, scale=2), nullable=True),
    )

    # Add target_balance for target_balance mode (account balance to reach)
    op.add_column(
        "savings_goals",
        sa.Column("target_balance", sa.Numeric(precision=18, scale=2), nullable=True),
    )

    # Add CHECK constraint: non-manual modes require account_id
    op.create_check_constraint(
        "ck_savings_goals_tracking_mode_account",
        "savings_goals",
        "tracking_mode = 'manual' OR account_id IS NOT NULL",
    )

    # Add CHECK constraint: target_balance mode requires target_balance field
    op.create_check_constraint(
        "ck_savings_goals_target_balance_required",
        "savings_goals",
        "tracking_mode != 'target_balance' OR target_balance IS NOT NULL",
    )


def downgrade() -> None:
    """Remove tracking mode fields from savings_goals."""
    # Drop CHECK constraints
    op.drop_constraint(
        "ck_savings_goals_target_balance_required", "savings_goals", type_="check"
    )
    op.drop_constraint(
        "ck_savings_goals_tracking_mode_account", "savings_goals", type_="check"
    )

    # Drop columns
    op.drop_column("savings_goals", "target_balance")
    op.drop_column("savings_goals", "starting_balance")
    op.drop_column("savings_goals", "tracking_mode")
