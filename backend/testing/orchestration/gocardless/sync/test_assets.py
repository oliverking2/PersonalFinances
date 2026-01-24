"""Tests for GoCardless Dagster sync assets.

These tests focus on the underlying database operations since
Dagster assets are tested via their integration with the orchestration layer.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import AccountStatus, AccountType, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.common.operations.sync import (
    mark_missing_accounts_inactive,
    sync_all_gocardless_accounts,
    sync_all_gocardless_connections,
)
from src.postgres.gocardless.models import BankAccount, RequisitionLink


class TestSyncIntegration:
    """Integration tests for sync operations."""

    def test_sync_connections_updates_existing_connection(
        self,
        db_session: Session,
        test_requisition_link: RequisitionLink,
        test_user: User,
    ) -> None:
        """Test that sync updates an existing connection from its requisition."""
        # Create institution for the requisition
        institution = Institution(
            id=test_requisition_link.institution_id,
            provider=Provider.GOCARDLESS.value,
            name="Test Bank",
            logo_url="https://example.com/logo.png",
            countries=["GB"],
        )
        db_session.add(institution)
        db_session.commit()

        # Create an existing connection that will be synced
        connection = Connection(
            user_id=test_user.id,
            provider=Provider.GOCARDLESS.value,
            provider_id=test_requisition_link.id,
            institution_id=institution.id,
            friendly_name="Old Name",  # Will be updated from requisition
            status=ConnectionStatus.PENDING.value,  # Will be updated
            created_at=datetime.now(),
        )
        db_session.add(connection)
        db_session.commit()

        connections = sync_all_gocardless_connections(db_session)
        db_session.commit()

        assert len(connections) == 1
        synced = connections[0]
        assert synced.id == connection.id
        assert synced.friendly_name == test_requisition_link.friendly_name
        assert synced.status == ConnectionStatus.ACTIVE.value  # Mapped from "LN"

    def test_sync_accounts_syncs_from_bank_accounts(
        self,
        db_session: Session,
        test_bank_account: BankAccount,
        test_requisition_link: RequisitionLink,
        test_user: User,
    ) -> None:
        """Test that sync creates accounts from bank accounts."""
        # Create institution and connection
        institution = Institution(
            id=test_requisition_link.institution_id,
            provider=Provider.GOCARDLESS.value,
            name="Test Bank",
            logo_url="https://example.com/logo.png",
            countries=["GB"],
        )
        db_session.add(institution)
        db_session.commit()

        connection = Connection(
            user_id=test_user.id,
            provider=Provider.GOCARDLESS.value,
            provider_id=test_requisition_link.id,
            institution_id=institution.id,
            friendly_name="Test Connection",
            status=ConnectionStatus.ACTIVE.value,
            created_at=datetime.now(),
        )
        db_session.add(connection)
        db_session.commit()

        accounts = sync_all_gocardless_accounts(db_session, connection)
        db_session.commit()

        assert len(accounts) >= 1
        account = next((a for a in accounts if a.provider_id == test_bank_account.id), None)
        assert account is not None
        assert account.status == AccountStatus.ACTIVE.value
        assert account.account_type == AccountType.BANK.value

    def test_mark_missing_accounts_inactive(
        self,
        db_session: Session,
        test_user: User,
    ) -> None:
        """Test that accounts not in synced set are marked inactive."""
        # Create a connection with an account
        institution = Institution(
            id="TEST_BANK",
            provider=Provider.GOCARDLESS.value,
            name="Test Bank",
            logo_url="https://example.com/logo.png",
            countries=["GB"],
        )
        db_session.add(institution)
        db_session.commit()

        connection = Connection(
            user_id=test_user.id,
            provider=Provider.GOCARDLESS.value,
            provider_id="test-req",
            institution_id=institution.id,
            friendly_name="Test",
            status=ConnectionStatus.ACTIVE.value,
            created_at=datetime.now(),
        )
        db_session.add(connection)
        db_session.commit()

        account = Account(
            connection_id=connection.id,
            provider_id="orphan-account-id",
            account_type=AccountType.BANK.value,
            status=AccountStatus.ACTIVE.value,
            name="Orphan Account",
        )
        db_session.add(account)
        db_session.commit()

        # Sync with empty set - should mark the account inactive
        inactive_count = mark_missing_accounts_inactive(db_session, connection, set())
        db_session.commit()

        assert inactive_count == 1

        db_session.refresh(account)
        assert account.status == AccountStatus.INACTIVE.value
