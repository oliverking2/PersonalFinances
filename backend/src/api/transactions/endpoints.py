"""Transaction API endpoints."""

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.common.helpers import get_user_account_ids
from src.api.dependencies import get_current_user, get_db
from src.api.responses import RESOURCE_RESPONSES, RESOURCE_WRITE_RESPONSES, UNAUTHORIZED
from src.api.transactions.models import (
    BulkTagRequest,
    BulkTagResponse,
    SetSplitsRequest,
    TransactionListResponse,
    TransactionQueryParams,
    TransactionResponse,
    TransactionSplitResponse,
    TransactionSplitsResponse,
    TransactionTagResponse,
    TransactionTagsRequest,
    TransactionTagsResponse,
    UpdateNoteRequest,
)
from src.postgres.auth.models import User
from src.postgres.common.models import Transaction
from src.postgres.common.operations.connections import get_connections_by_user_id
from src.postgres.common.operations.splits import (
    SplitValidationError,
    clear_transaction_splits,
    get_splits_with_tags,
    set_transaction_splits,
)
from src.postgres.common.operations.tags import (
    add_tags_to_transaction,
    bulk_tag_transactions,
    get_tag_by_id,
    remove_tag_from_transaction,
)
from src.postgres.common.operations.transactions import get_transactions_for_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=TransactionListResponse,
    summary="List transactions",
    responses=UNAUTHORIZED,
)
def list_transactions(
    params: TransactionQueryParams = Depends(),
    account_ids: list[UUID] = Query(default=[]),
    tag_ids: list[UUID] = Query(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionListResponse:
    """List transactions with optional filters.

    Supports filtering by accounts, tags, date range, amount range, and search term.
    """
    # Get all account IDs for this user
    connections = get_connections_by_user_id(db, current_user.id)
    user_account_ids = {acc.id for conn in connections for acc in conn.accounts}

    # If filtering by specific accounts, verify user owns them
    if account_ids:
        # Filter to only accounts the user owns
        valid_account_ids = [aid for aid in account_ids if aid in user_account_ids]
        if not valid_account_ids:
            # Return empty result if no valid accounts
            return TransactionListResponse(
                transactions=[],
                total=0,
                page=params.page,
                page_size=params.page_size,
            )
        query_account_ids = valid_account_ids
    else:
        # No filter - use all user accounts
        query_account_ids = list(user_account_ids)

    # Verify tag ownership if filtering by tags
    valid_tag_ids: list[UUID] = []
    if tag_ids:
        for tag_id in tag_ids:
            tag = get_tag_by_id(db, tag_id)
            if not tag or tag.user_id != current_user.id:
                # Skip tags user doesn't own (silently ignore invalid tags)
                continue
            valid_tag_ids.append(tag_id)

        # If all tags were invalid, return empty
        if not valid_tag_ids:
            return TransactionListResponse(
                transactions=[],
                total=0,
                page=params.page,
                page_size=params.page_size,
            )

    # Query transactions
    result = get_transactions_for_user(
        db,
        account_ids=query_account_ids,
        tag_ids=valid_tag_ids if valid_tag_ids else None,
        start_date=params.start_date,
        end_date=params.end_date,
        min_amount=params.min_amount,
        max_amount=params.max_amount,
        search=params.search,
        page=params.page,
        page_size=params.page_size,
    )

    return TransactionListResponse(
        transactions=[_to_response(txn, db) for txn in result.transactions],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


def _to_response(txn: Transaction, db: Session | None = None) -> TransactionResponse:
    """Convert a Transaction model to API response.

    In the unified model, all tagging is done via splits. The `tags` field is
    populated from splits for backwards compatibility with the frontend.

    :param txn: Transaction model.
    :param db: Optional session (unused in unified model, kept for compatibility).
    """
    # Build tag responses from splits (unified model: tags = splits)
    tag_responses = []
    split_responses = []

    for split in txn.splits:
        # Get rule name if auto-tagged
        rule_name = split.rule.name if split.rule else None

        # Add to tags list (for backwards compatibility)
        tag_responses.append(
            TransactionTagResponse(
                id=str(split.tag_id),
                name=split.tag.name,
                colour=split.tag.colour,
                is_auto=split.is_auto,
                rule_id=str(split.rule_id) if split.rule_id else None,
                rule_name=rule_name,
            )
        )

        # Add to splits list (with full split info)
        split_responses.append(
            TransactionSplitResponse(
                id=str(split.id),
                tag_id=str(split.tag_id),
                tag_name=split.tag.name,
                tag_colour=split.tag.colour,
                amount=float(split.amount),
                is_auto=split.is_auto,
                rule_id=str(split.rule_id) if split.rule_id else None,
                rule_name=rule_name,
            )
        )

    # Get recurring pattern info if linked
    recurring_pattern_id = None
    recurring_frequency = None
    recurring_status = None
    if txn.pattern_links:
        # Use the first linked pattern (typically there's only one)
        link = txn.pattern_links[0]
        pattern = link.pattern
        recurring_pattern_id = str(pattern.id)
        recurring_frequency = pattern.frequency
        recurring_status = pattern.status

    return TransactionResponse(
        id=str(txn.id),
        account_id=str(txn.account_id),
        booking_date=txn.booking_date.date() if txn.booking_date else None,
        value_date=txn.value_date.date() if txn.value_date else None,
        amount=float(txn.amount),
        currency=txn.currency,
        description=txn.description,
        merchant_name=txn.counterparty_name,
        category=txn.category,
        user_note=txn.user_note,
        tags=tag_responses,
        splits=split_responses,
        recurring_pattern_id=recurring_pattern_id,
        recurring_frequency=recurring_frequency,
        recurring_status=recurring_status,
    )


def _verify_transaction_ownership(
    db: Session, transaction_id: UUID, user: User
) -> Transaction | None:
    """Verify user owns the transaction and return it if so."""
    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        return None

    # Verify through account ownership
    account_ids = get_user_account_ids(db, user)
    if transaction.account_id not in account_ids:
        return None

    return transaction


@router.post(
    "/{transaction_id}/tags",
    response_model=TransactionTagsResponse,
    summary="Add tags to transaction",
    responses=RESOURCE_WRITE_RESPONSES,
)
def add_transaction_tags(
    transaction_id: UUID,
    request: TransactionTagsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionTagsResponse:
    """Add one or more tags to a transaction."""
    transaction = _verify_transaction_ownership(db, transaction_id, current_user)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")

    # Verify all tags belong to user
    tag_ids = [UUID(tid) for tid in request.tag_ids]
    for tag_id in tag_ids:
        tag = get_tag_by_id(db, tag_id)
        if not tag or tag.user_id != current_user.id:
            raise HTTPException(status_code=400, detail=f"Invalid tag: {tag_id}")

    tags = add_tags_to_transaction(db, transaction_id, tag_ids)
    db.commit()

    return TransactionTagsResponse(
        transaction_id=str(transaction_id),
        tags=[
            TransactionTagResponse(
                id=str(t.id),
                name=t.name,
                colour=t.colour,
                is_auto=False,  # Manually added tags are not auto
                rule_id=None,
                rule_name=None,
            )
            for t in tags
        ],
    )


@router.delete(
    "/{transaction_id}/tags/{tag_id}",
    response_model=TransactionTagsResponse,
    summary="Remove tag from transaction",
    responses=RESOURCE_RESPONSES,
)
def remove_transaction_tag(
    transaction_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionTagsResponse:
    """Remove a tag from a transaction."""
    transaction = _verify_transaction_ownership(db, transaction_id, current_user)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")

    tags = remove_tag_from_transaction(db, transaction_id, tag_id)
    db.commit()

    return TransactionTagsResponse(
        transaction_id=str(transaction_id),
        tags=[
            TransactionTagResponse(
                id=str(t.id),
                name=t.name,
                colour=t.colour,
                is_auto=False,
                rule_id=None,
                rule_name=None,
            )
            for t in tags
        ],
    )


@router.post(
    "/bulk/tags",
    response_model=BulkTagResponse,
    summary="Bulk tag transactions",
    responses=RESOURCE_WRITE_RESPONSES,
)
def bulk_tag(
    request: BulkTagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkTagResponse:
    """Add or remove tags from multiple transactions in a single operation."""
    account_ids = get_user_account_ids(db, current_user)

    # Verify all transactions belong to user
    transaction_ids = [UUID(tid) for tid in request.transaction_ids]
    for tid in transaction_ids:
        transaction = db.get(Transaction, tid)
        if not transaction or transaction.account_id not in account_ids:
            raise HTTPException(status_code=400, detail=f"Invalid transaction: {tid}")

    # Verify all tags belong to user
    add_tag_ids = [UUID(tid) for tid in request.add_tag_ids] if request.add_tag_ids else []
    remove_tag_ids = [UUID(tid) for tid in request.remove_tag_ids] if request.remove_tag_ids else []

    for tag_id in add_tag_ids + remove_tag_ids:
        tag = get_tag_by_id(db, tag_id)
        if not tag or tag.user_id != current_user.id:
            raise HTTPException(status_code=400, detail=f"Invalid tag: {tag_id}")

    updated_count = bulk_tag_transactions(db, transaction_ids, add_tag_ids, remove_tag_ids)
    db.commit()

    return BulkTagResponse(updated_count=updated_count)


# -----------------------------------------------------------------------------
# Split Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/{transaction_id}/splits",
    response_model=TransactionSplitsResponse,
    summary="Get transaction splits",
    responses=RESOURCE_RESPONSES,
)
def get_transaction_splits_endpoint(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionSplitsResponse:
    """Get all splits for a transaction."""
    transaction = _verify_transaction_ownership(db, transaction_id, current_user)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")

    splits_with_tags = get_splits_with_tags(db, transaction_id)

    return TransactionSplitsResponse(
        transaction_id=str(transaction_id),
        splits=[
            TransactionSplitResponse(
                id=str(split.id),
                tag_id=str(split.tag_id),
                tag_name=tag.name,
                tag_colour=tag.colour,
                amount=float(split.amount),
                is_auto=split.is_auto,
                rule_id=str(split.rule_id) if split.rule_id else None,
                rule_name=split.rule.name if split.rule else None,
            )
            for split, tag in splits_with_tags
        ],
    )


@router.put(
    "/{transaction_id}/splits",
    response_model=TransactionSplitsResponse,
    summary="Set transaction splits",
    responses=RESOURCE_WRITE_RESPONSES,
)
def set_transaction_splits_endpoint(
    transaction_id: UUID,
    request: SetSplitsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionSplitsResponse:
    """Set splits for a transaction (replaces all existing splits).

    The sum of all split amounts must equal the absolute transaction amount.
    """
    transaction = _verify_transaction_ownership(db, transaction_id, current_user)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")

    # Verify all tags belong to user
    splits = []
    for split_req in request.splits:
        tag_id = UUID(split_req.tag_id)
        tag = get_tag_by_id(db, tag_id)
        if not tag or tag.user_id != current_user.id:
            raise HTTPException(status_code=400, detail=f"Invalid tag: {split_req.tag_id}")
        splits.append((tag_id, Decimal(str(split_req.amount))))

    try:
        set_transaction_splits(db, transaction, splits)
        db.commit()
    except SplitValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Refresh to get updated splits with tag relationships
    db.refresh(transaction)
    splits_with_tags = get_splits_with_tags(db, transaction_id)

    return TransactionSplitsResponse(
        transaction_id=str(transaction_id),
        splits=[
            TransactionSplitResponse(
                id=str(split.id),
                tag_id=str(split.tag_id),
                tag_name=tag.name,
                tag_colour=tag.colour,
                amount=float(split.amount),
                is_auto=split.is_auto,
                rule_id=str(split.rule_id) if split.rule_id else None,
                rule_name=split.rule.name if split.rule else None,
            )
            for split, tag in splits_with_tags
        ],
    )


@router.delete(
    "/{transaction_id}/splits",
    status_code=204,
    summary="Clear transaction splits",
    responses=RESOURCE_RESPONSES,
)
def clear_transaction_splits_endpoint(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove all splits from a transaction."""
    transaction = _verify_transaction_ownership(db, transaction_id, current_user)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")

    clear_transaction_splits(db, transaction_id)
    db.commit()


# -----------------------------------------------------------------------------
# Note Endpoint
# -----------------------------------------------------------------------------


@router.patch(
    "/{transaction_id}/note",
    response_model=TransactionResponse,
    summary="Update transaction note",
    responses=RESOURCE_WRITE_RESPONSES,
)
def update_transaction_note(
    transaction_id: UUID,
    request: UpdateNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Update or clear the user note on a transaction."""
    transaction = _verify_transaction_ownership(db, transaction_id, current_user)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")

    transaction.user_note = request.user_note
    db.commit()
    db.refresh(transaction)

    return _to_response(transaction, db)
