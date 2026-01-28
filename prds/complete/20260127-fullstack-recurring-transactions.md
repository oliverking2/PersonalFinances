# PRD: Recurring Transactions & Subscription Detection

**Status**: Approved
**Author**: Claude
**Created**: 2026-01-27
**Updated**: 2026-01-27

---

## Overview

Automatically detect recurring transactions (subscriptions, bills, regular payments) from transaction history and provide users with visibility into their recurring commitments. This includes visual indicators on transactions, an upcoming bills widget on the home page, and a dedicated subscription management view.

## Problem Statement

Users currently have no visibility into their recurring payments:

1. **Hidden subscriptions** - Subscriptions accumulate over time and are easy to forget about
2. **Bill surprises** - Users don't know when upcoming bills will hit their account
3. **No spending insight** - No way to see total committed recurring spend per month
4. **Manual tracking** - Users must mentally track or use external tools to manage subscriptions

Identifying and visualising recurring transactions helps users understand their financial commitments and make informed decisions about cancelling unused subscriptions.

## Goals

- Automatically detect recurring transactions with high accuracy (low false positives)
- Show visual indicators on transaction list for recurring payments
- Display upcoming bills widget on home page to help users plan
- Provide subscription management view listing all detected recurring payments
- Allow users to confirm, reject, or manually add recurring transactions
- Calculate total monthly recurring spend

## Non-Goals

- Automatic subscription cancellation (out of scope)
- Price comparison or alternative suggestions
- Contract renewal reminders (requires external data)
- Shared subscription splitting with other users
- Integration with subscription management services
- Push notifications for upcoming bills (defer to Telegram integration phase)

---

## User Stories

1. **As a** user viewing my transactions, **I want to** see which transactions are recurring, **so that** I can identify subscriptions at a glance
2. **As a** user on the home page, **I want to** see upcoming bills for the next 7-14 days, **so that** I can ensure I have sufficient funds
3. **As a** user, **I want to** view all my detected subscriptions in one place, **so that** I can review and manage my recurring commitments
4. **As a** user, **I want to** see my total monthly recurring spend, **so that** I understand my committed expenses
5. **As a** user, **I want to** mark a transaction as "not recurring" when the system incorrectly detects it, **so that** I get accurate predictions
6. **As a** user, **I want to** manually mark a transaction as recurring, **so that** I can track payments the system missed
7. **As a** user, **I want to** see the next expected date for each subscription, **so that** I can plan accordingly

---

## Proposed Solution

### High-Level Design

The solution has three layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Recurring Transactions System                     │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend                                                            │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │ Transaction  │  │ Upcoming Bills   │  │ Subscriptions Page     │ │
│  │ Badges       │  │ Widget (Home)    │  │ /subscriptions         │ │
│  └──────────────┘  └──────────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  Backend API                                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ GET /subscriptions - List all detected recurring patterns    │   │
│  │ GET /subscriptions/upcoming - Upcoming bills in date range   │   │
│  │ PUT /subscriptions/{id} - Update (confirm/dismiss/pause)     │   │
│  │ POST /subscriptions - Manually create subscription           │   │
│  └──────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  Detection Engine (Dagster + dbt)                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Pattern detection algorithm → recurring_patterns table       │   │
│  │ dbt mart: fct_recurring_patterns with next_expected_date     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Detection Algorithm

The algorithm identifies recurring patterns based on:

1. **Merchant/counterparty grouping** - Group transactions by normalised merchant name
2. **Amount consistency** - Recurring payments typically have consistent amounts (within 5% tolerance for variable subscriptions)
3. **Frequency detection** - Identify intervals: weekly, fortnightly, monthly, quarterly, annual
4. **Minimum occurrences** - Require at least 2-3 occurrences to establish a pattern
5. **Recency check** - Pattern must have recent activity (within expected interval + grace period)

**Frequency detection logic:**

```python
# Calculate intervals between transactions from same merchant
intervals = [(t2.date - t1.date).days for t1, t2 in zip(transactions, transactions[1:])]

# Map intervals to frequency buckets with tolerance
FREQUENCY_RANGES = {
    'weekly': (5, 9),      # 7 days ± 2
    'fortnightly': (12, 18), # 14 days ± 4
    'monthly': (25, 35),   # 30 days ± 5
    'quarterly': (80, 100), # 90 days ± 10
    'annual': (350, 380),  # 365 days ± 15
}

def detect_frequency(intervals: list[int]) -> str | None:
    median_interval = statistics.median(intervals)
    for freq, (min_days, max_days) in FREQUENCY_RANGES.items():
        if min_days <= median_interval <= max_days:
            return freq
    return None
```

