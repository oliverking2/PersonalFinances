# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## How Claude Should Help

Beyond writing code, Claude should act as a thoughtful collaborator:

- **Challenge assumptions**: Point out potential issues before they become problems. Ask "have you considered X?" when there are better approaches.
- **Present options with trade-offs**: When multiple paths exist, lay them out with clear pros/cons rather than picking one silently.
- **Be direct about bad ideas**: If something is a bad idea, say so and explain why. Don't sugarcoat or go along with poor decisions to be agreeable.
- **Be realistic about complexity**: Don't oversell or undersell difficulty. Be honest about what's straightforward vs what will be tricky.
- **Explain the "why"**: Don't just implement - explain why we're choosing one approach over another.
- **Teach, don't just deliver**: Help understand what code is doing so it can be modified later. The goal is knowledge transfer, not just working code.
- **Suggest external packages**: Before implementing complex functionality from scratch, look for well-supported external packages that could simplify the codebase.

## Build Commands

```bash
# Install dependencies
make install

# Run all validation (lint, format, types, coverage)
make check

# Individual validation commands
make lint      # Ruff linting with fixes
make format    # Ruff formatter
make types     # mypy type checking
make test      # Unit tests only
make coverage  # Tests with coverage (80% threshold)

# Run single test file
poetry run pytest testing/path/to/test_file.py -v

# Run single test function
poetry run pytest testing/path/to/test_file.py::test_function_name -v

# Database migrations
poetry run alembic upgrade head
poetry run alembic revision --autogenerate -m "description"

# Start services locally
docker-compose up -d                         # All services
poetry run dagster dev                       # Dagster dev server
poetry run uvicorn src.api.app:app --reload  # FastAPI (when implemented)

# dbt commands
cd dbt && dbt run --profiles-dir . --profile duckdb_local
cd dbt && dbt test --profiles-dir . --profile duckdb_local

# Clean build artefacts
make clean
```

## Architecture

### Overview

Personal Finances is a self-hosted application for aggregating and visualising personal financial data. It connects to bank accounts via open banking (GoCardless), extracts transaction data, transforms it using dbt, and presents it through a web interface.

### Data Flow

1. **Bank Connections**: GoCardless API connects to banks via open banking
2. **Data Extraction**: Dagster orchestrates scheduled extraction of transactions and balances
3. **Raw Storage**: Transaction data stored in PostgreSQL and S3 (Parquet)
4. **Transformation**: dbt transforms raw data in DuckDB for analytics
5. **API Layer**: FastAPI exposes data to frontend (planned)
6. **Frontend**: Vue + Nuxt + Tailwind displays dashboards (planned, currently Streamlit)

### System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  GoCardless (Open Banking)  │  Manual Import (CSV)    │  Future: Vanguard   │
│  - Bank accounts            │  - Historical data      │  - Trading212       │
│  - Transactions             │                         │                     │
│  - Balances                 │                         │                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Dagster                                                                    │
│  - Scheduled extraction jobs                                                │
│  - dbt asset materialisation                                                │
│  - Background jobs (link expiry handling)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL               │  S3 (Parquet)           │  DuckDB               │
│  - Bank account metadata  │  - Raw transactions     │  - Analytics queries  │
│  - GoCardless state       │  - Historical data      │  - dbt transformations│
│  - Dagster storage        │                         │                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TRANSFORMATION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  dbt + DuckDB                                                               │
│  - Source layer: raw data ingestion                                         │
│  - Staging layer: cleaned and standardised                                  │
│  - Mart layer: analytics-ready aggregations                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PRESENTATION LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI (Backend)          │  Vue + Nuxt (Frontend)  │  Telegram (Alerts)  │
│  - REST endpoints           │  - Dashboard views      │  - Notifications    │
│  - Data queries             │  - Account management   │  - AI interactions  │
│  - Auth                     │  - Tailwind styling     │  (future)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module            | Purpose                                          |
|-------------------|--------------------------------------------------|
| `src/aws/`        | AWS clients (S3 for storage, SSM for parameters) |
| `src/dagster/`    | Dagster jobs, assets, schedules, and resources   |
| `src/gocardless/` | GoCardless API client for bank connections       |
| `src/postgres/`   | SQLAlchemy models and database operations        |
| `src/streamlit/`  | Current UI (to be replaced with Vue + Nuxt)      |
| `src/utils/`      | Shared utilities (logging, definitions)          |
| `dbt/`            | dbt project for data transformations             |

