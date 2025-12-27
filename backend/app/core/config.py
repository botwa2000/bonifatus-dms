# backend/app/core/config.py
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


def read_secret(secret_name: str, fallback_env_var: str = None) -> str:
    """
    Read secret from Docker Swarm secret file or fall back to environment variable.

    Priority:
    1. /run/secrets/{secret_name}_{env_suffix} (Docker Swarm secret with _dev or _prod suffix)
    2. Environment variable (fallback for migration/local dev)
    3. Raise error if neither found

    Args:
        secret_name: Base name of the secret (without _dev or _prod suffix)
        fallback_env_var: Environment variable name to fall back to

    Returns:
        Secret value as string

    Raises:
        ValueError: If secret not found in either location
    """
    # Determine environment suffix
    app_env = os.getenv('APP_ENVIRONMENT', 'development')
    env_suffix = '_dev' if app_env == 'development' else '_prod'

    # Try Docker secret with environment suffix first
    secret_path = Path(f"/run/secrets/{secret_name}{env_suffix}")

    if secret_path.exists():
        try:
            value = secret_path.read_text().strip()
            if value:
                logger.debug(f"Loaded secret '{secret_name}{env_suffix}' from Docker Swarm")
                return value
        except Exception as e:
            logger.warning(f"Failed to read secret from {secret_path}: {e}")

    # Fallback to environment variable
    if fallback_env_var:
        value = os.getenv(fallback_env_var)
        if value:
            logger.warning(f"Using environment variable for '{secret_name}' (Docker secret not found)")
            return value

    # Not found
    raise ValueError(
        f"Secret '{secret_name}{env_suffix}' not found in /run/secrets/ "
        f"or environment variable '{fallback_env_var}'"
    )


class DatabaseSettings(BaseSettings):
    """Database configuration from environment variables"""

    database_url: str = Field(
        default_factory=lambda: read_secret("database_url", "DATABASE_URL"),
        description="Database connection URL"
    )
    database_pool_size: int = Field(default=10, description="Connection pool size")
    database_pool_recycle: int = Field(default=60, description="Pool recycle time (60s for Supabase transaction pooler)")
    database_echo: bool = Field(default=False, description="Enable SQL query logging")
    database_pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    database_connect_timeout: int = Field(default=60, description="Connection timeout")

    class Config:
        case_sensitive = False
        extra = "ignore"


class GoogleSettings(BaseSettings):
    """Google services configuration"""

    google_client_id: str = Field(
        default_factory=lambda: read_secret("google_client_id", "GOOGLE_CLIENT_ID"),
        description="Google OAuth client ID"
    )
    google_client_secret: str = Field(
        default_factory=lambda: read_secret("google_client_secret", "GOOGLE_CLIENT_SECRET"),
        description="Google OAuth client secret"
    )
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI", description="OAuth redirect URI")
    google_vision_enabled: bool = Field(default=True, description="Enable Google Vision OCR")
    google_oauth_issuers: str = Field(default="https://accounts.google.com", description="Valid OAuth issuers")
    google_drive_service_account_key: str = Field(default="/secrets/google-drive-key", description="Google Drive service account key file path")
    google_drive_folder_name: str = Field(default="Bonifatus_DMS", env="GOOGLE_DRIVE_FOLDER_NAME", description="Google Drive folder name for documents (use different names for dev/prod)")
    google_project_id: str = Field(
        default_factory=lambda: read_secret("gcp_project", "GCP_PROJECT"),
        alias="GCP_PROJECT",
        description="Google Cloud Project ID"
    )

    class Config:
        case_sensitive = False
        extra = "ignore"


class OneDriveSettings(BaseSettings):
    """Microsoft OneDrive configuration"""

    onedrive_client_id: str = Field(
        default_factory=lambda: read_secret("onedrive_client_id", "ONEDRIVE_CLIENT_ID"),
        description="Microsoft Azure app client ID"
    )
    onedrive_client_secret: str = Field(
        default_factory=lambda: read_secret("onedrive_client_secret", "ONEDRIVE_CLIENT_SECRET"),
        description="Microsoft Azure app client secret"
    )
    onedrive_redirect_uri: str = Field(..., env="ONEDRIVE_REDIRECT_URI", description="OneDrive OAuth redirect URI")
    onedrive_folder_name: str = Field(default="Bonifatus_DMS", env="ONEDRIVE_FOLDER_NAME", description="OneDrive folder name for documents (use different names for dev/prod)")

    class Config:
        case_sensitive = False
        extra = "ignore"


class SecuritySettings(BaseSettings):
    """Security configuration from environment variables"""

    security_secret_key: str = Field(
        default_factory=lambda: read_secret("security_secret_key", "SECURITY_SECRET_KEY"),
        description="JWT secret key"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=480, description="JWT access token expiration (8 hours)")
    inactivity_timeout_minutes: int = Field(default=60, description="Inactivity timeout - logout after 60 minutes of no API calls")
    refresh_token_expire_days: int = Field(default=30, description="Refresh token expiration (30 days for persistent login)")
    default_user_tier: str = Field(default="free", description="Default user tier")
    admin_emails: str = Field(default="bonifatus.app@gmail.com", description="Admin email list")
    encryption_key: str = Field(
        default_factory=lambda: read_secret("encryption_key", "ENCRYPTION_KEY"),
        description="AES-256 encryption key for field-level encryption"
    )
    turnstile_site_key: Optional[str] = Field(default=None, description="Cloudflare Turnstile site key (public)")
    turnstile_secret_key: Optional[str] = Field(
        default_factory=lambda: (
            read_secret("turnstile_secret_key", "TURNSTILE_SECRET_KEY")
            if Path("/run/secrets/turnstile_secret_key").exists() or os.getenv("TURNSTILE_SECRET_KEY")
            else None
        ),
        description="Cloudflare Turnstile secret key"
    )

    class Config:
        case_sensitive = False
        extra = "ignore"


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


