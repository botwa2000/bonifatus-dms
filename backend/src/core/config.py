# backend/src/core/config.py
"""
Bonifatus DMS - Configuration Management System
All settings loaded from environment variables and database
Zero hardcoded configuration values
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Dict, Any, Optional
from functools import lru_cache
import os
import logging

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration from environment variables"""

    # Supabase PostgreSQL connection
    database_url: str = Field(..., description="Supabase PostgreSQL connection URL")
    database_pool_size: int = Field(
        default=5, description="Database connection pool size"
    )
    database_pool_recycle: int = Field(
        default=3600, description="Pool recycle time in seconds"
    )
    database_echo: bool = Field(default=False, description="Enable SQL query logging")

    # Connection health checks
    database_pool_pre_ping: bool = Field(
        default=True, description="Enable connection health checks"
    )
    database_connect_timeout: int = Field(
        default=30, description="Database connection timeout"
    )

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class GoogleSettings(BaseSettings):
    """Google services configuration"""

    # OAuth 2.0 configuration
    google_client_id: str = Field(..., description="Google OAuth client ID")
    google_client_secret: str = Field(..., description="Google OAuth client secret")
    google_redirect_uri: str = Field(default="", description="OAuth redirect URI")

    # Google Drive API settings
    google_drive_scopes: List[str] = Field(
        default=["https://www.googleapis.com/auth/drive.file"],
        description="Google Drive API scopes",
    )

    # Google Cloud Vision API (for OCR)
    google_vision_enabled: bool = Field(
        default=True, description="Enable Google Vision OCR"
    )

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class SecuritySettings(BaseSettings):
    """Security configuration from environment variables"""

    # JWT Configuration
    security_secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="JWT access token expiration time"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="JWT refresh token expiration time"
    )

    # Password Configuration
    password_min_length: int = Field(default=8, description="Minimum password length")
    password_require_special: bool = Field(
        default=True, description="Require special characters in passwords"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100, description="Rate limit requests per minute"
    )
    rate_limit_burst: int = Field(default=200, description="Rate limit burst size")

    @property
    def secret_key(self) -> str:
        """Backward compatibility property for secret_key access"""
        return self.security_secret_key

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class AppSettings(BaseSettings):
    """Application configuration from environment variables"""

    # Application Identity
    app_name: str = Field(default="Bonifatus DMS", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_description: str = Field(
        default="Professional Document Management System",
        description="Application description",
    )

    # Environment Configuration
    app_environment: str = Field(default="development", description="Environment")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    testing: bool = Field(default=False, description="Testing mode")

    # API Configuration
    api_prefix: str = Field(default="/api/v1", description="API URL prefix")
    docs_url: Optional[str] = Field(default="/docs", description="OpenAPI docs URL")
    redoc_url: Optional[str] = Field(default="/redoc", description="ReDoc URL")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000,https://bonifatus-dms-*.run.app",
        description="CORS allowed origins",
    )
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH"],
        description="CORS allowed methods",
    )

    # File Upload Configuration
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    allowed_file_types: List[str] = Field(
        default=[".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg"],
        description="Allowed file extensions",
    )

    # Internationalization
    default_language: str = Field(default="en", description="Default language")
    supported_languages: List[str] = Field(
        default=["en", "de"], description="Supported languages"
    )

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class CacheSettings(BaseSettings):
    """Cache configuration from environment variables"""

    # Redis Configuration (optional)
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    cache_ttl_seconds: int = Field(default=3600, description="Default cache TTL")

    # In-memory cache settings
    memory_cache_size: int = Field(default=1000, description="In-memory cache max size")

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class Settings(BaseSettings):
    """Complete application settings with modular structure"""

    # Modular configuration sections
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info(f"Configuration loaded for environment: {self.app.app_environment}")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.app.app_environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.app.app_environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.app.app_environment == "testing" or self.app.testing

    # Convenience properties for clean API access
    @property
    def environment(self) -> str:
        """Convenience property for environment access"""
        return self.app.app_environment

    @property
    def cors_origins(self) -> List[str]:
        """Convenience property for CORS origins as a list"""
        if isinstance(self.app.cors_origins, str):
            return [
                origin.strip()
                for origin in self.app.cors_origins.split(",")
                if origin.strip()
            ]
        return self.app.cors_origins if isinstance(self.app.cors_origins, list) else []

    @property
    def secret_key(self) -> str:
        """Convenience property for JWT secret key"""
        return self.security.security_secret_key

    @property
    def database_url(self) -> str:
        """Convenience property for database URL"""
        return self.database.database_url

    @property
    def docs_url(self) -> Optional[str]:
        """Convenience property for API docs URL"""
        return self.app.docs_url if not self.is_production else None

    @property
    def redoc_url(self) -> Optional[str]:
        """Convenience property for ReDoc URL"""
        return self.app.redoc_url if not self.is_production else None

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
