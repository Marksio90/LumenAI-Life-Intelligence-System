"""
Structured Logging Configuration for LumenAI
Advanced logging with Loguru for better observability
"""

import sys
import json
from pathlib import Path
from loguru import logger
from typing import Optional
from datetime import datetime

from shared.config.settings import settings


def serialize_record(record: dict) -> str:
    """
    Serialize log record to JSON format.

    Useful for log aggregation systems like ELK, Splunk, etc.
    """
    subset = {
        "timestamp": record["time"].timestamp(),
        "time": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }

    # Add extra fields if present
    if record.get("extra"):
        subset["extra"] = record["extra"]

    # Add exception info if present
    if record.get("exception"):
        subset["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback
        }

    return json.dumps(subset)


def patching(record: dict):
    """
    Patch log record with additional context.

    Adds request ID, user ID, etc. for better tracing.
    """
    # Extract extra fields from record
    extra = record.get("extra", {})

    # Add request context if available
    record["extra"]["request_id"] = extra.get("request_id", "N/A")
    record["extra"]["user_id"] = extra.get("user_id", "N/A")
    record["extra"]["endpoint"] = extra.get("endpoint", "N/A")


def configure_logging(
    level: str = None,
    log_file: bool = True,
    json_logs: bool = False,
    rotation: str = "500 MB",
    retention: str = "10 days"
):
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Whether to log to file
        json_logs: Whether to output JSON formatted logs
        rotation: When to rotate log files (size or time)
        retention: How long to keep old log files

    Example:
        configure_logging(level="INFO", log_file=True, json_logs=False)
    """

    # Remove default handler
    logger.remove()

    # Determine log level
    log_level = level or settings.LOG_LEVEL

    # Console handler with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    if log_file:
        # Ensure log directory exists
        log_dir = Path(settings.LOG_PATH)
        log_dir.mkdir(parents=True, exist_ok=True)

        if json_logs:
            # JSON formatted logs for log aggregation
            logger.add(
                log_dir / "lumenai_{time:YYYY-MM-DD}.json",
                format=serialize_record,
                level=log_level,
                rotation=rotation,
                retention=retention,
                compression="zip",
                serialize=True
            )
        else:
            # Human-readable logs
            logger.add(
                log_dir / "lumenai_{time:YYYY-MM-DD}.log",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level=log_level,
                rotation=rotation,
                retention=retention,
                compression="zip",
                backtrace=True,
                diagnose=True
            )

        # Separate error log file
        logger.add(
            log_dir / "lumenai_errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True
        )

    logger.info(f"✅ Logging configured - Level: {log_level}, File: {log_file}, JSON: {json_logs}")


def get_logger_with_context(
    name: str,
    **context
):
    """
    Get logger with additional context.

    Args:
        name: Logger name (usually __name__)
        **context: Additional context to bind to logger

    Returns:
        Logger with bound context

    Example:
        log = get_logger_with_context(__name__, user_id="user_123", request_id="req_456")
        log.info("User logged in")
    """
    return logger.bind(module=name, **context)


# ============================================================================
# LOGGING DECORATORS
# ============================================================================

def log_execution_time(func_name: Optional[str] = None):
    """
    Decorator to log function execution time.

    Example:
        @log_execution_time("process_message")
        async def process_message(message):
            ...
    """
    import functools
    import time

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            name = func_name or func.__name__

            logger.debug(f"Starting {name}")

            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time

                logger.info(
                    f"Completed {name} in {elapsed:.2f}s",
                    extra={"function": name, "elapsed_time": elapsed}
                )

                return result

            except Exception as e:
                elapsed = time.time() - start_time

                logger.error(
                    f"Failed {name} after {elapsed:.2f}s: {str(e)}",
                    extra={"function": name, "elapsed_time": elapsed, "error": str(e)}
                )

                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            name = func_name or func.__name__

            logger.debug(f"Starting {name}")

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                logger.info(
                    f"Completed {name} in {elapsed:.2f}s",
                    extra={"function": name, "elapsed_time": elapsed}
                )

                return result

            except Exception as e:
                elapsed = time.time() - start_time

                logger.error(
                    f"Failed {name} after {elapsed:.2f}s: {str(e)}",
                    extra={"function": name, "elapsed_time": elapsed, "error": str(e)}
                )

                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_api_call(endpoint: str):
    """
    Decorator to log API calls.

    Example:
        @app.get("/api/endpoint")
        @log_api_call("/api/endpoint")
        async def endpoint():
            ...
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(
                f"API Call: {endpoint}",
                extra={"endpoint": endpoint}
            )

            try:
                result = await func(*args, **kwargs)
                logger.debug(f"API Success: {endpoint}")
                return result

            except Exception as e:
                logger.error(
                    f"API Error: {endpoint} - {str(e)}",
                    extra={"endpoint": endpoint, "error": str(e)}
                )
                raise

        return wrapper

    return decorator


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

class RequestLoggingMiddleware:
    """
    Middleware to log all HTTP requests.

    Adds request ID and logs request/response details.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, request, call_next):
        import uuid
        from time import time

        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown"
            }
        )

        start_time = time()

        # Process request
        response = await call_next(request)

        # Log response
        elapsed = time() - start_time

        logger.info(
            f"Response: {request.method} {request.url.path} - {response.status_code} ({elapsed:.2f}s)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_time": elapsed
            }
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
