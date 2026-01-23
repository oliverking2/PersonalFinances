.PHONY: help setup up down reset check logs

# Default target
help:
	@echo "Usage:"
	@echo "  make setup   First-time setup (create .env files, install dependencies)"
	@echo "  make up      Start everything (postgres, migrations, backend, frontend)"
	@echo "  make down    Stop everything"
	@echo "  make reset   Stop and destroy all data, then start fresh"
	@echo "  make check   Run all validation checks"
	@echo "  make logs    Tail all container logs"

# =============================================================================
# First-time setup
# =============================================================================
setup:
	@echo "Creating .env files..."
	@if [ ! -f .env.compose ]; then \
		cp .env.compose.example .env.compose; \
		echo "  Created .env.compose"; \
	else \
		echo "  .env.compose already exists"; \
	fi
	@if [ ! -f backend/.env ]; then \
		cp backend/.env_example backend/.env; \
		echo "  Created backend/.env"; \
	else \
		echo "  backend/.env already exists"; \
	fi
	@echo ""
	@echo "Installing backend dependencies..."
	@cd backend && poetry install --with dev
	@echo ""
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo ""
	@echo "Setup complete!"
	@echo "Edit .env.compose and backend/.env with your credentials, then run: make up"

# =============================================================================
# Up / Down
# =============================================================================
COMPOSE := docker compose --env-file .env.compose

up:
	@echo "Starting postgres..."
	@$(COMPOSE) up -d postgres
	@echo "Waiting for postgres to be ready..."
	@until $(COMPOSE) exec postgres pg_isready -U $$(grep POSTGRES_USERNAME .env.compose | cut -d '=' -f2) > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Postgres ready."
	@echo ""
	@echo "Running database migrations..."
	@cd backend && poetry run alembic upgrade head
	@echo ""
	@echo "Starting all services..."
	@$(COMPOSE) up -d --build
	@echo ""
	@echo "All services started:"
	@echo "  Frontend:    http://localhost:3000"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs:    http://localhost:8000/docs"
	@echo "  Dagster:     http://localhost:3001"

down:
	@echo "Stopping all services..."
	@$(COMPOSE) down
	@echo "Done."

reset:
	@echo "Stopping and removing all data..."
	@$(COMPOSE) down -v
	@echo "Starting fresh..."
	@$(MAKE) up

# =============================================================================
# Development
# =============================================================================
check:
	@cd backend && make check
	@cd frontend && make check

logs:
	@$(COMPOSE) logs -f

# =============================================================================
# Individual services (for development)
# =============================================================================
.PHONY: up-db up-backend up-frontend migrate

up-db:
	@$(COMPOSE) up -d postgres
	@until $(COMPOSE) exec postgres pg_isready -U $$(grep POSTGRES_USERNAME .env.compose | cut -d '=' -f2) > /dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "Postgres ready."

migrate:
	@cd backend && poetry run alembic upgrade head

up-backend:
	@cd backend && poetry run uvicorn src.api.app:app --reload --port 8000

up-frontend:
	@cd frontend && npm run dev
