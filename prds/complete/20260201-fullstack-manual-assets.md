# PRD: Manual Assets & Liabilities

**Status**: Complete
**Author**: Claude
**Created**: 2026-02-01
**Updated**: 2026-02-01

---

## Overview

Add support for manually tracking assets (property, vehicles, pensions, crypto) and liabilities (student loans, mortgages) that aren't connected to banking providers. These integrate with net worth calculations and support historical value tracking.

## Problem Statement

Users have significant wealth stored in assets that can't be automatically synced via Open Banking - property, vehicles, pensions, student loans, mortgages. Without tracking these, the net worth calculation is incomplete and misleading.

## Goals

- Track manual assets and liabilities with current values
- Maintain historical value snapshots for trend analysis
- Integrate with existing net worth calculations in dbt
- Provide a simple UI for adding and updating values

## Non-Goals

- Automatic valuation lookups (e.g., property price APIs)
- Amortisation calculations for loans
- Reminders to update values (tracked separately in ROADMAP)

---

## User Stories

1. **As a** user, **I want to** add my property as a manual asset, **so that** my net worth reflects my true financial position
2. **As a** user, **I want to** track my student loan balance, **so that** I can see how my debt reduces over time
3. **As a** user, **I want to** update asset values periodically, **so that** my net worth chart shows accurate trends
4. **As a** user, **I want to** see a breakdown of assets vs liabilities, **so that** I understand my financial composition

---

## Proposed Solution

### High-Level Design

- Separate `ManualAsset` table (not reusing `Account` which requires `connection_id`)
- Append-only `ManualAssetValueSnapshot` table for historical tracking
- Forward-fill pattern in dbt for continuous time series
- New frontend page under Planning section

### Data Model

#### ManualAsset

```sql
CREATE TABLE manual_assets (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    asset_type VARCHAR(50) NOT NULL,  -- enum: student_loan, mortgage, vehicle, property, etc.
    custom_type VARCHAR(100),          -- user's custom label
    is_liability BOOLEAN NOT NULL,
    name VARCHAR(200) NOT NULL,
    notes TEXT,
    current_value DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'GBP',
    interest_rate DECIMAL(5,2),        -- for loans/mortgages
    acquisition_date DATE,
    acquisition_value DECIMAL(15,2),
    is_active BOOLEAN DEFAULT TRUE,
    value_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### ManualAssetValueSnapshot

```sql
CREATE TABLE manual_asset_value_snapshots (
    id SERIAL PRIMARY KEY,
    asset_id UUID REFERENCES manual_assets(id) ON DELETE CASCADE,
    value DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    notes VARCHAR(500),                -- reason for update
    captured_at TIMESTAMP DEFAULT NOW()
);
```

### API Endpoints

| Method  | Path                                   | Description                                                     |
|---------|----------------------------------------|-----------------------------------------------------------------|
| GET     | `/api/manual-assets`                   | List all assets for user (filterable by type, liability status) |
| GET     | `/api/manual-assets/summary`           | Get totals (assets, liabilities, net)                           |
| POST    | `/api/manual-assets`                   | Create new asset                                                |
| GET     | `/api/manual-assets/{id}`              | Get single asset with details                                   |
| PATCH   | `/api/manual-assets/{id}`              | Update asset details (not value)                                |
| POST    | `/api/manual-assets/{id}/update-value` | Record new value (creates snapshot)                             |
| GET     | `/api/manual-assets/{id}/history`      | Get value history                                               |
| DELETE  | `/api/manual-assets/{id}`              | Soft delete (sets is_active=false)                              |

### UI/UX

**Page Location**: `/planning/assets`

**Layout**:

```
┌─────────────────────────────────────────────────────────┐
│  Manual Assets & Liabilities              [+ Add Asset] │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Assets   │  │Liabilities│  │Net Impact│              │
│  │ £150,000 │  │ -£45,000  │  │ £105,000 │              │
│  └──────────┘  └──────────┘  └──────────┘              │
├─────────────────────────────────────────────────────────┤
│  [All] [Assets] [Liabilities]  ← Filter tabs            │
├─────────────────────────────────────────────────────────┤
│  Assets                                                 │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 🏠 Property - Main Residence          £450,000    │ │
│  │    Updated 15 Jan 2026                [Update ▾]  │ │
│  └────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  Liabilities                                            │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 📚 Student Loan - Plan 2              £32,000     │ │
│  │    3.5% APR   Updated 1 Jan 2026      [Update ▾]  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Components**:

- `ManualAssetCard.vue` - Displays asset with actions dropdown
- `ManualAssetModal.vue` - Create/edit form with all fields
- `ValueUpdateModal.vue` - Quick value update with diff display

---

## Technical Considerations

