"""Tag rule database operations.

This module provides CRUD operations for TagRule entities and rule matching logic.
"""

import logging
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.postgres.common.models import (
    Account,
    Connection,
    TagRule,
    Transaction,
    TransactionSplit,
)

logger = logging.getLogger(__name__)


class RuleConditions(TypedDict, total=False):
    """Rule matching conditions stored in JSONB. All fields are optional.

    Note: account_id is NOT included here - it's a separate FK column on TagRule
    for referential integrity.
    """

    # Include conditions (all must match)
    merchant_contains: str | None
    merchant_exact: str | None
    description_contains: str | None
    min_amount: float | None  # Stored as float in JSON, converted to Decimal for comparison
    max_amount: float | None

    # Exclude conditions (none must match)
    merchant_not_contains: str | None
    description_not_contains: str | None


def get_tag_rule_by_id(session: Session, rule_id: UUID) -> TagRule | None:
    """Get a tag rule by its ID.

    :param session: SQLAlchemy session.
    :param rule_id: Rule's UUID.
    :return: TagRule if found, None otherwise.
    """
    return session.get(TagRule, rule_id)


def get_tag_rules_by_user_id(
    session: Session,
    user_id: UUID,
    tag_id: UUID | None = None,
    enabled_only: bool = False,
) -> list[TagRule]:
    """Get all tag rules for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param tag_id: Optional tag ID to filter by.
    :param enabled_only: If True, only return enabled rules.
    :return: List of tag rules ordered by priority (ascending).
    """
    query = session.query(TagRule).filter(TagRule.user_id == user_id)

    if tag_id is not None:
        query = query.filter(TagRule.tag_id == tag_id)

    if enabled_only:
        query = query.filter(TagRule.enabled == True)  # noqa: E712

    return query.order_by(TagRule.priority).all()


def create_tag_rule(
    session: Session,
    user_id: UUID,
    name: str,
    tag_id: UUID,
    conditions: RuleConditions | None = None,
    account_id: UUID | None = None,
    enabled: bool = True,
) -> TagRule:
    """Create a new tag rule.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param name: Rule name (max 100 chars).
    :param tag_id: Target tag's UUID.
    :param conditions: Rule matching conditions (stored as JSONB).
    :param account_id: Optional account filter (kept as FK for integrity).
    :param enabled: Whether the rule is active.
    :return: Created TagRule entity.
    """
    # Get the next priority (append to end)
    max_priority = (
        session.query(func.max(TagRule.priority)).filter(TagRule.user_id == user_id).scalar()
    )
    priority = (max_priority or 0) + 1

    # Filter out None values from conditions
    clean_conditions = {k: v for k, v in (conditions or {}).items() if v is not None}

    rule = TagRule(
        user_id=user_id,
        name=name.strip()[:100],
        tag_id=tag_id,
        priority=priority,
        enabled=enabled,
        conditions=clean_conditions,
        account_id=account_id,
    )
    session.add(rule)
    session.flush()
    logger.info(f"Created tag rule: id={rule.id}, user_id={user_id}, name={name}")
    return rule


# Sentinel for "not provided" in update operations
_NOT_PROVIDED: object = object()


def update_tag_rule(
    session: Session,
    rule_id: UUID,
    name: str | None = None,
    tag_id: UUID | None = None,
    enabled: bool | None = None,
    conditions: RuleConditions | None = None,
    account_id: UUID | None | object = _NOT_PROVIDED,
) -> TagRule | None:
    """Update a tag rule.

    :param session: SQLAlchemy session.
    :param rule_id: Rule's UUID.
    :param name: New name (optional).
    :param tag_id: New target tag (optional).
    :param enabled: New enabled state (optional).
    :param conditions: New conditions dict. Keys present will be merged, None values remove keys.
    :param account_id: New account filter. Pass None to clear, omit to leave unchanged.
    :return: Updated TagRule, or None if not found.
    """
    rule = get_tag_rule_by_id(session, rule_id)
    if rule is None:
        return None

    if name is not None:
        rule.name = name.strip()[:100]
    if tag_id is not None:
        rule.tag_id = tag_id
    if enabled is not None:
        rule.enabled = enabled

    # Update account_id if explicitly provided (including None to clear)
    if account_id is not _NOT_PROVIDED:
        rule.account_id = account_id  # type: ignore[assignment]

    # Merge conditions if provided
    if conditions is not None:
        updated_conditions = dict(rule.conditions)  # Copy existing
        for key, value in conditions.items():
            if value is None:
                updated_conditions.pop(key, None)  # Remove key if value is None
            else:
                updated_conditions[key] = value
        rule.conditions = updated_conditions

    session.flush()
    logger.info(f"Updated tag rule: id={rule_id}")
    return rule


