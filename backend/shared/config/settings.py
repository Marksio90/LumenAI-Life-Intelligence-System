"""
LumenAI Configuration Settings
Centralized configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Main application settings"""

    # Application
    APP_NAME: str = "LumenAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # API Settings
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = Field(default="change-me-in-production", env="SECRET_KEY")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )

    # LLM Providers
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    DEFAULT_LLM_PROVIDER: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")

    # Model Selection - Use CHEAP models by default!
    DEFAULT_MODEL: str = Field(default="gpt-4o-mini", env="DEFAULT_MODEL")  # 75x cheaper!
    SMART_MODEL: str = Field(default="gpt-4o", env="SMART_MODEL")  # For complex tasks
    FAST_MODEL: str = Field(default="gpt-3.5-turbo", env="FAST_MODEL")  # Ultra fast

    # Cost Control
    ENABLE_SMART_ROUTING: bool = Field(default=True, env="ENABLE_SMART_ROUTING")  # Auto-select model
    MAX_TOKENS_DEFAULT: int = Field(default=1000, env="MAX_TOKENS_DEFAULT")
    MAX_TOKENS_SMART: int = Field(default=2000, env="MAX_TOKENS_SMART")
    ENABLE_RESPONSE_CACHE: bool = Field(default=True, env="ENABLE_RESPONSE_CACHE")
    CACHE_TTL_SECONDS: int = Field(default=3600, env="CACHE_TTL_SECONDS")  # 1 hour

    # Vector Database
    CHROMA_HOST: str = Field(default="localhost", env="CHROMA_HOST")
    CHROMA_PORT: int = Field(default=8001, env="CHROMA_PORT")
    VECTOR_DB_PATH: str = Field(default="./backend/data/vectordb", env="VECTOR_DB_PATH")

    # Redis Cache
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")

    # MongoDB (User Data)
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017",
        env="MONGODB_URL"
    )
    MONGODB_DB_NAME: str = Field(default="lumenai", env="MONGODB_DB_NAME")

    # ML Settings
    ML_MODEL_PATH: str = Field(default="./backend/ml/models", env="ML_MODEL_PATH")
    ENABLE_PERSONALIZATION: bool = Field(default=True, env="ENABLE_PERSONALIZATION")

    # Multimodal Settings
    WHISPER_MODEL: str = Field(default="base", env="WHISPER_MODEL")
    ENABLE_VOICE: bool = Field(default=True, env="ENABLE_VOICE")
    ENABLE_VISION: bool = Field(default=True, env="ENABLE_VISION")
    ENABLE_OCR: bool = Field(default=True, env="ENABLE_OCR")

    # External Integrations
    GOOGLE_CALENDAR_ENABLED: bool = Field(default=False, env="GOOGLE_CALENDAR_ENABLED")
    NOTION_API_KEY: Optional[str] = Field(default=None, env="NOTION_API_KEY")
    GMAIL_ENABLED: bool = Field(default=False, env="GMAIL_ENABLED")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_PATH: str = Field(default="./backend/data/logs", env="LOG_PATH")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
