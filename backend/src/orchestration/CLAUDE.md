# Orchestration (Dagster)

Dagster-specific guidance for the orchestration module.

## Structure

```
src/orchestration/
├── definitions.py           # Root Definitions combining all providers
├── resources.py             # Shared resources (PostgresDatabase, etc.)
└── gocardless/
    ├── definitions.py       # GoCardless-specific Definitions
    ├── extraction/
    │   └── assets.py        # Extract from GoCardless API to raw tables
    └── sync/
        └── assets.py        # Sync from raw tables to unified tables
```

## Key Patterns

### Config Classes

Dagster `Config` classes **cannot** use `str | None` union syntax. Use `Optional[str]` instead:

```python
from typing import Optional
from dagster import Config

# Correct - Dagster can parse this
class MyConfig(Config):
    connection_id: Optional[str] = None

# Wrong - Dagster fails with "Unable to resolve config type"
class MyConfig(Config):
    connection_id: str | None = None
```

This also means you **cannot** use `from __future__ import annotations` in files with Dagster Config classes, as it causes annotations to be stored as strings rather than evaluated at runtime.

The `UP045` ruff rule is disabled for `src/orchestration/` in `pyproject.toml` to allow `Optional[]` syntax.

### Assets

- Assets are functions decorated with `@asset`
- Use `AssetKey` for explicit naming: `AssetKey(["source", "gocardless", "extract", "transactions"])`
- Group related assets with `group_name="gocardless"`
- Declare dependencies with `deps=[AssetKey(...)]`

### Resources

- Shared resources defined in `resources.py`
- Accessed via `context.resources.<resource_name>`
- Declare requirements with `required_resource_keys={"postgres_database", "gocardless_api"}`

### Connection-Scoped Jobs

To run a job for a specific connection, pass config:

```python
run_config = {
    "ops": {
        "*": {
            "config": {
                "connection_id": "uuid-here"
            }
        }
    }
}
trigger_job("gocardless_sync_job", run_config)
```

Assets check `config.connection_id` and filter to that connection's data.

## Commands

```bash
# Start Dagster dev server
poetry run dagster dev

# Verify definitions load
poetry run python -c "from src.orchestration.definitions import defs; print('OK')"
```

## Triggering Jobs from API

The Dagster client in `src/providers/dagster/client.py` uses GraphQL to:

- `trigger_job(job_name, run_config)` - Returns run ID or None if unavailable
- `get_run_status(run_id)` - Returns status string (QUEUED, STARTED, SUCCESS, FAILURE, etc.)

Jobs are triggered asynchronously. The API creates a `Job` record to track status, polling Dagster when the frontend requests job status.

### Location Name

The Dagster location name depends on how `workspace.yaml` loads the definitions. With `python_file` loading, it's typically `<filename>:<attribute>` (e.g., `definitions.py:defs`).

To find the actual location name, query Dagster:

```bash
curl -s http://localhost:3001/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ repositoriesOrError { ... on RepositoryConnection { nodes { name location { name } } } } }"}' | jq
```
