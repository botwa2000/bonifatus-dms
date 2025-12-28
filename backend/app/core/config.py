# backend/app/core/config.py
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


def read_secret(secret_name: str) -> str:
    """
    Read secret from Docker Swarm secret file.

    Args:
        secret_name: Base name of the secret (without _dev or _prod suffix)

    Returns:
        Secret value as string

    Raises:
        ValueError: If secret file not found or empty
        RuntimeError: If APP_ENVIRONMENT not set
    """
    # Determine environment suffix
    app_env = os.getenv('APP_ENVIRONMENT')
    if not app_env:
        raise RuntimeError(
            "APP_ENVIRONMENT environment variable must be set to 'development' or 'production'"
        )

    env_suffix = '_dev' if app_env == 'development' else '_prod'
    secret_path = Path(f"/run/secrets/{secret_name}{env_suffix}")

    # Check if secret file exists
    if not secret_path.exists():
        raise ValueError(
            f"CRITICAL: Secret file '{secret_path}' not found. "
            f"Ensure Docker secret '{secret_name}{env_suffix}' is created and mounted to this container."
        )

    # Read secret file
    try:
        value = secret_path.read_text().strip()
    except Exception as e:
        raise ValueError(
            f"CRITICAL: Failed to read secret from {secret_path}: {e}"
        )

    # Validate secret is not empty
    if not value:
        raise ValueError(
            f"CRITICAL: Secret file '{secret_path}' exists but is empty. "
            f"Secret '{secret_name}{env_suffix}' must contain a non-empty value."
        )

    logger.info(f"Loaded secret '{secret_name}{env_suffix}' from Docker Swarm")
    return value


class DatabaseSettings(BaseSettings):
    """Database configuration from environment variables"""

    database_url: str = Field(
        default_factory=lambda: read_secret("database_url"),
        description="Database connection URL (loaded from Docker Swarm secret)"
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
        default_factory=lambda: read_secret("google_client_id"),
        description="Google OAuth client ID (loaded from Docker Swarm secret)"
    )
    google_client_secret: str = Field(
        default_factory=lambda: read_secret("google_client_secret"),
        description="Google OAuth client secret (loaded from Docker Swarm secret)"
    )
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI", description="OAuth redirect URI")
    google_vision_enabled: bool = Field(default=True, description="Enable Google Vision OCR")
    google_oauth_issuers: str = Field(default="https://accounts.google.com", description="Valid OAuth issuers")
    google_drive_service_account_key: str = Field(default="/secrets/google-drive-key", description="Google Drive service account key file path")
    google_drive_folder_name: str = Field(default="Bonifatus_DMS", env="GOOGLE_DRIVE_FOLDER_NAME", description="Google Drive folder name for documents (use different names for dev/prod)")
    google_project_id: str = Field(
        default_factory=lambda: read_secret("gcp_project"),
        alias="GCP_PROJECT",
        description="Google Cloud Project ID (loaded from Docker Swarm secret)"
    )

    class Config:
        case_sensitive = False
        extra = "ignore"


class OneDriveSettings(BaseSettings):
    """Microsoft OneDrive configuration"""

    onedrive_client_id: str = Field(
        default_factory=lambda: read_secret("onedrive_client_id"),
        description="Microsoft Azure app client ID (loaded from Docker Swarm secret)"
    )
    onedrive_client_secret: str = Field(
        default_factory=lambda: read_secret("onedrive_client_secret"),
        description="Microsoft Azure app client secret (loaded from Docker Swarm secret)"
    )
    onedrive_redirect_uri: str = Field(..., env="ONEDRIVE_REDIRECT_URI", description="OneDrive OAuth redirect URI")
    onedrive_folder_name: str = Field(default="Bonifatus_DMS", env="ONEDRIVE_FOLDER_NAME", description="OneDrive folder name for documents (use different names for dev/prod)")

    class Config:
        case_sensitive = False
        extra = "ignore"


