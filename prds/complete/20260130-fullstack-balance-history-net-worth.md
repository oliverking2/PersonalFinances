# PRD: Balance History & Net Worth

**Status**: Draft
**Author**: Claude
**Created**: 2026-01-30
**Updated**: 2026-01-30

---

## Overview

Track financial progress over time by capturing historical balance snapshots, visualising net worth trends, and projecting future cash flow based on recurring income and expenses.
This enables users to see where their money came from, where it's going, and when they'll hit financial milestones.

## Problem Statement

Currently, the app only stores the latest balance for each account. Users cannot:

- See how their net worth has changed over time
- Understand balance trends for individual accounts
- Project when they'll reach savings goals or run out of runway
- Identify recurring income patterns (salary, regular transfers)

Without historical data and forecasting, users lack the visibility needed for financial planning.

## Goals

- Capture balance snapshots at every sync to build historical data
- Visualise net worth and account balances over time
- Detect recurring income patterns (complement to subscription detection)
- Project future balances based on known recurring transactions
- Enable milestone targets and runway calculations
- Support "what if" scenario planning

## Non-Goals

- Real-time balance updates (daily sync is sufficient)
- ML-based forecasting (pattern-based projection is sufficient for single-user app)
- Multi-currency net worth aggregation (convert to GBP for now)
- Investment performance analytics (separate from balance tracking)

---

## User Stories

1. **As a** user, **I want to** see my net worth over time, **so that** I can track my financial progress.

2. **As a** user, **I want to** see individual account balance history, **so that** I can understand trends per account.

3. **As a** user, **I want to** set milestone targets (e.g., £50k net worth by December), **so that** I can track progress towards goals.

4. **As a** user, **I want to** see when my salary arrives automatically detected, **so that** I can include it in forecasts without manual entry.

5. **As a** user, **I want to** project my balance over the next 3 months, **so that** I can plan large purchases.

6. **As a** user, **I want to** know "when will I hit £0" (runway), **so that** I can plan accordingly.

7. **As a** user, **I want to** run "what if" scenarios (e.g., cancel Netflix, add new £100/month expense), **so that** I can make informed decisions.

8. **As a** user, **I want to** manually enter expected irregular income (freelance payments), **so that** forecasts include income that doesn't follow a pattern.

9. **As a** user, **I want to** manually enter planned one-off expenses (annual insurance, holiday), **so that** forecasts account for large known outgoings.

---

## Proposed Solution

### High-Level Design

#### Sub-phase 8.1: Balance History Foundation (MVP)

- New `balance_snapshots` table (append-only, provider-agnostic)
- Modify sync operations to append snapshots after each sync
- Create `fct_daily_balance_history` dbt mart (aggregate to daily grain with gap-filling)
- Basic "Balance Over Time" chart

#### Sub-phase 8.2: Net Worth History

- Create `fct_net_worth_history` dbt mart (sum of all account balances per day)
- Net worth trend chart component
- Enhanced home page MetricCard with sparkline

#### Sub-phase 8.3: Recurring Income Detection

- Extend `int_recurring_candidates` to detect positive amounts (income patterns)
- Add `direction` column to `RecurringPattern` model
- Surface income patterns in existing subscriptions UI

#### Sub-phase 8.4: Forecasting & Cash Flow

- Create `fct_cash_flow_forecast` dbt model (combine recurring income + expenses)
- API endpoints for forecast data and runway calculation
- Cash flow projections UI component

#### Sub-phase 8.5: Milestones, Scenarios & Polish

- `financial_milestones` table for target amounts with deadlines
- "What if" scenario API (exclude/modify recurring patterns)
- Planned transactions for irregular income/expenses not auto-detected
- Dashboard integration

### Data Model

#### `balance_snapshots` (New Table)

```sql
CREATE TABLE balance_snapshots (
    id SERIAL PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    -- Balance fields (unified across providers)
    balance_amount NUMERIC(18, 2) NOT NULL,
    balance_currency VARCHAR(3) NOT NULL,
    balance_type VARCHAR(50),  -- interimAvailable, cash, etc.

    -- For investment accounts
    total_value NUMERIC(18, 2),
    unrealised_pnl NUMERIC(18, 2),

    -- Metadata
    source_updated_at TIMESTAMPTZ,  -- last_change_date from provider
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_balance_snapshots_account_captured ON balance_snapshots(account_id, captured_at);
CREATE INDEX idx_balance_snapshots_captured_at ON balance_snapshots(captured_at);
```

**Design Rationale:**

- Append-only: No updates, just inserts. Preserves full history.
- Provider-agnostic: Unified structure for all account types (GoCardless, Trading212, future Vanguard).
- `captured_at` is when we recorded it; `source_updated_at` is when the bank says it changed.
- Grain: One snapshot per sync per account (dbt aggregates to daily).

