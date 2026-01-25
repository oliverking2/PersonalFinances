# PRD: Analytics Page

**Status**: Draft
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-25

---

## Overview

Create a dedicated analytics page with charts and visualisations for deeper insight into spending patterns. Users can filter by time period and compare current spending against previous periods.

## Problem Statement

The home page provides a quick glance at key metrics, but users need a dedicated space to explore their spending in detail - seeing breakdowns by category, trends over time, and comparing periods to understand their financial habits.

## Goals

- Visualise spending by tag/category
- Show spending trends over time
- Enable period filtering (this month, last month, custom)
- Compare current period vs previous period
- Provide manual refresh for analytics data

## Non-Goals

- Balance over time graphs (requires `fct_daily_balance_history` mart - future work)
- Export functionality (separate PRD exists)
- Mobile-optimised chart layouts (Phase 7)
- Drill-down into individual transactions from charts

---

## User Stories

1. **As a** user, **I want to** see a breakdown of my spending by category, **so that** I understand where my money goes.

2. **As a** user, **I want to** see my spending trend over the month, **so that** I can identify patterns (e.g., spending more at weekends).

3. **As a** user, **I want to** compare this month to last month, **so that** I can see if my spending habits are improving.

4. **As a** user, **I want to** filter analytics to specific time periods, **so that** I can analyse different timeframes.

5. **As a** user, **I want to** refresh the analytics data, **so that** I see the latest transactions reflected in charts.

---

## Proposed Solution

### High-Level Design

Create `/analytics` page with:

1. Time period filter controls
2. Chart visualisations (bar, line, pie/donut)
3. Data table view
4. Period comparison toggle
5. Manual refresh button

### Dependencies

**Prerequisite**: Home Page PRD must be implemented first as it creates:

- `useAnalyticsApi.ts` composable
- `types/analytics.ts` type definitions
- Navigation bar with Analytics link

### Data Sources

Uses existing dbt marts via analytics API:

| Dataset                     | Use                                    |
|-----------------------------|----------------------------------------|
| `fct_monthly_trends`        | Month-over-month totals for comparison |
| `fct_daily_spending_by_tag` | Daily breakdown by tag for charts      |
| `fct_transactions`          | Raw transaction data for table view    |
| `dim_tags`                  | Tag names and colours for chart labels |

### API Endpoints

No new endpoints. Uses existing:

| Method   | Path                                 | Description             |
|----------|--------------------------------------|-------------------------|
| GET      | `/api/analytics/datasets`            | List available datasets |
| GET      | `/api/analytics/datasets/{id}/query` | Query with filters      |
| POST     | `/api/analytics/refresh`             | Trigger dbt rebuild     |
| GET      | `/api/jobs/{id}`                     | Poll refresh job status |

### UI/UX

#### Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Analytics                                    [↻ Refresh]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Period: [This Month ▼]  ☑ Compare to previous period       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Spending by Category                                       │
│  ┌────────────────────────────────────────────────────────┐│
│  │ ████████████████████ Groceries     £456.78  (35%)     ││
│  │ ████████████████     Transport     £312.45  (24%)     ││
│  │ ██████████           Dining        £198.23  (15%)     ││
│  │ ████████             Shopping      £156.00  (12%)     ││
│  │ ██████               Other         £180.54  (14%)     ││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Daily Spending Trend                                       │
│  ┌────────────────────────────────────────────────────────┐│
│  │     ·                                                  ││
│  │    · ·      ·                    ·                     ││
│  │   ·   ·    · ·    ·   ·        · ·     ·              ││
│  │  ·     ·  ·   ·  · · · ·  ·   ·   ·   · ·  ·         ││
│  │ ·       ··     ··       ·· · ·     · ·   ·· ·         ││
│  │─────────────────────────────────────────────────────── ││
│  │ 1    5    10    15    20    25    30                  ││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────────┐│
│  │  Category Breakdown  │  │  Summary                     ││
│  │      [Donut Chart]   │  │                              ││
│  │                      │  │  Total Spent: £1,304.00      ││
│  │    ┌───┐             │  │  vs Last Month: +12.3%       ││
│  │   /     \            │  │  Transactions: 142           ││
│  │  │       │           │  │  Avg per day: £43.47         ││
│  │   \     /            │  │                              ││
│  │    └───┘             │  │                              ││
│  └──────────────────────┘  └──────────────────────────────┘│
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Transactions Table                          [Toggle view] │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Date       │ Tag       │ Count │ Total                 ││
│  │────────────┼───────────┼───────┼───────────────────────││
│  │ 2026-01-25 │ Groceries │ 3     │ £67.45                ││
│  │ 2026-01-25 │ Transport │ 2     │ £5.60                 ││
│  │ 2026-01-24 │ Dining    │ 1     │ £34.50                ││
│  │ ...        │           │       │                       ││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Period Filter

Dropdown with presets:

