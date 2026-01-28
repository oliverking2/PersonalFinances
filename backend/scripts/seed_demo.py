"""Seed script to create a demo user with fake data.

Usage:
    cd backend
    poetry run seed-demo

This script creates:
1. Demo user (username: "demo", password: "demopassword123")
2. Fake institutions (no GoCardless dependency)
3. Fake connections
4. Fake accounts with balances
5. Fake transactions

Useful for demos, UI testing, and CI/CD without real bank data.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import choice, randint, uniform
from uuid import UUID, uuid4

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from src.postgres.auth.operations.users import create_user, get_user_by_username
from src.postgres.common.enums import AccountStatus, AccountType, ConnectionStatus, Provider
from src.postgres.common.models import Account, Connection, Institution, Transaction
from src.postgres.core import create_session
from src.utils.definitions import gocardless_database_url

# Demo user credentials
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demopassword123"
DEMO_FIRST_NAME = "Demo"
DEMO_LAST_NAME = "User"

# Fake institutions
FAKE_INSTITUTIONS = [
    {
        "id": "DEMO_BANK_001",
        "name": "Demo Bank",
        "logo_url": "https://placehold.co/100x100/2563eb/white?text=DB",
        "countries": ["GB"],
    },
    {
        "id": "DEMO_SAVINGS_002",
        "name": "Demo Savings",
        "logo_url": "https://placehold.co/100x100/16a34a/white?text=DS",
        "countries": ["GB"],
    },
    {
        "id": "DEMO_CREDIT_003",
        "name": "Demo Credit",
        "logo_url": "https://placehold.co/100x100/dc2626/white?text=DC",
        "countries": ["GB"],
    },
]

# Transaction templates for realistic-looking data
INCOME_TRANSACTIONS = [
    ("ACME Corp", "Monthly Salary"),
    ("Freelance Client", "Invoice Payment"),
    ("Tax Refund", "HMRC Refund"),
    ("Interest", "Monthly Interest"),
]

EXPENSE_TRANSACTIONS = [
    ("Tesco", "Groceries"),
    ("Amazon", "Online Shopping"),
    ("Netflix", "Subscription"),
    ("Spotify", "Subscription"),
    ("British Gas", "Utilities"),
    ("Thames Water", "Utilities"),
    ("TfL", "Transport"),
    ("Costa Coffee", "Coffee"),
    ("Uber Eats", "Food Delivery"),
    ("Sainsburys", "Groceries"),
    ("EE Mobile", "Phone Bill"),
    ("Sky", "TV & Internet"),
    ("Gym Membership", "Health & Fitness"),
    ("Shell", "Petrol"),
    ("Boots", "Pharmacy"),
]

# Probability of income vs expense transactions
INCOME_PROBABILITY = 0.2


def main() -> None:  # noqa: PLR0915
    """Run the demo seed process."""
    load_dotenv()

    print("=" * 60)
    print("Demo User Seed Script")
    print("=" * 60)
    print()

    session = create_session(gocardless_database_url())

    try:
        # Step 1: Create demo user
        print("Step 1: Creating demo user...")
        user = get_user_by_username(session, DEMO_USERNAME)
        if user:
            print(f"  Found existing demo user: id={user.id}")
        else:
            user = create_user(
                session,
                username=DEMO_USERNAME,
                password=DEMO_PASSWORD,
                first_name=DEMO_FIRST_NAME,
                last_name=DEMO_LAST_NAME,
            )
            session.commit()
            print(f"  Created demo user: id={user.id}")
        print()

        # Step 2: Create fake institutions
        print("Step 2: Creating fake institutions...")
        for inst_data in FAKE_INSTITUTIONS:
            existing = session.get(Institution, inst_data["id"])
            if existing:
                print(f"  Institution already exists: {inst_data['name']}")
                continue

            institution = Institution(
                id=inst_data["id"],
                provider=Provider.GOCARDLESS.value,  # Use gocardless as provider
                name=inst_data["name"],
                logo_url=inst_data["logo_url"],
                countries=inst_data["countries"],
            )
            session.add(institution)
            print(f"  Created institution: {inst_data['name']}")
        session.commit()
        print()

        # Step 3: Create fake connections and accounts
        print("Step 3: Creating connections and accounts...")
        accounts_created = []

        # Current Account at Demo Bank
        _, acct1 = _create_connection_and_account(
            session,
            user_id=user.id,
            institution_id="DEMO_BANK_001",
            friendly_name="Main Current Account",
            account_name="Demo Bank Current",
            iban="GB82DEMO12345678901234",
            balance=Decimal("2847.52"),
            currency="GBP",
        )
        if acct1:
            accounts_created.append(("Current Account", acct1))

        # Savings Account
        _, acct2 = _create_connection_and_account(
            session,
            user_id=user.id,
            institution_id="DEMO_SAVINGS_002",
            friendly_name="Savings Account",
            account_name="Demo Savings ISA",
            iban="GB82DEMO12345678905678",
            balance=Decimal("15420.00"),
            currency="GBP",
        )
        if acct2:
            accounts_created.append(("Savings Account", acct2))

        # Credit Card
        _, acct3 = _create_connection_and_account(
            session,
            user_id=user.id,
            institution_id="DEMO_CREDIT_003",
            friendly_name="Credit Card",
            account_name="Demo Credit Card",
            iban=None,
            balance=Decimal("-1234.56"),  # Negative for credit card
            currency="GBP",
        )
        if acct3:
            accounts_created.append(("Credit Card", acct3))

        session.commit()
        print()

        # Step 4: Create fake transactions
        print("Step 4: Creating fake transactions...")
        total_transactions = 0

        for account_name, account in accounts_created:
            txn_count = _create_fake_transactions(session, account)
            total_transactions += txn_count
            print(f"  Created {txn_count} transactions for {account_name}")

        session.commit()
        print()

        # Summary
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Demo user: {DEMO_USERNAME} / {DEMO_PASSWORD}")
        print(f"Institutions: {len(FAKE_INSTITUTIONS)}")
        print(f"Accounts: {len(accounts_created)}")
        print(f"Transactions: {total_transactions}")
        print()
        print("Demo data seeded successfully.")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def _create_connection_and_account(
    session: Session,
    user_id: UUID,
    institution_id: str,
    friendly_name: str,
    account_name: str,
    iban: str | None,
    balance: Decimal,
    currency: str,
) -> tuple[Connection | None, Account | None]:
    """Create a connection and account if they don't exist."""
    # Check if connection already exists for this user/institution
    existing_conn = (
        session.query(Connection)
        .filter(
            Connection.user_id == user_id,
            Connection.institution_id == institution_id,
        )
        .first()
    )

    if existing_conn:
        print(f"  Connection already exists: {friendly_name}")
        # Check if account exists
        existing_acct = (
            session.query(Account).filter(Account.connection_id == existing_conn.id).first()
        )
        return existing_conn, existing_acct

    # Create connection
    connection = Connection(
        id=uuid4(),
        user_id=user_id,
        provider=Provider.GOCARDLESS.value,
        provider_id=f"demo_{institution_id}_{user_id}",
        institution_id=institution_id,
        friendly_name=friendly_name,
        status=ConnectionStatus.ACTIVE.value,
        created_at=datetime.now(UTC) - timedelta(days=30),
        synced_at=datetime.now(UTC),
    )
    session.add(connection)
    session.flush()
    print(f"  Created connection: {friendly_name}")

    # Create account
    account = Account(
        id=uuid4(),
        connection_id=connection.id,
        provider_id=f"demo_acct_{institution_id}",
        account_type=AccountType.BANK.value,
        name=account_name,
        iban=iban,
        currency=currency,
        status=AccountStatus.ACTIVE.value,
        balance_amount=balance,
        balance_currency=currency,
        balance_type="interimAvailable",
        balance_updated_at=datetime.now(UTC),
        synced_at=datetime.now(UTC),
    )
    session.add(account)
    session.flush()
    print(f"  Created account: {account_name}")

    return connection, account


