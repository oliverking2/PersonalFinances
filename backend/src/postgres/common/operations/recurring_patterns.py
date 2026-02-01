"""Recurring pattern database operations.

This module provides CRUD operations for RecurringPattern entities and
pattern-transaction linking. Implements the opt-in model where detection
creates pending patterns that users accept to activate.
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from dateutil.relativedelta import relativedelta
from rapidfuzz import fuzz
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.postgres.common.enums import (
    RecurringDirection,
    RecurringFrequency,
    RecurringSource,
    RecurringStatus,
)
from src.postgres.common.models import (
    RecurringPattern,
    RecurringPatternTransaction,
    Transaction,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Text Normalisation
# =============================================================================


def normalize_for_matching(text: str) -> str:
    """Normalise text for pattern matching by removing variable parts.

    Strips dates, reference numbers, and other variable elements that would
    prevent matching recurring transactions from the same merchant.

    :param text: Raw merchant name or description.
    :returns: Normalised text for comparison.
    """
    if not text:
        return ""

    result = text.lower().strip()

    # Remove dates in common formats
    result = re.sub(r"\d{4}-\d{2}-\d{2}", "", result)  # YYYY-MM-DD
    result = re.sub(r"\d{2}/\d{2}/\d{4}", "", result)  # DD/MM/YYYY
    result = re.sub(r"\d{2}/\d{2}/\d{2}", "", result)  # DD/MM/YY
    result = re.sub(
        r"\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4}",
        "",
        result,
        flags=re.IGNORECASE,
    )

    # Remove reference numbers (common patterns)
    result = re.sub(r"\*+\d+", "", result)  # *123456 (card refs)
    result = re.sub(r"ref[:\s]*\w+", "", result, flags=re.IGNORECASE)  # REF: ABC123
    result = re.sub(r"#\d+", "", result)  # #12345

    # Clean up whitespace
    return re.sub(r"\s+", " ", result).strip()


# =============================================================================
# Transaction Matching
# =============================================================================


def merchant_fuzzy_matches(
    pattern_merchant: str,
    txn_merchant: str,
    threshold: int = 75,
) -> bool:
    """Check if transaction merchant fuzzy-matches pattern merchant.

    Uses rapidfuzz partial_ratio for substring matching, which handles
    variations like "Netflix" matching "NETFLIX.COM*ABC123".

    :param pattern_merchant: Merchant string from pattern.
    :param txn_merchant: Merchant string from transaction.
    :param threshold: Minimum similarity score (0-100).
    :returns: True if similarity exceeds threshold.
    """
    # Normalise both strings
    pattern_norm = normalize_for_matching(pattern_merchant)
    txn_norm = normalize_for_matching(txn_merchant)

    if not pattern_norm or not txn_norm:
        return False

    # Use partial_ratio for substring matching
    # This handles cases like "netflix" matching "netflix.com*12345"
    return fuzz.partial_ratio(pattern_norm, txn_norm) >= threshold


def transaction_matches_pattern(  # noqa: PLR0911
    txn: Transaction, pattern: RecurringPattern
) -> bool:
    """Check if a transaction matches a recurring pattern's rules.

    Matching algorithm priority:
    1. Direction check (fast fail)
    2. Account check (if specified)
    3. Amount tolerance check
    4. Merchant matching with normalisation
    5. Advanced rules (if present)

    :param txn: Transaction to check.
    :param pattern: Pattern with matching rules.
    :returns: True if transaction matches all rules.
    """
    # 1. Direction check (fast fail)
    if pattern.direction == RecurringDirection.EXPENSE.value and txn.amount >= 0:
        return False
    if pattern.direction == RecurringDirection.INCOME.value and txn.amount < 0:
        return False

    # 2. Account check (if specified)
    if pattern.account_id and txn.account_id != pattern.account_id:
        return False

    # 3. Amount tolerance check
    expected = float(abs(pattern.expected_amount))
    actual = float(abs(txn.amount))
    tolerance = float(pattern.amount_tolerance_pct) / 100
    if actual < expected * (1 - tolerance) or actual > expected * (1 + tolerance):
        return False

    # 4. Merchant matching with fuzzy matching
    # Use fuzzy matching to handle variations in merchant names
    merchant = txn.counterparty_name or txn.description or ""

    if pattern.merchant_contains and not merchant_fuzzy_matches(
        pattern.merchant_contains, merchant
    ):
        return False

    # 5. Advanced rules (if present)
    rules = pattern.advanced_rules or {}

    merchant_exact = rules.get("merchant_exact")
    if merchant_exact and merchant != normalize_for_matching(merchant_exact):
        return False

    merchant_regex = rules.get("merchant_regex")
    if merchant_regex:
        # Regex runs on RAW text (not normalised) for precise matching
        raw_merchant = (txn.counterparty_name or txn.description or "").lower()
        if not re.search(merchant_regex, raw_merchant, re.IGNORECASE):
            return False

    description = normalize_for_matching(txn.description or "")
    desc_contains = rules.get("description_contains")
    if desc_contains and desc_contains.lower() not in description:
        return False

    desc_not_contains = rules.get("description_not_contains")
    return not (desc_not_contains and desc_not_contains.lower() in description)


def find_matching_transactions(
    session: Session,
    pattern: RecurringPattern,
    *,
    limit: int | None = None,
) -> list[Transaction]:
    """Find all transactions matching a pattern's rules.

    :param session: SQLAlchemy session.
    :param pattern: Pattern with matching rules.
    :param limit: Maximum transactions to return.
    :returns: List of matching transactions ordered by booking date (descending).
    """
    # Start with direction and account filter (database-level)
    query = session.query(Transaction).join(Transaction.account)

    if pattern.account_id:
        query = query.filter(Transaction.account_id == pattern.account_id)

    # Direction filter at database level
    if pattern.direction == RecurringDirection.EXPENSE.value:
        query = query.filter(Transaction.amount < 0)
    else:
        query = query.filter(Transaction.amount >= 0)

    # Order by date
    query = query.order_by(Transaction.booking_date.desc())

    if limit:
        query = query.limit(limit * 3)  # Fetch extra for in-memory filtering

    transactions = query.all()

    # Apply full matching rules in Python
    matching = [txn for txn in transactions if transaction_matches_pattern(txn, pattern)]

    if limit:
        matching = matching[:limit]

    return matching


# =============================================================================
# Pattern CRUD
# =============================================================================


def get_pattern_by_id(session: Session, pattern_id: UUID) -> RecurringPattern | None:
    """Get a recurring pattern by its ID.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :returns: RecurringPattern if found, None otherwise.
    """
    return session.get(RecurringPattern, pattern_id)


def get_patterns_by_user_id(
    session: Session,
    user_id: UUID,
    *,
    status: RecurringStatus | None = None,
    frequency: RecurringFrequency | None = None,
    source: RecurringSource | None = None,
    min_confidence: Decimal | None = None,
) -> list[RecurringPattern]:
    """Get all recurring patterns for a user with optional filters.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param status: Filter by status.
    :param frequency: Filter by frequency.
    :param source: Filter by source (detected/manual).
    :param min_confidence: Minimum confidence score (0.0-1.0).
    :returns: List of patterns ordered by expected amount (descending).
    """
    query = session.query(RecurringPattern).filter(RecurringPattern.user_id == user_id)

    if status:
        query = query.filter(RecurringPattern.status == status.value)

    if frequency:
        query = query.filter(RecurringPattern.frequency == frequency.value)

    if source:
        query = query.filter(RecurringPattern.source == source.value)

    if min_confidence is not None:
        query = query.filter(RecurringPattern.confidence_score >= min_confidence)

    return query.order_by(RecurringPattern.expected_amount).all()


def get_upcoming_patterns(
    session: Session,
    user_id: UUID,
    days: int = 7,
) -> list[RecurringPattern]:
    """Get patterns with upcoming expected dates.

    Only returns active patterns (not pending, paused, or cancelled).

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param days: Number of days to look ahead (default 7).
    :returns: List of patterns ordered by next expected date.
    """
    now = datetime.now(UTC)
    end_date = now + timedelta(days=days)

    return (
        session.query(RecurringPattern)
        .filter(
            RecurringPattern.user_id == user_id,
            RecurringPattern.status == RecurringStatus.ACTIVE.value,
            RecurringPattern.next_expected_date >= now,
            RecurringPattern.next_expected_date <= end_date,
        )
        .order_by(RecurringPattern.next_expected_date)
        .all()
    )


def create_pattern(
    session: Session,
    user_id: UUID,
    name: str,
    expected_amount: Decimal,
    frequency: RecurringFrequency,
    direction: RecurringDirection,
    anchor_date: datetime,
    *,
    account_id: UUID | None = None,
    tag_id: UUID | None = None,
    currency: str = "GBP",
    status: RecurringStatus = RecurringStatus.ACTIVE,
    source: RecurringSource = RecurringSource.MANUAL,
    merchant_contains: str | None = None,
    amount_tolerance_pct: Decimal = Decimal("10.0"),
    advanced_rules: dict[str, Any] | None = None,
    notes: str | None = None,
    confidence_score: Decimal | None = None,
    occurrence_count: int | None = None,
    detection_reason: str | None = None,
) -> RecurringPattern:
    """Create a new recurring pattern.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param name: Display name for the pattern.
    :param expected_amount: Expected transaction amount.
    :param frequency: Payment frequency.
    :param direction: Income or expense.
    :param anchor_date: Reference date for calculating next occurrence.
    :param account_id: Optional account filter.
    :param tag_id: Optional tag for budget integration.
    :param currency: Currency code (default GBP).
    :param status: Pattern status (default ACTIVE for manual).
    :param source: Creation source (default MANUAL).
    :param merchant_contains: Merchant name substring to match.
    :param amount_tolerance_pct: Amount tolerance percentage (default 10%).
    :param advanced_rules: JSONB rules for advanced matching.
    :param notes: User notes.
    :param confidence_score: Detection confidence (for detected patterns).
    :param occurrence_count: Number of detected transactions.
    :param detection_reason: Human-readable detection explanation.
    :returns: Created RecurringPattern entity.
    """
    next_date = _calculate_next_expected_date(anchor_date, frequency)

    pattern = RecurringPattern(
        user_id=user_id,
        account_id=account_id,
        tag_id=tag_id,
        name=name.strip()[:100],
        expected_amount=expected_amount,
        currency=currency,
        frequency=frequency.value,
        direction=direction.value,
        anchor_date=anchor_date,
        next_expected_date=next_date,
        last_matched_date=anchor_date,
        status=status.value,
        source=source.value,
        merchant_contains=merchant_contains.strip()[:256] if merchant_contains else None,
        amount_tolerance_pct=amount_tolerance_pct,
        advanced_rules=advanced_rules,
        notes=notes,
        match_count=0,
        confidence_score=confidence_score,
        occurrence_count=occurrence_count,
        detection_reason=detection_reason,
    )
    session.add(pattern)
    session.flush()

    logger.info(
        f"Created recurring pattern: id={pattern.id}, user_id={user_id}, "
        f"name={name}, status={status.value}, source={source.value}"
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
    :returns: Next expected date, or None for irregular patterns.
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


def update_pattern(  # noqa: PLR0912
    session: Session,
    pattern_id: UUID,
    *,
    name: str | None = None,
    status: RecurringStatus | None = None,
    notes: str | None | object = _NOT_SET,
    expected_amount: Decimal | None = None,
    frequency: RecurringFrequency | None = None,
    merchant_contains: str | None | object = _NOT_SET,
    amount_tolerance_pct: Decimal | None = None,
    advanced_rules: dict[str, Any] | None | object = _NOT_SET,
    end_date: datetime | None | object = _NOT_SET,
    last_matched_date: datetime | None = None,
    tag_id: UUID | None | object = _NOT_SET,
) -> RecurringPattern | None:
    """Update a recurring pattern.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :param name: New display name.
    :param status: New status.
    :param notes: New notes (pass None to clear).
    :param expected_amount: New expected amount.
    :param frequency: New frequency.
    :param merchant_contains: New merchant match string (pass None to clear).
    :param amount_tolerance_pct: New tolerance percentage.
    :param advanced_rules: New advanced rules (pass None to clear).
    :param end_date: End date for cancelled patterns.
    :param last_matched_date: Last matched transaction date.
    :param tag_id: Tag for budget integration (pass None to clear).
    :returns: Updated RecurringPattern, or None if not found.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    if pattern is None:
        return None

    if name is not None:
        pattern.name = name.strip()[:100]

    if status is not None:
        pattern.status = status.value

    if notes is not _NOT_SET:
        pattern.notes = notes if isinstance(notes, str) else None

    if expected_amount is not None:
        pattern.expected_amount = expected_amount

    if frequency is not None:
        pattern.frequency = frequency.value
        # Recalculate next expected date when frequency changes
        if pattern.last_matched_date:
            pattern.next_expected_date = _calculate_next_expected_date(
                pattern.last_matched_date, frequency
            )

    if merchant_contains is not _NOT_SET:
        mc = merchant_contains if isinstance(merchant_contains, str) else None
        pattern.merchant_contains = mc.strip()[:256] if mc else None

    if amount_tolerance_pct is not None:
        pattern.amount_tolerance_pct = amount_tolerance_pct

    if advanced_rules is not _NOT_SET:
        pattern.advanced_rules = advanced_rules if isinstance(advanced_rules, dict) else None

    if end_date is not _NOT_SET:
        pattern.end_date = end_date if isinstance(end_date, datetime) else None

    if tag_id is not _NOT_SET:
        pattern.tag_id = tag_id if isinstance(tag_id, UUID) else None

    if last_matched_date is not None:
        pattern.last_matched_date = last_matched_date
        # Recalculate next expected date
        pattern.next_expected_date = _calculate_next_expected_date(
            last_matched_date, pattern.frequency_enum
        )

    session.flush()
    logger.info(f"Updated recurring pattern: id={pattern_id}")
    return pattern


