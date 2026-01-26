# PRD: Budgeting & Financial Goals

**Status**: Draft
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-25

---

## Overview

A comprehensive financial planning system enabling users to set monthly budgets by category (tag), track progress toward savings goals, and receive proactive alerts when approaching or exceeding spending limits. This builds on the existing tag-based analytics to provide actionable financial insights.

## Problem Statement

Users can view historical spending by category but lack tools to:

1. **Plan ahead** - No way to set target spending by category
2. **Track savings** - No mechanism to define and monitor savings goals
3. **Get proactive alerts** - Users must manually check analytics; no push notifications for overspending

Without these features, the app is reactive rather than proactive, missing opportunities to help users achieve financial goals.

## Goals

- Enable monthly budget creation by tag with progress tracking
- Support flexible budgets (rollover unspent amounts, cover from other categories)
- Provide savings goal tracking with deadline-based projections
- Alert users via Telegram when approaching/exceeding limits
- Integrate seamlessly with existing analytics architecture (dbt marts)

## Non-Goals

- AI-generated budget suggestions (future phase)
- Automatic budget adjustment based on income changes
- Shared/household budgets (single-user app)
- Daily budget periods (too granular)
- Goal contributions from external accounts (only tracks linked internal accounts)
- Spending alerts before Telegram integration (Phase 7 prerequisite)

---

## User Stories

1. **As a** user, **I want to** set a budget for each spending category (weekly, monthly, or quarterly), **so that** I can control my spending at the granularity that makes sense for me
2. **As a** user, **I want to** see how much I've spent vs my budget this period, **so that** I know if I'm on track
3. **As a** user, **I want** unspent budget to roll over to next month, **so that** I'm not penalised for frugal months
4. **As a** user, **I want to** track my income against a target, **so that** I can monitor earnings
5. **As a** user, **I want to** create a savings goal with a target amount and deadline, **so that** I have clear financial targets
6. **As a** user, **I want to** see projected goal completion dates based on my savings rate, **so that** I can adjust my strategy
7. **As a** user, **I want to** link a savings goal to a specific account, **so that** the balance tracks my progress
8. **As a** user, **I want to** receive a Telegram notification at 80% budget usage, **so that** I can slow down spending
9. **As a** user, **I want to** receive a notification when I exceed my budget, **so that** I'm immediately aware

---

## Proposed Solution

### High-Level Design

Three interconnected features sharing a common notification system:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Budget & Goals System                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Budgets       │  Savings Goals  │  Spending Limits & Alerts   │
│   (by tag)      │  (by account)   │  (thresholds + Telegram)    │
├─────────────────┴─────────────────┴─────────────────────────────┤
│                    dbt Analytics Layer                           │
│   fct_budget_progress  │  fct_goal_progress                      │
├─────────────────────────────────────────────────────────────────┤
│                    Notification Engine                           │
│   Check thresholds → Queue alerts → Send via Telegram           │
└─────────────────────────────────────────────────────────────────┘
```

### Data Model

#### 1. Budget Table

```sql
-- Budget period types
CREATE TYPE budget_period AS ENUM ('weekly', 'monthly', 'quarterly');

CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,

    -- Budget configuration
    amount DECIMAL(18,2) NOT NULL,           -- Budget amount per period
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',
    period budget_period NOT NULL DEFAULT 'monthly',

    -- Rollover settings
    rollover_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    rollover_max DECIMAL(18,2),              -- Cap on rollover (NULL = unlimited)
    rollover_balance DECIMAL(18,2) NOT NULL DEFAULT 0, -- Current rollover from previous periods

    -- Metadata
    is_income BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE for income targets (Income tag)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_budgets_user_tag UNIQUE (user_id, tag_id)
);

