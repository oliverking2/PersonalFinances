"""Seed script to create a development user and link existing GoCardless data.

Usage:
    cd backend
    poetry run seed-dev

This script:
1. Creates a dev user (username: "dev", password: "devpassword123") if not exists
2. Links existing RequisitionLinks to the dev user via Connection records
3. Syncs accounts from gc_bank_accounts to the unified accounts table
4. Syncs transactions from gc_transactions to the unified transactions table

This allows testing the full flow with real bank data that was previously
pulled via the GoCardless seed script.
"""

from datetime import UTC, datetime

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.auth.operations.users import create_user, get_user_by_username
from src.postgres.common.enums import ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.common.operations.connections import (
    create_connection,
    get_connection_by_provider_id,
)
from src.postgres.common.operations.institutions import upsert_institution
from src.postgres.common.operations.sync import (
    sync_all_gocardless_accounts,
    sync_all_gocardless_transactions,
)
from src.postgres.core import create_session
from src.postgres.gocardless.models import GoCardlessInstitution, RequisitionLink
from src.utils.definitions import gocardless_database_url

# Dev user credentials
DEV_USERNAME = "dev"
DEV_PASSWORD = "devpassword123"
DEV_FIRST_NAME = "Dev"
DEV_LAST_NAME = "User"


def get_or_create_dev_user(session: Session) -> User:
    """Get or create the development user.

    :param session: SQLAlchemy session.
    :returns: The dev user.
    """
    user = get_user_by_username(session, DEV_USERNAME)
    if user:
        print(f"Found existing dev user: id={user.id}")
        return user

    user = create_user(
        session,
        username=DEV_USERNAME,
        password=DEV_PASSWORD,
        first_name=DEV_FIRST_NAME,
        last_name=DEV_LAST_NAME,
    )
    session.commit()
    print(f"Created dev user: id={user.id}, username={DEV_USERNAME}")
    return user


def ensure_institution_exists(session: Session, institution_id: str) -> Institution | None:
    """Ensure an institution exists in the unified table.

    First checks gc_institutions for the raw data, then upserts to institutions.

    :param session: SQLAlchemy session.
    :param institution_id: GoCardless institution ID.
    :returns: The Institution, or None if not found in gc_institutions.
    """
    # Check if it already exists in unified table
    existing = session.get(Institution, institution_id)
    if existing:
        return existing

    # Try to get from GoCardless raw table
    gc_inst = session.get(GoCardlessInstitution, institution_id)
    if not gc_inst:
        print(f"  Warning: Institution {institution_id} not found in gc_institutions")
        return None

    # Create in unified table
    institution = upsert_institution(
        session,
        institution_id=gc_inst.id,
        provider=Provider.GOCARDLESS,
        name=gc_inst.name,
        logo_url=gc_inst.logo,
        countries=gc_inst.countries,
    )
    print(f"  Created institution: id={institution_id}, name={gc_inst.name}")
    return institution


def link_requisitions_to_user(session: Session, user: User) -> int:
    """Link existing RequisitionLinks to the dev user via Connection records.

    :param session: SQLAlchemy session.
    :param user: The user to link requisitions to.
    :returns: Number of connections created.
    """
    # Get all requisitions
    requisitions = session.query(RequisitionLink).all()
    print(f"Found {len(requisitions)} requisition links")

    created_count = 0
    for req in requisitions:
        # Check if a connection already exists for this requisition
        existing = get_connection_by_provider_id(session, Provider.GOCARDLESS, req.id)
        if existing:
            print(f"  Requisition {req.id} already linked to connection {existing.id}")
            continue

        # Ensure institution exists
        institution = ensure_institution_exists(session, req.institution_id)
        if not institution:
            print(f"  Skipping requisition {req.id}: institution not found")
            continue

        # Map GoCardless status to ConnectionStatus
        if req.status == "LN":
            status = ConnectionStatus.ACTIVE
        elif req.status in ("EX", "RJ", "SA", "GA"):
            status = ConnectionStatus.EXPIRED
        else:
            status = ConnectionStatus.PENDING

        # Create connection
        connection = create_connection(
            session=session,
            user_id=user.id,
            provider=Provider.GOCARDLESS,
            provider_id=req.id,
            institution_id=req.institution_id,
            friendly_name=req.friendly_name or f"Connection - {institution.name}",
            status=status,
            created_at=req.created or datetime.now(UTC),
        )
        print(
            f"  Created connection: id={connection.id}, requisition={req.id}, status={status.value}"
        )
        created_count += 1

    return created_count


