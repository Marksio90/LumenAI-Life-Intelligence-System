# LumenAI Backend Tests

## Overview

Comprehensive test suite for LumenAI backend with unit tests, integration tests, and CI/CD integration.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── unit/                    # Unit tests (fast, no external dependencies)
│   ├── test_auth_service.py
│   ├── test_rate_limit.py
│   └── ...
└── integration/             # Integration tests (requires services)
    ├── test_api_auth.py
    ├── test_api_endpoints.py
    └── ...
```

## Running Tests

### All Tests

```bash
cd backend
pytest
```

### Unit Tests Only

```bash
pytest tests/unit/
```

### Integration Tests Only

```bash
pytest tests/integration/
```

### With Coverage

```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Specific Test File

```bash
pytest tests/unit/test_auth_service.py
```

### Specific Test

```bash
pytest tests/unit/test_auth_service.py::TestPasswordHashing::test_hash_password
```

## Test Markers

Use markers to run specific test categories:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run auth-related tests
pytest -m auth

# Run all except slow tests
pytest -m "not slow"
```

## Writing Tests

### Unit Test Example

```python
import pytest
from services.auth_service import AuthService

class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        return AuthService(secret_key="test-key")

    def test_hash_password(self, auth_service):
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)
        assert hashed != password
```

### Async Test Example

```python
import pytest

class TestAsyncFunction:
    @pytest.mark.asyncio
    async def test_async_operation(self):
        result = await some_async_function()
        assert result == expected_value
```

### Integration Test Example

```python
import pytest
from httpx import AsyncClient

class TestAPIEndpoint:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_register_endpoint(self, test_client):
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPassword123"
            }
        )
        assert response.status_code == 200
```

## Test Coverage Goals

- **Overall**: >80%
- **Critical modules** (auth, security): >95%
- **API endpoints**: >90%
- **Business logic**: >85%

## CI/CD Integration

Tests run automatically on:
- Every push to `main`, `develop`, or `claude/*` branches
- Every pull request
- Before deployment to staging/production

### GitHub Actions Workflow

See `.github/workflows/ci.yml` for full CI/CD configuration.

## Fixtures

Common fixtures available in `conftest.py`:

- `auth_service` - Authentication service instance
- `sample_user_create` - Sample user registration data
- `sample_user_in_db` - Sample user from database
- `test_user_token` - Valid JWT token for testing
- `mock_llm_response` - Mock LLM response
- `mock_streaming_tokens` - Mock streaming tokens

## Best Practices

1. **Keep tests fast** - Unit tests should run in <1s
2. **Use fixtures** - Reuse common test data
3. **Test one thing** - Each test should verify one behavior
4. **Clear names** - Test names should describe what they test
5. **AAA pattern** - Arrange, Act, Assert
6. **Mock external services** - Don't call real APIs in tests
7. **Clean up** - Use fixtures for setup/teardown
8. **Mark appropriately** - Use markers for categorization

## Troubleshooting

### Tests fail with "No module named 'backend'"

Add parent directory to PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
```

### MongoDB/Redis connection errors

Ensure services are running:
```bash
docker-compose up -d mongodb redis
```

Or run only unit tests:
```bash
pytest tests/unit/
```

### Async tests fail

Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