def delete_pattern(session: Session, pattern_id: UUID) -> bool:
    """Delete a recurring pattern.

    This also removes all pattern-transaction links (via CASCADE).

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :returns: True if deleted, False if not found.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    if pattern is None:
        return False

    session.delete(pattern)
    session.flush()
    logger.info(f"Deleted recurring pattern: id={pattern_id}")
    return True


# =============================================================================
# Status Transitions
# =============================================================================


def accept_pattern(session: Session, pattern_id: UUID) -> RecurringPattern | None:
    """Accept a pending pattern (pending -> active).

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :returns: Updated RecurringPattern, or None if not found.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    if pattern is None:
        return None

    if pattern.status != RecurringStatus.PENDING.value:
        logger.warning(
            f"Cannot accept pattern {pattern_id}: status is {pattern.status}, not pending"
        )
        return pattern

    return update_pattern(session, pattern_id, status=RecurringStatus.ACTIVE)


def pause_pattern(session: Session, pattern_id: UUID) -> RecurringPattern | None:
    """Pause a pattern (active -> paused).

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :returns: Updated RecurringPattern, or None if not found.
    """
    return update_pattern(session, pattern_id, status=RecurringStatus.PAUSED)


def resume_pattern(session: Session, pattern_id: UUID) -> RecurringPattern | None:
    """Resume a paused pattern (paused -> active).

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :returns: Updated RecurringPattern, or None if not found.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    if pattern is None:
        return None

    if pattern.status != RecurringStatus.PAUSED.value:
        logger.warning(
            f"Cannot resume pattern {pattern_id}: status is {pattern.status}, not paused"
        )
        return pattern

    return update_pattern(session, pattern_id, status=RecurringStatus.ACTIVE)


def cancel_pattern(
    session: Session, pattern_id: UUID, end_date: datetime | None = None
) -> RecurringPattern | None:
    """Cancel a pattern (-> cancelled).

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :param end_date: When the pattern ended (defaults to now).
    :returns: Updated RecurringPattern, or None if not found.
    """
    if end_date is None:
        end_date = datetime.now(UTC)

    return update_pattern(session, pattern_id, status=RecurringStatus.CANCELLED, end_date=end_date)


# =============================================================================
# Transaction Linking
# =============================================================================


def link_transaction_to_pattern(
    session: Session,
    pattern_id: UUID,
    transaction_id: UUID,
    *,
    is_manual: bool = False,
) -> RecurringPatternTransaction | None:
    """Link a transaction to a recurring pattern.

    Each transaction can only be linked to one pattern. If already linked
    to a different pattern, the link will be moved.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :param transaction_id: Transaction's UUID.
    :param is_manual: Whether the user manually linked (vs auto-matched).
    :returns: Created/updated link, or None if pattern/transaction not found.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    transaction = session.get(Transaction, transaction_id)

    if pattern is None or transaction is None:
        return None

    # Check if transaction is already linked to any pattern
    existing = (
        session.query(RecurringPatternTransaction)
        .filter(RecurringPatternTransaction.transaction_id == transaction_id)
        .first()
    )

    if existing:
        if existing.pattern_id == pattern_id:
            # Already linked to this pattern
            return existing
        # Move to new pattern
        existing.pattern_id = pattern_id
        existing.matched_at = datetime.now(UTC)
        existing.is_manual = is_manual
        session.flush()
        logger.info(f"Moved transaction {transaction_id} to pattern {pattern_id}")
        return existing

    # Create new link
    link = RecurringPatternTransaction(
        pattern_id=pattern_id,
        transaction_id=transaction_id,
        matched_at=datetime.now(UTC),
        is_manual=is_manual,
    )
    session.add(link)

    # Update pattern match count
    pattern.match_count = pattern.match_count + 1

    session.flush()
    logger.info(
        f"Linked transaction to pattern: pattern_id={pattern_id}, "
        f"transaction_id={transaction_id}, is_manual={is_manual}"
    )
    return link


