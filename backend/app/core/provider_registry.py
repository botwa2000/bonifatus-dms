"""
Centralized provider registry - Single source of truth for all storage providers.

This module contains ALL provider configurations in one place, eliminating
hardcoded provider logic scattered across the codebase.

To add a new provider, simply add a new ProviderRegistry.register() call below.
No need to modify OAuth callbacks, migrations, or any other files.
"""

from typing import Dict, List, Optional
from app.core.provider_config import ProviderMetadata, ProviderCapability


class ProviderRegistry:
    """
    Centralized registry for all storage provider configurations.

    This class serves as the single source of truth for provider metadata.
    All provider-related operations should query this registry instead of
    using hardcoded if/elif chains or provider-specific field names.

    Thread-safe: All operations are read-only after module initialization.
    """

    _providers: Dict[str, ProviderMetadata] = {}

    @classmethod
    def register(cls, metadata: ProviderMetadata) -> None:
        """
        Register a provider configuration.

        Args:
            metadata: Complete provider metadata

        Raises:
            ValueError: If provider_key is already registered
        """
        if metadata.provider_key in cls._providers:
            raise ValueError(
                f"Provider '{metadata.provider_key}' is already registered"
            )
        cls._providers[metadata.provider_key] = metadata

    @classmethod
    def get(cls, provider_key: str) -> Optional[ProviderMetadata]:
        """
        Get provider metadata by key.

        Args:
            provider_key: Provider identifier (e.g., 'google_drive')

        Returns:
            Provider metadata or None if not found
        """
        return cls._providers.get(provider_key)

    @classmethod
    def get_all(cls) -> List[ProviderMetadata]:
        """
        Get all registered providers.

        Returns:
            List of all provider metadata, sorted by sort_order
        """
        return sorted(cls._providers.values(), key=lambda p: p.sort_order)

    @classmethod
    def get_active(cls) -> List[ProviderMetadata]:
        """
        Get all active providers.

        Returns:
            List of active provider metadata, sorted by sort_order
        """
        return [p for p in cls.get_all() if p.is_active]

    @classmethod
    def exists(cls, provider_key: str) -> bool:
        """
        Check if provider is registered.

        Args:
            provider_key: Provider identifier

        Returns:
            True if provider is registered, False otherwise
        """
        return provider_key in cls._providers

    @classmethod
    def get_by_capability(
        cls, capability: ProviderCapability
    ) -> List[ProviderMetadata]:
        """
        Get providers supporting a specific capability.

        Args:
            capability: Provider capability to filter by

        Returns:
            List of providers with the specified capability
        """
        return [
            p for p in cls.get_active()
            if p.has_capability(capability)
        ]

    @classmethod
    def get_display_name(cls, provider_key: str) -> str:
        """
        Get display name for a provider.

        Args:
            provider_key: Provider identifier

        Returns:
            Display name or formatted provider_key if not found
        """
        metadata = cls.get(provider_key)
        if metadata:
            return metadata.display_name
        # Fallback: Convert 'google_drive' -> 'Google Drive'
        return provider_key.replace('_', ' ').title()


# =============================================================================
# Provider Configurations - Single Source of Truth
# =============================================================================
# All providers are registered here. To add a new provider, simply add a new
# ProviderRegistry.register() call with complete metadata.
# =============================================================================

# Google Drive
ProviderRegistry.register(ProviderMetadata(
    provider_key='google_drive',
    display_name='Google Drive',

    # OAuth
    oauth_client_id_secret='google_client_id',
    oauth_client_secret_secret='google_client_secret',
    oauth_scopes=[
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata.readonly',
        'openid',
        'email',
        'profile'
    ],
    oauth_redirect_uri_env='GOOGLE_REDIRECT_URI',

    # Storage
    folder_name_env='GOOGLE_DRIVE_FOLDER_NAME',
    default_folder_name='Bonifatus_DMS',

    # Provider Class
    provider_class_path='app.services.storage.google_drive_provider.GoogleDriveProvider',

    # UI
    icon='google-drive',
    description='Store your documents securely with Google Drive\'s version control and easy sharing',
    color='#4285F4',  # Google blue

    # Capabilities
    capabilities=[
        ProviderCapability.FILE_UPLOAD,
        ProviderCapability.FILE_DOWNLOAD,
        ProviderCapability.FILE_DELETE,
        ProviderCapability.FOLDER_STRUCTURE,
        ProviderCapability.FOLDER_DELETION,
        ProviderCapability.RESUMABLE_UPLOAD,
        ProviderCapability.SHARING,
    ],

    # Access
    min_tier_id=0,  # Available on free tier
    is_active=True,
    sort_order=1
))

