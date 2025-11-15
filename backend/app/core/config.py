# backend/app/core/config.py
import logging
import os
from functools import lru_cache
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration from environment variables"""
    
    database_url: str = Field(..., description="Database connection URL")
    database_pool_size: int = Field(default=10, description="Connection pool size")
    database_pool_recycle: int = Field(default=60, description="Pool recycle time (60s for Supabase transaction pooler)")
    database_echo: bool = Field(default=False, description="Enable SQL query logging")
    database_pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    database_connect_timeout: int = Field(default=60, description="Connection timeout")

    class Config:
        case_sensitive = False
        extra = "ignore"
        env_file = ".env"


class GoogleSettings(BaseSettings):
    """Google services configuration"""
    
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID", description="Google OAuth client ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET", description="Google OAuth client secret")
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI", description="OAuth redirect URI")
    google_vision_enabled: bool = Field(default=True, description="Enable Google Vision OCR")
    google_oauth_issuers: str = Field(default="https://accounts.google.com", description="Valid OAuth issuers")
    google_drive_service_account_key: str = Field(default="/secrets/google-drive-key", description="Google Drive service account key file path")
    google_drive_folder_name: str = Field(default="Bonifatus_DMS", env="GOOGLE_DRIVE_FOLDER_NAME", description="Google Drive folder name for documents (use different names for dev/prod)")
    google_project_id: str = Field(..., alias="GCP_PROJECT", description="Google Cloud Project ID")

    class Config:
        case_sensitive = False
        extra = "ignore"
        env_file = ".env"


class SecuritySettings(BaseSettings):
    """Security configuration from environment variables"""
    
    security_secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=60, description="JWT access token expiration (60 min for document review workflow)")
    refresh_token_expire_days: int = Field(default=30, description="Refresh token expiration (30 days for persistent login)")
    default_user_tier: str = Field(default="free", description="Default user tier")
    admin_emails: str = Field(default="bonifatus.app@gmail.com", description="Admin email list")
    encryption_key: str = Field(..., description="AES-256 encryption key for field-level encryption")
    turnstile_site_key: Optional[str] = Field(default=None, description="Cloudflare Turnstile site key (public)")
    turnstile_secret_key: Optional[str] = Field(default=None, description="Cloudflare Turnstile secret key")

    class Config:
        case_sensitive = False
        extra = "ignore"
        env_file = ".env"


class TranslationSettings(BaseSettings):
    """Translation service configuration from environment variables"""

    translation_provider: str = Field(..., description="Translation provider: libretranslate or deepl")
    translation_libretranslate_url: str = Field(..., description="LibreTranslate API URL")
    translation_deepl_api_key: Optional[str] = Field(default=None, description="DeepL API key (for paid tier)")
    translation_deepl_url: str = Field(..., description="DeepL API URL")
    translation_force_provider: Optional[str] = Field(default=None, description="Force specific provider (dev/test only)")
    translation_timeout: int = Field(..., description="Translation request timeout in seconds")

    class Config:
        case_sensitive = False
        extra = "ignore"
        env_file = ".env"


class ScannerSettings(BaseSettings):
    """Security scanner configuration from environment variables"""

    clamav_enabled: bool = Field(default=True, description="Enable ClamAV antivirus scanning")

    class Config:
        case_sensitive = False
        extra = "ignore"
        env_file = ".env"


class EmailSettings(BaseSettings):
    """Email service configuration from environment variables"""

    brevo_api_key: Optional[str] = Field(
        None,
        description="Brevo API key (set via system environment variable, NOT in .env file)"
    )
    email_from_info: str = Field(default="info@bonidoc.com", description="Info email address")
    email_from_noreply: str = Field(default="no-reply@bonidoc.com", description="No-reply email address")
    email_from_name: str = Field(default="BoniDoc", description="Sender name for emails")

    class Config:
        case_sensitive = False
        extra = "ignore"
        env_file = ".env"


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
    app_frontend_url: str = Field(..., alias="NEXTAUTH_URL", description="Frontend URL for OAuth redirects")

    class Config:
        case_sensitive = False
        extra = "ignore"
        env_file = ".env"


class Settings(BaseSettings):
    """Complete application settings with modular structure"""

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    translation: TranslationSettings = Field(default_factory=TranslationSettings)
    scanner: ScannerSettings = Field(default_factory=ScannerSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)

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
        env_file = ".env"


def get_settings() -> Settings:
    """Get settings instance without caching to ensure fresh environment variable reads"""
    return Settings()


# Global settings instance
settings = get_settings()