# Roadmap

Personal Finances App with Automated Data Pipeline and AI Insights

## Vision

A self-hosted personal finance platform that aggregates all financial data in one place, provides intelligent insights, and proactively alerts on important financial events.

---

## Phase 1: Foundation ✅

Stabilise the existing data pipeline and improve core functionality.

### Completed

- [x] GoCardless open banking integration
- [x] PostgreSQL for metadata storage
- [x] PostgreSQL for transaction data (gc_transactions table)
- [x] Dagster orchestration for data extraction
- [x] Dagster sync pipeline (raw tables -> unified tables)
- [x] dbt + DuckDB for transformations
- [x] Basic Streamlit UI for account management
- [x] Scheduled GoCardless job (daily at 4 AM)
- [x] Link expiry handling and re-authentication flow
- [x] Improve error handling in GoCardless API client
- [x] Add retry logic for failed extractions

### Backlog

- [ ] Historical data backfill tooling

---

## Phase 2: Frontend Overhaul

Replace Streamlit with a modern Vue + Nuxt + Tailwind frontend backed by FastAPI.

### Backend (FastAPI)

- [x] Project structure setup (`src/api/`)
- [x] Authentication (JWT access tokens + refresh token cookies)
- [x] Unified connections/accounts architecture (provider-agnostic)
- [x] Institutions API (list, get)
- [x] Connection endpoints (list, get, update friendly name, delete)
- [x] Account endpoints (list, get, update display name, filter by connection)
- [x] Balance lookup (included in account responses from gc_balances)
- [x] Create connection endpoint (GoCardless OAuth flow)
- [x] Reauthorise connection endpoint
- [x] Transaction endpoints (list, search, filter)
- [x] Seed scripts for development (`seed_dev.py`, `seed_demo.py`, `seed_gocardless.py`)
- [x] Request timing logging

### Frontend (Vue + Nuxt + Tailwind)

- [x] Project setup in `frontend/` directory
- [x] Tailwind theme and reusable components (AppButton, AppInput)
- [x] Authentication flow (login, logout, token refresh)
- [x] Auth middleware and Pinia store
- [x] Dashboard view (placeholder)
- [x] Accounts list view with balances and status indicators
- [x] Account display name editing (modal)
- [x] Connection management UI (add, rename, reauthorise, delete)
- [x] Transaction list with day grouping, infinite scroll, and filters

---

## Phase 2.5: Consolidation & Quality

Address tech debt and improve code quality before adding new data sources.

### Test Coverage

- [x] Add missing test files:
  - `testing/api/test_dependencies.py` - API dependency injection tests
  - `testing/api/jobs/test_endpoints.py` - Jobs API endpoint tests
  - `testing/postgres/common/operations/test_jobs.py` - Jobs CRUD operations tests
  - `testing/postgres/common/operations/test_transactions.py` - Transactions query tests
  - `testing/postgres/test_core.py` - Database core utilities tests
- [x] Fixed failing balance test assertion (float vs string comparison)
- [x] Improve coverage of other low-coverage files

### Code Quality

- [x] Replace broad exception handlers with specific exceptions in requisitions.py
- [x] Fix the alembic failing autogenerating migration files

### Completed Tech Debt (January 2026)

- [x] Remove debug token printing from `providers/gocardless/api/core.py`
- [x] Simplify GoCardless credentials to env vars (removed SSM dependency)
- [x] Fix meaningless test assertions in orchestration tests
- [x] Remove orphaned S3 code from `aws/s3.py` (~250 lines)
- [x] Remove unused SSM module
- [x] Consolidate enum definitions to single source (`postgres/common/enums.py`)
- [x] De-duplicate API test fixtures to `conftest.py`
- [x] Consolidate `load_dotenv()` calls to single location
- [x] Update outdated S3/DuckDB comments in transactions endpoint
- [x] **Remove all AWS/S3 dependencies** - dbt now reads from PostgreSQL via DuckDB's postgres extension
- [x] Delete `src/aws/` directory entirely

---

## Phase 2.6: Transaction Tagging ✅

User-defined tags for categorising transactions. See PRD: `prds/complete/20260124-fullstack-transaction-tagging.md`

### Backend

- [x] `Tag` and `TransactionTag` models + migration
- [x] Tags CRUD API (`/api/tags`)
- [x] Transaction tagging endpoints (add/remove/bulk)
- [x] Tag filter on transaction list

### Frontend

