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
├── backend/                 # Python (FastAPI, Dagster) - see backend/CLAUDE.md
│   ├── src/                 # Application code
│   ├── testing/             # Tests (mirrors src/)
│   ├── alembic/             # Database migrations
│   ├── dbt/                 # Data transformations (source → staging → mart)
│   └── CLAUDE.md            # Backend-specific guidance
├── frontend/                # Nuxt 4 (Vue 3) - see frontend/CLAUDE.md
│   ├── app/                 # Application code
│   └── CLAUDE.md            # Frontend-specific guidance
├── prds/                    # Product requirement documents
└── docker-compose.yml
```

## Technology Stack

| Layer      | Technology                                 |
|------------|--------------------------------------------|
| Backend    | Python 3.12+, FastAPI, SQLAlchemy, Dagster |
| Frontend   | Vue 3, Nuxt 4, Tailwind CSS, TypeScript    |
| Database   | PostgreSQL                                 |
| Analytics  | DuckDB (reads from PostgreSQL via dbt)     |
| Transforms | dbt                                        |
| Bank API   | GoCardless                                 |

## Shared Commands

```bash
# Development (from project root)
make up-db        # Start Postgres and run migrations
make up-backend   # Start API server (hot reload)
make up-frontend  # Start frontend (hot reload)
make up-dagster   # Start Dagster UI
make check        # Run all validation (backend + frontend)

# Pre-commit (from project root)
pre-commit install             # Install git hooks (one-time)
pre-commit run --all-files     # Run all hooks manually

# dbt (from backend/dbt/)
dbt run --profiles-dir . --profile duckdb_local
dbt test --profiles-dir . --profile duckdb_local
```

## Configuration

Backend environment variables in `backend/.env` (copy from `backend/.env_example`):

- `ENVIRONMENT` - local/prod
- `POSTGRES_*` - Database connection (also used by dbt/DuckDB)
- `GC_SECRET_ID`, `GC_SECRET_KEY` - GoCardless API credentials
- `GC_CALLBACK_URL` - GoCardless OAuth callback
- `CORS_ORIGINS` - Additional allowed origins (comma-separated) for production/tunnel domains

Frontend environment variables in `frontend/.env` (copy from `frontend/.env.example`):

- `NUXT_PUBLIC_API_URL` - Backend API URL (browser calls this directly)

## Deployment

The app runs on a home server exposed via **Cloudflare Tunnel** (cloudflared).

- **Frontend**: `https://finances.oliverking.me.uk`
- **Backend API**: `https://finances-api.oliverking.me.uk`

For tunnel deployments:

1. Set `CORS_ORIGINS=https://finances.oliverking.me.uk` in backend `.env`
2. Set `NUXT_PUBLIC_API_URL=https://finances-api.oliverking.me.uk` in frontend `.env`
3. Both tunnels must be configured in Cloudflare dashboard

## PRD Naming Convention

PRDs use the format: `YYYYMMDD-{scope}-feature-name.md`

| Scope       | Description                    |
|-------------|--------------------------------|
| `backend`   | Python/FastAPI/Dagster changes |
| `frontend`  | Nuxt/Vue changes               |
| `fullstack` | Changes spanning both          |
| `infra`     | Docker, CI/CD, deployment      |
| `data`      | dbt models, data pipeline      |

Once a PRD is fully implemented, move it to `prds/complete/`.

## Validation

All changes must pass before complete:

```bash
cd backend && make check    # Backend validation
cd frontend && make check   # Frontend validation
```

## After Completing Work

1. **Run validation** in affected directories
2. **Update documentation**:
   - `ROADMAP.md` - Mark completed items, add new items discussed
   - `README.md` - If user-facing behaviour changed
   - `CLAUDE.md` files - If new patterns or structures established
3. **Move completed PRDs** to `prds/complete/`

## Analytics Architecture

**All analytics logic belongs in dbt, not frontend.**

- **dbt models** handle: aggregations, calculations, derived metrics, business logic
- **Frontend** handles: formatting (currency, dates), display, user interaction
- **API** handles: querying dbt marts with user-specified filters (date range, account, etc.)

The pattern is:

1. dbt produces pre-aggregated mart tables (e.g., `fct_monthly_trends`, `fct_daily_spending_by_tag`)
2. Frontend queries these via the Analytics API with date/filter parameters
3. Frontend displays the results with formatting only

If the frontend needs to do aggregation beyond simple display formatting, consider whether that logic should be a new dbt model instead.

## See Also

- `backend/CLAUDE.md` - Python/FastAPI patterns and commands
- `frontend/CLAUDE.md` - Learning guide (teaching mode)
- `.claude/rules/` - Shared coding discipline
