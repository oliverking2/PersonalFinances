# PRD: Home Page & Navigation

**Status**: Complete
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-25

---

## Overview

Replace the placeholder dashboard with a proper home page showing key financial metrics at a glance. Add a navigation bar for easy access to all sections of the app.

## Problem Statement

The current dashboard is a placeholder with cards linking to other pages. Users have no quick overview of their financial position - they must navigate to individual pages to see anything useful. There's also no navigation bar, making it harder to move between sections.

Additionally, credit card balances currently show the credit limit as available funds, which would make net worth calculations incorrect.

## Goals

- Provide at-a-glance view of financial health (net worth, spending metrics)
- Enable quick navigation between app sections
- Fix credit card balance display to show actual liability
- Show recent transaction activity without leaving the home page

## Non-Goals

- Analytics page with charts and filtering (separate PRD)
- Mobile-optimised layouts (Phase 7)
- Upcoming bills/subscriptions (requires recurring transaction detection)
- Balance over time graphs (requires `fct_daily_balance_history` mart)

---

## User Stories

1. **As a** user, **I want to** see my net worth on the home page, **so that** I can quickly understand my overall financial position.

2. **As a** user, **I want to** see how much I've spent this month compared to last month, **so that** I can track my spending habits.

3. **As a** user, **I want to** see my recent transactions on the home page, **so that** I can spot any unexpected activity without navigating away.

4. **As a** user, **I want to** navigate between sections using a clear nav bar, **so that** I can quickly access accounts, transactions, and settings.

---

## Proposed Solution

### High-Level Design

1. **Navigation bar** - Add horizontal nav links to the header (Home, Accounts, Transactions, Settings)
2. **Home page** (`/`) - Replace redirect with actual content showing metrics and recent activity
3. **Credit card fix** - Investigate balance data and fix net worth calculation
4. **Analytics API composable** - Create frontend composable to query dbt marts for metrics

### Data Model

No schema changes required. Uses existing:

- `accounts` table (balance, category)
- `gc_balances` table (balance amounts)
- dbt marts (`fct_monthly_trends`, `fct_daily_spending_by_tag`)

**Credit card balance investigation needed:**

- Check what GoCardless returns in `gc_balances` for credit cards
- Determine if we need to use a different balance type or calculate owed amount
- May need to store/use `credit_limit` and `available_credit` differently

### API Endpoints

No new backend endpoints required. Uses existing:

| Method   | Path                                 | Description                           |
|----------|--------------------------------------|---------------------------------------|
| GET      | `/api/accounts`                      | Get all accounts with balances        |
| GET      | `/api/transactions`                  | Get recent transactions (limit=5)     |
| GET      | `/api/analytics/datasets/{id}/query` | Query spending metrics from dbt marts |
| GET      | `/api/analytics/status`              | Check if analytics data is available  |

### UI/UX

#### Navigation Bar

Add to `layouts/default.vue` header:

```
┌─────────────────────────────────────────────────────────────┐
│ Personal Finances    Home  Accounts  Transactions  Settings │
│                                               [User] [Logout]│
└─────────────────────────────────────────────────────────────┘
```

- "Personal Finances" title links to home (`/`)
- Active nav item highlighted
- Settings links to `/settings/tags` (or future `/settings` index)

