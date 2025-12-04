"""
Pytest configuration and fixtures for LumenAI tests
"""

import pytest
import asyncio
from typing import AsyncGenerator
from datetime import datetime

# Fixtures for authentication testing
from backend.services.auth_service import AuthService
from backend.models.user import UserCreate, UserInDB


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def auth_service():
    """Create auth service instance for testing."""
    return AuthService(secret_key="test-secret-key-minimum-32-characters-long")


@pytest.fixture
def sample_user_create():
    """Sample user creation data."""
    return UserCreate(
        email="test@example.com",
        username="testuser",
        password="TestPassword123",
        full_name="Test User"
    )


@pytest.fixture
def sample_user_in_db():
    """Sample user in database."""
    return UserInDB(
        user_id="user_test123",
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="$2b$12$hashed_password_here",
        is_active=True,
        is_verified=True,
        is_superuser=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


# Mock data for testing
@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return "This is a mock LLM response for testing purposes."


@pytest.fixture
def mock_streaming_tokens():
    """Mock streaming tokens for testing."""
    return ["Hello", " ", "world", "!", " ", "This", " ", "is", " ", "streaming", "."]


# Test client fixtures
@pytest.fixture
async def test_user_token(auth_service, sample_user_in_db):
    """Generate test JWT token."""
    return auth_service.create_access_token(
        user_id=sample_user_in_db.user_id,
        email=sample_user_in_db.email
    )
