.PHONY: help setup setup-demo up up-db up-backend up-frontend up-dagster up-telegram down reset check logs clone-prod

# Default target
help:
	@echo "Usage:"
	@echo ""
	@echo "Local dev:"
	@echo "  make setup        First-time setup with real bank data (requires GoCardless)"
	@echo "  make setup-demo   First-time setup with fake demo data (no API needed)"
	@echo "  make up-db        Start Postgres and run migrations"
	@echo "  make up-backend   Start API server (hot reload)"
	@echo "  make up-frontend  Start frontend (hot reload)"
	@echo "  make up-dagster   Start Dagster UI"
	@echo "  make up-telegram  Start Telegram bot (polling mode)"
	@echo ""
	@echo "Server:"
	@echo "  make up           Start all services (docker-compose)"
	@echo "  make down         Stop all services"
	@echo "  make reset        Destroy all data and run setup again"
	@echo ""
	@echo "Database:"
	@echo "  make clone-prod   Clone prod database to local (requires .env.prod)"
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
	@if [ ! -f frontend/.env ]; then \
		cp frontend/.env.example frontend/.env; \
		echo "Created frontend/.env"; \
	else \
		echo "frontend/.env already exists"; \
	fi
	@echo ""
	@echo "=== Installing dependencies ==="
	@cd backend && poetry install --with dev
	@cd frontend && npm install
	@echo ""
	@echo "=== Starting database ==="
	@$(COMPOSE) up -d --wait postgres
	@echo "Postgres ready."
	@echo ""
	@echo "=== Running migrations ==="
	@cd backend && poetry run alembic upgrade head
	@echo ""
	@echo "=== Fetching GoCardless data ==="
	@cd backend && poetry run seed-gocardless
	@echo ""
	@echo "=== Creating user ==="
	@cd backend && poetry run seed-user
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
	@echo "Login: <username> / <password>"

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
	@if [ ! -f frontend/.env ]; then \
		cp frontend/.env.example frontend/.env; \
		echo "Created frontend/.env"; \
	else \
		echo "frontend/.env already exists"; \
	fi
	@echo ""
	@echo "=== Installing dependencies ==="
	@cd backend && poetry install --with dev
	@cd frontend && npm install
	@echo ""
	@echo "=== Starting database ==="
	@$(COMPOSE) up -d --wait postgres
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
	@$(COMPOSE) up -d --wait postgres
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
up-db:
	@$(COMPOSE) up -d --wait postgres
	@echo "Postgres ready."
	@cd backend && poetry run alembic upgrade head
	@cd backend && make dbt

up-backend:
	@cd backend && poetry run uvicorn src.api.app:app --reload --port 8000

up-frontend:
	@cd frontend && npm run dev

up-dagster:
	@set -a && . backend/.env && set +a && cd backend && poetry run dagster dev --port 3001

up-telegram:
	@cd backend && poetry run python -m src.telegram

# =============================================================================
# Database Operations
# =============================================================================
clone-prod:
	@# Install postgresql-client-17 if pg_dump is not available or wrong version
	@if ! command -v pg_dump > /dev/null 2>&1 || ! pg_dump --version | grep -q "pg_dump (PostgreSQL) 17"; then \
		echo "=== Installing postgresql-client-17 ==="; \
		sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $$(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'; \
		wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -; \
		sudo apt-get update && sudo apt-get install -y postgresql-client-17; \
	fi
	@# Create .env.prod from example if it doesn't exist
	@if [ ! -f .env.prod ]; then \
		cp .env.prod.example .env.prod; \
		echo ""; \
		echo "Created .env.prod from .env.prod.example"; \
		echo "Please edit .env.prod with your production database credentials, then run 'make clone-prod' again."; \
		echo ""; \
		exit 1; \
	fi
	@echo "=== Loading prod credentials ==="
	@set -a && . ./.env.prod && . ./.env.compose && set +a && \
	echo "=== Dumping prod database ===" && \
	PGPASSWORD=$$PROD_POSTGRES_PASSWORD pg_dump \
		-h $$PROD_POSTGRES_HOSTNAME \
		-p $${PROD_POSTGRES_PORT:-5432} \
		-U $${PROD_POSTGRES_USERNAME:-personal_finances} \
		-d $${PROD_POSTGRES_DATABASE:-personal_finances} \
		-Fc \
		--no-owner \
		--no-acl \
		> .prod_backup.dump && \
	echo "=== Ensuring local database is running ===" && \
	$(COMPOSE) up -d --wait postgres && \
	echo "=== Dropping and recreating local database ===" && \
	docker exec postgres psql -U $$POSTGRES_USERNAME -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$$POSTGRES_DATABASE' AND pid <> pg_backend_pid();" > /dev/null && \
	docker exec postgres psql -U $$POSTGRES_USERNAME -d postgres -c "DROP DATABASE IF EXISTS $$POSTGRES_DATABASE;" && \
	docker exec postgres psql -U $$POSTGRES_USERNAME -d postgres -c "CREATE DATABASE $$POSTGRES_DATABASE;" && \
	echo "=== Restoring dump to local database ===" && \
	PGPASSWORD=$$POSTGRES_PASSWORD pg_restore \
		-h localhost \
		-p $${POSTGRES_PORT:-5432} \
		-U $$POSTGRES_USERNAME \
		-d $$POSTGRES_DATABASE \
		--no-owner \
		--no-acl \
		.prod_backup.dump && \
	rm .prod_backup.dump && \
	echo "=== Running migrations ===" && \
	cd backend && poetry run alembic upgrade head && cd .. && \
	echo "=== Rebuilding DuckDB ===" && \
	cd backend && poetry run bootstrap-duckdb && cd .. && \
	echo "=== Running dbt models ===" && \
	set -a && . backend/.env && set +a && cd backend/dbt && poetry run dbt run --profiles-dir . --profile duckdb_local && \
	echo "" && \
	echo "=== Clone complete! ===" && \
	echo "Local database now mirrors prod."

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
