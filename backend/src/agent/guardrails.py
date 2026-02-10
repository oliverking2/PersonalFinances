"""Rate limiting and safety guardrails for the agent API."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

logger = logging.getLogger(__name__)

# In-memory rate limit store: user_id -> list of request timestamps
_rate_limit_store: dict[UUID, list[datetime]] = {}

# Rolling window for rate limit checks
_RATE_LIMIT_WINDOW = timedelta(hours=24)


class RateLimitExceededError(Exception):
    """Raised when a user exceeds the agent API rate limit."""


def _get_rate_limit() -> int:
    """Get the configured rate limit from environment.

    :returns: Maximum requests per 24h window.
    """
    return int(os.environ.get("AGENT_RATE_LIMIT", "50"))


def enforce_rate_limit(user_id: UUID) -> None:
    """Check and enforce the per-user rate limit.

    :param user_id: User to check.
    :raises RateLimitExceededError: If the user has exceeded the limit.
    """
    limit = _get_rate_limit()
    now = datetime.now(UTC)
    cutoff = now - _RATE_LIMIT_WINDOW

    # Get existing timestamps and prune expired ones
    timestamps = _rate_limit_store.get(user_id, [])
    timestamps = [ts for ts in timestamps if ts > cutoff]

    if len(timestamps) >= limit:
        logger.warning(f"Rate limit exceeded: user_id={user_id}, count={len(timestamps)}")
        raise RateLimitExceededError(f"Rate limit exceeded. Maximum {limit} requests per 24 hours.")

    timestamps.append(now)
    _rate_limit_store[user_id] = timestamps


def handle_empty_results(question: str) -> str:
    """Generate a friendly message when a query returns no data.

    :param question: The user's original question.
    :returns: Friendly message about empty results.
    """
    return (
        "I wasn't able to find any data matching your question. "
        "This could mean there are no transactions for that period, "
        "or the data hasn't been refreshed yet. "
        "Try broadening your date range or check the analytics refresh status."
    )


def reset_rate_limit_store() -> None:
    """Clear the rate limit store. Used for test cleanup."""
    _rate_limit_store.clear()