**Confidence scoring:**

- Base confidence from number of occurrences (2 = low, 3 = medium, 4+ = high)
- Bonus for amount consistency (< 2% variation)
- Bonus for interval consistency (low standard deviation)
- Penalty for missed expected payments

### Data Model

#### 1. Recurring Patterns Table

Stores detected and user-confirmed recurring payment patterns.

```sql
CREATE TYPE recurring_frequency AS ENUM (
    'weekly', 'fortnightly', 'monthly', 'quarterly', 'annual', 'irregular'
);

CREATE TYPE recurring_status AS ENUM (
    'detected',    -- Auto-detected, not yet confirmed by user
    'confirmed',   -- User confirmed this is recurring
    'dismissed',   -- User marked as not recurring (false positive)
    'paused',      -- User temporarily paused (e.g., cancelled subscription)
    'manual'       -- Manually added by user
);

CREATE TABLE recurring_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Pattern identification
    merchant_pattern VARCHAR(256) NOT NULL,  -- Normalised merchant name/pattern
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,  -- Optional: specific account

    -- Pattern characteristics
    expected_amount DECIMAL(18,2) NOT NULL,
    amount_variance DECIMAL(5,2) DEFAULT 0,  -- Allowed % variance (e.g., 5.00 for 5%)
    currency VARCHAR(3) NOT NULL DEFAULT 'GBP',
    frequency recurring_frequency NOT NULL,

    -- Timing
    anchor_date DATE NOT NULL,              -- Reference date for calculating next occurrence
    next_expected_date DATE,                -- Calculated next expected date
    last_occurrence_date DATE,              -- Most recent matching transaction

    -- Detection metadata
    confidence_score DECIMAL(3,2) NOT NULL DEFAULT 0.5,  -- 0.0 to 1.0
    occurrence_count INTEGER NOT NULL DEFAULT 0,

    -- Status
    status recurring_status NOT NULL DEFAULT 'detected',

    -- User customisation
    display_name VARCHAR(100),              -- User-friendly name override
    category VARCHAR(100),                  -- User-assigned category
    notes TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique per user+merchant combination
    CONSTRAINT uq_recurring_patterns_user_merchant
        UNIQUE (user_id, merchant_pattern, account_id)
);

CREATE INDEX idx_recurring_patterns_user_id ON recurring_patterns(user_id);
CREATE INDEX idx_recurring_patterns_status ON recurring_patterns(status);
CREATE INDEX idx_recurring_patterns_next_date ON recurring_patterns(next_expected_date);
```

#### 2. Pattern-Transaction Link Table

Links detected patterns to their matching transactions for audit trail.

```sql
CREATE TABLE recurring_pattern_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_id UUID NOT NULL REFERENCES recurring_patterns(id) ON DELETE CASCADE,
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,

    -- Match quality
    amount_match BOOLEAN NOT NULL DEFAULT TRUE,  -- Did amount fall within variance?
    date_match BOOLEAN NOT NULL DEFAULT TRUE,    -- Was date within expected window?

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_pattern_transaction UNIQUE (pattern_id, transaction_id)
);

CREATE INDEX idx_pattern_transactions_pattern ON recurring_pattern_transactions(pattern_id);
CREATE INDEX idx_pattern_transactions_transaction ON recurring_pattern_transactions(transaction_id);
```

#### 3. Update Transactions Table

Add a column to link transactions to their recurring pattern (optional, for quick lookups).

```sql
ALTER TABLE transactions
ADD COLUMN recurring_pattern_id UUID REFERENCES recurring_patterns(id) ON DELETE SET NULL;

CREATE INDEX idx_transactions_recurring_pattern ON transactions(recurring_pattern_id);
```

### dbt Models

#### 1. int_recurring_candidates.sql

Intermediate model that groups transactions by merchant and calculates pattern candidates.

