# Roadmap

Personal Finances App with Automated Data Pipeline and AI Insights

## Vision

A self-hosted personal finance platform that aggregates all financial data in one place, provides intelligent insights, and proactively alerts on important financial events.

---

## Phase 1: Foundation

Stabilise the existing data pipeline and improve core functionality.

### Completed

- [x] GoCardless open banking integration
- [x] PostgreSQL for metadata storage
- [x] S3 storage for transaction data (Parquet)
- [x] Dagster orchestration for data extraction
- [x] dbt + DuckDB for transformations
- [x] Basic Streamlit UI for account management

### In Progress

- [ ] Scheduled account refresh via Dagster
- [ ] Link expiry handling and re-authentication flow

### Backlog

- [ ] Improve error handling in GoCardless API client
- [ ] Add retry logic for failed extractions
- [ ] Historical data backfill tooling
- [ ] Data quality checks in dbt (see `prds/20260123-data-dbt-improvements.md`)

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
- [ ] Create connection endpoint (GoCardless OAuth flow)
- [ ] Reauthorise connection endpoint
- [ ] Transaction endpoints (list, search, filter)
- [ ] Analytics endpoints (aggregations from dbt marts)

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
- [ ] Charts and visualisations (spending by category, trends)

> **Note**: Frontend currently uses mock data for connections, accounts, and transactions. Backend endpoints for create/reauthorise connection and transactions are still in progress.

### Infrastructure

- [ ] Docker setup for frontend
- [ ] Nginx reverse proxy configuration
- [ ] Environment-based configuration

---

## Phase 3: Additional Data Sources

Expand beyond GoCardless to include investment and trading platforms.

### Unified Provider Architecture

- [x] Provider-agnostic connections table (supports gocardless, trading212, vanguard)
- [x] Provider-agnostic accounts table
- [x] Institutions table for provider metadata
- [ ] Dagster sync pipeline (provider tables → standardised tables)

### Vanguard Integration

- [ ] Research API/scraping options
- [ ] Handle MFA (potentially via Telegram for code input)
- [ ] Extract portfolio holdings
- [ ] Extract transaction history
- [ ] dbt models for investment data

### Trading212 Integration

- [ ] Research API availability
- [ ] Extract holdings and positions
- [ ] Extract transaction/trade history
- [ ] dbt models for trading data

### Manual Import

- [ ] CSV import functionality
- [ ] Template for common bank statement formats
- [ ] Deduplication logic
- [ ] Historical data upload UI

### Manual Costs

- [ ] Student loans
- [ ] Mortgage payments

### Financial Planning

- [ ] Budget tracking
- [ ] Planned income
- [ ] Forecasting

---

## Phase 4: Intelligence Layer

Add AI-powered features for insights and automation.

### Analytics & Insights

- [ ] Spending categorisation (ML-based)
- [ ] Weekly/monthly trend analysis
- [ ] Anomaly detection (unusual transactions)
- [ ] Subscription detection and review
- [ ] Net worth tracking over time

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

## Phase 5: Notifications & Interaction

Proactive alerts and two-way communication via Telegram.

### Telegram Integration

- [ ] Bot setup and configuration
- [ ] Balance alerts (low balance, large deposits)
- [ ] Transaction alerts (configurable thresholds)
- [ ] Weekly summary reports
- [ ] MFA code relay for external integrations
- [ ] Integration via the current AI Personal Assistant managed in a different project.

### Interactive Features

- [ ] Query finances via chat
- [ ] Quick actions (categorise transaction, add note)
- [ ] Reminder acknowledgement

---

## Out of Scope

Items explicitly not needed for this project:

- **CI/CD Pipeline**: This is a personal app; local `make check` is sufficient
- **Multi-user Support**: Single-user application
- **High Availability**: Runs locally or on personal server

---

## Ideas & Future Considerations

Items not yet scheduled but worth exploring:

- **Data Lake Architecture**: Iceberg tables for better versioning and time travel
- **Goal Tracking**: Savings goals with progress tracking

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

### In Progress PRDs

- `20260124-backend-unified-connections.md` - Provider-agnostic data layer

### Implemented Without PRD

- Frontend transactions view - Day-grouped list with infinite scroll, filters (search, account, date range, amount range)
