"""Recurring pattern database operations.

This module provides CRUD operations for RecurringPattern entities and
pattern-transaction linking.
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.postgres.common.enums import RecurringDirection, RecurringFrequency, RecurringStatus
from src.postgres.common.models import (
    RecurringPattern,
    RecurringPatternTransaction,
    Transaction,
)

logger = logging.getLogger(__name__)


def get_pattern_by_id(session: Session, pattern_id: UUID) -> RecurringPattern | None:
    """Get a recurring pattern by its ID.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :return: RecurringPattern if found, None otherwise.
    """
    return session.get(RecurringPattern, pattern_id)


def get_patterns_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    status: RecurringStatus | None = None,
    frequency: RecurringFrequency | None = None,
    min_confidence: Decimal | None = None,
    include_dismissed: bool = False,
) -> list[RecurringPattern]:
    """Get all recurring patterns for a user with optional filters.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param status: Filter by status.
    :param frequency: Filter by frequency.
    :param min_confidence: Minimum confidence score (0.0-1.0).
    :param include_dismissed: Include dismissed patterns (default False).
    :return: List of patterns ordered by expected amount (descending).
    """
    query = session.query(RecurringPattern).filter(RecurringPattern.user_id == user_id)

    if status:
        query = query.filter(RecurringPattern.status == status.value)
    elif not include_dismissed:
        query = query.filter(RecurringPattern.status != RecurringStatus.DISMISSED.value)

    if frequency:
        query = query.filter(RecurringPattern.frequency == frequency.value)

    if min_confidence is not None:
        query = query.filter(RecurringPattern.confidence_score >= min_confidence)

    return query.order_by(RecurringPattern.expected_amount).all()


def get_upcoming_patterns(
    session: Session,
    user_id: UUID,
    days: int = 7,
) -> list[RecurringPattern]:
    """Get patterns with upcoming expected dates.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param days: Number of days to look ahead (default 7).
    :return: List of patterns ordered by next expected date.
    """
    now = datetime.now(UTC)
    end_date = now + timedelta(days=days)

    return (
        session.query(RecurringPattern)
        .filter(
            RecurringPattern.user_id == user_id,
            RecurringPattern.status.in_(
                [RecurringStatus.CONFIRMED.value, RecurringStatus.DETECTED.value]
            ),
            RecurringPattern.next_expected_date >= now,
            RecurringPattern.next_expected_date <= end_date,
        )
        .order_by(RecurringPattern.next_expected_date)
        .all()
    )


def calculate_monthly_total(
    session: Session,
    user_id: UUID,
) -> Decimal:
    """Calculate total monthly recurring spend.

    Converts all frequencies to monthly equivalent amounts.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Total monthly equivalent amount (as absolute value).
    """
    patterns = get_patterns_by_user_id(session, user_id)

    total = Decimal("0")
    for pattern in patterns:
        if pattern.status_enum in (
            RecurringStatus.CONFIRMED,
            RecurringStatus.DETECTED,
            RecurringStatus.MANUAL,
        ):
            monthly = _to_monthly_equivalent(abs(pattern.expected_amount), pattern.frequency_enum)
            total += monthly

    return total


def calculate_monthly_totals_by_direction(
    session: Session,
    user_id: UUID,
) -> dict[str, Decimal]:
    """Calculate monthly totals separated by direction.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Dict with 'income', 'expenses', and 'net' monthly totals.
    """
    patterns = get_patterns_by_user_id(session, user_id)

    income_total = Decimal("0")
    expense_total = Decimal("0")

    for pattern in patterns:
        if pattern.status_enum in (
            RecurringStatus.CONFIRMED,
            RecurringStatus.DETECTED,
            RecurringStatus.MANUAL,
        ):
            monthly = _to_monthly_equivalent(abs(pattern.expected_amount), pattern.frequency_enum)
            if pattern.direction_enum == RecurringDirection.INCOME:
                income_total += monthly
            else:
                expense_total += monthly

    return {
        "income": income_total,
        "expenses": expense_total,
        "net": income_total - expense_total,
    }


def count_patterns_by_direction(session: Session, user_id: UUID) -> dict[RecurringDirection, int]:
    """Count active patterns grouped by direction.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Dict mapping direction to count.
    """
    results = (
        session.query(RecurringPattern.direction, func.count(RecurringPattern.id))
        .filter(
            RecurringPattern.user_id == user_id,
            RecurringPattern.status != RecurringStatus.DISMISSED.value,
        )
        .group_by(RecurringPattern.direction)
        .all()
    )
    return {RecurringDirection(direction): count for direction, count in results}


def _to_monthly_equivalent(amount: Decimal, frequency: RecurringFrequency) -> Decimal:
    """Convert amount to monthly equivalent.

    :param amount: Original amount.
    :param frequency: Payment frequency.
    :return: Monthly equivalent amount.
    """
    multipliers = {
        RecurringFrequency.WEEKLY: Decimal("4.33"),
        RecurringFrequency.FORTNIGHTLY: Decimal("2.17"),
        RecurringFrequency.MONTHLY: Decimal("1"),
        RecurringFrequency.QUARTERLY: Decimal("1") / Decimal("3"),
        RecurringFrequency.ANNUAL: Decimal("1") / Decimal("12"),
        RecurringFrequency.IRREGULAR: Decimal("1"),
    }
    return amount * multipliers.get(frequency, Decimal("1"))


def create_pattern(
    session: Session,
    user_id: UUID,
    merchant_pattern: str,
    expected_amount: Decimal,
    frequency: RecurringFrequency,
    anchor_date: datetime,
    *,
    account_id: UUID | None = None,
    currency: str = "GBP",
    amount_variance: Decimal = Decimal("0"),
    confidence_score: Decimal = Decimal("0.5"),
    occurrence_count: int = 0,
    status: RecurringStatus = RecurringStatus.DETECTED,
    display_name: str | None = None,
    notes: str | None = None,
) -> RecurringPattern:
    """Create a new recurring pattern.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param merchant_pattern: Normalised merchant name/pattern.
    :param expected_amount: Expected transaction amount.
    :param frequency: Payment frequency.
    :param anchor_date: Reference date for calculating next occurrence.
    :param account_id: Optional account filter.
    :param currency: Currency code (default GBP).
    :param amount_variance: Allowed percentage variance.
    :param confidence_score: Detection confidence (0.0-1.0).
    :param occurrence_count: Number of matched transactions.
    :param status: Pattern status.
    :param display_name: User-friendly name override.
    :param notes: User notes.
    :return: Created RecurringPattern entity.
    """
    next_date = _calculate_next_expected_date(anchor_date, frequency)

    pattern = RecurringPattern(
        user_id=user_id,
        merchant_pattern=merchant_pattern.strip()[:256],
        account_id=account_id,
        expected_amount=expected_amount,
        amount_variance=amount_variance,
        currency=currency,
        frequency=frequency.value,
        anchor_date=anchor_date,
        next_expected_date=next_date,
        last_occurrence_date=anchor_date,
        confidence_score=confidence_score,
        occurrence_count=occurrence_count,
        status=status.value,
        display_name=display_name[:100] if display_name else None,
        notes=notes,
    )
    session.add(pattern)
    session.flush()

    logger.info(
        f"Created recurring pattern: id={pattern.id}, user_id={user_id}, "
        f"merchant={merchant_pattern}, frequency={frequency.value}"
    )
    return pattern


def _calculate_next_expected_date(
    anchor_date: datetime, frequency: RecurringFrequency
) -> datetime | None:
    """Calculate the next expected date based on anchor and frequency.

    Uses relativedelta for month-based intervals to properly handle
    varying month lengths (31-day months, February, etc.).

    :param anchor_date: Reference date.
    :param frequency: Payment frequency.
    :return: Next expected date, or None for irregular patterns.
    """
    # Use relativedelta for month-based intervals to avoid drift
    intervals: dict[RecurringFrequency, timedelta | relativedelta] = {
        RecurringFrequency.WEEKLY: timedelta(days=7),
        RecurringFrequency.FORTNIGHTLY: timedelta(days=14),
        RecurringFrequency.MONTHLY: relativedelta(months=1),
        RecurringFrequency.QUARTERLY: relativedelta(months=3),
        RecurringFrequency.ANNUAL: relativedelta(years=1),
    }

    interval = intervals.get(frequency)
    if not interval:
        return None

    # Ensure anchor_date has timezone info for comparison
    if anchor_date.tzinfo is None:
        anchor_date = anchor_date.replace(tzinfo=UTC)

    next_date = anchor_date + interval
    now = datetime.now(UTC)

    # Keep advancing until we're in the future
    while next_date < now:
        next_date += interval

    return next_date


_NOT_SET = object()


def update_pattern(
    session: Session,
    pattern_id: UUID,
    *,
    status: RecurringStatus | None = None,
    display_name: str | None | object = _NOT_SET,
    notes: str | None | object = _NOT_SET,
    expected_amount: Decimal | None = None,
    frequency: RecurringFrequency | None = None,
    last_occurrence_date: datetime | None = None,
    confidence_score: Decimal | None = None,
    occurrence_count: int | None = None,
) -> RecurringPattern | None:
    """Update a recurring pattern.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :param status: New status.
    :param display_name: New display name (pass None to clear).
    :param notes: New notes (pass None to clear).
    :param expected_amount: New expected amount.
    :param frequency: New frequency.
    :param last_occurrence_date: New last occurrence date.
    :param confidence_score: New confidence score.
    :param occurrence_count: New occurrence count.
    :return: Updated RecurringPattern, or None if not found.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    if pattern is None:
        return None

    if status is not None:
        pattern.status = status.value

    if display_name is not _NOT_SET:
        display_name_str = display_name if isinstance(display_name, str) else None
        pattern.display_name = display_name_str[:100] if display_name_str else None

    if notes is not _NOT_SET:
        pattern.notes = notes if isinstance(notes, str) else None

    if expected_amount is not None:
        pattern.expected_amount = expected_amount

    if frequency is not None:
        pattern.frequency = frequency.value
        # Recalculate next expected date when frequency changes
        if pattern.last_occurrence_date:
            pattern.next_expected_date = _calculate_next_expected_date(
                pattern.last_occurrence_date, frequency
            )

    if last_occurrence_date is not None:
        pattern.last_occurrence_date = last_occurrence_date
        # Recalculate next expected date
        pattern.next_expected_date = _calculate_next_expected_date(
            last_occurrence_date, pattern.frequency_enum
        )

    if confidence_score is not None:
        pattern.confidence_score = confidence_score

    if occurrence_count is not None:
        pattern.occurrence_count = occurrence_count

    session.flush()
    logger.info(f"Updated recurring pattern: id={pattern_id}")
    return pattern


