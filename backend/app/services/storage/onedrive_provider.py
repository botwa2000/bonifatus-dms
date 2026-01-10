"""
Microsoft OneDrive storage provider implementation.

This module implements the StorageProvider interface for Microsoft OneDrive,
providing OAuth authentication and document management via Microsoft Graph API.
"""

import logging
from typing import Optional, Dict, Any, BinaryIO
from urllib.parse import urlencode
import requests

from app.core.config import settings
from app.core.security import decrypt_token
from app.services.storage.base_provider import StorageProvider, UploadResult

logger = logging.getLogger(__name__)


class OneDriveProvider(StorageProvider):
    """
    Microsoft OneDrive storage provider implementation.

    Implements all StorageProvider abstract methods using Microsoft Graph API v1.0.
    """

    def __init__(self):
        super().__init__(provider_type='onedrive')
        self.app_folder_name = settings.onedrive.onedrive_folder_name
        self.client_id = settings.onedrive.onedrive_client_id
        self.client_secret = settings.onedrive.onedrive_client_secret
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.auth_base_url = "https://login.microsoftonline.com/common/oauth2/v2.0"
        self.scopes = "Files.ReadWrite.All offline_access"

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """
        Generate Microsoft OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection
            redirect_uri: Callback URL for OAuth

        Returns:
            Complete authorization URL
        """
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': self.scopes,
            'state': state,
            'response_mode': 'query',
            'prompt': 'consent'  # Force consent to always get refresh token
        }
        return f"{self.auth_base_url}/authorize?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization

        Returns:
            Dictionary with access_token, refresh_token, expires_in, etc.

        Raises:
            Exception: If token exchange fails
        """
        try:
            data = {
                'code': code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }

            token_url = f"{self.auth_base_url}/token"
            response = requests.post(token_url, data=data)
            response.raise_for_status()

            tokens = response.json()
            logger.info("Successfully exchanged authorization code for OneDrive tokens")
            return tokens

        except Exception as e:
            logger.error(f"Failed to exchange code for OneDrive tokens: {e}")
            raise

    def refresh_access_token(self, refresh_token_encrypted: str) -> str:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token_encrypted: Encrypted refresh token from database

        Returns:
            New access token (decrypted, ready to use)

        Raises:
            Exception: If refresh fails
        """
        try:
            refresh_token = decrypt_token(refresh_token_encrypted)

            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }

            token_url = f"{self.auth_base_url}/token"
            response = requests.post(token_url, data=data)
            response.raise_for_status()

            tokens = response.json()
            return tokens['access_token']

        except RuntimeError as e:
            # Token decryption failed
            logger.error(f"Token decryption failed for OneDrive: {e}")
            raise ValueError("Cloud storage connection is invalid. Please disconnect and reconnect your cloud storage in Settings")
        except Exception as e:
            logger.error(f"Failed to refresh OneDrive access token: {e}")
            raise

    def upload_document(
        self,
        refresh_token_encrypted: str,
        file_content: BinaryIO,
        filename: str,
        mime_type: str,
        folder_id: Optional[str] = None
    ) -> UploadResult:
        """
        Upload document to OneDrive.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            file_content: Binary file content stream
            filename: Name for the file
            mime_type: MIME type of the file
            folder_id: Optional folder ID to upload into

        Returns:
            UploadResult with file metadata

        Raises:
            Exception: If upload fails
        """
        try:
            logger.info(f"[OneDrive] DEBUG: upload_document called for '{filename}'")
            logger.info(f"[OneDrive] DEBUG: folder_id parameter = {folder_id}")

            access_token = self.refresh_access_token(refresh_token_encrypted)
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': mime_type
            }

            # Build upload URL
            if folder_id:
                upload_url = f"{self.graph_base_url}/me/drive/items/{folder_id}:/{filename}:/content"
                logger.info(f"[OneDrive] DEBUG: Uploading to specified folder_id: {folder_id}")
                logger.info(f"[OneDrive] DEBUG: Upload URL: {upload_url}")
            else:
                # Upload to app folder (create if doesn't exist)
                logger.warning(f"[OneDrive] DEBUG: No folder_id provided, using app folder")
                app_folder_id = self._get_or_create_app_folder(access_token)
                upload_url = f"{self.graph_base_url}/me/drive/items/{app_folder_id}:/{filename}:/content"
                folder_id = app_folder_id
                logger.info(f"[OneDrive] DEBUG: Using app folder_id: {app_folder_id}")
                logger.info(f"[OneDrive] DEBUG: Upload URL: {upload_url}")

            # Upload file
            file_content.seek(0)
            logger.info(f"[OneDrive] DEBUG: Sending PUT request to OneDrive API")
            response = requests.put(upload_url, headers=headers, data=file_content)
            response.raise_for_status()

            result = response.json()
            logger.info(f"[OneDrive] DEBUG: Upload response - file_id: {result['id']}, parentReference: {result.get('parentReference', {})}")
            logger.info(f"Document uploaded successfully to OneDrive: {result['id']}")

            return UploadResult(
                file_id=result['id'],
                name=result['name'],
                size_bytes=result['size'],
                mime_type=mime_type,
                provider_type=self.provider_type,
                web_view_link=result.get('webUrl'),
                folder_id=folder_id
            )

        except requests.HTTPError as e:
            logger.error(f"Failed to upload document '{filename}' to OneDrive: {e}")
            raise
        except Exception as e:
            logger.error(f"OneDrive document upload error: {e}")
            raise

    def download_document(self, refresh_token_encrypted: str, file_id: str) -> bytes:
        """
        Download document from OneDrive.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            file_id: OneDrive file ID

        Returns:
            File content as bytes

        Raises:
            Exception: If download fails or file not found
        """
        try:
            access_token = self.refresh_access_token(refresh_token_encrypted)
            headers = {'Authorization': f'Bearer {access_token}'}

            # Get download URL
            download_url = f"{self.graph_base_url}/me/drive/items/{file_id}/content"

            response = requests.get(download_url, headers=headers)
            response.raise_for_status()

            logger.info(f"Document downloaded successfully from OneDrive: {file_id}")
            return response.content

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"File not found in OneDrive: {file_id}")
            else:
                logger.error(f"Failed to download document from OneDrive: {e}")
            raise
        except Exception as e:
            logger.error(f"OneDrive document download error: {e}")
            raise

    def delete_document(self, refresh_token_encrypted: str, file_id: str) -> bool:
        """
        Delete document from OneDrive.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            file_id: OneDrive file ID

        Returns:
            True if successful, False if file not found

        Raises:
            Exception: If deletion fails for reasons other than file not found
        """
        try:
            access_token = self.refresh_access_token(refresh_token_encrypted)
            headers = {'Authorization': f'Bearer {access_token}'}

            delete_url = f"{self.graph_base_url}/me/drive/items/{file_id}"

            response = requests.delete(delete_url, headers=headers)
            response.raise_for_status()

            logger.info(f"Document deleted successfully from OneDrive: {file_id}")
            return True

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"File not found for deletion in OneDrive: {file_id}")
                return False
            else:
                logger.error(f"Failed to delete document from OneDrive: {e}")
                raise
        except Exception as e:
            logger.error(f"OneDrive document deletion error: {e}")
            raise

    def initialize_folder_structure(
        self,
        refresh_token_encrypted: str,
        folder_names: list[str]
    ) -> Dict[str, str]:
        """
        Create folder structure in OneDrive.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            folder_names: List of folder names to create

        Returns:
            Dictionary mapping folder names to folder IDs

        Raises:
            Exception: If folder creation fails
        """
        try:
            logger.info(f"[OneDrive] DEBUG: initialize_folder_structure called")
            logger.info(f"[OneDrive] DEBUG: folder_names to create: {folder_names}")

            access_token = self.refresh_access_token(refresh_token_encrypted)
            folder_map = {}

            # Create or get main app folder
            logger.info(f"[OneDrive] DEBUG: Getting/creating main app folder: '{self.app_folder_name}'")
            main_folder_id = self._get_or_create_app_folder(access_token)
            folder_map['main'] = main_folder_id
            logger.info(f"[OneDrive] DEBUG: Main folder '{self.app_folder_name}' ID: {main_folder_id}")
            logger.info(f"Main folder '{self.app_folder_name}' ready: {main_folder_id}")

            # Create category folders
            for folder_name in folder_names:
                logger.info(f"[OneDrive] DEBUG: Creating category folder '{folder_name}' under parent {main_folder_id}")
                folder_id = self._create_folder(access_token, folder_name, main_folder_id)
                folder_map[folder_name] = folder_id
                logger.info(f"[OneDrive] DEBUG: Folder '{folder_name}' created with ID: {folder_id}")
                logger.info(f"Folder '{folder_name}' ready: {folder_id}")

            logger.info(f"[OneDrive] DEBUG: Final folder_map: {folder_map}")
            logger.info(f"Folder structure initialized in OneDrive with {len(folder_map)} folders")
            return folder_map

        except Exception as e:
            logger.error(f"Failed to initialize folder structure in OneDrive: {e}")
            raise

    def _get_or_create_app_folder(self, access_token: str) -> str:
        """
        Get or create the main application folder in OneDrive.

        Args:
            access_token: Valid access token

        Returns:
            Folder ID of the main app folder
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}

            # Try to find existing folder
            search_url = f"{self.graph_base_url}/me/drive/root/children"
            response = requests.get(search_url, headers=headers, params={'$filter': f"name eq '{self.app_folder_name}'"})
            response.raise_for_status()

            folders = response.json().get('value', [])
            if folders:
                logger.info(f"Found existing OneDrive folder '{self.app_folder_name}': {folders[0]['id']}")
                return folders[0]['id']

            # Create new folder
            return self._create_folder(access_token, self.app_folder_name, None)

        except Exception as e:
            logger.error(f"Failed to get/create app folder in OneDrive: {e}")
            raise

    def _create_folder(self, access_token: str, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in OneDrive.

        Args:
            access_token: Valid access token
            folder_name: Name of the folder
            parent_id: Parent folder ID (None for root)

        Returns:
            Created folder ID
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Build folder metadata
            folder_metadata = {
                'name': folder_name,
                'folder': {},
                '@microsoft.graph.conflictBehavior': 'fail'
            }

            # Determine parent path
            if parent_id:
                create_url = f"{self.graph_base_url}/me/drive/items/{parent_id}/children"
            else:
                create_url = f"{self.graph_base_url}/me/drive/root/children"

            response = requests.post(create_url, headers=headers, json=folder_metadata)

            # Check if folder already exists
            if response.status_code == 409:
                # Folder exists - find it and return its ID
                logger.info(f"Folder '{folder_name}' already exists in OneDrive")
                search_url = create_url
                search_response = requests.get(search_url, headers=headers, params={'$filter': f"name eq '{folder_name}'"})
                search_response.raise_for_status()
                folders = search_response.json().get('value', [])
                if folders:
                    return folders[0]['id']

            response.raise_for_status()
            result = response.json()

            logger.info(f"Created folder '{folder_name}' in OneDrive: {result['id']}")
            return result['id']

        except Exception as e:
            logger.error(f"Failed to create folder '{folder_name}' in OneDrive: {e}")
            raise

    def delete_app_folder(self, refresh_token_encrypted: str) -> Dict[str, Any]:
        """
        Delete the entire app folder from OneDrive.

        This permanently deletes the app folder and all its contents (category folders and files).
        Used during migration to clean up after successful document migration.

        Args:
            refresh_token_encrypted: Encrypted refresh token from database

        Returns:
            Dictionary with:
                - success: Boolean indicating if deletion was successful
                - message: Human-readable status message
                - folder_id: Optional ID of the deleted folder (if found)
        """
        try:
            access_token = self.refresh_access_token(refresh_token_encrypted)
            headers = {'Authorization': f'Bearer {access_token}'}

            # Search for the main app folder
            search_url = f"{self.graph_base_url}/me/drive/root/children"
            search_params = {'$filter': f"name eq '{self.app_folder_name}'"}

            search_response = requests.get(search_url, headers=headers, params=search_params)
            search_response.raise_for_status()

            items = search_response.json().get('value', [])

            # Filter to ensure it's actually a folder
            folders = [item for item in items if 'folder' in item]

            if not folders:
                logger.info(f"App folder '{self.app_folder_name}' not found in OneDrive - nothing to delete")
                return {
                    'success': True,
                    'message': f"Folder '{self.app_folder_name}' not found (already deleted or never existed)",
                    'folder_id': None
                }

            folder_id = folders[0]['id']

            # Delete the folder (OneDrive will recursively delete all contents)
            delete_url = f"{self.graph_base_url}/me/drive/items/{folder_id}"
            delete_response = requests.delete(delete_url, headers=headers)
            delete_response.raise_for_status()

            logger.info(f"App folder '{self.app_folder_name}' (ID: {folder_id}) deleted successfully from OneDrive")
            return {
                'success': True,
                'message': f"Folder '{self.app_folder_name}' and all contents deleted successfully",
                'folder_id': folder_id
            }

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # Folder already deleted
                logger.info(f"App folder already deleted (404) from OneDrive: {self.app_folder_name}")
                return {
                    'success': True,
                    'message': f"Folder '{self.app_folder_name}' already deleted",
                    'folder_id': None
                }
            else:
                error_msg = f"Failed to delete app folder from OneDrive: {e}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'message': error_msg,
                    'folder_id': None
                }
        except Exception as e:
            error_msg = f"Error deleting app folder from OneDrive: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'folder_id': None
            }
