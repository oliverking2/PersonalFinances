# PRD: Semantic Layer — dbt Metadata + Query Builder

**Status**: Complete
**Author**: Claude
**Created**: 2026-02-07
**Updated**: 2026-02-08

---

## Overview

Extend dbt's existing schema metadata with semantic definitions (measures, dimensions, sample questions) and build a Python query builder that translates structured query specs into safe DuckDB SQL. This gives the Agent API (PRD 3) a governed query vocabulary without introducing a separate service.

## Problem Statement

The Agent API needs a constrained query vocabulary — it should not generate arbitrary SQL. But adding a separate semantic layer service (Cube, etc.) introduces operational complexity and creates a second source of truth for metric definitions alongside dbt's `schema.yml`.

Instead, we extend dbt's existing metadata — which already defines datasets, columns, filters, and descriptions — with semantic information (measures, dimensions, aggregation types). A Python query builder validates and translates agent query specs into parameterised DuckDB SQL, using the same pattern as the existing `queries.py`.

## Goals

- Semantic metadata (measures, dimensions, sample questions) defined in dbt `schema.yml` — single source of truth
- Extended `manifest.py` to parse semantic metadata from the dbt manifest
- New query builder that translates structured query specs into safe DuckDB SQL
- Schema discovery for the agent to learn what queries are possible
- No new services or infrastructure

## Non-Goals

- Separate semantic layer service (Cube, MetricFlow)
- Cross-dataset joins (single-dataset queries only for now)
- Pre-aggregations or caching layer (DuckDB + Parquet is fast enough)
- Changing existing analytics API endpoints (these continue to use `build_dataset_query`)

---

## User Stories

1. **As a** developer, **I want** measures and dimensions defined alongside dbt models, **so that** there's one place to maintain metric definitions
2. **As a** developer, **I want** a query builder that only accepts known measures/dimensions, **so that** the agent can't generate invalid or dangerous queries
3. **As a** developer, **I want** schema discovery from the manifest, **so that** the agent dynamically learns what queries are possible without hardcoding

---

## Proposed Solution

### High-Level Design

```
dbt schema.yml (meta.semantic)
    ↓ dbt build / dbt parse
manifest.json (contains semantic metadata)
    ↓ parsed by
manifest.py (extended with SemanticDataset)
    ↓ used by
semantic.py (query builder: spec → DuckDB SQL)
    ↓ executed by
client.py (DuckDB connection)
```

### Dependency on PRD 1

PRD 1 (Parquet Migration) is **complete**. The backend now reads mart models from Parquet files via in-memory DuckDB connections with views registered under the `mart` schema. The semantic query builder generates SQL referencing `mart.{table}`, which resolves to these Parquet-backed views.

### dbt Schema Enrichment

**`backend/dbt/models/3_mart/schema.yml`** — Add `meta.semantic` block per dataset:

```yaml
- name: fct_monthly_trends
  description: |
    Monthly income, spending, and net trends per user.
  meta:
    dataset: true
    friendly_name: "Monthly Trends"
    group: "aggregations"
    time_grain: "month"
    filters:
      date_column: "month_start"
    semantic:
      measures:
        - name: total_income
          expr: total_income
          agg: sum
          description: "Total income for the period"
        - name: total_spending
          expr: total_spending
          agg: sum
          description: "Total spending for the period"
        - name: net_change
          expr: net_change
          agg: sum
          description: "Net change (income minus spending)"
        - name: savings_rate
          expr: savings_rate_pct
          agg: avg
          description: "Average savings rate as percentage"
        - name: total_transactions
          expr: total_transactions
          agg: sum
          description: "Total number of transactions"
      dimensions:
        - name: month
          expr: month_start
          type: time
          granularities: [month, quarter, year]
          description: "Month of the data"
        - name: currency
          expr: currency
          type: categorical
          description: "Currency code (ISO 4217)"
      sample_questions:
        - "How much did I spend last month?"
        - "What's my average monthly income?"
        - "Show me my savings rate trend over the last 6 months"
        - "Which month had the highest spending this year?"
```

There are **11 datasets** with `meta.dataset: true` in the current `schema.yml` (excluding `int_recurring_candidates` which has `dataset: false`). Each gets a `semantic` block. The existing `filters`, `friendly_name`, `group`, and `time_grain` metadata stays as-is.

**Important — run `make dbt` (or `dbt parse`) after modifying `schema.yml`** to regenerate `manifest.json`. The semantic metadata is only available to the parser after this step.

### Double Aggregation Caveat

Mart tables are pre-aggregated. The semantic layer applies aggregation on top. This is correct for `SUM` (e.g., summing monthly totals to get a yearly total) but can be misleading for `AVG` (e.g., averaging monthly savings rates gives "average of monthly rates", not a single overall rate).

**Rule for measure definitions:**

