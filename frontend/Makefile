# Frontend Makefile
SHELL := /bin/bash

.PHONY: install dev build preview lint lint-check typecheck check clean

# Install dependencies
install:
	npm install

# Run development server
dev:
	npm run dev

# Build for production
build:
	npm run build

# Preview production build
preview:
	npm run preview

# Format and lint (auto-fix)
lint:
	npm run lint

# Lint check only (no auto-fix)
lint-check:
	npx eslint . --max-warnings 0

# Type check
typecheck:
	npx nuxi typecheck

# Run all checks (format + lint + typecheck)
check: lint typecheck

# Clean build artifacts
clean:
	rm -rf .nuxt .output dist node_modules/.cache

# Generate static site (if needed)
generate:
	npm run generate

# Update dependencies
update:
	npm update

# Help
help:
	@echo "Available targets:"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Run development server"
	@echo "  build      - Build for production"
	@echo "  preview    - Preview production build"
	@echo "  lint       - Format and lint (auto-fix)"
	@echo "  lint-check - Lint check only (no auto-fix)"
	@echo "  typecheck  - Run type checking"
	@echo "  check      - Run fix + typecheck"
	@echo "  clean      - Remove build artifacts"
