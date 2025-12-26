"""
Google Drive storage provider implementation.

This module implements the StorageProvider interface for Google Drive,
providing OAuth authentication and document management capabilities.
"""

import logging
import io
from typing import Optional, Dict, Any, BinaryIO
from urllib.parse import urlencode

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import requests

from app.core.config import settings
from app.core.security import decrypt_token
from app.services.storage.base_provider import StorageProvider, UploadResult

logger = logging.getLogger(__name__)


class GoogleDriveProvider(StorageProvider):
    """
    Google Drive storage provider implementation.

    Implements all StorageProvider abstract methods for Google Drive API v3.
    """

    def __init__(self):
        super().__init__(provider_type='google_drive')
        self.app_folder_name = settings.google.google_drive_folder_name
        self.client_id = settings.google.google_client_id
        self.client_secret = settings.google.google_client_secret
        self.scopes = ["https://www.googleapis.com/auth/drive.file"]
        self.token_uri = "https://oauth2.googleapis.com/token"
        self.auth_uri = "https://accounts.google.com/o/oauth2/v2/auth"

    def _get_drive_service(self, refresh_token_encrypted: str):
        """
        Create Google Drive API service with refresh token.

        Args:
            refresh_token_encrypted: Encrypted refresh token from database

        Returns:
            Google Drive API service instance
        """
        try:
            refresh_token = decrypt_token(refresh_token_encrypted)

            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=self.token_uri,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes
            )

            service = build('drive', 'v3', credentials=credentials)
            return service

        except Exception as e:
            logger.error(f"Failed to create Drive service: {e}")
            raise

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection
            redirect_uri: Callback URL for OAuth

        Returns:
            Complete authorization URL
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'state': state,
            'access_type': 'offline',  # Required for refresh token
            'prompt': 'consent'  # Force consent to always get refresh token
        }
        return f"{self.auth_uri}?{urlencode(params)}"

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

            response = requests.post(self.token_uri, data=data)
            response.raise_for_status()

            tokens = response.json()
            logger.info("Successfully exchanged authorization code for tokens")
            return tokens

        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
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

            response = requests.post(self.token_uri, data=data)
            response.raise_for_status()

            tokens = response.json()
            return tokens['access_token']

        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
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
        Upload document to Google Drive.

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
            service = self._get_drive_service(refresh_token_encrypted)

            # If no folder specified, find/create main app folder
            if not folder_id:
                folder_id = self._find_folder(service, self.app_folder_name)
                if not folder_id:
                    folder_id = self._create_folder(service, self.app_folder_name)

            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }

            file_content.seek(0)
            media = MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True
            )

            file_result = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,mimeType,webViewLink'
            ).execute()

            logger.info(f"Document uploaded successfully: {file_result['id']}")

            return UploadResult(
                file_id=file_result['id'],
                name=file_result['name'],
                size_bytes=int(file_result.get('size', 0)),
                mime_type=file_result['mimeType'],
                provider_type=self.provider_type,
                web_view_link=file_result.get('webViewLink'),
                folder_id=folder_id
            )

        except HttpError as e:
            logger.error(f"Failed to upload document '{filename}': {e}")
            raise
        except Exception as e:
            logger.error(f"Document upload error: {e}")
            raise

    def download_document(self, refresh_token_encrypted: str, file_id: str) -> bytes:
        """
        Download document from Google Drive.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            file_id: Google Drive file ID

        Returns:
            File content as bytes

        Raises:
            Exception: If download fails or file not found
        """
        try:
            service = self._get_drive_service(refresh_token_encrypted)

            request = service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()

            downloader = MediaIoBaseDownload(file_content, request)
            done = False

            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")

            file_content.seek(0)
            logger.info(f"Document downloaded successfully: {file_id}")
            return file_content.getvalue()

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File not found in Google Drive: {file_id}")
            else:
                logger.error(f"Failed to download document: {e}")
            raise
        except Exception as e:
            logger.error(f"Document download error: {e}")
            raise

    def delete_document(self, refresh_token_encrypted: str, file_id: str) -> bool:
        """
        Delete document from Google Drive.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            file_id: Google Drive file ID

        Returns:
            True if successful, False if file not found

        Raises:
            Exception: If deletion fails for reasons other than file not found
        """
        try:
            service = self._get_drive_service(refresh_token_encrypted)
            service.files().delete(fileId=file_id).execute()
            logger.info(f"Document deleted successfully: {file_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File not found for deletion: {file_id}")
                return False
            else:
                logger.error(f"Failed to delete document: {e}")
                raise
        except Exception as e:
            logger.error(f"Document deletion error: {e}")
            raise

    def initialize_folder_structure(
        self,
        refresh_token_encrypted: str,
        folder_names: list[str]
    ) -> Dict[str, str]:
        """
        Create folder structure in Google Drive.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            folder_names: List of folder names to create

        Returns:
            Dictionary mapping folder names to folder IDs

        Raises:
            Exception: If folder creation fails
        """
        try:
            service = self._get_drive_service(refresh_token_encrypted)
            folder_map = {}

            # Create or find main app folder
            main_folder_id = self._find_folder(service, self.app_folder_name)
            if not main_folder_id:
                main_folder_id = self._create_folder(service, self.app_folder_name)

            folder_map['main'] = main_folder_id
            logger.info(f"Main folder '{self.app_folder_name}' ready: {main_folder_id}")

            # Create category folders
            for folder_name in folder_names:
                folder_id = self._find_folder(service, folder_name, main_folder_id)
                if not folder_id:
                    folder_id = self._create_folder(service, folder_name, main_folder_id)

                folder_map[folder_name] = folder_id
                logger.info(f"Folder '{folder_name}' ready: {folder_id}")

            logger.info(f"Folder structure initialized with {len(folder_map)} folders")
            return folder_map

        except Exception as e:
            logger.error(f"Failed to initialize folder structure: {e}")
            raise

    def _create_folder(self, service, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive.

        Args:
            service: Google Drive API service
            folder_name: Name of the folder
            parent_id: Parent folder ID (None for root)

        Returns:
            Created folder ID
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = service.files().create(
                body=file_metadata,
                fields='id, name, webViewLink'
            ).execute()

            logger.info(f"Created folder '{folder_name}' with ID: {folder['id']}")
            return folder['id']

        except HttpError as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            raise

    def _find_folder(self, service, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find a folder by name in Google Drive.

        Args:
            service: Google Drive API service
            folder_name: Name of the folder to find
            parent_id: Parent folder ID (None for root)

        Returns:
            Folder ID if found, None otherwise
        """
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

            if parent_id:
                query += f" and '{parent_id}' in parents"

            results = service.files().list(
                q=query,
                fields='files(id, name)',
                spaces='drive'
            ).execute()

            files = results.get('files', [])
            if files:
                logger.info(f"Found existing folder '{folder_name}' with ID: {files[0]['id']}")
                return files[0]['id']

            return None

        except HttpError as e:
            logger.error(f"Failed to find folder '{folder_name}': {e}")
            return None

    def get_or_create_category_folder(
        self,
        refresh_token_encrypted: str,
        category_name: str,
        category_code: str,
        main_folder_id: str
    ) -> str:
        """
        Get or create a category folder in Drive.

        This is a Google Drive-specific helper method for backward compatibility.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            category_name: Category display name
            category_code: Category code (e.g., BNK, TAX)
            main_folder_id: Main app folder ID

        Returns:
            Category folder ID
        """
        try:
            service = self._get_drive_service(refresh_token_encrypted)
            folder_name = f"{category_name} ({category_code})"

            folder_id = self._find_folder(service, folder_name, main_folder_id)
            if folder_id:
                return folder_id

            folder_id = self._create_folder(service, folder_name, main_folder_id)
            return folder_id

        except Exception as e:
            logger.error(f"Failed to get/create category folder '{category_name}': {e}")
            raise

    def move_document_to_folder(
        self,
        refresh_token_encrypted: str,
        file_id: str,
        new_folder_id: str
    ) -> bool:
        """
        Move document to a different folder.

        This is a Google Drive-specific helper method for backward compatibility.

        Args:
            refresh_token_encrypted: Encrypted refresh token
            file_id: Google Drive file ID to move
            new_folder_id: Target folder ID

        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_drive_service(refresh_token_encrypted)

            file = service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()

            previous_parents = ",".join(file.get('parents', []))

            service.files().update(
                fileId=file_id,
                addParents=new_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()

            logger.info(f"Document moved successfully: {file_id} to folder {new_folder_id}")
            return True

        except HttpError as e:
            logger.error(f"Failed to move document: {e}")
            return False
        except Exception as e:
            logger.error(f"Document move error: {e}")
            return False
