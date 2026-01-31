# Personal Finances

A self-hosted personal finance aggregation and analytics platform. Connect bank accounts via open banking, track transactions, and gain insights into spending patterns.

Key highlights:

- **Open banking integration** - Connect UK bank accounts via GoCardless Bank Account Data API with OAuth flow and automatic token refresh
- **Analytics pipeline** - Dagster orchestration with dbt transformations (DuckDB reads from PostgreSQL)
- **Layered backend** - FastAPI REST layer with thin endpoints, domain logic in dedicated modules, SQLAlchemy 2.0 for persistence
- **Modern frontend** - Nuxt 4 with Vue 3 Composition API, Tailwind CSS, Pinia state management, and TypeScript
- **Self-hosted** - Full control over financial data, deployed via Cloudflare Tunnel

## Project Goal

This project is a personal finance platform designed to aggregate bank account data and provide insights into spending patterns through a unified dashboard.

The primary use cases include:

- Connecting multiple UK bank accounts via GoCardless open banking
- Viewing consolidated account balances and transactions
- Tagging and categorising transactions
- Analysing spending patterns with dbt-powered transformations

The system maintains incremental extraction state, only fetching new transactions since the last sync.

## Architecture Overview

This section provides a high-level overview of how the system works, intended as context for designing new features and PRDs.

### System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Nuxt 4 Application                                                         │
│  (Vue 3 + Tailwind CSS + Pinia + TypeScript)                                │
│                                                                             │
│  • Pages: Dashboard, Accounts, Transactions, Analytics, Settings            │
│  • Composables: useAuthenticatedFetch, use*Api (domain APIs)                │
│  • Components: AppButton, AppInput, AppSelect (design system)               │
│  • Auth: SSR validation with HttpOnly refresh token cookie                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI REST API                                                           │
│                                                                             │
│  /auth             │  /connections      │  /transactions   │  /analytics    │
│  • Login/logout    │  • List/create     │  • List/filter   │  • Spending    │
│  • Refresh token   │  • OAuth callback  │  • Tag/update    │  • Trends      │
│  • User info       │  • Sync accounts   │  • Date range    │  • Categories  │
│                                                                             │
│  /recurring        │  /budgets          │  /goals          │  /notifications│
│  • Pattern CRUD    │  • Budget CRUD     │  • Goal tracking │  • In-app      │
│  • Accept/pause    │  • Tag-based       │  • Progress      │  • Mark read   │
│  • Transaction link│  • Thresholds      │  • Link accounts │  • Alert types │
│                                                                             │
│  Thin layer: validation, error handling, delegates to domain modules        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOMAIN SERVICES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  postgres/common/         │  postgres/gocardless/    │  providers/gocardless/│
│  (Standardised models)    │  (Raw provider data)     │  (API client)         │
│                           │                          │                       │
│  • Connections            │  • Requisitions          │  • Institution lookup │
│  • Accounts               │  • Bank accounts         │  • Agreement creation │
│  • Transactions           │  • Balances              │  • Transaction fetch  │
│  • Tags                   │                          │  • Balance fetch      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Dagster                                                                    │
│                                                                             │
│  Assets:                         │  Jobs:                                   │
│  • sync_transactions             │  • Sync all accounts                     │
│  • sync_balances                 │  • Backfill transactions                 │
│                                  │                                          │
│  Resources:                      │  Schedules:                              │
│  • PostgresResource              │  • Daily sync                            │
│  • GoCardlessResource            │                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA TRANSFORMATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  dbt (DuckDB reads from PostgreSQL)                                         │
│                                                                             │
│  source/             │  staging/             │  mart/                       │
│  • PostgreSQL tables │  • Cleaned data       │  • fct_daily_spending        │
│  • Schema definitions│  • Type casting       │  • fct_monthly_trends        │
│                      │                       │  • fct_category_breakdown    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  GoCardless API               │  PostgreSQL                                 │
│  (Bank Account Data)          │  (All application data)                     │
│                               │                                             │
│  • Institutions list          │  • Users, auth tokens                       │
│  • Account access (OAuth)     │  • Connections, accounts                    │
│  • Transactions               │  • Transactions, tags                       │
│  • Balances                   │  • GoCardless raw data                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Patterns

#### 1. Bank Connection Flow (User-initiated)

```
Frontend (Accounts page)
    → POST /api/connections (institution_id)
    → GoCardless API (create agreement + requisition)
    → Redirect to bank OAuth
    → Bank authorises
    → Callback to /api/connections/callback
    → Store connection + accounts in PostgreSQL
    → Redirect to frontend
```

#### 2. Transaction Sync (Scheduled/Manual)

```
Dagster Job (daily or triggered via API)
    → For each active account:
        → Get last sync date from PostgreSQL
        → Fetch transactions since last sync from GoCardless
        → Upsert transactions to PostgreSQL
        → Update sync timestamp
```

#### 3. Analytics Query (User-initiated)

```
Frontend (Analytics page)
    → GET /api/analytics/spending?start_date=...&end_date=...
    → API queries dbt mart tables (DuckDB reads from PostgreSQL)
    → Return pre-aggregated analytics data
```

### Key Design Decisions

| Decision                  | Rationale                                                             |
|---------------------------|-----------------------------------------------------------------------|
| Thin API layer            | Endpoints handle HTTP concerns only; business logic in domain modules |
| Session-per-request       | Database operations receive Session, caller manages transactions      |
| PostgreSQL for all data   | Single database simplifies deployment; DuckDB provides analytics perf |
| SSR auth validation       | Server validates auth before rendering; no flash of protected content |
| HttpOnly refresh token    | Secure cookie-based refresh; access token in memory only              |
| Incremental sync          | Watermark prevents re-fetching old transactions                       |
| dbt for analytics         | Version-controlled transformations, testable, self-documenting        |
| Dagster for orchestration | Better observability, native scheduling, asset-based mental model     |