#### `financial_milestones` (New Table)

```sql
CREATE TABLE financial_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name VARCHAR(100) NOT NULL,
    target_amount NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',

    -- Scope: null = net worth, account_id = specific account
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,

    target_date TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, reached, dismissed
    reached_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_milestones_user_id ON financial_milestones(user_id);
```

#### `planned_transactions` (New Table)

```sql
CREATE TABLE planned_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name VARCHAR(100) NOT NULL,  -- "Freelance Client A", "Annual Insurance"
    amount NUMERIC(18, 2) NOT NULL,  -- Positive = income, Negative = expense
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',

    frequency VARCHAR(20),  -- null = one-time, weekly, monthly, quarterly, annual
    next_expected_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,  -- Optional: when recurring entry should stop

    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    notes TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_planned_transactions_user_id ON planned_transactions(user_id);
CREATE INDEX idx_planned_transactions_next_date ON planned_transactions(next_expected_date);
```

**Design notes:**

- Positive `amount` = income, negative = expense (matches transaction convention)
- `frequency: null` = one-time event (e.g., annual insurance payment)
- `end_date` allows recurring entries to expire (e.g., 6-month freelance contract)

#### `recurring_patterns` (Modification)

```sql
ALTER TABLE recurring_patterns ADD COLUMN direction VARCHAR(10) NOT NULL DEFAULT 'expense';
-- Values: 'expense', 'income'
```

### dbt Models

#### `fct_daily_balance_history`

