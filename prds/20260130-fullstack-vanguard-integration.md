# PRD: Vanguard Investor UK Integration

## Goals

- Automatically fetch daily ISA valuations and holdings from Vanguard Investor UK
- Display Vanguard accounts alongside bank accounts and Trading212 in the unified accounts view
- Handle MFA via existing Telegram integration
- Provide manual valuation fallback when automation fails

## Non-Goals

- Transaction history import (valuations and holdings only for now)
- Support for non-UK Vanguard platforms
- Real-time valuations (daily is sufficient for long-term ISA)

## Background

Vanguard Investor UK has no public API and no data export functionality. Browser automation is required to fetch account data. This follows the Trading212 integration pattern but uses Playwright instead of REST API calls.

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Raw Provider Tables                      │
│  vanguard_sessions    vanguard_valuations                   │
│  (credentials, session state, status)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ sync_vanguard_connection()
                          │ sync_vanguard_account()
                          │ sync_vanguard_holdings()
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Unified Common Tables                      │
│  institutions    connections    accounts    holdings        │
│  (Provider.VANGUARD)                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │ GET /api/connections
                          │ GET /api/accounts
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (accounts.vue)                  │
│  Vanguard appears alongside GoCardless and Trading212       │
│  in the same connections/accounts list                      │
└─────────────────────────────────────────────────────────────┘
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Dagster Orchestration                     │
│  ┌──────────────────┐    ┌─────────────────────────────┐   │
│  │ Auth Refresh Job │───▶│ Data Extraction Job         │   │
│  │ 7:15am weekdays  │    │ (runs after successful auth)│   │
│  │ 9:00am weekends  │    └─────────────────────────────┘   │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 VanguardClient (Playwright)                  │
│  - playwright-stealth for anti-detection                    │
│  - Human-like delays between actions                        │
│  - Session persistence via encrypted storage_state          │
│  - MFA via wait_for_reply() in telegram/polling.py          │
└─────────────────────────────────────────────────────────────┘
```

## Data Model

### VanguardSession

| Column                  | Type         | Description                                    |
|-------------------------|--------------|------------------------------------------------|
| id                      | UUID PK      | Primary key                                    |
| user_id                 | UUID FK      | References users.id CASCADE                    |
| credentials_encrypted   | TEXT         | Fernet encrypted username:password             |
| session_state_encrypted | TEXT         | Fernet encrypted Playwright storage_state JSON |
| friendly_name           | VARCHAR(128) | User-provided name                             |
| status                  | VARCHAR(20)  | active, auth_required, mfa_pending, error      |
| error_message           | TEXT         | Error details when status=error                |
| last_auth_at            | TIMESTAMP    | Last successful authentication                 |
| last_synced_at          | TIMESTAMP    | Last successful data sync                      |
| created_at              | TIMESTAMP    | Record creation time                           |
| updated_at              | TIMESTAMP    | Record update time                             |

### VanguardValuation

| Column      | Type          | Description                             |
|-------------|---------------|-----------------------------------------|
| id          | INTEGER PK    | Auto-increment                          |
| session_id  | UUID FK       | References vanguard_sessions.id CASCADE |
| total_value | NUMERIC(18,2) | Total account value                     |
| currency    | VARCHAR(3)    | Default 'GBP'                           |
| source      | VARCHAR(20)   | 'automated' or 'manual'                 |
| fetched_at  | TIMESTAMP     | When valuation was captured             |

Index: `(session_id, fetched_at)`

## API Endpoints

| Method   | Path                           | Purpose                                          |
|----------|--------------------------------|--------------------------------------------------|
| GET      | `/api/vanguard`                | List user's Vanguard connections                 |
| POST     | `/api/vanguard`                | Create connection (stores encrypted credentials) |
| GET      | `/api/vanguard/{id}`           | Get connection details                           |
| DELETE   | `/api/vanguard/{id}`           | Delete connection                                |
| POST     | `/api/vanguard/{id}/sync`      | Trigger manual sync                              |
| POST     | `/api/vanguard/{id}/valuation` | Add manual valuation (fallback)                  |
| GET      | `/api/vanguard/{id}/holdings`  | Get current holdings                             |

## Files to Create

### Database Layer

| File                                                     | Purpose                                       |
|----------------------------------------------------------|-----------------------------------------------|
| `backend/src/postgres/vanguard/__init__.py`              | Package exports                               |
| `backend/src/postgres/vanguard/models.py`                | `VanguardSession`, `VanguardValuation` tables |
| `backend/src/postgres/vanguard/operations/__init__.py`   | Operations exports                            |
| `backend/src/postgres/vanguard/operations/sessions.py`   | Session CRUD                                  |
| `backend/src/postgres/vanguard/operations/valuations.py` | Valuation CRUD                                |
| `backend/alembic/versions/xxx_add_vanguard_tables.py`    | Migration                                     |

### Provider Layer

| File                                                        | Purpose                                                         |
|-------------------------------------------------------------|-----------------------------------------------------------------|
| `backend/src/providers/vanguard/__init__.py`                | Package exports                                                 |
| `backend/src/providers/vanguard/exceptions.py`              | `VanguardError`, `VanguardAuthError`, `VanguardMfaTimeoutError` |
| `backend/src/providers/vanguard/client.py`                  | High-level `VanguardClient` orchestrating browser               |
| `backend/src/providers/vanguard/browser/__init__.py`        | Browser package                                                 |
| `backend/src/providers/vanguard/browser/core.py`            | `VanguardBrowser` context manager                               |
| `backend/src/providers/vanguard/browser/stealth.py`         | Anti-detection: delays, fingerprint config                      |
| `backend/src/providers/vanguard/browser/pages/__init__.py`  | Pages package                                                   |
| `backend/src/providers/vanguard/browser/pages/login.py`     | `LoginPage` - login + MFA flow                                  |
| `backend/src/providers/vanguard/browser/pages/portfolio.py` | `PortfolioPage` - extract holdings                              |

### Orchestration Layer

| File                                                      | Purpose                              |
|-----------------------------------------------------------|--------------------------------------|
| `backend/src/orchestration/vanguard/__init__.py`          | Package exports                      |
| `backend/src/orchestration/vanguard/definitions.py`       | Jobs, schedules, assets registration |
| `backend/src/orchestration/vanguard/auth/assets.py`       | Auth refresh asset                   |
| `backend/src/orchestration/vanguard/extraction/assets.py` | Portfolio extraction asset           |

### API Layer

| File                                    | Purpose                          |
|-----------------------------------------|----------------------------------|
| `backend/src/api/vanguard/__init__.py`  | Router exports                   |
| `backend/src/api/vanguard/endpoints.py` | CRUD + manual valuation endpoint |
| `backend/src/api/vanguard/models.py`    | Pydantic request/response models |

### Frontend

| File                                                    | Purpose                |
|---------------------------------------------------------|------------------------|
| `frontend/app/components/accounts/AddVanguardModal.vue` | Connection setup modal |
| `frontend/app/composables/useVanguardApi.ts`            | API composable         |

## Files to Modify

| File                                             | Change                                                 |
|--------------------------------------------------|--------------------------------------------------------|
| `backend/src/utils/definitions.py`               | Rename `t212_encryption_key()` → `encryption_key()`    |
| `backend/src/utils/security.py`                  | Update to use generic `encryption_key()`               |
| `backend/src/providers/trading212/`              | Update imports for renamed encryption function         |
| `backend/src/orchestration/definitions.py`       | Register Vanguard assets/jobs/schedules                |
| `backend/src/api/app.py`                         | Register Vanguard router                               |
| `backend/src/postgres/common/operations/sync.py` | Add `sync_vanguard_*` functions                        |
| `backend/.env_example`                           | Document any new env vars                              |
| `backend/pyproject.toml`                         | Add `playwright`, `playwright-stealth` dependencies    |
| `frontend/app/pages/accounts.vue`                | Add "Add Vanguard" button (next to Trading 212 button) |

## Sync Operations

Add to `backend/src/postgres/common/operations/sync.py`:

### ensure_vanguard_institution()

```python
Institution(
    id="VANGUARD_UK",
    provider=Provider.VANGUARD.value,
    name="Vanguard Investor UK",
    logo_url="https://www.vanguardinvestor.co.uk/favicon.ico",
    countries=["GB"],
)
```

### sync_vanguard_connection(session, vg_session)

Map `VanguardSession` → `Connection`:

- `provider` = `Provider.VANGUARD.value`
- `provider_id` = `str(vg_session.id)`
- `institution_id` = `"VANGUARD_UK"`
- `friendly_name` = `vg_session.friendly_name`
- `status` = map from `vg_session.status` (active→ACTIVE, auth_required/mfa_pending/error→ERROR)

### sync_vanguard_account(session, vg_session, connection)

Map `VanguardSession` + latest `VanguardValuation` → `Account`:

- `connection_id` = `connection.id`
- `provider_id` = `"isa"` (or from Vanguard if multiple accounts)
- `account_type` = `AccountType.INVESTMENT.value`
- `name` = `"Vanguard ISA"`
- `total_value` = `latest_valuation.total_value`
- `currency` = `"GBP"`

### sync_vanguard_holdings(session, account, holdings_data)

Map extracted holdings → `Holding` records:

- `account_id` = `account.id`
- `ticker` = fund ISIN or Vanguard code
- `name` = fund name
- `quantity` = units
- `current_price` = unit price
- `current_value` = value
- Upsert by `(account_id, ticker)` unique constraint

## Anti-Detection Strategy

1. **playwright-stealth plugin** - Patches WebGL, canvas, webdriver flags, navigator properties
2. **Human-like delays** - Random intervals between actions:
   - Short (0.5-1.5s): Between form field interactions
   - Medium (1.5-3.0s): After page loads
   - Long (3.0-6.0s): Before sensitive actions (login submit)
   - Typing (50-150ms): Between keystrokes
3. **Realistic browser context** - UK locale, London timezone, 1920x1080 viewport
4. **Personal IP** - No proxy needed, already residential

## MFA Flow

1. Auth job runs at scheduled time (7:15am weekdays, 9:00am weekends)
2. VanguardClient attempts login with stored credentials
3. If MFA required:
   - Send Telegram: "Vanguard requires MFA. Reply with your 6-digit code."
   - Call `wait_for_reply(timeout_seconds=300)`
   - Enter code, complete login
   - On timeout: mark session as `mfa_pending`, notify user
4. Save new storage_state (encrypted)
5. Data extraction job can now run

## Frontend Changes

**accounts.vue:**

- Add `showVanguardModal` ref
- Add `openVanguardModal()`, `closeVanguardModal()`, `handleVanguardCreated()` handlers
- Add "Add Vanguard" button in header (same row as "Connect Bank" and "Add Trading 212")
- Add `<AccountsAddVanguardModal>` component

**AddVanguardModal.vue:**

- Username/password fields (both masked, with show/hide toggle)
- Friendly name field
- Warning about credential encryption
- Pre-requisite check: user must have Telegram linked (for MFA)
- Submit calls `POST /api/vanguard` to store credentials and trigger initial auth

## Implementation Order

1. **Dependencies** - Add playwright, playwright-stealth to pyproject.toml
2. **Rename encryption** - `t212_encryption_key()` → `encryption_key()`
3. **Database** - Models, migration, operations
4. **Browser automation** - Core, stealth, page objects
5. **Client** - VanguardClient with MFA handling
6. **Sync operations** - Vanguard → Connection/Account mapping
7. **Dagster** - Assets, jobs, schedules
8. **API** - Endpoints including manual valuation
9. **Frontend** - Modal and composable
10. **Tests** - Throughout implementation

## Acceptance Criteria

- [ ] User can add Vanguard connection via frontend modal
- [ ] Credentials are encrypted at rest using Fernet
- [ ] Auth job runs at scheduled times (7:15am weekdays, 9am weekends)
- [ ] MFA prompt sent via Telegram with 5-minute timeout
- [ ] Valuations synced to unified `accounts` table
- [ ] Holdings synced to unified `holdings` table
- [ ] Vanguard accounts appear in accounts page alongside other providers
- [ ] Manual valuation entry works as fallback
- [ ] `make check` passes in both backend/ and frontend/

## Risks

| Risk                   | Mitigation                                                      |
|------------------------|-----------------------------------------------------------------|
| Page structure changes | Page Object Model isolates selectors                            |
| Account lockout        | Human-like delays, stealth plugin, monitor for blocks           |
| MFA timeout            | Clear Telegram message, 5-minute timeout, graceful failure      |
| Session expiry         | Daily auth refresh before market hours                          |
| ToS violation          | Personal use only, read-only access, no high-frequency requests |
