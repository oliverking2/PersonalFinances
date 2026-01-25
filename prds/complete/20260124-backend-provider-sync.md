# PRD: Unified Provider Sync & Multi-Provider Architecture

**Date:** 2026-01-24
**Scope:** backend
**Status:** Complete

## Goal

Build Dagster sync pipelines to keep unified tables (connections, accounts) in sync with raw provider tables, and establish the foundation for Trading212 and Vanguard integration.

## Current State

**Completed (previous PRD):**

- Unified tables: `institutions`, `connections`, `accounts`
- Balance fields on accounts table
- API endpoints using unified tables
- One-time migration backfill from GoCardless

**Gap:**

- No ongoing sync from raw tables to unified tables
- New connections/status changes not propagated
- No Trading212 or Vanguard provider modules

## Architecture

```
+----------------------------------------------------------------+
|                         API Layer                               |
|  /connections    /accounts    /institutions                     |
+--------------------------------+-------------------------------+
                                 |
+--------------------------------v-------------------------------+
|                    Unified Tables (PostgreSQL)                  |
|        connections          accounts          institutions      |
+--------------------------------+-------------------------------+
                                 | Dagster sync assets
+--------------------------------v-------------------------------+
|                    Raw Provider Tables (PostgreSQL)             |
|  gc_*              t212_*              vg_*                     |
|  (GoCardless)      (Trading212)        (Vanguard)              |
+--------------------------------+-------------------------------+
                                 | Dagster extraction assets
+--------------------------------v-------------------------------+
|                    External APIs / Scrapers                     |
|  GoCardless API    Trading212 API     Vanguard Scraper         |
+----------------------------------------------------------------+

Analytics Pipeline (separate from sync):
+--------------------------------+-------------------------------+
|          PostgreSQL            |        dbt transforms          |
|    (source of truth)           |        (read-only)             |
+--------------------------------+-------------------------------+
                                 |
                                 v
+--------------------------------+-------------------------------+
|                    DuckDB (analytics layer)                     |
|        Aggregations, reports, trend analysis                    |
+--------------------------------+-------------------------------+
```

**Data Strategy:**

- PostgreSQL is the source of truth for all operational data
- Extraction assets write directly to PostgreSQL raw tables (`gc_*`)
- Sync assets propagate changes to unified tables (`connections`, `accounts`)
- dbt reads from PostgreSQL and transforms into DuckDB for analytics
- This architecture supports transaction tagging in the UI (writes to PostgreSQL)

## Phase 1: GoCardless Sync Pipeline

### 1.1 Extraction Assets

**File:** `src/orchestration/gocardless/extraction/assets.py`

Extraction assets write directly to PostgreSQL:

- `gocardless_extract_transactions` - Writes to `gc_transactions`
- `gocardless_extract_account_details` - Writes to `gc_bank_accounts`
- `gocardless_extract_balances` - Writes to `gc_balances`

### 1.2 Sync Operations

**File:** `src/postgres/common/operations/sync.py`

```python
def sync_gocardless_connection(session, connection) -> Connection:
    """Sync a Connection from its corresponding GoCardless requisition."""

def sync_gocardless_account(session, bank_account, connection) -> Account:
    """Upsert GoCardless bank account to unified Account with balance."""

def sync_all_gocardless_connections(session) -> list[Connection]:
    """Sync all GoCardless connections from their raw requisitions."""

def sync_all_gocardless_accounts(session) -> list[Account]:
    """Sync all GoCardless bank accounts to unified accounts table."""
```

### 1.3 Dagster Sync Assets

**File:** `src/orchestration/gocardless/sync/assets.py`

```python
@asset(
    key=["sync", "gocardless", "connections"],
    group_name="gocardless",
)
def sync_gc_connections(context): ...

@asset(
    key=["sync", "gocardless", "accounts"],
    deps=[["sync", "gocardless", "connections"]],
    group_name="gocardless",
)
def sync_gc_accounts(context): ...
```

### 1.4 Scheduled Job

All GoCardless assets (extraction + sync) are grouped together and run on a schedule:

```python
gocardless_sync_job = define_asset_job(
    name="gocardless_sync_job",
    selection=AssetSelection.groups("gocardless"),
)

gocardless_sync_schedule = ScheduleDefinition(
    job=gocardless_sync_job,
    cron_schedule="0 4 * * *",  # Daily at 4 AM
)
```

**Trigger:** Runs daily at 4 AM via scheduled job (not individual asset crons).

### 1.5 Dagster Definitions

**File:** `src/orchestration/gocardless/definitions.py`

Includes all extraction assets, sync assets, job, and schedule.

## Phase 2: Account Model Extensions

### 2.1 New Fields

Add to `Account` model for investment accounts:

| Field            | Type          | Purpose                           |
|------------------|---------------|-----------------------------------|
| `account_type`   | String(20)    | "bank" / "investment" / "trading" |
| `total_value`    | Numeric(18,2) | Portfolio total value             |
| `unrealised_pnl` | Numeric(18,2) | Unrealised profit/loss            |

### 2.2 New Enum

```python
class AccountType(StrEnum):
    BANK = "bank"           # GoCardless bank accounts
    INVESTMENT = "investment"  # Vanguard portfolios
    TRADING = "trading"     # Trading212 ISA/GIA
```

### 2.3 Holdings Table

For investment accounts, create a unified holdings table:

