# PRD: Analytics Polish

**Status**: Complete
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-25

---

## Overview

Three improvements to analytics accuracy and home page usability: exclude internal transfers from spending calculations, add net worth trend indicator, and make metric cards clickable with navigation.

## Problem Statement

1. **Internal transfers inflate spending**: When transferring money between accounts, both the outgoing and incoming transactions are counted, making spending appear higher than actual external expenditure.
2. **Net worth lacks context**: Users see their current net worth but have no indication of whether it's growing or shrinking compared to last month.
3. **Metric cards are static**: Users must manually navigate to relevant pages; the dashboard should provide direct access to detailed views.

## Goals

- Accurately reflect external spending by excluding matched internal transfer pairs
- Show net worth trend (% change from last month) on home page
- Enable click-through navigation from metric cards to relevant detail pages

## Non-Goals

- Detecting cross-currency internal transfers (rare, acceptable limitation)
- Manual transfer tagging UI
- Historical net worth tracking beyond current month comparison

---

## User Stories

1. **As a** user with multiple bank accounts, **I want** internal transfers excluded from spending totals, **so that** I see only money leaving my accounts to external parties.
2. **As a** user tracking my finances, **I want** to see if my net worth is growing or shrinking, **so that** I can monitor my financial health at a glance.
3. **As a** user viewing the dashboard, **I want** to click on metrics to see more detail, **so that** I can quickly investigate specific areas.

---

## Proposed Solution

### High-Level Design

1. **Internal transfer detection in dbt**: Match transactions where same user, different accounts, same date, and opposite amounts (e.g., -100 and +100). Exclude matched pairs from spending/income calculations.

2. **Net worth trend calculation**: Frontend computes `previous_net_worth = current_net_worth - this_month_net_change` using existing monthly trends data. Display percentage change.

3. **Clickable metric cards**: Add optional `to` prop to MetricCard component; renders as NuxtLink when provided.

### Data Model

No schema changes. Logic changes in dbt models:

- `fct_daily_spending_by_tag.sql`: Exclude internal transfer spending
- `fct_monthly_trends.sql`: Exclude both sides of internal transfers

### Internal Transfer Detection Logic

```sql
-- A negative transaction is an internal transfer if there exists a positive transaction
-- on the same day, same absolute amount, same user, different account
INTERNAL_TRANSFER_IDS AS (
    SELECT DISTINCT T1.TRANSACTION_ID
    FROM TRANSACTIONS_WITH_USER AS T1
    WHERE T1.AMOUNT < 0
      AND EXISTS (
          SELECT 1
          FROM TRANSACTIONS_WITH_USER AS T2
          WHERE T2.USER_ID = T1.USER_ID
            AND T2.ACCOUNT_ID != T1.ACCOUNT_ID
            AND T2.BOOKING_DATE = T1.BOOKING_DATE
            AND T2.AMOUNT = -T1.AMOUNT
      )
)
```

### UI/UX

**Net Worth Card Changes:**

- Shows trend arrow with percentage (green up for growth, red down for decline)
- Subtitle "vs last month" when trend is available
- Clicks through to `/accounts`

**Metric Card Navigation:**

| Card             | Destination                                            |
|------------------|--------------------------------------------------------|
| Net Worth        | `/accounts`                                            |
| Spent This Month | `/analytics`                                           |
| vs Last Month    | `/analytics`                                           |
| Top Category     | `/transactions?tag={name}&start_date=...&end_date=...` |
| Transactions     | `/transactions?start_date=...&end_date=...`            |

---

## Technical Considerations

### Dependencies

- Existing dbt models for transaction aggregation
- Existing MetricCard component
- Existing monthly trends API

### Performance

- Internal transfer detection uses EXISTS subquery (efficient for indexed columns)
- Net worth trend calculation is client-side using already-fetched data (no additional API calls)

### Edge Cases

- **Different currencies**: GBP to EUR transfers won't match exactly due to conversion. These remain in spending totals (acceptable for rare cases).
- **Multiple transfers same day/amount**: Both pairs detected correctly.
- **New users with no history**: Net worth trend shows null (no trend displayed).
- **Muted cards (analytics unavailable)**: Not clickable, maintains disabled appearance.

---

## Implementation Plan

### Phase 1: dbt Models (Backend)

- [x] Update `fct_daily_spending_by_tag.sql` to exclude internal transfer spending
- [x] Update `fct_monthly_trends.sql` to exclude both sides of internal transfers

### Phase 2: MetricCard Component (Frontend)

- [x] Add `to` prop for optional navigation
- [x] Add `trendInverted` prop (positive = good for net worth)
- [x] Render as NuxtLink when `to` provided and not loading/muted
- [x] Add hover state styling for clickable cards

### Phase 3: Home Page (Frontend)

- [x] Add net worth trend computation from monthly trends data
- [x] Add navigation destinations to all metric cards
- [x] Compute filtered transaction links with date/tag parameters

---

## Testing Strategy

- [x] dbt models build without errors
- [x] Frontend typecheck passes
- [ ] Manual: Verify spending totals lower after excluding transfers
- [ ] Manual: Verify legitimate external payments still counted
- [ ] Manual: Net Worth card shows trend with correct colour (green for growth)
- [ ] Manual: All metric cards navigate to correct destinations
- [ ] Manual: Muted cards (analytics unavailable) are not clickable

---

## Files Modified

| File                                                      | Changes                                                     |
|-----------------------------------------------------------|-------------------------------------------------------------|
| `backend/dbt/models/3_mart/fct_daily_spending_by_tag.sql` | Internal transfer pair detection                            |
| `backend/dbt/models/3_mart/fct_monthly_trends.sql`        | Internal transfer pair detection (both sides)               |
| `frontend/app/components/home/MetricCard.vue`             | Added `to` and `trendInverted` props, NuxtLink rendering    |
| `frontend/app/pages/index.vue`                            | Net worth trend computation, navigation links for all cards |
