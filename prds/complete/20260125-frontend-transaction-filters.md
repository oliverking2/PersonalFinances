# PRD: Transaction Filter Dropdowns

**Status**: Complete
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-25

---

## Overview

Replace the four separate date/amount filter inputs with two dropdown components: DateFilterDropdown (with presets) and ValueFilterDropdown. This consolidates the filter bar from 6 fields to 4, providing quicker filtering for common date ranges.

## Problem Statement

The current filter bar has six separate inputs (Accounts, Tags, From date, To date, Min amount, Max amount), making it cluttered. Users frequently filter by common date ranges (this month, last 30 days, this year) and currently must manually enter both start and end dates.

## Goals

- Provide quick access to common date range presets
- Consolidate filter UI from 6 fields to 4 dropdowns
- Maintain full custom date/amount filtering capability
- Match existing dropdown patterns for consistency

## Non-Goals

- Server-side filtering changes (filtering remains client-side)
- Adding additional preset options beyond the initial four

---

## User Stories

1. **As a** user filtering transactions, **I want to** quickly select "This month" from a dropdown, **so that** I can view this month's transactions with one click.
2. **As a** user filtering transactions, **I want to** specify custom date ranges when presets don't match my needs, **so that** I can filter to any arbitrary period.
3. **As a** user filtering by amount, **I want to** set min/max values in a dropdown, **so that** the filter bar is less cluttered.

---

## Proposed Solution

### High-Level Design

**Before:**

```
[Accounts ▼] [Tags ▼] [From: ___] [To: ___] [Min] [Max] [Clear]
```

**After:**

```
[Accounts ▼] [Tags ▼] [Date ▼] [Value ▼] [Clear]
```

### Date Presets

| Preset       | Start Date              | End Date       |
|--------------|-------------------------|----------------|
| This month   | 1st of current month    | Today          |
| Last 30 days | Today - 30 days         | Today          |
| This year    | Jan 1st of current year | Today          |
| Custom       | User-specified          | User-specified |

### UI/UX

**DateFilterDropdown:**

- Radio-style options for presets
- "Custom" option reveals From/To date inputs within the dropdown
- Display shows preset name or "Custom: Jan 1 - Jan 25"

**ValueFilterDropdown:**

- Min/Max number inputs inside dropdown
- Display shows "All values" or "£10 - £100"

---

## Technical Considerations

### Files Created

| File                                                           | Purpose                    |
|----------------------------------------------------------------|----------------------------|
| `frontend/app/composables/useDatePresets.ts`                   | Date calculation utilities |
| `frontend/app/components/transactions/DateFilterDropdown.vue`  | Date preset dropdown       |
| `frontend/app/components/transactions/ValueFilterDropdown.vue` | Amount range dropdown      |

### Files Modified

| File                                                          | Changes                            |
|---------------------------------------------------------------|------------------------------------|
| `frontend/app/components/transactions/TransactionFilters.vue` | Replaced 4 inputs with 2 dropdowns |

---

## Implementation Plan

### Phase 1: Composable

- [x] Create useDatePresets with preset calculation functions
- [x] Add detectPreset function for matching dates to presets
- [x] Add formatDateRangeDisplay for human-readable output

### Phase 2: Components

- [x] Create DateFilterDropdown with radio options and custom inputs
- [x] Create ValueFilterDropdown with min/max inputs

### Phase 3: Integration

- [x] Update TransactionFilters to use new dropdowns
- [x] Update event handlers to match new emit signatures

---

## Testing Strategy

- [x] Manual testing: Preset selection sets correct dates
- [x] Manual testing: Custom mode shows date inputs
- [x] Manual testing: Value filter sets min/max correctly
- [x] Manual testing: Clear button resets all filters
- [x] TypeScript/linting: `make check` passes

---

## References

- Pattern reference: `frontend/app/components/FilterDropdown.vue`
- Date preset inspiration: Common patterns in financial apps (Mint, YNAB)