- This month (default)
- Last month
- Last 30 days
- Last 90 days
- This year
- Custom range (shows date pickers)

#### Comparison Mode

When "Compare to previous period" is checked:

- Bar chart shows side-by-side bars (current vs previous)
- Summary card shows percentage change
- Line chart overlays previous period as dashed line

#### Refresh Button

- Shows spinner while refreshing
- Polls job status until complete
- Toast notification on success/failure
- Disables button during refresh

#### Chart Library

ApexCharts + vue3-apexcharts

Chosen for:

- Better animations and transitions out of the box
- Built-in toolbar (download as PNG/SVG, zoom controls)
- More interactive (zoom, pan, data point selection)
- Good TypeScript support
- Modern look with less styling effort

Bundle size ~120KB gzipped - acceptable for a dedicated analytics page.

#### Empty States

- **No data for period**: "No transactions found for this period"
- **No tags assigned**: "Tag your transactions to see category breakdowns"
- **Analytics unavailable**: "Analytics data is being prepared. Try refreshing."

---

## Technical Considerations

### Chart Component Structure

```
components/analytics/
├── PeriodFilter.vue        # Dropdown + date pickers
├── SpendingByCategory.vue  # Horizontal bar chart
├── DailySpendingTrend.vue  # Line chart
├── CategoryBreakdown.vue   # Donut/pie chart
├── SpendingSummary.vue     # Summary stats card
└── SpendingTable.vue       # Data table with sorting
```

### Data Fetching Strategy

1. On mount and period change, fetch all required datasets in parallel
2. Transform data for each chart component
3. Cache results - only refetch on period change or manual refresh

### Performance

- ApexCharts is ~120KB gzipped - acceptable for dedicated analytics page
- Limit data points on line chart (aggregate to daily)
- ApexCharts handles animations efficiently, no special optimisation needed

### Accessibility

- Ensure charts have aria labels
- Provide data table as accessible alternative to visual charts
- Colour choices should work for colour-blind users

---

## Implementation Plan

### Phase 1: Setup & Period Filter

- [ ] Install chart library (`apexcharts`, `vue3-apexcharts`)
- [ ] Create `pages/analytics.vue` skeleton
- [ ] Create `PeriodFilter.vue` component
- [ ] Wire up period selection to API queries

### Phase 2: Bar Chart - Spending by Category

- [ ] Create `SpendingByCategory.vue`
- [ ] Query `fct_daily_spending_by_tag` grouped by tag
- [ ] Render horizontal bar chart with tag colours
- [ ] Add comparison bars when comparison mode enabled

### Phase 3: Line Chart - Daily Trend

- [ ] Create `DailySpendingTrend.vue`
- [ ] Query `fct_daily_spending_by_tag` grouped by date
- [ ] Render line chart with daily totals
- [ ] Add dashed line for previous period in comparison mode

### Phase 4: Donut Chart & Summary

- [ ] Create `CategoryBreakdown.vue` (donut/pie)
- [ ] Create `SpendingSummary.vue` (stats card)
- [ ] Calculate totals, averages, percentage changes

### Phase 5: Data Table

- [ ] Create `SpendingTable.vue`
- [ ] Show daily spending by tag in tabular format
- [ ] Add sorting by date/tag/amount

### Phase 6: Refresh Functionality

- [ ] Add refresh button to page header
- [ ] Call `/api/analytics/refresh` on click
- [ ] Poll job status and show progress
- [ ] Refetch data on completion

### Phase 7: Polish

- [ ] Loading skeletons for each chart
- [ ] Empty state handling
- [ ] Error handling and retry
- [ ] Responsive layout adjustments

---

## Testing Strategy

- [ ] Manual testing: Period filter changes update all charts
- [ ] Manual testing: Comparison mode shows correct data
- [ ] Manual testing: Refresh triggers dbt and updates data
- [ ] Manual testing: Empty states display correctly
- [ ] Manual testing: Charts render correctly with various data shapes

---

## Rollout Plan

1. **Development**: Build with seed data, test various scenarios
2. **Validation**: Run `make check` in frontend/
3. **Production**: Deploy - no backend changes needed

---

## Open Questions

- [x] Which chart library to use? → **ApexCharts** (better UX, built-in toolbar, smooth animations)
- [x] Should table be collapsible or always visible? → **Toggle view button**
- [x] Should charts animate on load? → **Yes, ApexCharts has good defaults**

---

## Future Enhancements

- Balance over time chart (when `fct_daily_balance_history` available)
- Account filter (show spending for specific accounts)
- Export charts as images
- Drill-down from chart segment to transaction list

---

## References

- [ROADMAP.md - Phase 2.9](../ROADMAP.md)
- [Home Page PRD](./20260125-fullstack-home-page.md) (prerequisite)
- [Analytics API endpoints](../backend/src/api/analytics/endpoints.py)
- [dbt marts](../backend/dbt/models/mart/)
