.PHONY: help install test lint format clean run-api run-dashboard security-check

help:
	@echo "Available commands:"
	@echo "  install       Install dependencies"
	@echo "  test          Run tests"
	@echo "  lint          Run linting"
	@echo "  format        Format code"
	@echo "  clean         Clean cache files"
	@echo "  run-api       Start API server"
	@echo "  run-dashboard Start dashboard"
	@echo "  security-check Run security validation"

install:
	pip install -r requirements.txt

test:
	pytest

lint:
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

run-api:
	python -m src.api.main

run-dashboard:
	streamlit run src/dashboard/main.py

security-check:
	python scripts/security_check.py