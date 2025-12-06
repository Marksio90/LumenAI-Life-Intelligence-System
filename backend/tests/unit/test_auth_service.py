"""
Unit tests for Authentication Service
"""

import pytest
from datetime import datetime, timedelta

from services.auth_service import AuthService
from models.user import UserCreate, TokenData


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert hashed.startswith("$2b$")  # Bcrypt prefix

    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password."""
        password = "TestPassword123"
        wrong_password = "WrongPassword456"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(wrong_password, hashed) is False

    def test_password_hashing_unique(self, auth_service):
        """Test that same password generates different hashes (salt)."""
        password = "TestPassword123"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        assert hash1 != hash2  # Different salts
        assert auth_service.verify_password(password, hash1)
        assert auth_service.verify_password(password, hash2)


class TestUserIDGeneration:
    """Test user ID generation."""

    def test_generate_user_id(self, auth_service):
        """Test user ID generation."""
        email = "test@example.com"
        user_id = auth_service.generate_user_id(email)

        assert user_id.startswith("user_")
        assert len(user_id) == 17  # "user_" + 12 hex chars

    def test_generate_user_id_unique(self, auth_service):
        """Test that user IDs are unique."""
        email = "test@example.com"
        id1 = auth_service.generate_user_id(email)
        id2 = auth_service.generate_user_id(email)

        assert id1 != id2  # Should be unique due to timestamp + random


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self, auth_service):
        """Test access token creation."""
        user_id = "user_test123"
        email = "test@example.com"

        token = auth_service.create_access_token(user_id, email)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_create_refresh_token(self, auth_service):
        """Test refresh token creation."""
        user_id = "user_test123"
        email = "test@example.com"

        token = auth_service.create_refresh_token(user_id, email)

        assert isinstance(token, str)
        assert len(token) > 50

    def test_verify_token_valid(self, auth_service):
        """Test token verification with valid token."""
        user_id = "user_test123"
        email = "test@example.com"

        token = auth_service.create_access_token(user_id, email)
        token_data = auth_service.verify_token(token)

        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.email == email
        assert token_data.exp is not None

    def test_verify_token_invalid(self, auth_service):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"

        token_data = auth_service.verify_token(invalid_token)

        assert token_data is None

    def test_verify_token_expired(self, auth_service):
        """Test token verification with expired token."""
        user_id = "user_test123"
        email = "test@example.com"

        # Create token with negative expiry (already expired)
        token = auth_service.create_access_token(
            user_id,
            email,
            expires_delta=timedelta(seconds=-10)
        )

        token_data = auth_service.verify_token(token)

        assert token_data is None  # Expired tokens should fail verification

    def test_refresh_access_token_valid(self, auth_service):
        """Test refreshing access token with valid refresh token."""
        user_id = "user_test123"
        email = "test@example.com"

        refresh_token = auth_service.create_refresh_token(user_id, email)
        new_access_token = auth_service.refresh_access_token(refresh_token)

        assert new_access_token is not None
        assert isinstance(new_access_token, str)

        # Verify new token
        token_data = auth_service.verify_token(new_access_token)
        assert token_data.user_id == user_id
        assert token_data.email == email

    def test_refresh_access_token_invalid(self, auth_service):
        """Test refreshing with invalid refresh token."""
        invalid_token = "invalid.token.here"

        new_access_token = auth_service.refresh_access_token(invalid_token)

        assert new_access_token is None

    def test_refresh_with_access_token_fails(self, auth_service):
        """Test that access tokens cannot be used for refresh."""
        user_id = "user_test123"
        email = "test@example.com"

        # Try to use access token as refresh token
        access_token = auth_service.create_access_token(user_id, email)
        new_token = auth_service.refresh_access_token(access_token)

        assert new_token is None  # Should fail (wrong token type)


class TestUserCreation:
    """Test user creation from registration."""

    def test_create_user_from_registration(self, auth_service, sample_user_create):
        """Test creating UserInDB from registration data."""
        user = auth_service.create_user_from_registration(sample_user_create)

        assert user.email == sample_user_create.email
        assert user.username == sample_user_create.username
        assert user.full_name == sample_user_create.full_name
        assert user.user_id.startswith("user_")
        assert user.hashed_password != sample_user_create.password
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_superuser is False

    def test_password_is_hashed(self, auth_service, sample_user_create):
        """Test that password is properly hashed."""
        user = auth_service.create_user_from_registration(sample_user_create)

        # Password should be hashed
        assert user.hashed_password != sample_user_create.password
        assert user.hashed_password.startswith("$2b$")

        # Should be verifiable
        assert auth_service.verify_password(
            sample_user_create.password,
            user.hashed_password
        )
