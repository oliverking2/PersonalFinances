# Backend CLAUDE.md

Backend-specific guidance for Claude Code. See also root `CLAUDE.md` for project overview.

## Structure

```
backend/
├── src/
│   ├── api/            # FastAPI endpoints
│   ├── orchestration/  # Dagster jobs & assets
│   ├── postgres/       # SQLAlchemy models & operations
│   │   ├── auth/       # User authentication (users, refresh_tokens)
│   │   ├── common/     # Provider-agnostic models (connections, accounts, institutions)
│   │   ├── gocardless/ # GoCardless-specific raw data (requisitions, bank_accounts, balances)
│   │   └── core.py     # Base, engine, session utilities
│   ├── providers/      # External API clients (GoCardless)
│   └── utils/          # Shared utilities (config, logging, security)
├── testing/            # Tests (mirrors src/ structure)
├── alembic/            # Database migrations
├── dbt/                # dbt analytics (reads from PostgreSQL via DuckDB)
├── .env                # Environment config (from .env_example)
└── pyproject.toml
```

## Commands

```bash
cd backend

# Validation (run before completing any change)
make check                    # Run all: lint, format, types, sql-lint, coverage

# Individual checks
make test                     # Unit tests only
make lint                     # Ruff linting
make format                   # Ruff formatting
make types                    # mypy type checking
make sql                      # SQLFluff lint and auto-fix for dbt models
make sql-lint                 # SQLFluff lint only (no auto-fix)
make coverage                 # Tests with 80% threshold

# dbt commands
make dbt                      # Build dbt models (run + test)
make dbt-docs                 # Generate and serve dbt docs

# Development
poetry run pytest testing/path/to/test.py::test_name -v  # Single test
poetry run alembic upgrade head                          # Run migrations
poetry run alembic revision --autogenerate -m "desc"     # Create migration
poetry run uvicorn src.api.app:app --reload              # Start API server
poetry run dagster dev                                   # Dagster dev server
```

## Technology

| Component     | Technology                    |
|---------------|-------------------------------|
| Framework     | FastAPI                       |
| Database      | PostgreSQL, SQLAlchemy 2.0    |
| Orchestration | Dagster                       |
| Transforms    | dbt + DuckDB                  |
| Bank API      | GoCardless (env var secrets)  |
| Testing       | pytest, pytest-mock           |
| Linting       | Ruff, mypy, SQLFluff          |

## Key Patterns

- **Domain logic** lives in `postgres/` and `providers/`. API layer is thin.
- **Database operations** take `Session` as first param; caller manages transactions.
- **API endpoints** use Pydantic models for request/response, `Depends()` for injection.
- **dbt** follows source → staging → mart layer convention.

## Data Architecture

The database uses a two-layer approach for multi-provider support:

```
┌─────────────────────────────────────────────────────────────┐
│                    Standardised Tables                       │
│  connections    accounts    institutions                     │
│  (postgres/common/)                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │ sync/backfill
┌───────────────────────────▼─────────────────────────────────┐
│                    Raw Provider Tables                       │
│  gc_requisition_links    gc_bank_accounts    gc_balances    │
│  (postgres/gocardless/)                                      │
└─────────────────────────────────────────────────────────────┘
```

- **Standardised tables** (`postgres/common/`): Provider-agnostic, used by API endpoints
- **Raw tables** (`postgres/gocardless/`): Provider-specific, source of truth for Dagster
- **Enums** in `postgres/common/enums.py`: Provider, ConnectionStatus, AccountStatus with mapping helpers

## File Placement

| Type             | Location                                       |
|------------------|------------------------------------------------|
| API endpoints    | `src/api/<resource>/endpoints.py`              |
| Pydantic models  | `src/api/<resource>/models.py`                 |
| DB models        | `src/postgres/<domain>/models.py`              |
| DB operations    | `src/postgres/<domain>/operations/<entity>.py` |
| External clients | `src/providers/<provider>/api/`                |
| Tests            | `testing/<module>/` (mirrors src)              |
| Migrations       | `alembic/versions/`                            |

## Coding Standards

- Python 3.12+, Poetry for dependencies
- Type hints everywhere
- Ruff for linting/formatting, mypy for type checking, SQLFluff for SQL
- **80% test coverage minimum per file** - every file should aim for 80%+ coverage
- Sphinx-style docstrings for public functions
- British English in comments and user-facing text
- Enums defined once in `postgres/common/enums.py` (single source of truth)
- No backward compatibility required (single-user personal project)

## See Also

Detailed patterns in `.claude/rules/`:

- `python.md` - Style, naming, functions, testing
- `api.md` - FastAPI endpoints, Pydantic models
- `database.md` - SQLAlchemy models, operations, migrations
- `infrastructure.md` - AWS, configuration, security
