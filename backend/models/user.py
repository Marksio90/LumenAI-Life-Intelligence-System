"""
User Model - Authentication and User Management
Defines user schema for MongoDB with authentication support
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


# Common weak passwords to reject
COMMON_WEAK_PASSWORDS = {
    'password', 'password123', '123456', '12345678', 'qwerty', 'abc123',
    'monkey', '1234567', 'letmein', 'trustno1', 'dragon', 'baseball',
    'iloveyou', 'master', 'sunshine', 'ashley', 'bailey', 'shadow',
    'superman', 'qazwsx', 'michael', 'football', 'welcome', 'jesus',
    'ninja', 'mustang', 'password1', 'admin', 'admin123', 'root',
    'toor', 'pass', 'test', 'guest', 'info', 'adm', 'mysql', 'user',
    'administrator', 'oracle', 'ftp', 'pi', 'puppet', 'ansible',
    'ec2-user', 'vagrant', 'azureuser', 'admin@123', 'P@ssw0rd',
    'Password123', 'Welcome123', 'Changeme123', 'Qwerty123'
}


def validate_password_strength(password: str) -> str:
    """
    Reusable password strength validator

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not in common weak passwords list
    """
    # Check minimum length
    if len(password) < 12:
        raise ValueError(
            'Password must be at least 12 characters long. '
            'Current length: {} characters.'.format(len(password))
        )

    # Check for uppercase
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain at least one uppercase letter (A-Z)')

    # Check for lowercase
    if not re.search(r'[a-z]', password):
        raise ValueError('Password must contain at least one lowercase letter (a-z)')

    # Check for digit
    if not re.search(r'[0-9]', password):
        raise ValueError('Password must contain at least one digit (0-9)')

    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', password):
        raise ValueError(
            'Password must contain at least one special character '
            '(!@#$%^&*(),.?":{}|<>_-+=[]\\\/~`)'
        )

    # Check against common weak passwords
    password_lower = password.lower()
    if password_lower in COMMON_WEAK_PASSWORDS:
        raise ValueError(
            'This password is too common and easily guessable. '
            'Please choose a more unique password.'
        )

    # Check for sequential characters (e.g., "123456", "abcdef")
    if re.search(r'(012|123|234|345|456|567|678|789|abc|bcd|cde|def|efg)', password_lower):
        raise ValueError('Password should not contain sequential characters')

    # Check for repeated characters (e.g., "aaaa", "1111")
    if re.search(r'(.)\1{3,}', password):
        raise ValueError('Password should not contain more than 3 repeated characters')

    return password


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    full_name: Optional[str] = None

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        """Validate username is alphanumeric with underscores"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must be alphanumeric with underscores only')
        return v


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=12, description="Strong password (12+ chars, uppercase, lowercase, digit, special char)")

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        """Validate password strength using reusable validator"""
        return validate_password_strength(v)


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserInDB(UserBase):
    """User schema stored in database"""
    user_id: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    # Profile fields
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"

    # Usage tracking
    total_conversations: int = 0
    total_messages: int = 0

    # Settings
    preferences: dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123abc",
                "email": "user@example.com",
                "username": "john_doe",
                "full_name": "John Doe",
                "is_active": True,
                "is_verified": True,
                "created_at": "2025-12-04T10:00:00",
            }
        }


class UserPublic(UserBase):
    """Public user schema (no sensitive data)"""
    user_id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    total_conversations: int = 0
    total_messages: int = 0


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)
    timezone: Optional[str] = Field(None, pattern=r'^[A-Za-z_]+/[A-Za-z_]+$')  # e.g., "America/New_York"
    language: Optional[str] = Field(None, pattern=r'^[a-z]{2}$')  # e.g., "en", "pl"
    preferences: Optional[dict] = None


class UserPreferences(BaseModel):
    """Validated user preferences schema"""
    theme: Optional[str] = Field(None, pattern=r'^(light|dark|auto)$')
    language: Optional[str] = Field(None, pattern=r'^(en|pl|es|fr|de)$')
    timezone: Optional[str] = Field(None, pattern=r'^[A-Za-z_]+/[A-Za-z_]+$')
    compact_mode: Optional[bool] = None
    show_avatars: Optional[bool] = None
    animations_enabled: Optional[bool] = None

    class Config:
        extra = "forbid"  # Reject unknown fields


class NotificationSettings(BaseModel):
    """Validated notification settings schema"""
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    notification_frequency: Optional[str] = Field(None, pattern=r'^(immediate|hourly|daily|weekly)$')

    class Config:
        extra = "forbid"  # Reject unknown fields


class UserSettingsUpdate(BaseModel):
    """
    Schema for updating user settings

    Security: All fields are validated and unknown fields are rejected
    """
    preferences: Optional[UserPreferences] = None
    notifications: Optional[NotificationSettings] = None

    class Config:
        extra = "forbid"  # Reject unknown fields - prevents injection attacks
        json_schema_extra = {
            "example": {
                "preferences": {
                    "theme": "dark",
                    "language": "pl",
                    "compact_mode": False
                },
                "notifications": {
                    "email_notifications": True,
                    "push_notifications": False,
                    "notification_frequency": "daily"
                }
            }
        }


class PasswordChange(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: str = Field(..., min_length=12, description="Strong password (12+ chars, uppercase, lowercase, digit, special char)")

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        """Validate password strength using reusable validator"""
        return validate_password_strength(v)


class Token(BaseModel):
    """JWT token response schema"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Data extracted from JWT token"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    exp: Optional[int] = None