| Pre-aggregated column     | Safe semantic `agg`                                 | Avoid                                         |
|---------------------------|-----------------------------------------------------|-----------------------------------------------|
| SUM (total_spending)      | `sum` (re-aggregates correctly)                     | `avg` (misleading)                            |
| COUNT (transaction_count) | `sum` (counts are additive)                         | `avg` (gives avg count per period, not total) |
| AVG (savings_rate_pct)    | `avg` (only when grouping at same or coarser grain) | `sum` (meaningless)                           |
| Snapshot (net_worth)      | `max` or `min` (latest/earliest)                    | `sum` (double-counts)                         |

Document this rule in `backend/dbt/CLAUDE.md` so future measure authors avoid incorrect aggregations.

### Extended Manifest Parser

**`backend/src/duckdb/manifest.py`** — New dataclasses and parsing:

```python
@dataclass
class Measure:
    """A queryable measure (metric) in a dataset."""
    name: str           # Agent-facing name
    expr: str           # SQL column expression
    agg: str            # Aggregation type: sum, avg, count, count_distinct, min, max
    description: str

@dataclass
class Dimension:
    """A queryable dimension in a dataset."""
    name: str           # Agent-facing name
    expr: str           # SQL column expression
    type: str           # time, categorical, numeric
    description: str
    granularities: list[str] | None = None  # For time dims: day, week, month, etc.

@dataclass
class SemanticDataset:
    """A dataset with full semantic metadata for agent queries."""
    id: UUID
    name: str
    friendly_name: str
    description: str
    group: str
    time_grain: str | None
    schema_name: str
    filters: DatasetFilters
    measures: list[Measure]
    dimensions: list[Dimension]
    sample_questions: list[str]
    columns: list[DatasetColumn] | None = None
```

New functions:

- `get_semantic_datasets()` → `list[SemanticDataset]` — Returns datasets with measures/dimensions parsed from `meta.semantic`. Uses the same manifest node key format (`model.dbt_project.{name}`) as existing code.
- `get_semantic_dataset(dataset_id: UUID | str)` → `SemanticDataset | None` — Single dataset lookup. Accepts UUID or name, matching the existing `get_dataset_schema()` signature.
- `get_all_sample_questions()` → `list[str]` — Collects sample questions across all datasets

The existing `get_datasets()` and `get_dataset_schema()` remain unchanged — existing analytics endpoints are unaffected.

### Semantic Query Builder

**`backend/src/duckdb/semantic.py`** (new file):

The query builder takes a structured `QuerySpec` and a `SemanticDataset`, validates the spec against the dataset's measures/dimensions, and produces safe parameterised SQL.

```python
@dataclass
class QuerySpec:
    """Structured query specification from the agent."""
    dataset: str                              # Dataset name (e.g., "fct_monthly_trends")
    measures: list[str]                       # Measure names to select
    dimensions: list[str] | None = None       # Dimension names to group by
    filters: list[QueryFilter] | None = None  # Filters to apply
    time_granularity: str | None = None       # For time dimensions: day, week, month, etc.
    order_by: str | None = None               # Measure or dimension name to order by
    order_direction: str = "DESC"             # ASC or DESC
    limit: int = 1000                         # Row limit

@dataclass
class QueryFilter:
    """A filter in a query spec."""
    dimension: str           # Dimension name
    operator: str            # eq, neq, gt, gte, lt, lte, in, not_in, between
    value: Any               # Filter value(s)

@dataclass
class QueryResult:
    """Result of a semantic query with provenance."""
    data: list[dict[str, Any]]
    provenance: QueryProvenance

@dataclass
class QueryProvenance:
    """What was queried and how — for the agent's response and API output."""
    dataset_name: str
    dataset_friendly_name: str
    measures_queried: list[str]
    dimensions_queried: list[str]
    filters_applied: list[dict[str, Any]]
    row_count: int
    query_duration_ms: int
```

**Note:** `QueryProvenance` is the single provenance type used throughout. PRD 3's API `Provenance` response model maps directly to this dataclass. There is no separate `Provenance` type — `QueryProvenance` is the source of truth.

**Exception class** — Define in `semantic.py`:

```python
class InvalidQueryError(Exception):
    """Raised when a query spec fails validation."""
```

Core functions:

- `validate_query_spec(spec, dataset)` → raises `InvalidQueryError` if measures/dimensions don't exist, operator is invalid, etc.
- `build_semantic_query(spec, dataset, user_id)` → `tuple[str, dict[str, Any]]` — Produces parameterised SQL
- `execute_semantic_query(spec, user_id)` → `QueryResult` — Validates, builds, executes, returns results with provenance

**Query building logic:**