- Aggregates balance snapshots to daily grain (latest snapshot per day)
- Forward-fills gaps (if no sync for a day, use previous day's balance)
- Includes daily change calculation
- Filter metadata: `date_column: balance_date`, `account_id_column: account_id`

#### `fct_net_worth_history`

- Sums all account balances per user per day
- Includes daily change, 7-day rolling average, month start comparison
- Filter metadata: `date_column: balance_date`

#### `fct_cash_flow_forecast`

- Projects future balances based on recurring patterns
- Combines detected expenses (negative) and income (positive)
- 90-day forward projection by default
- Includes cumulative running total

#### `int_recurring_candidates` (Modification)

- Remove `WHERE TXN.AMOUNT < 0` filter to include income
- Add `direction` column based on amount sign
- Adjust confidence scoring for income patterns (may need different thresholds)

### API Endpoints

| Method | Path                              | Description                                 |
|--------|-----------------------------------|---------------------------------------------|
| GET    | /api/analytics/balance-history    | Get balance history for accounts            |
| GET    | /api/analytics/net-worth-history  | Get net worth history                       |
| GET    | /api/forecasting/forecast         | Get cash flow forecast (next N days)        |
| GET    | /api/forecasting/runway           | Calculate days until balance threshold      |
| POST   | /api/forecasting/scenario         | Run what-if scenario                        |
| GET    | /api/milestones                   | List milestones                             |
| POST   | /api/milestones                   | Create milestone                            |
| PATCH  | /api/milestones/{id}              | Update milestone                            |
| DELETE | /api/milestones/{id}              | Delete milestone                            |
| GET    | /api/planned-transactions         | List planned transactions (income/expenses) |
| POST   | /api/planned-transactions         | Create planned transaction                  |
| PATCH  | /api/planned-transactions/{id}    | Update planned transaction                  |
| DELETE | /api/planned-transactions/{id}    | Delete planned transaction                  |

### UI/UX

#### New Components

- `NetWorthChart.vue` - Line/area chart for net worth over time with milestone markers
- `BalanceHistoryChart.vue` - Multi-line chart for individual account balances
- `CashFlowForecast.vue` - Dual-axis chart (bars for income/expenses, line for projected balance)
- `MilestoneCard.vue` - Progress card showing target vs current with days remaining
- `RunwayWidget.vue` - Days until threshold crossed, "best day for big purchase"

#### Page Updates

- **Home page**: Add net worth sparkline to MetricCard, RunwayWidget to dashboard
- **New `/net-worth`**: Full net worth chart, account breakdown, milestone progress
- **New `/forecasting`**: Cash flow forecast, upcoming income/expenses, scenario builder
- **Subscriptions page**: Show income patterns alongside expenses

---

## Technical Considerations

### Dependencies

**Internal modules affected:**

- `backend/src/postgres/common/operations/sync.py` - Append balance snapshots
- `backend/src/orchestration/` - No changes to extraction, only sync
- `backend/dbt/models/3_mart/int_recurring_candidates.sql` - Income detection
- `frontend/app/components/analytics/` - New chart components

**External libraries:**

- None new required (ApexCharts already available for charts)

### Migration

**Backfill strategy:**

1. Create `balance_snapshots` table (migration)
2. Run one-time Dagster job to create initial snapshots from current Account balances
3. All future syncs append normally
4. Optional: Migrate Trading212's existing `t212_cash_balances` history (low priority)

**Rationale:** Historical GoCardless balances don't exist anyway. Clean start is pragmatic.

### Performance

- `balance_snapshots` will grow linearly (~1 row/account/day with daily sync)
- 10 accounts × 365 days = 3,650 rows/year - negligible
- Indexes on (account_id, captured_at) for efficient range queries
- dbt aggregation handles heavy lifting, API queries pre-aggregated marts

### Security

- All endpoints require authentication
- User can only see their own balance history (user_id filtering in dbt/API)
- No new external API exposure

---

## Implementation Plan

### Sub-phase 8.1: Balance History Foundation

- [ ] Create `balance_snapshots` SQLAlchemy model + migration
- [ ] Create balance snapshot operations (insert)
- [ ] Modify `sync_gocardless_account()` to append snapshot
- [ ] Modify `sync_trading212_account()` to append snapshot
- [ ] Create dbt source model `src_balance_snapshots`
- [ ] Create dbt mart model `fct_daily_balance_history`
- [ ] Add schema.yml filters for API integration
- [ ] Add `/api/analytics/balance-history` endpoint
- [ ] Create `BalanceHistoryChart.vue` component
- [ ] Add balance history section to analytics page

### Sub-phase 8.2: Net Worth History

- [ ] Create dbt mart model `fct_net_worth_history`
- [ ] Add `/api/analytics/net-worth-history` endpoint
- [ ] Create `NetWorthChart.vue` component
- [ ] Create `/net-worth` page
- [ ] Enhance home page MetricCard with sparkline link

### Sub-phase 8.3: Recurring Income Detection

- [ ] Add `direction` column to `RecurringPattern` model + migration
- [ ] Extend `int_recurring_candidates.sql` to detect income (remove amount < 0 filter)
- [ ] Update `fct_recurring_patterns.sql` with direction column
- [ ] Update subscriptions page to show income patterns
- [ ] Add income filter toggle to subscriptions list

### Sub-phase 8.4: Forecasting & Cash Flow

- [ ] Create dbt mart model `fct_cash_flow_forecast`
- [ ] Add `/api/forecasting/forecast` endpoint
- [ ] Add `/api/forecasting/runway` endpoint
- [ ] Create `planned_transactions` table + operations + CRUD endpoints
- [ ] Create `CashFlowForecast.vue` component
- [ ] Create `RunwayWidget.vue` component
- [ ] Create `/forecasting` page
- [ ] UI for managing planned transactions (income and expenses)

### Sub-phase 8.5: Milestones, Scenarios & Polish

- [ ] Create `financial_milestones` table + operations + CRUD endpoints
- [ ] Add milestone markers to `NetWorthChart.vue`
- [ ] Create `MilestoneCard.vue` component
- [ ] Add `/api/forecasting/scenario` endpoint
- [ ] Add scenario builder UI to forecasting page
- [ ] Add RunwayWidget to home page
- [ ] Documentation updates

---

## Testing Strategy

- [ ] Unit tests for balance snapshot operations (insert, query by date range)
- [ ] Unit tests for milestone CRUD operations
- [ ] Unit tests for planned transaction CRUD operations
- [ ] Integration tests for sync operations appending snapshots
- [ ] dbt tests for mart models (not null, unique, relationships)
- [ ] API tests for new endpoints (auth, filtering, edge cases)
- [ ] Manual testing: verify charts render correctly with various data scenarios

---

## Rollout Plan

1. **Development**: Implement sub-phases incrementally, local testing
2. **Validation**: `make check` passes in backend and frontend
3. **Production**: Deploy, trigger initial balance snapshot backfill, verify data appears in charts

---

## Open Questions

- [x] ~~Should milestones support multiple targets?~~ → No, single target per milestone (create multiple milestones if needed)
- [x] ~~Should runway calculations consider scheduled one-time expenses?~~ → Yes, via `planned_transactions` table
- [ ] Should "what if" scenarios be saveable for comparison?
- [ ] How to handle currency conversion for multi-currency accounts in net worth?

---

## References

- `fct_daily_spending_by_tag.sql` - Reference for daily aggregation pattern with gap-filling
- `fct_recurring_patterns.sql` - Reference for recurring pattern detection
- `DailySpendingTrend.vue` - Reference for time-series chart component
- `MetricCard.vue` - Reference for dashboard summary cards