```sql
-- Identify candidate recurring patterns from transaction data
WITH merchant_groups AS (
    SELECT
        t.account_id,
        -- Normalise merchant name (lowercase, trim, remove common suffixes)
        LOWER(TRIM(COALESCE(t.counterparty_name, t.description))) AS merchant_key,
        t.id AS transaction_id,
        t.booking_date,
        t.amount,
        t.currency,
        ROW_NUMBER() OVER (
            PARTITION BY t.account_id, LOWER(TRIM(COALESCE(t.counterparty_name, t.description)))
            ORDER BY t.booking_date
        ) AS occurrence_num
    FROM {{ ref('stg_transactions') }} t
    WHERE t.amount < 0  -- Only expenses
      AND t.booking_date >= CURRENT_DATE - INTERVAL '18 months'
),
with_intervals AS (
    SELECT
        *,
        LAG(booking_date) OVER (
            PARTITION BY account_id, merchant_key
            ORDER BY booking_date
        ) AS prev_date,
        DATE_DIFF('day',
            LAG(booking_date) OVER (PARTITION BY account_id, merchant_key ORDER BY booking_date),
            booking_date
        ) AS interval_days
    FROM merchant_groups
),
merchant_stats AS (
    SELECT
        account_id,
        merchant_key,
        COUNT(*) AS occurrence_count,
        MIN(amount) AS min_amount,
        MAX(amount) AS max_amount,
        AVG(amount) AS avg_amount,
        STDDEV(amount) AS amount_stddev,
        AVG(interval_days) AS avg_interval,
        STDDEV(interval_days) AS interval_stddev,
        MAX(booking_date) AS last_occurrence,
        MIN(booking_date) AS first_occurrence
    FROM with_intervals
    WHERE interval_days IS NOT NULL
    GROUP BY account_id, merchant_key
    HAVING COUNT(*) >= 2  -- Minimum 2 occurrences
)
SELECT
    ms.*,
    -- Detect frequency from average interval
    CASE
        WHEN avg_interval BETWEEN 5 AND 9 THEN 'weekly'
        WHEN avg_interval BETWEEN 12 AND 18 THEN 'fortnightly'
        WHEN avg_interval BETWEEN 25 AND 35 THEN 'monthly'
        WHEN avg_interval BETWEEN 80 AND 100 THEN 'quarterly'
        WHEN avg_interval BETWEEN 350 AND 380 THEN 'annual'
        ELSE 'irregular'
    END AS detected_frequency,
    -- Calculate confidence score
    LEAST(1.0,
        (occurrence_count / 5.0) *  -- More occurrences = higher confidence
        (1.0 - LEAST(1.0, COALESCE(interval_stddev, 0) / avg_interval)) *  -- Consistent intervals
        (1.0 - LEAST(1.0, COALESCE(amount_stddev, 0) / ABS(avg_amount)))   -- Consistent amounts
    ) AS confidence_score
FROM merchant_stats
WHERE avg_interval BETWEEN 5 AND 380  -- Filter out very irregular patterns
```

#### 2. fct_recurring_patterns.sql

Final mart that combines detected patterns with user overrides.

```sql
-- Merge detected patterns with user-managed patterns
WITH detected AS (
    SELECT * FROM {{ ref('int_recurring_candidates') }}
    WHERE confidence_score >= 0.5  -- Threshold for auto-detection
      AND detected_frequency != 'irregular'
),
user_patterns AS (
    SELECT
        rp.*,
        a.user_id
    FROM {{ source('app', 'recurring_patterns') }} rp
    JOIN {{ ref('dim_accounts') }} a ON rp.account_id = a.id
),
-- Calculate next expected date based on frequency
with_next_date AS (
    SELECT
        COALESCE(up.id, gen_random_uuid()) AS pattern_id,
        COALESCE(up.user_id, d.user_id) AS user_id,
        COALESCE(up.account_id, d.account_id) AS account_id,
        COALESCE(up.merchant_pattern, d.merchant_key) AS merchant_pattern,
        COALESCE(up.expected_amount, d.avg_amount) AS expected_amount,
        COALESCE(up.currency, 'GBP') AS currency,
        COALESCE(up.frequency, d.detected_frequency) AS frequency,
        COALESCE(up.status, 'detected') AS status,
        COALESCE(up.display_name, d.merchant_key) AS display_name,
        COALESCE(up.confidence_score, d.confidence_score) AS confidence_score,
        COALESCE(up.occurrence_count, d.occurrence_count) AS occurrence_count,
        d.last_occurrence AS last_occurrence_date,
        -- Calculate next expected date
        CASE COALESCE(up.frequency, d.detected_frequency)
            WHEN 'weekly' THEN d.last_occurrence + INTERVAL '7 days'
            WHEN 'fortnightly' THEN d.last_occurrence + INTERVAL '14 days'
            WHEN 'monthly' THEN d.last_occurrence + INTERVAL '1 month'
            WHEN 'quarterly' THEN d.last_occurrence + INTERVAL '3 months'
            WHEN 'annual' THEN d.last_occurrence + INTERVAL '1 year'
        END AS next_expected_date,
        up.notes,
        up.category
    FROM detected d
    FULL OUTER JOIN user_patterns up
        ON d.account_id = up.account_id
        AND d.merchant_key = up.merchant_pattern
    WHERE COALESCE(up.status, 'detected') NOT IN ('dismissed')
)
SELECT
    *,
    -- Calculate monthly equivalent amount for comparison
    CASE frequency
        WHEN 'weekly' THEN expected_amount * 4.33
        WHEN 'fortnightly' THEN expected_amount * 2.17
        WHEN 'monthly' THEN expected_amount
        WHEN 'quarterly' THEN expected_amount / 3
        WHEN 'annual' THEN expected_amount / 12
        ELSE expected_amount
    END AS monthly_equivalent,
    -- Is the pattern overdue? (past expected date + grace period)
    CASE
        WHEN next_expected_date < CURRENT_DATE - INTERVAL '7 days' THEN TRUE
        ELSE FALSE
    END AS is_overdue
FROM with_next_date
```

