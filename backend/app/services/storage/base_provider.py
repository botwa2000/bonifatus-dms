"""
Base storage provider interface for multi-cloud document storage.

This module defines the abstract base class that all storage providers
(Google Drive, OneDrive, Dropbox, Box, etc.) must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UploadResult:
    """
    Standardized result from document upload operations.

    Attributes:
        file_id: Provider-specific unique file identifier
        name: Document filename
        size_bytes: File size in bytes
        mime_type: MIME type of the uploaded file
        provider_type: Storage provider identifier (e.g., 'google_drive', 'onedrive')
        web_view_link: Optional URL to view the file in the provider's web interface
        folder_id: Optional folder/directory ID where the file was uploaded
    """
    file_id: str
    name: str
    size_bytes: int
    mime_type: str
    provider_type: str
    web_view_link: Optional[str] = None
    folder_id: Optional[str] = None


class StorageProvider(ABC):
    """
    Abstract base class for cloud storage providers.

    All storage provider implementations must inherit from this class
    and implement all abstract methods. This ensures a consistent interface
    across different cloud storage services.

    Design Decisions:
    - redirect_uri passed to methods (not constructor) for flexibility in different contexts
    - folder_id in upload (not folder_name) for efficiency - avoids extra API calls
    - Encrypted tokens passed to methods to maintain security
    """

    def __init__(self, provider_type: str):
        """
        Initialize the storage provider.

        Args:
            provider_type: Unique identifier for this provider (e.g., 'google_drive')
        """
        self.provider_type = provider_type

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """
        Generate OAuth authorization URL for user consent.

        Args:
            state: State parameter for CSRF protection (format: {user_id}:{provider})
            redirect_uri: Callback URL where OAuth provider will redirect after consent

        Returns:
            Complete authorization URL to redirect the user to

        Security:
            - Must use HTTPS-only redirect URIs
            - State parameter must be validated on callback
            - Must request offline_access/refresh_token scope
        """
        pass

    @abstractmethod
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization request

        Returns:
            Dictionary containing:
                - access_token: Short-lived access token
                - refresh_token: Long-lived refresh token (to be encrypted before storage)
                - expires_in: Token expiration time in seconds
                - token_type: Usually "Bearer"

        Raises:
            Exception: If token exchange fails or code is invalid
        """
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token_encrypted: str) -> str:
        """
        Refresh an expired access token using the refresh token.

        Args:
            refresh_token_encrypted: Encrypted refresh token from database

        Returns:
            New access token (not encrypted - for immediate use)

        Raises:
            Exception: If refresh token is invalid or expired

        Note:
            Implementation must decrypt the refresh token before use
        """
        pass

    @abstractmethod
    def upload_document(
        self,
        refresh_token_encrypted: str,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        folder_id: Optional[str] = None
    ) -> UploadResult:
        """
        Upload a document to the cloud storage provider.

        Args:
            refresh_token_encrypted: Encrypted refresh token from database
            file_content: Binary file content stream
            filename: Name for the uploaded file
            mime_type: MIME type of the file (e.g., 'application/pdf')
            folder_id: Optional folder ID to upload into (provider-specific)

        Returns:
            UploadResult with file metadata

        Raises:
            Exception: If upload fails or authentication is invalid

        Implementation Notes:
            - Must call file_content.seek(0) before reading
            - Should handle resumable uploads for large files (>5MB)
            - Must refresh access token if expired
        """
        pass

    @abstractmethod
    def download_document(self, refresh_token_encrypted: str, file_id: str) -> bytes:
        """
        Download a document from the cloud storage provider.

        Args:
            refresh_token_encrypted: Encrypted refresh token from database
            file_id: Provider-specific file identifier

        Returns:
            Binary file content

        Raises:
            Exception: If download fails, file not found, or authentication invalid
        """
        pass

    @abstractmethod
    def delete_document(self, refresh_token_encrypted: str, file_id: str) -> bool:
        """
        Delete a document from the cloud storage provider.

        Args:
            refresh_token_encrypted: Encrypted refresh token from database
            file_id: Provider-specific file identifier

        Returns:
            True if deletion successful, False otherwise

        Raises:
            Exception: If authentication is invalid

        Note:
            Should return False (not raise exception) if file doesn't exist
        """
        pass

    @abstractmethod
    def initialize_folder_structure(
        self,
        refresh_token_encrypted: str,
        folder_names: list[str]
    ) -> Dict[str, str]:
        """
        Create folder structure for organizing documents by category.

        Args:
            refresh_token_encrypted: Encrypted refresh token from database
            folder_names: List of folder names to create (e.g., ['Invoices', 'Contracts'])

        Returns:
            Dictionary mapping folder names to provider-specific folder IDs
            Example: {'Invoices': 'folder_id_123', 'Contracts': 'folder_id_456'}

        Raises:
            Exception: If folder creation fails or authentication invalid

        Implementation Notes:
            - Should check if folders already exist before creating
            - Should be idempotent (safe to call multiple times)
        """
        pass