class ScannerSettings(BaseSettings):
    """Security scanner configuration from environment variables"""

    clamav_enabled: bool = Field(default=True, description="Enable ClamAV antivirus scanning")

    class Config:
        case_sensitive = False
        extra = "ignore"


class EmailSettings(BaseSettings):
    """Email service configuration from environment variables"""

    brevo_api_key: Optional[str] = Field(
        default_factory=lambda: (
            read_secret("brevo_api_key", "BREVO_API_KEY")
            if Path("/run/secrets/brevo_api_key").exists() or os.getenv("BREVO_API_KEY")
            else None
        ),
        description="Brevo API key (loaded from Docker Swarm secret or environment variable)"
    )
    email_from_info: str = Field(default="info@bonidoc.com", description="Info email address")
    email_from_noreply: str = Field(default="no-reply@bonidoc.com", description="No-reply email address")
    email_from_name: str = Field(default="BoniDoc", description="Sender name for emails")

    class Config:
        case_sensitive = False
        extra = "ignore"


class StripeSettings(BaseSettings):
    """Stripe payment integration configuration from environment variables"""

    stripe_secret_key: Optional[str] = Field(
        default_factory=lambda: (
            read_secret("stripe_secret_key", "STRIPE_SECRET_KEY")
            if Path("/run/secrets/stripe_secret_key").exists() or os.getenv("STRIPE_SECRET_KEY")
            else None
        ),
        description="Stripe secret key (loaded from Docker Swarm secret or environment variable)"
    )
    stripe_publishable_key: Optional[str] = Field(
        default_factory=lambda: (
            read_secret("stripe_publishable_key", "STRIPE_PUBLISHABLE_KEY")
            if Path("/run/secrets/stripe_publishable_key").exists() or os.getenv("STRIPE_PUBLISHABLE_KEY")
            else None
        ),
        description="Stripe publishable key (loaded from Docker Swarm secret or environment variable)"
    )
    stripe_webhook_secret: Optional[str] = Field(
        default_factory=lambda: (
            read_secret("stripe_webhook_secret", "STRIPE_WEBHOOK_SECRET")
            if Path("/run/secrets/stripe_webhook_secret").exists() or os.getenv("STRIPE_WEBHOOK_SECRET")
            else None
        ),
        description="Stripe webhook endpoint secret for signature verification"
    )
    # Price IDs for each tier and billing cycle
    stripe_price_id_starter_monthly: Optional[str] = Field(None, description="Stripe price ID for Starter monthly")
    stripe_price_id_starter_yearly: Optional[str] = Field(None, description="Stripe price ID for Starter yearly")
    stripe_price_id_pro_monthly: Optional[str] = Field(None, description="Stripe price ID for Pro monthly")
    stripe_price_id_pro_yearly: Optional[str] = Field(None, description="Stripe price ID for Pro yearly")

    class Config:
        case_sensitive = False
        extra = "ignore"


class EmailProcessingSettings(BaseSettings):
    """Email-to-document processing configuration from environment variables"""

    # IMAP settings for receiving emails (Zoho EU for info@bonidoc.com)
    imap_host: str = Field(default="imappro.zoho.eu", description="IMAP server hostname (Zoho EU)")
    imap_port: int = Field(default=993, description="IMAP port (993 for SSL)")
    imap_user: str = Field(default="info@bonidoc.com", description="IMAP username")
    imap_password: str = Field(
        default_factory=lambda: read_secret("imap_password", "IMAP_PASSWORD"),
        description="IMAP password (loaded from Docker Swarm secret or environment variable)"
    )
    imap_use_ssl: bool = Field(default=True, description="Use SSL for IMAP connection")

    # Email processing settings
    doc_domain: str = Field(default="doc.bonidoc.com", description="Document processing email domain")
    temp_storage_path: str = Field(default="/tmp/email_attachments", description="Temporary file storage path")
    polling_interval_seconds: int = Field(default=300, description="How often to poll for new emails (5 minutes)")

    # Processing limits (defaults, overridden by tier settings)
    max_attachment_size_mb: int = Field(default=20, description="Default max attachment size in MB")
    max_attachments_per_email: int = Field(default=10, description="Max attachments per email")

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
    app_frontend_url: str = Field(..., alias="NEXTAUTH_URL", description="Frontend URL for OAuth redirects")

    class Config:
        case_sensitive = False
        extra = "ignore"


class Settings(BaseSettings):
    """Complete application settings with modular structure"""

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    onedrive: OneDriveSettings = Field(default_factory=OneDriveSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    translation: TranslationSettings = Field(default_factory=TranslationSettings)
    scanner: ScannerSettings = Field(default_factory=ScannerSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    email_processing: EmailProcessingSettings = Field(default_factory=EmailProcessingSettings)
    stripe: StripeSettings = Field(default_factory=StripeSettings)

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