#### Home Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Welcome back, [Name]                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Net Worth   │  │ This Month  │  │ vs Last     │         │
│  │ £12,345.67  │  │ £1,234.56   │  │ Month       │         │
│  │             │  │ spent       │  │ +12.3%      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐                          │
│  │ Top Category│  │ Transactions│                          │
│  │ Groceries   │  │ 142         │                          │
│  │ £456.78     │  │ this month  │                          │
│  └─────────────┘  └─────────────┘                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Recent Transactions                          View all →     │
├─────────────────────────────────────────────────────────────┤
│ Today                                                       │
│   Tesco          Groceries              -£45.23            │
│   TfL            Transport              -£2.80             │
│ Yesterday                                                   │
│   Amazon         Shopping               -£29.99            │
│   ...                                                       │
└─────────────────────────────────────────────────────────────┘
```

**Metric Cards:**

- Net Worth: Sum of all account balances (credit cards as negative)
- This Month Spent: Total outgoing transactions this month
- vs Last Month: Percentage change in spending
- Top Category: Highest spending tag this month with amount
- Transactions: Count of transactions this month

**Recent Transactions:**

- Show 5 most recent transactions
- Grouped by day (reuse existing `TransactionDayGroup` component)
- "View all" links to `/transactions`

#### Empty/Loading States

- **Loading**: Skeleton cards while fetching
- **No accounts**: "Connect a bank account to see your finances" with link to Accounts
- **No transactions**: "No transactions yet" message
- **Analytics unavailable**: Show net worth (from accounts API) but grey out spending metrics with "Analytics loading..." or similar

---

## Technical Considerations

### Dependencies

**Frontend:**

- New `useAnalyticsApi.ts` composable for querying dbt marts
- Existing `useAccountsApi.ts` for account balances
- Existing `useTransactionsApi.ts` for recent transactions
- Existing `TransactionRow.vue` / `TransactionDayGroup.vue` components

**Backend:**

- Existing analytics endpoints
- May need to investigate GoCardless balance types for credit cards

### Credit Card Balance Investigation

Need to check:

1. What balance types does GoCardless return for credit cards?
2. Is `balance.amount` the owed amount or available credit?
3. Do we need to use `balance.type` to distinguish?

Options:

- If GoCardless returns owed amount as negative: use as-is
- If GoCardless returns available credit: calculate owed = credit_limit - available
- May need to store credit_limit on account model

### Performance

- Home page makes 3 parallel API calls (accounts, transactions, analytics)
- Analytics queries hit DuckDB which is fast for aggregations
- Consider caching metrics in frontend for quick navigation back to home

### Security

No new security considerations - uses existing authenticated endpoints.

---

## Implementation Plan

### Phase 1: Navigation Bar ✅

- [x] Add nav links to `layouts/default.vue` header
- [x] Style active link state
- [x] Update "Personal Finances" title to link to `/`
- [x] Add Settings to nav (links to `/settings/tags`)

### Phase 2: Credit Card Balance Fix ✅

- [x] Investigate GoCardless balance data for credit cards
- [x] Determine correct calculation for owed amount
- [x] ~~Update backend or frontend to show correct balance~~ Deferred - needs credit limit storage
- [x] Ensure net worth calculation treats credit cards as liabilities (excluded from net worth for now)

**Note**: Investigation found that GoCardless stores `credit_limit_included` flag but not the actual credit limit value. For accurate liability calculation, backend would need to store credit limit. MVP approach: exclude credit cards from net worth calculation.

### Phase 3: Analytics API Composable ✅

- [x] Create `composables/useAnalyticsApi.ts`
- [x] Add functions: `fetchAnalyticsStatus()`, `queryDataset()`
- [x] Add types in `types/analytics.ts`

### Phase 4: Home Page ✅

- [x] Create metric card component (`components/home/MetricCard.vue`)
- [x] Replace `/` redirect with actual home page content
- [x] Implement net worth card (sum accounts, credit cards excluded)
- [x] Implement spending metrics cards (query `fct_monthly_trends`)
- [x] Implement top category card (query `fct_daily_spending_by_tag`)
- [x] Implement recent transactions section
- [x] Add loading skeletons
- [x] Add empty states
- [x] Handle analytics unavailable state

### Phase 5: Cleanup ✅

- [x] Remove `pages/dashboard.vue`
- [x] Update `login.vue` to redirect to `/` instead of `/dashboard`

---

## Testing Strategy

- [ ] Manual testing: Navigation works on all pages
- [ ] Manual testing: Home page loads with real data
- [ ] Manual testing: Credit card balances show correctly
- [ ] Manual testing: Empty states display correctly
- [ ] Manual testing: Analytics unavailable state handled gracefully

---

## Rollout Plan

1. **Development**: Build and test locally with seed data
2. **Validation**: Run `make check` in both backend/ and frontend/
3. **Production**: Deploy - no migration needed

---

## Open Questions

- [x] What balance type does GoCardless return for credit cards? → **Needs investigation**
- [x] Should Settings be a nav item or just accessible from a user menu? → **Nav item**
- [x] Should we show "Analytics refreshing..." during dbt rebuild? → **Yes, grey out spending metrics**

---

## References

- [ROADMAP.md - Phase 2.9](../ROADMAP.md)
- [Analytics API endpoints](../backend/src/api/analytics/endpoints.py)
- [Account types](../frontend/app/types/accounts.ts)