### Key Patterns

- **Domain logic in domain modules**: `src/gocardless/`, `src/postgres/` contain all business logic
- **Dagster for orchestration**: All scheduled jobs and data pipelines run through Dagster
- **dbt for transformations**: SQL transformations in `dbt/models/` with source/staging/mart layers
- **Pydantic models for boundaries**: Used for API schemas and configuration
- **SQLAlchemy models for persistence**: ORM in `src/postgres/*/models.py`

### dbt Model Layers

```
dbt/models/
├── 1_source/      # Raw data sources (external tables)
├── 2_staging/     # Cleaned and standardised data
└── 3_mart/        # Analytics-ready aggregations
```

## Project Structure

- Source code lives under `src/`. Place new code in the correct existing package/module.
- Tests live under `testing/` and mirror `src/` structure.
- dbt models live under `dbt/models/`.
- PRDs for new features live in `prds/`. Use `prds/_template.md` as a starting point.
- Do not create new top-level folders unless explicitly asked.
- Review `ROADMAP.md` before starting work and update it when completing features.
- Review existing PRDs in `prds/` before implementing new features.

## Technology Stack

| Layer            | Technology                      |
|------------------|---------------------------------|
| Language         | Python 3.12+                    |
| API Framework    | FastAPI                         |
| Frontend         | Vue + Nuxt + Tailwind (planned) |
| Database         | PostgreSQL + DuckDB             |
| Object Storage   | AWS S3 (Parquet)                |
| Transformations  | dbt                             |
| Orchestration    | Dagster                         |
| Bank Connections | GoCardless (Open Banking)       |
| Containerisation | Docker Compose                  |
| Future: AI       | AWS Bedrock (Claude)            |
| Future: Alerts   | Telegram Bot API                |

## Coding Standards

### Python Style
- Use type hints for all function signatures
- Follow PEP 8 naming conventions
- Use `X | None` syntax instead of `Optional[X]`
- Docstrings for public functions and classes (Google style)

### Code Quality
- All changes must pass `ruff check` and `ruff format --check`
- All changes must pass `mypy` with no errors
- All changes must pass tests with at least 80% coverage

### Database
- SQLAlchemy models in `src/postgres/*/models.py`
- Database operations in dedicated `operations/` subdirectories
- Use Alembic for all schema migrations

### dbt
- Follow the source/staging/mart layer convention
- All models should have schema.yml definitions
- Use DuckDB for local development

## Configuration

Environment variables are defined in `.env` (copy from `.env_example`):

| Variable                  | Purpose                           |
|---------------------------|-----------------------------------|
| `ENVIRONMENT`             | Environment name (local/prod)     |
| `AWS_ACCESS_KEY_ID`       | AWS credentials for S3/SSM        |
| `AWS_SECRET_ACCESS_KEY`   | AWS credentials                   |
| `AWS_REGION`              | AWS region (default: eu-west-2)   |
| `S3_BUCKET_NAME`          | S3 bucket for data storage        |
| `POSTGRES_HOSTNAME`       | PostgreSQL host                   |
| `POSTGRES_USERNAME`       | PostgreSQL user                   |
| `POSTGRES_PASSWORD`       | PostgreSQL password               |
| `POSTGRES_DATABASE`       | PostgreSQL database name          |
| `GC_CALLBACK_URL`         | GoCardless OAuth callback URL     |

## Validation Requirements

All changes must pass before considering work complete:

```bash
make check  # Runs lint, format, types, coverage
```

- Update `README.md` to reflect new or modified behaviour
- Update `ROADMAP.md` to reflect completed features
