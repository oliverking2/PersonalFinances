# Personal Finances

A self-hosted personal finance aggregation and analytics platform. Connect bank accounts via open banking, track transactions, and gain insights into spending patterns.

## Features

- **Open Banking Integration** - Connect UK bank accounts via GoCardless
- **Unified Dashboard** - Vue 3 + Nuxt 4 frontend with Nuxt UI
- **Data Pipeline** - Dagster orchestration with dbt transformations
- **REST API** - FastAPI backend for data access
- **Self-Hosted** - Full control over your financial data

## Project Structure

```
PersonalFinances/
├── backend/                 # Python backend
│   ├── src/
│   │   ├── api/            # FastAPI endpoints
│   │   ├── aws/            # S3, SSM clients
│   │   ├── orchestration/  # Dagster jobs & assets
│   │   ├── postgres/       # SQLAlchemy models & operations
│   │   ├── providers/      # External API clients (GoCardless)
│   │   └── utils/          # Shared utilities
│   ├── testing/            # Test suite
│   ├── alembic/            # Database migrations
│   ├── pyproject.toml
│   └── Makefile
├── frontend/                # Nuxt 4 frontend
│   ├── app/
│   │   ├── composables/    # API client, shared logic
│   │   ├── components/     # Vue components
│   │   └── pages/          # Route pages
│   ├── nuxt.config.ts
│   └── package.json
├── dbt/                     # Data transformations
│   ├── models/
│   │   ├── 1_source/       # Raw data sources
│   │   ├── 2_staging/      # Cleaned data
│   │   └── 3_mart/         # Analytics aggregations
│   └── profiles.yml
├── setup/dagster/           # Dagster Docker config
├── docker-compose.yml
└── .env
```

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry
- Node.js 22+
- Docker and Docker Compose
- AWS account (S3 storage)
- GoCardless account (bank connections)

### Installation

```bash
# Clone and enter directory
git clone <repository-url>
cd PersonalFinances

# Copy environment template
cp .env_example .env
# Edit .env with your credentials

# Install backend dependencies
cd backend
poetry install --with dev
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..

# Install pre-commit hooks
pre-commit install
```

### Running Locally

**Option 1: Individual services**

```bash
# Terminal 1: Start database
docker-compose up -d postgres

# Terminal 2: Run database migrations and start backend
cd backend
poetry run alembic upgrade head
poetry run uvicorn src.api.app:app --reload --port 8000

# Terminal 3: Start frontend
cd frontend
npm run dev
```

**Option 2: Docker Compose**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Dagster | http://localhost:3000 |
| PostgreSQL | localhost:5432 |

## Development

### Backend Commands

```bash
cd backend

# Run all validation
make check

# Individual commands
make lint      # Ruff linting
make format    # Ruff formatting
make types     # mypy type checking
make test      # Unit tests
make coverage  # Tests with 80% coverage threshold

# Single test
poetry run pytest testing/path/to/test_file.py::test_name -v

# Database migrations
poetry run alembic upgrade head
poetry run alembic revision --autogenerate -m "description"

# Dagster dev server
poetry run dagster dev
```

### Frontend Commands

```bash
cd frontend

# Using Makefile
make dev        # Development server
make build      # Build for production
make preview    # Preview production build
make lint       # ESLint
make typecheck  # Nuxt type checking
make check      # Run lint and typecheck
make clean      # Remove build artifacts

# Or using npm directly
npm run dev
npm run build
npm run lint
```

### dbt Commands

```bash
cd dbt
dbt run --profiles-dir . --profile duckdb_local
dbt test --profiles-dir . --profile duckdb_local
```

### Pre-commit Hooks

Pre-commit runs ruff (linting and formatting) on backend code automatically on commit.
MyPy type checking is excluded from pre-commit and runs via `make check` instead.

```bash
# Install hooks (one-time setup, from project root)
pre-commit install

# Run all hooks manually
pre-commit run --all-files
```

## Configuration

Edit `.env` in the project root:

```bash
# Environment
ENVIRONMENT=local

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=eu-west-2
S3_BUCKET_NAME=your-bucket

# PostgreSQL
POSTGRES_HOSTNAME=localhost
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=postgres

# GoCardless
GC_CALLBACK_URL=http://localhost:3001/connections/callback
```

## PyCharm Setup

1. Open project root (`PersonalFinances/`)
2. **Settings → Project → Python Interpreter** → Select `backend/.venv`
3. **Right-click `backend/src`** → Mark Directory as → Sources Root
4. **Right-click `backend/testing`** → Mark Directory as → Test Sources Root
5. Frontend Node.js auto-detects from `frontend/package.json`

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   GoCardless    │────▶│     Dagster     │────▶│   PostgreSQL    │
│  (Open Banking) │     │ (Orchestration) │     │    + S3         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Nuxt Frontend  │◀───▶│    FastAPI      │◀───▶│   dbt/DuckDB    │
│   (Vue 3 + UI)  │     │   (REST API)    │     │ (Transforms)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Roadmap

See `ROADMAP.md` for planned features.

## License

Private - not for redistribution.
