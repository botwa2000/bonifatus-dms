"""
Document storage service - High-level abstraction for multi-cloud storage.

This service provides a unified interface for document operations across
different cloud storage providers (Google Drive, OneDrive, etc.).
"""

import logging
from typing import Optional, Dict, BinaryIO

from app.services.storage.provider_factory import ProviderFactory
from app.services.storage.base_provider import UploadResult
from app.database.models import User

logger = logging.getLogger(__name__)


class DocumentStorageService:
    """
    High-level service for managing documents across multiple cloud storage providers.

    This service abstracts away provider-specific details and provides a consistent
    interface for document operations regardless of which provider the user has selected.

    Design Pattern:
        - Uses ProviderFactory to create provider instances
        - Routes operations to the user's active storage provider
        - Handles provider token retrieval from user model
    """

    def __init__(self):
        """Initialize the document storage service."""
        pass

    def _get_refresh_token(self, user: User, provider_type: str) -> Optional[str]:
        """
        Get the encrypted refresh token for a specific provider from user model.

        Args:
            user: User model instance
            provider_type: Provider identifier (e.g., 'google_drive', 'onedrive')

        Returns:
            Encrypted refresh token, or None if not available

        Raises:
            ValueError: If provider type is unknown
        """
        token_map = {
            'google_drive': user.drive_refresh_token_encrypted,
            'onedrive': getattr(user, 'onedrive_refresh_token_encrypted', None),
            'dropbox': getattr(user, 'dropbox_refresh_token_encrypted', None),
            'box': getattr(user, 'box_refresh_token_encrypted', None),
        }

        if provider_type not in token_map:
            raise ValueError(f"Unknown provider type: {provider_type}")

        token = token_map.get(provider_type)
        if not token:
            raise ValueError(f"User has not connected {provider_type}")

        return token

    def upload_document(
        self,
        user: User,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        folder_id: Optional[str] = None,
        provider_type: Optional[str] = None
    ) -> UploadResult:
        """
        Upload a document to user's active cloud storage provider.

        Args:
            user: User model instance
            file_content: Binary file content stream
            filename: Name for the uploaded file
            mime_type: MIME type of the file
            folder_id: Optional folder ID to upload into
            provider_type: Optional override for provider (uses active_storage_provider if None)

        Returns:
            UploadResult with file metadata

        Raises:
            ValueError: If user has no active provider or provider not connected
            Exception: If upload fails
        """
        # Determine which provider to use
        target_provider = provider_type or user.active_storage_provider
        if not target_provider:
            raise ValueError("User has no active storage provider configured")

        # Get refresh token for the provider
        refresh_token = self._get_refresh_token(user, target_provider)

        # Create provider instance and upload
        provider = ProviderFactory.create(target_provider)
        result = provider.upload_document(
            refresh_token_encrypted=refresh_token,
            file_content=file_content,
            filename=filename,
            mime_type=mime_type,
            folder_id=folder_id
        )

        logger.info(f"Document '{filename}' uploaded to {target_provider}: {result.file_id}")
        return result

    def download_document(
        self,
        user: User,
        file_id: str,
        provider_type: Optional[str] = None
    ) -> bytes:
        """
        Download a document from user's cloud storage.

        Args:
            user: User model instance
            file_id: Provider-specific file identifier
            provider_type: Optional override for provider (uses active_storage_provider if None)

        Returns:
            Binary file content

        Raises:
            ValueError: If user has no active provider or provider not connected
            Exception: If download fails or file not found
        """
        target_provider = provider_type or user.active_storage_provider
        if not target_provider:
            raise ValueError("User has no active storage provider configured")

        refresh_token = self._get_refresh_token(user, target_provider)

        provider = ProviderFactory.create(target_provider)
        content = provider.download_document(
            refresh_token_encrypted=refresh_token,
            file_id=file_id
        )

        logger.info(f"Document {file_id} downloaded from {target_provider}")
        return content

    def delete_document(
        self,
        user: User,
        file_id: str,
        provider_type: Optional[str] = None
    ) -> bool:
        """
        Delete a document from user's cloud storage.

        Args:
            user: User model instance
            file_id: Provider-specific file identifier
            provider_type: Optional override for provider (uses active_storage_provider if None)

        Returns:
            True if deletion successful, False if file not found

        Raises:
            ValueError: If user has no active provider or provider not connected
            Exception: If deletion fails
        """
        target_provider = provider_type or user.active_storage_provider
        if not target_provider:
            raise ValueError("User has no active storage provider configured")

        refresh_token = self._get_refresh_token(user, target_provider)

        provider = ProviderFactory.create(target_provider)
        success = provider.delete_document(
            refresh_token_encrypted=refresh_token,
            file_id=file_id
        )

        if success:
            logger.info(f"Document {file_id} deleted from {target_provider}")
        else:
            logger.warning(f"Document {file_id} not found in {target_provider}")

        return success

    def initialize_folder_structure(
        self,
        user: User,
        folder_names: list[str],
        provider_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Initialize folder structure in user's cloud storage.

        Args:
            user: User model instance
            folder_names: List of folder names to create
            provider_type: Optional override for provider (uses active_storage_provider if None)

        Returns:
            Dictionary mapping folder names to provider-specific folder IDs

        Raises:
            ValueError: If user has no active provider or provider not connected
            Exception: If folder creation fails
        """
        target_provider = provider_type or user.active_storage_provider
        if not target_provider:
            raise ValueError("User has no active storage provider configured")

        refresh_token = self._get_refresh_token(user, target_provider)

        provider = ProviderFactory.create(target_provider)
        folder_map = provider.initialize_folder_structure(
            refresh_token_encrypted=refresh_token,
            folder_names=folder_names
        )

        logger.info(f"Initialized {len(folder_map)} folders in {target_provider}")
        return folder_map

    def get_authorization_url(
        self,
        provider_type: str,
        state: str,
        redirect_uri: str
    ) -> str:
        """
        Get OAuth authorization URL for a storage provider.

        Args:
            provider_type: Provider identifier (e.g., 'google_drive', 'onedrive')
            state: State parameter for CSRF protection
            redirect_uri: Callback URL for OAuth

        Returns:
            Complete authorization URL to redirect user to

        Raises:
            ValueError: If provider type is unknown
        """
        provider = ProviderFactory.create(provider_type)
        auth_url = provider.get_authorization_url(state=state, redirect_uri=redirect_uri)

        logger.info(f"Generated authorization URL for {provider_type}")
        return auth_url

    def exchange_code_for_tokens(
        self,
        provider_type: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, any]:
        """
        Exchange OAuth authorization code for access and refresh tokens.

        Args:
            provider_type: Provider identifier
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization

        Returns:
            Dictionary with access_token, refresh_token, expires_in, etc.

        Raises:
            ValueError: If provider type is unknown
            Exception: If token exchange fails
        """
        provider = ProviderFactory.create(provider_type)
        tokens = provider.exchange_code_for_tokens(code=code, redirect_uri=redirect_uri)

        logger.info(f"Successfully exchanged code for tokens: {provider_type}")
        return tokens

    def is_provider_connected(self, user: User, provider_type: str) -> bool:
        """
        Check if user has connected a specific storage provider.

        Args:
            user: User model instance
            provider_type: Provider identifier

        Returns:
            True if provider is connected (has refresh token), False otherwise
        """
        try:
            token = self._get_refresh_token(user, provider_type)
            return token is not None
        except (ValueError, AttributeError):
            return False

    def get_active_provider(self, user: User) -> Optional[str]:
        """
        Get the user's currently active storage provider.

        Args:
            user: User model instance

        Returns:
            Provider type string, or None if no active provider
        """
        return user.active_storage_provider


# Singleton instance for easy importing
document_storage_service = DocumentStorageService()
