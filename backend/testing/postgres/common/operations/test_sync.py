"""Tests for sync operations."""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import AccountStatus, AccountType, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.common.operations.sync import (
    mark_missing_accounts_inactive,
    sync_all_gocardless_accounts,
    sync_all_gocardless_connections,
    sync_all_gocardless_institutions,
    sync_all_gocardless_transactions,
    sync_gocardless_account,
    sync_gocardless_connection,
    sync_gocardless_institution,
    sync_gocardless_transaction,
)
from src.postgres.gocardless.models import (
    Balance,
    BankAccount,
    GoCardlessInstitution,
    GoCardlessTransaction,
    RequisitionLink,
)


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

    def test_updates_balance_on_existing_account(
        self,
        db_session: Session,
        test_connection: Connection,
        test_bank_account: BankAccount,
    ) -> None:
        """Should update balance on existing account when syncing again."""
        # First sync without balance
        account = sync_gocardless_account(db_session, test_bank_account, test_connection)
        db_session.commit()

        assert account.balance_amount is None

        # Create balance and sync again
        balance = Balance(
            account_id=test_bank_account.id,
            balance_amount=Decimal("2500.00"),
            balance_currency="EUR",
            balance_type="closingAvailable",
            last_change_date=datetime.now(),
        )
        db_session.add(balance)
        db_session.commit()

        updated = sync_gocardless_account(db_session, test_bank_account, test_connection)
        db_session.commit()

        assert updated.id == account.id
        assert updated.balance_amount == Decimal("2500.00")
        assert updated.balance_currency == "EUR"
        assert updated.balance_type == "closingAvailable"


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


class TestSyncGocardlessInstitution:
    """Tests for sync_gocardless_institution operation."""

    def test_creates_new_institution(self, db_session: Session) -> None:
        """Should create a new institution from GoCardless data."""
        gc_inst = GoCardlessInstitution(
            id="BANK_GB_TEST",
            name="Test Bank UK",
            bic="TESTGB2L",
            logo="https://cdn.example.com/logo.png",
            countries=["GB", "IE"],
        )
        db_session.add(gc_inst)
        db_session.flush()

        result = sync_gocardless_institution(db_session, gc_inst)
        db_session.commit()

        assert result.id == "BANK_GB_TEST"
        assert result.provider == Provider.GOCARDLESS.value
        assert result.name == "Test Bank UK"
        assert result.logo_url == "https://cdn.example.com/logo.png"
        assert result.countries == ["GB", "IE"]

    def test_updates_existing_institution(self, db_session: Session) -> None:
        """Should update existing institution with new data."""
        # Create existing institution
        existing = Institution(
            id="BANK_GB_UPDATE",
            provider=Provider.GOCARDLESS.value,
            name="Old Name",
            logo_url="https://old.example.com/logo.png",
            countries=["GB"],
        )
        db_session.add(existing)
        db_session.commit()

        # Create GoCardless institution with updated data
        gc_inst = GoCardlessInstitution(
            id="BANK_GB_UPDATE",
            name="New Name",
            logo="https://new.example.com/logo.png",
            countries=["GB", "IE", "US"],
        )
        db_session.add(gc_inst)
        db_session.flush()

        result = sync_gocardless_institution(db_session, gc_inst)
        db_session.commit()

        assert result.id == "BANK_GB_UPDATE"
        assert result.name == "New Name"
        assert result.logo_url == "https://new.example.com/logo.png"
        assert result.countries == ["GB", "IE", "US"]


class TestSyncAllGocardlessInstitutions:
    """Tests for sync_all_gocardless_institutions operation."""

    def test_syncs_all_institutions(self, db_session: Session) -> None:
        """Should sync all GoCardless institutions."""
        # Create multiple GoCardless institutions
        for i in range(3):
            gc_inst = GoCardlessInstitution(
                id=f"BANK_TEST_{i}",
                name=f"Test Bank {i}",
                countries=["GB"],
            )
            db_session.add(gc_inst)
        db_session.commit()

        result = sync_all_gocardless_institutions(db_session)
        db_session.commit()

        assert len(result) == 3
        assert all(inst.provider == Provider.GOCARDLESS.value for inst in result)

    def test_returns_empty_when_no_institutions(self, db_session: Session) -> None:
        """Should return empty list when no GoCardless institutions exist."""
        result = sync_all_gocardless_institutions(db_session)

        assert result == []


