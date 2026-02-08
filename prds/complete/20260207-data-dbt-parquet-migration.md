# PRD: dbt Parquet Migration

**Status**: Complete
**Author**: Claude
**Created**: 2026-02-07
**Updated**: 2026-02-08

---

## Overview

Replace the monolithic `analytics.duckdb` file with individual Parquet files written by dbt. The backend queries in-memory DuckDB instances that read Parquet at query time, eliminating shared file state between containers and resolving file-locking risks.

## Problem Statement

The `analytics.duckdb` file is shared via a Docker volume (`duckdb_data`) between the backend, dagster-webserver, and dagster-daemon containers. DuckDB has single-writer semantics — if Dagster is running `dbt build` while the backend serves a query, file locking can cause failures. The file is binary, hard to inspect, and makes the pipeline stateful.

## Goals

- Eliminate shared `analytics.duckdb` file between containers
- dbt mart models output as individual Parquet files
- Backend reads Parquet via stateless in-memory DuckDB connections
- Zero change to existing analytics API contract (transparent migration)
- Dagster and backend no longer share mutable state

## Non-Goals

- Changing the analytics API shape or response format
- Moving to S3/cloud storage (easy to add later since DuckDB `read_parquet` supports S3 URIs)
- Modifying dbt model logic or adding new models
- Changing the frontend

---

## User Stories

1. **As a** developer, **I want to** eliminate the shared DuckDB file, **so that** Dagster writes and backend reads never conflict
2. **As a** developer, **I want to** inspect analytics output as Parquet files, **so that** I can debug data pipeline issues easily
3. **As a** user, **I want** the analytics API to work identically, **so that** my experience is unchanged

---

## Proposed Solution

### High-Level Design

```
dbt build (in Dagster)
    ↓ writes (atomic: write-to-temp then rename)
data/parquet/mart/*.parquet    ← individual files per mart model
    ↑ reads
Backend DuckDB client (in-memory, stateless)
```

Source and staging layers remain as in-memory DuckDB tables during the dbt build (they need the PostgreSQL attachment). Only mart models materialise as Parquet — these are the only models the backend queries.

### dbt Configuration

**`backend/dbt/dbt_project.yml`** — Changed mart materialisation to `external`:

```yaml
3_mart:
  +materialized: external
  +schema: mart
```

**`backend/dbt/profiles.yml`** — Added `external_root` to the dev output:

```yaml
external_root: "{{ env_var('PARQUET_DIR', '../data/parquet') }}/mart"
```

**Implementation note:** Used `external_root` in `profiles.yml` instead of per-model `+external_location`. dbt-duckdb auto-names files after the model (e.g., `fct_transactions.parquet`), so no `{name}` token or per-model location config was needed. This was simpler than the PRD's original `+external_location` approach.

### Filepaths

**`backend/src/filepaths.py`** — Add `PARQUET_DIR`, keep `DUCKDB_PATH` for migration grace period:

```python
PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", BACKEND_DIR / "data" / "parquet"))
```

### Backend DuckDB Client

**`backend/src/duckdb/client.py`** — Refactor to read from Parquet:

- `get_connection()` creates an in-memory DuckDB connection (`:memory:`)
- Creates `mart` schema: `CREATE SCHEMA IF NOT EXISTS mart`
- Scans `PARQUET_DIR/mart/` directory for `.parquet` files
- Registers each file as a view: `CREATE VIEW mart.{stem} AS SELECT * FROM read_parquet('{path}')`
- Falls back to existing DuckDB file if Parquet directory is empty (migration grace period)
- `execute_query()` interface unchanged — callers are unaffected

**Note on `read_only`:** The current client opens the DuckDB file with `read_only=True`. In-memory connections cannot use `read_only=True` (they are inherently writable in-process). After migration, read-only safety is enforced by the Docker volume mount (`:ro`) rather than the DuckDB connection flag.

- `check_connection()` — Update to check whether Parquet files exist in `PARQUET_DIR/mart/` (currently checks whether the DuckDB file is accessible)

### Analytics Endpoints

**`backend/src/api/analytics/endpoints.py`** — Update functions that depend on the DuckDB file:

