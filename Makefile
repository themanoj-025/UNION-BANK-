.PHONY: dev test lint format migrate seed docker-up

dev:
	pip install -e .

test:
	pytest tests/

lint:
	ruff check .
	mypy src/unionbank

format:
	ruff format .

migrate:
	alembic upgrade head

seed:
	python -m unionbank.scripts.seed_demo_data

docker-up:
	docker compose up --build