### Module Boundaries

```
backend/src/
├── api/                 # FastAPI endpoints (thin HTTP layer)
│   ├── auth/            # Login, logout, refresh, registration
│   ├── accounts/        # Account listing, balances
│   ├── analytics/       # Spending analytics (queries dbt marts)
│   ├── budgets/         # Tag-based budget tracking
│   ├── connections/     # OAuth flow, connection management
│   ├── goals/           # Savings goals and progress tracking
│   ├── jobs/            # Background job status API
│   ├── milestones/      # Goal milestones
│   ├── notifications/   # In-app notifications
│   ├── planned_transactions/  # Future planned transactions
│   ├── recurring/       # Recurring patterns (opt-in detection)
│   ├── tag_rules/       # Automatic tag application rules
│   ├── tags/            # Tag CRUD
│   ├── trading212/      # Trading212 investment integration
│   ├── transactions/    # Transaction queries and tagging
│   └── user/            # User settings and preferences
├── orchestration/       # Dagster definitions
│   ├── dbt/             # dbt asset definitions
│   ├── exports/         # Data export jobs
│   ├── gocardless/      # Bank sync assets & jobs
│   ├── maintenance/     # Database maintenance jobs
│   ├── recurring_patterns/  # Pattern detection and matching
│   ├── trading212/      # Investment sync assets
│   └── unified/         # Cross-provider unified sync
├── postgres/            # Database layer
│   ├── auth/            # Users, refresh tokens
│   ├── common/          # Standardised models (connections, accounts, transactions, recurring)
│   └── gocardless/      # Raw provider data (requisitions, bank accounts)
├── providers/           # External API clients
│   └── gocardless/      # GoCardless API wrapper
└── utils/               # Logging, security, shared utilities

frontend/app/
├── components/          # Reusable Vue components (App*, feature-grouped)
├── composables/         # useAuthenticatedFetch, use*Api
├── layouts/             # Page layouts (default with nav)
├── middleware/          # Route guards (auth.global.ts)
├── pages/               # File-based routes
├── stores/              # Pinia stores (auth, toast)
└── types/               # TypeScript interfaces
```

## Technology Stack

| Layer         | Technology                                        |
|---------------|---------------------------------------------------|
| Frontend      | Vue 3, Nuxt 4, Tailwind CSS, Pinia, TypeScript    |
| Backend       | Python 3.12+, FastAPI, SQLAlchemy 2.0             |
| Database      | PostgreSQL (all data), DuckDB (analytics queries) |
| Orchestration | Dagster                                           |
| Transforms    | dbt                                               |
| Bank API      | GoCardless Bank Account Data                      |
| Deployment    | Docker Compose, Cloudflare Tunnel                 |

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

### Access Points (Local Development)

| Service     | URL                          |
|-------------|------------------------------|
| Frontend    | <http://localhost:3000>      |
| Backend API | <http://localhost:8000>      |
| API Docs    | <http://localhost:8000/docs> |
| Dagster     | <http://localhost:3001>      |

### Testing Authentication (Postman)

The backend includes JWT-based authentication. To test locally with Postman:

#### 1. Register a User

In local development (`ENVIRONMENT=local`), registration is open. In production, an admin token is required.

**Request (local):**

```
POST http://localhost:8000/auth/register
Content-Type: application/json

{
  "username": "testuser",
  "password": "testpassword123"
}
```

**Request (production):**

```
POST https://finances-api.oliverking.me.uk/auth/register
Content-Type: application/json
Authorization: Bearer <your-admin-token>

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
| `backend/.env`     | Backend runtime (APIs, security, CORS)     | No        |
| `frontend/.env`    | Frontend config (API URL)                  | No        |

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

Key backend variables:

| Variable       | Description                                                                 |
|----------------|-----------------------------------------------------------------------------|
| `ENVIRONMENT`  | `local` or `prod` (affects logging, admin token requirement)                |
| `CORS_ORIGINS` | Comma-separated allowed origins (e.g., `https://finances.oliverking.me.uk`) |
| `ADMIN_TOKEN`  | Required in prod for `/auth/register` endpoint                              |
| `JWT_SECRET`   | Secret for signing tokens (min 32 chars)                                    |

**3. Frontend** (`frontend/.env`):

```bash
cp frontend/.env.example frontend/.env
# Set NUXT_PUBLIC_API_URL to your backend URL
```

| Variable              | Description                                    |
|-----------------------|------------------------------------------------|
| `NUXT_PUBLIC_API_URL` | Backend API URL (browser calls this directly)  |

## Deployment

The app runs on a home server exposed via **Cloudflare Tunnel** (cloudflared).

| Service  | URL                                     |
|----------|-----------------------------------------|
| Frontend | <https://finances.oliverking.me.uk>     |
| Backend  | <https://finances-api.oliverking.me.uk> |

### Tunnel Setup

1. Configure two tunnels in Cloudflare dashboard pointing to local services
2. Set `CORS_ORIGINS=https://finances.oliverking.me.uk` in `backend/.env`
3. Set `NUXT_PUBLIC_API_URL=https://finances-api.oliverking.me.uk` in `frontend/.env`
4. Restart services after env changes

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
