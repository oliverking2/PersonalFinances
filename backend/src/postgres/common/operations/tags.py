"""Tag database operations.

This module provides CRUD operations for Tag entities and transaction tagging.
"""

import logging
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.postgres.common.models import Tag, Transaction, TransactionSplit

logger = logging.getLogger(__name__)

# Soft limits
MAX_TAGS_PER_USER = 100
MAX_TAGS_PER_TRANSACTION = 10

# Standard tags seeded for new users
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
    {"name": "Transfers", "colour": "#6b7280"},
    {"name": "Fees", "colour": "#f59e0b"},
]


class StandardTagDeletionError(Exception):
    """Raised when attempting to delete a standard tag."""

    pass


def get_tag_by_id(session: Session, tag_id: UUID) -> Tag | None:
    """Get a tag by its ID.

    :param session: SQLAlchemy session.
    :param tag_id: Tag's UUID.
    :return: Tag if found, None otherwise.
    """
    return session.get(Tag, tag_id)


def get_tags_by_user_id(session: Session, user_id: UUID) -> list[Tag]:
    """Get all tags for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: List of tags ordered by name.
    """
    return session.query(Tag).filter(Tag.user_id == user_id).order_by(Tag.name).all()


def get_tag_by_name(session: Session, user_id: UUID, name: str) -> Tag | None:
    """Get a tag by user and name.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param name: Tag name (case-sensitive).
    :return: Tag if found, None otherwise.
    """
    return session.query(Tag).filter(Tag.user_id == user_id, Tag.name == name).first()


def get_visible_tags_by_user_id(session: Session, user_id: UUID) -> list[Tag]:
    """Get all non-hidden tags for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: List of visible tags ordered by name.
    """
    return (
        session.query(Tag)
        .filter(Tag.user_id == user_id, Tag.is_hidden == False)  # noqa: E712
        .order_by(Tag.name)
        .all()
    )


def seed_standard_tags(session: Session, user_id: UUID) -> list[Tag]:
    """Create standard tags for a user.

    Should be called once when a new user is created.
    Skips any tags that already exist (idempotent).

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: List of created or existing standard tags.
    """
    tags = []
    for tag_def in STANDARD_TAGS:
        existing = get_tag_by_name(session, user_id, tag_def["name"])
        if existing:
            tags.append(existing)
            continue

        tag = Tag(
            user_id=user_id,
            name=tag_def["name"],
            colour=tag_def["colour"],
            is_standard=True,
            is_hidden=False,
        )
        session.add(tag)
        tags.append(tag)

    session.flush()
    logger.info(f"Seeded standard tags: user_id={user_id}, count={len(STANDARD_TAGS)}")
    return tags


def count_tags_by_user_id(session: Session, user_id: UUID) -> int:
    """Count tags for a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Number of tags.
    """
    return session.query(func.count(Tag.id)).filter(Tag.user_id == user_id).scalar() or 0


def create_tag(
    session: Session,
    user_id: UUID,
    name: str,
    colour: str | None = None,
) -> Tag:
    """Create a new tag.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :param name: Tag name (max 50 chars).
    :param colour: Hex colour code (optional, e.g., "#10B981").
    :return: Created Tag entity.
    """
    tag = Tag(
        user_id=user_id,
        name=name.strip()[:50],
        colour=colour,
    )
    session.add(tag)
    session.flush()
    logger.info(f"Created tag: id={tag.id}, user_id={user_id}, name={name}")
    return tag


_NOT_SET = object()


def update_tag(
    session: Session,
    tag_id: UUID,
    name: str | None = None,
    colour: str | None | object = _NOT_SET,
) -> Tag | None:
    """Update a tag's name and/or colour.

    :param session: SQLAlchemy session.
    :param tag_id: Tag's UUID.
    :param name: New name (optional).
    :param colour: New colour (optional, pass None to clear).
    :return: Updated Tag, or None if not found.
    """
    tag = get_tag_by_id(session, tag_id)
    if tag is None:
        return None

    if name is not None:
        tag.name = name.strip()[:50]
    if colour is not _NOT_SET:
        tag.colour = colour  # type: ignore[assignment]

    session.flush()
    logger.info(f"Updated tag: id={tag_id}")
    return tag


