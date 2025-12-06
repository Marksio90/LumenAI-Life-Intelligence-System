"""
Authentication Service - JWT and Password Management
Handles user authentication, JWT token generation, and password hashing
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext
from loguru import logger

from models.user import UserInDB, UserCreate, TokenData
from shared.config.settings import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days


class AuthService:
    """
    Authentication service for user management and JWT tokens.

    Features:
    - Password hashing with bcrypt
    - JWT token generation and validation
    - Refresh token support
    - Secure user ID generation
    """

    def __init__(self, secret_key: str = None):
        """
        Initialize authentication service.

        Args:
            secret_key: Secret key for JWT signing (defaults to settings.SECRET_KEY)
        """
        self.secret_key = secret_key or settings.SECRET_KEY
        if self.secret_key == "change-me-in-production":
            logger.warning("⚠️  Using default SECRET_KEY! Set SECRET_KEY in production!")

    # ============================================================================
    # PASSWORD HASHING
    # ============================================================================

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    # ============================================================================
    # USER ID GENERATION
    # ============================================================================

    @staticmethod
    def generate_user_id(email: str) -> str:
        """
        Generate a unique, deterministic user ID from email.

        Uses SHA-256 hash + random suffix for uniqueness.

        Args:
            email: User's email address

        Returns:
            Unique user ID (e.g., "user_a3f8b2c1d5e9")
        """
        # Create hash of email + timestamp + random bytes
        hash_input = f"{email}_{datetime.utcnow().isoformat()}_{secrets.token_hex(8)}"
        hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
        return f"user_{hash_digest}"

    # ============================================================================
    # JWT TOKEN MANAGEMENT
    # ============================================================================

    def create_access_token(
        self,
        user_id: str,
        email: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User's unique ID
            email: User's email
            expires_delta: Optional custom expiration time

        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=ALGORITHM)
        return encoded_jwt

    def create_refresh_token(
        self,
        user_id: str,
        email: str
    ) -> str:
        """
        Create a JWT refresh token (longer expiration).

        Args:
            user_id: User's unique ID
            email: User's email

        Returns:
            JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])

            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            exp: int = payload.get("exp")

            if user_id is None or email is None:
                logger.warning("Invalid token payload: missing user_id or email")
                return None

            return TokenData(user_id=user_id, email=email, exp=exp)

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Generate a new access token from a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if refresh token is valid, None otherwise
        """
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[ALGORITHM])

            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                logger.warning("Token is not a refresh token")
                return None

            user_id: str = payload.get("sub")
            email: str = payload.get("email")

            if user_id is None or email is None:
                return None

            # Create new access token
            return self.create_access_token(user_id, email)

        except JWTError as e:
            logger.warning(f"Refresh token verification failed: {e}")
            return None

    # ============================================================================
    # USER CREATION HELPERS
    # ============================================================================

    def create_user_from_registration(self, user_create: UserCreate) -> UserInDB:
        """
        Create a UserInDB object from registration data.

        Args:
            user_create: User registration data

        Returns:
            UserInDB object ready to be stored
        """
        user_id = self.generate_user_id(user_create.email)
        hashed_password = self.hash_password(user_create.password)

        user_in_db = UserInDB(
            user_id=user_id,
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,  # Can add email verification later
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        return user_in_db


# ============================================================================
# GLOBAL AUTH SERVICE INSTANCE
# ============================================================================

_auth_service: Optional[AuthService] = None


def init_auth_service(secret_key: str = None) -> AuthService:
    """
    Initialize the global authentication service.

    Args:
        secret_key: Optional secret key for JWT signing

    Returns:
        Initialized AuthService instance
    """
    global _auth_service
    _auth_service = AuthService(secret_key=secret_key)
    logger.info("✅ Authentication Service initialized")
    return _auth_service


def get_auth_service() -> AuthService:
    """
    Get the global authentication service instance.

    Returns:
        AuthService instance

    Raises:
        RuntimeError: If service not initialized
    """
    if _auth_service is None:
        # Auto-initialize with default settings
        return init_auth_service()
    return _auth_service
