# Backend CLAUDE.md

Backend-specific guidance for Claude Code. See also root `CLAUDE.md` for project overview.

## Structure

```
backend/
├── src/
│   ├── api/            # FastAPI endpoints (see src/api/CLAUDE.md)
│   │   ├── auth/       # Authentication (login, register, refresh)
│   │   ├── accounts/   # Bank accounts and balances
│   │   ├── analytics/  # Spending analytics (queries dbt marts)
│   │   ├── budgets/    # Tag-based budgets
│   │   ├── connections/# Bank connections (OAuth flow)
│   │   ├── goals/      # Savings goals
│   │   ├── institutions/ # Bank institution lookup
│   │   ├── jobs/       # Background job status
│   │   ├── manual_assets/ # Manual assets and liabilities
│   │   ├── milestones/ # Financial milestones
│   │   ├── notifications/ # In-app notification system
│   │   ├── planned_transactions/ # Future planned transactions
│   │   ├── recurring/  # Recurring patterns (opt-in model)
│   │   ├── tag_rules/  # Automatic tag application rules
│   │   ├── tags/       # Tag CRUD
│   │   ├── trading212/ # Trading212 investment integration
│   │   ├── transactions/ # Transaction queries
│   │   └── user/       # User settings and Telegram linking
│   ├── orchestration/  # Dagster jobs & assets (see orchestration/CLAUDE.md)
│   │   ├── dbt/        # Analytics transforms
│   │   ├── exports/    # Data export jobs (CSV/Parquet to S3)
│   │   ├── gocardless/ # Bank sync (extraction + sync)
│   │   ├── maintenance/ # Database cleanup and maintenance
│   │   ├── recurring_patterns/ # Pattern detection and matching
│   │   ├── trading212/ # Investment sync from Trading212
│   │   └── unified/    # Cross-provider unified sync
│   ├── postgres/       # SQLAlchemy models & operations (see postgres/CLAUDE.md)
│   │   ├── auth/       # Users, refresh tokens
│   │   ├── common/     # Provider-agnostic models (connections, accounts, recurring)
│   │   │   └── operations/  # CRUD operations by entity
│   │   ├── gocardless/ # GoCardless raw data (requisitions, bank_accounts)
│   │   ├── telegram/   # Telegram bot state (polling cursor)
│   │   ├── trading212/ # Trading212 raw data (holdings, transactions)
│   │   └── core.py     # Base, engine, session utilities
│   ├── duckdb/         # DuckDB client for analytics queries
│   ├── providers/      # External API clients (GoCardless, Dagster)
│   └── utils/          # Shared utilities (config, logging, security)
├── testing/            # Tests (see testing/CLAUDE.md)
├── alembic/            # Database migrations
├── dbt/                # dbt analytics (see dbt/CLAUDE.md)
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
│  connections    accounts    transactions    recurring_patterns│
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
- **Enums** in `postgres/common/enums.py`: Provider, AccountType, ConnectionStatus, AccountStatus, AccountCategory, JobType/Status, RecurringFrequency/Status/Source/Direction, BudgetPeriod, GoalStatus/TrackingMode, TransactionStatus, NotificationType, ManualAssetType
- **Recurring patterns**: Use opt-in model with status workflow (pending → active ⟷ paused / cancelled)

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

Module-specific guides:

- `src/api/CLAUDE.md` - API docstring conventions, error responses
- `src/orchestration/CLAUDE.md` - Dagster patterns, Config classes
- `src/postgres/CLAUDE.md` - Database models, operations, enums
- `dbt/CLAUDE.md` - dbt layer conventions, DuckDB integration
- `testing/CLAUDE.md` - Test fixtures, patterns, coverage

Detailed patterns in `.claude/rules/`:

- `python.md` - Style, naming, functions, testing
- `api.md` - FastAPI endpoints, Pydantic models
- `database.md` - SQLAlchemy models, operations, migrations
- `infrastructure.md` - Configuration, security