- [x] Tags management page (`/settings/tags`)
- [x] Tag components (`TagChip`, `TagSelector`)
- [x] Transaction row tagging UI (inline add/remove tags)
- [x] Selection mode infrastructure for bulk operations
- [x] Filter transactions by tag dropdown

### Future (Not in Scope)

- [ ] Multi-tag support with cost splitting (e.g., split £100 grocery shop: £80 Food, £20 Household)
- [ ] Smart tag suggestions (ML-based)

#### Auto-Tagging with Standard Tags

When implementing auto-tagging, introduce a distinction between **standard tags** and **custom tags**:

Standard Tags (system-provided)

- Seeded on account creation via migration
- Consistent set used by auto-tagging rules
- Enable reliable analytics and reporting
- Cannot be deleted (only hidden/disabled)
- Suggested set: Groceries, Dining, Transport, Utilities, Entertainment, Shopping, Subscriptions, Health, Travel, Income, Transfers, Fees

Custom Tags (user-created)

- Created by user for personal categorisation
- Not used by auto-tagging rules (unless user creates a rule)
- Can be deleted freely

Auto-Tagging Rules

- Rule structure: condition(s) → standard tag
- Conditions: merchant name pattern, merchant category code, amount range, account
- Examples:
  - Merchant contains "TESCO" or "SAINSBURY" → Groceries
  - Merchant contains "UBER" or "TFL" → Transport
  - MCC code 5411 (Grocery Stores) → Groceries
- Rules have priority order (first match wins)
- User can override auto-assigned tags manually
- Consider a "learn from corrections" feature (user overrides train the model)

Schema Changes

- Add `is_standard` boolean to Tag model
- Add `TagRule` model: id, user_id, name, conditions (JSON), tag_id, priority, enabled
- Add `auto_tagged` boolean to TransactionTag to track which were auto-assigned

---

## Phase 2.7: Analytics & Visualisation

Charts and dashboards to understand spending patterns. Requires tagging (Phase 2.6).

### Backend ✅

- [x] dbt mart models with filter metadata (dim_accounts, dim_tags, fct_transactions, fct_daily_spending_by_tag, fct_monthly_trends)
- [x] DuckDB client for read-only analytics queries
- [x] Dataset discovery endpoints (list datasets, get schema from dbt metadata)
- [x] Generic dataset query endpoint (`/api/analytics/datasets/{id}/query`) - reads filter columns from dbt meta
- [x] Analytics refresh endpoint (trigger dbt via Dagster)

### Future Work

- [ ] `fct_daily_balance_history` mart model - requires unified balance table first (currently only raw gc_balances available)
- [ ] Export engine (Dagster job) - CSV/Parquet exports with parameterised filters, see plan file for design

### Frontend

- [ ] Charts and visualisations (spending by category, trends)
- [ ] Dashboard with key metrics
- [ ] Balance over time graphs
- [ ] Spending breakdown charts

---

## Phase 2.8: Misc UI Improvements

Improve the user experience and visual design of the app.

### Accounts

- [ ] Account config popup on the accounts page - convert the "Edit Account Name" to a settings cog
  - [ ] Min balance alerts etc.
  - [ ] Last sync date
- [ ] Account favourites/reordering (pin important accounts to top)

### Transactions

- [ ] Transaction detail view (more details button to create a modal)
- [ ] Split transactions (one payment → multiple categories - linked to tags)
- [ ] Recurring transaction indicators (visual badge for subscriptions)
- [ ] Date range presets ("This month", "Last 30 days", "This year")

### Dashboard

- [ ] Net worth summary (total across all accounts)
- [ ] Recent activity feed
- [ ] Upcoming bills/subscriptions

### General

- [ ] Mobile responsive improvements

---

## Phase 3: Complete Financial Picture

Expand beyond GoCardless to capture full net worth across all assets and liabilities.

### Unified Provider Architecture ✅

- [x] Provider-agnostic connections table (supports gocardless, trading212, vanguard)
- [x] Provider-agnostic accounts table
- [x] Institutions table for provider metadata
- [x] Dagster extraction assets (write to PostgreSQL)
- [x] Dagster sync pipeline (provider tables -> standardised tables)
- [x] Scheduled job with all GoCardless assets grouped together
- [x] Account type classification (bank/investment/trading)
- [x] Holdings table for investment positions
- [x] Transaction storage in PostgreSQL (gc_transactions)

### Manual Assets & Liabilities

Track items not available via APIs for complete net worth visibility.

#### Liabilities

- [ ] Student loan balance tracking
- [ ] Mortgage balance tracking
- [ ] Other loans and credit facilities

#### Assets