### Dependencies

- Backend: SQLAlchemy, FastAPI, Alembic
- Frontend: Vue 3, Nuxt 4, existing App* components
- Analytics: dbt, DuckDB

### Migration

Single Alembic migration creates both tables with indexes:

- `idx_manual_assets_user_id`
- `idx_manual_assets_user_active` (user_id, is_active)
- `idx_manual_asset_snapshots_asset_captured` (asset_id, captured_at)

### dbt Integration

**New models**:

- `src_manual_assets.sql` - Source model filtering active assets
- `src_manual_asset_value_snapshots.sql` - Source model for snapshots
- `int_manual_asset_daily_values.sql` - Forward-fills gaps for continuous time series

**Modified models**:

- `fct_net_worth_history.sql` - UNIONs manual assets with account balances, adds:
  - `TOTAL_MANUAL_ASSETS` column
  - `TOTAL_MANUAL_LIABILITIES` column
  - Both included in `NET_WORTH` calculation

### Performance

- Forward-fill uses window functions (efficient in DuckDB)
- Indexes on user_id for fast filtering
- Summary endpoint aggregates in single query

### Security

- All endpoints require authentication
- User can only access their own assets (filtered by user_id from JWT)
- Soft delete preserves audit trail

---

## Implementation Plan

### Phase 1: Backend Database

- [x] Add `ManualAssetType` enum to `enums.py`
- [x] Add `ManualAsset` and `ManualAssetValueSnapshot` models
- [x] Generate migration with `alembic revision --autogenerate`
- [x] Create CRUD operations in `operations/manual_assets.py`

### Phase 2: Backend API

- [x] Create Pydantic schemas in `api/manual_assets/models.py`
- [x] Create endpoints in `api/manual_assets/endpoints.py`
- [x] Register router in `api/app.py`

### Phase 3: Frontend

- [x] Add types in `types/manual-assets.ts`
- [x] Create `composables/useManualAssetsApi.ts`
- [x] Build `ManualAssetCard.vue`, `ManualAssetModal.vue`, `ValueUpdateModal.vue`
- [x] Create page `pages/planning/assets.vue`
- [x] Add navigation link in `pages/planning.vue`

### Phase 4: dbt Integration

- [x] Add source definitions to `schema.yml`
- [x] Create `src_manual_assets.sql` and `src_manual_asset_value_snapshots.sql`
- [x] Create `int_manual_asset_daily_values.sql` with forward-fill logic
- [x] Update `fct_net_worth_history.sql` to include manual assets

### Phase 5: Tech Debt Cleanup

- [x] Extend `AppInput` to support number types with min/max/step/autofocus
- [x] Convert native number inputs to `AppInput` for consistency
- [x] Fix multi-line event handler syntax errors

---

## Testing Strategy

- [x] Unit tests for CRUD operations (covered by existing test patterns)
- [x] API endpoint tests (1001 tests passing, 82% coverage)
- [x] dbt model tests (147 tests passing)
- [x] TypeScript type checking (frontend passes)

---

## Rollout Plan

1. **Development**: Local testing with `make check` in both backend and frontend
2. **Production**: Deploy backend first (migration runs automatically), then frontend

---

## Files Changed

**Backend (new)**:

- `src/postgres/common/enums.py` - ManualAssetType enum
- `src/postgres/common/models.py` - ManualAsset, ManualAssetValueSnapshot models
- `src/postgres/common/operations/manual_assets.py` - CRUD operations
- `src/api/manual_assets/` - API module (models.py, endpoints.py, **init**.py)
- `alembic/versions/0d1c0abe3d33_add_manual_assets_tables.py` - Migration

**Backend (modified)**:

- `src/api/app.py` - Register router

**Frontend (new)**:

- `app/types/manual-assets.ts`
- `app/composables/useManualAssetsApi.ts`
- `app/components/assets/ManualAssetCard.vue`
- `app/components/assets/ManualAssetModal.vue`
- `app/components/assets/ValueUpdateModal.vue`
- `app/pages/planning/assets.vue`

**Frontend (modified)**:

- `app/pages/planning.vue` - Added "Assets" nav tab
- `app/components/AppInput.vue` - Extended for number type support

**dbt (new)**:

- `models/1_source/unified/src_manual_assets.sql`
- `models/1_source/unified/src_manual_asset_value_snapshots.sql`
- `models/3_mart/int_manual_asset_daily_values.sql`

**dbt (modified)**:

- `models/1_source/unified/schema.yml` - Added sources
- `models/3_mart/fct_net_worth_history.sql` - Integrated manual assets

---

## References

- Plan file: `/home/oli/.claude/plans/wild-pondering-cascade.md`
- ROADMAP.md: Manual Assets section marked complete
