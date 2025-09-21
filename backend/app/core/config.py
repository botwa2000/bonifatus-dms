# backend/src/core/config.py
"""
Bonifatus DMS - Configuration Management System
All settings loaded from environment variables and database
Zero hardcoded configuration values
"""

import logging
from functools import lru_cache
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration from environment variables"""
    
    database_url: str = Field(..., description="Supabase PostgreSQL connection URL")
    database_pool_size: int = Field(default=5, description="Connection pool size")
    database_pool_recycle: int = Field(default=3600, description="Pool recycle time")
    database_echo: bool = Field(default=False, description="Enable SQL query logging")
    database_pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    database_connect_timeout: int = Field(default=30, description="Connection timeout")

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class GoogleSettings(BaseSettings):
    """Google services configuration"""
    
    google_client_id: str = Field(..., description="Google OAuth client ID")
    google_client_secret: str = Field(..., description="Google OAuth client secret")
    google_redirect_uri: str = Field(default="", description="OAuth redirect URI")
    google_vision_enabled: bool = Field(default=True, description="Enable Google Vision OCR")
    google_oauth_issuers: str = Field(default="accounts.google.com,https://accounts.google.com", description="Valid OAuth issuers")

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class SecuritySettings(BaseSettings):
    """Security configuration from environment variables"""
    
    security_secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="JWT expiration")
    refresh_token_expire_days: int = Field(default=30, description="Refresh token expiration")
    default_user_tier: str = Field(default="free", description="Default user tier")
    admin_emails: str = Field(default="admin@bonifatus.com", description="Admin email list")

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class AppSettings(BaseSettings):
    """Application configuration from environment variables"""
    
    app_environment: str = Field(default="development", description="Environment")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    cors_origins: str = Field(default="http://localhost:3000", description="CORS origins")
    port: int = Field(default=8000, description="Application port")

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class Settings(BaseSettings):
    """Complete application settings with modular structure"""
    
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info(f"Configuration loaded for environment: {self.app.app_environment}")

    @property
    def is_production(self) -> bool:
        return self.app.app_environment == "production"

    @property
    def is_development(self) -> bool:
        return self.app.app_environment == "development"
    
    @property
    def admin_email_list(self) -> List[str]:
        """Get admin emails as list"""
        return [email.strip() for email in self.security.admin_emails.split(",")]
    
    @property
    def google_oauth_issuer_list(self) -> List[str]:
        """Get Google OAuth issuers as list"""
        return [issuer.strip() for issuer in self.google.google_oauth_issuers.split(",")]

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