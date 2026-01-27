# Roadmap

Personal Finances App with Automated Data Pipeline and AI Insights

## Vision

A self-hosted personal finance platform that aggregates all financial data in one place, provides intelligent insights, and proactively alerts on important financial events.

---

## Completed Phases

### Phase 1: Foundation ✅

Stabilise the existing data pipeline and improve core functionality.

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

### Phase 2: Frontend Overhaul ✅

Replace Streamlit with a modern Vue + Nuxt + Tailwind frontend backed by FastAPI.

#### Backend (FastAPI)

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

#### Frontend (Vue + Nuxt + Tailwind)

- [x] Project setup in `frontend/` directory
- [x] Tailwind theme and reusable components (AppButton, AppInput)
- [x] Authentication flow (login, logout, token refresh)
- [x] Auth middleware and Pinia store
- [x] Dashboard view (placeholder)
- [x] Accounts list view with balances and status indicators
- [x] Account display name editing (modal)
- [x] Connection management UI (add, rename, reauthorise, delete)
- [x] Transaction list with day grouping, infinite scroll, and filters

### Phase 2.5: Consolidation & Quality ✅

Address tech debt and improve code quality before adding new data sources.

- [x] Add missing test files (dependencies, jobs, transactions, core)
- [x] Fixed failing balance test assertion
- [x] Improve coverage of low-coverage files
- [x] Replace broad exception handlers with specific exceptions
- [x] Fix alembic autogenerate migration issues
- [x] Remove all AWS/S3 dependencies - dbt reads from PostgreSQL via DuckDB
- [x] Consolidate enum definitions, fixtures, and dotenv loading

### Phase 2.6: Transaction Tagging ✅

User-defined tags for categorising transactions.

- [x] `Tag` and `TransactionTag` models + migration
- [x] Tags CRUD API (`/api/tags`)
- [x] Transaction tagging endpoints (add/remove/bulk)
- [x] Tag filter on transaction list
- [x] Tags management page (`/settings/tags`)
- [x] Tag components (`TagChip`, `TagSelector`)
- [x] Transaction row tagging UI (inline add/remove tags)
- [x] Selection mode infrastructure for bulk operations

### Phase 2.7: Analytics Backend ✅

Charts and dashboards to understand spending patterns.

- [x] dbt mart models with filter metadata (dim_accounts, dim_tags, fct_transactions, fct_daily_spending_by_tag, fct_monthly_trends)
- [x] DuckDB client for read-only analytics queries
- [x] Dataset discovery endpoints (list datasets, get schema from dbt metadata)
- [x] Generic dataset query endpoint (`/api/analytics/datasets/{id}/query`)
- [x] Analytics refresh endpoint (trigger dbt via Dagster)

### Phase 2.8: UI Improvements ✅

Improve the user experience and visual design.

- [x] Account settings modal (display name, category, min balance threshold, last sync)
- [x] Transaction detail view (modal showing all fields, tag management)
- [x] Date range presets dropdown (This month, Last 30 days, This year, Custom)
- [x] Value filter dropdown (min/max amount)

### Phase 2.9: Dashboard & Analytics UI ✅

Home page overview and dedicated analytics section.

- [x] Rename "Dashboard" nav item to "Home" (`/` index route)
- [x] Add "Analytics" as top-level nav item (`/analytics`)
- [x] Fix net worth calculation (credit cards excluded - needs credit limit storage)
- [x] Net worth summary card
- [x] Key metrics cards (spending, vs last month, top category, transaction count)
- [x] Recent transactions list
- [x] Analytics page with period filter, bar/line/donut charts, table view
- [x] This month vs last month comparison view
- [x] Manual refresh button (triggers dbt build via Dagster)

### Unified Provider Architecture ✅

Provider-agnostic foundation for multiple data sources.

- [x] Provider-agnostic connections table (supports gocardless, trading212, vanguard)
- [x] Provider-agnostic accounts table
- [x] Institutions table for provider metadata
- [x] Dagster extraction assets (write to PostgreSQL)
- [x] Dagster sync pipeline (provider tables -> standardised tables)
- [x] Scheduled job with all GoCardless assets grouped together
- [x] Account type classification (bank/investment/trading)
- [x] Holdings table for investment positions
- [x] Transaction storage in PostgreSQL (gc_transactions)

---

## Phase 3: Analytics Polish

Quick wins to improve analytics accuracy and home page usefulness.

- [x] Exclude internal transfers from spending calculations (dbt model improvement)
- [x] Net worth trend indicator (sparkline or % change from previous month)
- [x] Metric cards click through to relevant analytics page sections
- [ ] Dynamic rounded x/y axis labels on charts (currently spending by category squashes labels too close together)
- [ ] DBT throwing errors on dbt build in dagster for column lineage (id column)
- [ ] Axis doing weird things when clicking "Compare to previous period"
- [ ] Count not working on transactions table
- [ ] Last sync time on account settings modal not working
- [ ] Credit card balance varies from Amex to Nationwide (maybe based on if balance is negative?)

---

## Phase 4: Smart Tagging ✅

Automated categorisation and transaction splitting. Foundation for accurate budgeting.

### Standard Tags ✅

