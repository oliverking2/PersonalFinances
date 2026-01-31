"""Financial milestone database operations.

This module provides CRUD operations for FinancialMilestone entities.
Used for tracking net worth targets and achievements.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.models import FinancialMilestone

logger = logging.getLogger(__name__)


def get_milestone_by_id(
    session: Session,
    milestone_id: UUID,
) -> FinancialMilestone | None:
    """Get a financial milestone by its ID.

    :param session: SQLAlchemy session.
    :param milestone_id: Milestone's UUID.
    :return: FinancialMilestone if found, None otherwise.
    """
    return session.get(FinancialMilestone, milestone_id)


def get_milestones_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    achieved_only: bool = False,
    pending_only: bool = False,
) -> list[FinancialMilestone]:
    """Get all milestones for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param achieved_only: If True, only return achieved milestones.
    :param pending_only: If True, only return unachieved milestones.
    :return: List of milestones ordered by target_amount ascending.
    """
    query = session.query(FinancialMilestone).filter(FinancialMilestone.user_id == user_id)

    if achieved_only:
        query = query.filter(FinancialMilestone.achieved.is_(True))
    elif pending_only:
        query = query.filter(FinancialMilestone.achieved.is_(False))

    return query.order_by(FinancialMilestone.target_amount.asc()).all()


def create_milestone(
    session: Session,
    user_id: UUID,
    name: str,
    target_amount: Decimal,
    *,
    target_date: datetime | None = None,
    colour: str = "#f59e0b",
    notes: str | None = None,
) -> FinancialMilestone:
    """Create a new financial milestone.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param name: Milestone name (e.g., "Emergency Fund", "First £100K").
    :param target_amount: Net worth target to reach.
    :param target_date: Optional deadline for the milestone.
    :param colour: Hex colour for chart display (default amber).
    :param notes: Optional notes.
    :return: Created FinancialMilestone entity.
    """
    milestone = FinancialMilestone(
        user_id=user_id,
        name=name,
        target_amount=target_amount,
        target_date=target_date,
        colour=colour,
        notes=notes,
    )
    session.add(milestone)
    session.flush()

    logger.info(
        f"Created financial milestone: id={milestone.id}, user_id={user_id}, "
        f"name={name}, target_amount={target_amount}"
    )
    return milestone


def update_milestone(
    session: Session,
    milestone_id: UUID,
    *,
    name: str | None = None,
    target_amount: Decimal | None = None,
    target_date: datetime | None | object = ...,  # Sentinel to distinguish None from "not set"
    colour: str | None = None,
    notes: str | None | object = ...,
) -> FinancialMilestone | None:
    """Update a financial milestone.

    Use ... (Ellipsis) as sentinel for fields that shouldn't be updated.
    Use None to clear nullable fields.

    :param session: SQLAlchemy session.
    :param milestone_id: Milestone's UUID.
    :param name: New name.
    :param target_amount: New target amount.
    :param target_date: New target date (None to clear, ... to skip).
    :param colour: New colour.
    :param notes: New notes (None to clear, ... to skip).
    :return: Updated FinancialMilestone, or None if not found.
    """
    milestone = get_milestone_by_id(session, milestone_id)
    if milestone is None:
        return None

    if name is not None:
        milestone.name = name

    if target_amount is not None:
        milestone.target_amount = target_amount

    if target_date is not ...:
        milestone.target_date = target_date  # type: ignore[assignment]

    if colour is not None:
        milestone.colour = colour

    if notes is not ...:
        milestone.notes = notes  # type: ignore[assignment]

    session.flush()
    logger.info(f"Updated financial milestone: id={milestone_id}")
    return milestone


def mark_milestone_achieved(
    session: Session,
    milestone_id: UUID,
    achieved_at: datetime | None = None,
) -> FinancialMilestone | None:
    """Mark a milestone as achieved.

    :param session: SQLAlchemy session.
    :param milestone_id: Milestone's UUID.
    :param achieved_at: When the milestone was achieved (defaults to now).
    :return: Updated milestone, or None if not found.
    """
    milestone = get_milestone_by_id(session, milestone_id)
    if milestone is None:
        return None

    milestone.achieved = True
    milestone.achieved_at = achieved_at or datetime.now(UTC)

    session.flush()
    logger.info(f"Marked milestone as achieved: id={milestone_id}")
    return milestone


def delete_milestone(session: Session, milestone_id: UUID) -> bool:
    """Delete a financial milestone.

    :param session: SQLAlchemy session.
    :param milestone_id: Milestone's UUID.
    :return: True if deleted, False if not found.
    """
    milestone = get_milestone_by_id(session, milestone_id)
    if milestone is None:
        return False

    session.delete(milestone)
    session.flush()
    logger.info(f"Deleted financial milestone: id={milestone_id}")
    return True


def check_and_update_achievements(
    session: Session,
    user_id: UUID,
    current_net_worth: Decimal,
) -> list[FinancialMilestone]:
    """Check if any pending milestones should be marked as achieved.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param current_net_worth: User's current net worth.
    :return: List of milestones that were just achieved.
    """
    pending = get_milestones_by_user_id(session, user_id, pending_only=True)
    newly_achieved = []

    now = datetime.now(UTC)
    for milestone in pending:
        if current_net_worth >= milestone.target_amount:
            milestone.achieved = True
            milestone.achieved_at = now
            newly_achieved.append(milestone)
            logger.info(
                f"Milestone auto-achieved: id={milestone.id}, "
                f"target={milestone.target_amount}, current={current_net_worth}"
            )

    if newly_achieved:
        session.flush()

    return newly_achieved
