"""Tests for sync operations."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import AccountStatus, AccountType, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.common.operations.sync import (
    mark_missing_accounts_inactive,
    sync_all_gocardless_connections,
    sync_gocardless_account,
    sync_gocardless_connection,
)
from src.postgres.gocardless.models import Balance, BankAccount, RequisitionLink


class TestSyncGocardlessConnection:
    """Tests for sync_gocardless_connection operation."""

    def test_updates_connection_from_requisition(
        self,
        db_session: Session,
        test_connection: Connection,
        test_requisition_link: RequisitionLink,
    ) -> None:
        """Should update connection status from requisition."""
        # Update requisition status
        test_requisition_link.status = "EX"  # Expired
        test_requisition_link.friendly_name = "Updated Name"
        db_session.commit()

        # Ensure connection provider_id matches requisition id
        test_connection.provider_id = test_requisition_link.id
        db_session.commit()

        result = sync_gocardless_connection(db_session, test_connection)
        db_session.commit()

        assert result.status == ConnectionStatus.EXPIRED.value
        assert result.friendly_name == "Updated Name"

    def test_handles_missing_requisition(
        self,
        db_session: Session,
        test_connection: Connection,
    ) -> None:
        """Should return connection unchanged if requisition not found."""
        # Set provider_id to non-existent requisition
        test_connection.provider_id = "nonexistent-req-id"
        original_status = test_connection.status
        db_session.commit()

        result = sync_gocardless_connection(db_session, test_connection)
        db_session.commit()

        assert result.status == original_status

    def test_maps_requisition_status_correctly(
        self,
        db_session: Session,
        test_user: User,
        test_institution: Institution,
    ) -> None:
        """Should correctly map GoCardless status to ConnectionStatus."""
        status_mappings = [
            ("CR", ConnectionStatus.PENDING),
            ("LN", ConnectionStatus.ACTIVE),
            ("EX", ConnectionStatus.EXPIRED),
            ("RJ", ConnectionStatus.ERROR),
        ]

        for gc_status, expected_status in status_mappings:
            # Create requisition with specific status
            req = RequisitionLink(
                id=f"test-req-{gc_status}",
                created=datetime.now(),
                updated=datetime.now(),
                redirect="https://example.com/callback",
                status=gc_status,
                institution_id=test_institution.id,
                agreement="test-agreement",
                reference="test-reference",
                link="https://gocardless.com/auth/test",
                account_selection=False,
                redirect_immediate=False,
                friendly_name=f"Test {gc_status}",
                dg_account_expired=False,
            )
            db_session.add(req)
            db_session.commit()

            # Create connection linked to requisition
            connection = Connection(
                user_id=test_user.id,
                provider=Provider.GOCARDLESS.value,
                provider_id=req.id,
                institution_id=test_institution.id,
                friendly_name="Test",
                status=ConnectionStatus.PENDING.value,
                created_at=datetime.now(),
            )
            db_session.add(connection)
            db_session.commit()

            result = sync_gocardless_connection(db_session, connection)
            db_session.commit()

            assert result.status == expected_status.value, (
                f"Expected {expected_status.value} for GC status {gc_status}, got {result.status}"
            )


class TestSyncGocardlessAccount:
    """Tests for sync_gocardless_account operation."""

    def test_creates_new_account(
        self,
        db_session: Session,
        test_connection: Connection,
        test_bank_account: BankAccount,
    ) -> None:
        """Should create a new account from bank account."""
        result = sync_gocardless_account(db_session, test_bank_account, test_connection)
        db_session.commit()

        assert result is not None
        assert result.connection_id == test_connection.id
        assert result.provider_id == test_bank_account.id
        assert result.account_type == AccountType.BANK.value
        assert result.status == AccountStatus.ACTIVE.value

    def test_updates_existing_account(
        self,
        db_session: Session,
        test_connection: Connection,
        test_bank_account: BankAccount,
    ) -> None:
        """Should update existing account when syncing again."""
        # First sync
        account1 = sync_gocardless_account(db_session, test_bank_account, test_connection)
        db_session.commit()
        original_id = account1.id

        # Update bank account and sync again
        test_bank_account.name = "Updated Name"
        db_session.commit()

        account2 = sync_gocardless_account(db_session, test_bank_account, test_connection)
        db_session.commit()

        assert account2.id == original_id
        assert account2.name == "Updated Name"

    def test_syncs_balance_when_available(
        self,
        db_session: Session,
        test_connection: Connection,
        test_bank_account: BankAccount,
    ) -> None:
        """Should sync balance data when available."""
        # Create balance for the bank account
        balance = Balance(
            account_id=test_bank_account.id,
            balance_amount=Decimal("1500.00"),
            balance_currency="GBP",
            balance_type="interimAvailable",
            last_change_date=datetime.now(),
        )
        db_session.add(balance)
        db_session.commit()

        result = sync_gocardless_account(db_session, test_bank_account, test_connection)
        db_session.commit()

        assert result.balance_amount == Decimal("1500.00")
        assert result.balance_currency == "GBP"
        assert result.balance_type == "interimAvailable"


class TestSyncAllGocardlessConnections:
    """Tests for sync_all_gocardless_connections operation."""

    def test_syncs_all_gocardless_connections(
        self,
        db_session: Session,
        test_user: User,
        test_institution: Institution,
    ) -> None:
        """Should sync all GoCardless connections."""
        # Create requisitions and connections
        for i in range(3):
            req = RequisitionLink(
                id=f"test-req-{i}",
                created=datetime.now(),
                updated=datetime.now(),
                redirect="https://example.com/callback",
                status="LN",
                institution_id=test_institution.id,
                agreement="test-agreement",
                reference=f"test-reference-{i}",
                link="https://gocardless.com/auth/test",
                account_selection=False,
                redirect_immediate=False,
                friendly_name=f"Test Connection {i}",
                dg_account_expired=False,
            )
            db_session.add(req)

            conn = Connection(
                user_id=test_user.id,
                provider=Provider.GOCARDLESS.value,
                provider_id=req.id,
                institution_id=test_institution.id,
                friendly_name=f"Old Name {i}",
                status=ConnectionStatus.PENDING.value,
                created_at=datetime.now(),
            )
            db_session.add(conn)
        db_session.commit()

        result = sync_all_gocardless_connections(db_session)
        db_session.commit()

        assert len(result) == 3
        # All should be updated to ACTIVE status (LN -> ACTIVE)
        assert all(c.status == ConnectionStatus.ACTIVE.value for c in result)

    def test_ignores_non_gocardless_connections(
        self,
        db_session: Session,
        test_user: User,
        test_institution: Institution,
    ) -> None:
        """Should only sync GoCardless connections, not other providers."""
        # Create a Trading212 connection (no requisition needed)
        t212_conn = Connection(
            user_id=test_user.id,
            provider=Provider.TRADING212.value,
            provider_id="t212-account-id",
            institution_id=test_institution.id,
            friendly_name="Trading212 Account",
            status=ConnectionStatus.ACTIVE.value,
            created_at=datetime.now(),
        )
        db_session.add(t212_conn)
        db_session.commit()

        result = sync_all_gocardless_connections(db_session)
        db_session.commit()

        # Should not include the Trading212 connection
        assert all(c.provider == Provider.GOCARDLESS.value for c in result)


class TestMarkMissingAccountsInactive:
    """Tests for mark_missing_accounts_inactive operation."""

    def test_marks_missing_accounts_inactive(
        self,
        db_session: Session,
        test_connection: Connection,
    ) -> None:
        """Should mark accounts inactive if not in synced set."""
        # Create two accounts
        account1 = Account(
            connection_id=test_connection.id,
            provider_id="account-1",
            account_type=AccountType.BANK.value,
            status=AccountStatus.ACTIVE.value,
        )
        account2 = Account(
            connection_id=test_connection.id,
            provider_id="account-2",
            account_type=AccountType.BANK.value,
            status=AccountStatus.ACTIVE.value,
        )
        db_session.add_all([account1, account2])
        db_session.commit()

        # Only account-1 was synced
        result = mark_missing_accounts_inactive(db_session, test_connection, {"account-1"})
        db_session.commit()

        assert result == 1
        db_session.refresh(account2)
        assert account2.status == AccountStatus.INACTIVE.value

    def test_does_not_mark_synced_accounts_inactive(
        self,
        db_session: Session,
        test_connection: Connection,
    ) -> None:
        """Should not mark accounts inactive if they were synced."""
        account = Account(
            connection_id=test_connection.id,
            provider_id="account-1",
            account_type=AccountType.BANK.value,
            status=AccountStatus.ACTIVE.value,
        )
        db_session.add(account)
        db_session.commit()

        result = mark_missing_accounts_inactive(db_session, test_connection, {"account-1"})
        db_session.commit()

        assert result == 0
        db_session.refresh(account)
        assert account.status == AccountStatus.ACTIVE.value
