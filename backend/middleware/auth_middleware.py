"""
Authentication Middleware - JWT Verification and User Dependencies
FastAPI dependencies for authentication and authorization
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from models.user import UserInDB, TokenData
from services.auth_service import get_auth_service
from services.user_repository import get_user_repository


# HTTP Bearer token scheme
security = HTTPBearer()


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInDB:
    """
    Dependency to get current authenticated user from JWT token.

    Extracts and validates JWT token from Authorization header.
    Fetches user from database and verifies they're active.

    Args:
        credentials: HTTP Bearer token from request header

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found/inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract token from credentials
        token = credentials.credentials

        # Verify token
        auth_service = get_auth_service()
        token_data: Optional[TokenData] = auth_service.verify_token(token)

        if token_data is None or token_data.user_id is None:
            logger.warning("Invalid token: could not extract user_id")
            raise credentials_exception

        # Fetch user from database
        user_repo = get_user_repository()
        if user_repo is None:
            logger.error("User repository not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

        user = await user_repo.get_user_by_id(token_data.user_id)

        if user is None:
            logger.warning(f"User not found: {token_data.user_id}")
            raise credentials_exception

        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user_from_token)
) -> UserInDB:
    """
    Dependency to get current active user.

    Additional layer to ensure user is active.

    Args:
        current_user: User from token validation

    Returns:
        Active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


async def get_current_verified_user(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """
    Dependency to get current verified user.

    Requires user to have verified email.

    Args:
        current_user: Active user from previous dependency

    Returns:
        Verified user

    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


async def get_current_superuser(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """
    Dependency to get current superuser.

    Requires user to have superuser privileges.

    Args:
        current_user: Active user from previous dependency

    Returns:
        Superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Superuser access required."
        )
    return current_user


# ============================================================================
# OPTIONAL AUTHENTICATION (for public endpoints with optional auth)
# ============================================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserInDB]:
    """
    Dependency to get current user if authenticated, None otherwise.

    Useful for endpoints that work for both authenticated and anonymous users.

    Args:
        credentials: Optional HTTP Bearer token

    Returns:
        User if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await get_current_user_from_token(credentials)
    except HTTPException:
        # Invalid token, treat as anonymous
        return None


# ============================================================================
# RATE LIMITING HELPERS
# ============================================================================

def check_rate_limit(user: UserInDB) -> None:
    """
    Check if user has exceeded rate limits.

    Args:
        user: User to check

    Raises:
        HTTPException: If rate limit exceeded

    Note:
        This is a placeholder. Implement with Redis or similar in production.
    """
    # TODO: Implement actual rate limiting with Redis
    # For now, just a placeholder

    # Example implementation would check:
    # - Requests per minute
    # - Requests per hour
    # - Requests per day
    # Based on user tier/subscription

    pass


# ============================================================================
# PERMISSION HELPERS
# ============================================================================

def require_permission(permission: str):
    """
    Dependency factory to require specific permission.

    Args:
        permission: Permission name required

    Returns:
        FastAPI dependency function

    Example:
        @app.get("/admin/users", dependencies=[Depends(require_permission("admin:users:read"))])
    """
    async def permission_checker(current_user: UserInDB = Depends(get_current_active_user)):
        # Check if user has permission
        user_permissions = current_user.preferences.get("permissions", [])

        if permission not in user_permissions and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )

        return current_user

    return permission_checker
