"""Tag rules API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.responses import BAD_REQUEST, RESOURCE_RESPONSES, UNAUTHORIZED
from src.api.tag_rules.models import (
    ApplyRulesRequest,
    ApplyRulesResponse,
    ReorderRulesRequest,
    RuleConditions,
    TagRuleCreateRequest,
    TagRuleListResponse,
    TagRuleResponse,
    TagRuleUpdateRequest,
    TestConditionsRequest,
    TestRuleRequest,
    TestRuleResponse,
    TransactionMatchResponse,
)
from src.postgres.auth.models import User
from src.postgres.common.models import TagRule
from src.postgres.common.operations.accounts import get_account_by_id
from src.postgres.common.operations.tag_rules import (
    _NOT_PROVIDED,
    bulk_apply_rules,
    create_tag_rule,
    delete_tag_rule,
    get_tag_rule_by_id,
    get_tag_rules_by_user_id,
    reorder_tag_rules,
    test_conditions_against_transactions,
    test_rule_against_transactions,
    update_tag_rule,
)
from src.postgres.common.operations.tag_rules import RuleConditions as RuleConditionsDict
from src.postgres.common.operations.tags import get_tag_by_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _pydantic_to_dict(conditions: RuleConditions) -> RuleConditionsDict:
    """Convert Pydantic RuleConditions to dict for storage."""
    # Serialize to dict, excluding None values, converting Decimals to floats
    return conditions.model_dump(exclude_none=True, mode="json")  # type: ignore[return-value]


@router.get(
    "",
    response_model=TagRuleListResponse,
    summary="List tag rules",
    responses=UNAUTHORIZED,
)
def list_rules(
    tag_id: UUID | None = Query(None, description="Filter by target tag"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRuleListResponse:
    """List all tag rules for the authenticated user."""
    rules = get_tag_rules_by_user_id(db, current_user.id, tag_id=tag_id)

    return TagRuleListResponse(
        rules=[_to_response(rule) for rule in rules],
        total=len(rules),
    )


@router.post(
    "",
    response_model=TagRuleResponse,
    status_code=201,
    summary="Create tag rule",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def create_new_rule(
    request: TagRuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRuleResponse:
    """Create a new auto-tagging rule."""
    # Validate tag exists and belongs to user
    tag = get_tag_by_id(db, UUID(request.tag_id))
    if not tag or tag.user_id != current_user.id:
        raise HTTPException(status_code=400, detail=f"Tag not found: {request.tag_id}")

    # Validate account if specified
    account_id = None
    if request.account_id:
        account = get_account_by_id(db, UUID(request.account_id))
        if not account:
            raise HTTPException(status_code=400, detail=f"Account not found: {request.account_id}")
        account_id = UUID(request.account_id)

    rule = create_tag_rule(
        db,
        user_id=current_user.id,
        name=request.name,
        tag_id=UUID(request.tag_id),
        conditions=_pydantic_to_dict(request.conditions) if request.conditions else None,
        account_id=account_id,
        enabled=request.enabled,
    )
    db.commit()
    db.refresh(rule)
    logger.info(f"Created tag rule: id={rule.id}, name={rule.name}")
    return _to_response(rule)


@router.get(
    "/{rule_id}",
    response_model=TagRuleResponse,
    summary="Get tag rule by ID",
    responses=RESOURCE_RESPONSES,
)
def get_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRuleResponse:
    """Retrieve a specific tag rule by its UUID."""
    rule = get_tag_rule_by_id(db, rule_id)
    if not rule or rule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    return _to_response(rule)


@router.put(
    "/{rule_id}",
    response_model=TagRuleResponse,
    summary="Update tag rule",
    responses={**RESOURCE_RESPONSES, **BAD_REQUEST},
)
def update_existing_rule(
    rule_id: UUID,
    request: TagRuleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRuleResponse:
    """Update a tag rule's conditions or settings."""
    rule = get_tag_rule_by_id(db, rule_id)
    if not rule or rule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    # Validate tag if changing
    tag_id = None
    if request.tag_id:
        tag = get_tag_by_id(db, UUID(request.tag_id))
        if not tag or tag.user_id != current_user.id:
            raise HTTPException(status_code=400, detail=f"Tag not found: {request.tag_id}")
        tag_id = UUID(request.tag_id)

    # Handle account_id: None = not provided, empty string = clear, uuid = set
    account_id_value: UUID | None | object = _NOT_PROVIDED
    if request.account_id is not None:
        if request.account_id:  # Non-empty string
            account = get_account_by_id(db, UUID(request.account_id))
            if not account:
                raise HTTPException(
                    status_code=400, detail=f"Account not found: {request.account_id}"
                )
            account_id_value = UUID(request.account_id)
        else:  # Empty string = clear
            account_id_value = None

    # Convert conditions if provided
    conditions = _pydantic_to_dict(request.conditions) if request.conditions else None

    updated = update_tag_rule(
        db,
        rule_id,
        name=request.name,
        tag_id=tag_id,
        enabled=request.enabled,
        conditions=conditions,
        account_id=account_id_value,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    db.commit()
    db.refresh(updated)
    logger.info(f"Updated tag rule: id={rule_id}")
    return _to_response(updated)


@router.delete(
    "/{rule_id}",
    status_code=204,
    summary="Delete tag rule",
    responses=RESOURCE_RESPONSES,
)
def delete_existing_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a tag rule."""
    rule = get_tag_rule_by_id(db, rule_id)
    if not rule or rule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    deleted = delete_tag_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    db.commit()
    logger.info(f"Deleted tag rule: id={rule_id}")


@router.post(
    "/{rule_id}/test",
    response_model=TestRuleResponse,
    summary="Test rule against transactions",
    responses=RESOURCE_RESPONSES,
)
def test_rule(
    rule_id: UUID,
    request: TestRuleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestRuleResponse:
    """Test a rule against existing transactions to preview matches."""
    rule = get_tag_rule_by_id(db, rule_id)
    if not rule or rule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    account_ids = [UUID(aid) for aid in request.account_ids] if request.account_ids else None

    matches = test_rule_against_transactions(db, rule, account_ids=account_ids, limit=request.limit)

    return TestRuleResponse(
        matches=[
            TransactionMatchResponse(
                id=str(t.id),
                booking_date=t.booking_date,
                counterparty_name=t.counterparty_name,
                description=t.description,
                amount=t.amount,
                currency=t.currency,
            )
            for t in matches
        ],
        total=len(matches),
    )


@router.post(
    "/test-conditions",
    response_model=TestRuleResponse,
    summary="Test conditions before saving",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def test_conditions(
    request: TestConditionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestRuleResponse:
    """Test rule conditions without saving the rule first.

    Useful for previewing what transactions would match before creating a rule.
    """
    # Validate account if specified
    account_id = None
    if request.account_id:
        account = get_account_by_id(db, UUID(request.account_id))
        if not account:
            raise HTTPException(status_code=400, detail=f"Account not found: {request.account_id}")
        account_id = UUID(request.account_id)

    # Convert conditions to dict
    conditions_dict = _pydantic_to_dict(request.conditions)

    matches = test_conditions_against_transactions(
        db,
        user_id=current_user.id,
        conditions=conditions_dict,
        account_id=account_id,
        limit=request.limit,
    )

    return TestRuleResponse(
        matches=[
            TransactionMatchResponse(
                id=str(t.id),
                booking_date=t.booking_date,
                counterparty_name=t.counterparty_name,
                description=t.description,
                amount=t.amount,
                currency=t.currency,
            )
            for t in matches
        ],
        total=len(matches),
    )


@router.post(
    "/reorder",
    response_model=TagRuleListResponse,
    summary="Reorder rules",
    responses={**UNAUTHORIZED, **BAD_REQUEST},
)
def reorder_rules(
    request: ReorderRulesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRuleListResponse:
    """Update the priority order of rules."""
    rule_ids = [UUID(rid) for rid in request.rule_ids]

    # Verify all rules belong to user
    existing_rules = get_tag_rules_by_user_id(db, current_user.id)
    existing_ids = {rule.id for rule in existing_rules}

    for rid in rule_ids:
        if rid not in existing_ids:
            raise HTTPException(status_code=400, detail=f"Rule not found: {rid}")

    rules = reorder_tag_rules(db, current_user.id, rule_ids)
    db.commit()

    logger.info(f"Reordered tag rules: user_id={current_user.id}")
    return TagRuleListResponse(
        rules=[_to_response(rule) for rule in rules],
        total=len(rules),
    )


@router.post(
    "/apply",
    response_model=ApplyRulesResponse,
    summary="Apply rules to transactions",
    responses=UNAUTHORIZED,
)
def apply_rules(
    request: ApplyRulesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplyRulesResponse:
    """Apply all enabled rules to existing transactions."""
    account_ids = [UUID(aid) for aid in request.account_ids] if request.account_ids else None

    tagged_count = bulk_apply_rules(
        db,
        user_id=current_user.id,
        account_ids=account_ids,
        untagged_only=request.untagged_only,
    )
    db.commit()

    logger.info(f"Applied tag rules: user_id={current_user.id}, tagged_count={tagged_count}")
    return ApplyRulesResponse(tagged_count=tagged_count)


def _to_response(rule: TagRule) -> TagRuleResponse:
    """Convert a TagRule model to response."""
    cond = rule.conditions or {}
    return TagRuleResponse(
        id=str(rule.id),
        name=rule.name,
        tag_id=str(rule.tag_id),
        tag_name=rule.tag.name,
        tag_colour=rule.tag.colour,
        priority=rule.priority,
        enabled=rule.enabled,
        conditions=RuleConditions(
            merchant_contains=cond.get("merchant_contains"),
            merchant_exact=cond.get("merchant_exact"),
            description_contains=cond.get("description_contains"),
            min_amount=cond.get("min_amount"),
            max_amount=cond.get("max_amount"),
            merchant_not_contains=cond.get("merchant_not_contains"),
            description_not_contains=cond.get("description_not_contains"),
        ),
        account_id=str(rule.account_id) if rule.account_id else None,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )
