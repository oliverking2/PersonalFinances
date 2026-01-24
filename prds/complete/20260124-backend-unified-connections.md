# Backend PRD: Unified Connections & Accounts Architecture

**Date**: 2026-01-24
**Scope**: backend

## Goal

Create a provider-agnostic data layer for connections and accounts that supports GoCardless, Trading212, and Vanguard. Keep raw provider data in dedicated tables while exposing standardised tables and APIs for the frontend.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  GET /api/connections    GET /api/accounts    GET /api/institutions │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    Standardised Tables                           │
│        connections          accounts          institutions       │
└───────────────────────────────┬─────────────────────────────────┘
                                │ sync
┌───────────────────────────────▼─────────────────────────────────┐
│                    Raw Provider Tables                           │
│  gc_requisition_links    gc_bank_accounts    gc_balances        │
│  (future: t212_*, vanguard_*)                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Tables

```sql
-- Institutions cache (provider metadata)
CREATE TABLE institutions (
    id VARCHAR(100) PRIMARY KEY,      -- Provider's institution ID (e.g., NATIONWIDE_NAIAGB21)
    provider VARCHAR(20) NOT NULL,    -- 'gocardless' | 'vanguard' | 'trading212'
    name VARCHAR(255) NOT NULL,
    logo_url VARCHAR(512),
    countries JSONB,                  -- ["GB", "IE"]
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Standardised connections
CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL,
    provider_id VARCHAR(128) NOT NULL,   -- e.g., GoCardless requisition ID
    institution_id VARCHAR(100) NOT NULL REFERENCES institutions(id),
    friendly_name VARCHAR(128) NOT NULL,
    status VARCHAR(20) NOT NULL,         -- 'active' | 'expired' | 'pending' | 'error'
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_id)
);

-- Standardised accounts
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    provider_id VARCHAR(128) NOT NULL,   -- e.g., GoCardless account ID
    display_name VARCHAR(128),           -- User-editable
    name VARCHAR(128),                   -- Provider-sourced (read-only)
    iban VARCHAR(200),
    currency VARCHAR(3),
    status VARCHAR(20) NOT NULL,         -- 'active' | 'inactive'
    last_synced_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(connection_id, provider_id)
);
```

### Keep Existing Tables

Raw GoCardless tables remain unchanged as the source of truth for provider data:
- `gc_requisition_links`
- `gc_bank_accounts`
- `gc_balances`
- `gc_end_user_agreements`

---

## Status Mapping

### Connection Status (from GoCardless requisition)

| GoCardless Code | Meaning | Maps To |
|-----------------|---------|---------|
| CR | Created | `pending` |
| LN | Linked | `active` |
| EX | Expired | `expired` |
| RJ, UA, SU | Rejected/Abandoned/Suspended | `error` |
| GA, SA | Granting Access/Selecting | `pending` |

### Account Status (from GoCardless account)

| GoCardless Status | Maps To |
|-------------------|---------|
| READY | `active` |
| EXPIRED, SUSPENDED, null | `inactive` |

---

## API Changes

### Response Models (align with frontend PRD)

**ConnectionResponse** (changed fields marked with *)
```python
class ConnectionResponse:
    id: str                          # * UUID instead of requisition ID
    friendly_name: str
    provider: Provider               # * NEW
    institution: InstitutionResponse # * NEW (nested object)
    status: ConnectionStatus         # * normalised enum
    account_count: int
    created_at: datetime
    expires_at: datetime | None      # * NEW
    # REMOVED: link, expired (boolean)
```

**AccountResponse** (changed fields marked with *)
```python
class AccountResponse:
    id: str                          # * UUID instead of GC account ID
    connection_id: str               # * renamed from requisition_id
    display_name: str | None
    name: str | None
    iban: str | None
    currency: str | None
    status: AccountStatus            # * normalised enum
    balance: AccountBalance | None   # * NEW
    last_synced_at: datetime | None  # * NEW
    # REMOVED: owner_name, product, transaction_extract_date
```

### Endpoints

| Endpoint | Change |
|----------|--------|
| `GET /api/connections` | Read from `connections` table, add auth |
| `POST /api/connections` | Implement (currently 501), create in both tables |
| `PATCH /api/connections/{id}` | NEW - update friendly_name |
| `DELETE /api/connections/{id}` | Read from `connections`, cascade delete |
| `POST /api/connections/{id}/reauthorise` | NEW - generate new auth URL |
| `GET /api/accounts` | Read from `accounts` table, add balance lookup |
| `PATCH /api/accounts/{id}` | Update in standardised table |
| `GET /api/institutions` | NEW - list institutions for dropdown |

---

## File Structure

### New Files

```
backend/src/
├── postgres/
│   └── common/
│       ├── __init__.py
│       ├── enums.py              # Provider, ConnectionStatus, AccountStatus
│       ├── models.py             # Connection, Account, Institution (SQLAlchemy)
│       └── operations/
│           ├── __init__.py
│           ├── connections.py    # CRUD for connections
│           ├── accounts.py       # CRUD for accounts
│           └── institutions.py   # CRUD for institutions
├── api/
│   └── institutions/
│       ├── __init__.py
│       ├── endpoints.py          # GET /api/institutions
│       └── models.py             # InstitutionResponse

backend/alembic/versions/
└── xxxx_add_unified_tables.py    # Migration + backfill
```

### Modified Files

```
backend/src/
├── api/
│   ├── app.py                    # Add institutions router
│   ├── connections/
│   │   ├── endpoints.py          # Switch to standardised tables, add auth
│   │   └── models.py             # Update response models
│   └── accounts/
│       ├── endpoints.py          # Switch to standardised tables, add balance
│       └── models.py             # Update response models
```

---

## Implementation Sequence

### Phase 1: Database Layer
1. Create `src/postgres/common/enums.py` with StrEnum definitions
2. Create `src/postgres/common/models.py` with SQLAlchemy models
3. Create Alembic migration for new tables
4. Create operations modules (CRUD functions)
5. Write tests for all operations

### Phase 2: Seed & Backfill (in migration)
1. Seed institutions from GoCardless (hardcoded for existing connections)
2. Backfill existing `gc_requisition_links` → `connections`
3. Backfill existing `gc_bank_accounts` → `accounts`
4. Associate with first user (single-user backfill)

### Phase 3: API Layer
1. Update connection endpoints to use standardised tables
2. Update account endpoints, add balance lookup
3. Create institutions endpoints
4. Implement `POST /api/connections` (create flow)
5. Implement `POST /api/connections/{id}/reauthorise`
6. Add `get_current_user` dependency to all endpoints
7. Write API tests

**Out of Scope (future PRD):**
- Dagster sync pipeline (GoCardless → standardised tables)
- Automatic institution list refresh from GoCardless API

---

## Verification

1. Run `cd backend && make check`
2. API tests cover:
   - List connections returns correct structure
   - List accounts with `connection_id` filter
   - Edit display_name persists
   - Create connection returns auth URL
   - Delete cascades to accounts
3. Manual verification:
   - Existing data migrated correctly
   - Frontend PRD mock data matches API responses