def unlink_transaction_from_pattern(
    session: Session,
    pattern_id: UUID,
    transaction_id: UUID,
) -> bool:
    """Unlink a transaction from a pattern.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :param transaction_id: Transaction's UUID.
    :returns: True if unlinked, False if link not found.
    """
    link = (
        session.query(RecurringPatternTransaction)
        .filter(
            RecurringPatternTransaction.pattern_id == pattern_id,
            RecurringPatternTransaction.transaction_id == transaction_id,
        )
        .first()
    )

    if not link:
        return False

    # Update pattern match count
    pattern = get_pattern_by_id(session, pattern_id)
    if pattern and pattern.match_count > 0:
        pattern.match_count = pattern.match_count - 1

    session.delete(link)
    session.flush()
    logger.info(
        f"Unlinked transaction from pattern: pattern_id={pattern_id}, "
        f"transaction_id={transaction_id}"
    )
    return True


def relink_pattern_transactions(session: Session, pattern_id: UUID) -> int:
    """Re-run matching for a pattern, unlinking old and linking new matches.

    Call this after editing matching rules to update linked transactions.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :returns: Number of transactions now linked.
    """
    pattern = get_pattern_by_id(session, pattern_id)
    if pattern is None:
        return 0

    # Get currently linked transactions (keep manual links)
    current_links = (
        session.query(RecurringPatternTransaction)
        .filter(RecurringPatternTransaction.pattern_id == pattern_id)
        .all()
    )
    manual_txn_ids = {link.transaction_id for link in current_links if link.is_manual}
    auto_txn_ids = {link.transaction_id for link in current_links if not link.is_manual}

    # Find new matches
    matching_txns = find_matching_transactions(session, pattern)
    new_match_ids = {txn.id for txn in matching_txns}

    # Unlink auto-matched that no longer match (keep manual)
    for txn_id in auto_txn_ids - new_match_ids:
        unlink_transaction_from_pattern(session, pattern_id, txn_id)

    # Link new matches
    for txn_id in new_match_ids - auto_txn_ids - manual_txn_ids:
        link_transaction_to_pattern(session, pattern_id, txn_id, is_manual=False)

    # Update last matched date if we have matches
    if matching_txns:
        latest_date = max(txn.booking_date for txn in matching_txns if txn.booking_date)
        if latest_date:
            pattern.last_matched_date = latest_date
            pattern.next_expected_date = _calculate_next_expected_date(
                latest_date, pattern.frequency_enum
            )

    # Update match count
    pattern.match_count = len(new_match_ids | manual_txn_ids)
    session.flush()

    return pattern.match_count


