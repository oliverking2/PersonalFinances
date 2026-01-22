# Frontend Makefile

.PHONY: install dev build preview lint typecheck clean

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

# Lint code
lint:
	npm run lint

# Type check
typecheck:
	npx nuxi typecheck

# Run all checks
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
	@echo "  install   - Install dependencies"
	@echo "  dev       - Run development server"
	@echo "  build     - Build for production"
	@echo "  preview   - Preview production build"
	@echo "  lint      - Lint code"
	@echo "  typecheck - Run type checking"
	@echo "  check     - Run lint and typecheck"
	@echo "  clean     - Remove build artifacts"
