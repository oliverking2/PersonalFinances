"""Shared pytest fixtures for the test suite."""

import os

# Set environment variables BEFORE any src imports to avoid import-time failures
# in orchestration modules that read env vars at module level.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("GC_CALLBACK_URL", "http://localhost:8501/callback")
os.environ.setdefault("POSTGRES_HOSTNAME", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USERNAME", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DATABASE", "test")
os.environ.setdefault("POSTGRES_DAGSTER_DATABASE", "dagster_test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-jwt-signing-min-32-chars")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("GC_SECRET_ID", "test-secret-id")
os.environ.setdefault("GC_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token-for-registration")
os.environ.setdefault("T212_ENCRYPTION_KEY", "I2bDZ1RTbAvAoYcf304u3XqUtWUO4zSWzSugt4tst_M=")
os.environ.setdefault("AWS_BEDROCK_REGION", "us-east-1")
os.environ.setdefault("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-v1-0")
os.environ.setdefault("AGENT_RATE_LIMIT", "50")

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

# Import FastAPI test dependencies
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.app import app
from src.api.dependencies import get_db
from src.postgres.auth.models import RefreshToken, User
from src.postgres.common.enums import AccountStatus, AccountType, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.core import Base
from src.postgres.gocardless.models import BankAccount, RequisitionLink
from src.utils.security import create_access_token, hash_password


@pytest.fixture(autouse=True)
def set_test_env_vars() -> Generator[None]:
    """Ensure environment variables are set for testing.

    Environment variables are set at module level for collection-time imports.
    This fixture ensures they're restored after each test in case a test modifies them.
    """
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def db_session() -> Generator[Session]:
    """Create a test database session with in-memory SQLite.

    :yields: A SQLAlchemy session connected to an in-memory database.
    """
    # check_same_thread=False allows SQLite to be used across threads (for TestClient)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# API Test Fixtures
# ============================================================================
# These fixtures are used by FastAPI endpoint tests that need TestClient


