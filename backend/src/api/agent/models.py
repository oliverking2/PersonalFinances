"""Pydantic request/response models for the agent API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request body for the agent ask endpoint."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language question about your finances.",
    )


class SuggestionsResponse(BaseModel):
    """Response containing suggested questions."""

    suggestions: list[str]