def delete_pattern(session: Session, pattern_id: UUID) -> bool:
    """Delete a recurring pattern.

    This also removes all pattern-transaction links (via CASCADE).

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :return: True if deleted, False if not found.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    if pattern is None:
        return False

    session.delete(pattern)
    session.flush()
    logger.info(f"Deleted recurring pattern: id={pattern_id}")
    return True


def dismiss_pattern(session: Session, pattern_id: UUID) -> RecurringPattern | None:
    """Dismiss a recurring pattern (mark as false positive).

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :return: Updated RecurringPattern, or None if not found.
    """
    return update_pattern(session, pattern_id, status=RecurringStatus.DISMISSED)


def confirm_pattern(session: Session, pattern_id: UUID) -> RecurringPattern | None:
    """Confirm a detected recurring pattern.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :return: Updated RecurringPattern, or None if not found.
    """
    return update_pattern(session, pattern_id, status=RecurringStatus.CONFIRMED)


def pause_pattern(session: Session, pattern_id: UUID) -> RecurringPattern | None:
    """Pause a recurring pattern (temporarily hide).

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :return: Updated RecurringPattern, or None if not found.
    """
    return update_pattern(session, pattern_id, status=RecurringStatus.PAUSED)


def link_transaction_to_pattern(
    session: Session,
    pattern_id: UUID,
    transaction_id: UUID,
    *,
    amount_match: bool = True,
    date_match: bool = True,
) -> RecurringPatternTransaction | None:
    """Link a transaction to a recurring pattern.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :param transaction_id: Transaction's UUID.
    :param amount_match: Whether the amount matched expected.
    :param date_match: Whether the date matched expected.
    :return: Created link, or None if pattern/transaction not found.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    transaction = session.get(Transaction, transaction_id)

    if pattern is None or transaction is None:
        return None

    # Check if link already exists
    existing = (
        session.query(RecurringPatternTransaction)
        .filter(
            RecurringPatternTransaction.pattern_id == pattern_id,
            RecurringPatternTransaction.transaction_id == transaction_id,
        )
        .first()
    )
    if existing:
        return existing

    link = RecurringPatternTransaction(
        pattern_id=pattern_id,
        transaction_id=transaction_id,
        amount_match=amount_match,
        date_match=date_match,
    )
    session.add(link)
    session.flush()

    logger.info(
        f"Linked transaction to pattern: pattern_id={pattern_id}, transaction_id={transaction_id}"
    )
    return link


