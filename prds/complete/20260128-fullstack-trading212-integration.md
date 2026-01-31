# PRD: Trading 212 Integration

**Status**: Complete
**Author**: Claude
**Created**: 2026-01-28
**Updated**: 2026-01-30

---

## Overview

Integrate Trading 212 Invest API to pull investment account data including cash balances, order history, dividends, and cash transactions. Follows the existing two-layer architecture (raw provider tables → unified tables) and integrates with dbt analytics.

## Problem Statement

Users with Trading 212 investment accounts cannot track their portfolio value alongside bank accounts. This integration allows unified financial tracking across both traditional banking (via GoCardless) and investment accounts (via Trading 212).

## Goals

- Pull Trading 212 account balances and sync to unified accounts table
- Extract and store order history, dividends, and cash transactions
- Sync Trading 212 transactions to unified transactions table for analytics
- Integrate with existing dbt models for cross-provider analytics
- Provide REST API and frontend for managing Trading 212 connections

## Non-Goals

- Real-time portfolio tracking (batch sync only)
- Holdings/positions data (future enhancement)
- Order execution or trading functionality
- Multiple Trading 212 accounts per user (one API key per user for now)

---

## User Stories

1. **As a** user, **I want to** connect my Trading 212 account, **so that** I can see my investment balance alongside my bank accounts
2. **As a** user, **I want to** see my Trading 212 transactions in analytics, **so that** I can track dividends and deposits/withdrawals
3. **As a** user, **I want to** manually refresh my Trading 212 data, **so that** I can see up-to-date balances

---

## Proposed Solution

### High-Level Design

```
Trading 212 API
      ↓
[Dagster Extraction Assets]
      ↓
Raw Tables (t212_*)
      ↓
[Dagster Sync Assets]
      ↓
Unified Tables (accounts, transactions)
      ↓
[Unified Sync Gates]
      ↓
dbt Models
```

### Data Model

**t212_api_keys** - Stores encrypted API keys per user

| Column                 | Type        | Notes                      |
|------------------------|-------------|----------------------------|
| id                     | UUID        | PK                         |
| user_id                | UUID FK     | → users.id                 |
| api_key_encrypted      | Text        | Fernet-encrypted           |
| friendly_name          | String(128) | User-provided label        |
| t212_account_id        | String(50)  | From API                   |
| currency_code          | String(3)   | From API                   |
| status                 | String(20)  | active/error               |
| error_message          | Text        | Last error if status=error |
| last_synced_at         | DateTime    | Last successful sync       |
| created_at, updated_at | DateTime    | Timestamps                 |

**t212_cash_balances** - Historical cash balance snapshots

| Column                                                | Type          |
|-------------------------------------------------------|---------------|
| id                                                    | Integer PK    |
| api_key_id                                            | UUID FK       |
| free, blocked, invested, pie_cash, ppl, result, total | Decimal(18,2) |
| fetched_at                                            | DateTime      |

**t212_orders** - Order/trade history

| Column                                     | Type               |
|--------------------------------------------|--------------------|
| id                                         | Integer PK         |
| api_key_id                                 | UUID FK            |
| t212_order_id                              | String(100) UNIQUE |
| ticker, instrument_name                    | String             |
| order_type, status                         | String             |
| quantity, filled_quantity, filled_value    | Decimal            |
| limit_price, stop_price, fill_price        | Decimal            |
| currency                                   | String(3)          |
| date_created, date_executed, date_modified | DateTime           |

**t212_dividends** - Dividend payments

| Column                                         | Type               |
|------------------------------------------------|--------------------|
| id                                             | Integer PK         |
| api_key_id                                     | UUID FK            |
| t212_reference                                 | String(100) UNIQUE |
| ticker, instrument_name                        | String             |
| amount, amount_in_euro, gross_amount_per_share | Decimal            |
| quantity                                       | Decimal            |
| currency, dividend_type                        | String             |
| paid_on                                        | DateTime           |

**t212_transactions** - Cash movements (deposits, withdrawals, fees)

| Column           | Type               |
|------------------|--------------------|
| id               | Integer PK         |
| api_key_id       | UUID FK            |
| t212_reference   | String(100) UNIQUE |
| transaction_type | String             |
| amount           | Decimal            |
| currency         | String(3)          |
| date_time        | DateTime           |

### API Endpoints

| Method   | Path                 | Description                               |
|----------|----------------------|-------------------------------------------|
| POST     | /api/trading212      | Add T212 connection (validates key first) |
| GET      | /api/trading212      | List user's T212 connections              |
| DELETE   | /api/trading212/{id} | Remove connection                         |

Sync is triggered via the existing `/api/connections/{id}/sync` endpoint which detects the provider and triggers the appropriate Dagster job.

### Dagster Assets

**Extraction (from T212 API → raw tables)**:

- `source/trading212/extract/cash` - Cash balances
- `source/trading212/extract/orders` - Order history
- `source/trading212/extract/dividends` - Dividend payments
- `source/trading212/extract/transactions` - Cash movements

