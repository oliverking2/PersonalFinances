"""Tests for Trading 212 API key operations."""

from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.trading212.operations.api_keys import (
    create_api_key,
    delete_api_key,
    get_active_api_keys,
    get_api_key_by_id,
    get_api_keys_by_user,
    update_api_key_status,
)


class TestCreateApiKey:
    """Tests for create_api_key operation."""

    def test_create_api_key_success(self, db_session: Session, test_user: "User") -> None:
        """Creating an API key should store encrypted key and metadata."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="encrypted_key_data",
            friendly_name="My ISA",
            t212_account_id="12345",
            currency_code="GBP",
        )

        assert api_key.id is not None
        assert api_key.user_id == test_user.id
        assert api_key.api_key_encrypted == "encrypted_key_data"
        assert api_key.friendly_name == "My ISA"
        assert api_key.t212_account_id == "12345"
        assert api_key.currency_code == "GBP"
        assert api_key.status == "active"

    def test_create_api_key_minimal(self, db_session: Session, test_user: "User") -> None:
        """Creating an API key with minimal fields should work."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="encrypted",
            friendly_name="Test",
        )

        assert api_key.id is not None
        assert api_key.t212_account_id is None
        assert api_key.currency_code is None


class TestGetApiKey:
    """Tests for get_api_key operations."""

    def test_get_api_key_by_id_found(self, db_session: Session, test_user: "User") -> None:
        """Getting an API key by ID should return the key."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="encrypted",
            friendly_name="Test",
        )

        result = get_api_key_by_id(db_session, api_key.id)

        assert result is not None
        assert result.id == api_key.id

    def test_get_api_key_by_id_not_found(self, db_session: Session) -> None:
        """Getting a non-existent API key should return None."""
        result = get_api_key_by_id(db_session, uuid4())

        assert result is None

    def test_get_api_keys_by_user(self, db_session: Session, test_user: "User") -> None:
        """Getting API keys by user should return all user's keys."""
        create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key1",
            friendly_name="ISA",
        )
        create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key2",
            friendly_name="Invest",
        )

        results = get_api_keys_by_user(db_session, test_user.id)

        assert len(results) == 2
        assert all(r.user_id == test_user.id for r in results)

    def test_get_active_api_keys(self, db_session: Session, test_user: "User") -> None:
        """Getting active API keys should exclude error status."""
        active_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key1",
            friendly_name="Active",
        )
        error_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key2",
            friendly_name="Error",
        )
        update_api_key_status(db_session, error_key.id, status="error")

        results = get_active_api_keys(db_session, test_user.id)

        assert len(results) == 1
        assert results[0].id == active_key.id


class TestUpdateApiKeyStatus:
    """Tests for update_api_key_status operation."""

    def test_update_status_to_error(self, db_session: Session, test_user: "User") -> None:
        """Updating status to error should store error message."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        result = update_api_key_status(
            db_session,
            api_key.id,
            status="error",
            error_message="API key revoked",
        )

        assert result is not None
        assert result.status == "error"
        assert result.error_message == "API key revoked"

    def test_update_metadata(self, db_session: Session, test_user: "User") -> None:
        """Updating should allow setting account metadata."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        result = update_api_key_status(
            db_session,
            api_key.id,
            status="active",
            t212_account_id="99999",
            currency_code="EUR",
        )

        assert result is not None
        assert result.t212_account_id == "99999"
        assert result.currency_code == "EUR"

    def test_update_not_found(self, db_session: Session) -> None:
        """Updating non-existent key should return None."""
        result = update_api_key_status(db_session, uuid4(), status="error")

        assert result is None


class TestDeleteApiKey:
    """Tests for delete_api_key operation."""

    def test_delete_api_key_success(self, db_session: Session, test_user: "User") -> None:
        """Deleting an API key should remove it."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        result = delete_api_key(db_session, api_key.id, test_user.id)

        assert result is True
        assert get_api_key_by_id(db_session, api_key.id) is None

    def test_delete_api_key_wrong_user(self, db_session: Session, test_user: "User") -> None:
        """Deleting with wrong user ID should fail."""
        api_key = create_api_key(
            db_session,
            user_id=test_user.id,
            api_key_encrypted="key",
            friendly_name="Test",
        )

        result = delete_api_key(db_session, api_key.id, uuid4())

        assert result is False
        assert get_api_key_by_id(db_session, api_key.id) is not None

    def test_delete_api_key_not_found(self, db_session: Session, test_user: "User") -> None:
        """Deleting non-existent key should return False."""
        result = delete_api_key(db_session, uuid4(), test_user.id)

        assert result is False


# Import User type for type hints
if True:
    from src.postgres.auth.models import User