def get_pattern_transactions(session: Session, pattern_id: UUID) -> list[Transaction]:
    """Get all transactions linked to a pattern.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :return: List of transactions ordered by booking date (descending).
    """
    links = (
        session.query(RecurringPatternTransaction)
        .filter(RecurringPatternTransaction.pattern_id == pattern_id)
        .all()
    )

    if not links:
        return []

    transaction_ids = [link.transaction_id for link in links]
    return (
        session.query(Transaction)
        .filter(Transaction.id.in_(transaction_ids))
        .order_by(Transaction.booking_date.desc())
        .all()
    )


def get_pattern_by_merchant(
    session: Session,
    user_id: UUID,
    merchant_pattern: str,
    account_id: UUID | None = None,
) -> RecurringPattern | None:
    """Get a pattern by user, merchant, and optional account.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param merchant_pattern: Normalised merchant pattern.
    :param account_id: Optional account filter.
    :return: RecurringPattern if found, None otherwise.
    """
    query = session.query(RecurringPattern).filter(
        RecurringPattern.user_id == user_id,
        RecurringPattern.merchant_pattern == merchant_pattern,
    )

    if account_id:
        query = query.filter(RecurringPattern.account_id == account_id)
    else:
        query = query.filter(RecurringPattern.account_id.is_(None))

    return query.first()


