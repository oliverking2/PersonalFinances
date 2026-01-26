"""Pydantic models for tag rule endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RuleConditions(BaseModel):
    """Filter conditions for a tag rule. All fields are optional."""

    # Include conditions (all must match)
    merchant_contains: str | None = Field(
        None, max_length=200, description="Merchant name must contain this (case-insensitive)"
    )
    merchant_exact: str | None = Field(
        None, max_length=200, description="Merchant name must match exactly"
    )
    description_contains: str | None = Field(
        None, max_length=200, description="Description must contain this (case-insensitive)"
    )
    min_amount: Decimal | None = Field(None, ge=0, description="Minimum absolute amount")
    max_amount: Decimal | None = Field(None, ge=0, description="Maximum absolute amount")

    # Exclude conditions (none must match)
    merchant_not_contains: str | None = Field(
        None, max_length=200, description="Merchant name must NOT contain this"
    )
    description_not_contains: str | None = Field(
        None, max_length=200, description="Description must NOT contain this"
    )


class TagRuleResponse(BaseModel):
    """Response model for a tag rule."""

    id: str = Field(..., description="Rule UUID")
    name: str = Field(..., description="Rule name")
    tag_id: str = Field(..., description="Target tag UUID")
    tag_name: str = Field(..., description="Target tag name")
    tag_colour: str | None = Field(None, description="Target tag colour")
    priority: int = Field(..., description="Rule priority (lower = higher priority)")
    enabled: bool = Field(..., description="Whether the rule is active")
    conditions: RuleConditions = Field(..., description="Filter conditions")
    account_id: str | None = Field(None, description="Limit to this account (FK)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class TagRuleListResponse(BaseModel):
    """Response model for listing tag rules."""

    rules: list[TagRuleResponse] = Field(..., description="List of tag rules")
    total: int = Field(..., description="Total number of rules")


class TagRuleCreateRequest(BaseModel):
    """Request model for creating a tag rule."""

    name: str = Field(..., min_length=1, max_length=100, description="Rule name")
    tag_id: str = Field(..., description="Target tag UUID")
    enabled: bool = Field(True, description="Whether the rule is active")
    conditions: RuleConditions | None = Field(None, description="Filter conditions")
    account_id: str | None = Field(None, description="Limit to this account UUID")


class TagRuleUpdateRequest(BaseModel):
    """Request model for updating a tag rule. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=100, description="New rule name")
    tag_id: str | None = Field(None, description="New target tag UUID")
    enabled: bool | None = Field(None, description="New enabled state")
    conditions: RuleConditions | None = Field(None, description="New filter conditions")
    account_id: str | None = Field(
        None, description="New account UUID (empty string to clear, omit to keep)"
    )


class ReorderRulesRequest(BaseModel):
    """Request model for reordering rules."""

    rule_ids: list[str] = Field(..., min_length=1, description="Rule IDs in desired order")


class ApplyRulesRequest(BaseModel):
    """Request model for applying rules to transactions."""

    account_ids: list[str] | None = Field(None, description="Limit to these accounts")
    untagged_only: bool = Field(True, description="Only process untagged transactions")


class ApplyRulesResponse(BaseModel):
    """Response model for apply rules operation."""

    tagged_count: int = Field(..., description="Number of transactions tagged")


class TestRuleRequest(BaseModel):
    """Request model for testing a saved rule."""

    account_ids: list[str] | None = Field(None, description="Limit search to these accounts")
    limit: int = Field(20, ge=1, le=100, description="Maximum matches to return")


class TestConditionsRequest(BaseModel):
    """Request model for testing rule conditions before saving."""

    conditions: RuleConditions = Field(..., description="Conditions to test")
    account_id: str | None = Field(None, description="Limit to this account UUID")
    limit: int = Field(20, ge=1, le=100, description="Maximum matches to return")


class TestRuleResponse(BaseModel):
    """Response model for testing a rule."""

    matches: list["TransactionMatchResponse"] = Field(..., description="Matching transactions")
    total: int = Field(..., description="Number of matches found (up to limit)")


class TransactionMatchResponse(BaseModel):
    """Simplified transaction info for rule testing."""

    id: str = Field(..., description="Transaction UUID")
    booking_date: datetime | None = Field(None, description="Booking date")
    counterparty_name: str | None = Field(None, description="Counterparty/merchant name")
    description: str | None = Field(None, description="Transaction description")
    amount: Decimal = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
