# backend/app/services/drive_service.py
"""
Google Drive integration service for folder management and file operations
"""

import logging
from typing import Optional, Dict, List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.security import decrypt_token

logger = logging.getLogger(__name__)


class DriveService:
    """Handles Google Drive folder structure and file operations"""

    def __init__(self):
        self.app_folder_name = settings.google.google_drive_folder_name  # "Bonifatus_DMS"

    def _get_drive_service(self, refresh_token_encrypted: str):
        """
        Create Google Drive API service with refresh token

        Args:
            refresh_token_encrypted: Encrypted refresh token from database

        Returns:
            Google Drive API service instance
        """
        try:
            # Decrypt the refresh token
            refresh_token = decrypt_token(refresh_token_encrypted)

            # Create credentials with refresh token
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google.google_client_id,
                client_secret=settings.google.google_client_secret,
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )

            # Build Drive API service
            service = build('drive', 'v3', credentials=credentials)
            return service

        except Exception as e:
            logger.error(f"Failed to create Drive service: {e}")
            raise

    def _create_folder(self, service, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive

        Args:
            service: Google Drive API service
            folder_name: Name of the folder to create
            parent_id: Parent folder ID (None for root)

        Returns:
            Folder ID of created folder
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
        Find a folder by name in Google Drive

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

    def initialize_folder_structure(
        self,
        refresh_token_encrypted: str,
        session: Session
    ) -> Dict[str, str]:
        """
        Initialize complete folder structure in Google Drive
        Creates main app folder and category folders

        Args:
            refresh_token_encrypted: Encrypted refresh token
            session: Database session to fetch categories

        Returns:
            Dict mapping folder names to their Drive IDs
        """
        try:
            service = self._get_drive_service(refresh_token_encrypted)
            folder_map = {}

            # 1. Create or find main app folder
            main_folder_id = self._find_folder(service, self.app_folder_name)
            if not main_folder_id:
                main_folder_id = self._create_folder(service, self.app_folder_name)

            folder_map['main'] = main_folder_id
            logger.info(f"Main folder '{self.app_folder_name}' ready: {main_folder_id}")

            # 2. Fetch all categories from database with English translations
            categories_result = session.execute(
                text("""
                    SELECT c.id, COALESCE(ct.name, c.reference_key) as name, c.category_code
                    FROM categories c
                    LEFT JOIN category_translations ct ON c.id = ct.category_id AND ct.language_code = 'en'
                    WHERE c.is_system = true
                    ORDER BY name
                """)
            )
            categories = categories_result.fetchall()

            # 3. Create category folders
            for category in categories:
                cat_id, cat_name, cat_code = category

                # Create folder with name format: "CategoryName (CODE)"
                folder_name = f"{cat_name} ({cat_code})"

                # Check if folder already exists
                category_folder_id = self._find_folder(service, folder_name, main_folder_id)
                if not category_folder_id:
                    category_folder_id = self._create_folder(service, folder_name, main_folder_id)

                folder_map[cat_code] = category_folder_id
                logger.info(f"Category folder '{folder_name}' ready: {category_folder_id}")

            # 4. Create config/metadata folder for app data
            config_folder_id = self._find_folder(service, ".config", main_folder_id)
            if not config_folder_id:
                config_folder_id = self._create_folder(service, ".config", main_folder_id)

            folder_map['config'] = config_folder_id
            logger.info(f"Config folder ready: {config_folder_id}")

            logger.info(f"Folder structure initialized successfully with {len(folder_map)} folders")
            return folder_map

        except Exception as e:
            logger.error(f"Failed to initialize folder structure: {e}")
            raise

    def get_or_create_category_folder(
        self,
        refresh_token_encrypted: str,
        category_name: str,
        category_code: str,
        main_folder_id: str
    ) -> str:
        """
        Get or create a category folder in Drive

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

            # Try to find existing folder
            folder_id = self._find_folder(service, folder_name, main_folder_id)
            if folder_id:
                return folder_id

            # Create new folder
            folder_id = self._create_folder(service, folder_name, main_folder_id)
            return folder_id

        except Exception as e:
            logger.error(f"Failed to get/create category folder '{category_name}': {e}")
            raise

    def upload_document(
        self,
        refresh_token_encrypted: str,
        file_content,
        filename: str,
        mime_type: str,
        folder_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Upload document to user's Google Drive

        Args:
            refresh_token_encrypted: Encrypted refresh token from user
            file_content: File content (BytesIO or file-like object)
            filename: Name of the file
            mime_type: MIME type of the file
            folder_id: Optional folder ID (uses main folder if not specified)

        Returns:
            Dict with file metadata (drive_file_id, name, size, web_view_link, etc.)
        """
        try:
            from googleapiclient.http import MediaIoBaseUpload

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

            media = MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True
            )

            file_result = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,mimeType,createdTime,modifiedTime,webViewLink'
            ).execute()

            logger.info(f"Document uploaded successfully: {file_result['id']}")

            return {
                'drive_file_id': file_result['id'],
                'name': file_result['name'],
                'size': int(file_result.get('size', 0)),
                'mime_type': file_result['mimeType'],
                'created_time': file_result['createdTime'],
                'modified_time': file_result['modifiedTime'],
                'web_view_link': file_result.get('webViewLink'),
                'folder_id': folder_id
            }

        except HttpError as e:
            logger.error(f"Failed to upload document '{filename}': {e}")
            return None
        except Exception as e:
            logger.error(f"Document upload error: {e}")
            return None

    def download_document(
        self,
        refresh_token_encrypted: str,
        drive_file_id: str
    ) -> Optional[bytes]:
        """
        Download document content from Google Drive

        Args:
            refresh_token_encrypted: Encrypted refresh token from user
            drive_file_id: Google Drive file ID

        Returns:
            File content as bytes, or None if download fails
        """
        try:
            import io
            from googleapiclient.http import MediaIoBaseDownload

            service = self._get_drive_service(refresh_token_encrypted)

            request = service.files().get_media(fileId=drive_file_id)
            file_content = io.BytesIO()

            downloader = MediaIoBaseDownload(file_content, request)
            done = False

            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")

            file_content.seek(0)
            logger.info(f"Document downloaded successfully: {drive_file_id}")
            return file_content.getvalue()

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File not found in Google Drive: {drive_file_id}")
            else:
                logger.error(f"Failed to download document: {e}")
            return None
        except Exception as e:
            logger.error(f"Document download error: {e}")
            return None

    def delete_document(
        self,
        refresh_token_encrypted: str,
        drive_file_id: str
    ) -> bool:
        """
        Delete document from Google Drive

        Args:
            refresh_token_encrypted: Encrypted refresh token from user
            drive_file_id: Google Drive file ID

        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_drive_service(refresh_token_encrypted)
            service.files().delete(fileId=drive_file_id).execute()
            logger.info(f"Document deleted successfully: {drive_file_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File not found for deletion: {drive_file_id}")
                return True  # Consider already deleted as success
            else:
                logger.error(f"Failed to delete document: {e}")
                return False
        except Exception as e:
            logger.error(f"Document deletion error: {e}")
            return False

    def move_document_to_folder(
        self,
        refresh_token_encrypted: str,
        drive_file_id: str,
        new_folder_id: str
    ) -> bool:
        """
        Move document to a different folder in Google Drive

        Args:
            refresh_token_encrypted: Encrypted refresh token from user
            drive_file_id: Google Drive file ID to move
            new_folder_id: Target folder ID

        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_drive_service(refresh_token_encrypted)

            # Get current file metadata including parents
            file = service.files().get(
                fileId=drive_file_id,
                fields='parents'
            ).execute()

            previous_parents = ",".join(file.get('parents', []))

            # Move file to new folder (remove from old, add to new)
            service.files().update(
                fileId=drive_file_id,
                addParents=new_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()

            logger.info(f"Document moved successfully: {drive_file_id} to folder {new_folder_id}")
            return True

        except HttpError as e:
            logger.error(f"Failed to move document: {e}")
            return False
        except Exception as e:
            logger.error(f"Document move error: {e}")
            return False


# Singleton instance
drive_service = DriveService()
