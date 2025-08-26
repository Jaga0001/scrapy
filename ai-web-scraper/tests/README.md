# AI Web Scraper Test Suite

This directory contains the comprehensive test suite for the AI Web Scraper project, designed to ensure 90%+ code coverage and robust system validation.

## Test Structure

```
tests/
├── unit/                           # Unit tests for individual components
├── integration/                    # Integration tests for component interactions
├── performance/                    # Performance and load testing
├── fixtures/                       # Test fixtures and mock services
│   ├── auth_fixtures.py           # Authentication test data
│   ├── schema_fixtures.py         # Schema validation test data
│   ├── mock_services.py           # Mock external services
│   └── test_data_fixtures.py      # Comprehensive test data
├── conftest.py                     # Pytest configuration and shared fixtures
├── run_comprehensive_tests.py     # Comprehensive test runner
└── README.md                       # This file
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Coverage**: Individual modules, functions, and classes
- **Dependencies**: Minimal external dependencies, heavy use of mocks
- **Execution Time**: Fast (< 30 seconds)
- **Run Command**: `make test-unit` or `pytest tests/unit/`

**Key Areas Covered**:
- Data models and validation
- Database operations
- Configuration management
- Utility functions
- Error handling

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions and workflows
- **Coverage**: Cross-module functionality, API endpoints, database integration
- **Dependencies**: May require database, Redis, external services
- **Execution Time**: Medium (1-5 minutes)
- **Run Command**: `make test-integration` or `pytest tests/integration/ -m integration`

**Key Areas Covered**:
- End-to-end scraping workflows
- API endpoint functionality
- Dashboard components
- Database integration
- Service interactions

### Performance Tests (`tests/performance/`)
- **Purpose**: Test system performance under various load conditions
- **Coverage**: Concurrent processing, scalability, resource usage
- **Dependencies**: System resources, may require external services
- **Execution Time**: Long (5-15 minutes)
- **Run Command**: `make test-performance` or `pytest tests/performance/ -m performance`

**Key Areas Covered**:
- Concurrent job processing
- Load balancing
- Memory usage under load
- Throughput and latency
- Error handling under stress

## Test Configuration

### Pytest Configuration (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=90"
markers = [
    "unit: Unit tests",
    "integration: Integration tests", 
    "performance: Performance tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
]
```

### Coverage Configuration
- **Minimum Coverage**: 90%
- **Source Directory**: `src/`
- **Reports**: HTML, XML, Terminal
- **Branch Coverage**: Enabled
- **Parallel Execution**: Supported

## Running Tests

### Quick Start
```bash
# Install dependencies
make install

# Run all tests with coverage
make test-coverage

# Run comprehensive test suite
make test-comprehensive
```

### Individual Test Categories
```bash
# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Performance tests only
make test-performance

# End-to-end tests only
make test-e2e
```

### Advanced Options
```bash
# Run tests with verbose output
pytest tests/ -v

# Run tests in parallel
pytest tests/ -n auto

# Run specific test file
pytest tests/unit/test_scraper.py

# Run tests matching pattern
pytest tests/ -k "test_scraping"

# Run tests with specific markers
pytest tests/ -m "not slow"
```

## Test Data and Fixtures

### Mock Services (`tests/fixtures/mock_services.py`)
Provides mock implementations for:
- **MockWebDriver**: Selenium WebDriver simulation
- **MockGeminiAPI**: AI processing service simulation
- **MockDatabase**: Database operations simulation
- **MockRedis**: Redis cache simulation
- **MockFileSystem**: File system operations simulation

### Test Data Generators (`tests/fixtures/test_data_fixtures.py`)
Provides fixtures for:
- Large datasets for performance testing
- Edge cases and malformed data
- Concurrent processing scenarios
- API testing scenarios
- Security testing scenarios

### Authentication Fixtures (`tests/fixtures/auth_fixtures.py`)
Provides fixtures for:
- User authentication testing
- JWT token validation
- Permission and role testing
- Security scenario testing

## Coverage Requirements

### Minimum Coverage Targets
- **Overall Coverage**: 90%
- **Unit Tests**: 95%
- **Integration Tests**: 85%
- **Critical Paths**: 100%

### Coverage Exclusions
The following are excluded from coverage requirements:
- Test files themselves
- Migration scripts
- Development utilities
- Abstract base classes
- Exception handling for impossible conditions

### Coverage Reports
- **HTML Report**: `htmlcov/index.html`
- **XML Report**: `coverage.xml`
- **Terminal Report**: Displayed after test execution

## Continuous Integration