CREATE INDEX idx_budgets_user_id ON budgets(user_id);
```

#### 2. Savings Goal Table

```sql
CREATE TABLE savings_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Goal definition
    name VARCHAR(100) NOT NULL,
    target_amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',
    deadline DATE,                           -- Optional target date

    -- Linked account (tracks balance as progress)
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,

    -- Manual progress (when not linked to account)
    current_amount DECIMAL(18,2) NOT NULL DEFAULT 0,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, completed, paused, cancelled
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    colour VARCHAR(7),                       -- Hex colour for UI
    icon VARCHAR(50),                        -- Icon identifier (e.g., "home", "car", "vacation")
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_savings_goals_user_id ON savings_goals(user_id);
CREATE INDEX idx_savings_goals_account_id ON savings_goals(account_id);
```

#### 3. Spending Limit Table

```sql
CREATE TABLE spending_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,

    -- Limit configuration
    limit_amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',

    -- Alert thresholds (percentage of limit)
    warning_threshold INTEGER NOT NULL DEFAULT 80,   -- First alert at 80%
    critical_threshold INTEGER NOT NULL DEFAULT 100, -- Second alert at 100%

    -- Notification settings
    notify_warning BOOLEAN NOT NULL DEFAULT TRUE,
    notify_critical BOOLEAN NOT NULL DEFAULT TRUE,

    -- Tracking (reset monthly)
    last_warning_sent_at TIMESTAMP WITH TIME ZONE,
    last_critical_sent_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_spending_limits_user_tag UNIQUE (user_id, tag_id)
);

