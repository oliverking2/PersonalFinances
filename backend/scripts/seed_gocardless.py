"""Seed script to fetch all GoCardless data into raw tables.

Usage:
    cd backend
    poetry run seed-gocardless

This script fetches:
1. Institutions (gc_institutions)
2. Requisitions (gc_requisition_links)
3. Bank accounts (gc_bank_accounts)
4. Balances (gc_balances)
5. Transactions (gc_transactions) - last 90 days
6. End user agreements (gc_end_user_agreements)
"""

from datetime import datetime, timedelta

from dotenv import load_dotenv

from src.postgres.core import create_session
from src.postgres.gocardless.models import RequisitionLink
from src.postgres.gocardless.operations.agreements import upsert_agreement
from src.postgres.gocardless.operations.balances import upsert_balances
from src.postgres.gocardless.operations.bank_accounts import upsert_bank_accounts
from src.postgres.gocardless.operations.institutions import upsert_institutions
from src.postgres.gocardless.operations.requisitions import add_requisition_link
from src.postgres.gocardless.operations.transactions import upsert_transactions
from src.providers.gocardless.api.account import (
    get_account_metadata_by_id,
    get_balance_data_by_id,
    get_transaction_data_by_id,
)
from src.providers.gocardless.api.agreements import get_all_agreements
from src.providers.gocardless.api.core import GoCardlessCredentials
from src.providers.gocardless.api.institutions import get_institutions
from src.providers.gocardless.api.requisition import get_all_requisition_data
from src.utils.definitions import gocardless_database_url


def main() -> None:  # noqa: PLR0915
    """Run the GoCardless seed process."""
    load_dotenv()

    print("=" * 60)
    print("GoCardless Seed Script")
    print("=" * 60)
    print()

    # Transaction date range (last 90 days)
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    creds = GoCardlessCredentials()
    session = create_session(gocardless_database_url())

    try:
        # Step 1: Fetch institutions
        print("Step 1: Fetching institutions...")
        institutions = get_institutions(creds)
        count = upsert_institutions(session, institutions)
        session.commit()
        print(f"  Upserted {count} institutions")
        print()

        # Step 2: Fetch requisitions and accounts
        print("Step 2: Fetching requisitions and accounts...")
        requisitions = get_all_requisition_data(creds)
        print(f"  Found {len(requisitions)} requisitions")

        total_accounts = 0
        total_balances = 0
        total_transactions = 0

        for requisition in requisitions:
            requisition_id = requisition["id"]

            # Upsert requisition
            link = session.get(RequisitionLink, requisition_id)
            if link is None:
                friendly_name = requisition.get("institution_id", "Unknown")
                add_requisition_link(session, requisition, friendly_name)
                print(f"  Created requisition: {requisition_id}")

            # Fetch and upsert accounts
            account_ids = requisition.get("accounts", [])
            detailed_accounts = []
            for acct_id in account_ids:
                info = get_account_metadata_by_id(creds, acct_id)
                detailed_accounts.append(info)
            upsert_bank_accounts(session, requisition_id, detailed_accounts)
            total_accounts += len(detailed_accounts)

            # Fetch balances and transactions for each account
            for acct_id in account_ids:
                try:
                    # Fetch balances
                    balance_data = get_balance_data_by_id(creds, acct_id)
                    balance_count = upsert_balances(session, acct_id, balance_data)
                    total_balances += balance_count
                except Exception as e:
                    print(f"  Warning: Could not fetch balances for {acct_id}: {e}")

                try:
                    # Fetch transactions (last 90 days)
                    txn_data = get_transaction_data_by_id(creds, acct_id, date_from, date_to)
                    txn_count = upsert_transactions(session, acct_id, txn_data)
                    total_transactions += txn_count
                except Exception as e:
                    print(f"  Warning: Could not fetch transactions for {acct_id}: {e}")

        session.commit()
        print(f"  Upserted {total_accounts} accounts")
        print(f"  Upserted {total_balances} balances")
        print(f"  Upserted {total_transactions} transactions")
        print()

        # Step 3: Fetch agreements
        print("Step 3: Fetching end user agreements...")
        agreements = get_all_agreements(creds)
        for agreement in agreements:
            upsert_agreement(session, agreement)
        session.commit()
        print(f"  Upserted {len(agreements)} agreements")
        print()

        # Summary
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Institutions: {count}")
        print(f"Requisitions: {len(requisitions)}")
        print(f"Accounts: {total_accounts}")
        print(f"Balances: {total_balances}")
        print(f"Transactions: {total_transactions}")
        print(f"Agreements: {len(agreements)}")
        print()
        print("GoCardless data seeded successfully.")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
