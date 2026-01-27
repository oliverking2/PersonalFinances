# PRD: Budgeting & Goals

**Status**: Draft
**Author**: Claude
**Created**: 2026-01-27
**Updated**: 2026-01-27

---

## Overview

Add budgeting and savings goal features to help users plan and track their finances. This includes monthly budgets by category (tag), savings goals with progress tracking, and spending alerts when approaching limits.

## Problem Statement

Users currently have no way to:

1. **Set spending limits** - No budgets mean spending is reactive, not proactive
2. **Track savings progress** - No visibility into progress toward financial goals
3. **Get early warnings** - No alerts when approaching spending limits
4. **Plan finances** - No tools to help balance spending vs saving

Budgeting features help users take control of their finances by setting limits, tracking progress, and receiving timely warnings.

## Goals

- Allow users to set monthly budgets per category (tag)
- Show real-time spending vs budget with visual indicators
- Support savings goals with target amounts and deadlines
- Generate alerts when budget thresholds are crossed
- Integrate budget/goal status into the home dashboard

## Non-Goals

- Automatic bill pay or money movement
- Investment tracking or recommendations
- Shared budgets between users
- Complex budgeting methodologies (envelope, zero-based, etc.)
- AI-powered budget recommendations
- Telegram notifications (defer to Phase 7)

---

## User Stories

1. **As a** user, **I want to** set a monthly budget for Dining, **so that** I can control my restaurant spending
2. **As a** user, **I want to** see how much of my Groceries budget I've used, **so that** I know if I need to slow down
3. **As a** user, **I want to** get a warning when I reach 80% of a budget, **so that** I can adjust before overspending
4. **As a** user, **I want to** create a savings goal for a holiday, **so that** I can track my progress
5. **As a** user, **I want to** see when I'll reach my savings goal at the current rate, **so that** I can adjust if needed
6. **As a** user, **I want to** link a savings goal to a specific account, **so that** it tracks the balance automatically
7. **As a** user, **I want to** see budget and goal status on my home page, **so that** I have a quick overview

---

## Proposed Solution

### High-Level Design

```
+-----------------------------------------------------------------------+
|                     Budgeting & Goals System                           |
+-----------------------------------------------------------------------+
|  Frontend                                                              |
|  +----------------+  +----------------+  +-------------------------+   |
|  | Budget Page    |  | Goals Page     |  | Dashboard Widgets       |   |
|  | /budgets       |  | /goals         |  | Budget summary, Goals   |   |
|  +----------------+  +----------------+  +-------------------------+   |
+-----------------------------------------------------------------------+
|  Backend API                                                           |
|  +----------------------------------------------------------------+   |
|  | GET/POST /budgets - Budget CRUD                                |   |
|  | GET/POST /goals - Goal CRUD                                    |   |
|  | GET /alerts - View spending alerts                             |   |
|  +----------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
|  Analytics (dbt)                                                       |
|  +----------------------------------------------------------------+   |
|  | fct_budget_vs_actual - Budget spending aggregation             |   |
|  | fct_goal_progress - Goal progress with projections             |   |
|  | (uses existing fct_daily_spending_by_tag)                      |   |
|  +----------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
```

### Data Model

#### 1. Budgets Table

Stores user-defined budgets per tag (category).

```sql
CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,

    -- Budget configuration
    amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',
    period VARCHAR(20) NOT NULL DEFAULT 'monthly',  -- monthly, weekly, annual

    -- Rollover settings (for future expansion)
    rollover_type VARCHAR(20) NOT NULL DEFAULT 'reset',  -- reset, rollover, cap
    rollover_amount DECIMAL(18,2) NOT NULL DEFAULT 0,

    -- Alert threshold
    warning_threshold DECIMAL(5,2) NOT NULL DEFAULT 80,  -- Percentage

    -- Metadata
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    notes VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_budgets_user_tag UNIQUE (user_id, tag_id)
);

CREATE INDEX idx_budgets_user_id ON budgets(user_id);
```

#### 2. Savings Goals Table

Stores savings goals with target amounts and deadlines.

```sql
CREATE TABLE savings_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Goal definition
    name VARCHAR(100) NOT NULL,
    target_amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',
    target_date TIMESTAMP WITH TIME ZONE,  -- Optional deadline

    -- Tracking method
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,  -- If set, tracks balance
    current_amount DECIMAL(18,2) NOT NULL DEFAULT 0,  -- For manual tracking

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, paused, completed, cancelled
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Display
    colour VARCHAR(7),  -- Hex colour
    icon VARCHAR(50),
    notes TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_savings_goals_user_id ON savings_goals(user_id);
CREATE INDEX idx_savings_goals_user_status ON savings_goals(user_id, status);
```

#### 3. Spending Alerts Table

Records generated alerts for budget threshold breaches.