**Sync (from raw tables → unified tables)**:

- `sync/trading212/connections` - Upsert to connections table
- `sync/trading212/accounts` - Upsert to accounts table with total_value/unrealised_pnl
- `sync/trading212/transactions` - Sync orders, dividends, cash txns to unified transactions

**Unified Gates (for dbt dependencies)**:

- `sync/unified/accounts` - Depends on both GC and T212 account syncs
- `sync/unified/connections` - Depends on both GC and T212 connection syncs
- `sync/unified/transactions` - Depends on both GC and T212 transaction syncs

### UI/UX

- "Add Trading 212" button on accounts page opens modal
- Modal accepts API key and optional friendly name
- Validates API key before saving
- T212 accounts appear in standard account list with TRADING type badge

---

## Technical Considerations

### Dependencies

- `cryptography` - Fernet encryption for API keys
- Environment variable: `T212_ENCRYPTION_KEY`

### API Rate Limits

| Endpoint                     | Rate Limit  |
|------------------------------|-------------|
| /equity/account/cash         | 1 req/2s    |
| /equity/account/info         | 1 req/30s   |
| /equity/history/orders       | 1 req/5s    |
| /equity/history/dividends    | 1 req/30s   |
| /equity/history/transactions | 1 req/30s   |

Client implements per-endpoint rate limiting with sleep between requests.

### Security

- API keys encrypted at rest using Fernet symmetric encryption
- Encryption key stored in environment variable, not in code/database
- API keys never logged or exposed in API responses

### Transaction Mapping

| T212 Source       | Unified Transaction Fields                                                          |
|-------------------|-------------------------------------------------------------------------------------|
| Filled orders     | provider_id: "order_{id}", amount: filled_value, description: "{BUY/SELL} {ticker}" |
| Dividends         | provider_id: "dividend_{ref}", amount: amount, description: "Dividend: {ticker}"    |
| Cash transactions | provider_id: "txn_{ref}", amount: amount, description: "{type}"                     |

---

## Implementation Plan

### Phase 1: Core Infrastructure (Complete)

- [x] Fernet encryption utilities in security.py
- [x] Database models (t212_api_keys, t212_cash_balances)
- [x] Database operations (api_keys.py, cash_balances.py)
- [x] Trading212Client API client with rate limiting
- [x] Alembic migration

### Phase 2: Dagster Pipeline - Cash (Complete)

- [x] Extraction asset: trading212_extract_cash
- [x] Sync assets: sync_t212_connections, sync_t212_accounts
- [x] Job definition: trading212_sync_job
- [x] Integration with connections endpoint for manual sync

### Phase 3: REST API & Frontend (Complete)

- [x] Trading 212 API endpoints (add, list, delete)
- [x] AddTrading212Modal.vue component
- [x] useTrading212Api.ts composable
- [x] Integration with accounts page

### Phase 4: Transaction History (Complete)

- [x] Database models (t212_orders, t212_dividends, t212_transactions)
- [x] API client methods with pagination (get_orders, get_dividends, get_transactions)
- [x] Database operations (history.py)
- [x] Extraction assets for orders, dividends, transactions
- [x] Sync to unified transactions table
- [x] Update Dagster job with all assets

### Phase 5: dbt Integration (Complete)

- [x] Unified sync gate assets (sync_unified_*)
- [x] Update dbt schema to depend on unified gates
- [x] Verify dbt models receive T212 data

---

## Testing Strategy

- [x] Unit tests for encryption utilities
- [x] Unit tests for database operations
- [x] Unit tests for API client (mocked)
- [x] Unit tests for API endpoints
- [x] Integration: Manual test of full flow (add key → sync → verify data)
- [x] 80%+ code coverage maintained

---

## File Structure

```
backend/src/
├── postgres/trading212/
│   ├── __init__.py
│   ├── models.py                    # T212ApiKey, T212CashBalance, T212Order, T212Dividend, T212Transaction
│   └── operations/
│       ├── __init__.py
│       ├── api_keys.py
│       ├── cash_balances.py
│       └── history.py
├── providers/trading212/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── core.py                  # Trading212Client
│   └── exceptions.py
├── orchestration/
│   ├── trading212/
│   │   ├── __init__.py
│   │   ├── definitions.py
│   │   ├── extraction/assets.py
│   │   └── sync/assets.py
│   └── unified/
│       ├── __init__.py
│       └── assets.py                # Unified sync gates for dbt
├── api/trading212/
│   ├── __init__.py
│   ├── endpoints.py
│   └── models.py
└── utils/security.py                # encrypt_api_key, decrypt_api_key

frontend/app/
├── components/accounts/
│   └── AddTrading212Modal.vue
└── composables/
    └── useTrading212Api.ts

backend/dbt/models/1_source/unified/
└── schema.yml                       # Updated to use sync/unified/* asset keys
```

---

## References

- [Trading 212 API Documentation](https://t212public-api-docs.redoc.ly/)
- Plan file: `.claude/plans/melodic-frolicking-wilkinson.md`