- [x] Add `is_standard` and `is_hidden` booleans to Tag model
- [x] Seed standard tags on account creation (Groceries, Dining, Transport, Utilities, Entertainment, Shopping, Subscriptions, Health, Travel, Income, Transfers, Fees)
- [x] Standard tags cannot be deleted (only hidden)
- [x] Backfill migration for existing users
- [ ] Remove ability to add tags on the transactions view

### Auto-Tagging Rules ✅

- [x] `TagRule` model: id, user_id, name, conditions (JSON), tag_id, priority, enabled, account_id
- [x] Add `is_auto` and `rule_id` to TransactionTag
- [x] Rule conditions: business name pattern (contains/exact/not contains), description pattern, amount range, account filter
- [x] Priority ordering (first match wins)
- [x] User can override auto-assigned tags
- [x] Rules management UI (`/settings/rules`)
- [x] Test rule endpoint (preview matching transactions)
- [x] Bulk apply rules to untagged transactions
- [x] Test conditions before saving rule
- [x] "From account" is a weird name on create rule modal?
- [x] Search box on Apply Tag button, close box after selecting tag on single select
- [x] Removal of min value doesn't work
- [x] Need to show "Auto tagged" on the transaction detail modal

### Split Transactions ✅

- [x] `TransactionSplit` model for splitting amounts across tags
- [x] Split validation (amounts must sum to transaction total)
- [x] UI for managing splits with percentage slider
- [x] Analytics correctly handles split amounts per tag (dbt model)
- [x] Unify tags and splits (all tagging via splits, default 100%)

### Future

- [ ] Multi-rule match notifications (alert when transaction matches multiple rules, built-in notification system)
- [ ] Smart tag suggestions (ML-based, learn from user corrections)

---

## Phase 5: Recurring Transactions

Identify subscriptions and predict upcoming bills.

- [ ] Recurring transaction detection algorithm
- [ ] Visual indicators/badges for subscriptions on transaction list
- [ ] Upcoming bills/subscriptions widget on home page
- [ ] Subscription management view (list all detected subscriptions)
- [ ] Mark false positives / confirm recurring status

### General Transport Improvements

- [x] Transactions filtering needs to continue requesting for a given filter if there isn't max values showing

---

## Phase 6: Budgeting & Goals

Financial planning features for tracking progress and controlling spending.

### Budget Tracking

- [ ] Monthly budget by category (tag)
- [ ] Spending vs budget dashboard
- [ ] Rollover/flexible budgets
- [ ] Income tracking

### Savings Goals

- [ ] Target amount + deadline
- [ ] Progress tracking with projections
- [ ] Link goals to specific accounts

### Spending Limits & Alerts

- [ ] Category-based limits (e.g., dining £200/month)
- [ ] Warning thresholds (80%, 100%)
- [ ] Notification when approaching/exceeding (via Telegram)

---

## Phase 7: Telegram Integration

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

## Phase 8: Investment Platforms

Expand beyond bank accounts to see full investment portfolio.

### Vanguard Integration

- [ ] Research API/scraping options
- [ ] Handle MFA (via Telegram)
- [ ] Extract portfolio holdings
- [ ] Extract transaction history
- [ ] dbt models for investment data

### Trading212 Integration

- [ ] Research API availability
- [ ] Extract holdings and positions
- [ ] Extract transaction/trade history
- [ ] dbt models for trading data

---

## Phase 9: Balance History & Net Worth

Track financial progress over time. Requires unified balance table.

- [ ] Unified balance table (consolidate provider-specific balance tables)
- [ ] `fct_daily_balance_history` dbt mart model
- [ ] Balance over time graphs
- [ ] Net worth tracking over time
- [ ] Set milestone targets
- [ ] Forecasting (project future balances based on recurring income/expenses)
- [ ] "What if" scenarios
- [ ] Runway calculations

---

## Phase 10: Low Priority & Polish

Items to tackle when core functionality is complete.

### Mobile Responsiveness

- [ ] Responsive navigation (hamburger menu)
- [ ] Home page mobile layout
- [ ] Analytics page mobile layout
- [ ] Accounts page mobile layout
- [ ] Transactions page mobile layout
- [ ] Settings pages mobile layout

### Export Engine

- [ ] Dagster job for CSV/Parquet exports
- [ ] Parameterised filters (date range, accounts, tags)

### Manual Assets & Liabilities

- [ ] Student loan balance tracking
- [ ] Mortgage balance tracking
- [ ] Property valuations (manual entry with date)
- [ ] Vehicle values
- [ ] Other assets/liabilities

### AI Features

- [ ] Natural language queries ("How much did I spend on groceries last month?")
- [ ] Budget allocation suggestions
- [ ] Spending pattern insights
- [ ] Anomaly detection (unusual transactions)
- [ ] Financial health score

### Backlog

- [ ] Historical data backfill tooling
- [ ] Rate limiting for logging in, and add lock user after 10 failed attempts
- [ ] Admin page
  - [ ] See current jobs without going into Dagster UI
  - [ ] Trigger manual syncs - remove from the front UI

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
- `20260125-frontend-transaction-detail-modal.md` - Transaction detail modal with tag management
- `20260125-frontend-transaction-filters.md` - Date presets and value filter dropdowns
- `20260125-frontend-analytics-page.md` - Analytics page with charts, filters, and comparison view

### Implemented Without PRD

- Frontend transactions view - Day-grouped list with infinite scroll, filters (search, account, date range, amount range)
- Account settings modal - Category selection, min balance threshold, last sync date display
