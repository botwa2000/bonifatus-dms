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
    google_vision_monthly_limit: int = Field(
        default=950, description="Monthly Vision API request limit"
    )
    google_application_credentials: Optional[str] = Field(
        default=None, description="Service account key path"
    )

    # API rate limiting
    google_api_requests_per_minute: int = Field(
        default=100, description="API requests per minute limit"
    )
    google_api_requests_per_day: int = Field(
        default=10000, description="API requests per day limit"
    )

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class SecuritySettings(BaseSettings):
    """Security and authentication configuration"""

    # JWT configuration
    security_secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # Password requirements
    password_min_length: int = Field(default=12, description="Minimum password length")
    password_require_uppercase: bool = Field(
        default=True, description="Require uppercase in password"
    )
    password_require_lowercase: bool = Field(
        default=True, description="Require lowercase in password"
    )
    password_require_numbers: bool = Field(
        default=True, description="Require numbers in password"
    )
    password_require_symbols: bool = Field(
        default=True, description="Require symbols in password"
    )

    # Session security
    session_cookie_secure: bool = Field(default=True, description="Secure cookie flag")
    session_cookie_httponly: bool = Field(
        default=True, description="HTTP only cookie flag"
    )
    session_cookie_samesite: str = Field(
        default="lax", description="SameSite cookie attribute"
    )

    # Rate limiting
    rate_limit_requests_per_minute: int = Field(
        default=60, description="API rate limit per minute"
    )
    rate_limit_burst_size: int = Field(
        default=10, description="Rate limit burst allowance"
    )

    # CAPTCHA settings
    recaptcha_enabled: bool = Field(default=True, description="Enable reCAPTCHA")
    recaptcha_site_key: Optional[str] = Field(
        default=None, description="reCAPTCHA site key"
    )
    recaptcha_secret_key: Optional[str] = Field(
        default=None, description="reCAPTCHA secret key"
    )

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class ApplicationSettings(BaseSettings):
    """General application configuration"""

    # Application identification
    app_name: str = Field(default="Bonifatus DMS", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_description: str = Field(
        default="Professional Document Management System", description="App description"
    )

    # Environment
    app_environment: str = Field(
        default="development", description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    testing: bool = Field(default=False, description="Testing mode")

    # API configuration
    api_prefix: str = Field(default="/api/v1", description="API URL prefix")
    docs_url: Optional[str] = Field(
        default="/api/docs", description="API documentation URL"
    )
    redoc_url: Optional[str] = Field(
        default="/api/redoc", description="ReDoc documentation URL"
    )

    # CORS settings - using string that gets parsed to list
    cors_origins: str = Field(
        default="http://localhost:3000", description="Comma-separated CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow CORS credentials"
    )
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods",
    )
    cors_allow_headers: List[str] = Field(
        default=["*"], description="Allowed CORS headers"
    )

    # File processing
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    allowed_file_types: List[str] = Field(
        default=[
            ".pdf",
            ".doc",
            ".docx",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".tiff",
            ".bmp",
        ],
        description="Allowed file extensions",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )

    @validator("app_environment")
    def validate_environment(cls, v):
        allowed_environments = ["development", "staging", "production", "testing"]
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of: {allowed_environments}")
        return v

    @validator("cors_origins")
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins string into list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @validator("docs_url", "redoc_url")
    def disable_docs_in_production(cls, v, values):
        if values.get("app_environment") == "production":
            return None
        return v

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class Settings:
    """Main settings container combining all configuration sources"""

    def __init__(self):
        self.database = DatabaseSettings()
        self.google = GoogleSettings()
        self.security = SecuritySettings()
        self.app = ApplicationSettings()

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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
