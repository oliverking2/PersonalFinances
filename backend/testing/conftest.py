"""Shared pytest fixtures for the test suite."""

import os

# Set environment variables BEFORE any src imports to avoid import-time failures
# in orchestration modules that read env vars at module level.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("AWS_REGION", "eu-west-2")
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

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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
def mock_s3_client() -> MagicMock:
    """Create a mock S3 client.

    :returns: A MagicMock configured for S3 operations.
    """
    mock = MagicMock()
    mock.put_object.return_value = {}
    mock.get_object.return_value = {"Body": MagicMock(read=lambda: b'{"test": "data"}')}
    mock.upload_file.return_value = None
    mock.upload_fileobj.return_value = None
    return mock


@pytest.fixture
def mock_ssm_client() -> MagicMock:
    """Create a mock SSM client.

    :returns: A MagicMock configured for SSM operations.
    """
    mock = MagicMock()
    mock.get_parameter.return_value = {"Parameter": {"Value": "test_value"}}
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