CREATE INDEX idx_spending_limits_user_id ON spending_limits(user_id);
```

#### 4. Alert History Table

```sql
CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Alert details
    alert_type VARCHAR(50) NOT NULL,         -- 'budget_warning', 'budget_exceeded', 'goal_achieved'
    entity_type VARCHAR(50) NOT NULL,        -- 'budget', 'spending_limit', 'savings_goal'
    entity_id UUID NOT NULL,

    -- Message content
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,

    -- Delivery status
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, sent, failed
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alert_history_user_id ON alert_history(user_id);
CREATE INDEX idx_alert_history_status ON alert_history(status);
```

### dbt Models

#### 1. fct_budget_progress.sql

Pre-aggregated budget vs spending for the current period (supports weekly, monthly, quarterly).

```sql
-- Calculates spending vs budget per tag per period
WITH budget_config AS (
    SELECT
        b.id AS budget_id,
        b.user_id,
        b.tag_id,
        t.name AS tag_name,
        t.colour AS tag_colour,
        b.amount AS budget_amount,
        b.currency,
        b.period,
        b.rollover_enabled,
        b.rollover_balance,
        b.is_income,
        -- Calculate period boundaries based on budget period type
        CASE b.period
            WHEN 'weekly' THEN DATE_TRUNC('week', CURRENT_DATE)
            WHEN 'monthly' THEN DATE_TRUNC('month', CURRENT_DATE)
            WHEN 'quarterly' THEN DATE_TRUNC('quarter', CURRENT_DATE)
        END AS period_start,
        CASE b.period
            WHEN 'weekly' THEN DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '6 days'
            WHEN 'monthly' THEN (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
            WHEN 'quarterly' THEN (DATE_TRUNC('quarter', CURRENT_DATE) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
        END AS period_end
    FROM {{ ref('src_unified_budgets') }} b
    JOIN {{ ref('dim_tags') }} t ON b.tag_id = t.id
),
period_spending AS (
    SELECT
        bc.budget_id,
        bc.user_id,
        bc.tag_id,
        SUM(ds.total_spending) AS spent_amount,
        SUM(ds.transaction_count) AS transaction_count
    FROM budget_config bc
    JOIN {{ ref('fct_daily_spending_by_tag') }} ds
        ON bc.user_id = ds.user_id
        AND bc.tag_id = ds.tag_id
        AND ds.spending_date BETWEEN bc.period_start AND bc.period_end
    GROUP BY 1, 2, 3
)
SELECT
    bc.budget_id,
    bc.user_id,
    bc.tag_id,
    bc.tag_name,
    bc.tag_colour,
    bc.period,
    bc.period_start,
    bc.period_end,
    bc.budget_amount,
    bc.currency,
    bc.rollover_enabled,
    bc.rollover_balance,
    bc.is_income,
    COALESCE(ps.spent_amount, 0) AS spent_amount,
    COALESCE(ps.transaction_count, 0) AS transaction_count,
    -- Effective budget = base + rollover
    bc.budget_amount + COALESCE(bc.rollover_balance, 0) AS effective_budget,
    -- Remaining = effective - spent
    (bc.budget_amount + COALESCE(bc.rollover_balance, 0)) - COALESCE(ps.spent_amount, 0) AS remaining_amount,
    -- Progress percentage
    CASE
        WHEN bc.budget_amount + COALESCE(bc.rollover_balance, 0) > 0
        THEN ROUND(COALESCE(ps.spent_amount, 0) / (bc.budget_amount + COALESCE(bc.rollover_balance, 0)) * 100, 1)
        ELSE 0
    END AS progress_percent,
    -- Days remaining in period
    DATE_DIFF('day', CURRENT_DATE, bc.period_end) AS days_remaining
FROM budget_config bc
LEFT JOIN period_spending ps ON bc.budget_id = ps.budget_id
```

#### 2. fct_goal_progress.sql

Savings goal progress with projections.

```sql
WITH goals AS (
    SELECT
        g.id AS goal_id,
        g.user_id,
        g.name,
        g.target_amount,
        g.currency,
        g.deadline,
        g.account_id,
        g.current_amount AS manual_amount,
        g.status,
        g.colour,
        g.icon
    FROM {{ ref('src_unified_savings_goals') }} g
    WHERE g.status = 'active'
),
account_balances AS (
    SELECT
        id AS account_id,
        balance_amount,
        balance_currency
    FROM {{ ref('dim_accounts') }}
),
-- Calculate monthly savings rate from last 3 months of balance changes
-- (This would need a balance history table - simplified for now)
goal_progress AS (
    SELECT
        g.goal_id,
        g.user_id,
        g.name,
        g.target_amount,
        g.currency,
        g.deadline,
        g.status,
        g.colour,
        g.icon,
        -- Current amount: account balance if linked, else manual amount
        CASE
            WHEN g.account_id IS NOT NULL THEN COALESCE(ab.balance_amount, 0)
            ELSE g.manual_amount
        END AS current_amount,
        g.account_id
    FROM goals g
    LEFT JOIN account_balances ab ON g.account_id = ab.account_id
)
SELECT
    goal_id,
    user_id,
    name,
    target_amount,
    currency,
    deadline,
    status,
    colour,
    icon,
    current_amount,
    account_id,
    -- Progress percentage
    ROUND(current_amount / NULLIF(target_amount, 0) * 100, 1) AS progress_percent,
    -- Remaining amount
    target_amount - current_amount AS remaining_amount,
    -- Days until deadline
    CASE WHEN deadline IS NOT NULL
        THEN DATE_DIFF('day', CURRENT_DATE, deadline)
        ELSE NULL
    END AS days_remaining,
    -- Required monthly savings (if deadline set)
    CASE
        WHEN deadline IS NOT NULL AND DATE_DIFF('month', CURRENT_DATE, deadline) > 0
        THEN ROUND((target_amount - current_amount) / DATE_DIFF('month', CURRENT_DATE, deadline), 2)
        ELSE NULL
    END AS required_monthly_savings
FROM goal_progress
```

### API Endpoints

#### Budgets

| Method   | Path                    | Description                                  |
|----------|-------------------------|----------------------------------------------|
| GET      | `/api/budgets`          | List all budgets with current month progress |
| POST     | `/api/budgets`          | Create a budget for a tag                    |
| GET      | `/api/budgets/{id}`     | Get budget details with spending history     |
| PUT      | `/api/budgets/{id}`     | Update budget amount/settings                |
| DELETE   | `/api/budgets/{id}`     | Delete budget                                |
| POST     | `/api/budgets/rollover` | Trigger month-end rollover calculation       |

#### Savings Goals

| Method  | Path                         | Description                                |
|---------|------------------------------|--------------------------------------------|
| GET     | `/api/goals`                 | List all savings goals with progress       |
| POST    | `/api/goals`                 | Create a savings goal                      |
| GET     | `/api/goals/{id}`            | Get goal details with projections          |
| PUT     | `/api/goals/{id}`            | Update goal settings                       |
| DELETE  | `/api/goals/{id}`            | Delete goal                                |
| POST    | `/api/goals/{id}/contribute` | Add manual contribution (non-linked goals) |
| POST    | `/api/goals/{id}/complete`   | Mark goal as completed                     |

#### Spending Limits

| Method   | Path                        | Description                         |
|----------|-----------------------------|-------------------------------------|
| GET      | `/api/spending-limits`      | List all limits with current status |
| POST     | `/api/spending-limits`      | Create a spending limit             |
| PUT      | `/api/spending-limits/{id}` | Update limit settings               |
| DELETE   | `/api/spending-limits/{id}` | Delete limit                        |

#### Alerts (read-only for history)

| Method   | Path                  | Description                        |
|----------|-----------------------|------------------------------------|
| GET      | `/api/alerts`         | List alert history                 |
| GET      | `/api/alerts/pending` | List unsent alerts (for debugging) |

### UI/UX

#### 1. Budget Management Page (`/settings/budgets`)

- List of all budgets grouped by tag type (expenses vs income)
- Each row shows: tag chip, budget amount, progress bar, spent/remaining
- Quick-edit inline for budget amount
- "Add Budget" button opens modal with tag selector and amount
- Rollover settings toggle per budget

#### 2. Budget Dashboard (Home Page Widget)

- Summary card: "Budget: £X spent of £Y" with progress ring
- Click to expand showing per-category breakdown
- Colour-coded progress bars (green < 80%, yellow 80-99%, red >= 100%)
- "View Details" links to dedicated budgets page

#### 3. Savings Goals Page (`/goals`)

- Card-based layout, one card per goal
- Each card shows:
  - Goal name + icon
  - Progress bar with current/target amounts
  - Deadline (if set) with days remaining
  - Projected completion date
  - Linked account indicator (if applicable)
- "Add Goal" floating action button
- Goal detail modal with contribution history (for manual goals)

#### 4. Spending Limits Settings (`/settings/limits`)

- List view similar to budgets
- Each row: tag, limit amount, threshold settings, notification toggles
- Visual indicator of current month status

#### 5. Analytics Page Integration

- New "Budget vs Actual" chart option
- Bar chart comparing budget amount vs spent per category
- Trend view showing budget adherence over time

---

## Technical Considerations

### Dependencies

- **Smart Tagging (Phase 4)**: Consistent tags are essential for meaningful budgets
- **Telegram Integration (Phase 7)**: Required for push notifications
- **Balance History (Phase 9)**: Needed for accurate savings goal projections

### Alert Processing

Alerts should be processed via a Dagster job that:

1. Runs after transaction sync completes
2. Queries `fct_budget_progress` for each user
3. Checks thresholds against spending limits
4. Creates alert records for triggered conditions
5. Sends pending alerts via Telegram (when integration available)

```python
# Simplified alert check logic
@asset(deps=[dbt_models])
def check_spending_alerts(context):
    # Query current month progress for all users
    progress = query_budget_progress()

    for row in progress:
        limit = get_spending_limit(row.user_id, row.tag_id)
        if not limit:
            continue

        percent = row.progress_percent

        # Check warning threshold
        if percent >= limit.warning_threshold and not already_sent_warning(limit):
            create_alert(
                type='budget_warning',
                title=f'{row.tag_name} budget at {percent}%',
                message=f"You've spent £{row.spent_amount} of your £{row.effective_budget} budget"
            )

        # Check critical threshold
        if percent >= limit.critical_threshold and not already_sent_critical(limit):
            create_alert(
                type='budget_exceeded',
                title=f'{row.tag_name} budget exceeded!',
                message=f"You've spent £{row.spent_amount}, £{-row.remaining_amount} over budget"
            )
```

### Month-End Rollover

A scheduled Dagster job on the 1st of each month:

1. Calculate unspent amounts for each budget with rollover enabled
2. Apply rollover_max cap if configured
3. Update rollover_balance for the new month
4. Reset last_*_sent_at timestamps on spending limits

### Performance

- Budget progress pre-computed in dbt (no runtime aggregation)
- Index on `budgets(user_id)` for fast lookup
- Alert processing is async (Dagster job, not API-blocking)

### Security

- All endpoints user-scoped (existing pattern)
- Budget/goal amounts validated as positive decimals
- Threshold percentages validated (0-200 range)

---

## Implementation Plan

### Phase 1: Budget Foundation

- [ ] Create `budgets` table and migration (with period enum)
- [ ] Budget SQLAlchemy model and operations
- [ ] Budgets CRUD API endpoints
- [ ] Add `src_unified_budgets` dbt source
- [ ] Create `fct_budget_progress` dbt model (supports weekly/monthly/quarterly)
- [ ] Budget management UI (settings page)
- [ ] Home page budget summary widget
- [ ] Tests for budget operations and API

### Phase 2: Budget Rollover

- [ ] Implement rollover calculation logic
- [ ] Create Dagster job for period-end rollover (handles all period types)
- [ ] UI for rollover settings
- [ ] Tests for rollover logic

### Phase 3: Savings Goals

- [ ] Create `savings_goals` table and migration
- [ ] SavingsGoal model and operations
- [ ] Goals CRUD API endpoints
- [ ] Add `src_unified_savings_goals` dbt source
- [ ] Create `fct_goal_progress` dbt model
- [ ] Goals page UI with progress cards
- [ ] Manual contribution flow (for non-linked goals)
- [ ] Tests for goals operations and API

### Phase 4: Spending Limits & Alerts

*Deferred until Phase 7 (Telegram Integration) is complete. Implement as part of that phase.*

- [ ] Create `spending_limits` table and migration
- [ ] Create `alert_history` table and migration
- [ ] SpendingLimit and Alert models
- [ ] Spending limits API endpoints
- [ ] Dagster job for alert checking (post-sync)
- [ ] Alert processing logic (check thresholds, create alerts)
- [ ] Telegram notification sender
- [ ] Spending limits settings UI
- [ ] Alert history view
- [ ] User notification preferences
- [ ] Tests for alert logic

---

## Testing Strategy

### Unit Tests

- [ ] Budget model: amount validation, rollover calculations
- [ ] SavingsGoal model: progress calculations, deadline projections
- [ ] SpendingLimit model: threshold validation
- [ ] Alert generation logic: threshold checks, duplicate prevention

### Integration Tests

- [ ] Budget CRUD with progress calculation
- [ ] Goal progress tracking (linked vs manual)
- [ ] Alert creation from spending limit breach
- [ ] Month-end rollover job

### Manual Testing

- [ ] Create budgets for multiple categories, verify progress
- [ ] Enable rollover, verify month transition behaviour
- [ ] Create savings goal linked to account, verify balance tracking
- [ ] Create spending limit, exceed threshold, verify alert created

---

## Rollout Plan

1. **Phase 1-2 (Budgets)**: Deploy independently, no external dependencies
2. **Phase 3 (Goals)**: Deploy independently
3. **Phase 4 (Limits/Alerts)**: Deferred to Roadmap Phase 7 (Telegram Integration)

---

## Open Questions

- [x] Should budgets support custom periods (weekly, quarterly)? **Decision: Yes, flexible periods (weekly/monthly/quarterly)**
- [x] Should goals support manual contributions or account-linked only? **Decision: Both methods supported**
- [x] Should alerts be usable before Telegram? **Decision: No, defer to Phase 7 (Telegram Integration)**
- [ ] Should there be a "total budget" cap across all categories? **Proposed: No, individual budgets only**
- [ ] Should goals support multiple linked accounts? **Proposed: Single account for simplicity**
- [ ] What happens to spending limits when a tag is deleted? **Proposed: CASCADE delete**
- [ ] Should users receive a summary notification at period end? **Proposed: Yes, when Telegram available**

---

## References

- Current analytics architecture: `backend/dbt/models/3_mart/`
- Tag model: `backend/src/postgres/common/models.py`
- Existing spending analytics: `fct_daily_spending_by_tag.sql`
- Smart Tagging PRD: `prds/20260125-fullstack-smart-tagging.md`
- Roadmap Phase 6: `ROADMAP.md`