# OneDrive
ProviderRegistry.register(ProviderMetadata(
    provider_key='onedrive',
    display_name='OneDrive',

    # OAuth
    oauth_client_id_secret='onedrive_client_id',
    oauth_client_secret_secret='onedrive_client_secret',
    oauth_scopes=[
        'Files.ReadWrite.All',
        'offline_access',
        'User.Read'
    ],
    oauth_redirect_uri_env='ONEDRIVE_REDIRECT_URI',

    # Storage
    folder_name_env='ONEDRIVE_FOLDER_NAME',
    default_folder_name='Bonifatus_DMS',

    # Provider Class
    provider_class_path='app.services.storage.onedrive_provider.OneDriveProvider',

    # UI
    icon='onedrive',
    description='Save documents to Microsoft OneDrive with enterprise-grade security and collaboration',
    color='#0078D4',  # Microsoft blue

    # Capabilities
    capabilities=[
        ProviderCapability.FILE_UPLOAD,
        ProviderCapability.FILE_DOWNLOAD,
        ProviderCapability.FILE_DELETE,
        ProviderCapability.FOLDER_STRUCTURE,
        ProviderCapability.FOLDER_DELETION,
        ProviderCapability.SHARING,
    ],

    # Access
    min_tier_id=0,  # Available on free tier
    is_active=True,
    sort_order=2
))

# Dropbox (Future implementation)
ProviderRegistry.register(ProviderMetadata(
    provider_key='dropbox',
    display_name='Dropbox',

    # OAuth
    oauth_client_id_secret='dropbox_client_id',
    oauth_client_secret_secret='dropbox_client_secret',
    oauth_scopes=['files.content.write', 'files.content.read'],
    oauth_redirect_uri_env='DROPBOX_REDIRECT_URI',

    # Storage
    folder_name_env='DROPBOX_FOLDER_NAME',
    default_folder_name='Bonifatus_DMS',

    # Provider Class
    provider_class_path='app.services.storage.dropbox_provider.DropboxProvider',

    # UI
    icon='dropbox',
    description='Sync your documents across devices with Dropbox\'s reliable cloud storage',
    color='#0061FF',  # Dropbox blue

    # Capabilities
    capabilities=[
        ProviderCapability.FILE_UPLOAD,
        ProviderCapability.FILE_DOWNLOAD,
        ProviderCapability.FILE_DELETE,
        ProviderCapability.FOLDER_STRUCTURE,
    ],

    # Access
    min_tier_id=1,  # Requires Starter tier
    is_active=False,  # Not yet implemented
    sort_order=3
))

# Box (Future implementation)
ProviderRegistry.register(ProviderMetadata(
    provider_key='box',
    display_name='Box',

    # OAuth
    oauth_client_id_secret='box_client_id',
    oauth_client_secret_secret='box_client_secret',
    oauth_scopes=['root_readwrite', 'base'],
    oauth_redirect_uri_env='BOX_REDIRECT_URI',

    # Storage
    folder_name_env='BOX_FOLDER_NAME',
    default_folder_name='Bonifatus_DMS',

    # Provider Class
    provider_class_path='app.services.storage.box_provider.BoxProvider',

    # UI
    icon='box',
    description='Securely store and manage documents with Box\'s enterprise content management',
    color='#0061D5',  # Box blue

    # Capabilities
    capabilities=[
        ProviderCapability.FILE_UPLOAD,
        ProviderCapability.FILE_DOWNLOAD,
        ProviderCapability.FILE_DELETE,
        ProviderCapability.FOLDER_STRUCTURE,
        ProviderCapability.VERSIONING,
    ],

    # Access
    min_tier_id=2,  # Requires Pro tier
    is_active=False,  # Not yet implemented
    sort_order=4
))
