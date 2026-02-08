.PHONY: check test lint format types coverage clean dbt dbt-docs sql sql-lint

# Default target
help:
	@echo "Backend validation commands:"
	@echo ""
	@echo "  make check    Run all checks (lint, format, types, sql, coverage)"
	@echo "  make test     Run unit tests only"
	@echo "  make clean    Remove caches and build artefacts"
	@echo ""
	@echo "SQL commands:"
	@echo ""
	@echo "  make sql      Lint and auto-fix SQL files with sqlfluff"
	@echo "  make sql-lint Lint SQL files without auto-fix (check only)"
	@echo ""
	@echo "dbt commands:"
	@echo ""
	@echo "  make dbt      Build dbt models (run + test)"
	@echo "  make dbt-docs Generate and serve dbt docs"
	@echo ""
	@echo "For setup and dev servers, use the root Makefile."

check: lint format types sql coverage

test:
	poetry run pytest testing/ -v -n auto

lint:
	poetry run ruff check --fix

format:
	poetry run ruff format

types:
	poetry run mypy .

coverage:
	poetry run pytest testing/ -n auto --cov=src --cov-report=term-missing --cov-fail-under=80

clean:
	rm -rf .mypy_cache .ruff_cache .coverage htmlcov dist build .pytest_cache

# SQL linting and auto-fix (run from backend directory)
# Source .env for PostgreSQL connection vars needed by dbt templater
# Set DUCKDB_PATH relative to backend/ since SQLFluff runs from here
sql:
	@set -a && . ./.env && set +a && DUCKDB_PATH=./data/analytics.duckdb poetry run sqlfluff fix dbt/models/ --config pyproject.toml

# SQL lint only (no auto-fix) - useful for checking what violations exist
sql-lint:
	@set -a && . ./.env && set +a && DUCKDB_PATH=./data/analytics.duckdb poetry run sqlfluff lint dbt/models/ --config pyproject.toml

# dbt commands (run from backend directory)
# Source .env for PostgreSQL connection vars needed by DuckDB postgres extension
dbt:
	@mkdir -p data/parquet/mart
	@set -a && . ./.env && set +a && cd dbt && poetry run dbt build --profiles-dir . --profile duckdb_local && poetry run dbt docs generate --profiles-dir . --profile duckdb_local

dbt-docs:
	@set -a && . ./.env && set +a && cd dbt && poetry run dbt docs generate --profiles-dir . --profile duckdb_local && poetry run dbt docs serve --profiles-dir . --profile duckdb_local