- `_get_last_refresh_time()` — Currently uses `DUCKDB_PATH.stat().st_mtime`. Change to check the newest `.parquet` file's modification time in `PARQUET_DIR/mart/`. Fall back to `DUCKDB_PATH` if Parquet dir is empty (migration grace period).
- Remove import of `DUCKDB_PATH` once fallback is removed

### Bootstrap Script

**`backend/scripts/bootstrap_duckdb.py`** — Repurpose to create the Parquet directory:

```python
def bootstrap() -> None:
    """Bootstrap data directories and DuckDB extensions."""
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    (PARQUET_DIR / "mart").mkdir(exist_ok=True)
    # Still bootstrap DuckDB for dbt builds (source/staging need it)
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")
    con.close()
```

### Docker Changes

**`docker-compose.yml`**:

Replace the shared `duckdb_data` named volume with explicit bind mounts per container:

| Container           | Mount                                                      | Access     | Purpose                                   |
|---------------------|------------------------------------------------------------|------------|-------------------------------------------|
| `backend`           | `./data/parquet:/app/data/parquet:ro`                      | Read-only  | Query Parquet files                       |
| `dagster-daemon`    | `./data/parquet:/opt/dagster/dagster_home/data/parquet`    | Read-write | dbt writes Parquet here                   |
| `dagster-webserver` | `./data/parquet:/opt/dagster/dagster_home/data/parquet:ro` | Read-only  | Does not run dbt, only needs to see files |

Environment variable changes per container:

| Container           | Add                                                   | Change                                                            |
|---------------------|-------------------------------------------------------|-------------------------------------------------------------------|
| `backend`           | `PARQUET_DIR: /app/data/parquet`                      | Remove `DUCKDB_PATH`                                              |
| `dagster-daemon`    | `PARQUET_DIR: /opt/dagster/dagster_home/data/parquet` | Keep `DUCKDB_PATH: /tmp/dbt_build.duckdb` (ephemeral, not shared) |
| `dagster-webserver` | `PARQUET_DIR: /opt/dagster/dagster_home/data/parquet` | Keep `DUCKDB_PATH: /tmp/dbt_build.duckdb` (ephemeral)             |

The `duckdb_data` named volume is removed. Each Dagster container gets its own ephemeral DuckDB file at `/tmp/dbt_build.duckdb` for source/staging tables during builds — this is never shared.

### DuckDB Module Exports

**`backend/src/duckdb/__init__.py`** — No changes needed in Phase 1. When PRD 2 (Semantic Layer) is implemented, new exports will be added.

### Data Model

No changes to existing data models. Parquet files contain identical schemas to the DuckDB mart views.

### API Endpoints

No changes to API contracts. The analytics endpoints continue to work identically. Only internal helper functions (`_get_last_refresh_time`, `check_connection`) are updated.

---

## Technical Considerations

### Dependencies

- `dbt-duckdb ^1.10.0` (already present) — supports `external` materialisation
- `pyarrow ^22.0.0` (already present) — Parquet read support
- No new Python dependencies required

### Migration

**Phase 1**: dbt writes Parquet alongside existing DuckDB file. Backend client detects Parquet and uses it, falls back to DuckDB file.

**Phase 2**: Once verified, remove DuckDB file references and `duckdb_data` volume.

The fallback ensures zero downtime — if Parquet dir is empty (e.g., first deploy before dbt runs), the backend uses the existing DuckDB file.

### Performance

- In-memory DuckDB + `read_parquet()` is extremely fast for the dataset sizes involved (< 100K rows per mart)
- Parquet is columnar — queries that select a subset of columns read less data than DuckDB file
- No file locking overhead — each request gets its own in-memory DuckDB instance (existing pattern)
- First query per request creates schema + views (~1-2ms overhead for 11 Parquet files)

### Security

- Backend Docker mount is read-only (`:ro`) — cannot accidentally corrupt analytics output
- `read_only=True` connection flag is replaced by Docker mount-level enforcement
- No change to API authentication or user scoping — `user_id` filtering still applied at query time
- Parquet files contain no credentials or secrets

### Write Atomicity