```python
class Holding(Base):
    __tablename__ = "holdings"

    id: UUID                       # Primary key
    account_id: UUID               # FK to accounts
    ticker: str                    # Stock/fund ticker
    name: str                      # Display name
    isin: str | None               # ISIN if available
    quantity: Decimal              # Number of shares/units
    average_cost: Decimal | None   # Average purchase price
    current_price: Decimal         # Latest price
    current_value: Decimal         # quantity * current_price
    unrealised_pnl: Decimal | None # Profit/loss
    currency: str                  # Currency code
    updated_at: datetime           # Last sync time
```

### 2.4 Transaction Table (GoCardless)

Raw transaction storage in PostgreSQL for tagging support:

```python
class Transaction(Base):
    __tablename__ = "gc_transactions"

    id: int                        # Auto-increment primary key
    account_id: str                # FK to gc_bank_accounts
    transaction_id: str            # Provider transaction ID
    booking_date: date | None      # When booked
    value_date: date | None        # Value date
    transaction_amount: Decimal    # Amount
    currency: str                  # Currency code
    creditor_name: str | None      # Who received
    debtor_name: str | None        # Who paid
    remittance_information: str | None  # Description
    status: str                    # booked/pending
    extracted_at: datetime         # When extracted

    __table_args__ = (
        UniqueConstraint("account_id", "transaction_id"),
    )
```

### 2.5 Migrations

- `c8e9f1a2b3c4_add_investment_fields_and_holdings.py` - Account extensions and holdings table
- `28663f2f3281_add_gc_transactions_table.py` - GoCardless transactions table

## Implementation Scope

**Completed:**

- Phase 1: GoCardless sync pipeline (extraction + sync assets)
- Phase 2: Account model extensions (account_type, investment fields)
- Holdings table schema (for future Trading212/Vanguard use)
- Transaction table with PostgreSQL storage

**Out of Scope (future PRDs):**

- Trading212 integration
- Vanguard integration
- dbt transformations to DuckDB

## File Structure

### New Files

```
backend/src/
├── postgres/common/operations/
│   └── sync.py                    # Sync operations
├── postgres/gocardless/operations/
│   ├── balances.py               # Balance upserts
│   └── transactions.py           # Transaction upserts
├── orchestration/gocardless/sync/
│   ├── __init__.py
│   └── assets.py                  # Dagster sync assets

backend/alembic/versions/
├── c8e9f1a2b3c4_add_investment_fields_and_holdings.py
└── 28663f2f3281_add_gc_transactions_table.py

backend/testing/
├── postgres/common/operations/
│   └── test_sync.py
├── postgres/gocardless/operations/
│   └── test_transactions.py
└── orchestration/gocardless/sync/
    └── test_assets.py
```

### Modified Files

```
backend/src/
├── postgres/common/
│   ├── enums.py               # Add AccountType enum
│   └── models.py              # Add investment fields to Account, add Holding model
├── postgres/gocardless/
│   ├── models.py              # Add Transaction model
│   └── operations/bank_accounts.py  # Add upsert_bank_account_details
├── orchestration/
│   └── gocardless/
│       ├── definitions.py     # Include sync assets, job, schedule
│       └── extraction/assets.py  # Write to Postgres instead of S3
```

## Key Design Decisions

| Decision                                 | Rationale                                                           |
|------------------------------------------|---------------------------------------------------------------------|
| PostgreSQL as source of truth            | Supports writes (transaction tagging), simpler architecture         |
| No S3 for raw data                       | Eliminated complexity; PostgreSQL handles operational needs         |
| dbt reads from PostgreSQL                | Clean separation of OLTP (Postgres) and OLAP (DuckDB)               |
| Pull-based sync (scheduled)              | Simpler than event-driven; sufficient for daily financial data      |
| Single Account table with `account_type` | Avoids table explosion; single API response                         |
| Transactions in raw tables               | Provider-specific; unified via dbt if needed                        |
| Unified Holdings table                   | Expose investment positions through API regardless of provider      |
| Scheduled job by group                   | All `gocardless` group assets run together; scalable to more assets |
| No user assumption                       | Syncs all connections regardless of user                            |

## Verification

1. **Unit tests:** Sync operations, transaction upserts, balance upserts
2. **Integration tests:** Full extraction -> sync flow
3. **Dagster UI:** Verify asset dependencies and materialisation
4. **API tests:** Unified endpoints return correct data for all providers
5. **Manual verification:** Data matches provider dashboards

```bash
cd backend && make check   # 256 tests, 92% coverage
```

## Future PRDs (Out of Scope)

### dbt + DuckDB Analytics

- Configure dbt to read from PostgreSQL
- Transform to DuckDB for analytics queries
- API endpoints for aggregations

### Trading212 Integration

- Official REST API available
- Auth: API key in header
- Endpoints: `/api/v0/equity/account/cash`, `/api/v0/equity/portfolio`
- Raw tables: `t212_accounts`, `t212_positions`

### Vanguard Integration

- No official API - requires web scraper (Playwright)
- MFA challenge - Telegram bot or manual input
- Raw tables: `vg_accounts`, `vg_holdings`

## Open Questions (Deferred)

1. **Vanguard MFA:** Telegram bot integration or manual input endpoint?
2. **Trading212 API key:** How to obtain? (Settings -> API in app)

## References

- [Trading212 API Docs](https://t212public-api-docs.redoc.ly/)
- [Vanguard Scraper (GitHub)](https://github.com/hongkiulam/vanguard-scraper)
- Existing patterns: `src/orchestration/gocardless/extraction/assets.py`
