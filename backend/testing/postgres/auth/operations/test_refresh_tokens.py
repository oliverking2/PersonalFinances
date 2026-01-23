"""Tests for refresh token database operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.postgres.auth.models import RefreshToken, User
from src.postgres.auth.operations.refresh_tokens import (
    create_refresh_token,
    find_token_by_raw_value,
    is_token_valid,
    revoke_all_user_tokens,
    revoke_token,
    rotate_token,
)
from src.utils.security import verify_refresh_token


class TestCreateRefreshToken:
    """Tests for create_refresh_token operation."""

    def test_creates_token_with_hashed_value(self, db_session: Session, test_user: User) -> None:
        """Should create token with bcrypt hashed value."""
        raw_token, token = create_refresh_token(db_session, test_user)
        db_session.commit()

        assert token.id is not None
        assert token.user_id == test_user.id
        assert token.token_hash != raw_token
        assert verify_refresh_token(raw_token, token.token_hash) is True

    def test_sets_expiry(self, db_session: Session, test_user: User) -> None:
        """Should set expires_at based on config."""
        _, token = create_refresh_token(db_session, test_user, expires_days=7)
        db_session.commit()

        # Should expire roughly 7 days from now
        expected = datetime.now(UTC) + timedelta(days=7)
        # SQLite may return naive datetimes, so make both naive for comparison
        token_expires = token.expires_at.replace(tzinfo=None)
        expected_naive = expected.replace(tzinfo=None)
        assert abs((token_expires - expected_naive).total_seconds()) < 60

    def test_stores_metadata(self, db_session: Session, test_user: User) -> None:
        """Should store user agent and IP address."""
        _, token = create_refresh_token(
            db_session,
            test_user,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )
        db_session.commit()

        assert token.user_agent == "Mozilla/5.0"
        assert token.ip_address == "192.168.1.1"

    def test_stores_rotation_link(self, db_session: Session, test_user: User) -> None:
        """Should store rotated_from ID when provided."""
        _, first_token = create_refresh_token(db_session, test_user)
        _, second_token = create_refresh_token(
            db_session, test_user, rotated_from_id=first_token.id
        )
        db_session.commit()

        assert second_token.rotated_from == first_token.id


class TestFindTokenByRawValue:
    """Tests for find_token_by_raw_value operation."""

    def test_finds_valid_token(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should find token by raw value."""
        raw_token, expected_token = test_refresh_token

        result = find_token_by_raw_value(db_session, raw_token)

        assert result is not None
        assert result.id == expected_token.id

    def test_returns_none_for_invalid_token(self, db_session: Session) -> None:
        """Should return None for non-existent token."""
        result = find_token_by_raw_value(db_session, "invalid-token-value")

        assert result is None

    def test_finds_revoked_token(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should find revoked tokens (for replay detection)."""
        raw_token, token = test_refresh_token
        token.revoked_at = datetime.now(UTC)
        db_session.commit()

        result = find_token_by_raw_value(db_session, raw_token)

        assert result is not None
        assert result.id == token.id


class TestIsTokenValid:
    """Tests for is_token_valid function."""

    def test_valid_token(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should return True for valid, non-revoked, non-expired token."""
        _, token = test_refresh_token

        assert is_token_valid(token) is True

    def test_revoked_token(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should return False for revoked token."""
        _, token = test_refresh_token
        token.revoked_at = datetime.now(UTC)

        assert is_token_valid(token) is False

    def test_expired_token(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should return False for expired token."""
        _, token = test_refresh_token
        token.expires_at = datetime.now(UTC) - timedelta(days=1)

        assert is_token_valid(token) is False


class TestRevokeToken:
    """Tests for revoke_token operation."""

    def test_sets_revoked_at(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should set revoked_at timestamp."""
        _, token = test_refresh_token
        assert token.revoked_at is None

        revoke_token(db_session, token)
        db_session.commit()

        assert token.revoked_at is not None
        assert is_token_valid(token) is False


class TestRevokeAllUserTokens:
    """Tests for revoke_all_user_tokens operation."""

    def test_revokes_all_active_tokens(self, db_session: Session, test_user: User) -> None:
        """Should revoke all non-revoked tokens for user."""
        # Create multiple tokens
        _, token1 = create_refresh_token(db_session, test_user)
        _, token2 = create_refresh_token(db_session, test_user)
        _, token3 = create_refresh_token(db_session, test_user)
        db_session.commit()

        count = revoke_all_user_tokens(db_session, test_user.id)
        db_session.commit()

        assert count == 3
        assert token1.revoked_at is not None
        assert token2.revoked_at is not None
        assert token3.revoked_at is not None

    def test_ignores_already_revoked(self, db_session: Session, test_user: User) -> None:
        """Should not count already revoked tokens."""
        _, token1 = create_refresh_token(db_session, test_user)
        _, _token2 = create_refresh_token(db_session, test_user)
        db_session.commit()

        # Revoke one first
        revoke_token(db_session, token1)
        db_session.commit()

        count = revoke_all_user_tokens(db_session, test_user.id)

        assert count == 1


class TestRotateToken:
    """Tests for rotate_token operation."""

    def test_revokes_old_and_creates_new(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should revoke old token and create new one."""
        _, old_token = test_refresh_token

        new_raw, new_token = rotate_token(db_session, old_token)
        db_session.commit()

        assert old_token.revoked_at is not None
        assert new_token.id != old_token.id
        assert new_token.rotated_from == old_token.id
        assert verify_refresh_token(new_raw, new_token.token_hash) is True

    def test_preserves_user_id(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should create new token for same user."""
        _, old_token = test_refresh_token

        _, new_token = rotate_token(db_session, old_token)

        assert new_token.user_id == old_token.user_id

    def test_stores_metadata(
        self, db_session: Session, test_refresh_token: tuple[str, RefreshToken]
    ) -> None:
        """Should store user agent and IP on new token."""
        _, old_token = test_refresh_token

        _, new_token = rotate_token(
            db_session,
            old_token,
            user_agent="New User Agent",
            ip_address="10.0.0.1",
        )

        assert new_token.user_agent == "New User Agent"
        assert new_token.ip_address == "10.0.0.1"