class SecuritySettings(BaseSettings):
    """Security configuration from environment variables"""

    security_secret_key: str = Field(
        default_factory=lambda: read_secret("security_secret_key"),
        description="JWT secret key (loaded from Docker Swarm secret)"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=480, description="JWT access token expiration (8 hours)")
    inactivity_timeout_minutes: int = Field(default=60, description="Inactivity timeout - logout after 60 minutes of no API calls")
    refresh_token_expire_days: int = Field(default=30, description="Refresh token expiration (30 days for persistent login)")
    default_user_tier: str = Field(default="free", description="Default user tier")
    admin_emails: str = Field(default="bonifatus.app@gmail.com", description="Admin email list")
    encryption_key: str = Field(
        default_factory=lambda: read_secret("encryption_key"),
        description="AES-256 encryption key for field-level encryption (loaded from Docker Swarm secret)"
    )
    turnstile_site_key: Optional[str] = Field(default=None, description="Cloudflare Turnstile site key (public)")
    turnstile_secret_key: str = Field(
        default_factory=lambda: read_secret("turnstile_secret_key"),
        description="Cloudflare Turnstile secret key (loaded from Docker Swarm secret)"
    )
    cookie_domain: str = Field(
        default=".bonidoc.com",
        description="Cookie domain for auth tokens (use leading dot for wildcard subdomain access)"
    )
    cookie_secure: bool = Field(
        default=True,
        description="Enable secure flag on cookies (requires HTTPS)"
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

    brevo_api_key: str = Field(
        default_factory=lambda: read_secret("brevo_api_key"),
        description="Brevo API key (loaded from Docker Swarm secret)"
    )
    email_from_info: str = Field(default="info@bonidoc.com", description="Info email address")
    email_from_noreply: str = Field(default="no-reply@bonidoc.com", description="No-reply email address")
    email_from_name: str = Field(default="BoniDoc", description="Sender name for emails")

    class Config:
        case_sensitive = False
        extra = "ignore"


class StripeSettings(BaseSettings):
    """Stripe payment integration configuration from environment variables"""

    stripe_secret_key: str = Field(
        default_factory=lambda: read_secret("stripe_secret_key"),
        description="Stripe secret key (loaded from Docker Swarm secret)"
    )
    stripe_publishable_key: str = Field(
        default_factory=lambda: read_secret("stripe_publishable_key"),
        description="Stripe publishable key (loaded from Docker Swarm secret)"
    )
    stripe_webhook_secret: str = Field(
        default_factory=lambda: read_secret("stripe_webhook_secret"),
        description="Stripe webhook endpoint secret for signature verification (loaded from Docker Swarm secret)"
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
        default_factory=lambda: read_secret("imap_password"),
        description="IMAP password (loaded from Docker Swarm secret)"
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
    app_log_level: str = Field(
        default="INFO",
        description="Application log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    app_debug_logging: bool = Field(
        default=False,
        description="Enable verbose debug logging with detailed data (development only)"
    )
    app_cors_allow_headers: str = Field(
        default="Content-Type,Accept,Authorization,X-Acting-As-User-Id",
        description="Comma-separated list of allowed CORS request headers"
    )
    app_cors_expose_headers: str = Field(
        default="Content-Type,X-Process-Time,X-Request-ID,X-RateLimit-Remaining,X-RateLimit-Tier",
        description="Comma-separated list of exposed CORS response headers"
    )
    app_cors_allow_methods: str = Field(
        default="GET,POST,PUT,DELETE,PATCH,OPTIONS",
        description="Comma-separated list of allowed HTTP methods"
    )

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

    @property
    def cors_allow_headers_list(self) -> List[str]:
        """Get CORS allowed headers as list"""
        return [header.strip() for header in self.app.app_cors_allow_headers.split(",")]

    @property
    def cors_expose_headers_list(self) -> List[str]:
        """Get CORS exposed headers as list"""
        return [header.strip() for header in self.app.app_cors_expose_headers.split(",")]

    @property
    def cors_allow_methods_list(self) -> List[str]:
        """Get CORS allowed methods as list"""
        return [method.strip() for method in self.app.app_cors_allow_methods.split(",")]

    class Config:
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance (secrets are read once at startup, then cached).

    NOTE: In most cases, you should use the global 'settings' object directly instead of calling this function.
    This function exists primarily for backwards compatibility and testing purposes.
    """
    return Settings()


# Global settings instance
settings = get_settings()