### GitHub Actions Workflow
The project includes a comprehensive CI/CD pipeline (`.github/workflows/comprehensive-tests.yml`) that:
- Runs tests on multiple Python versions (3.9-3.12)
- Tests against PostgreSQL and Redis services
- Generates coverage reports
- Performs security checks
- Runs performance benchmarks

### CI Test Matrix
```yaml
strategy:
  matrix:
    python-version: [3.9, 3.10, 3.11, 3.12]
    test-type: [unit, integration, performance]
```

## Performance Benchmarks

### Target Performance Metrics
- **Scraping Speed**: 50+ pages/minute
- **API Response Time**: <500ms average
- **Memory Usage**: <500MB for typical workloads
- **Concurrent Jobs**: Support 10+ simultaneous jobs
- **Test Execution**: Unit tests <30s, Integration tests <5min

### Benchmark Tests
Performance tests include benchmarks for:
- Concurrent job processing
- Database query performance
- API endpoint response times
- Memory usage patterns
- Error recovery times

## Test Environment Setup

### Local Development
```bash
# Set up development environment
make dev-setup

# Run development test suite
make dev-test
```

### Required Environment Variables
```bash
export DATABASE_URL="${TEST_DATABASE_URL}"
export REDIS_URL="${TEST_REDIS_URL}"
export GEMINI_API_KEY="${TEST_GEMINI_API_KEY}"
export SECRET_KEY="test-secret-key"
export ENVIRONMENT="test"
```

### Docker Testing
```bash
# Build test image
make docker-build

# Run tests in Docker
make docker-test
```

## Debugging Tests

### Common Issues and Solutions

#### Test Database Issues
```bash
# Reset test database
make setup-test-db

# Check database connection
python -c "from config.database import get_db_connection; print('DB OK')"
```

#### Redis Connection Issues
```bash
# Check Redis connection
redis-cli ping

# Use alternative Redis instance
export REDIS_URL="redis://localhost:6379/15"
```

#### Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Install in development mode
pip install -e .
```

### Debugging Specific Tests
```bash
# Run single test with debugging
pytest tests/unit/test_scraper.py::TestWebScraper::test_scrape_url -v -s

# Run with pdb debugger
pytest tests/unit/test_scraper.py --pdb

# Run with coverage debugging
pytest tests/unit/test_scraper.py --cov-report=term-missing --cov-report=html
```

## Writing New Tests

### Test Naming Conventions
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`
- Fixture files: `*_fixtures.py`

### Test Structure Template
```python
"""
Test module for [component name].

This module tests [brief description of what's being tested].
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.component import ComponentClass


class TestComponentClass:
    """Test suite for ComponentClass."""
    
    @pytest.fixture
    def mock_dependency(self):
        """Mock external dependency."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_component_method(self, mock_dependency):
        """Test component method functionality."""
        # Arrange
        component = ComponentClass(mock_dependency)
        expected_result = "expected"
        
        # Act
        result = await component.method()
        
        # Assert
        assert result == expected_result
        mock_dependency.some_method.assert_called_once()
```

### Best Practices
1. **Use descriptive test names** that explain what is being tested
2. **Follow AAA pattern** (Arrange, Act, Assert)
3. **Mock external dependencies** to ensure test isolation
4. **Test both success and failure scenarios**
5. **Use appropriate pytest markers** for test categorization
6. **Include docstrings** explaining test purpose
7. **Keep tests focused** on single functionality
8. **Use fixtures** for common test data and setup

## Test Maintenance

### Regular Maintenance Tasks
- Review and update test data fixtures
- Monitor test execution times
- Update mock services to match real implementations
- Review coverage reports for gaps
- Update performance benchmarks

### Test Quality Metrics
- Test execution time trends
- Coverage percentage over time
- Test failure rates
- Performance benchmark results
- Code quality metrics

## Contributing to Tests

### Adding New Tests
1. Identify the appropriate test category (unit/integration/performance)
2. Create test file following naming conventions
3. Write tests following best practices
4. Ensure adequate coverage of new functionality
5. Update fixtures if needed
6. Run comprehensive test suite to ensure no regressions

### Modifying Existing Tests
1. Understand the purpose of existing tests
2. Maintain backward compatibility where possible
3. Update related fixtures and mock services
4. Verify coverage is maintained or improved
5. Update documentation if test behavior changes

## Resources

### Documentation
- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

### Tools
- **pytest**: Test framework
- **coverage**: Coverage measurement
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **pytest-xdist**: Parallel test execution
- **pytest-benchmark**: Performance benchmarking

### Support
For questions about the test suite:
1. Check this README
2. Review existing test examples
3. Check CI/CD pipeline logs
4. Consult team documentation
5. Ask in team channels