def count_patterns_by_status(session: Session, user_id: UUID) -> dict[RecurringStatus, int]:
    """Count patterns grouped by status.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Dict mapping status to count.
    """
    results = (
        session.query(RecurringPattern.status, func.count(RecurringPattern.id))
        .filter(RecurringPattern.user_id == user_id)
        .group_by(RecurringPattern.status)
        .all()
    )
    return {RecurringStatus(status): count for status, count in results}


def _extract_merchant_base_key(merchant_pattern: str) -> str:
    """Extract base key from merchant pattern by removing amount bucket suffix.

    Handles keys like "merchant_exp_£16" -> "merchant_exp".

    :param merchant_pattern: Full merchant pattern with amount bucket.
    :returns: Base key without amount bucket.
    """
    return re.sub(r"_£\d+$", "", merchant_pattern)


def sync_detected_pattern(
    session: Session,
    user_id: UUID,
    account_id: UUID,
    merchant_pattern: str,
    expected_amount: Decimal,
    frequency: RecurringFrequency,
    confidence_score: Decimal,
    occurrence_count: int,
    last_occurrence_date: datetime,
    next_expected_date: datetime | None,
    display_name: str | None = None,
    currency: str = "GBP",
    amount_variance: Decimal = Decimal("0"),
) -> tuple[RecurringPattern, bool]:
    """Sync a detected pattern from dbt mart to PostgreSQL.

    Creates new patterns or updates existing detected ones. Patterns with
    user-managed status (confirmed, dismissed, paused, manual) are not modified.

    Matching is done on the base merchant key (without amount bucket) to handle
    price changes without creating duplicates.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param account_id: Account's UUID.
    :param merchant_pattern: Normalised merchant name (with amount bucket).
    :param expected_amount: Expected transaction amount.
    :param frequency: Detected payment frequency.
    :param confidence_score: Detection confidence (0.0-1.0).
    :param occurrence_count: Number of matched transactions.
    :param last_occurrence_date: Date of most recent occurrence.
    :param next_expected_date: Calculated next expected date.
    :param display_name: Display name for the pattern.
    :param currency: Currency code (default GBP).
    :param amount_variance: Amount variance percentage.
    :return: Tuple of (pattern, created) where created is True if new.
    """
    # Extract base key (without amount bucket) for flexible matching
    base_key = _extract_merchant_base_key(merchant_pattern)

    # Find existing patterns for this account and check for base key match
    account_patterns = (
        session.query(RecurringPattern)
        .filter(
            RecurringPattern.user_id == user_id,
            RecurringPattern.account_id == account_id,
        )
        .all()
    )

    # Find pattern with matching base key
    existing = None
    for pat in account_patterns:
        if _extract_merchant_base_key(pat.merchant_pattern) == base_key:
            existing = pat
            break

    if existing:
        # Only update if status is still 'detected' (user hasn't acted on it)
        if existing.status == RecurringStatus.DETECTED.value:
            # Update merchant_pattern to reflect current amount bucket
            existing.merchant_pattern = merchant_pattern[:256]
            existing.expected_amount = expected_amount
            existing.frequency = frequency.value
            existing.confidence_score = confidence_score
            existing.occurrence_count = occurrence_count
            existing.last_occurrence_date = last_occurrence_date
            existing.next_expected_date = next_expected_date
            existing.amount_variance = amount_variance
            existing.currency = currency
            if display_name:
                existing.display_name = display_name[:100]
            session.flush()
            logger.info(f"Updated detected pattern: id={existing.id}, merchant={merchant_pattern}")
        # For user-managed patterns, still update amount if it changed
        # This ensures the forecast uses current pricing
        elif existing.expected_amount != expected_amount:
            existing.expected_amount = expected_amount
            existing.merchant_pattern = merchant_pattern[:256]
            session.flush()
            logger.info(
                f"Updated amount for user-managed pattern: id={existing.id}, "
                f"new_amount={expected_amount}"
            )
        else:
            logger.debug(
                f"Skipped pattern with user status: id={existing.id}, status={existing.status}"
            )
        return existing, False

    # Create new pattern
    pattern = RecurringPattern(
        user_id=user_id,
        account_id=account_id,
        merchant_pattern=merchant_pattern[:256],
        expected_amount=expected_amount,
        amount_variance=amount_variance,
        currency=currency,
        frequency=frequency.value,
        anchor_date=last_occurrence_date,
        next_expected_date=next_expected_date,
        last_occurrence_date=last_occurrence_date,
        confidence_score=confidence_score,
        occurrence_count=occurrence_count,
        status=RecurringStatus.DETECTED.value,
        display_name=display_name[:100] if display_name else None,
    )
    session.add(pattern)
    session.flush()

    logger.info(
        f"Created detected pattern: id={pattern.id}, user_id={user_id}, "
        f"merchant={merchant_pattern}, confidence={confidence_score}"
    )
    return pattern, True
