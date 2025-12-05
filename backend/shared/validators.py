"""
Security validators for input sanitization and NoSQL injection prevention

These validators ensure user inputs are safe before they reach the database
"""

import re
from typing import Any
from fastapi import HTTPException, status


def validate_mongodb_id(value: Any, field_name: str = "id") -> str:
    """
    Validate that a value is a safe MongoDB ID string

    Prevents NoSQL injection by ensuring:
    - Value is a string
    - Contains only alphanumeric characters, underscores, and hyphens
    - No MongoDB operators ($ne, $gt, etc.)
    - No special characters that could be exploited

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)

    Returns:
        Validated string value

    Raises:
        HTTPException: If validation fails
    """
    # Check type
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a string, got {type(value).__name__}"
        )

    # Check length (reasonable bounds)
    if len(value) < 1 or len(value) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be between 1 and 100 characters"
        )

    # Check for MongoDB operators (NoSQL injection prevention)
    if value.startswith('$'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot start with '$' (potential NoSQL injection)"
        )

    # Check for only safe characters (alphanumeric, underscore, hyphen)
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} can only contain alphanumeric characters, underscores, and hyphens"
        )

    return value


def validate_mongodb_string(value: Any, field_name: str = "field", max_length: int = 1000) -> str:
    """
    Validate that a value is a safe string for MongoDB queries

    Prevents NoSQL injection and XSS by ensuring:
    - Value is a string
    - No MongoDB operators
    - Reasonable length
    - No executable code patterns

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        max_length: Maximum allowed length

    Returns:
        Validated string value

    Raises:
        HTTPException: If validation fails
    """
    # Check type
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a string"
        )

    # Check length
    if len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} exceeds maximum length of {max_length}"
        )

    # Check for MongoDB operators
    dangerous_patterns = ['$where', '$regex', '$ne', '$gt', '$lt', '$in', '$nin', '$or', '$and']
    value_lower = value.lower()
    for pattern in dangerous_patterns:
        if pattern in value_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} contains potentially dangerous pattern: {pattern}"
            )

    # Check for JavaScript/code injection attempts
    code_patterns = ['function', 'eval(', 'return', 'this.', 'db.', 'process.']
    for pattern in code_patterns:
        if pattern in value_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} contains potentially dangerous code pattern"
            )

    return value


def sanitize_mongodb_query_dict(query: dict) -> dict:
    """
    Sanitize a MongoDB query dictionary to prevent injection

    Removes or validates:
    - MongoDB operators from user-provided keys
    - Nested dictionaries with operators
    - JavaScript code in $where clauses

    Args:
        query: Query dictionary to sanitize

    Returns:
        Sanitized query dictionary
    """
    sanitized = {}

    for key, value in query.items():
        # Reject keys starting with $ (MongoDB operators)
        if key.startswith('$'):
            continue

        # Recursively sanitize nested dicts
        if isinstance(value, dict):
            # Don't allow nested operators in user input
            if any(k.startswith('$') for k in value.keys()):
                continue
            sanitized[key] = sanitize_mongodb_query_dict(value)
        elif isinstance(value, list):
            # Sanitize list items
            sanitized[key] = [
                sanitize_mongodb_query_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized
