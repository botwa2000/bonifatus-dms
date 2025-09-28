# backend/app/core/config.py
import logging
import os
from functools import lru_cache
from typing import List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration from environment variables"""
    
    database_url: str = Field(..., description="Database connection URL")
    database_pool_size: int = Field(..., description="Connection pool size")
    database_pool_recycle: int = Field(..., description="Pool recycle time")
    database_echo: bool = Field(..., description="Enable SQL query logging")
    database_pool_pre_ping: bool = Field(..., description="Enable connection health checks")
    database_connect_timeout: int = Field(..., description="Connection timeout")

    class Config:
        case_sensitive = False
        extra = "ignore"


class GoogleSettings(BaseSettings):
    """Google services configuration"""
    
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID", description="Google OAuth client ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET", description="Google OAuth client secret")
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI", description="OAuth redirect URI")
    google_vision_enabled: bool = Field(..., description="Enable Google Vision OCR")
    google_oauth_issuers: str = Field(..., description="Valid OAuth issuers")
    google_drive_service_account_key: str = Field(..., description="Google Drive service account key file path")
    google_drive_folder_name: str = Field(..., description="Google Drive folder name for documents")
    google_project_id: str = Field(..., alias="GCP_PROJECT", description="Google Cloud Project ID")

    class Config:
        case_sensitive = False
        extra = "ignore"


class SecuritySettings(BaseSettings):
    """Security configuration from environment variables"""
    
    security_secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(..., description="JWT algorithm")
    access_token_expire_minutes: int = Field(..., description="JWT expiration")
    refresh_token_expire_days: int = Field(..., description="Refresh token expiration")
    default_user_tier: str = Field(..., description="Default user tier")
    admin_emails: str = Field(..., description="Admin email list")

    class Config:
        case_sensitive = False
        extra = "ignore"


class AppSettings(BaseSettings):
    """Application configuration from environment variables"""
    
    app_environment: str = Field(..., description="Environment")
    app_debug_mode: bool = Field(..., description="Enable debug mode")
    app_cors_origins: str = Field(..., description="CORS origins")
    app_host: str = Field(..., description="Application host")
    app_port: int = Field(..., description="Application port")
    app_title: str = Field(..., description="Application title")
    app_description: str = Field(..., description="Application description")
    app_version: str = Field(..., description="Application version")

    class Config:
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
    def is_staging(self) -> bool:
        return self.app.app_environment == "staging"
    
    @property
    def admin_email_list(self) -> List[str]:
        """Get admin emails as list"""
        return [email.strip() for email in self.security.admin_emails.split(",")]
    
    @property
    def google_oauth_issuer_list(self) -> List[str]:
        """Get Google OAuth issuers as list"""
        return [issuer.strip() for issuer in self.google.google_oauth_issuers.split(",")]

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list"""
        return [origin.strip() for origin in self.app.app_cors_origins.split(",")]

    class Config:
        case_sensitive = False
        extra = "ignore"


def get_settings() -> Settings:
    """Get settings instance without caching to ensure fresh environment variable reads"""
    return Settings()


# Global settings instance
settings = get_settings()