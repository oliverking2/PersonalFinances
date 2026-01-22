"""Shared pytest fixtures for the test suite."""

import os
from collections.abc import Generator
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.postgres.core import Base
from src.postgres.gocardless.models import BankAccount, RequisitionLink


@pytest.fixture(autouse=True)
def set_test_env_vars() -> Generator[None]:
    """Set environment variables for testing."""
    original_env = os.environ.copy()
    os.environ["ENVIRONMENT"] = "test"
    os.environ["S3_BUCKET_NAME"] = "test-bucket"
    os.environ["AWS_REGION"] = "eu-west-2"
    os.environ["GC_CALLBACK_URL"] = "http://localhost:8501/callback"
    os.environ["POSTGRES_HOSTNAME"] = "localhost"
    os.environ["POSTGRES_USERNAME"] = "test"
    os.environ["POSTGRES_PASSWORD"] = "test"
    os.environ["POSTGRES_DATABASE"] = "test"
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def db_session() -> Generator[Session]:
    """Create a test database session with in-memory SQLite.

    :yields: A SQLAlchemy session connected to an in-memory database.
    """
    engine = create_engine("sqlite:///:memory:")
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
