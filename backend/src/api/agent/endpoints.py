"""Agent API endpoints for natural language analytics queries."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.agent.guardrails import RateLimitExceededError
from src.agent.models import AgentResponse
from src.agent.service import AgentError, AgentService
from src.api.agent.models import AskRequest, SuggestionsResponse
from src.api.dependencies import get_current_user
from src.api.responses import BAD_REQUEST, INTERNAL_ERROR, UNAUTHORIZED, ResponseDict
from src.metadata.service import MetadataService
from src.postgres.auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter()

RATE_LIMITED: ResponseDict = {429: {"description": "Rate limit exceeded"}}


@router.post(
    "/ask",
    response_model=AgentResponse,
    summary="Ask a question about your finances",
    responses={**UNAUTHORIZED, **BAD_REQUEST, **RATE_LIMITED, **INTERNAL_ERROR},
)
def ask_question(
    body: AskRequest,
    current_user: User = Depends(get_current_user),
) -> AgentResponse:
    """Translate a natural language question into analytics and return a narrative answer."""
    try:
        return AgentService.ask(body.question, current_user.id)
    except RateLimitExceededError as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    except AgentError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Agent request failed: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.") from e


@router.get(
    "/suggestions",
    response_model=SuggestionsResponse,
    summary="Get suggested questions",
    responses=UNAUTHORIZED,
)
def get_suggestions(
    current_user: User = Depends(get_current_user),
) -> SuggestionsResponse:
    """Return sample questions derived from dataset metadata."""
    suggestions = MetadataService.get_suggestions()
    return SuggestionsResponse(suggestions=suggestions)
