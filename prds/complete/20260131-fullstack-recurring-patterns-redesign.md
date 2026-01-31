# Recurring Patterns Redesign PRD

**Date**: 2026-01-31
**Scope**: fullstack
**Status**: Implemented

## Summary

Redesigned the recurring patterns system from an **opt-out** model (detection creates patterns, user dismisses unwanted) to an **opt-in** model (detection suggests patterns, user accepts wanted). This gives users control while keeping detection as a useful helper.

## Problem Statement

The previous system automatically created recurring patterns when detected, requiring users to dismiss unwanted ones. This led to:

- Clutter from false positives
- Users feeling they had lost control over their financial tracking
- Confusion between "detected" and "confirmed" states

## Solution

### Design Decisions

1. **Single Table with Status**: Rather than separate tables for patterns and suggestions, use a single `recurring_patterns` table with status field (`pending`/`active`/`paused`/`cancelled`).

2. **Hybrid Matching Rules**: Common cases use dedicated columns (`merchant_contains`, `amount_tolerance_pct`) for performance. Edge cases use JSONB (`advanced_rules`) for flexibility.

3. **One Pattern Per Transaction**: A transaction can only be linked to one pattern. This prevents confusion and simplifies forecasting.

4. **Opt-in Flow**: Detection creates patterns as `pending`. Users must explicitly accept them to make them `active`.

### Status Workflow

```
[Detection] → pending → [Accept] → active ⟷ paused
                ↓                      ↓
           [Dismiss]              [Cancel]
           (delete)               cancelled
```

### New Schema

**RecurringPattern**:

- `name` (renamed from `display_name`)
- `source` (`detected`/`manual`)
- `status` (`pending`/`active`/`paused`/`cancelled`)
- `merchant_contains` (case-insensitive partial match)
- `amount_tolerance_pct` (default 10%)
- `last_matched_date` (renamed from `last_occurrence_date`)
- `end_date` (for cancelled patterns)
- `match_count` (number of linked transactions)
- `detection_reason` (human-readable explanation)

**RecurringPatternTransaction**:

- `is_manual` (user linked vs auto-matched)
- `matched_at` (when the link was created)
- UNIQUE constraint on `transaction_id`

### API Changes

**Renamed**: `/api/subscriptions` → `/api/recurring`

**New Endpoints**:

- `POST /api/recurring/patterns/{id}/accept` - Accept pending pattern
- `POST /api/recurring/patterns/{id}/pause` - Pause active pattern
- `POST /api/recurring/patterns/{id}/resume` - Resume paused pattern
- `POST /api/recurring/patterns/{id}/cancel` - Cancel pattern
- `POST /api/recurring/patterns/{id}/relink` - Re-run matching
- `POST /api/recurring/patterns/from-transactions` - Create from selected transactions
- `POST /api/recurring/patterns/{id}/transactions` - Manually link transaction
- `DELETE /api/recurring/patterns/{id}/transactions/{txn}` - Unlink transaction

**Removed**:

- `PUT /api/subscriptions/{id}/confirm` - Replaced by `/accept`

## Implementation

### Backend

1. **Enums** (`backend/src/postgres/common/enums.py`):
   - Updated `RecurringStatus`: `pending`, `active`, `paused`, `cancelled`
   - Added `RecurringSource`: `detected`, `manual`

2. **Models** (`backend/src/postgres/common/models.py`):
   - Refactored `RecurringPattern` with new fields
   - Updated `RecurringPatternTransaction` with unique constraint

3. **Operations** (`backend/src/postgres/common/operations/recurring_patterns.py`):
   - Complete rewrite with new matching logic
   - Added `normalize_for_matching()` for stripping variable parts from merchant names
   - Added status transition functions

4. **API** (`backend/src/api/recurring/`):
   - Renamed from `subscriptions/`
   - New endpoints for status actions
   - Updated request/response models

5. **Dagster** (`backend/src/orchestration/recurring_patterns/assets.py`):
   - Now creates patterns as `pending` instead of auto-confirming
   - Links matching transactions during sync

6. **dbt** (`backend/dbt/models/`):
   - Updated source and fact models for new schema
   - Cash flow forecast now filters by `status = 'active'`

### Frontend

1. **Types** (`frontend/app/types/recurring.ts`):
   - New types for `RecurringPattern`, `RecurringStatus`, `RecurringSource`
   - Updated API response types

2. **Composable** (`frontend/app/composables/useRecurringApi.ts`):
   - New API composable with all endpoints
   - Renamed from `useSubscriptionsApi.ts`

3. **Page** (`frontend/app/pages/planning/recurring.vue`):
   - Updated to use new types and API
   - Status tabs now show `pending`/`active`/`paused`/`cancelled`

4. **Components** (`frontend/app/components/subscriptions/`):
   - `RecurringPatternCard.vue` - New card component
   - `RecurringPatternEditModal.vue` - Updated modal
   - `UpcomingBillsWidget.vue` - Updated for new API

### Migration

Alembic migration handles:

- Adding new columns
- Migrating status values: `detected` → `pending`, `confirmed`/`manual` → `active`, `dismissed` → delete
- Adding unique constraint on `transaction_id`

## Testing

- [x] Backend API tests for new endpoints
- [x] Backend operations tests for matching and status transitions
- [ ] Frontend integration tests
- [ ] Manual testing of full flow:
  - Accept pending pattern
  - Dismiss pending pattern
  - Pause/resume active pattern
  - Create pattern from transactions
  - Edit pattern rules and verify re-linking

## Future Considerations

- AI-powered rule suggestions via `ai_metadata` JSONB field
- Natural language pattern creation ("track my gym membership")
- Anomaly detection for missed payments
