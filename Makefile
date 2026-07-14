# ═══════════════════════════════════════════════════════════════════════════════
#  UNION BANK MANAGEMENT SYSTEM  —  Makefile
# ═══════════════════════════════════════════════════════════════════════════════
#  Common Docker commands for development and production.
#
#  Prerequisites:
#    - Docker Engine 24+  (docker.com)
#    - Docker Compose V2  (comes with Docker Desktop)
#
#  Usage:
#    make help          # Show this help
#    make build         # Build all Docker images
#    make up            # Start all services (detached)
#    make logs          # Follow logs
#    make down          # Stop all services
#    make test          # Run test suite inside a Docker container
#    make shell-web     # Open a shell in the web container
#    make shell-api     # Open a shell in the api container
#    make clean         # Remove containers, images, and volumes
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help build build-web build-api up up-dev down logs test shell-web shell-api clean

# ── Default target ──────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'


# ── Build ────────────────────────────────────────────────────────────────────

build: ## Build all Docker images
	docker compose build

build-web: ## Build only the Flask web image
	docker compose build web

build-api: ## Build only the FastAPI image
	docker compose build api


# ── Run ──────────────────────────────────────────────────────────────────────

up: ## Start all services in detached mode
	docker compose up -d
	@echo ""
	@echo "  Web:   http://localhost:5000"
	@echo "  API:   http://localhost:8000"
	@echo "  Docs:  http://localhost:8000/docs"

up-dev: ## Start with hot-reload (development mode — rebuilds images first)
	docker compose build
	docker compose up -d
	@echo ""
	@echo "  Web:   http://localhost:5000"
	@echo "  API:   http://localhost:8000"
	@echo "  Docs:  http://localhost:8000/docs"
	@echo ""
	@echo "  ℹ  For hot-reload, set TARGET=api and use:"
	@echo "     docker compose build --target dev"
	@echo "     docker compose up -d"

up-prod: ## Start with production overrides
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

logs: ## Follow logs from all services
	docker compose logs -f

down: ## Stop and remove containers
	docker compose down


# ── Testing ──────────────────────────────────────────────────────────────────

test: ## Run test suite inside a Docker container
	docker compose run --rm --no-deps web \
		python -m pytest tests/ -v --tb=short --cov --cov-report=term

test-ci: ## Run tests with coverage (CI-friendly output)
	docker compose run --rm --no-deps web \
		python -m pytest tests/ -v --tb=short --cov --cov-report=term --cov-report=xml


# ── Interactive ──────────────────────────────────────────────────────────────

shell-web: ## Open a bash shell inside the web container
	docker compose run --rm web bash

shell-api: ## Open a bash shell inside the api container
	docker compose run --rm api bash


# ── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Remove containers, images, volumes, and cached data
	docker compose down --volumes --remove-orphans
	docker rmi union-bank/web:latest union-bank/api:latest 2>/dev/null || true
	@echo "  [✓] Cleaned up Docker resources"
