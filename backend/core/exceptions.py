"""
Custom Exception Classes for LumenAI
Structured error handling with detailed context
"""

from typing import Optional, Dict, Any
from fastapi import status


class LumenAIException(Exception):
    """
    Base exception for all LumenAI errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details
        }


# ============================================================================
# AUTHENTICATION ERRORS
# ============================================================================

class AuthenticationError(LumenAIException):
    """Base class for authentication errors."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password."""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Invalid email or password",
            details=details
        )
        self.error_code = "INVALID_CREDENTIALS"


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Token has expired. Please login again.",
            details=details
        )
        self.error_code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    """JWT token is invalid."""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Invalid token. Please login again.",
            details=details
        )
        self.error_code = "INVALID_TOKEN"


class InactiveAccountError(AuthenticationError):
    """User account is inactive."""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Account is inactive. Please contact support.",
            details=details
        )
        self.status_code = status.HTTP_403_FORBIDDEN
        self.error_code = "ACCOUNT_INACTIVE"


class UnverifiedAccountError(AuthenticationError):
    """User email is not verified."""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Email not verified. Please check your email for verification link.",
            details=details
        )
        self.status_code = status.HTTP_403_FORBIDDEN
        self.error_code = "EMAIL_UNVERIFIED"


# ============================================================================
# AUTHORIZATION ERRORS
# ============================================================================

class AuthorizationError(LumenAIException):
    """Base class for authorization errors."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class InsufficientPermissionsError(AuthorizationError):
    """User lacks required permissions."""

    def __init__(self, required_permission: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Insufficient permissions. Required: {required_permission}",
            details={**(details or {}), "required_permission": required_permission}
        )
        self.error_code = "INSUFFICIENT_PERMISSIONS"


class SuperuserRequiredError(AuthorizationError):
    """Action requires superuser privileges."""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Superuser access required",
            details=details
        )
        self.error_code = "SUPERUSER_REQUIRED"


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class ValidationError(LumenAIException):
    """Base class for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        details = details or {}
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details
        )


class InvalidEmailError(ValidationError):
    """Invalid email format."""

    def __init__(self, email: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Invalid email format: {email}",
            field="email",
            details=details
        )
        self.error_code = "INVALID_EMAIL"


class WeakPasswordError(ValidationError):
    """Password does not meet strength requirements."""

    def __init__(self, requirements: list, details: Optional[Dict] = None):
        super().__init__(
            message="Password does not meet requirements",
            field="password",
            details={**(details or {}), "requirements": requirements}
        )
        self.error_code = "WEAK_PASSWORD"


class InvalidUsernameError(ValidationError):
    """Invalid username format."""

    def __init__(self, username: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Invalid username: {username}. Must be alphanumeric with underscores.",
            field="username",
            details=details
        )
        self.error_code = "INVALID_USERNAME"


# ============================================================================
# RESOURCE ERRORS
# ============================================================================

class ResourceError(LumenAIException):
    """Base class for resource-related errors."""
    pass


class ResourceNotFoundError(ResourceError):
    """Requested resource not found."""

    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={**(details or {}), "resource_type": resource_type, "resource_id": resource_id}
        )


class ResourceAlreadyExistsError(ResourceError):
    """Resource already exists."""

    def __init__(self, resource_type: str, identifier: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"{resource_type} already exists: {identifier}",
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_EXISTS",
            details={**(details or {}), "resource_type": resource_type, "identifier": identifier}
        )


class ResourceConflictError(ResourceError):
    """Resource operation conflicts with current state."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            details=details
        )


# ============================================================================
# RATE LIMITING ERRORS
# ============================================================================

class RateLimitError(LumenAIException):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int, limit: int, window: int, details: Optional[Dict] = None):
        super().__init__(
            message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={
                **(details or {}),
                "retry_after": retry_after,
                "limit": limit,
                "window": window
            }
        )


# ============================================================================
# SERVICE ERRORS
# ============================================================================

class ServiceError(LumenAIException):
    """Base class for service errors."""

    def __init__(self, service_name: str, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"{service_name} error: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_ERROR",
            details={**(details or {}), "service": service_name}
        )


class DatabaseError(ServiceError):
    """Database operation failed."""

    def __init__(self, operation: str, details: Optional[Dict] = None):
        super().__init__(
            service_name="Database",
            message=f"Operation failed: {operation}",
            details=details
        )
        self.error_code = "DATABASE_ERROR"


class LLMError(ServiceError):
    """LLM API error."""

    def __init__(self, provider: str, message: str, details: Optional[Dict] = None):
        super().__init__(
            service_name=f"LLM ({provider})",
            message=message,
            details=details
        )
        self.error_code = "LLM_ERROR"


class CacheError(ServiceError):
    """Cache operation failed."""

    def __init__(self, operation: str, details: Optional[Dict] = None):
        super().__init__(
            service_name="Cache",
            message=f"Operation failed: {operation}",
            details=details
        )
        self.error_code = "CACHE_ERROR"


# ============================================================================
# EXTERNAL API ERRORS
# ============================================================================

class ExternalAPIError(LumenAIException):
    """External API call failed."""

    def __init__(self, api_name: str, status_code: int, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"{api_name} API error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_API_ERROR",
            details={
                **(details or {}),
                "api_name": api_name,
                "api_status_code": status_code
            }
        )


# ============================================================================
# BUSINESS LOGIC ERRORS
# ============================================================================

class BusinessLogicError(LumenAIException):
    """Business logic validation failed."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BUSINESS_LOGIC_ERROR",
            details=details
        )


class InsufficientQuotaError(BusinessLogicError):
    """User has insufficient quota."""

    def __init__(self, quota_type: str, current: int, required: int, details: Optional[Dict] = None):
        super().__init__(
            message=f"Insufficient {quota_type} quota. Required: {required}, Available: {current}",
            details={
                **(details or {}),
                "quota_type": quota_type,
                "current": current,
                "required": required
            }
        )
        self.error_code = "INSUFFICIENT_QUOTA"


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigurationError(LumenAIException):
    """Configuration is invalid or missing."""

    def __init__(self, config_key: str, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Configuration error ({config_key}): {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CONFIGURATION_ERROR",
            details={**(details or {}), "config_key": config_key}
        )