def delete_tag_rule(session: Session, rule_id: UUID) -> bool:
    """Delete a tag rule.

    :param session: SQLAlchemy session.
    :param rule_id: Rule's UUID.
    :return: True if deleted, False if not found.
    """
    rule = get_tag_rule_by_id(session, rule_id)
    if rule is None:
        return False

    session.delete(rule)
    session.flush()
    logger.info(f"Deleted tag rule: id={rule_id}")
    return True


def reorder_tag_rules(session: Session, user_id: UUID, rule_ids: list[UUID]) -> list[TagRule]:
    """Reorder tag rules by setting priorities based on the given order.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param rule_ids: List of rule IDs in desired order.
    :return: Updated list of rules in new order.
    """
    rules = get_tag_rules_by_user_id(session, user_id)
    rule_map = {rule.id: rule for rule in rules}

    # Update priorities based on position in the list
    for i, rule_id in enumerate(rule_ids):
        if rule_id in rule_map:
            rule_map[rule_id].priority = i

    session.flush()
    logger.info(f"Reordered tag rules: user_id={user_id}, count={len(rule_ids)}")
    return get_tag_rules_by_user_id(session, user_id)


def transaction_matches_rule(transaction: Transaction, rule: TagRule) -> bool:
    """Check if a transaction matches all conditions of a rule.

    All include conditions must match (AND logic).
    None of the exclude conditions must match.

    :param transaction: Transaction to check.
    :param rule: Rule to evaluate against.
    :return: True if transaction matches all conditions.
    """
    # Get the text to match against (use counterparty_name as merchant)
    merchant = (transaction.counterparty_name or "").lower()
    description = (transaction.description or "").lower()
    amount = abs(transaction.amount)

    # Extract conditions from JSONB
    cond = rule.conditions or {}
    merchant_contains = cond.get("merchant_contains")
    merchant_exact = cond.get("merchant_exact")
    description_contains = cond.get("description_contains")
    min_amount = cond.get("min_amount")
    max_amount = cond.get("max_amount")
    merchant_not_contains = cond.get("merchant_not_contains")
    description_not_contains = cond.get("description_not_contains")

    # Check include conditions (all must match)
    include_checks = [
        not merchant_contains or merchant_contains.lower() in merchant,
        not merchant_exact or transaction.counterparty_name == merchant_exact,
        not description_contains or description_contains.lower() in description,
        min_amount is None or amount >= Decimal(str(min_amount)),
        max_amount is None or amount <= Decimal(str(max_amount)),
        rule.account_id is None or transaction.account_id == rule.account_id,
    ]

    # Check exclude conditions (none must match)
    exclude_checks = [
        not merchant_not_contains or merchant_not_contains.lower() not in merchant,
        not description_not_contains or description_not_contains.lower() not in description,
    ]

    return all(include_checks) and all(exclude_checks)


def transaction_matches_conditions(
    transaction: Transaction,
    conditions: RuleConditions,
    account_id: UUID | None = None,
) -> bool:
    """Check if a transaction matches conditions (without needing a saved rule).

    Used for testing conditions before saving a rule.

    :param transaction: Transaction to check.
    :param conditions: Conditions dict to evaluate.
    :param account_id: Optional account filter.
    :return: True if transaction matches all conditions.
    """
    # Get the text to match against
    merchant = (transaction.counterparty_name or "").lower()
    description = (transaction.description or "").lower()
    amount = abs(transaction.amount)

    # Extract conditions
    merchant_contains = conditions.get("merchant_contains")
    merchant_exact = conditions.get("merchant_exact")
    description_contains = conditions.get("description_contains")
    min_amount = conditions.get("min_amount")
    max_amount = conditions.get("max_amount")
    merchant_not_contains = conditions.get("merchant_not_contains")
    description_not_contains = conditions.get("description_not_contains")

    # Check include conditions (all must match)
    include_checks = [
        not merchant_contains or merchant_contains.lower() in merchant,
        not merchant_exact or transaction.counterparty_name == merchant_exact,
        not description_contains or description_contains.lower() in description,
        min_amount is None or amount >= Decimal(str(min_amount)),
        max_amount is None or amount <= Decimal(str(max_amount)),
        account_id is None or transaction.account_id == account_id,
    ]

    # Check exclude conditions (none must match)
    exclude_checks = [
        not merchant_not_contains or merchant_not_contains.lower() not in merchant,
        not description_not_contains or description_not_contains.lower() not in description,
    ]

    return all(include_checks) and all(exclude_checks)


