"""
Authentication utilities for HTTP and WebSocket connections.

Integrates with the main authentication service for JWT validation.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from services.auth_service import get_auth_service
from services.user_repository import get_user_repository


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current authenticated user from HTTP request.

    Validates JWT token and returns user data.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract and verify token
        token = credentials.credentials
        auth_service = get_auth_service()
        token_data = auth_service.verify_token(token)

        if token_data is None or token_data.user_id is None:
            logger.warning("Invalid token: could not extract user_id")
            raise credentials_exception

        # Try to fetch user from database
        try:
            user_repo = get_user_repository()
            user = await user_repo.get_user_by_id(token_data.user_id)

            if user:
                if not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User account is inactive"
                    )
                return {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email
                }
        except Exception as e:
            logger.debug(f"User lookup failed, using token data: {e}")
            # Fallback to token data if user repo not available
            pass

        # Return token data if DB lookup failed (for backward compatibility)
        return {
            "user_id": token_data.user_id,
            "username": "user",
            "email": token_data.email
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception


async def get_current_user_ws(token: str = Query(...)) -> Dict[str, Any]:
    """
    Get current authenticated user from WebSocket connection.

    Validates JWT token and returns user data for WebSocket connections.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        # Verify token
        auth_service = get_auth_service()
        token_data = auth_service.verify_token(token)

        if token_data is None or token_data.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        # Try to fetch user from database
        try:
            user_repo = get_user_repository()
            user = await user_repo.get_user_by_id(token_data.user_id)

            if user:
                if not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User account is inactive"
                    )
                return {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email
                }
        except Exception as e:
            logger.debug(f"User lookup failed, using token data: {e}")
            pass

        # Return token data if DB lookup failed
        return {
            "user_id": token_data.user_id,
            "username": "user",
            "email": token_data.email
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