def get_pattern_transactions(
    session: Session,
    pattern_id: UUID,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[Transaction], int]:
    """Get transactions linked to a pattern with pagination.

    :param session: SQLAlchemy session.
    :param pattern_id: Pattern's UUID.
    :param limit: Maximum transactions to return (None for all).
    :param offset: Number of transactions to skip.
    :returns: Tuple of (transactions list, total count).
    """
    links = (
        session.query(RecurringPatternTransaction)
        .filter(RecurringPatternTransaction.pattern_id == pattern_id)
        .all()
    )

    if not links:
        return [], 0

    transaction_ids = [link.transaction_id for link in links]
    total = len(transaction_ids)

    query = (
        session.query(Transaction)
        .filter(Transaction.id.in_(transaction_ids))
        .order_by(Transaction.booking_date.desc())
    )

    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)

    return query.all(), total


# =============================================================================
# Summary & Statistics
# =============================================================================


def calculate_monthly_total(
    session: Session,
    user_id: UUID,
) -> Decimal:
    """Calculate total monthly recurring spend.

    Converts all frequencies to monthly equivalent amounts.
    Only includes active patterns.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :returns: Total monthly equivalent amount (as absolute value).
    """
    patterns = get_patterns_by_user_id(session, user_id, status=RecurringStatus.ACTIVE)

    total = Decimal("0")
    for pattern in patterns:
        monthly = _to_monthly_equivalent(abs(pattern.expected_amount), pattern.frequency_enum)
        total += monthly

    return total


