# Personal Finances

A self-hosted personal finance aggregation and analytics platform. Connect all your bank accounts in one place, track transactions, and gain insights into your spending patterns.

**Key highlights:**

- **Open Banking Integration** - Connect UK bank accounts via GoCardless to automatically fetch transactions and balances
- **Unified Dashboard** - View all accounts and transactions in a single interface (Vue + Nuxt frontend planned)
- **Data Pipeline** - Dagster orchestration with dbt transformations for analytics-ready data
- **Self-Hosted** - Full control over your financial data with local storage options

---

## Project Goal

This project is a personal finance tracker designed to aggregate financial data from multiple sources into a single, self-hosted dashboard. The goal is to provide complete visibility into spending patterns, account balances, and financial trends without relying on third-party services that store your data.

The primary use cases include:
- Viewing all bank account balances in one place
- Analysing transaction history across accounts
- Tracking spending trends and patterns
- Future: AI-powered insights and budget allocation
- Future: Telegram notifications for account activity

## Architecture Overview

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
│  - Source layer: raw data ingestion from S3                                 │
│  - Staging layer: cleaned and standardised transactions                     │
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

### Data Flow

1. **Bank Connection**: User links bank accounts via GoCardless open banking
2. **Data Extraction**: Dagster jobs fetch transactions and balances on schedule
3. **Storage**: Raw data stored in PostgreSQL (metadata) and S3 (Parquet files)
4. **Transformation**: dbt models transform raw data into analytics tables
5. **Presentation**: Frontend displays dashboards and account views

### Technology Stack

| Layer            | Technology                    |
|------------------|-------------------------------|
| Language         | Python 3.12+                  |
| API Framework    | FastAPI                       |
| Frontend         | Vue + Nuxt + Tailwind (planned) |
| Current UI       | Streamlit (temporary)         |
| Database         | PostgreSQL + DuckDB           |
| Object Storage   | AWS S3 (Parquet)              |
| Transformations  | dbt                           |
| Orchestration    | Dagster                       |
| Bank Connections | GoCardless (Open Banking)     |
| Containerisation | Docker Compose                |

### Module Structure

```
src/
├── aws/           # AWS clients (S3, SSM parameters)
├── dagster/       # Orchestration jobs and schedules
│   ├── dbt/       # dbt asset definitions
│   └── gocardless/# GoCardless extraction assets
├── gocardless/    # GoCardless API client
│   └── api/       # API endpoints (accounts, requisitions, etc.)
├── postgres/      # Database layer
│   └── gocardless/# GoCardless models and operations
├── streamlit/     # Current UI (to be replaced)
└── utils/         # Shared utilities

dbt/
├── models/
│   ├── 1_source/  # Raw data sources
│   ├── 2_staging/ # Cleaned data
│   └── 3_mart/    # Analytics aggregations
└── profiles.yml   # DuckDB connection config
```

## Setup

### Prerequisites
- Python 3.12+
- Poetry
- Docker and Docker Compose
- AWS account (for S3 storage)
- GoCardless account (for bank connections)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd PersonalFinances

# Install dependencies
poetry install

# Copy environment template
cp .env_example .env
# Edit .env with your credentials
```

### Configuration

Edit `.env` with your credentials:

```bash
# Environment
ENVIRONMENT=local

# AWS (for S3 storage)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=eu-west-2
S3_BUCKET_NAME=your-bucket-name

# PostgreSQL
POSTGRES_HOSTNAME=localhost
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=postgres

# GoCardless callback URL
GC_CALLBACK_URL=http://localhost:8501/connections?gc_callback=1
```

### Running Locally

Start the database with Docker:
```bash
docker-compose up -d postgres
```

Run database migrations:
```bash
poetry run alembic upgrade head
```

Start Dagster for orchestration:
```bash
poetry run dagster dev
```

Start the Streamlit UI (temporary):
```bash
poetry run streamlit run src/streamlit/app.py
```

### Running with Docker

Start all services:
```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Dagster webserver (http://localhost:3000)
- Dagster daemon (runs scheduled jobs)

## Features

### Bank Account Connections

Connect UK bank accounts via GoCardless open banking:
- Supports major UK banks
- Automatic transaction fetching
- Balance synchronisation
- Link expiry handling

### Transaction Extraction

Dagster orchestrates scheduled data extraction:
- Fetches new transactions from connected accounts
- Stores raw data in S3 as Parquet files
- Tracks extraction state in PostgreSQL

### Data Transformation

dbt transforms raw data for analytics:
- **Source layer**: Raw transaction data from S3
- **Staging layer**: Cleaned and standardised transactions
- **Mart layer**: Aggregated views for dashboards

### Current UI (Streamlit)

Temporary interface for account management:
- View connected accounts
- Manage bank connections
- Basic transaction views

## Development

### Running Checks

```bash
# Run all validation
make check

# Individual commands
make lint      # Ruff linting
make format    # Ruff formatting
make types     # mypy type checking
make test      # Unit tests
make coverage  # Tests with coverage
```

### Database Migrations

```bash
# Apply migrations
poetry run alembic upgrade head

# Create new migration
poetry run alembic revision --autogenerate -m "description"
```

### dbt Commands

```bash
cd dbt

# Run models
dbt run --profiles-dir . --profile duckdb_local

# Run tests
dbt test --profiles-dir . --profile duckdb_local
```

## Roadmap

See `ROADMAP.md` for planned features including:
- Vue + Nuxt frontend migration
- Additional data sources (Vanguard, Trading212)
- AI-powered spending insights
- Telegram notifications
- Budget allocation features

## Contributing

This is a personal project, but suggestions and feedback are welcome via issues.

## License

Private - not for redistribution.
