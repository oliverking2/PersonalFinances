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
│   ├── dbt/                 # Data transformations (source → staging → mart)
│   └── pyproject.toml
├── frontend/                # Nuxt 4 frontend (see frontend/CLAUDE.md)
│   ├── app/                 # Application code
│   └── nuxt.config.ts
├── docker/                  # Docker configuration
│   └── postgres/            # Postgres init scripts
├── docs/                    # Shared documentation
│   └── api/                 # API contracts for frontend/backend
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

# First-time setup (creates .env files, installs dependencies)
make setup

# Edit credentials
# - .env.compose: PostgreSQL credentials for Docker
# - backend/.env: Backend runtime config (must match .env.compose for database)
```

### Running

```bash
# Start everything (postgres, migrations, backend, frontend, dagster)
make up

# Stop everything
make down

# Reset (destroy all data and start fresh)
make reset

# View logs
make logs
```

### Development Mode

For local development with hot-reloading, run services individually:

```bash
# Terminal 1: Start database only
make up-db

# Terminal 2: Run backend with hot-reload
make up-backend

# Terminal 3: Run frontend with hot-reload
make up-frontend
```

### Access Points

| Service     | URL                          |
|-------------|------------------------------|
| Frontend    | <http://localhost:3000>      |
| Backend API | <http://localhost:8000>      |
| API Docs    | <http://localhost:8000/docs> |
| Dagster     | <http://localhost:3001>      |

### Testing Authentication (Postman)

The backend includes JWT-based authentication. To test locally with Postman:

#### 1. Register a User

**Request:**

```
POST http://localhost:8000/auth/register
Content-Type: application/json

{
  "username": "testuser",
  "password": "testpassword123"
}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "testuser"
}
```

Username must be 3-50 characters; password must be at least 8 characters.

#### 2. Login

**Request:**

```
POST http://localhost:8000/auth/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "testpassword123"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 900
}
```

The response also sets a `refresh_token` HttpOnly cookie. In Postman, enable **Settings → Cookies → Automatically follow redirects** and cookies will be stored automatically.

#### 3. Access Protected Endpoints

Use the access token from login:

**Request:**

```
GET http://localhost:8000/auth/me
Authorization: Bearer <access_token>
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "testuser"
}
```

#### 4. Refresh Token

When the access token expires (15 minutes), refresh it using the cookie:

**Request:**

```
POST http://localhost:8000/auth/refresh
```

No body required - Postman sends the `refresh_token` cookie automatically.

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 900
}
```

#### 5. Logout

**Request:**

```
POST http://localhost:8000/auth/logout
```

**Response:**

```json
{
  "ok": true
}
```

This revokes the refresh token and clears the cookie.

#### Postman Tips

- **Cookie handling:** Postman automatically manages cookies per domain. After login, the `refresh_token` cookie is stored and sent with subsequent requests to `/auth/*` endpoints.
- **Environment variables:** Save the `access_token` to a Postman environment variable in a post-request script:

  ```javascript
  if (pm.response.code === 200) {
      pm.environment.set("access_token", pm.response.json().access_token);
  }
  ```

- **Authorization header:** Use `{{access_token}}` in the Authorization header for protected endpoints.

## Configuration

The project uses separate `.env` files with distinct responsibilities:

| File               | Purpose                                    | Committed |
|--------------------|--------------------------------------------|-----------|
| `.env.compose`     | Docker infrastructure (ports, credentials) | No        |
| `backend/.env`     | Backend runtime (APIs, security)           | No        |
| `frontend/.env`    | Frontend defaults (public config)          | Yes       |

### Quick Setup

```bash
make setup  # Creates .env files from examples and installs dependencies
```

### Manual Setup

**1. Docker infrastructure** (`.env.compose`):

```bash
cp .env.compose.example .env.compose
# Edit with your PostgreSQL credentials
```

**2. Backend runtime** (`backend/.env`):

```bash
cp backend/.env_example backend/.env
# Edit with your credentials (must match .env.compose for database)
```

**3. Frontend** (`frontend/.env`):
Already committed with safe defaults. Create `frontend/.env.local` for secrets if needed.

## PRD Context

When writing PRDs for this project, consider:

- **Where does the request originate?** (Frontend, Dagster schedule, API)
- **What layer handles it?** (API → Domain → External service)
- **What data flows where?** (PostgreSQL for state, S3 for bulk data)
- **Is extraction incremental?** (Use watermarks/extract_date pattern)
- **Does it affect the pipeline?** (Consider Dagster asset dependencies)

Existing PRDs are in `prds/` and follow a consistent structure.

## Development

### Makefile Commands

| Command            | Description                                        |
|--------------------|----------------------------------------------------|
| `make setup`       | First-time setup (create .env files, install deps) |
| `make up`          | Start everything (postgres, migrations, services)  |
| `make down`        | Stop all services                                  |
| `make reset`       | Destroy all data and start fresh                   |
| `make logs`        | Tail all container logs                            |
| `make check`       | Run all validation (backend + frontend)            |
| `make up-db`       | Start Postgres and run migrations                  |
| `make up-backend`  | Start backend with hot-reload (local development)  |
| `make up-frontend` | Start frontend with hot-reload (local development) |
| `make up-dagster`  | Start Dagster UI (local development)               |

### Validation

```bash
make check              # Run backend + frontend validation
cd backend && make check    # Backend only (lint, types, tests)
cd frontend && make check   # Frontend only (lint, typecheck)
```

### Further Reading

- `backend/CLAUDE.md` - Python/FastAPI patterns
- `frontend/CLAUDE.md` - Vue/Nuxt patterns

## Roadmap

See `ROADMAP.md` for planned features.

## Licence

Private - not for redistribution.