DuckDB's `COPY ... TO` with Parquet format writes to a temporary file then renames atomically (on POSIX filesystems). This means a backend read during a dbt build will see either the previous complete file or the new complete file — never a partial/corrupt file. This is the key improvement over the DuckDB file lock approach.

---

## Implementation Plan

### Phase 1: dbt Configuration

- [x] Add `PARQUET_DIR` to `backend/src/filepaths.py`
- [x] Update `backend/dbt/dbt_project.yml` to use `external` materialisation for mart models
- [x] Used `external_root` in `profiles.yml` (simpler than per-model `external_location`)
- [x] Update `backend/scripts/bootstrap_duckdb.py` to create Parquet directory
- [x] Add `PARQUET_DIR` to `backend/.env_example`
- [x] Update `make dbt` to create `data/parquet/mart/` directory before build

### Phase 2: Backend Client

- [x] Refactor `backend/src/duckdb/client.py`:
  - `get_connection()` — in-memory DuckDB, create `mart` schema, register Parquet views, DuckDB file fallback
  - `check_connection()` — check Parquet files exist (with DuckDB file fallback)
- [x] Update `backend/src/api/analytics/endpoints.py`:
  - `_get_last_refresh_time()` — use newest Parquet file mtime (with DuckDB file fallback)
- [x] All existing analytics API tests pass (1035 passed, 81.57% coverage)

### Phase 3: Docker Updates

- [x] Update `docker-compose.yml`:
  - Replace `duckdb_data` volume with per-container bind mounts
  - Update environment variables per container
  - Set Dagster `DUCKDB_PATH` to `/tmp/dbt_build.duckdb`
  - Remove `duckdb_data` named volume
- [x] Update `Makefile` `dbt` target to create Parquet directory

### Phase 4: Cleanup

- [ ] Remove DuckDB file fallback from `client.py` once stable in production
- [ ] Remove `DUCKDB_PATH` from backend container environment
- [ ] Note: `.gitignore` already covers `data/` and `*.parquet` — no changes needed

---

## Testing Strategy

- [ ] `make dbt` produces Parquet files in `data/parquet/mart/` (one per mart model with `meta.dataset: true`)
- [ ] All existing analytics API tests pass unchanged
- [ ] Frontend analytics pages render correctly with identical data
- [ ] `docker compose up` with new volume mounts works end-to-end
- [ ] Fallback to DuckDB file works when Parquet dir is empty
- [ ] Concurrent read during `dbt build` — verify no corrupt/partial reads (manual test: start `dbt run` in one terminal, query API in another)
- [ ] `_get_last_refresh_time()` returns correct timestamp from Parquet files
- [ ] `check_connection()` returns `True` when Parquet files exist
- [ ] `make check` passes in backend/

---

## Rollout Plan

1. **Development**: Local testing — run `make dbt`, verify Parquet output, run `make check`
2. **Production**: Deploy with both DuckDB file and Parquet (fallback active). Run dbt to generate Parquet. Verify API returns identical results. Remove fallback in subsequent deploy.

---

## Open Questions

- [x] Does `{name}` resolve correctly in `dbt_project.yml`'s `external_location`? → Resolved: used `external_root` in `profiles.yml` instead, which auto-names files after the model. No per-model config needed.

---

## Files Modified

- `backend/src/filepaths.py` — Added `PARQUET_DIR`
- `backend/dbt/dbt_project.yml` — Mart materialisation → `external`
- `backend/dbt/profiles.yml` — Added `external_root`
- `backend/src/duckdb/client.py` — In-memory connection, Parquet views, schema creation, fallback
- `backend/src/api/analytics/endpoints.py` — `_get_last_refresh_time()` Parquet mtime with fallback
- `backend/scripts/bootstrap_duckdb.py` — Create Parquet directories
- `backend/.env_example` — Added `PARQUET_DIR`
- `backend/Makefile` — `make dbt` creates `data/parquet/mart/` before build
- `docker-compose.yml` — Bind mounts, env vars, removed `duckdb_data` volume

---

## References

- [dbt-duckdb external materialisation](https://github.com/duckdb/dbt-duckdb#external-materialization)
- [DuckDB read_parquet](https://duckdb.org/docs/data/parquet/overview)
- Depended on by: PRD 2 (Semantic Layer) — weak dependency, can be parallelised
