.PHONY: help install test run docker-up docker-down reset-db

help:
	@echo "Available commands:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make test        - Run tests"
	@echo "  make run         - Run API server locally"
	@echo "  make docker-up   - Start Docker Compose services"
	@echo "  make docker-down - Stop Docker Compose services"
	@echo "  make reset-db    - Reset and reindex sample data"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

run:
	uvicorn api.app:app --reload --port 8000

docker-up:
	cd deploy && docker compose up -d

docker-down:
	cd deploy && docker compose down

reset-db:
	./scripts/reset_local_db.sh

