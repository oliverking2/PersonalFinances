"""Tests for connection operations."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import ConnectionStatus, Provider
from src.postgres.common.models import Connection, Institution
from src.postgres.common.operations.connections import (
    create_connection,
    delete_connection,
    get_connection_by_id,
    get_connection_by_provider_id,
    get_connections_by_user_id,
    update_connection_friendly_name,
    update_connection_status,
)


class TestGetConnectionById:
    """Tests for get_connection_by_id operation."""

    def test_returns_connection_when_found(
        self, db_session: Session, test_connection: Connection
    ) -> None:
        """Should return connection when it exists."""
        result = get_connection_by_id(db_session, test_connection.id)

        assert result is not None
        assert result.id == test_connection.id

    def test_returns_none_when_not_found(
        self, db_session: Session, test_institution: Institution
    ) -> None:
        """Should return None when connection doesn't exist."""
        result = get_connection_by_id(db_session, uuid4())

        assert result is None


class TestGetConnectionByProviderId:
    """Tests for get_connection_by_provider_id operation."""

    def test_returns_connection_when_found(
        self, db_session: Session, test_connection: Connection
    ) -> None:
        """Should return connection when provider and provider_id match."""
        result = get_connection_by_provider_id(
            db_session,
            provider=Provider.GOCARDLESS,
            provider_id=test_connection.provider_id,
        )

        assert result is not None
        assert result.id == test_connection.id

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        """Should return None when no match."""
        result = get_connection_by_provider_id(
            db_session,
            provider=Provider.GOCARDLESS,
            provider_id="nonexistent-id",
        )

        assert result is None


class TestGetConnectionsByUserId:
    """Tests for get_connections_by_user_id operation."""

    def test_returns_user_connections(
        self, db_session: Session, test_connection: Connection, test_user: User
    ) -> None:
        """Should return all connections for a user."""
        result = get_connections_by_user_id(db_session, test_user.id)

        assert len(result) >= 1
        assert any(conn.id == test_connection.id for conn in result)

    def test_filters_by_status(
        self, db_session: Session, test_connection: Connection, test_user: User
    ) -> None:
        """Should filter by status when specified."""
        result = get_connections_by_user_id(
            db_session, test_user.id, status=ConnectionStatus.ACTIVE
        )

        assert all(conn.status == ConnectionStatus.ACTIVE.value for conn in result)

    def test_returns_empty_for_user_with_no_connections(
        self, db_session: Session, test_institution: Institution
    ) -> None:
        """Should return empty list for user without connections."""
        result = get_connections_by_user_id(db_session, uuid4())

        assert result == []


class TestCreateConnection:
    """Tests for create_connection operation."""

    def test_creates_connection(
        self, db_session: Session, test_user: User, test_institution: Institution
    ) -> None:
        """Should create connection with all fields."""
        now = datetime.now()
        result = create_connection(
            db_session,
            user_id=test_user.id,
            provider=Provider.GOCARDLESS,
            provider_id="new-req-id",
            institution_id=test_institution.id,
            friendly_name="New Connection",
            status=ConnectionStatus.PENDING,
            created_at=now,
        )
        db_session.commit()

        assert result.id is not None
        assert result.user_id == test_user.id
        assert result.provider == Provider.GOCARDLESS.value
        assert result.provider_id == "new-req-id"
        assert result.friendly_name == "New Connection"
        assert result.status == ConnectionStatus.PENDING.value


class TestUpdateConnectionFriendlyName:
    """Tests for update_connection_friendly_name operation."""

    def test_updates_friendly_name(self, db_session: Session, test_connection: Connection) -> None:
        """Should update the friendly name."""
        result = update_connection_friendly_name(db_session, test_connection.id, "Updated Name")
        db_session.commit()

        assert result is not None
        assert result.friendly_name == "Updated Name"

    def test_returns_none_when_not_found(
        self, db_session: Session, test_institution: Institution
    ) -> None:
        """Should return None when connection doesn't exist."""
        result = update_connection_friendly_name(db_session, uuid4(), "Name")

        assert result is None


class TestUpdateConnectionStatus:
    """Tests for update_connection_status operation."""

    def test_updates_status(self, db_session: Session, test_connection: Connection) -> None:
        """Should update the status."""
        result = update_connection_status(db_session, test_connection.id, ConnectionStatus.EXPIRED)
        db_session.commit()

        assert result is not None
        assert result.status == ConnectionStatus.EXPIRED.value

    def test_returns_none_when_not_found(
        self, db_session: Session, test_institution: Institution
    ) -> None:
        """Should return None when connection doesn't exist."""
        result = update_connection_status(db_session, uuid4(), ConnectionStatus.ACTIVE)

        assert result is None


class TestDeleteConnection:
    """Tests for delete_connection operation."""

    def test_deletes_connection(self, db_session: Session, test_connection: Connection) -> None:
        """Should delete the connection."""
        conn_id = test_connection.id
        result = delete_connection(db_session, conn_id)
        db_session.commit()

        assert result is True
        assert get_connection_by_id(db_session, conn_id) is None

    def test_returns_false_when_not_found(
        self, db_session: Session, test_institution: Institution
    ) -> None:
        """Should return False when connection doesn't exist."""
        result = delete_connection(db_session, uuid4())

        assert result is False
