# Personal Finances

A self-hosted personal finance aggregation and analytics platform. Connect bank accounts via open banking, track transactions, and gain insights into spending patterns.

Key highlights:

- **Open banking integration** - Connect UK bank accounts via GoCardless Bank Account Data API with OAuth flow and automatic token refresh
- **Data pipeline architecture** - Dagster orchestration with incremental extraction, S3 storage (Parquet), and dbt transformations
- **Layered backend** - FastAPI REST layer with thin endpoints, domain logic in dedicated modules, SQLAlchemy 2.0 for persistence
- **Modern frontend** - Nuxt 4 with Vue 3 Composition API, Nuxt UI components, and TypeScript
- **Self-hosted** - Full control over financial data with Docker Compose deployment

## Project Goal

This project is a personal finance platform designed to aggregate bank account data and provide insights into spending patterns through a unified dashboard.

The primary use cases include:

- Connecting multiple UK bank accounts via GoCardless open banking
- Viewing consolidated account balances and transactions
- Analysing spending patterns with dbt-powered transformations
- Storing transaction history in S3 (Parquet) for long-term analytics

The system maintains incremental extraction state, only fetching new transactions since the last sync.

## Architecture Overview

This section provides a high-level overview of how the system works, intended as context for designing new features and PRDs.

### System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Nuxt 4 Application                                                         │
│  (Vue 3 + Nuxt UI + TypeScript)                                             │
│                                                                             │
│  • Pages: Dashboard, Connections, Accounts, Transactions                    │
│  • Composables: useApi (HTTP client wrapper)                                │
│  • Layouts: Dashboard layout with navigation                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI REST API                                                           │
│                                                                             │
│  /connections      │  /accounts           │  /transactions                  │
│  • List/create     │  • List by conn      │  • List with filters            │
│  • OAuth callback  │  • Get balances      │  • Date range queries           │
│  • Delete          │                      │                                 │
│                                                                             │
│  Thin layer: validation, error handling, delegates to domain modules        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOMAIN SERVICES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  postgres/gocardless/     │  providers/gocardless/   │  aws/                │
│  (Database operations)    │  (API client)            │  (Cloud services)    │
│                           │                          │                      │
│  • Requisitions CRUD      │  • Institution lookup    │  • S3 read/write     │
│  • Bank accounts CRUD     │  • Agreement creation    │  • SSM parameters    │
│  • Agreements CRUD        │  • Requisition flow      │                      │
│                           │  • Transaction fetch     │                      │
│                           │  • Balance fetch         │                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Dagster                                                                    │
│                                                                             │
│  Assets:                         │  Schedules:                              │
│  • extract_transactions          │  • Daily transaction extraction          │
│  • extract_balances              │  • Daily balance snapshots               │
│                                  │                                          │
│  Resources:                      │  Background Jobs:                        │
│  • PostgresResource              │  • Agreement refresh (before expiry)     │
│  • S3Resource                    │  • Token management                      │
│  • GoCardlessResource            │                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA TRANSFORMATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  dbt (DuckDB)                                                               │
│                                                                             │
│  1_source/           │  2_staging/           │  3_mart/                     │
│  • Raw S3 sources    │  • Cleaned data       │  • Analytics aggregations    │
│  • Schema definitions│  • Type casting       │  • Spending summaries        │
│                      │  • Deduplication      │  • Category breakdowns       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  GoCardless API          │  AWS S3                │  PostgreSQL             │
│  (Bank Account Data)     │  (Parquet storage)     │  (Metadata & state)     │
│                          │                        │                         │
│  • Institutions list     │  • Transaction files   │  • Requisitions         │
│  • Account access        │  • Balance snapshots   │  • Bank accounts        │
│  • Transactions          │  • Extraction logs     │  • Agreements           │
│  • Balances              │                        │  • Extract dates        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Patterns

#### 1. Bank Connection Flow (User-initiated)

```
Frontend (Connections page)
    → POST /connections (institution_id)
    → GoCardless API (create agreement + requisition)
    → Redirect to bank OAuth
    → Bank authorises
    → Callback to /connections/callback
    → Store requisition + accounts in PostgreSQL
    → Redirect to frontend
```

#### 2. Transaction Extraction (Scheduled)

```
Dagster Schedule (daily)
    → For each active bank account:
        → Get last extract_date from PostgreSQL
        → Fetch transactions since extract_date from GoCardless
        → Write to S3 as Parquet (partitioned by date)
        → Update extract_date in PostgreSQL
```

#### 3. Analytics Query (User-initiated)

```
Frontend (Transactions page)
    → GET /transactions?date_from=...&date_to=...
    → dbt query against DuckDB (reads from S3)
    → Return aggregated/filtered results
```