### API Endpoints

#### Subscriptions

| Method | Path                          | Description                                       |
|--------|-------------------------------|---------------------------------------------------|
| GET    | `/api/subscriptions`          | List all recurring patterns (with filters)        |
| GET    | `/api/subscriptions/{id}`     | Get subscription details with transaction history |
| PUT    | `/api/subscriptions/{id}`     | Update subscription (confirm/dismiss/pause/edit)  |
| POST   | `/api/subscriptions`          | Manually create a subscription                    |
| DELETE | `/api/subscriptions/{id}`     | Delete subscription (sets status to dismissed)    |
| GET    | `/api/subscriptions/upcoming` | Get upcoming bills in date range                  |
| GET    | `/api/subscriptions/summary`  | Get summary statistics (total monthly, count)     |

**Query parameters for GET /subscriptions:**

- `status` - Filter by status (detected, confirmed, paused)
- `frequency` - Filter by frequency (monthly, annual, etc.)
- `min_confidence` - Minimum confidence score (0.0-1.0)
- `include_dismissed` - Include dismissed patterns (default: false)

**Request body for PUT /subscriptions/{id}:**

```json
{
  "status": "confirmed",
  "display_name": "Netflix",
  "category": "Entertainment",
  "expected_amount": -15.99,
  "frequency": "monthly",
  "notes": "Family plan"
}
```

**Response for GET /subscriptions/upcoming:**

```json
{
  "upcoming": [
    {
      "id": "uuid",
      "display_name": "Netflix",
      "merchant_pattern": "netflix",
      "expected_amount": -15.99,
      "currency": "GBP",
      "next_expected_date": "2026-01-30",
      "frequency": "monthly",
      "confidence_score": 0.95,
      "status": "confirmed"
    }
  ],
  "total_expected": -45.97,
  "date_range": {
    "start": "2026-01-27",
    "end": "2026-02-03"
  }
}
```

### UI/UX

#### 1. Transaction List Badges

Add a recurring indicator badge to `TransactionRow`:

- **Icon**: Small repeat/cycle icon (↻) next to merchant name
- **Colour**: Muted colour (grey or subtle primary) to avoid visual noise
- **Tooltip**: "Recurring payment • Monthly" (shows frequency)
- **Interaction**: Click opens quick actions (confirm/dismiss as recurring)

Visual placement options:

```
Option A: Badge after merchant name
┌─────────────────────────────────────────────────────────┐
│ ○  Netflix ↻              [Entertainment]    -£15.99   │
│    Monthly • Entertainment                              │
└─────────────────────────────────────────────────────────┘

Option B: Badge in metadata line
┌─────────────────────────────────────────────────────────┐
│ ○  Netflix                [Entertainment]    -£15.99   │
│    Monthly subscription • Main Account                  │
└─────────────────────────────────────────────────────────┘
```

**Recommendation**: Option A - badge next to merchant name is more visible.

#### 2. Upcoming Bills Widget (Home Page)

New widget below the metrics grid, before recent transactions:

```
┌─────────────────────────────────────────────────────────┐
│  Upcoming Bills                               Next 7 days│
├─────────────────────────────────────────────────────────┤
│  Jan 28   Netflix             Monthly         -£15.99   │
│  Jan 30   Spotify             Monthly          -£9.99   │
│  Feb 1    Rent                Monthly       -£1,200.00  │
├─────────────────────────────────────────────────────────┤
│  Total expected: -£1,225.98           View all →        │
└─────────────────────────────────────────────────────────┘
```