```sql
CREATE TABLE spending_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Alert context
    alert_type VARCHAR(30) NOT NULL,  -- budget_warning, budget_exceeded
    budget_id UUID REFERENCES budgets(id) ON DELETE CASCADE,

    -- Content
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,

    -- Threshold info
    threshold_percent DECIMAL(5,2),
    spent_amount DECIMAL(18,2),
    budget_amount DECIMAL(18,2),

    -- Deduplication
    period_key VARCHAR(50) NOT NULL,  -- e.g., "2026-01"

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, acknowledged
    acknowledged_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_alerts_dedup UNIQUE (user_id, budget_id, alert_type, threshold_percent, period_key)
);

CREATE INDEX idx_spending_alerts_user_id ON spending_alerts(user_id);
CREATE INDEX idx_spending_alerts_status ON spending_alerts(status);
```

### dbt Models

#### 1. fct_budget_vs_actual.sql

Joins budgets with `fct_daily_spending_by_tag` to calculate current period spending.

**Output columns:**

- `budget_id`, `user_id`, `tag_id`, `tag_name`, `tag_colour`
- `period`, `period_start`, `period_end`
- `budget_amount`, `effective_budget` (includes rollover)
- `spent_amount`, `remaining_amount`, `percent_used`
- `warning_threshold`
- `status` ("on_track", "warning", "exceeded")

#### 2. fct_goal_progress.sql

Calculates goal progress and projections.

**Output columns:**

- `goal_id`, `user_id`, `goal_name`, `target_amount`, `current_amount`
- `target_date`, `days_remaining`
- `percent_complete`, `amount_remaining`
- `daily_savings_needed` (if deadline set)
- `projected_completion_date` (linear extrapolation)
- `on_track` (boolean if deadline set)

### API Endpoints

#### Budgets

| Method   | Path                   | Description                          |
|----------|------------------------|--------------------------------------|
| POST     | `/api/budgets`         | Create a budget                      |
| GET      | `/api/budgets`         | List budgets with current spending   |
| GET      | `/api/budgets/{id}`    | Get budget with spending details     |
| PUT      | `/api/budgets/{id}`    | Update budget                        |
| DELETE   | `/api/budgets/{id}`    | Delete budget                        |
| GET      | `/api/budgets/summary` | Aggregate summary across all budgets |

#### Goals

| Method  | Path                         | Description                     |
|---------|------------------------------|---------------------------------|
| POST    | `/api/goals`                 | Create a goal                   |
| GET     | `/api/goals`                 | List goals with progress        |
| GET     | `/api/goals/{id}`            | Get goal with progress          |
| PUT     | `/api/goals/{id}`            | Update goal                     |
| DELETE  | `/api/goals/{id}`            | Delete goal                     |
| POST    | `/api/goals/{id}/contribute` | Add contribution (manual goals) |
| PUT     | `/api/goals/{id}/complete`   | Mark as completed               |

#### Alerts

| Method  | Path                           | Description                    |
|---------|--------------------------------|--------------------------------|
| GET     | `/api/alerts`                  | List alerts (filter by status) |
| GET     | `/api/alerts/unread`           | Get unread alert count         |
| PUT     | `/api/alerts/{id}/acknowledge` | Acknowledge alert              |

### UI/UX

#### 1. Budgets Page (`/budgets`)

```
+---------------------------------------------------------------+
|  Budgets                                          [+ Add Budget]|
+---------------------------------------------------------------+
|                                                                 |
|  Total Budgeted: GBP 1,500    Spent: GBP 876    On Track: 4/6    |
|                                                                 |
+---------------------------------------------------------------+
|                                                                 |
|  Groceries                                         GBP 400/mo   |
|  [=============>          ]  62%     GBP 152 left              |
|  On Track                                                       |
|                                                                 |
|  --------------------------------------------------------      |
|                                                                 |
|  Dining                                            GBP 200/mo   |
|  [======================> ]  87%     GBP 26 left               |
|  Warning - Approaching limit                                    |
|                                                                 |
|  --------------------------------------------------------      |
|                                                                 |
|  Entertainment                                     GBP 100/mo   |
|  [============================]  112%  GBP 12 over             |
|  Exceeded                                                       |
|                                                                 |
+---------------------------------------------------------------+
```

#### 2. Goals Page (`/goals`)

```
+---------------------------------------------------------------+
|  Savings Goals                                      [+ Add Goal]|
+---------------------------------------------------------------+
|                                                                 |
|  +---------------------------+  +---------------------------+  |
|  |  Holiday Fund             |  |  Emergency Fund           |  |
|  |                           |  |                           |  |
|  |      [====]  42%          |  |      [========]  75%      |  |
|  |                           |  |                           |  |
|  |  GBP 2,100 / GBP 5,000    |  |  GBP 7,500 / GBP 10,000   |  |
|  |  Target: Aug 2026         |  |  No deadline              |  |
|  |  On track                 |  |  Linked: Savings Account  |  |
|  +---------------------------+  +---------------------------+  |
|                                                                 |
+---------------------------------------------------------------+
```

#### 3. Dashboard Widgets

**Budget Summary Widget:**

