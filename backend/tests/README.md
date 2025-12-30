# Bonifatus DMS Backend Tests

## Overview

This directory contains unit and integration tests for the Bonifatus DMS backend.

## Structure

```
tests/
├── conftest.py                    # Pytest configuration and shared fixtures
├── unit/                          # Unit tests (isolated, no external dependencies)
│   ├── core/                      # Core component tests
│   │   └── test_provider_registry.py
│   └── services/                  # Service layer tests
│       ├── test_provider_manager.py
│       └── test_provider_factory.py
└── integration/                   # Integration tests (database, external services)
    └── (future integration tests)
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock
```

### Run All Tests

```bash
# From backend directory
pytest

# With coverage report
pytest --cov=app --cov-report=html --cov-report=term
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Specific test file
pytest tests/unit/core/test_provider_registry.py

# Specific test class
pytest tests/unit/core/test_provider_registry.py::TestProviderRegistry

# Specific test method
pytest tests/unit/core/test_provider_registry.py::TestProviderRegistry::test_get_google_drive_provider
```

### Run with Markers

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only (slower, requires database)
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run with Verbose Output

```bash
pytest -v           # Verbose
pytest -vv          # Extra verbose
pytest -s           # Show print statements
```

## Test Coverage

View coverage report after running tests with coverage:
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

## Phase 1 Tests

Phase 1 unit tests cover the centralized provider management infrastructure:

1. **ProviderRegistry** (`test_provider_registry.py`)
   - Provider registration and lookup
   - Filtering by capabilities
   - Display name resolution
   - Metadata validation

2. **ProviderManager** (`test_provider_manager.py`)
   - Connection management
   - Token retrieval
   - Provider status checks
   - Connection info API responses

3. **ProviderFactory** (`test_provider_factory.py`)
   - Dynamic provider instantiation
   - Auto-registration from registry
   - Provider availability checks
   - Interface compliance

## Writing New Tests

### Unit Test Example

```python
import pytest
from app.services.my_service import MyService

class TestMyService:
    def test_my_function(self):
        result = MyService.my_function('input')
        assert result == 'expected'
```

### Integration Test Example

```python
import pytest
from sqlalchemy import create_engine
from app.database.models import User

@pytest.mark.integration
class TestDatabaseIntegration:
    def test_user_creation(self, db_session):
        user = User(email='test@example.com')
        db_session.add(user)
        db_session.commit()
        assert user.id is not None
```

## CI/CD Integration

Tests are designed to run in CI/CD pipelines. Add to your pipeline:

```yaml
test:
  script:
    - pip install -r requirements-test.txt
    - pytest --cov=app --cov-report=xml
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```