@pytest.fixture(scope="function")
def api_db_session() -> Generator[Session]:
    """Create a test database session for API tests.

    Uses StaticPool to ensure all connections share the same in-memory database,
    which is required for TestClient to work correctly with SQLite.

    :yields: A SQLAlchemy session connected to an in-memory database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(api_db_session: Session) -> Generator[TestClient]:
    """Create test client with overridden database dependency.

    :param api_db_session: The test database session.
    :yields: A FastAPI TestClient configured for testing.
    """

    def override_get_db() -> Generator[Session]:
        try:
            yield api_db_session
        finally:
            pass  # Don't close - the fixture owns the session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_in_db(api_db_session: Session) -> User:
    """Create a user directly in the database for API testing.

    :param api_db_session: The test database session.
    :returns: The created User with password "testpassword123".
    """
    user = User(
        username="testuser",
        password_hash=hash_password("testpassword123"),
        first_name="Test",
        last_name="User",
    )
    api_db_session.add(user)
    api_db_session.commit()
    return user


@pytest.fixture
def api_auth_headers(test_user_in_db: User) -> dict[str, str]:
    """Create authentication headers with a valid JWT token for API tests.

    :param test_user_in_db: The test user.
    :returns: Dictionary with Authorization header.
    """
    token = create_access_token(test_user_in_db.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers() -> dict[str, str]:
    """Create authentication headers with admin token for protected operations.

    :returns: Dictionary with Authorization header containing admin token.
    """
    return {"Authorization": "Bearer test-admin-token-for-registration"}


@pytest.fixture
def test_institution_in_db(api_db_session: Session) -> Institution:
    """Create an institution in the API test database.

    :param api_db_session: The API test database session.
    :returns: The created Institution.
    """
    institution = Institution(
        id="CHASE_CHASGB2L",
        provider=Provider.GOCARDLESS.value,
        name="Chase UK",
        logo_url="https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png",
        countries=["GB"],
    )
    api_db_session.add(institution)
    api_db_session.commit()
    return institution


@pytest.fixture
def test_connection_in_db(
    api_db_session: Session, test_user_in_db: User, test_institution_in_db: Institution
) -> Connection:
    """Create a connection in the API test database.

    :param api_db_session: The API test database session.
    :param test_user_in_db: The test user.
    :param test_institution_in_db: The test institution.
    :returns: The created Connection.
    """
    connection = Connection(
        user_id=test_user_in_db.id,
        provider=Provider.GOCARDLESS.value,
        provider_id="test-req-id",
        institution_id=test_institution_in_db.id,
        friendly_name="Test Connection",
        status=ConnectionStatus.ACTIVE.value,
        created_at=datetime.now(),
    )
    api_db_session.add(connection)
    api_db_session.commit()
    return connection


@pytest.fixture
def test_account_in_db(api_db_session: Session, test_connection_in_db: Connection) -> Account:
    """Create an account in the API test database.

    :param api_db_session: The API test database session.
    :param test_connection_in_db: The test connection.
    :returns: The created Account.
    """
    account = Account(
        connection_id=test_connection_in_db.id,
        provider_id="test-gc-account-id",
        status=AccountStatus.ACTIVE.value,
        name="Test Account",
        display_name="My Account",
        iban="GB00TEST00000000001234",
        currency="GBP",
    )
    api_db_session.add(account)
    api_db_session.commit()
    return account


@pytest.fixture
def mock_gocardless_credentials() -> MagicMock:
    """Create a mock GoCardlessCredentials object.

    :returns: A MagicMock configured for GoCardless credentials.
    """
    mock = MagicMock()
    mock.access_token = "test_access_token"
    mock.make_get_request.return_value = {}
    mock.make_post_request.return_value = {}
    mock.make_delete_request.return_value = {}
    mock.make_put_request.return_value = {}
    return mock


@pytest.fixture
def test_requisition_link(db_session: Session) -> RequisitionLink:
    """Create a test RequisitionLink in the database.

    :param db_session: Database session.
    :returns: The created RequisitionLink.
    """
    link = RequisitionLink(
        id="test-req-id",
        created=datetime.now(),
        updated=datetime.now(),
        redirect="https://example.com/callback",
        status="LN",
        institution_id="CHASE_CHASGB2L",
        agreement="test-agreement-id",
        reference="test-reference",
        link="https://gocardless.com/auth/test",
        ssn=None,
        account_selection=False,
        redirect_immediate=False,
        friendly_name="Test Account",
        dg_account_expired=False,
    )
    db_session.add(link)
    db_session.commit()
    return link


@pytest.fixture
def test_bank_account(db_session: Session, test_requisition_link: RequisitionLink) -> BankAccount:
    """Create a test BankAccount in the database.

    :param db_session: Database session.
    :param test_requisition_link: The requisition link to associate with.
    :returns: The created BankAccount.
    """
    account = BankAccount(
        id="test-account-id",
        requisition_id=test_requisition_link.id,
        status="READY",
        currency="GBP",
        name="Test Account",
        iban="GB00TEST00000000001234",
    )
    db_session.add(account)
    db_session.commit()
    return account


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user in the database.

    :param db_session: Database session.
    :returns: The created User with password "testpassword".
    """
    user = User(
        username="testuser",
        password_hash=hash_password("testpassword"),
        first_name="Test",
        last_name="User",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_institution(db_session: Session) -> Institution:
    """Create a test Institution in the database.

    :param db_session: Database session.
    :returns: The created Institution.
    """
    institution = Institution(
        id="CHASE_CHASGB2L",
        provider=Provider.GOCARDLESS.value,
        name="Chase UK",
        logo_url="https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png",
        countries=["GB"],
    )
    db_session.add(institution)
    db_session.commit()
    return institution


@pytest.fixture
def test_connection(
    db_session: Session, test_user: User, test_institution: Institution
) -> Connection:
    """Create a test Connection in the database.

    :param db_session: Database session.
    :param test_user: The user to associate with.
    :param test_institution: The institution to associate with.
    :returns: The created Connection.
    """
    connection = Connection(
        user_id=test_user.id,
        provider=Provider.GOCARDLESS.value,
        provider_id="test-req-id",
        institution_id=test_institution.id,
        friendly_name="Test Connection",
        status=ConnectionStatus.ACTIVE.value,
        created_at=datetime.now(),
    )
    db_session.add(connection)
    db_session.commit()
    return connection


@pytest.fixture
def test_account(db_session: Session, test_connection: Connection) -> Account:
    """Create a test Account in the database.

    :param db_session: Database session.
    :param test_connection: The connection to associate with.
    :returns: The created Account.
    """
    account = Account(
        connection_id=test_connection.id,
        provider_id="test-gc-account-id",
        account_type=AccountType.BANK.value,
        status=AccountStatus.ACTIVE.value,
        name="Test Account",
        display_name="My Test Account",
        iban="GB00TEST00000000001234",
        currency="GBP",
        balance_amount=Decimal("1000.00"),
        balance_currency="GBP",
        balance_type="interimAvailable",
        balance_updated_at=datetime.now(),
    )
    db_session.add(account)
    db_session.commit()
    return account


@pytest.fixture
def test_refresh_token(db_session: Session, test_user: User) -> tuple[str, RefreshToken]:
    """Create a test refresh token for the test user.

    :param db_session: Database session.
    :param test_user: The user to create a token for.
    :returns: Tuple of (raw_token, RefreshToken entity).
    """
    # Import here to avoid circular imports during test collection
    from src.postgres.auth.operations.refresh_tokens import (  # noqa: PLC0415
        create_refresh_token,
    )

    raw_token, token = create_refresh_token(db_session, test_user)
    db_session.commit()
    return raw_token, token


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Create authentication headers with a valid JWT token.

    :param test_user: The user to create a token for.
    :returns: Dictionary with Authorization header.
    """
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


# Builder functions for mock API responses


def build_gocardless_requisition_response(
    requisition_id: str = "test-req-id",
    status: str = "LN",
    institution_id: str = "CHASE_CHASGB2L",
    accounts: list[str] | None = None,
) -> dict[str, Any]:
    """Build a mock GoCardless requisition API response.

    :param requisition_id: The requisition ID.
    :param status: The requisition status.
    :param institution_id: The institution ID.
    :param accounts: Optional list of account IDs.
    :returns: A dictionary matching GoCardless API response format.
    """
    return {
        "id": requisition_id,
        "created": "2024-01-01T00:00:00Z",
        "redirect": "https://example.com/callback",
        "status": status,
        "institution_id": institution_id,
        "agreement": "test-agreement-id",
        "reference": "test-reference",
        "link": "https://gocardless.com/auth/test",
        "ssn": None,
        "account_selection": False,
        "redirect_immediate": False,
        "accounts": accounts or [],
    }


def build_gocardless_account_response(
    account_id: str = "test-account-id",
    status: str = "READY",
) -> dict[str, Any]:
    """Build a mock GoCardless account API response.

    :param account_id: The account ID.
    :param status: The account status.
    :returns: A dictionary matching GoCardless API response format.
    """
    return {
        "id": account_id,
        "status": status,
        "iban": "GB00TEST00000000001234",
        "currency": "GBP",
        "name": "Test Account",
        "owner_name": "Test Owner",
        "bban": None,
        "bic": None,
    }


def build_gocardless_transactions_response() -> dict[str, Any]:
    """Build a mock GoCardless transactions API response.

    :returns: A dictionary matching GoCardless API response format.
    """
    return {
        "transactions": {
            "booked": [
                {
                    "transactionId": "txn-001",
                    "bookingDate": "2024-01-15",
                    "valueDate": "2024-01-15",
                    "transactionAmount": {"amount": "-50.00", "currency": "GBP"},
                    "creditorName": "Test Shop",
                    "remittanceInformationUnstructured": "Purchase at Test Shop",
                },
            ],
            "pending": [],
        },
    }


def build_gocardless_balances_response() -> dict[str, Any]:
    """Build a mock GoCardless balances API response.

    :returns: A dictionary matching GoCardless API response format.
    """
    return {
        "balances": [
            {
                "balanceAmount": {"amount": "1000.00", "currency": "GBP"},
                "balanceType": "interimAvailable",
                "referenceDate": "2024-01-15",
            },
        ],
    }