- [ ] Property valuations (manual entry with date)
- [ ] Vehicle values
- [ ] Other assets (collectibles, crypto held elsewhere, etc.)

### Investment Platforms

#### Vanguard Integration

- [ ] Research API/scraping options
- [ ] Handle MFA (via Telegram - see Phase 5)
- [ ] Extract portfolio holdings
- [ ] Extract transaction history
- [ ] dbt models for investment data

#### Trading212 Integration

- [ ] Research API availability
- [ ] Extract holdings and positions
- [ ] Extract transaction/trade history
- [ ] dbt models for trading data

---

## Phase 4: Budgeting & Goals

Financial planning features for tracking progress and controlling spending.

### Budget Tracking

- [ ] Monthly budget by category
- [ ] Spending vs budget dashboard
- [ ] Rollover/flexible budgets
- [ ] Income tracking and forecasting

### Savings Goals

- [ ] Target amount + deadline
- [ ] Progress tracking with projections
- [ ] Link goals to specific accounts
- [ ] Milestone celebrations

### Spending Limits & Alerts

- [ ] Category-based limits (e.g., dining £200/month)
- [ ] Warning thresholds (80%, 100%)
- [ ] Notification when approaching/exceeding

### Net Worth Tracking

- [ ] Track total net worth over time
- [ ] Set milestone targets
- [ ] Visualise progress across all accounts

### Forecasting

- [ ] Project future balances based on recurring income/expenses
- [ ] "What if" scenarios
- [ ] Runway calculations

---

## Phase 5: Telegram Integration

Proactive alerts and two-way communication. Required for Vanguard MFA.

### Bot Setup

- [ ] Bot configuration (leverage existing personal assistant project)
- [ ] MFA code relay for Vanguard/other integrations

### Notifications

- [ ] Balance alerts (low balance, large deposits)
- [ ] Transaction alerts (configurable thresholds)
- [ ] Weekly summary reports
- [ ] Budget/spending limit warnings

### Interactive Features

- [ ] Quick actions (categorise transaction, add note)
- [ ] Reminder acknowledgement

---

## Phase 6: Intelligence Layer

AI-powered features for insights and automation. Lower priority.

### Analytics & Insights

- [ ] Spending categorisation (ML-based)
- [ ] Weekly/monthly trend analysis
- [ ] Anomaly detection (unusual transactions)
- [ ] Subscription detection and review

### AI Features (AWS Bedrock)

- [ ] Natural language queries ("How much did I spend on groceries last month?")
- [ ] Budget allocation suggestions
- [ ] Spending pattern insights
- [ ] Financial health score

### Automation

- [ ] Rule-based transaction tagging
- [ ] Recurring transaction detection
- [ ] Bill prediction and reminders

---

## Out of Scope

Items explicitly not needed for this project:

- **CI/CD Pipeline**: This is a personal app; local `make check` is sufficient
- **Multi-user Support**: Single-user application
- **High Availability**: Runs locally or on personal server

---

## PRD Process

New features should have a PRD in `prds/` before implementation. See `prds/_template.md` for the format.

PRD naming convention: `prds/YYYYMMDD-{scope}-feature-name.md`

Once a PRD is fully implemented, move it to `prds/complete/`.

### Completed PRDs

- `20260123-backend-authentication.md` - JWT auth with refresh tokens
- `20260123-backend-bug-fixes.md` - Various bug fixes
- `20260123-backend-code-quality.md` - Linting, types, test coverage
- `20260123-backend-test-suite.md` - pytest infrastructure
- `20260123-frontend-authentication.md` - Login/logout flow
- `20260124-frontend-accounts-view.md` - Accounts list page
- `20260124-fullstack-accounts-api-integration.md` - Connect frontend to real API
- `20260124-backend-provider-sync.md` - Dagster sync pipeline, Postgres extraction, investment account fields
- `20260124-backend-unified-connections.md` - Provider-agnostic data layer
- `20260124-backend-gocardless-oauth.md` - GoCardless OAuth flow (create, callback, reauthorise endpoints)
- `20260124-frontend-gocardless-callback.md` - OAuth callback handling and toast notifications
- `20260124-fullstack-background-jobs-dagster.md` - Background jobs table, Dagster sync triggers, connection-scoped sync
- `20260124-fullstack-transaction-tagging.md` - User-defined tags for transactions
- `20260125-backend-analytics-visualisation.md` - Analytics API with dbt marts and DuckDB

### Implemented Without PRD

- Frontend transactions view - Day-grouped list with infinite scroll, filters (search, account, date range, amount range)
