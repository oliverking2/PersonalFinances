# Backend CLAUDE.md

Backend-specific guidance for Claude Code. See also root `CLAUDE.md` for project overview.

## Structure

```
backend/
├── src/
│   ├── api/            # FastAPI endpoints
│   ├── aws/            # S3, SSM clients
│   ├── orchestration/  # Dagster jobs & assets
│   ├── postgres/       # SQLAlchemy models & operations
│   ├── providers/      # External API clients (GoCardless)
│   └── utils/          # Shared utilities
├── testing/            # Tests (mirrors src/ structure)
├── alembic/            # Database migrations
├── .env                # Environment config (from .env_example)
└── pyproject.toml
```

## Commands

```bash
cd backend

# Validation (run before completing any change)
make check                    # Run all: lint, format, types, coverage

# Individual checks
make test                     # Unit tests only
make lint                     # Ruff linting
make format                   # Ruff formatting
make types                    # mypy type checking
make coverage                 # Tests with 80% threshold

# Development
poetry run pytest testing/path/to/test.py::test_name -v  # Single test
poetry run alembic upgrade head                          # Run migrations
poetry run alembic revision --autogenerate -m "desc"     # Create migration
poetry run uvicorn src.api.app:app --reload              # Start API server
poetry run dagster dev                                   # Dagster dev server
```

## Technology

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL, SQLAlchemy 2.0 |
| Orchestration | Dagster |
| Transforms | dbt |
| Storage | AWS S3 (Parquet) |
| Bank API | GoCardless |
| Testing | pytest, pytest-mock |
| Linting | Ruff, mypy |

## Key Patterns

- **Domain logic** lives in `postgres/` and `providers/`. API layer is thin.
- **Database operations** take `Session` as first param; caller manages transactions.
- **API endpoints** use Pydantic models for request/response, `Depends()` for injection.
- **dbt** follows source → staging → mart layer convention.

## File Placement

| Type | Location |
|------|----------|
| API endpoints | `src/api/<resource>/endpoints.py` |
| Pydantic models | `src/api/<resource>/models.py` |
| DB models | `src/postgres/<domain>/models.py` |
| DB operations | `src/postgres/<domain>/operations/<entity>.py` |
| External clients | `src/providers/<provider>/api/` |
| Tests | `testing/<module>/` (mirrors src) |
| Migrations | `alembic/versions/` |

## Coding Standards

- Python 3.12+, Poetry for dependencies
- Type hints everywhere, `X | None` not `Optional[X]`
- Ruff for linting/formatting, mypy for type checking
- 80% test coverage minimum
- Sphinx-style docstrings for public functions
- British English in comments and user-facing text

## See Also

Detailed patterns in `.claude/rules/`:
- `python.md` - Style, naming, functions, testing
- `api.md` - FastAPI endpoints, Pydantic models
- `database.md` - SQLAlchemy models, operations, migrations
- `infrastructure.md` - AWS, configuration, security
