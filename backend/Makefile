.PHONY: check test lint format types coverage clean

# Default target
help:
	@echo "Backend validation commands:"
	@echo ""
	@echo "  make check    Run all checks (lint, format, types, coverage)"
	@echo "  make test     Run unit tests only"
	@echo "  make clean    Remove caches and build artefacts"
	@echo ""
	@echo "For setup and dev servers, use the root Makefile."

check: lint format types coverage

test:
	poetry run pytest testing/ -v

lint:
	poetry run ruff check --fix

format:
	poetry run ruff format

types:
	poetry run mypy .

coverage:
	poetry run pytest testing/ --cov=src --cov-report=term-missing --cov-fail-under=80

clean:
	rm -rf .mypy_cache .ruff_cache .coverage htmlcov dist build .pytest_cache