- Shows next 7 days by default (configurable)
- Sorted by expected date
- Shows total expected outgoing
- "View all" links to subscriptions page
- Collapsed/expandable on mobile

#### 3. Subscriptions Page (`/subscriptions`)

Dedicated page for managing all recurring payments:

**Header section:**

- Total monthly recurring spend (large number)
- Count of active subscriptions
- Filter/sort controls

**List view:**

```
┌─────────────────────────────────────────────────────────┐
│  🔄 Subscriptions                                        │
│                                                          │
│  Monthly total: £156.47              12 subscriptions   │
│                                                          │
│  [All] [Confirmed] [Detected] [Paused]   Sort: Amount ▼ │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Netflix                            Monthly    -£15.99  │
│  ✓ Confirmed • Last: Jan 15 • Next: Feb 15              │
│  Entertainment                                   [···]  │
│                                                          │
│  ─────────────────────────────────────────────────────  │
│                                                          │
│  Spotify                            Monthly     -£9.99  │
│  ? Detected • Last: Jan 10 • Next: Feb 10               │
│  85% confidence                      [Confirm] [Dismiss]│
│                                                          │
│  ─────────────────────────────────────────────────────  │
│                                                          │
│  Amazon Prime                       Annual   -£95.00    │
│  ✓ Confirmed • Last: Dec 1 • Next: Dec 1 2026           │
│  Entertainment • Includes delivery           [···]      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Subscription card actions:**

- **Confirm**: Mark detected pattern as confirmed (increases confidence)
- **Dismiss**: Mark as not recurring (false positive)
- **Pause**: Temporarily hide (for cancelled subscriptions)
- **Edit**: Change display name, category, expected amount, notes
- **View history**: See all matching transactions

**Add subscription manually:**

- Search transactions to find candidates
- Or create from scratch with merchant name, amount, frequency

#### 4. Subscription Detail Modal

Clicking a subscription opens a detail view:

- **Header**: Display name, frequency, amount, status
- **Next expected**: Date with days until
- **Monthly equivalent**: For non-monthly frequencies
- **Edit fields**: Name, category, amount, notes
- **Transaction history**: List of all matched transactions
- **Actions**: Confirm/Dismiss/Pause buttons

---

## Technical Considerations

### Dependencies

- **Transaction data**: Requires sufficient transaction history (3+ months ideal)
- **Analytics pipeline**: Detection runs as part of dbt/Dagster pipeline
- **Tags (Phase 4)**: Can leverage tag data for category suggestions

### Detection Pipeline

The detection algorithm runs as a Dagster asset after transaction sync:

1. **Trigger**: After new transactions are loaded
2. **Process**:
   - dbt runs `int_recurring_candidates` model
   - Python asset compares with existing `recurring_patterns` table
   - New patterns inserted with status='detected'
   - Existing patterns updated (occurrence_count, last_occurrence, next_expected)
3. **Output**: Updated `recurring_patterns` table

```python
@asset(deps=[dbt_run])
def update_recurring_patterns(context, duckdb: DuckDBResource):
    """Sync detected patterns to PostgreSQL recurring_patterns table."""

    # Query detected patterns from dbt mart
    detected = duckdb.query("""
        SELECT * FROM fct_recurring_patterns
        WHERE status = 'detected'
    """)

    # Upsert to PostgreSQL
    for pattern in detected:
        upsert_recurring_pattern(
            user_id=pattern.user_id,
            merchant_pattern=pattern.merchant_pattern,
            expected_amount=pattern.expected_amount,
            frequency=pattern.frequency,
            confidence_score=pattern.confidence_score,
            # ... other fields
        )