def calculate_monthly_totals_by_direction(
    session: Session,
    user_id: UUID,
) -> dict[str, Decimal]:
    """Calculate monthly totals separated by direction.

    Only includes active patterns.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :returns: Dict with 'income', 'expenses', and 'net' monthly totals.
    """
    patterns = get_patterns_by_user_id(session, user_id, status=RecurringStatus.ACTIVE)

    income_total = Decimal("0")
    expense_total = Decimal("0")

    for pattern in patterns:
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
    :returns: Dict mapping direction to count.
    """
    results = (
        session.query(RecurringPattern.direction, func.count(RecurringPattern.id))
        .filter(
            RecurringPattern.user_id == user_id,
            RecurringPattern.status == RecurringStatus.ACTIVE.value,
        )
        .group_by(RecurringPattern.direction)
        .all()
    )
    return {RecurringDirection(direction): count for direction, count in results}


def count_patterns_by_status(session: Session, user_id: UUID) -> dict[RecurringStatus, int]:
    """Count patterns grouped by status.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :returns: Dict mapping status to count.
    """
    results = (
        session.query(RecurringPattern.status, func.count(RecurringPattern.id))
        .filter(RecurringPattern.user_id == user_id)
        .group_by(RecurringPattern.status)
        .all()
    )
    return {RecurringStatus(status): count for status, count in results}


def _to_monthly_equivalent(amount: Decimal, frequency: RecurringFrequency) -> Decimal:
    """Convert amount to monthly equivalent.

    :param amount: Original amount.
    :param frequency: Payment frequency.
    :returns: Monthly equivalent amount.
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