### Key Design Decisions

| Decision                | Rationale                                                             |
|-------------------------|-----------------------------------------------------------------------|
| Thin API layer          | Endpoints handle HTTP concerns only; business logic in domain modules |
| Session-per-request     | Database operations receive Session, caller manages transactions      |
| S3 for transactions     | Parquet enables efficient columnar queries, separates hot/cold data   |
| PostgreSQL for metadata | Relational integrity for connections, accounts, extraction state      |
| Incremental extraction  | extract_date watermark prevents re-fetching old transactions          |
| dbt over raw SQL        | Version-controlled transformations, testable, self-documenting        |
| Dagster over Celery     | Better observability, native scheduling, asset-based mental model     |

### Module Boundaries

```
backend/src/
├── api/                 # FastAPI endpoints (thin HTTP layer)
│   ├── accounts/        # Account listing, balances
│   ├── connections/     # OAuth flow, requisition management
│   └── transactions/    # Transaction queries
├── aws/                 # AWS service clients
│   ├── s3.py            # S3 read/write operations
│   └── ssm_parameters.py # Parameter Store access
├── orchestration/       # Dagster definitions
│   ├── gocardless/      # Extraction assets & schedules
│   └── dbt/             # dbt asset definitions
├── postgres/            # Database layer
│   └── gocardless/      # Models and CRUD operations
├── providers/           # External API clients
│   └── gocardless/      # GoCardless API wrapper
└── utils/               # Logging, shared utilities

frontend/app/
├── components/          # Reusable Vue components
├── composables/         # useApi, shared logic
├── layouts/             # Page layouts
└── pages/               # File-based routes
```

## Technology Stack

| Layer            | Technology                                       |
|------------------|--------------------------------------------------|
| Frontend         | Vue 3, Nuxt 4, Nuxt UI, TypeScript, Tailwind CSS |
| Backend          | Python 3.12+, FastAPI, SQLAlchemy 2.0            |
| Database         | PostgreSQL (metadata), DuckDB (analytics)        |
| Storage          | AWS S3 (Parquet files)                           |
| Orchestration    | Dagster                                          |
| Transforms       | dbt                                              |
| Bank API         | GoCardless Bank Account Data                     |
| Containerisation | Docker Compose                                   |

## Project Structure

```
PersonalFinances/
├── backend/                 # Python backend (see backend/CLAUDE.md)
│   ├── src/                 # Application code
│   ├── testing/             # Tests (mirrors src/)
│   ├── alembic/             # Database migrations
│   └── pyproject.toml
├── frontend/                # Nuxt 4 frontend (see frontend/CLAUDE.md)
│   ├── app/                 # Application code
│   └── nuxt.config.ts
├── dbt/                     # Data transformations
│   └── models/              # source → staging → mart
├── prds/                    # Product requirement documents
└── docker-compose.yml
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
cp backend/.env_example backend/.env
# Edit backend/.env with your credentials

# Install backend dependencies
cd backend && poetry install --with dev && cd ..

# Install frontend dependencies
cd frontend && npm install && cd ..

# Install pre-commit hooks
pre-commit install
```

### Running Locally

```bash
# Terminal 1: Start database
docker-compose up -d postgres

# Terminal 2: Run migrations and start backend
cd backend
poetry run alembic upgrade head
poetry run uvicorn src.api.app:app --reload --port 8000

# Terminal 3: Start frontend
cd frontend
npm run dev
```

### Access Points

| Service     | URL                          |
|-------------|------------------------------|
| Frontend    | <http://localhost:3001>      |
| Backend API | <http://localhost:8000>      |
| API Docs    | <http://localhost:8000/docs> |
| Dagster     | <http://localhost:3000>      |

## Configuration

Edit `backend/.env` (copy from `backend/.env_example`):

```bash
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

## PRD Context

When writing PRDs for this project, consider:

- **Where does the request originate?** (Frontend, Dagster schedule, API)
- **What layer handles it?** (API → Domain → External service)
- **What data flows where?** (PostgreSQL for state, S3 for bulk data)
- **Is extraction incremental?** (Use watermarks/extract_date pattern)
- **Does it affect the pipeline?** (Consider Dagster asset dependencies)

Existing PRDs are in `prds/` and follow a consistent structure.

## Development

See `CLAUDE.md` for development commands and patterns:

- `backend/CLAUDE.md` - Python/FastAPI patterns
- `frontend/CLAUDE.md` - Vue/Nuxt patterns

```bash
# Validation
cd backend && make check    # Backend (lint, types, tests)
cd frontend && make check   # Frontend (lint, typecheck)
```

## Roadmap

See `ROADMAP.md` for planned features.

## Licence

Private - not for redistribution.