```

### Performance

- Pattern detection is O(n log n) per merchant group (sorting by date)
- dbt model is incremental-capable (only process new transactions)
- API queries use indexed columns (user_id, status, next_expected_date)
- Frontend caches subscription list (refresh on transaction sync)

### Migration

1. Create new tables (`recurring_patterns`, `recurring_pattern_transactions`)
2. Run initial detection on historical data (backfill)
3. Add `recurring_pattern_id` to transactions table
4. Link existing transactions to detected patterns

### Security

- All endpoints user-scoped (existing pattern)
- Pattern merchant names may contain PII - treat as sensitive
- No cross-user pattern sharing

---

## Implementation Plan

### Phase 1: Backend Foundation

- [ ] Create `recurring_patterns` table and migration
- [ ] Create `recurring_pattern_transactions` table and migration
- [ ] Add `recurring_pattern_id` column to transactions table
- [ ] Create RecurringPattern SQLAlchemy model
- [ ] Create RecurringPatternTransaction model
- [ ] Implement pattern CRUD operations
- [ ] Unit tests for models and operations

### Phase 2: Detection Algorithm

- [ ] Create `int_recurring_candidates` dbt model
- [ ] Create `fct_recurring_patterns` dbt mart
- [ ] Implement Dagster asset for pattern sync
- [ ] Add confidence scoring logic
- [ ] Add next_expected_date calculation
- [ ] Integration tests for detection accuracy
- [ ] Backfill historical data

### Phase 3: API Endpoints

- [ ] GET `/api/subscriptions` - List with filters
- [ ] GET `/api/subscriptions/{id}` - Detail with history
- [ ] PUT `/api/subscriptions/{id}` - Update status/details
- [ ] POST `/api/subscriptions` - Manual creation
- [ ] DELETE `/api/subscriptions/{id}` - Dismiss
- [ ] GET `/api/subscriptions/upcoming` - Upcoming bills
- [ ] GET `/api/subscriptions/summary` - Statistics
- [ ] API integration tests

### Phase 4: Frontend - Transaction Badges

- [ ] Add `recurring_pattern_id` to Transaction type
- [ ] Create `RecurringBadge` component
- [ ] Update `TransactionRow` to show badge
- [ ] Add tooltip with frequency info
- [ ] Add quick confirm/dismiss actions
- [ ] Update transaction detail modal

### Phase 5: Frontend - Upcoming Bills Widget

- [ ] Create `useSubscriptionsApi` composable
- [ ] Create `UpcomingBillsWidget` component
- [ ] Add widget to home page
- [ ] Style for collapsed/expanded states
- [ ] Link to subscriptions page

### Phase 6: Frontend - Subscriptions Page

- [ ] Create `/subscriptions` page
- [ ] Create `SubscriptionCard` component
- [ ] Implement filter controls (status, frequency)
- [ ] Implement sort controls (amount, date, name)
- [ ] Create subscription detail modal
- [ ] Implement confirm/dismiss/pause actions
- [ ] Create "Add subscription" flow
- [ ] Display monthly total calculation

---

## Testing Strategy

### Unit Tests

- [ ] Pattern detection: frequency classification from intervals
- [ ] Confidence scoring: various occurrence/variance scenarios
- [ ] Next date calculation: all frequency types
- [ ] Amount matching: variance tolerance logic

### Integration Tests

- [ ] End-to-end detection: seed transactions → detect patterns → verify results
- [ ] API CRUD operations with pattern-transaction linking
- [ ] User override persistence (confirm/dismiss survives re-detection)

### Manual Testing

- [ ] Verify detection accuracy on real transaction data
- [ ] Test false positive rate on one-time payments
- [ ] Test badge visibility on various transaction types
- [ ] Test upcoming bills widget with various date ranges
- [ ] Test subscription management workflows

---

## Rollout Plan

1. **Phase 1-2 (Backend + Detection)**: Deploy and run initial detection
2. **Phase 3 (API)**: Deploy API endpoints
3. **Phase 4 (Badges)**: Deploy transaction badges (low risk, additive)
4. **Phase 5 (Widget)**: Deploy home page widget
5. **Phase 6 (Page)**: Deploy full subscriptions page

---

## Open Questions

- [x] Should detected patterns require explicit confirmation before appearing in the upcoming bills widget? **Decision: Yes, show all with confidence >= 0.7, mark unconfirmed with different styling**
- [x] How to handle subscriptions with variable amounts (e.g., utility bills)? **Decision: Support amount_variance field, show "approximately" in UI**
- [x] Should users be able to snooze a subscription? **Decision: Yes, via 'paused' status**
- [x] How many days ahead should the widget show by default? **Decision: 7 days**
- [x] Should there be a "Review detected subscriptions" onboarding flow? **Decision: Skip for now, can add later if needed**

---

## References

- Current transaction model: `backend/src/postgres/common/models.py`
- Transaction API: `backend/src/api/transactions/`
- Home page: `frontend/app/pages/index.vue`
- TransactionRow component: `frontend/app/components/transactions/TransactionRow.vue`
- Existing tags system (similar pattern): `backend/src/postgres/common/models.py`
- Budgeting PRD: `prds/20260125-fullstack-budgeting-goals.md` (similar analytics pattern)