- Shows budgets with warnings or exceeded status
- Quick link to full budgets page
- Collapsed on mobile

**Goals Progress Widget:**

- Shows top 2-3 active goals with progress
- Quick link to full goals page

---

## Technical Considerations

### Analytics Integration

Budget vs actual calculations use the existing `fct_daily_spending_by_tag` dbt model, which already:

- Aggregates spending by user, date, and tag
- Excludes internal transfers
- Handles split transactions correctly

This minimises new complexity - we only need to join budgets with this existing model.

### Alert Generation

Alerts are generated by a Dagster job that runs after transaction sync:

1. Query `fct_budget_vs_actual` for current period
2. Find budgets at/above warning threshold
3. Create `spending_alert` records (deduplicated by period_key)
4. Future: Send via Telegram (Phase 7)

### Performance

- Budget queries indexed on `user_id`, `tag_id`
- Alert deduplication via unique constraint (no duplicate checks needed)
- dbt models pre-aggregate data; API does simple lookups

### Security

- All endpoints user-scoped
- Ownership verification before any operation
- No cross-user data access

---

## Implementation Plan

### Phase 6a: Core Budget Tracking

**Backend:**

- [ ] Add `BudgetPeriod`, `GoalStatus`, `AlertType` enums
- [ ] Create `Budget` SQLAlchemy model
- [ ] Create Alembic migration for `budgets` table
- [ ] Create budget operations module (CRUD)
- [ ] Create budget API endpoints
- [ ] Add `src_unified_budgets.sql` dbt source
- [ ] Create `fct_budget_vs_actual.sql` dbt model
- [ ] Register dataset in schema.yml
- [ ] Write tests (80% coverage)

**Frontend:**

- [ ] Add budget TypeScript types
- [ ] Create `useBudgetsApi` composable
- [ ] Create `BudgetCard` component
- [ ] Create `BudgetProgressBar` component
- [ ] Create `/budgets` page with CRUD
- [ ] Create budget creation modal

### Phase 6b: Savings Goals

**Backend:**

- [ ] Create `SavingsGoal` SQLAlchemy model
- [ ] Create Alembic migration for `savings_goals` table
- [ ] Create goals operations module
- [ ] Create goals API endpoints
- [ ] Add `src_unified_savings_goals.sql` dbt source
- [ ] Create `fct_goal_progress.sql` dbt model
- [ ] Register dataset in schema.yml
- [ ] Write tests

**Frontend:**

- [ ] Add goals TypeScript types
- [ ] Create `useGoalsApi` composable
- [ ] Create `GoalCard` component with progress ring
- [ ] Create `/goals` page
- [ ] Create goal creation modal

### Phase 6c: Dashboard Integration

**Frontend:**

- [ ] Create `BudgetSummaryWidget` component
- [ ] Create `GoalsProgressWidget` component
- [ ] Add widgets to home page (`/`)
- [ ] Responsive layout for mobile

### Phase 6d: Alerts System

**Backend:**

- [ ] Create `SpendingAlert` SQLAlchemy model
- [ ] Create Alembic migration for `spending_alerts` table
- [ ] Create alerts operations module
- [ ] Create alerts API endpoints
- [ ] Create Dagster job for alert generation
- [ ] Wire into transaction sync pipeline
- [ ] Write tests

**Frontend:**

- [ ] Create `AlertBadge` header component
- [ ] Create `AlertDropdown` for quick view
- [ ] Add acknowledge functionality

### Phase 6e: Telegram Integration (Defer to Phase 7)

- Telegram bot setup
- Notification settings UI
- Alert delivery via Telegram

---

## Testing Strategy

### Unit Tests

- Budget CRUD operations
- Goal CRUD and contribution operations
- Alert generation and deduplication
- Period calculations (monthly start/end)

### Integration Tests

- End-to-end: create budget -> add transactions -> verify spending calculation
- Alert generation: budget exceeds threshold -> alert created
- Goal progress: manual contribution -> progress updates

### Manual Testing

- [ ] Create budgets for different categories
- [ ] Verify spending updates after transaction sync
- [ ] Test warning/exceeded status transitions
- [ ] Create goals with and without deadlines
- [ ] Test account-linked goal balance tracking
- [ ] Verify dashboard widgets update correctly

---

## Open Questions

- [x] Should budgets support weekly/annual periods? **Decision: Monthly only for v1, add others later**
- [x] Should rollover be supported in v1? **Decision: No, reset only for v1**
- [x] How should account-linked goals update? **Decision: Calculated from balance in dbt model, updated on analytics refresh**
- [x] Should there be a separate "Income" budget category? **Decision: No, use existing "Income" tag for income transactions; budgets are for spending limits**

---

## References

- Existing tag system: `backend/src/postgres/common/models.py`
- Spending aggregation: `backend/dbt/models/3_mart/fct_daily_spending_by_tag.sql`
- Subscriptions pattern: `backend/src/api/subscriptions/`
- Analytics API: `backend/src/api/analytics/`