```python
def build_semantic_query(
    spec: QuerySpec,
    dataset: SemanticDataset,
    user_id: UUID,
) -> tuple[str, dict[str, Any]]:
    # 1. Resolve measures → SELECT with aggregation
    select_parts = []
    for m_name in spec.measures:
        measure = _find_measure(dataset, m_name)
        select_parts.append(f"{measure.agg.upper()}({measure.expr}) AS {measure.name}")

    # 2. Resolve dimensions → SELECT + GROUP BY
    group_parts = []
    for d_name in (spec.dimensions or []):
        dim = _find_dimension(dataset, d_name)
        if dim.type == "time" and spec.time_granularity:
            expr = _apply_time_granularity(dim.expr, spec.time_granularity)
        else:
            expr = dim.expr
        select_parts.append(f"{expr} AS {dim.name}")
        group_parts.append(expr)

    # 3. Build query
    select_clause = ", ".join(select_parts)
    query = f"SELECT {select_clause} FROM {dataset.schema_name}.{dataset.name}"
    query += " WHERE user_id = $user_id"
    params: dict[str, Any] = {"user_id": str(user_id)}

    # 4. Apply filters (validated against known dimensions)
    for idx, f in enumerate(spec.filters or []):
        dim = _find_dimension(dataset, f.dimension)
        param_name = f"filter_{idx}"
        if f.operator == "eq":
            query += f" AND {dim.expr} = ${param_name}"
            params[param_name] = f.value
        elif f.operator == "neq":
            query += f" AND {dim.expr} != ${param_name}"
            params[param_name] = f.value
        elif f.operator in ("gt", "gte", "lt", "lte"):
            op = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[f.operator]
            query += f" AND {dim.expr} {op} ${param_name}"
            params[param_name] = f.value
        elif f.operator == "in":
            # IN requires list expansion — use DuckDB list syntax
            placeholders = ", ".join(f"${param_name}_{i}" for i in range(len(f.value)))
            query += f" AND {dim.expr} IN ({placeholders})"
            for i, v in enumerate(f.value):
                params[f"{param_name}_{i}"] = v
        elif f.operator == "not_in":
            placeholders = ", ".join(f"${param_name}_{i}" for i in range(len(f.value)))
            query += f" AND {dim.expr} NOT IN ({placeholders})"
            for i, v in enumerate(f.value):
                params[f"{param_name}_{i}"] = v
        elif f.operator == "between":
            query += f" AND {dim.expr} BETWEEN ${param_name}_lo AND ${param_name}_hi"
            params[f"{param_name}_lo"] = f.value[0]
            params[f"{param_name}_hi"] = f.value[1]

    # 5. GROUP BY, ORDER BY, LIMIT
    if group_parts:
        query += f" GROUP BY {', '.join(group_parts)}"
    if spec.order_by:
        direction = "ASC" if spec.order_direction == "ASC" else "DESC"
        query += f" ORDER BY {spec.order_by} {direction}"
    query += f" LIMIT {min(spec.limit, 10000)}"

    return query, params
```

**Validation rules:**

| Check                       | What it validates                                                              |
|-----------------------------|--------------------------------------------------------------------------------|
| Measures exist              | Every measure name in `spec.measures` exists in `dataset.measures`             |
| Dimensions exist            | Every dimension name exists in `dataset.dimensions`                            |
| At least one measure        | Queries must select at least one measure                                       |
| Operators valid             | Only allowed: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `between` |
| Time granularity valid      | If specified, must be in the dimension's `granularities` list                  |
| Limit bounded               | Must be between 1 and 10,000                                                   |
| Order direction valid       | Must be `ASC` or `DESC`                                                        |
| `in`/`not_in` value is list | `value` must be a list for these operators                                     |
| `between` value is pair     | `value` must be a list of exactly 2 elements                                   |

### DuckDB Module Exports

**`backend/src/duckdb/__init__.py`** — Add new exports:

```python
from src.duckdb.semantic import (
    InvalidQueryError,
    QueryFilter,
    QueryProvenance,
    QueryResult,
    QuerySpec,
    build_semantic_query,
    execute_semantic_query,
    validate_query_spec,
)
```

Also add `SemanticDataset`, `Measure`, `Dimension`, `get_semantic_datasets`, `get_semantic_dataset`, `get_all_sample_questions` from manifest.

### Data Model

No database changes. All metadata lives in dbt `schema.yml` and flows through `manifest.json`.

### API Endpoints

No new API endpoints in this PRD. The semantic query builder is used internally by the Agent API (PRD 3). Existing analytics endpoints remain unchanged.

### Test Coverage

The `src/duckdb/` directory is currently excluded from coverage in `pyproject.toml`. The new `semantic.py` module should be **included** in coverage since it is pure Python logic (no DuckDB integration required for unit tests). Add an exception for `semantic.py` in the coverage config, or restructure the exclusion to only cover `client.py`.

---

## Technical Considerations

### Dependencies