def delete_tag(session: Session, tag_id: UUID) -> bool:
    """Delete a tag.

    This also removes the tag from all transactions (via CASCADE).
    Standard tags cannot be deleted (use hide_tag instead).

    :param session: SQLAlchemy session.
    :param tag_id: Tag's UUID.
    :return: True if deleted, False if not found.
    :raises StandardTagDeletionError: If the tag is a standard tag.
    """
    tag = get_tag_by_id(session, tag_id)
    if tag is None:
        return False

    if tag.is_standard:
        raise StandardTagDeletionError(f"Cannot delete standard tag: {tag.name}")

    session.delete(tag)
    session.flush()
    logger.info(f"Deleted tag: id={tag_id}")
    return True


def hide_tag(session: Session, tag_id: UUID) -> Tag | None:
    """Hide a tag from the user interface.

    Hidden tags are not shown in selectors but remain on transactions.
    Typically used for standard tags the user doesn't need.

    :param session: SQLAlchemy session.
    :param tag_id: Tag's UUID.
    :return: Updated Tag, or None if not found.
    """
    tag = get_tag_by_id(session, tag_id)
    if tag is None:
        return None

    tag.is_hidden = True
    session.flush()
    logger.info(f"Hid tag: id={tag_id}")
    return tag


def unhide_tag(session: Session, tag_id: UUID) -> Tag | None:
    """Unhide a previously hidden tag.

    :param session: SQLAlchemy session.
    :param tag_id: Tag's UUID.
    :return: Updated Tag, or None if not found.
    """
    tag = get_tag_by_id(session, tag_id)
    if tag is None:
        return None

    tag.is_hidden = False
    session.flush()
    logger.info(f"Unhid tag: id={tag_id}")
    return tag


# Transaction tagging operations (via splits - unified model)


def get_transaction_tags(session: Session, transaction_id: UUID) -> list[Tag]:
    """Get all tags for a transaction (derived from splits).

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :return: List of unique tags from splits.
    """
    splits = (
        session.query(TransactionSplit)
        .filter(TransactionSplit.transaction_id == transaction_id)
        .all()
    )
    # Get unique tags
    tag_ids = {split.tag_id for split in splits}
    if not tag_ids:
        return []
    return session.query(Tag).filter(Tag.id.in_(tag_ids)).all()


def add_tag_to_transaction(
    session: Session,
    transaction_id: UUID,
    tag_id: UUID,
    is_auto: bool = False,
    rule_id: UUID | None = None,
) -> TransactionSplit | None:
    """Add a tag to a transaction (creates a 100% split).

    If the transaction already has splits, this replaces them with a single
    100% split to the new tag. Use set_transaction_splits for multi-tag splits.

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :param tag_id: Tag UUID to add.
    :param is_auto: Whether this was auto-tagged by a rule.
    :param rule_id: The rule that applied this tag (if auto).
    :return: Created split, or None if transaction not found.
    """
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        return None

    # Check if this tag already exists as a split
    existing = (
        session.query(TransactionSplit)
        .filter(
            TransactionSplit.transaction_id == transaction_id,
            TransactionSplit.tag_id == tag_id,
        )
        .first()
    )
    if existing:
        return existing

    # Clear existing splits (single tag = replaces all)
    session.query(TransactionSplit).filter(
        TransactionSplit.transaction_id == transaction_id
    ).delete()

    # Create new 100% split
    split = TransactionSplit(
        transaction_id=transaction_id,
        tag_id=tag_id,
        amount=abs(transaction.amount),
        is_auto=is_auto,
        rule_id=rule_id,
    )
    session.add(split)
    session.flush()

    logger.info(
        f"Added tag to transaction: transaction_id={transaction_id}, "
        f"tag_id={tag_id}, is_auto={is_auto}"
    )
    return split


