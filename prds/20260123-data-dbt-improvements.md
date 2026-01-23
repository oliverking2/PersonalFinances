# PRD: dbt Model Improvements

**Status**: In Progress
**Author**: Claude
**Created**: 2026-01-17
**Updated**: 2026-01-23

---

## Overview

Fix broken dbt models, add comprehensive data quality tests, and implement source freshness monitoring.

## Problem Statement

The dbt layer has several issues:

1. `src_gocardless_transactions.sql` fails with a column reference error
2. No data quality tests on staging models
3. No source freshness monitoring to detect stale data

## Goals

- Fix all dbt model build errors
- Add comprehensive data quality tests
- Implement source freshness checks
- Add model documentation

## Non-Goals

- Adding new mart models
- Performance optimisation
- Changing the source → staging → mart layer structure

---

## Improvements

### 1. Fix Broken Model

**File**: `dbt/models/1_source/src_gocardless_transactions.sql`

**Issue**: Model fails with "Binder Error: Referenced column '_extract_dt' not found in FROM clause"

**Fix**: Update the SQL to correctly reference columns available from `READ_JSON()` or remove the column if not needed.

**Status**: [ ] Not started

### 2. Add Data Quality Tests

**File**: `dbt/models/2_staging/schema.yml`

Add comprehensive tests to staging models:

```yaml
models:
  - name: stg_gocardless_all_transactions
    columns:
      - name: transaction_id
        data_tests:
          - not_null
          - unique
      - name: account_id
        data_tests:
          - not_null
      - name: amount
        data_tests:
          - not_null
      - name: currency
        data_tests:
          - not_null
          - accepted_values:
              values: ['GBP', 'EUR', 'USD']
      - name: transaction_type
        data_tests:
          - not_null
          - accepted_values:
              values: ['booked', 'pending']
```

**Status**: [ ] Not started

### 3. Add Source Freshness

**File**: `dbt/models/1_source/schema.yml`

```yaml
sources:
  - name: dagster
    freshness:
      warn_after: {count: 24, period: hour}
      error_after: {count: 48, period: hour}
    loaded_at_field: _extract_dt
    tables:
      - name: gocardless_raw_transactions
        description: Raw transaction data from GoCardless API
      - name: gocardless_raw_account_details
        description: Account metadata from GoCardless API
      - name: gocardless_raw_account_balances
        description: Balance snapshots from GoCardless API
```

**Status**: [ ] Not started

### 4. Add Model Documentation

Add descriptions to all models and columns in schema.yml files.

**Status**: [ ] Not started

---

## Implementation Plan

### Phase 1: Critical Fix

- [ ] Fix `src_gocardless_transactions.sql` error

### Phase 2: Data Quality

- [ ] Add tests to staging models
- [ ] Add source freshness checks

### Phase 3: Documentation

- [ ] Add model descriptions
- [ ] Add column descriptions

---

## Testing Strategy

```bash
cd dbt

# Build models
dbt run --profiles-dir . --profile duckdb_local

# Run tests
dbt test --profiles-dir . --profile duckdb_local

# Check freshness
dbt source freshness --profiles-dir . --profile duckdb_local
```

---

## Success Metrics

- [ ] dbt models build without errors
- [ ] All data quality tests pass
- [ ] Source freshness checks configured

---

## References

- Original PRD: `202601-backend-foundation-improvements.md` (split)
- dbt best practices: <https://docs.getdbt.com/best-practices>
