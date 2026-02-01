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
- [x] Dynamic rounded x/y axis labels on charts (currently spending by category squashes labels too close together)
- [x] DBT throwing errors on dbt build in dagster for column lineage (id column)
- [x] Axis doing weird things when clicking "Compare to previous period"
- [x] Count not working on transactions table
- [x] Last sync time on account settings modal not working
- [x] Credit card balance varies from Amex to Nationwide (maybe based on if balance is negative?)

---

## Phase 4: Smart Tagging ✅

Automated categorisation and transaction splitting. Foundation for accurate budgeting.

### Standard Tags ✅

- [x] Add `is_standard` and `is_hidden` booleans to Tag model
- [x] Seed standard tags on account creation (Groceries, Dining, Transport, Utilities, Entertainment, Shopping, Subscriptions, Health, Travel, Income, Transfers, Fees)
- [x] Standard tags cannot be deleted (only hidden)
- [x] Backfill migration for existing users

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

---

## Phase 5: Recurring Transactions ✅

Identify subscriptions and predict upcoming bills.

- [x] Recurring transaction detection algorithm (dbt model)
- [x] Visual indicators/badges for subscriptions on transaction list
- [x] Upcoming bills/subscriptions widget on home page
- [x] Subscription management page (`/subscriptions`)
- [x] Confirm/dismiss/pause/restore patterns
- [x] Dagster sync job (auto-runs after dbt builds)
- [x] Subscription detail view with linked transactions
- [x] Transactions filtering needs to continue requesting for a given filter if there isn't max values showing

---

## Phase 6: Budgeting & Goals ✅

Financial planning features for tracking progress and controlling spending.

### Budget Tracking ✅

- [x] Monthly budget by category (tag)
- [x] Spending vs budget progress bar
- [x] Budget summary widget on home page
- [x] Warning thresholds (configurable, default 80%)
- [x] In-app alerts for warning/exceeded budgets

### Savings Goals ✅

- [x] Target amount + deadline
- [x] Progress tracking with ring indicator
- [x] Manual contributions
- [x] Link goals to specific accounts (optional)
- [x] Goal states (active, paused, completed, cancelled)
- [x] Goals summary widget on home page

### Spending Alerts ✅

- [x] `SpendingAlert` model with deduplication per budget/period
- [x] Alert types: budget_warning, budget_exceeded
- [x] Alert badge in header with pending count
- [x] Alert dropdown with acknowledge actions
- [x] Dagster job to check budgets and generate alerts

---

## Phase 7: Telegram Integration ✅

Proactive alerts and two-way communication. Required for Vanguard MFA.

### Core Infrastructure ✅

- [x] Telegram client module (send messages, receive updates)
- [x] Telegram config via pydantic-settings (`TELEGRAM_BOT_TOKEN`, etc.)
- [x] Polling runner for receiving messages
- [x] `wait_for_reply()` helper for 2FA flows
- [x] Polling cursor persistence in database
- [x] Migration for telegram_polling_cursor table
- [x] Convert telegram tests to pytest style
- [x] Add `telegram_chat_id` to User model (multi-user support)
- [x] API endpoints to link/verify/unlink Telegram account (`/api/user/telegram`)
- [x] Bot command handlers (`/start`, `/link`, `/status`, `/help`)
- [x] User settings page for linking Telegram account (`/settings/account`)

### In-App Notification System ✅

- [x] `Notification` model (type, title, message, read, created_at, metadata)
- [x] Notifications API (list, mark read, mark all read)
- [x] Notification bell icon in header with unread count
- [x] Notification dropdown/panel
- [x] Auto-create notifications for: export complete, sync complete, budget warnings
- [x] Replace current alert system with unified notifications

### Export Engine ✅

- [x] Dagster job for CSV/Parquet exports (S3 storage, signed URLs)
- [x] Parameterised filters (date range, accounts, tags)
- [x] Telegram notification on completion
- [x] Datasets page UI with export modal
- [x] Export history page (view past exports, regenerate download URLs)

### Trading212 Integration ✅

- [x] Research API availability
- [x] Extract holdings and positions
- [x] Extract transaction/trade history
- [x] dbt models for trading data

---

## Phase 8: Balance History & Net Worth ✅

Track financial progress over time.

### Balance History ✅

- [x] `balance_snapshots` table (append-only, captured on each sync)
- [x] `fct_daily_balance_history` dbt mart model (gap-filled time series)
- [x] Balance history chart (BalanceHistoryChart component)

### Net Worth Tracking ✅

- [x] `fct_net_worth_history` dbt mart model (aggregated net worth with rolling averages)
- [x] Net worth tracking page (`/net-worth`) with period filters and account breakdown
- [x] Net worth chart (NetWorthChart component) with 7-day rolling average

### Income Detection ✅

- [x] Recurring income detection (direction column on recurring patterns)
- [x] Updated subscriptions page to show both income and expenses
- [x] Income/expense summary in recurring patterns

### Forecasting ✅

- [x] `fct_cash_flow_forecast` dbt model (90-day projection)
- [x] Forecasting API endpoints (`/api/analytics/forecast`, `/api/analytics/forecast/weekly`)
- [x] Cash flow forecast chart (CashFlowForecastChart component)
- [x] Forecasting page (`/forecasting`) with summary cards and weekly view

### Milestones ✅

- [x] `financial_milestones` table with CRUD operations
- [x] Milestones API endpoints (`/api/milestones`)
- [x] Milestone markers on net worth chart

