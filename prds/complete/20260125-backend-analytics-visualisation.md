# PRD: Analytics & Visualisation Backend

**Status**: Complete
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-25

---

## Overview

Implementation of a metadata-driven analytics layer using dbt marts, exposed via FastAPI endpoints. This provides the foundation for frontend analytics dashboards and future dataset exports.

## Problem Statement

Users need insights into their financial data - spending patterns, balance trends, and income/expense breakdowns. The raw transaction data exists in PostgreSQL but lacks the aggregated views needed for efficient analytics queries and visualisations.

## Goals

- Pre-aggregated analytics marts for efficient querying
- RESTful API endpoints for common analytics use cases
- Dataset discovery mechanism for future self-service exports
- User data isolation (queries always filter by user)

## Non-Goals

- Frontend visualisation components (separate implementation)
- CSV/Parquet export functionality (future work via Dagster jobs)
- Real-time streaming analytics
- Machine learning/forecasting

---

## User Stories

1. **As a** user, **I want to** see my spending breakdown by tag, **so that** I understand where my money goes
2. **As a** user, **I want to** view monthly income vs spending trends, **so that** I can track my savings rate
3. **As a** user, **I want to** see my account balance history, **so that** I can monitor my financial health

---

## Proposed Solution

### High-Level Design

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PostgreSQL    │────▶│     DuckDB      │────▶│    FastAPI      │
│  (source data)  │     │  (dbt marts)    │     │  (analytics)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       ▲                       │
        │                       │                       │
        └───────────────────────┘                       │
                dbt (via Dagster)                       │
                                                        ▼
                                               Real-time queries
```

### Data Model

**Dimension Tables** (`backend/dbt/models/3_mart/`):

| Model          | Purpose                                                 |
|----------------|---------------------------------------------------------|
| `dim_accounts` | Account context with connection and institution details |
| `dim_tags`     | User-defined tags metadata                              |

**Fact Tables**:

| Model                       | Purpose                             | Time Grain      |
|-----------------------------|-------------------------------------|-----------------|
| `fct_transactions`          | Transactions with denormalized tags | per-transaction |
| `fct_daily_spending_by_tag` | Pre-aggregated spending per tag     | day             |
| `fct_daily_balance_history` | Balance snapshots per account       | day             |
| `fct_monthly_trends`        | Income/spending/net by month        | month           |

**dbt Meta Convention**:

```yaml
meta:
  dataset: true              # Discoverable via API
  friendly_name: "Transactions"
  group: "facts|dimensions|aggregations"
  time_grain: "day|month"    # Optional
  filters:                   # Filter column configuration
    date_column: "booking_date"       # Column for date range filtering
    account_id_column: "account_id"   # Column for account filtering
    tag_id_column: "tag_id"           # Column for tag filtering
```

### API Endpoints

| Method  | Path                                  | Description                                 |
|---------|---------------------------------------|---------------------------------------------|
| GET     | `/api/analytics/status`               | Check analytics system availability         |
| GET     | `/api/analytics/datasets`             | List available datasets (from dbt metadata) |
| GET     | `/api/analytics/datasets/{id}/schema` | Get dataset schema & columns                |
| GET     | `/api/analytics/datasets/{id}/query`  | Query any dataset with filters              |
| POST    | `/api/analytics/refresh`              | Trigger dbt rerun via Dagster               |

**Query Parameters** (for `/datasets/{id}/query`):

- `start_date`: Filter from date (YYYY-MM-DD) - uses `meta.filters.date_column`
- `end_date`: Filter to date (YYYY-MM-DD)
- `account_ids`: Filter by account UUIDs - uses `meta.filters.account_id_column`
- `tag_ids`: Filter by tag UUIDs - uses `meta.filters.tag_id_column`
- `limit`: Max rows (default 1000, max 10000)
- `offset`: Pagination offset

---

## Technical Considerations

### Dependencies

- **DuckDB**: Read-only analytics database (`analytics.duckdb`)
- **dbt**: Data transformation framework
- **Dagster**: Orchestration for dbt runs

### New Modules

```
backend/
├── src/
│   ├── api/analytics/
│   │   ├── __init__.py
│   │   ├── endpoints.py    # API routes
│   │   └── models.py       # Pydantic response models
│   └── duckdb/
│       ├── __init__.py
│       ├── client.py       # Read-only connection management
│       ├── manifest.py     # Parse dbt metadata for discovery
│       └── queries.py      # Parameterized query builders
└── dbt/models/3_mart/
    ├── schema.yml          # Model definitions with meta tags
    ├── dim_accounts.sql
    ├── dim_tags.sql
    ├── fct_transactions.sql
    ├── fct_daily_spending_by_tag.sql
    ├── fct_daily_balance_history.sql
    └── fct_monthly_trends.sql
```

### Performance

- Connection-per-request pattern (DuckDB is fast, no pooling needed)
- Query timeout: 10 seconds
- Result set limit: 10,000 rows
- Pre-aggregated tables reduce query complexity

### Security

- All queries filter by `user_id` (fetched from JWT)
- Account/tag IDs validated against user ownership before querying
- Parameterized queries only (no string interpolation)
- Read-only DuckDB connections

---

## Implementation Plan

### Phase A: dbt Foundation - Complete

- [x] Create `dim_accounts.sql` with connection/institution joins
- [x] Create `dim_tags.sql` for tag metadata
- [x] Create `fct_transactions.sql` with denormalized tags
- [x] Add `schema.yml` with meta tags and data quality tests

### Phase B: DuckDB Client - Complete

- [x] Create `client.py` for read-only connection management
- [x] Create `manifest.py` for parsing dbt metadata
- [x] Create `queries.py` for parameterized query building

### Phase C: Analytics API - Complete

- [x] Create Pydantic response models
- [x] Implement dataset discovery endpoints
- [x] Implement convenience endpoints (spending-by-tag, trends, balance-history)
- [x] Implement refresh trigger endpoint
- [x] Register router in `app.py`

### Phase D: Aggregation Models - Complete

- [x] Create `fct_daily_spending_by_tag.sql`
- [x] Create `fct_monthly_trends.sql`
- [x] Create `fct_daily_balance_history.sql`
- [x] Update schema.yml with column documentation

---

## Testing Strategy

- [x] Unit tests for analytics endpoints (mocked DuckDB)
- [x] Integration tests via existing test fixtures
- [x] All tests passing: 427 tests, 91% coverage

**Test Coverage**:

- Dataset discovery endpoints
- Spending-by-tag with date/tag filtering
- Monthly trends with date filtering
- Balance history with account filtering
- Refresh job triggering
- Error handling (DuckDB unavailable, unknown datasets)

---

## Rollout Plan

1. **Development**: Run `dbt build` to create analytics.duckdb
2. **Verification**: Test endpoints via curl or API docs
3. **Production**: Deploy with existing CI/CD pipeline

**Verification Commands**:

```bash
# Build dbt models
cd backend/dbt && dbt build --profiles-dir . --profile duckdb_local

# Run backend tests
cd backend && make check

# Manual API test
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/analytics/spending-by-tag?start_date=2025-01-01"
```

---

## Future Work

### Export Engine (Dagster Job)

When CSV/Parquet exports are needed, implement as a Dagster job:

```python
@job
def dataset_export_job():
    execute_export()
```

**Additional Endpoints**:

- `POST /api/analytics/exports` - Create export job
- `GET /api/analytics/exports/{job_id}` - Poll status, get download URL

---

## References

- [dbt Documentation](https://docs.getdbt.com/)
- [DuckDB Python API](https://duckdb.org/docs/api/python/overview)
- Backend patterns: `backend/CLAUDE.md`