def test_conditions_against_transactions(
    session: Session,
    user_id: UUID,
    conditions: RuleConditions,
    account_id: UUID | None = None,
    filter_account_ids: list[UUID] | None = None,
    limit: int = 100,
) -> list[Transaction]:
    """Test conditions against transactions without a saved rule.

    Useful for previewing what conditions would match before saving a rule.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID (to find their transactions).
    :param conditions: Conditions dict to test.
    :param account_id: Account ID filter from rule (if any).
    :param filter_account_ids: Additional account IDs to limit search.
    :param limit: Maximum number of matches to return.
    :return: List of matching transactions.
    """
    # Get transactions from user's accounts
    query = (
        session.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .join(Connection, Account.connection_id == Connection.id)
        .filter(Connection.user_id == user_id)
    )

    # Apply account filters
    if filter_account_ids:
        query = query.filter(Transaction.account_id.in_(filter_account_ids))
    if account_id:
        query = query.filter(Transaction.account_id == account_id)

    # Order by most recent first
    query = query.order_by(Transaction.booking_date.desc())

    # Test each transaction against the conditions
    matches = []
    for transaction in query.yield_per(100):
        if transaction_matches_conditions(transaction, conditions, account_id):
            matches.append(transaction)
            if len(matches) >= limit:
                break

    return matches


def test_rule_against_transactions(
    session: Session,
    rule: TagRule,
    account_ids: list[UUID] | None = None,
    limit: int = 100,
) -> list[Transaction]:
    """Test a rule against existing transactions and return matches.

    Useful for previewing what a rule would match before enabling it.

    :param session: SQLAlchemy session.
    :param rule: Rule to test.
    :param account_ids: Optional list of account IDs to limit search.
    :param limit: Maximum number of matches to return.
    :return: List of matching transactions.
    """
    # Get transactions from user's accounts
    query = (
        session.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .join(Connection, Account.connection_id == Connection.id)
        .filter(Connection.user_id == rule.user_id)
    )

    if account_ids:
        query = query.filter(Transaction.account_id.in_(account_ids))

    # Order by most recent first
    query = query.order_by(Transaction.booking_date.desc())

    # Test each transaction against the rule
    matches = []
    for transaction in query.yield_per(100):
        if transaction_matches_rule(transaction, rule):
            matches.append(transaction)
            if len(matches) >= limit:
                break

    return matches


def apply_rule_to_transaction(
    session: Session,
    transaction: Transaction,
    rule: TagRule,
) -> bool:
    """Apply a rule's tag to a transaction (creates a 100% split).

    Only applies if the transaction doesn't already have any splits.
    If splits exist, the rule is not applied (user has already tagged/split).

    :param session: SQLAlchemy session.
    :param transaction: Transaction to tag.
    :param rule: Rule that matched.
    :return: True if tag was applied, False if already tagged.
    """
    # Check if transaction already has any splits (user already tagged it)
    existing = (
        session.query(TransactionSplit)
        .filter(TransactionSplit.transaction_id == transaction.id)
        .first()
    )

    if existing:
        return False

    # Create a 100% split with auto-tag metadata
    split = TransactionSplit(
        transaction_id=transaction.id,
        tag_id=rule.tag_id,
        amount=abs(transaction.amount),
        is_auto=True,
        rule_id=rule.id,
    )
    session.add(split)
    session.flush()

    logger.debug(
        f"Auto-tagged transaction: transaction_id={transaction.id}, "
        f"rule_id={rule.id}, tag_id={rule.tag_id}"
    )
    return True


def apply_rules_to_transaction(
    session: Session,
    transaction: Transaction,
    rules: list[TagRule],
) -> TagRule | None:
    """Apply all matching rules to a transaction.

    Rules are evaluated in priority order. The first matching rule's tag is applied.

    :param session: SQLAlchemy session.
    :param transaction: Transaction to process.
    :param rules: List of rules (should be sorted by priority).
    :return: The rule that was applied, or None if no match.
    """
    for rule in rules:
        if not rule.enabled:
            continue

        if transaction_matches_rule(transaction, rule):
            if apply_rule_to_transaction(session, transaction, rule):
                return rule
            # If tag already exists, continue to next rule
            # (but still return that a rule matched)
            return rule

    return None


def bulk_apply_rules(
    session: Session,
    user_id: UUID,
    account_ids: list[UUID] | None = None,
    untagged_only: bool = True,
) -> int:
    """Apply all enabled rules to transactions.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param account_ids: Optional list of account IDs to process.
    :param untagged_only: If True, only process transactions with no tags.
    :return: Number of transactions that were tagged.
    """
    rules = get_tag_rules_by_user_id(session, user_id, enabled_only=True)
    if not rules:
        return 0

    # Get transactions from user's accounts
    query = (
        session.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .join(Connection, Account.connection_id == Connection.id)
        .filter(Connection.user_id == user_id)
    )

    if account_ids:
        query = query.filter(Transaction.account_id.in_(account_ids))

    if untagged_only:
        # Subquery to find transactions with any splits (= tagged)
        tagged_subq = session.query(TransactionSplit.transaction_id).distinct().subquery()
        query = query.filter(~Transaction.id.in_(session.query(tagged_subq)))

    tagged_count = 0
    for transaction in query.yield_per(100):
        if apply_rules_to_transaction(session, transaction, rules):
            tagged_count += 1

    session.flush()
    logger.info(f"Bulk applied rules: user_id={user_id}, tagged_count={tagged_count}")
    return tagged_count