### Planned Transactions ✅

- [x] `planned_transactions` table for manual income/expenses
- [x] Planned transactions API endpoints (`/api/planned-transactions`)

### Home Page Enhancements ✅

- [x] Net worth sparkline in metric card
- [x] Financial runway widget (days until balance threshold)

---

## Phase 9: Mobile Responsiveness

Make the app usable on mobile devices.

- [ ] Responsive navigation (hamburger menu)
- [ ] Home page mobile layout
- [ ] Transactions page mobile layout
- [ ] Analytics page mobile layout
- [ ] Accounts page mobile layout
- [ ] Settings pages mobile layout

---

## Phase 10: Recurring Transaction Polish

Improve subscription detection accuracy and usability.

### Recurring Patterns Redesign ✅

Shifted from opt-out (detection creates patterns, user dismisses) to opt-in (detection suggests, user accepts):

- [x] New status model: `pending` → `active` → `paused` / `cancelled`
- [x] New source field: `detected` vs `manual`
- [x] Unique constraint: one pattern per transaction (prevents double-counting)
- [x] Dedicated matching columns: `merchant_contains`, `amount_tolerance_pct`
- [x] Detection metadata: `confidence_score`, `detection_reason`
- [x] API endpoints for accept/pause/resume/cancel workflow
- [x] Create pattern from selected transactions
- [x] Relink transactions after editing rules

### Remaining Tasks

- [x] Improve confidence calculation (current formula too harsh for consistent payments)
- [x] Separate patterns by amount bucket (Apple £4.99 and £2.99 should be different) - Already in dbt
- [x] Allow editing expected amount when subscription price changes - Already supported
- [x] Fuzzy merchant name matching (handle slight variations in merchant names)
- [x] Add pagination to pattern transactions endpoint (currently returns all)
- [x] Allow adjusting detected frequency (e.g., detected fortnightly but actually weekly)
- [x] Add "Edit Pattern" button to subscription detail view - Already exists
- [x] Add "Create Pattern" button to subscription list view
- [x] Migration to clear out old patterns (run after applying changes above)
- [x] New subscriptions don't get picked up soon enough - Solved by Create Pattern button

### Addressed by Redesign

The following issues from the previous architecture have been resolved:

1. **Transaction-to-Pattern Linking** - Now uses explicit linking via `recurring_pattern_transactions` table with unique constraint per transaction
2. **Variable Descriptions** - Added `normalize_for_matching()` that strips dates, reference numbers, and variable parts
3. **Pattern Key Migration** - Replaced fragile compound keys with separate `name` and `merchant_contains` fields
4. **Multiple Patterns for Same Merchant** - Patterns now have user-editable `name` field separate from matching rules
5. **Manual Pattern Creation** - Implemented via `create_pattern_from_transactions` API

---

## Phase 11: Budget Enhancements

More flexible budgeting options.

- [ ] Rollover/flexible budgets (unused budget carries forward)
- [ ] Weekly/annual budget periods
- [ ] Incorporate budgets into cash flow forecast (project when budgets will be exceeded)

---

## Phase 12: Lower Priority

Items to tackle when higher priority work is complete.

### Manual Assets & Liabilities

- [ ] Student loan balance tracking
- [ ] Mortgage balance tracking
- [ ] Property valuations (manual entry with date)
- [ ] Vehicle values
- [ ] Other assets/liabilities

### Settings - Jobs

- [ ] See current jobs without going into Dagster UI
- [ ] Trigger manual syncs - remove from the front UI

### Telegram Notifications

- [ ] Balance alerts (low balance, large deposits)
- [ ] Transaction alerts (configurable thresholds)
- [ ] Weekly summary reports
- [ ] Budget/spending limit warnings via Telegram
- [ ] MFA code relay for Vanguard/other integrations
- [ ] Manual Asset/Liability reminders - send reminders to update value

### Vanguard Integration

- [ ] Research API/scraping options
- [ ] Handle MFA (via Telegram)
- [ ] Extract portfolio holdings
- [ ] Extract transaction history
- [ ] dbt models for investment data

### Smart Tagging Enhancements

- [ ] Multi-rule match notifications (alert when transaction matches multiple rules)
- [ ] Smart tag suggestions (ML-based, learn from user corrections)

### AI Features

- [ ] Natural language queries ("How much did I spend on groceries last month?")
- [ ] Budget allocation suggestions
- [ ] Spending pattern insights
- [ ] Anomaly detection (unusual transactions)
- [ ] Financial health score

### Proactive Insights

- [ ] Spending velocity alerts ("You've spent £X in the first 10 days, Y% higher than usual")
- [ ] Category trend detection ("Groceries spending up 15% over 3 months")

### Backlog

- [ ] Historical data backfill tooling
- [x] Rate limiting for logging in, and add lock user after 10 failed attempts

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
- `20260127-fullstack-budgeting-goals.md` - Budgets, savings goals, and spending alerts
- `20260127-fullstack-recurring-transactions.md` - Recurring transaction detection and subscription management
- `20260130-fullstack-balance-history-net-worth.md` - Balance history, net worth tracking, forecasting, milestones
- `20260131-fullstack-recurring-patterns-redesign.md` - Opt-in recurring patterns, status workflow, matching rules

### Implemented Without PRD

- Frontend transactions view - Day-grouped list with infinite scroll, filters (search, account, date range, amount range)
- Account settings modal - Category selection, min balance threshold, last sync date display
