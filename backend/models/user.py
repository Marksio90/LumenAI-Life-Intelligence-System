"""
User Model - Authentication and User Management
Defines user schema for MongoDB with authentication support
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


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
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


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
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[dict] = None


class PasswordChange(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


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
