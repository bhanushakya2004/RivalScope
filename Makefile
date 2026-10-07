.PHONY: up down build demo test lint typecheck migrate seed clean help

PYTHON ?= uv run python
UV ?= uv

help:
	@echo "RivalScope Makefile Commands:"
	@echo "  make up          - Start all Docker services (api, worker, postgres, redis, web)"
	@echo "  make down        - Stop all Docker services"
	@echo "  make build       - Build docker images"
	@echo "  make demo        - Run full offline demo pipeline (seeds data, runs agents, generates report)"
	@echo "  make evals       - Run agent benchmark harness with LLM-as-a-judge & guardrails"
	@echo "  make migrate     - Run database migrations via Alembic"
	@echo "  make seed        - Seed database with fintech competitor data"
	@echo "  make test        - Run backend test suite"
	@echo "  make lint        - Run ruff linter & formatter check"
	@echo "  make typecheck   - Run mypy type checking"
	@echo "  make clean       - Remove cache, temp, and build files"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	cd backend && $(UV) run alembic upgrade head

seed:
	cd backend && $(PYTHON) -m app.db.seed

demo:
	cd backend && $(PYTHON) -m app.scripts.demo_runner

evals:
	cd backend && $(PYTHON) -m app.evals.harness

test:
	cd backend && $(UV) run pytest tests/ -v

lint:
	cd backend && $(UV) run ruff check app tests
	cd backend && $(UV) run ruff format --check app tests

typecheck:
	cd backend && $(UV) run mypy app

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
