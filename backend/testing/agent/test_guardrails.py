"""Tests for agent guardrails."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.agent.guardrails import (
    RateLimitExceededError,
    _rate_limit_store,
    enforce_rate_limit,
    handle_empty_results,
    reset_rate_limit_store,
)


@pytest.fixture(autouse=True)
def _clean_rate_limit_store() -> None:
    """Reset rate limit store before each test."""
    reset_rate_limit_store()


class TestEnforceRateLimit:
    """Tests for enforce_rate_limit."""

    def test_allows_first_request(self) -> None:
        """Should allow the first request."""
        user_id = uuid4()
        enforce_rate_limit(user_id)

        assert user_id in _rate_limit_store
        assert len(_rate_limit_store[user_id]) == 1

    def test_allows_multiple_requests_within_limit(self) -> None:
        """Should allow multiple requests under the limit."""
        user_id = uuid4()
        for _ in range(5):
            enforce_rate_limit(user_id)

        assert len(_rate_limit_store[user_id]) == 5

    def test_raises_when_limit_exceeded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should raise RateLimitExceededError when limit is reached."""
        monkeypatch.setenv("AGENT_RATE_LIMIT", "3")
        user_id = uuid4()

        for _ in range(3):
            enforce_rate_limit(user_id)

        with pytest.raises(RateLimitExceededError, match="Rate limit exceeded"):
            enforce_rate_limit(user_id)

    def test_prunes_expired_timestamps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should prune timestamps older than 24 hours."""
        monkeypatch.setenv("AGENT_RATE_LIMIT", "2")
        user_id = uuid4()

        # Add old timestamps manually
        _rate_limit_store[user_id] = [
            datetime.now(UTC) - timedelta(hours=25),
            datetime.now(UTC) - timedelta(hours=26),
        ]

        # Should succeed because old timestamps are pruned
        enforce_rate_limit(user_id)

        assert len(_rate_limit_store[user_id]) == 1

    def test_isolates_users(self) -> None:
        """Should track rate limits independently per user."""
        user_a = uuid4()
        user_b = uuid4()

        enforce_rate_limit(user_a)
        enforce_rate_limit(user_b)

        assert len(_rate_limit_store[user_a]) == 1
        assert len(_rate_limit_store[user_b]) == 1


class TestHandleEmptyResults:
    """Tests for handle_empty_results."""

    def test_returns_friendly_message(self) -> None:
        """Should return a helpful message about empty results."""
        msg = handle_empty_results("How much did I spend?")

        assert "no transactions" in msg.lower() or "no data" in msg.lower()

    def test_suggests_broadening_date_range(self) -> None:
        """Should suggest broadening the date range."""
        msg = handle_empty_results("How much did I spend?")

        assert "broadening" in msg.lower() or "date range" in msg.lower()


class TestResetRateLimitStore:
    """Tests for reset_rate_limit_store."""

    def test_clears_all_entries(self) -> None:
        """Should clear the entire rate limit store."""
        user_id = uuid4()
        enforce_rate_limit(user_id)

        assert len(_rate_limit_store) > 0

        reset_rate_limit_store()

        assert len(_rate_limit_store) == 0
