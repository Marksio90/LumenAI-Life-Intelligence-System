"""
Error Handling Middleware for FastAPI
Centralized error handling with structured responses
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from loguru import logger
from typing import Union
import traceback
from datetime import datetime

from core.exceptions import LumenAIException


class ErrorHandlingMiddleware:
    """
    Middleware to catch and handle all exceptions.

    Provides consistent error responses across the API.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        """Process request and handle any exceptions."""
        try:
            response = await call_next(request)
            return response

        except LumenAIException as exc:
            # Handle custom LumenAI exceptions
            return await self.handle_lumenai_exception(request, exc)

        except StarletteHTTPException as exc:
            # Handle FastAPI/Starlette HTTP exceptions
            return await self.handle_http_exception(request, exc)

        except RequestValidationError as exc:
            # Handle validation errors
            return await self.handle_validation_error(request, exc)

        except Exception as exc:
            # Handle unexpected exceptions
            return await self.handle_unexpected_exception(request, exc)

    async def handle_lumenai_exception(
        self,
        request: Request,
        exc: LumenAIException
    ) -> JSONResponse:
        """Handle custom LumenAI exceptions."""

        # Log the error
        logger.warning(
            f"LumenAI Exception: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "details": exc.details
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        )

    async def handle_http_exception(
        self,
        request: Request,
        exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""

        logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        )

    async def handle_validation_error(
        self,
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""

        # Extract validation errors
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        logger.warning(
            f"Validation Error: {len(errors)} field(s) failed validation",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": errors
            }
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        )

    async def handle_unexpected_exception(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""

        # Log full traceback for unexpected errors
        error_id = f"ERR_{datetime.utcnow().timestamp()}"
        tb = traceback.format_exc()

        logger.error(
            f"Unexpected Exception [{error_id}]: {str(exc)}",
            extra={
                "error_id": error_id,
                "exception_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
                "traceback": tb
            }
        )

        # In production, don't expose internal error details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "error_id": error_id,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        )


# ============================================================================
# EXCEPTION HANDLERS (Alternative to Middleware)
# ============================================================================

async def lumenai_exception_handler(request: Request, exc: LumenAIException):
    """Exception handler for LumenAI exceptions."""
    logger.warning(
        f"LumenAI Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Exception handler for validation errors."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation Error: {len(errors)} field(s) failed validation",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors
        }
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Exception handler for HTTP exceptions."""
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )


async def unexpected_exception_handler(request: Request, exc: Exception):
    """Exception handler for unexpected exceptions."""
    error_id = f"ERR_{datetime.utcnow().timestamp()}"
    tb = traceback.format_exc()

    logger.error(
        f"Unexpected Exception [{error_id}]: {str(exc)}",
        extra={
            "error_id": error_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "traceback": tb
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app.

    Usage:
        from middleware.error_middleware import register_exception_handlers
        register_exception_handlers(app)
    """
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app.add_exception_handler(LumenAIException, lumenai_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)

    logger.info("✅ Exception handlers registered")