def _create_fake_transactions(
    session: Session, account: Account, num_transactions: int = 50
) -> int:
    """Create fake transactions for an account."""
    # Check if transactions already exist
    existing_count = session.query(Transaction).filter(Transaction.account_id == account.id).count()
    if existing_count > 0:
        return 0

    now = datetime.now(UTC)
    transactions_created = 0

    for i in range(num_transactions):
        # Random date in last 90 days
        days_ago = randint(0, 90)
        txn_date = now - timedelta(days=days_ago)

        # 20% chance of income, 80% expense
        if uniform(0, 1) < INCOME_PROBABILITY:
            counterparty, description = choice(INCOME_TRANSACTIONS)
            amount = Decimal(str(round(uniform(100, 3000), 2)))
        else:
            counterparty, description = choice(EXPENSE_TRANSACTIONS)
            amount = Decimal(str(round(uniform(-150, -5), 2)))

        transaction = Transaction(
            id=uuid4(),
            account_id=account.id,
            provider_id=f"demo_txn_{account.id}_{i}",
            booking_date=txn_date,
            value_date=txn_date,
            amount=amount,
            currency=account.currency or "GBP",
            counterparty_name=counterparty,
            description=description,
            synced_at=now,
        )
        session.add(transaction)
        transactions_created += 1

    session.flush()
    return transactions_created


if __name__ == "__main__":
    main()
