"""Seed script to create a demo user with comprehensive data.

Usage:
    cd backend
    poetry run seed-demo

This script creates:
1. Demo user (username: "demo", password: "demopassword123")
2. Fake institutions (no GoCardless dependency)
3. Fake connections and accounts
4. Fake transactions with tags
5. Budgets with various states (on-track, warning, exceeded)
6. Recurring patterns (subscriptions, salary, bills)
7. Manual assets and liabilities with historical snapshots
8. Savings goals with different tracking modes
9. Financial milestones
10. Planned transactions (one-time and recurring)
11. Tag rules for auto-tagging

Useful for demos, UI testing, and CI/CD without real bank data.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from random import choice, randint, uniform
from uuid import UUID, uuid4

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from src.postgres.auth.operations.users import create_user, get_user_by_username
from src.postgres.common.enums import (
    AccountStatus,
    AccountType,
    BudgetPeriod,
    ConnectionStatus,
    GoalStatus,
    GoalTrackingMode,
    ManualAssetType,
    Provider,
    RecurringDirection,
    RecurringFrequency,
    RecurringSource,
    RecurringStatus,
)
from src.postgres.common.models import (
    Account,
    Budget,
    Connection,
    FinancialMilestone,
    Institution,
    ManualAsset,
    ManualAssetValueSnapshot,
    Notification,
    PlannedTransaction,
    RecurringPattern,
    SavingsGoal,
    Tag,
    TagRule,
    Transaction,
    TransactionSplit,
)
from src.postgres.common.operations.tags import seed_standard_tags
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

# Transaction templates with tag mapping: (counterparty, description, tag_name)
INCOME_TRANSACTIONS = [
    ("ACME Corp", "Monthly Salary", "Income"),
    ("Freelance Client", "Invoice Payment", "Income"),
    ("Tax Refund", "HMRC Refund", "Income"),
    ("Interest", "Monthly Interest", "Income"),
]

EXPENSE_TRANSACTIONS = [
    ("Tesco", "Groceries", "Groceries"),
    ("Sainsburys", "Groceries", "Groceries"),
    ("Amazon", "Online Shopping", "Shopping"),
    ("Netflix", "Subscription", "Subscriptions"),
    ("Spotify", "Subscription", "Subscriptions"),
    ("British Gas", "Utilities", "Utilities"),
    ("Thames Water", "Utilities", "Utilities"),
    ("TfL", "Transport", "Transport"),
    ("Costa Coffee", "Coffee", "Dining"),
    ("Uber Eats", "Food Delivery", "Dining"),
    ("EE Mobile", "Phone Bill", "Utilities"),
    ("Sky", "TV & Internet", "Subscriptions"),
    ("Gym Membership", "Health & Fitness", "Health"),
    ("Shell", "Petrol", "Transport"),
    ("Boots", "Pharmacy", "Health"),
]

# Probability of income vs expense transactions
INCOME_PROBABILITY = 0.2


def _clear_demo_data(session: Session, user_id: UUID) -> dict[str, int]:
    """Remove all existing data for the demo user.

    Deletes in dependency order to respect foreign key constraints.
    Returns counts of deleted records for logging.
    """
    counts: dict[str, int] = {}

    # Get account IDs for this user (needed for transaction deletion)
    account_ids = [
        acc.id
        for acc in session.query(Account.id)
        .join(Connection)
        .filter(Connection.user_id == user_id)
        .all()
    ]

    # Delete transactions and their splits (via cascade)
    if account_ids:
        counts["transactions"] = (
            session.query(Transaction).filter(Transaction.account_id.in_(account_ids)).delete()
        )

    # Delete these BEFORE accounts (they have account_id FKs with SET NULL or check constraints)
    counts["savings_goals"] = (
        session.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).delete()
    )
    counts["recurring_patterns"] = (
        session.query(RecurringPattern).filter(RecurringPattern.user_id == user_id).delete()
    )
    counts["planned_transactions"] = (
        session.query(PlannedTransaction).filter(PlannedTransaction.user_id == user_id).delete()
    )

    # Delete connections (cascades to accounts)
    counts["connections"] = session.query(Connection).filter(Connection.user_id == user_id).delete()

    # Delete budgets
    counts["budgets"] = session.query(Budget).filter(Budget.user_id == user_id).delete()

    # Delete tag rules
    counts["tag_rules"] = session.query(TagRule).filter(TagRule.user_id == user_id).delete()

    # Delete manual assets (cascades to value snapshots)
    counts["manual_assets"] = (
        session.query(ManualAsset).filter(ManualAsset.user_id == user_id).delete()
    )

    # Delete milestones
    counts["milestones"] = (
        session.query(FinancialMilestone).filter(FinancialMilestone.user_id == user_id).delete()
    )

    # Delete notifications
    counts["notifications"] = (
        session.query(Notification).filter(Notification.user_id == user_id).delete()
    )

    # Delete tags (will be re-seeded)
    counts["tags"] = session.query(Tag).filter(Tag.user_id == user_id).delete()

    session.flush()
    return counts


def main() -> None:  # noqa: PLR0915
    """Run the demo seed process."""
    load_dotenv()

    print("=" * 60)
    print("Demo User Seed Script")
    print("=" * 60)
    print()

    session = create_session(gocardless_database_url())

    try:
        # Step 1: Create or find demo user
        print("Step 1: Creating demo user...")
        user = get_user_by_username(session, DEMO_USERNAME)
        if user:
            print(f"  Found existing demo user: id={user.id}")
            # Clear existing demo data for a fresh start
            print("  Clearing existing demo data...")
            counts = _clear_demo_data(session, user.id)
            session.commit()
            for entity, count in counts.items():
                if count > 0:
                    print(f"    Deleted {count} {entity.replace('_', ' ')}")
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
                provider=Provider.GOCARDLESS.value,
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
        accounts_created: list[tuple[str, Account]] = []

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
            balance=Decimal("-1234.56"),
            currency="GBP",
        )
        if acct3:
            accounts_created.append(("Credit Card", acct3))

        session.commit()
        print()

        # Step 4: Ensure standard tags exist and get lookup
        print("Step 4: Ensuring standard tags...")
        tag_lookup = _get_or_seed_tags(session, user.id)
        session.commit()
        print(f"  Tags available: {len(tag_lookup)}")
        print()

        # Step 5: Create fake transactions with tags
        print("Step 5: Creating tagged transactions...")
        total_transactions = 0

        for account_name, account in accounts_created:
            txn_count = _create_fake_transactions(session, account, tag_lookup)
            total_transactions += txn_count
            print(f"  Created {txn_count} transactions for {account_name}")

        session.commit()
        print()

        # Step 6: Create budgets
        print("Step 6: Creating budgets...")
        budgets = _create_budgets(session, user.id, tag_lookup)
        session.commit()
        print(f"  Created {len(budgets)} budgets")
        print()

        # Step 7: Create recurring patterns
        print("Step 7: Creating recurring patterns...")
        current_account = accounts_created[0][1] if accounts_created else None
        patterns = _create_recurring_patterns(
            session,
            user.id,
            current_account.id if current_account else None,
            tag_lookup,
        )
        session.commit()
        print(f"  Created {len(patterns)} recurring patterns")
        print()

        # Step 8: Create tag rules
        print("Step 8: Creating tag rules...")
        rules = _create_tag_rules(session, user.id, tag_lookup)
        session.commit()
        print(f"  Created {len(rules)} tag rules")
        print()

        # Step 9: Create manual assets
        print("Step 9: Creating manual assets...")
        assets = _create_manual_assets(session, user.id)
        session.commit()
        print(f"  Created {len(assets)} manual assets with historical snapshots")
        print()

        # Step 10: Create savings goals
        print("Step 10: Creating savings goals...")
        savings_account = accounts_created[1][1] if len(accounts_created) > 1 else None
        goals = _create_savings_goals(
            session,
            user.id,
            savings_account.id if savings_account else None,
        )
        session.commit()
        print(f"  Created {len(goals)} savings goals")
        print()

        # Step 11: Create milestones
        print("Step 11: Creating milestones...")
        milestones = _create_milestones(session, user.id)
        session.commit()
        print(f"  Created {len(milestones)} milestones")
        print()

        # Step 12: Create planned transactions
        print("Step 12: Creating planned transactions...")
        planned = _create_planned_transactions(
            session,
            user.id,
            current_account.id if current_account else None,
        )
        session.commit()
        print(f"  Created {len(planned)} planned transactions")
        print()

        # Summary
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Demo user: {DEMO_USERNAME} / {DEMO_PASSWORD}")
        print(f"Institutions: {len(FAKE_INSTITUTIONS)}")
        print(f"Accounts: {len(accounts_created)}")
        print(f"Transactions: {total_transactions}")
        print(f"Budgets: {len(budgets)}")
        print(f"Recurring patterns: {len(patterns)}")
        print(f"Tag rules: {len(rules)}")
        print(f"Manual assets: {len(assets)}")
        print(f"Savings goals: {len(goals)}")
        print(f"Milestones: {len(milestones)}")
        print(f"Planned transactions: {len(planned)}")
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
        existing_acct = (
            session.query(Account).filter(Account.connection_id == existing_conn.id).first()
        )
        return existing_conn, existing_acct

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


def _get_or_seed_tags(session: Session, user_id: UUID) -> dict[str, UUID]:
    """Ensure standard tags exist and return a lookup dict by name."""
    existing_tags = session.query(Tag).filter(Tag.user_id == user_id).all()

    if not existing_tags:
        seed_standard_tags(session, user_id)
        session.flush()
        existing_tags = session.query(Tag).filter(Tag.user_id == user_id).all()

    return {tag.name: tag.id for tag in existing_tags}


def _create_fake_transactions(
    session: Session,
    account: Account,
    tag_lookup: dict[str, UUID],
    num_transactions: int = 50,
) -> int:
    """Create fake transactions for an account with tag splits."""
    existing_count = session.query(Transaction).filter(Transaction.account_id == account.id).count()
    if existing_count > 0:
        return 0

    now = datetime.now(UTC)
    today = date.today()
    current_month_start = today.replace(day=1)
    transactions_created = 0

    # Create current month transactions with deterministic amounts for budget calibration
    current_month_txns = _create_current_month_transactions(
        session, account, tag_lookup, now, current_month_start
    )
    transactions_created += current_month_txns

    # Create older transactions (random)
    older_txns_count = num_transactions - current_month_txns
    for i in range(older_txns_count):
        days_ago = randint(31, 90)
        txn_date = now - timedelta(days=days_ago)

        if uniform(0, 1) < INCOME_PROBABILITY:
            counterparty, description, tag_name = choice(INCOME_TRANSACTIONS)
            amount = Decimal(str(round(uniform(100, 3000), 2)))
        else:
            counterparty, description, tag_name = choice(EXPENSE_TRANSACTIONS)
            amount = Decimal(str(round(uniform(-150, -5), 2)))

        transaction = Transaction(
            id=uuid4(),
            account_id=account.id,
            provider_id=f"demo_txn_{account.id}_{i}_old",
            booking_date=txn_date,
            value_date=txn_date,
            amount=amount,
            currency=account.currency or "GBP",
            counterparty_name=counterparty,
            description=description,
            synced_at=now,
        )
        session.add(transaction)
        session.flush()

        # Add tag split
        tag_id = tag_lookup.get(tag_name)
        if tag_id:
            split = TransactionSplit(
                id=uuid4(),
                transaction_id=transaction.id,
                tag_id=tag_id,
                amount=abs(amount),
                is_auto=True,
            )
            session.add(split)

        transactions_created += 1

    session.flush()
    return transactions_created


def _create_current_month_transactions(
    session: Session,
    account: Account,
    tag_lookup: dict[str, UUID],
    now: datetime,
    month_start: date,
) -> int:
    """Create transactions for current month with calibrated amounts for budget demos.

    Spreads transactions across the month (days 1-28) for realistic demo data.
    """
    transactions = []

    def random_date_in_range(max_day: int = 28) -> datetime:
        """Get a random date within the month, capped at max_day."""
        day_offset = randint(0, min(max_day, 27))  # 0-27 = days 1-28
        return datetime.combine(month_start + timedelta(days=day_offset), now.time(), UTC)

    # Groceries: target ~60% of 400 = 240, so 8 transactions averaging 30
    for i in range(8):
        txn_date = random_date_in_range()
        transactions.append(
            _make_transaction(
                account,
                f"demo_txn_{account.id}_groc_{i}",
                txn_date,
                Decimal(str(round(uniform(-35, -25), 2))),
                choice(["Tesco", "Sainsburys", "Aldi", "Lidl"]),
                "Groceries",
                "Groceries",
                now,
            )
        )

    # Dining: target ~85% of 150 = 127.50, so 7 transactions averaging 18
    for i in range(7):
        txn_date = random_date_in_range()
        transactions.append(
            _make_transaction(
                account,
                f"demo_txn_{account.id}_dine_{i}",
                txn_date,
                Decimal(str(round(uniform(-22, -14), 2))),
                choice(["Costa Coffee", "Uber Eats", "Deliveroo", "Pret"]),
                "Food & Drink",
                "Dining",
                now,
            )
        )

    # Subscriptions: target ~120% of 100 = 120 (exceeded!)
    subscription_txns = [
        ("Netflix", Decimal("-15.99")),
        ("Spotify", Decimal("-9.99")),
        ("Sky", Decimal("-45.00")),
        ("Disney+", Decimal("-10.99")),
        ("Amazon Prime", Decimal("-8.99")),
        ("Gym Membership", Decimal("-29.99")),
    ]
    for i, (name, amount) in enumerate(subscription_txns):
        # Subscriptions typically charge early in the month
        txn_date = random_date_in_range(15)
        transactions.append(
            _make_transaction(
                account,
                f"demo_txn_{account.id}_sub_{i}",
                txn_date,
                amount,
                name,
                "Subscription",
                "Subscriptions",
                now,
            )
        )

    # Transport: target ~40% of 200 = 80, so 4 transactions averaging 20
    for i in range(4):
        txn_date = random_date_in_range()
        transactions.append(
            _make_transaction(
                account,
                f"demo_txn_{account.id}_tran_{i}",
                txn_date,
                Decimal(str(round(uniform(-25, -15), 2))),
                choice(["TfL", "Shell", "BP", "Uber"]),
                "Transport",
                "Transport",
                now,
            )
        )

    # Utilities: bills typically early in the month
    utility_txns = [
        ("British Gas", Decimal("-85.00")),
        ("Thames Water", Decimal("-35.00")),
        ("EE Mobile", Decimal("-45.00")),
    ]
    for i, (name, amount) in enumerate(utility_txns):
        txn_date = random_date_in_range(10)
        transactions.append(
            _make_transaction(
                account,
                f"demo_txn_{account.id}_util_{i}",
                txn_date,
                amount,
                name,
                "Utilities",
                "Utilities",
                now,
            )
        )

    # Income: salary on day 25 (only if we're past that date or using last month)
    salary_date = datetime.combine(month_start + timedelta(days=25), now.time(), UTC)
    if salary_date <= now:
        transactions.append(
            _make_transaction(
                account,
                f"demo_txn_{account.id}_salary",
                salary_date,
                Decimal("3500.00"),
                "ACME Corp",
                "Monthly Salary",
                "Income",
                now,
            )
        )

    # Add all transactions and their splits
    for txn_data in transactions:
        txn, tag_name = txn_data
        session.add(txn)
        session.flush()

        tag_id = tag_lookup.get(tag_name)
        if tag_id:
            split = TransactionSplit(
                id=uuid4(),
                transaction_id=txn.id,
                tag_id=tag_id,
                amount=abs(txn.amount),
                is_auto=True,
            )
            session.add(split)

    return len(transactions)


def _make_transaction(
    account: Account,
    provider_id: str,
    txn_date: datetime,
    amount: Decimal,
    counterparty: str,
    description: str,
    tag_name: str,
    now: datetime,
) -> tuple[Transaction, str]:
    """Create a transaction object (not yet added to session)."""
    txn = Transaction(
        id=uuid4(),
        account_id=account.id,
        provider_id=provider_id,
        booking_date=txn_date,
        value_date=txn_date,
        amount=amount,
        currency=account.currency or "GBP",
        counterparty_name=counterparty,
        description=description,
        synced_at=now,
    )
    return txn, tag_name


def _create_budgets(session: Session, user_id: UUID, tag_lookup: dict[str, UUID]) -> list[Budget]:
    """Create demo budgets linked to standard tags."""
    budgets_data = [
        # (tag_name, amount, period, warning_threshold)
        ("Groceries", Decimal("400.00"), BudgetPeriod.MONTHLY, Decimal("0.80")),
        ("Dining", Decimal("150.00"), BudgetPeriod.MONTHLY, Decimal("0.75")),
        ("Subscriptions", Decimal("100.00"), BudgetPeriod.MONTHLY, Decimal("0.80")),
        ("Transport", Decimal("200.00"), BudgetPeriod.MONTHLY, Decimal("0.80")),
    ]

    created = []
    for tag_name, amount, period, warning in budgets_data:
        tag_id = tag_lookup.get(tag_name)
        if not tag_id:
            continue

        # Check if budget already exists
        existing = (
            session.query(Budget).filter(Budget.user_id == user_id, Budget.tag_id == tag_id).first()
        )
        if existing:
            continue

        budget = Budget(
            id=uuid4(),
            user_id=user_id,
            tag_id=tag_id,
            amount=amount,
            currency="GBP",
            period=period.value,
            warning_threshold=warning,
            enabled=True,
        )
        session.add(budget)
        created.append(budget)

    session.flush()
    return created


def _create_recurring_patterns(
    session: Session,
    user_id: UUID,
    account_id: UUID | None,
    tag_lookup: dict[str, UUID],
) -> list[RecurringPattern]:
    """Create demo recurring patterns."""
    now = datetime.now(UTC)

    patterns_data = [
        # (name, amount, direction, frequency, status, tag_name, merchant_contains)
        (
            "Monthly Salary",
            Decimal("3500.00"),
            RecurringDirection.INCOME,
            RecurringFrequency.MONTHLY,
            RecurringStatus.ACTIVE,
            "Income",
            "ACME",
        ),
        (
            "Netflix",
            Decimal("15.99"),
            RecurringDirection.EXPENSE,
            RecurringFrequency.MONTHLY,
            RecurringStatus.ACTIVE,
            "Subscriptions",
            "Netflix",
        ),
        (
            "Spotify",
            Decimal("9.99"),
            RecurringDirection.EXPENSE,
            RecurringFrequency.MONTHLY,
            RecurringStatus.ACTIVE,
            "Subscriptions",
            "Spotify",
        ),
        (
            "Gym Membership",
            Decimal("29.99"),
            RecurringDirection.EXPENSE,
            RecurringFrequency.MONTHLY,
            RecurringStatus.ACTIVE,
            "Health",
            "Gym",
        ),
        (
            "British Gas",
            Decimal("85.00"),
            RecurringDirection.EXPENSE,
            RecurringFrequency.MONTHLY,
            RecurringStatus.PENDING,
            "Utilities",
            "British Gas",
        ),
        (
            "Freelance Work",
            Decimal("500.00"),
            RecurringDirection.INCOME,
            RecurringFrequency.IRREGULAR,
            RecurringStatus.ACTIVE,
            "Income",
            "Freelance",
        ),
    ]

    created = []
    for name, amount, direction, frequency, status, tag_name, merchant in patterns_data:
        # Check if pattern already exists
        existing = (
            session.query(RecurringPattern)
            .filter(RecurringPattern.user_id == user_id, RecurringPattern.name == name)
            .first()
        )
        if existing:
            continue

        tag_id = tag_lookup.get(tag_name)
        anchor = now - timedelta(days=randint(5, 25))

        pattern = RecurringPattern(
            id=uuid4(),
            user_id=user_id,
            account_id=account_id,
            tag_id=tag_id,
            name=name,
            expected_amount=amount,
            currency="GBP",
            frequency=frequency.value,
            direction=direction.value,
            anchor_date=anchor,
            next_expected_date=anchor + timedelta(days=30),
            status=status.value,
            source=RecurringSource.DETECTED.value,
            merchant_contains=merchant,
            amount_tolerance_pct=Decimal("10.0"),
            confidence_score=Decimal("0.85"),
            occurrence_count=randint(3, 12),
            detection_reason="Demo: Regular pattern detected",
        )
        session.add(pattern)
        created.append(pattern)

    session.flush()
    return created


def _create_tag_rules(
    session: Session, user_id: UUID, tag_lookup: dict[str, UUID]
) -> list[TagRule]:
    """Create demo auto-tagging rules."""
    rules_data = [
        # (name, tag_name, priority, conditions)
        (
            "Amazon Shopping",
            "Shopping",
            0,
            {"counterparty_contains": "amazon"},
        ),
        (
            "Supermarkets",
            "Groceries",
            1,
            {"counterparty_contains": "tesco,sainsburys,asda,lidl,aldi,waitrose"},
        ),
    ]

    created = []
    for name, tag_name, priority, conditions in rules_data:
        tag_id = tag_lookup.get(tag_name)
        if not tag_id:
            continue

        # Check if rule already exists
        existing = (
            session.query(TagRule).filter(TagRule.user_id == user_id, TagRule.name == name).first()
        )
        if existing:
            continue

        rule = TagRule(
            id=uuid4(),
            user_id=user_id,
            name=name,
            tag_id=tag_id,
            priority=priority,
            enabled=True,
            conditions=conditions,
        )
        session.add(rule)
        created.append(rule)

    session.flush()
    return created


def _create_manual_assets(session: Session, user_id: UUID) -> list[ManualAsset]:
    """Create demo manual assets and liabilities with historical snapshots."""
    now = datetime.now(UTC)

    assets_data = [
        # (name, type, is_liability, value, interest, acq_date, acq_value, snapshots)
        (
            "Family Home",
            ManualAssetType.PROPERTY,
            False,
            Decimal("425000.00"),
            None,
            datetime(2018, 6, 15, tzinfo=UTC),
            Decimal("320000.00"),
            [
                (Decimal("320000.00"), -2555),  # ~7 years ago
                (Decimal("350000.00"), -1825),  # ~5 years ago
                (Decimal("380000.00"), -1095),  # ~3 years ago
                (Decimal("410000.00"), -365),  # ~1 year ago
                (Decimal("425000.00"), -30),  # recent
            ],
        ),
        (
            "Workplace Pension",
            ManualAssetType.PENSION,
            False,
            Decimal("67500.00"),
            None,
            datetime(2015, 1, 1, tzinfo=UTC),
            Decimal("0.00"),
            [
                (Decimal("25000.00"), -1460),  # ~4 years ago
                (Decimal("40000.00"), -730),  # ~2 years ago
                (Decimal("55000.00"), -365),  # ~1 year ago
                (Decimal("62000.00"), -180),  # ~6 months ago
                (Decimal("67500.00"), -30),  # recent
            ],
        ),
        (
            "Mazda 3",
            ManualAssetType.VEHICLE,
            False,
            Decimal("12500.00"),
            None,
            datetime(2022, 3, 20, tzinfo=UTC),
            Decimal("18000.00"),
            [
                (Decimal("18000.00"), -1048),  # purchase
                (Decimal("16000.00"), -730),  # ~2 years ago
                (Decimal("14500.00"), -365),  # ~1 year ago
                (Decimal("13000.00"), -180),  # ~6 months ago
                (Decimal("12500.00"), -30),  # recent
            ],
        ),
        (
            "Student Loan",
            ManualAssetType.STUDENT_LOAN,
            True,
            Decimal("18750.00"),
            Decimal("6.25"),
            datetime(2012, 9, 1, tzinfo=UTC),
            Decimal("45000.00"),
            [
                (Decimal("35000.00"), -1095),  # ~3 years ago
                (Decimal("28000.00"), -730),  # ~2 years ago
                (Decimal("23000.00"), -365),  # ~1 year ago
                (Decimal("20500.00"), -180),  # ~6 months ago
                (Decimal("18750.00"), -30),  # recent
            ],
        ),
    ]

    created = []
    for (
        name,
        asset_type,
        is_liability,
        value,
        interest,
        acq_date,
        acq_value,
        snapshots,
    ) in assets_data:
        # Check if asset already exists
        existing = (
            session.query(ManualAsset)
            .filter(ManualAsset.user_id == user_id, ManualAsset.name == name)
            .first()
        )
        if existing:
            continue

        asset = ManualAsset(
            id=uuid4(),
            user_id=user_id,
            asset_type=asset_type.value,
            is_liability=is_liability,
            name=name,
            current_value=value,
            currency="GBP",
            interest_rate=interest,
            acquisition_date=acq_date,
            acquisition_value=acq_value,
            is_active=True,
            value_updated_at=now,
        )
        session.add(asset)
        session.flush()

        # Add historical snapshots
        for snapshot_value, days_ago in snapshots:
            snapshot = ManualAssetValueSnapshot(
                asset_id=asset.id,
                value=snapshot_value,
                currency="GBP",
                captured_at=now + timedelta(days=days_ago),
            )
            session.add(snapshot)

        created.append(asset)

    session.flush()
    return created


def _create_savings_goals(
    session: Session, user_id: UUID, savings_account_id: UUID | None
) -> list[SavingsGoal]:
    """Create demo savings goals with different tracking modes."""
    now = datetime.now(UTC)

    goals_data = [
        # (name, target, current, mode, deadline, account_id, starting_balance, target_balance)
        (
            "Emergency Fund",
            Decimal("10000.00"),
            Decimal("8500.00"),
            GoalTrackingMode.MANUAL,
            datetime(2026, 12, 31, tzinfo=UTC),
            None,
            None,
            None,
        ),
        (
            "Holiday 2026",
            Decimal("2000.00"),
            Decimal("750.00"),
            GoalTrackingMode.MANUAL,
            datetime(2026, 7, 1, tzinfo=UTC),
            None,
            None,
            None,
        ),
        (
            "House Deposit Top-up",
            Decimal("20000.00"),
            Decimal("0.00"),
            GoalTrackingMode.BALANCE,
            datetime(2027, 6, 1, tzinfo=UTC),
            savings_account_id,
            Decimal("15420.00"),
            None,
        ),
    ]

    created = []
    for name, target, current, mode, deadline, account_id, starting_bal, target_bal in goals_data:
        # Check if goal already exists
        existing = (
            session.query(SavingsGoal)
            .filter(SavingsGoal.user_id == user_id, SavingsGoal.name == name)
            .first()
        )
        if existing:
            continue

        goal = SavingsGoal(
            id=uuid4(),
            user_id=user_id,
            name=name,
            target_amount=target,
            current_amount=current,
            currency="GBP",
            deadline=deadline,
            account_id=account_id,
            tracking_mode=mode.value,
            starting_balance=starting_bal,
            target_balance=target_bal,
            status=GoalStatus.ACTIVE.value,
            created_at=now - timedelta(days=randint(30, 180)),
        )
        session.add(goal)
        created.append(goal)

    session.flush()
    return created


def _create_milestones(session: Session, user_id: UUID) -> list[FinancialMilestone]:
    """Create demo net worth milestones."""
    milestones_data = [
        # (name, target, colour, target_date)
        ("First 100k", Decimal("100000.00"), "#f59e0b", None),
        ("Half Million", Decimal("500000.00"), "#10b981", datetime(2030, 1, 1, tzinfo=UTC)),
    ]

    created = []
    for name, target, colour, target_date in milestones_data:
        # Check if milestone already exists
        existing = (
            session.query(FinancialMilestone)
            .filter(FinancialMilestone.user_id == user_id, FinancialMilestone.name == name)
            .first()
        )
        if existing:
            continue

        milestone = FinancialMilestone(
            id=uuid4(),
            user_id=user_id,
            name=name,
            target_amount=target,
            colour=colour,
            target_date=target_date,
            achieved=False,
        )
        session.add(milestone)
        created.append(milestone)

    session.flush()
    return created


def _create_planned_transactions(
    session: Session, user_id: UUID, account_id: UUID | None
) -> list[PlannedTransaction]:
    """Create demo planned transactions (one-time and recurring)."""
    now = datetime.now(UTC)

    planned_data = [
        # (name, amount, frequency, next_date, notes)
        (
            "Annual Bonus",
            Decimal("5000.00"),
            RecurringFrequency.ANNUAL,
            datetime(2026, 12, 15, tzinfo=UTC),
            "Expected year-end bonus from ACME Corp",
        ),
        (
            "Quarterly Tax Payment",
            Decimal("-1200.00"),
            RecurringFrequency.QUARTERLY,
            datetime(2026, 4, 30, tzinfo=UTC),
            "Self-assessment tax payment",
        ),
        (
            "Car Insurance Renewal",
            Decimal("-450.00"),
            None,  # One-time
            datetime(2026, 2, 28, tzinfo=UTC),
            "Annual car insurance renewal",
        ),
    ]

    created = []
    for name, amount, frequency, next_date, notes in planned_data:
        # Check if planned transaction already exists
        existing = (
            session.query(PlannedTransaction)
            .filter(PlannedTransaction.user_id == user_id, PlannedTransaction.name == name)
            .first()
        )
        if existing:
            continue

        planned = PlannedTransaction(
            id=uuid4(),
            user_id=user_id,
            name=name,
            amount=amount,
            currency="GBP",
            frequency=frequency.value if frequency else None,
            next_expected_date=next_date,
            account_id=account_id,
            notes=notes,
            enabled=True,
            created_at=now,
        )
        session.add(planned)
        created.append(planned)

    session.flush()
    return created


if __name__ == "__main__":
    main()
