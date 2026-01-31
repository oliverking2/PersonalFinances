# dbt CLAUDE.md

dbt-specific guidance for analytics transformations. See also `backend/CLAUDE.md`.

## Architecture

DuckDB reads from PostgreSQL via the postgres extension, enabling:

- Fast analytical queries without impacting the main database
- SQL-based transformations with version control
- Self-documenting data lineage

```
PostgreSQL (source of truth)
    ↓ (postgres extension)
DuckDB (analytics engine)
    ↓ (dbt transforms)
Mart tables → API → Frontend
```

## Layer Convention

```
models/
├── 1_source/          # Raw tables from PostgreSQL
│   ├── gocardless/    # Provider-specific sources
│   └── unified/       # Standardised tables (accounts, transactions)
├── 2_staging/         # Cleaned and typed data
│   └── stg_*.sql      # One model per source table
└── 3_mart/            # Business-ready aggregations
    ├── dim_*.sql      # Dimension tables (accounts, tags)
    ├── fct_*.sql      # Fact tables (transactions, spending)
    └── int_*.sql      # Intermediate models (not exposed to API)
```

### Layer Rules

| Layer   | Prefix | Purpose                          | Materialized |
|---------|--------|----------------------------------|--------------|
| Source  | -      | Mirror PostgreSQL tables         | table        |
| Staging | `stg_` | Clean, type, rename columns      | view         |
| Mart    | `dim_` | Dimension/lookup tables          | view         |
| Mart    | `fct_` | Fact tables with metrics         | view         |
| Mart    | `int_` | Intermediate (not for API)       | view         |

## Naming Conventions

- **Source tables**: Match PostgreSQL table names exactly
- **Staging models**: `stg_{source}_{table}` (e.g., `stg_gocardless_all_transactions`)
- **Fact models**: `fct_{metric}` (e.g., `fct_daily_spending_by_tag`)
- **Dimension models**: `dim_{entity}` (e.g., `dim_accounts`)
- **Intermediate**: `int_{purpose}` (e.g., `int_recurring_candidates`)

## Commands

```bash
cd backend

# Build all models
make dbt

# Build specific model
poetry run dbt run --profiles-dir dbt --profile duckdb_local -s fct_transactions

# Run tests
poetry run dbt test --profiles-dir dbt --profile duckdb_local

# Generate docs
make dbt-docs
```

## Schema Files

Each layer has a `schema.yml` defining:

- Column descriptions (shown in docs)
- Tests (not_null, unique, accepted_values, relationships)
- Meta tags for Dagster integration

```yaml
models:
  - name: fct_transactions
    description: "All transactions with tags and splits"
    columns:
      - name: id
        description: "Transaction UUID"
        tests:
          - not_null
          - unique
      - name: status
        tests:
          - accepted_values:
              values: ['pending', 'active', 'paused', 'cancelled']
```

## Dagster Integration

Models are tagged for Dagster scheduling:

```yaml
+meta:
  dagster:
    group: dbt_mart
+tags: ["auto_eager", "auto_hourly"]
```

- `auto_eager`: Run when upstream changes
- `auto_hourly`: Also run on hourly schedule

## Key Patterns

### Filter Metadata

Mart models expose filter options via metadata comments:

```sql
-- Filter options exposed to frontend
-- Available filters: account_ids, tag_ids, start_date, end_date
SELECT ...
```

### User Scoping

All mart models filter by `user_id` for multi-tenancy:

```sql
SELECT *
FROM {{ ref('stg_transactions') }}
WHERE user_id = '{{ var("user_id") }}'  -- Passed at query time
```

### Date Handling

- Store dates as `DATE` type, datetimes as `TIMESTAMP`
- Use `CAST(column AS DATE)` when comparing date ranges
- Gap-fill time series with `GENERATE_SERIES` for charts

## Testing

```bash
# Run all dbt tests
poetry run dbt test --profiles-dir dbt --profile duckdb_local

# Test specific model
poetry run dbt test --profiles-dir dbt --profile duckdb_local -s fct_transactions
```

Tests run automatically via `make dbt` and during `make check`.

## Troubleshooting

### "Column not found" errors

Check that source tables are materialised first (`make dbt` runs in order).

### Stale data

Source tables are `materialized: table` - they snapshot PostgreSQL. Re-run dbt to refresh.

### Type mismatches

DuckDB is strict about types. Use explicit `CAST()` when joining or comparing.
