# AI Web Scraper Makefile

.PHONY: help install test test-unit test-integration test-performance test-e2e test-all
.PHONY: test-coverage test-comprehensive lint format security clean
.PHONY: run-api run-dashboard setup-db setup-test-db
.PHONY: docker-build docker-run docker-test

help:
	@echo "Available commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          - Install dependencies"
	@echo "  setup-db         - Set up the database"
	@echo "  setup-test-db    - Set up test database"
	@echo ""
	@echo "Testing:"
	@echo "  test             - Run basic tests"
	@echo "  test-unit        - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-performance - Run performance tests only"
	@echo "  test-e2e         - Run end-to-end tests only"
	@echo "  test-all         - Run all test suites"
	@echo "  test-coverage    - Run tests with coverage report"
	@echo "  test-comprehensive - Run comprehensive test suite"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             - Run linting checks"
	@echo "  format           - Format code with black and isort"
	@echo "  security         - Run security checks"
	@echo ""
	@echo "Running:"
	@echo "  run-api          - Run the API server"
	@echo "  run-dashboard    - Run the dashboard"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     - Build Docker image"
	@echo "  docker-run       - Run in Docker container"
	@echo "  docker-test      - Run tests in Docker"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean            - Clean up generated files"

# Installation
install:
	pip install -r requirements.txt
	pip install pytest-xdist pytest-benchmark pytest-mock
	pip install black isort flake8 bandit safety mypy

# Database setup
setup-db:
	python -m alembic upgrade head

setup-test-db:
	@echo "Setting up test database..."
	@export DATABASE_URL="sqlite:///test.db" && python -m alembic upgrade head

# Basic testing
test:
	python -m pytest tests/ -v --tb=short

test-unit:
	python -m pytest tests/unit/ -v --tb=short -m "not integration and not performance"

test-integration:
	python -m pytest tests/integration/ -v --tb=short -m "integration"

test-performance:
	python -m pytest tests/performance/ -v --tb=short -m "performance" --durations=10

test-e2e:
	python -m pytest tests/integration/test_end_to_end_workflows.py -v --tb=short

test-all:
	python -m pytest tests/ -v --tb=short --durations=20

# Coverage testing
test-coverage:
	python -m pytest tests/ \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=90 \
		-v

test-comprehensive:
	python tests/run_comprehensive_tests.py --all --verbose --report

# Code quality
lint:
	@echo "Running flake8..."
	python -m flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503
	@echo "Running mypy..."
	python -m mypy src/ --ignore-missing-imports --no-strict-optional
	@echo "Checking import sorting..."
	python -m isort --check-only --diff src/ tests/
	@echo "Checking code formatting..."
	python -m black --check --diff src/ tests/

format:
	@echo "Formatting code with black..."
	python -m black src/ tests/
	@echo "Sorting imports with isort..."
	python -m isort src/ tests/

security:
	@echo "Running bandit security check..."
	python -m bandit -r src/ -f json -o bandit-report.json || true
	@echo "Running safety dependency check..."
	python -m safety check --json --output safety-report.json || true
	@echo "Security reports generated: bandit-report.json, safety-report.json"

# Running applications
run-api:
	python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-dashboard:
	python run_dashboard.py

# Docker commands
docker-build:
	docker build -t ai-web-scraper .

docker-run:
	docker run -p 8000:8000 -p 8501:8501 ai-web-scraper

docker-test:
	docker run --rm ai-web-scraper python -m pytest tests/ -v

# Development helpers
dev-setup: install setup-test-db
	@echo "Development environment setup complete!"

dev-test: format lint test-coverage
	@echo "Development testing complete!"

# CI/CD helpers
ci-test: test-comprehensive security
	@echo "CI testing complete!"

# Performance monitoring
benchmark:
	python -m pytest tests/performance/ \
		--benchmark-only \
		--benchmark-json=benchmark-results.json \
		--benchmark-compare-fail=min:5% \
		--benchmark-compare-fail=mean:10%

# Cleanup
clean:
	@echo "Cleaning up generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/
	rm -rf .coverage*
	rm -rf coverage*.xml
	rm -rf junit*.xml
	rm -rf benchmark-results.json
	rm -rf bandit-report.json
	rm -rf safety-report.json
	rm -rf test-report.md
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf dist/
	rm -rf build/
	@echo "Cleanup complete!"

# Help for specific test categories
test-help:
	@echo "Test Categories:"
	@echo ""
	@echo "Unit Tests (tests/unit/):"
	@echo "  - Test individual components in isolation"
	@echo "  - Fast execution, no external dependencies"
	@echo "  - Run with: make test-unit"
	@echo ""
	@echo "Integration Tests (tests/integration/):"
	@echo "  - Test component interactions"
	@echo "  - May require database/Redis"
	@echo "  - Run with: make test-integration"
	@echo ""
	@echo "Performance Tests (tests/performance/):"
	@echo "  - Test system performance under load"
	@echo "  - Concurrent processing, scalability"
	@echo "  - Run with: make test-performance"
	@echo ""
	@echo "End-to-End Tests:"
	@echo "  - Test complete workflows"
	@echo "  - Full system integration"
	@echo "  - Run with: make test-e2e"
	@echo ""
	@echo "Comprehensive Suite:"
	@echo "  - All tests + coverage + quality checks"
	@echo "  - Run with: make test-comprehensive"