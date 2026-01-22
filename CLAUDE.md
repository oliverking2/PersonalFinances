# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Collaboration Style

- **Challenge assumptions** - Point out issues before they become problems
- **Present trade-offs** - When multiple paths exist, explain pros/cons
- **Be direct** - If something is a bad idea, say so and explain why
- **Teach** - Explain the "why", not just the "what"
- **Suggest packages** - Look for well-supported external packages before implementing from scratch

## Project Structure

```
PersonalFinances/
├── backend/                 # Python (FastAPI, Dagster, dbt)
│   ├── src/
│   │   ├── api/            # FastAPI endpoints
│   │   ├── aws/            # S3, SSM clients
│   │   ├── orchestration/  # Dagster jobs & assets
│   │   ├── postgres/       # SQLAlchemy models & operations
│   │   ├── providers/      # External API clients (GoCardless)
│   │   └── utils/          # Shared utilities
│   ├── testing/            # Tests (mirrors src/ structure)
│   ├── alembic/            # Database migrations
│   └── pyproject.toml
├── frontend/                # Nuxt 4 (Vue 3 + Nuxt UI)
│   ├── app/
│   │   ├── composables/    # API client, shared logic
│   │   ├── components/     # Vue components
│   │   └── pages/          # Route pages
│   └── nuxt.config.ts
├── dbt/                     # Data transformations
│   └── models/             # source → staging → mart
└── docker-compose.yml
```

## Build Commands

```bash
# Backend (from backend/)
make check                    # Run all validation (lint, format, types, coverage)
make test                     # Unit tests only
make lint                     # Ruff linting
make format                   # Ruff formatting
make types                    # mypy type checking
poetry run pytest testing/path/to/test.py::test_name -v  # Single test
poetry run alembic upgrade head                          # Run migrations
poetry run uvicorn src.api.app:app --reload              # Start API server
poetry run dagster dev                                   # Dagster dev server

# Frontend (from frontend/)
make dev                      # Development server
make build                    # Production build
make lint                     # ESLint
make typecheck                # Nuxt type checking
make check                    # Run lint and typecheck

# Pre-commit (from project root)
pre-commit install            # Install git hooks
pre-commit run --all-files    # Run all hooks manually

# dbt (from dbt/)
dbt run --profiles-dir . --profile duckdb_local
dbt test --profiles-dir . --profile duckdb_local

# Docker
docker-compose up -d postgres  # Start database
docker-compose up -d           # Start all services
```

## Pre-commit Hooks

Pre-commit runs ruff (lint + format) on backend code automatically on commit.
MyPy is excluded from pre-commit (needs full project environment) - run via `make check`.

```bash
# Install hooks (one-time setup)
pre-commit install

# Run manually
pre-commit run --all-files
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy |
| Frontend | Vue 3, Nuxt 4, Nuxt UI, TypeScript |
| Database | PostgreSQL, DuckDB |
| Storage | AWS S3 (Parquet) |
| Transforms | dbt |
| Orchestration | Dagster |
| Bank API | GoCardless |

## Key Patterns

- **Backend**: Domain logic in `postgres/`, `providers/`. API layer is thin.
- **Database**: Operations take `Session` as first param, caller manages transactions.
- **API**: Pydantic models for request/response, FastAPI dependencies for injection.
- **Frontend**: Composables for API calls, pages for routes.
- **dbt**: Source → staging → mart layer convention.

## Coding Standards

- Type hints everywhere, `X | None` not `Optional[X]`
- 80% test coverage minimum
- All changes pass `make check` before complete
- Docstrings for public functions (Sphinx style)
- British English in comments and user-facing text

## Configuration

Environment variables in `.env` (copy from `.env_example`):
- `ENVIRONMENT` - local/prod
- `AWS_*` - S3/SSM credentials
- `POSTGRES_*` - Database connection
- `GC_CALLBACK_URL` - GoCardless OAuth callback

## File Placement

- Backend code: `backend/src/<module>/`
- Backend tests: `backend/testing/<module>/` (mirrors src)
- Frontend pages: `frontend/app/pages/`
- Frontend components: `frontend/app/components/`
- dbt models: `dbt/models/<layer>/`
- PRDs: `prds/` (use `_template.md`)

## Validation

All changes must pass before complete:
```bash
cd backend && make check
```

Update `README.md` and `ROADMAP.md` when completing features.