- No new Python dependencies. Uses existing `duckdb`, `dataclasses`, `uuid`.
- Requires dbt manifest to be regenerated after `schema.yml` changes (`make dbt` or `dbt parse`)

### Migration

No migration. Additive metadata in `schema.yml` — existing fields unchanged.

### Performance

- Manifest parsing is fast (JSON load, dict iteration)
- Query building is pure string manipulation — negligible overhead
- Generated SQL uses the same parameterised pattern as existing `queries.py`
- DuckDB + Parquet reads are ~10-50ms for typical mart queries

### Security

- All generated queries include `WHERE user_id = $user_id` — mandatory, not optional
- Measure/dimension names validated against known schema before SQL generation — prevents injection
- Filter values are parameterised (`$param_name`) — no string interpolation of user data
- Column expressions (`expr`) come from dbt YAML (developer-authored), not from the agent
- `validate_query_spec()` rejects any unknown measures, dimensions, or operators

---

## Implementation Plan

### Phase 1: Schema Enrichment

- [ ] Add `meta.semantic` blocks to all 11 datasets with `meta.dataset: true` in `backend/dbt/models/3_mart/schema.yml`
- [ ] Add `sample_questions` to each dataset (3-4 questions per dataset)
- [ ] Run `make dbt` (or `dbt parse`) to regenerate `manifest.json`
- [ ] Verify semantic metadata appears in `manifest.json` under each node's `meta.semantic`

### Phase 2: Manifest Parser Extension

- [ ] Add `Measure`, `Dimension`, `SemanticDataset` dataclasses to `manifest.py`
- [ ] Add `get_semantic_datasets()` and `get_semantic_dataset()` functions
- [ ] Add `get_all_sample_questions()` function
- [ ] Update `backend/src/duckdb/__init__.py` to export new types and functions
- [ ] Write unit tests for semantic parsing (mock manifest JSON)

### Phase 3: Query Builder

- [ ] Create `backend/src/duckdb/semantic.py` with `QuerySpec`, `QueryFilter`, `QueryProvenance`, `InvalidQueryError`
- [ ] Implement `validate_query_spec()` with all validation rules
- [ ] Implement `build_semantic_query()` with full filter parameterisation
- [ ] Implement `execute_semantic_query()`
- [ ] Update `pyproject.toml` coverage config to include `semantic.py`
- [ ] Write unit tests for query building (valid specs, invalid specs, edge cases)
- [ ] Write unit tests for validation (unknown measures, bad operators, type mismatches)
- [ ] Write unit tests for each filter operator

### Phase 4: Documentation

- [ ] Add double-aggregation rules to `backend/dbt/CLAUDE.md`
- [ ] Document semantic metadata format in `backend/dbt/CLAUDE.md`

---

## Testing Strategy

- [ ] Unit tests for `get_semantic_datasets()` with mock manifest containing semantic metadata
- [ ] Unit tests for `validate_query_spec()` — valid specs pass, invalid specs raise `InvalidQueryError`
- [ ] Unit tests for `build_semantic_query()` — generated SQL is correct for various spec combinations
- [ ] Unit tests for every filter operator (eq, neq, gt, gte, lt, lte, in, not_in, between)
- [ ] Unit tests for time granularity application
- [ ] Unit tests for edge cases (empty measures list, no dimensions, limit at boundaries)
- [ ] Integration test: `execute_semantic_query()` returns correct data from DuckDB (manual test, since `src/duckdb/` is excluded from automated coverage)
- [ ] `make check` passes in backend/

---

## Rollout Plan

1. **Development**: Add semantic metadata, extend parser, build query builder, all tested locally
2. **Production**: Deploy — no impact on existing functionality. Semantic layer is only used by Agent API (PRD 3).

---

## Open Questions

- [ ] Should measure aggregation support computed measures (e.g., `total_spending / total_transactions`)? → Not for POC. Add later if needed.

---

## Files to Create/Modify

**New:**

- `backend/src/duckdb/semantic.py` — Query builder, validation, provenance

**Modified:**

- `backend/dbt/models/3_mart/schema.yml` — Add `meta.semantic` blocks to 11 datasets
- `backend/src/duckdb/manifest.py` — Add `Measure`, `Dimension`, `SemanticDataset`, parsing functions
- `backend/src/duckdb/__init__.py` — Export new types and functions
- `backend/pyproject.toml` — Coverage config for `semantic.py`
- `backend/dbt/CLAUDE.md` — Document semantic metadata format and aggregation rules

---

## References

- Existing manifest parser: `backend/src/duckdb/manifest.py` (node key format: `model.dbt_project.{name}`)
- Existing query builder: `backend/src/duckdb/queries.py`
- PRD 1 (dbt Parquet Migration) — **complete**
- Depended on by: PRD 3 (Agent API)
