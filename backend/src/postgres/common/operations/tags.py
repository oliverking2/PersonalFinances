"""Tag database operations.

This module provides CRUD operations for Tag entities and transaction tagging.
"""

import logging
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.postgres.common.models import Tag, Transaction, TransactionTag

logger = logging.getLogger(__name__)

# Soft limits
MAX_TAGS_PER_USER = 100
MAX_TAGS_PER_TRANSACTION = 10


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

    :param session: SQLAlchemy session.
    :param tag_id: Tag's UUID.
    :return: True if deleted, False if not found.
    """
    tag = get_tag_by_id(session, tag_id)
    if tag is None:
        return False

    session.delete(tag)
    session.flush()
    logger.info(f"Deleted tag: id={tag_id}")
    return True


# Transaction tagging operations


def get_transaction_tags(session: Session, transaction_id: UUID) -> list[Tag]:
    """Get all tags for a transaction.

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :return: List of tags.
    """
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        return []
    return list(transaction.tags)


def add_tags_to_transaction(
    session: Session,
    transaction_id: UUID,
    tag_ids: list[UUID],
) -> list[Tag]:
    """Add tags to a transaction.

    Existing tags are preserved. Duplicate tags are ignored.

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :param tag_ids: List of tag UUIDs to add.
    :return: Updated list of all tags on the transaction.
    """
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        return []

    existing_tag_ids = {tag.id for tag in transaction.tags}
    tags_to_add = (
        session.query(Tag).filter(Tag.id.in_(tag_ids), ~Tag.id.in_(existing_tag_ids)).all()
    )

    # Respect the limit
    available_slots = MAX_TAGS_PER_TRANSACTION - len(existing_tag_ids)
    tags_to_add = tags_to_add[:available_slots]

    for tag in tags_to_add:
        transaction.tags.append(tag)

    session.flush()
    if tags_to_add:
        logger.info(
            f"Added tags to transaction: transaction_id={transaction_id}, "
            f"tag_ids={[str(t.id) for t in tags_to_add]}"
        )
    return list(transaction.tags)


def remove_tag_from_transaction(
    session: Session,
    transaction_id: UUID,
    tag_id: UUID,
) -> list[Tag]:
    """Remove a tag from a transaction.

    :param session: SQLAlchemy session.
    :param transaction_id: Transaction's UUID.
    :param tag_id: Tag's UUID to remove.
    :return: Updated list of remaining tags on the transaction.
    """
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        return []

    tag = session.get(Tag, tag_id)
    if tag and tag in transaction.tags:
        transaction.tags.remove(tag)
        session.flush()
        logger.info(
            f"Removed tag from transaction: transaction_id={transaction_id}, tag_id={tag_id}"
        )

    return list(transaction.tags)


def bulk_tag_transactions(
    session: Session,
    transaction_ids: list[UUID],
    add_tag_ids: list[UUID] | None = None,
    remove_tag_ids: list[UUID] | None = None,
) -> int:
    """Bulk add/remove tags from multiple transactions.

    :param session: SQLAlchemy session.
    :param transaction_ids: List of transaction UUIDs.
    :param add_tag_ids: Tags to add (optional).
    :param remove_tag_ids: Tags to remove (optional).
    :return: Number of transactions updated.
    """
    add_tag_ids = add_tag_ids or []
    remove_tag_ids = remove_tag_ids or []

    transactions = session.query(Transaction).filter(Transaction.id.in_(transaction_ids)).all()

    if not transactions:
        return 0

    tags_to_add = session.query(Tag).filter(Tag.id.in_(add_tag_ids)).all() if add_tag_ids else []
    tags_to_remove = (
        session.query(Tag).filter(Tag.id.in_(remove_tag_ids)).all() if remove_tag_ids else []
    )

    updated_count = 0
    for transaction in transactions:
        changed = False

        # Remove tags first
        for tag in tags_to_remove:
            if tag in transaction.tags:
                transaction.tags.remove(tag)
                changed = True

        # Then add tags (respecting limit)
        current_count = len(transaction.tags)
        for tag in tags_to_add:
            if tag not in transaction.tags and current_count < MAX_TAGS_PER_TRANSACTION:
                transaction.tags.append(tag)
                current_count += 1
                changed = True

        if changed:
            updated_count += 1

    session.flush()
    logger.info(
        f"Bulk tagged transactions: count={updated_count}, "
        f"add_tags={len(tags_to_add)}, remove_tags={len(tags_to_remove)}"
    )
    return updated_count


def get_tag_usage_counts(session: Session, user_id: UUID) -> dict[UUID, int]:
    """Get usage counts for all tags of a user.

    :param session: SQLAlchemy session.
    :param user_id: User's UUID.
    :return: Dict mapping tag ID to usage count.
    """
    results = (
        session.query(Tag.id, func.count(TransactionTag.transaction_id))
        .outerjoin(TransactionTag, Tag.id == TransactionTag.tag_id)
        .filter(Tag.user_id == user_id)
        .group_by(Tag.id)
        .all()
    )
    return {tag_id: count for tag_id, count in results}