class TestSyncGocardlessTransaction:
    """Tests for sync_gocardless_transaction operation."""

    def test_creates_new_transaction(
        self,
        db_session: Session,
        test_account: Account,
    ) -> None:
        """Should create a new transaction from GoCardless data."""
        gc_txn = GoCardlessTransaction(
            account_id=test_account.provider_id,
            transaction_id="txn-001",
            booking_date=date(2024, 1, 15),
            value_date=date(2024, 1, 15),
            transaction_amount=Decimal("-50.00"),
            currency="GBP",
            creditor_name="Test Shop",
            creditor_account="GB00CRED12345678",
            remittance_information="Purchase at Test Shop",
            status="booked",
            extracted_at=datetime.now(UTC),
        )
        db_session.add(gc_txn)
        db_session.flush()

        result = sync_gocardless_transaction(db_session, gc_txn, test_account)
        db_session.commit()

        assert result.account_id == test_account.id
        assert result.provider_id == "txn-001"
        assert result.amount == Decimal("-50.00")
        assert result.currency == "GBP"
        # Negative amount means outgoing -> creditor_name used
        assert result.counterparty_name == "Test Shop"
        assert result.counterparty_account == "GB00CRED12345678"

    def test_creates_incoming_transaction_uses_debtor(
        self,
        db_session: Session,
        test_account: Account,
    ) -> None:
        """Should use debtor info for incoming (positive) transactions."""
        gc_txn = GoCardlessTransaction(
            account_id=test_account.provider_id,
            transaction_id="txn-002",
            booking_date=date(2024, 1, 16),
            transaction_amount=Decimal("100.00"),
            currency="GBP",
            debtor_name="Employer Ltd",
            debtor_account="GB00DEBT87654321",
            remittance_information="Salary payment",
            status="booked",
            extracted_at=datetime.now(UTC),
        )
        db_session.add(gc_txn)
        db_session.flush()

        result = sync_gocardless_transaction(db_session, gc_txn, test_account)
        db_session.commit()

        assert result.amount == Decimal("100.00")
        # Positive amount means incoming -> debtor_name used
        assert result.counterparty_name == "Employer Ltd"
        assert result.counterparty_account == "GB00DEBT87654321"

    def test_updates_existing_transaction(
        self,
        db_session: Session,
        test_account: Account,
    ) -> None:
        """Should update existing transaction when syncing again."""
        # Create initial transaction
        gc_txn = GoCardlessTransaction(
            account_id=test_account.provider_id,
            transaction_id="txn-003",
            booking_date=date(2024, 1, 17),
            transaction_amount=Decimal("-25.00"),
            currency="GBP",
            creditor_name="Original Shop",
            remittance_information="Original description",
            status="booked",
            extracted_at=datetime.now(UTC),
        )
        db_session.add(gc_txn)
        db_session.flush()

        txn1 = sync_gocardless_transaction(db_session, gc_txn, test_account)
        db_session.commit()
        original_id = txn1.id

        # Update the GoCardless transaction
        gc_txn.creditor_name = "Updated Shop"
        gc_txn.remittance_information = "Updated description"
        db_session.flush()

        txn2 = sync_gocardless_transaction(db_session, gc_txn, test_account)
        db_session.commit()

        # Should be same record, updated
        assert txn2.id == original_id
        assert txn2.counterparty_name == "Updated Shop"
        assert txn2.description == "Updated description"

    def test_handles_booking_datetime(
        self,
        db_session: Session,
        test_account: Account,
    ) -> None:
        """Should use booking_datetime when available over booking_date."""
        booking_dt = datetime(2024, 1, 18, 14, 30, 0, tzinfo=UTC)
        gc_txn = GoCardlessTransaction(
            account_id=test_account.provider_id,
            transaction_id="txn-004",
            booking_date=date(2024, 1, 18),
            booking_datetime=booking_dt,
            transaction_amount=Decimal("-10.00"),
            currency="GBP",
            status="booked",
            extracted_at=datetime.now(UTC),
        )
        db_session.add(gc_txn)
        db_session.flush()

        result = sync_gocardless_transaction(db_session, gc_txn, test_account)
        db_session.commit()

        # Compare without timezone (SQLite doesn't preserve timezone info)
        assert result.booking_date is not None
        assert result.booking_date.year == 2024
        assert result.booking_date.month == 1
        assert result.booking_date.day == 18
        assert result.booking_date.hour == 14
        assert result.booking_date.minute == 30


class TestSyncAllGocardlessTransactions:
    """Tests for sync_all_gocardless_transactions operation."""

    def test_syncs_all_transactions_for_account(
        self,
        db_session: Session,
        test_account: Account,
    ) -> None:
        """Should sync all GoCardless transactions for an account."""
        # Create multiple transactions
        for i in range(3):
            gc_txn = GoCardlessTransaction(
                account_id=test_account.provider_id,
                transaction_id=f"txn-sync-{i}",
                booking_date=date(2024, 1, 15 + i),
                transaction_amount=Decimal(f"-{10 + i}.00"),
                currency="GBP",
                status="booked",
                extracted_at=datetime.now(UTC),
            )
            db_session.add(gc_txn)
        db_session.commit()

        result = sync_all_gocardless_transactions(db_session, test_account)
        db_session.commit()

        assert len(result) == 3

    def test_returns_empty_when_no_transactions(
        self,
        db_session: Session,
        test_account: Account,
    ) -> None:
        """Should return empty list when no transactions exist."""
        result = sync_all_gocardless_transactions(db_session, test_account)

        assert result == []


class TestSyncAllGocardlessAccounts:
    """Tests for sync_all_gocardless_accounts operation."""

    def test_syncs_all_accounts_for_connection(
        self,
        db_session: Session,
        test_connection: Connection,
        test_requisition_link: RequisitionLink,
    ) -> None:
        """Should sync all bank accounts for a connection."""
        # Ensure connection points to the requisition
        test_connection.provider_id = test_requisition_link.id
        db_session.commit()

        # Create multiple bank accounts for the requisition
        for i in range(2):
            bank_acc = BankAccount(
                id=f"bank-acc-{i}",
                requisition_id=test_requisition_link.id,
                status="READY",
                currency="GBP",
                name=f"Account {i}",
            )
            db_session.add(bank_acc)
        db_session.commit()

        result = sync_all_gocardless_accounts(db_session, test_connection)
        db_session.commit()

        assert len(result) == 2

    def test_returns_empty_when_no_bank_accounts(
        self,
        db_session: Session,
        test_connection: Connection,
    ) -> None:
        """Should return empty list when no bank accounts exist."""
        # Set provider_id to a requisition with no accounts
        test_connection.provider_id = "no-accounts-req"
        db_session.commit()

        result = sync_all_gocardless_accounts(db_session, test_connection)

        assert result == []