# =============================================================================
# Detection Sync (for Dagster)
# =============================================================================


def sync_detected_pattern(
    session: Session,
    user_id: UUID,
    account_id: UUID,
    name: str,
    expected_amount: Decimal,
    frequency: RecurringFrequency,
    direction: RecurringDirection,
    confidence_score: Decimal,
    occurrence_count: int,
    last_occurrence_date: datetime,
    next_expected_date: datetime | None,
    merchant_contains: str | None = None,
    currency: str = "GBP",
    amount_tolerance_pct: Decimal = Decimal("10.0"),
    detection_reason: str | None = None,
) -> tuple[RecurringPattern, bool]:
    """Sync a detected pattern from dbt mart to PostgreSQL.

    Creates new patterns as PENDING. Does not modify patterns that users
    have already acted on (active, paused, cancelled).

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param account_id: Account's UUID.
    :param name: Display name for the pattern.
    :param expected_amount: Expected transaction amount.
    :param frequency: Detected payment frequency.
    :param direction: Income or expense direction.
    :param confidence_score: Detection confidence (0.0-1.0).
    :param occurrence_count: Number of matched transactions.
    :param last_occurrence_date: Date of most recent occurrence.
    :param next_expected_date: Calculated next expected date.
    :param merchant_contains: Merchant name to match.
    :param currency: Currency code (default GBP).
    :param amount_tolerance_pct: Amount tolerance percentage.
    :param detection_reason: Human-readable detection explanation.
    :returns: Tuple of (pattern, created) where created is True if new.
    """
    # Look for existing pattern with similar merchant for this account
    existing_patterns = (
        session.query(RecurringPattern)
        .filter(
            RecurringPattern.user_id == user_id,
            RecurringPattern.account_id == account_id,
        )
        .all()
    )

    # Find matching pattern by merchant_contains
    merchant_lower = (merchant_contains or name).lower() if merchant_contains else name.lower()
    existing = None
    for pat in existing_patterns:
        pat_merchant = (pat.merchant_contains or pat.name).lower()
        if pat_merchant == merchant_lower:
            existing = pat
            break

    if existing:
        # Only update if status is still 'pending' (user hasn't acted on it)
        if existing.status == RecurringStatus.PENDING.value:
            existing.expected_amount = expected_amount
            existing.frequency = frequency.value
            existing.confidence_score = confidence_score
            existing.occurrence_count = occurrence_count
            existing.last_matched_date = last_occurrence_date
            existing.next_expected_date = next_expected_date
            existing.amount_tolerance_pct = amount_tolerance_pct
            existing.currency = currency
            if detection_reason:
                existing.detection_reason = detection_reason
            session.flush()
            logger.info(f"Updated pending pattern: id={existing.id}, name={name}")
        # For user-managed patterns, still update amount if it changed
        # This ensures the forecast uses current pricing
        elif existing.expected_amount != expected_amount:
            existing.expected_amount = expected_amount
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

    # Create new pattern as PENDING
    pattern = create_pattern(
        session,
        user_id=user_id,
        name=name,
        expected_amount=expected_amount,
        frequency=frequency,
        direction=direction,
        anchor_date=last_occurrence_date,
        account_id=account_id,
        currency=currency,
        status=RecurringStatus.PENDING,
        source=RecurringSource.DETECTED,
        merchant_contains=merchant_contains,
        amount_tolerance_pct=amount_tolerance_pct,
        confidence_score=confidence_score,
        occurrence_count=occurrence_count,
        detection_reason=detection_reason,
    )

    # Update next expected date if provided
    if next_expected_date:
        pattern.next_expected_date = next_expected_date
        session.flush()

    logger.info(
        f"Created pending pattern: id={pattern.id}, user_id={user_id}, "
        f"name={name}, confidence={confidence_score}"
    )
    return pattern, True


