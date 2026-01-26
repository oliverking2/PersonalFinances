"""Transaction split database operations.

This module provides operations for managing transaction splits, which allow
allocating a transaction's amount across multiple tags for accurate budgeting.
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from src.postgres.common.models import Tag, Transaction, TransactionSplit

logger = logging.getLogger(__name__)


class SplitValidationError(Exception):
    """Raised when split validation fails."""

    pass


def get_transaction_splits(session: Session, transaction_id: UUID) -> list[TransactionSplit]:
    """Get all splits for a transaction.

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :return: List of splits for the transaction.
    """
    return (
        session.query(TransactionSplit)
        .filter(TransactionSplit.transaction_id == transaction_id)
        .all()
    )


def validate_splits(
    transaction_amount: Decimal,
    splits: list[tuple[UUID, Decimal]],
) -> None:
    """Validate that splits sum to the transaction amount.

    :param transaction_amount: The transaction amount (can be negative).
    :param splits: List of (tag_id, amount) tuples. Amounts should be positive.
    :raises SplitValidationError: If validation fails.
    """
    if not splits:
        raise SplitValidationError("At least one split is required")

    # Check for duplicate tags
    tag_ids = [tag_id for tag_id, _ in splits]
    if len(tag_ids) != len(set(tag_ids)):
        raise SplitValidationError("Duplicate tags in splits")

    # Check all amounts are positive
    for tag_id, amount in splits:
        if amount <= 0:
            raise SplitValidationError(f"Split amount must be positive: {amount}")

    # Check sum equals absolute transaction amount
    total = sum(amount for _, amount in splits)
    expected = abs(transaction_amount)

    # Allow for small rounding differences (up to 0.01)
    if abs(total - expected) > Decimal("0.01"):
        raise SplitValidationError(
            f"Split amounts ({total}) must equal transaction amount ({expected})"
        )


def set_transaction_splits(
    session: Session,
    transaction: Transaction,
    splits: list[tuple[UUID, Decimal]],
) -> list[TransactionSplit]:
    """Set splits for a transaction (replaces all existing splits).

    :param session: SQLAlchemy session.
    :param transaction: Transaction to split.
    :param splits: List of (tag_id, amount) tuples.
    :return: Created TransactionSplit entities.
    :raises SplitValidationError: If validation fails.
    """
    # Validate splits
    validate_splits(transaction.amount, splits)

    # Delete existing splits
    session.query(TransactionSplit).filter(
        TransactionSplit.transaction_id == transaction.id
    ).delete()

    # Create new splits
    created_splits = []
    for tag_id, amount in splits:
        split = TransactionSplit(
            transaction_id=transaction.id,
            tag_id=tag_id,
            amount=amount,
        )
        session.add(split)
        created_splits.append(split)

    session.flush()
    logger.info(f"Set transaction splits: transaction_id={transaction.id}, count={len(splits)}")
    return created_splits


def clear_transaction_splits(session: Session, transaction_id: UUID) -> bool:
    """Remove all splits from a transaction.

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :return: True if any splits were deleted.
    """
    count = (
        session.query(TransactionSplit)
        .filter(TransactionSplit.transaction_id == transaction_id)
        .delete()
    )
    session.flush()

    if count > 0:
        logger.info(f"Cleared transaction splits: transaction_id={transaction_id}, count={count}")

    return count > 0


def get_splits_with_tags(
    session: Session, transaction_id: UUID
) -> list[tuple[TransactionSplit, Tag]]:
    """Get splits with their associated tag data.

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :return: List of (split, tag) tuples.
    """
    rows = (
        session.query(TransactionSplit, Tag)
        .join(Tag, TransactionSplit.tag_id == Tag.id)
        .filter(TransactionSplit.transaction_id == transaction_id)
        .all()
    )
    # Convert Row objects to plain tuples for type consistency
    return [(row[0], row[1]) for row in rows]
