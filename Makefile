.PHONY: help setup setup-demo up up-backend up-frontend up-dagster down reset check logs

# Default target
help:
	@echo "Usage:"
	@echo ""
	@echo "Local dev:"
	@echo "  make setup        First-time setup with real bank data (requires GoCardless)"
	@echo "  make setup-demo   First-time setup with fake demo data (no API needed)"
	@echo "  make up-backend   Start API server (hot reload)"
	@echo "  make up-frontend  Start frontend (hot reload)"
	@echo "  make up-dagster   Start Dagster UI"
	@echo ""
	@echo "Server:"
	@echo "  make up           Start all services (docker-compose)"
	@echo "  make down         Stop all services"
	@echo "  make reset        Destroy all data and run setup again"
	@echo ""
	@echo "  make check        Run all validation checks"

# =============================================================================
# Setup
# =============================================================================
setup:
	@echo "=== Creating .env files ==="
	@if [ ! -f .env.compose ]; then \
		cp .env.compose.example .env.compose; \
		echo "Created .env.compose"; \
	else \
		echo ".env.compose already exists"; \
	fi
	@if [ ! -f backend/.env ]; then \
		cp backend/.env_example backend/.env; \
		echo "Created backend/.env"; \
	else \
		echo "backend/.env already exists"; \
	fi
	@echo ""
	@echo "=== Installing dependencies ==="
	@cd backend && poetry install --with dev
	@cd frontend && npm install
	@echo ""
	@echo "=== Starting database ==="
	@$(COMPOSE) up -d postgres
	@until $(COMPOSE) exec postgres pg_isready -U $$(grep POSTGRES_USERNAME .env.compose | cut -d '=' -f2) > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Postgres ready."
	@echo ""
	@echo "=== Running migrations ==="
	@cd backend && poetry run alembic upgrade head
	@echo ""
	@echo "=== Fetching GoCardless data ==="
	@cd backend && poetry run seed-gocardless
	@echo ""
	@echo "=== Creating dev user ==="
	@cd backend && poetry run seed-dev
	@echo ""
	@echo "=== Bootstrapping DuckDB ==="
	@cd backend && poetry run bootstrap-duckdb
	@echo ""
	@echo "=== Running dbt models ==="
	@set -a && . backend/.env && set +a && cd backend/dbt && poetry run dbt run --profiles-dir . --profile duckdb_local
	@echo ""
	@echo "=== Setup complete! ==="
	@echo ""
	@echo "Start dev servers in separate terminals:"
	@echo "  make up-backend    http://localhost:8000"
	@echo "  make up-frontend   http://localhost:3000"
	@echo "  make up-dagster    http://localhost:3001"
	@echo ""
	@echo "Login: dev / devpassword123"

setup-demo:
	@echo "=== Creating .env files ==="
	@if [ ! -f .env.compose ]; then \
		cp .env.compose.example .env.compose; \
		echo "Created .env.compose"; \
	else \
		echo ".env.compose already exists"; \
	fi
	@if [ ! -f backend/.env ]; then \
		cp backend/.env_example backend/.env; \
		echo "Created backend/.env"; \
	else \
		echo "backend/.env already exists"; \
	fi
	@echo ""
	@echo "=== Installing dependencies ==="
	@cd backend && poetry install --with dev
	@cd frontend && npm install
	@echo ""
	@echo "=== Starting database ==="
	@$(COMPOSE) up -d postgres
	@until $(COMPOSE) exec postgres pg_isready -U $$(grep POSTGRES_USERNAME .env.compose | cut -d '=' -f2) > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Postgres ready."
	@echo ""
	@echo "=== Running migrations ==="
	@cd backend && poetry run alembic upgrade head
	@echo ""
	@echo "=== Creating demo user with fake data ==="
	@cd backend && poetry run seed-demo
	@echo ""
	@echo "=== Bootstrapping DuckDB ==="
	@cd backend && poetry run bootstrap-duckdb
	@echo ""
	@echo "=== Running dbt models ==="
	@set -a && . backend/.env && set +a && cd backend/dbt && poetry run dbt run --profiles-dir . --profile duckdb_local
	@echo ""
	@echo "=== Setup complete! ==="
	@echo ""
	@echo "Start dev servers in separate terminals:"
	@echo "  make up-backend    http://localhost:8000"
	@echo "  make up-frontend   http://localhost:3000"
	@echo "  make up-dagster    http://localhost:3001"
	@echo ""
	@echo "Login: demo / demopassword123"

# =============================================================================
# Server (docker-compose)
# =============================================================================
COMPOSE := docker compose --env-file .env.compose

up:
	@$(COMPOSE) up -d postgres
	@until $(COMPOSE) exec postgres pg_isready -U $$(grep POSTGRES_USERNAME .env.compose | cut -d '=' -f2) > /dev/null 2>&1; do \
		sleep 1; \
	done
	@cd backend && poetry run alembic upgrade head
	@$(COMPOSE) up -d --build
	@echo ""
	@echo "Services running:"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  Dagster:   http://localhost:3001"

# =============================================================================
# Local dev servers
# =============================================================================
up-backend:
	@cd backend && poetry run uvicorn src.api.app:app --reload --port 8000

up-frontend:
	@cd frontend && npm run dev

up-dagster:
	@cd backend && poetry run dagster dev --port 3001

# =============================================================================
# Other
# =============================================================================
down:
	@$(COMPOSE) down

reset:
	@echo "Destroying all data..."
	@$(COMPOSE) down -v
	@echo ""
	@$(MAKE) setup

check:
	@cd backend && make check
	@cd frontend && make check

logs:
	@$(COMPOSE) logs -f