def sync_accounts_for_connections(session: Session) -> int:
    """Sync accounts from gc_bank_accounts for all active connections.

    :param session: SQLAlchemy session.
    :returns: Total number of accounts synced.
    """
    # Get all active GoCardless connections
    connections = (
        session.query(Connection)
        .filter(
            Connection.provider == Provider.GOCARDLESS.value,
            Connection.status == ConnectionStatus.ACTIVE.value,
        )
        .all()
    )

    print(f"Found {len(connections)} active connections to sync accounts for")

    total_accounts = 0
    for connection in connections:
        accounts = sync_all_gocardless_accounts(session, connection)
        if accounts:
            print(f"  Synced {len(accounts)} accounts for connection {connection.id}")
            total_accounts += len(accounts)

    return total_accounts


def sync_transactions_for_accounts(session: Session) -> int:
    """Sync transactions from gc_transactions for all accounts.

    :param session: SQLAlchemy session.
    :returns: Total number of transactions synced.
    """
    # Get all accounts
    accounts = session.query(Account).all()

    print(f"Found {len(accounts)} accounts to sync transactions for")

    total_transactions = 0
    for account in accounts:
        transactions = sync_all_gocardless_transactions(session, account)
        if transactions:
            print(f"  Synced {len(transactions)} transactions for account {account.id}")
            total_transactions += len(transactions)

    return total_transactions


def main() -> None:  # noqa: PLR0915
    """Run the development user seed process."""
    load_dotenv()

    print("=" * 60)
    print("Development User Seed Script")
    print("=" * 60)
    print()

    # Create database session
    session = create_session(gocardless_database_url())

    try:
        # Step 1: Create/get dev user
        print("Step 1: Creating/getting dev user...")
        user = get_or_create_dev_user(session)
        print()

        # Step 2: Link requisitions to user (if any exist)
        print("Step 2: Linking requisitions to user...")
        connections_created = link_requisitions_to_user(session, user)
        session.commit()
        if connections_created > 0:
            print(f"Created {connections_created} new connections")
        else:
            print("No requisitions found to link (run 'make seed-gocardless' first)")
        print()

        # Step 3: Sync accounts (if any connections exist)
        print("Step 3: Syncing accounts from gc_bank_accounts...")
        accounts_synced = sync_accounts_for_connections(session)
        session.commit()
        if accounts_synced > 0:
            print(f"Synced {accounts_synced} accounts")
        else:
            print("No accounts to sync")
        print()

        # Step 4: Sync transactions (if any accounts exist)
        print("Step 4: Syncing transactions from gc_transactions...")
        transactions_synced = sync_transactions_for_accounts(session)
        session.commit()
        if transactions_synced > 0:
            print(f"Synced {transactions_synced} transactions")
        else:
            print("No transactions to sync")
        print()

        # Summary
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Dev user: {DEV_USERNAME} / {DEV_PASSWORD}")
        print(f"Connections created: {connections_created}")
        print(f"Accounts synced: {accounts_synced}")
        print(f"Transactions synced: {transactions_synced}")
        print()
        print("You can now log in with the dev user credentials.")
        if connections_created == 0:
            print()
            print("Tip: Run 'make seed-gocardless' to fetch bank data, then")
            print("     run 'make seed-dev' again to link it to the dev user.")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