def add_tags_to_transaction(
    session: Session,
    transaction_id: UUID,
    tag_ids: list[UUID],
) -> list[Tag]:
    """Add tags to a transaction (single tag only in unified model).

    For simplicity, only the first tag is used (creates a 100% split).
    Use set_transaction_splits for multiple tags with amounts.

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :param tag_ids: List of tag UUIDs (only first is used).
    :return: Updated list of all tags on the transaction.
    """
    if not tag_ids:
        return get_transaction_tags(session, transaction_id)

    # Add only the first tag (unified model = single tag default)
    add_tag_to_transaction(session, transaction_id, tag_ids[0])
    return get_transaction_tags(session, transaction_id)


def remove_tag_from_transaction(
    session: Session,
    transaction_id: UUID,
    tag_id: UUID,
) -> list[Tag]:
    """Remove a tag from a transaction (removes the split).

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :param tag_id: Tag's UUID to remove.
    :return: Updated list of remaining tags on the transaction.
    """
    # Delete split for this tag
    deleted = (
        session.query(TransactionSplit)
        .filter(
            TransactionSplit.transaction_id == transaction_id,
            TransactionSplit.tag_id == tag_id,
        )
        .delete()
    )

    if deleted:
        session.flush()
        logger.info(
            f"Removed tag from transaction: transaction_id={transaction_id}, tag_id={tag_id}"
        )

    return get_transaction_tags(session, transaction_id)


def bulk_tag_transactions(
    session: Session,
    transaction_ids: list[UUID],
    add_tag_ids: list[UUID] | None = None,
    remove_tag_ids: list[UUID] | None = None,
) -> int:
    """Bulk add/remove tags from multiple transactions (via splits).

    In the unified model, adding a tag replaces existing splits with a 100% split.
    Use this for simple single-tag operations only.

    :param session: SQLAlchemy session.
    :param transaction_ids: List of transaction UUIDs.
    :param add_tag_ids: Tags to add (only first is used per transaction).
    :param remove_tag_ids: Tags to remove.
    :return: Number of transactions updated.
    """
    add_tag_ids = add_tag_ids or []
    remove_tag_ids = remove_tag_ids or []

    transactions = session.query(Transaction).filter(Transaction.id.in_(transaction_ids)).all()

    if not transactions:
        return 0

    updated_count = 0
    for transaction in transactions:
        changed = False

        # Remove splits for specified tags
        if remove_tag_ids:
            deleted = (
                session.query(TransactionSplit)
                .filter(
                    TransactionSplit.transaction_id == transaction.id,
                    TransactionSplit.tag_id.in_(remove_tag_ids),
                )
                .delete(synchronize_session="fetch")
            )
            if deleted:
                changed = True

        # Add tag (first one only, replaces all existing)
        if add_tag_ids:
            tag_id = add_tag_ids[0]
            # Check if already exists
            existing = (
                session.query(TransactionSplit)
                .filter(
                    TransactionSplit.transaction_id == transaction.id,
                    TransactionSplit.tag_id == tag_id,
                )
                .first()
            )
            if not existing:
                # Clear other splits and add this one
                session.query(TransactionSplit).filter(
                    TransactionSplit.transaction_id == transaction.id
                ).delete(synchronize_session="fetch")
                split = TransactionSplit(
                    transaction_id=transaction.id,
                    tag_id=tag_id,
                    amount=abs(transaction.amount),
                    is_auto=False,
                )
                session.add(split)
                changed = True

        if changed:
            updated_count += 1

    session.flush()
    logger.info(
        f"Bulk tagged transactions: count={updated_count}, "
        f"add_tags={len(add_tag_ids)}, remove_tags={len(remove_tag_ids)}"
    )
    return updated_count


def get_tag_usage_counts(session: Session, user_id: UUID) -> dict[UUID, int]:
    """Get usage counts for all tags of a user (from splits).

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Dict mapping tag ID to usage count.
    """
    results = (
        session.query(Tag.id, func.count(TransactionSplit.transaction_id))
        .outerjoin(TransactionSplit, Tag.id == TransactionSplit.tag_id)
        .filter(Tag.user_id == user_id)
        .group_by(Tag.id)
        .all()
    )
    return {tag_id: count for tag_id, count in results}