# =============================================================================
# Create From Transactions
# =============================================================================


def create_pattern_from_transactions(
    session: Session,
    user_id: UUID,
    transaction_ids: list[UUID],
    name: str,
    frequency: RecurringFrequency,
    *,
    merchant_contains: str | None = None,
    notes: str | None = None,
) -> RecurringPattern | None:
    """Create a pattern from selected transactions.

    Infers amount, direction, and account from the transactions.
    Created as ACTIVE with source=MANUAL.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param transaction_ids: List of transaction UUIDs to link.
    :param name: Display name for the pattern.
    :param frequency: Payment frequency.
    :param merchant_contains: Optional merchant match string.
    :param notes: Optional notes.
    :returns: Created pattern, or None if transactions invalid.
    """
    if len(transaction_ids) < 1:
        return None

    # Fetch transactions
    transactions = (
        session.query(Transaction)
        .filter(Transaction.id.in_(transaction_ids))
        .order_by(Transaction.booking_date.desc())
        .all()
    )

    if not transactions:
        return None

    # Infer direction from amounts (majority wins)
    expense_count = sum(1 for t in transactions if t.amount < 0)
    income_count = len(transactions) - expense_count
    direction = (
        RecurringDirection.EXPENSE if expense_count >= income_count else RecurringDirection.INCOME
    )

    # Use latest transaction amount
    latest = transactions[0]
    expected_amount = abs(latest.amount)

    # Use account from latest transaction
    account_id = latest.account_id

    # Infer merchant_contains from counterparty if not provided
    if not merchant_contains and latest.counterparty_name:
        merchant_contains = normalize_for_matching(latest.counterparty_name)

    # Anchor date from latest transaction
    anchor_date = latest.booking_date or datetime.now(UTC)
    if anchor_date.tzinfo is None:
        anchor_date = anchor_date.replace(tzinfo=UTC)

    # Create pattern
    pattern = create_pattern(
        session,
        user_id=user_id,
        name=name,
        expected_amount=expected_amount,
        frequency=frequency,
        direction=direction,
        anchor_date=anchor_date,
        account_id=account_id,
        currency=latest.currency,
        status=RecurringStatus.ACTIVE,
        source=RecurringSource.MANUAL,
        merchant_contains=merchant_contains,
        notes=notes,
    )

    # Link all provided transactions
    for txn_id in transaction_ids:
        link_transaction_to_pattern(session, pattern.id, txn_id, is_manual=True)

    return pattern
