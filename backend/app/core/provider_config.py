"""
Provider configuration system for storage providers.

This module defines the structure for provider metadata, eliminating
hardcoded provider logic throughout the application.

Design: Each provider has a single ProviderMetadata entry that defines
ALL its properties: OAuth config, database fields, UI metadata, capabilities, etc.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ProviderCapability(Enum):
    """Provider capabilities enumeration."""

    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    FOLDER_STRUCTURE = "folder_structure"
    FOLDER_DELETION = "folder_deletion"
    RESUMABLE_UPLOAD = "resumable_upload"
    BATCH_UPLOAD = "batch_upload"
    VERSIONING = "versioning"
    SHARING = "sharing"


@dataclass
class ProviderMetadata:
    """
    Complete metadata configuration for a storage provider.

    This dataclass serves as the single source of truth for all provider
    configuration, replacing hardcoded if/elif chains and field access.

    All provider-specific logic should reference this configuration instead
    of hardcoding provider names or field names.
    """

    # =========================================================================
    # Identity
    # =========================================================================
    provider_key: str  # Unique identifier: 'google_drive', 'onedrive', etc.
    display_name: str  # Human-readable name: 'Google Drive', 'OneDrive'

    # =========================================================================
    # OAuth Configuration
    # =========================================================================
    oauth_client_id_secret: str  # Docker secret name for client ID
    oauth_client_secret_secret: str  # Docker secret name for client secret
    oauth_scopes: List[str]  # Required OAuth scopes
    oauth_redirect_uri_env: str  # Environment variable for redirect URI

    # =========================================================================
    # Storage Configuration
    # =========================================================================
    folder_name_env: str  # Environment variable for folder name
    default_folder_name: str  # Default folder name if env not set

    # =========================================================================
    # Provider Class
    # =========================================================================
    provider_class_path: str  # Full import path to provider class
    # Example: 'app.services.storage.google_drive_provider.GoogleDriveProvider'

    # =========================================================================
    # UI Metadata
    # =========================================================================
    icon: str  # Icon identifier for frontend
    description: str  # User-facing description
    color: Optional[str] = None  # Brand color (hex code)

    # =========================================================================
    # Capabilities
    # =========================================================================
    capabilities: List[ProviderCapability] = field(default_factory=list)

    # =========================================================================
    # Access Control
    # =========================================================================
    min_tier_id: int = 0  # Minimum tier required (0 = free tier)
    is_active: bool = True  # Whether provider is currently available

    # =========================================================================
    # Ordering
    # =========================================================================
    sort_order: int = 0  # Display order in UI

    # =========================================================================
    # Extensibility
    # =========================================================================
    extra_metadata: Optional[Dict[str, Any]] = None  # Additional metadata

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.provider_key:
            raise ValueError("provider_key cannot be empty")
        if not self.display_name:
            raise ValueError("display_name cannot be empty")
        if not self.oauth_client_id_secret:
            raise ValueError("oauth_client_id_secret cannot be empty")
        if not self.oauth_client_secret_secret:
            raise ValueError("oauth_client_secret_secret cannot be empty")
        if not self.oauth_scopes:
            raise ValueError("oauth_scopes cannot be empty")
        if not self.provider_class_path:
            raise ValueError("provider_class_path cannot be empty")

    def has_capability(self, capability: ProviderCapability) -> bool:
        """Check if provider supports a specific capability."""
        return capability in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert provider metadata to dictionary for API responses.

        Returns:
            Dictionary representation of provider metadata
        """
        return {
            'key': self.provider_key,
            'display_name': self.display_name,
            'icon': self.icon,
            'description': self.description,
            'color': self.color,
            'capabilities': [c.value for c in self.capabilities],
            'min_tier_id': self.min_tier_id,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
        }
