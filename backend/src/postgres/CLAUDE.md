# Postgres Module CLAUDE.md

Database layer guidance. See also `backend/.claude/rules/database.md` for general patterns.

## Structure

```
postgres/
├── core.py              # Engine, session, Base class
├── auth/                # Authentication domain
│   ├── models.py        # User, RefreshToken
│   └── operations/      # Auth-specific CRUD
├── common/              # Provider-agnostic models
│   ├── models.py        # Connections, Accounts, Transactions, RecurringPatterns,
│   │                    # Tags, TagRules, Budgets, Goals, Notifications,
│   │                    # BalanceSnapshots, ManualAssets, PlannedTransactions, etc.
│   ├── enums.py         # All enums (single source of truth, 17 enum classes)
│   └── operations/      # CRUD by entity
├── gocardless/          # GoCardless raw data
│   ├── models.py        # Requisitions, BankAccounts, Balances
│   └── operations/
├── telegram/            # Telegram bot state
│   └── models.py        # PollingCursor
└── trading212/          # Trading212 raw data
    ├── models.py        # Holdings, Transactions
    └── operations/
```

## Model Conventions

### SQLAlchemy 2.0 Style

```python
from sqlalchemy.orm import Mapped, mapped_column

class Item(Base):
    __tablename__ = "items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

### Enum Usage

All enums live in `common/enums.py`:

```python
class RecurringStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
```

Store as string in database, use enum in code:

```python
status: Mapped[str] = mapped_column(String(50), nullable=False)

# In operations:
pattern.status = RecurringStatus.ACTIVE.value
```

## Operations Conventions

### File Per Entity

```
operations/
├── accounts.py
├── connections.py
├── transactions.py
├── recurring_patterns.py
└── ...
```

### Function Signatures

```python
def create_item(session: Session, user_id: UUID, name: str, **kwargs) -> Item:
    """Create an item.

    :param session: Database session (caller manages transaction).
    :param user_id: Owner's user ID.
    :param name: Item name.
    :returns: Created item.
    """
    item = Item(user_id=user_id, name=name, **kwargs)
    session.add(item)
    session.flush()  # Get auto-generated ID
    return item
```

### Query Patterns

```python
# Get by ID with user scope
def get_item(session: Session, user_id: UUID, item_id: UUID) -> Item | None:
    return session.query(Item).filter(
        Item.id == item_id,
        Item.user_id == user_id,
    ).first()

# List with filters
def list_items(
    session: Session,
    user_id: UUID,
    status: str | None = None,
    limit: int = 100,
) -> list[Item]:
    query = session.query(Item).filter(Item.user_id == user_id)
    if status:
        query = query.filter(Item.status == status)
    return query.order_by(Item.created_at.desc()).limit(limit).all()
```

### Transaction Management

Operations do NOT commit - caller manages transactions:

```python
# In API endpoint:
with get_session() as session:
    item = create_item(session, user_id, name)
    link = create_link(session, item.id, other_id)
    session.commit()  # Commit both together
```

## Common vs Provider-Specific

### Common (provider-agnostic)

Used by API, shared across providers:

- `Connection` - Bank connection (any provider)
- `Account` - Bank account (any provider)
- `Transaction` - Unified transaction format
- `RecurringPattern` - Detected/manual recurring payments
- `Tag`, `TagRule`, `TransactionSplit` - User categorisation
- `Budget`, `Goal`, `Notification` - User features
- `BalanceSnapshot` - Append-only balance history
- `ManualAsset` - Manual assets/liabilities (property, loans, etc.)
- `PlannedTransaction` - Future planned income/expenses
- `FinancialMilestone` - User-defined milestones for net worth chart
- `Job` - Background job tracking

### Provider-Specific (raw data)

Source of truth for Dagster sync:

- `gocardless/` - Requisitions, BankAccounts, Balances
- `trading212/` - Holdings, Transactions

Sync pipeline: Provider tables → Common tables

## Key Models

### RecurringPattern (opt-in model)

```
Status workflow: pending → active ⟷ paused / cancelled
Source: detected (by dbt) or manual (user-created)
```

- `status`: pending/active/paused/cancelled
- `source`: detected/manual
- `merchant_contains`: Case-insensitive matching
- `amount_tolerance_pct`: Default 10%
- One transaction can only link to one pattern (unique constraint)

### Notification

```python
# Types: budget_warning, budget_exceeded, export_complete, sync_complete, goal_reached
# Deduplication via unique constraint on (user_id, type, dedup_key)
```

## Migrations

Always use autogenerate:

```bash
poetry run alembic revision --autogenerate -m "add status to items"
poetry run alembic upgrade head
```

For data migrations, see `backend/.claude/rules/database.md`.
