.PHONY: help install test test-health run docker-up docker-down reset-db

help:
	@echo "Available commands:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make test        - Run all tests"
	@echo "  make test-health - Run health check and integration tests (for PR validation)"
	@echo "  make run         - Run API server locally"
	@echo "  make docker-up   - Start Docker Compose services"
	@echo "  make docker-down - Stop Docker Compose services"
	@echo "  make reset-db    - Reset and reindex sample data"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

test-health:
	@echo "Running health check and integration tests..."
	@echo "Make sure services are running: make docker-up"
	pytest tests/test_health_integration.py -v -m "not slow"

run:
	uvicorn api.app:app --reload --port 8000

docker-up:
	cd deploy && docker compose up -d

docker-down:
	cd deploy && docker compose down

reset-db:
	./scripts/reset_local_db.sh

