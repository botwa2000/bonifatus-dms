# backend/app/services/google_drive_service.py
"""
Bonifatus DMS - Google Drive Integration Service
Production-ready file operations with Google Drive API
"""

import logging
import io
import mimetypes
from typing import Optional, Dict, Any, List, BinaryIO
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

from app.core.google_config import google_config
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Google Drive operations service"""

    def __init__(self):
        self.drive_service = google_config.drive_service
        self.folder_name = settings.google.google_drive_folder_name

    async def upload_document(
        self, 
        file_content: BinaryIO, 
        filename: str, 
        user_email: str,
        mime_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload document to user's Bonifatus folder in Google Drive
        
        Returns file metadata or None if upload fails
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return None

            folder_id = await self._ensure_user_folder(user_email)
            if not folder_id:
                logger.error(f"Failed to create/find folder for user: {user_email}")
                return None

            if not mime_type:
                mime_type, _ = mimetypes.guess_type(filename)
                if not mime_type:
                    mime_type = 'application/octet-stream'

            file_metadata = {
                'name': filename,
                'parents': [folder_id],
                'description': f'Uploaded via Bonifatus DMS for {user_email}'
            }

            media = MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True
            )

            file_result = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,mimeType,createdTime,modifiedTime,webViewLink'
            ).execute()

            logger.info(f"Document uploaded successfully: {file_result['id']} for user {user_email}")
            
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
            logger.error(f"Google Drive upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Document upload error: {e}")
            return None

    async def download_document(self, drive_file_id: str) -> Optional[io.BytesIO]:
        """
        Download document content from Google Drive
        
        Returns file content as BytesIO or None if download fails
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return None

            request = self.drive_service.files().get_media(fileId=drive_file_id)
            file_content = io.BytesIO()
            
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")

            file_content.seek(0)
            logger.info(f"Document downloaded successfully: {drive_file_id}")
            return file_content

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File not found in Google Drive: {drive_file_id}")
            else:
                logger.error(f"Google Drive download failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Document download error: {e}")
            return None

    async def get_document_metadata(self, drive_file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata from Google Drive
        
        Returns metadata dictionary or None if request fails
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return None

            file_metadata = self.drive_service.files().get(
                fileId=drive_file_id,
                fields='id,name,size,mimeType,createdTime,modifiedTime,webViewLink,trashed'
            ).execute()

            if file_metadata.get('trashed', False):
                logger.warning(f"File is in trash: {drive_file_id}")
                return None

            return {
                'drive_file_id': file_metadata['id'],
                'name': file_metadata['name'],
                'size': int(file_metadata.get('size', 0)),
                'mime_type': file_metadata['mimeType'],
                'created_time': file_metadata['createdTime'],
                'modified_time': file_metadata['modifiedTime'],
                'web_view_link': file_metadata.get('webViewLink'),
                'trashed': file_metadata.get('trashed', False)
            }

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File not found in Google Drive: {drive_file_id}")
            else:
                logger.error(f"Google Drive metadata request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Document metadata error: {e}")
            return None

    async def delete_document(self, drive_file_id: str) -> bool:
        """
        Delete document from Google Drive
        
        Returns True if successful, False otherwise
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return False

            self.drive_service.files().delete(fileId=drive_file_id).execute()
            logger.info(f"Document deleted successfully: {drive_file_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File not found for deletion: {drive_file_id}")
                return True  # Consider already deleted as success
            else:
                logger.error(f"Google Drive deletion failed: {e}")
                return False
        except Exception as e:
            logger.error(f"Document deletion error: {e}")
            return False

    async def list_user_documents(self, user_email: str, page_size: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        List all documents in user's Bonifatus folder
        
        Returns list of document metadata or None if request fails
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return None

            folder_id = await google_config.find_bonifatus_folder(user_email)
            if not folder_id:
                logger.info(f"No Bonifatus folder found for user: {user_email}")
                return []

            query = f"'{folder_id}' in parents and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id,name,size,mimeType,createdTime,modifiedTime)',
                pageSize=page_size,
                orderBy='modifiedTime desc'
            ).execute()

            files = results.get('files', [])
            
            documents = []
            for file_item in files:
                documents.append({
                    'drive_file_id': file_item['id'],
                    'name': file_item['name'],
                    'size': int(file_item.get('size', 0)),
                    'mime_type': file_item['mimeType'],
                    'created_time': file_item['createdTime'],
                    'modified_time': file_item['modifiedTime']
                })

            logger.info(f"Listed {len(documents)} documents for user: {user_email}")
            return documents

        except HttpError as e:
            logger.error(f"Google Drive list request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Document listing error: {e}")
            return None

    async def validate_file_access(self, drive_file_id: str, user_email: str) -> bool:
        """
        Validate that user has access to the specified file
        
        Returns True if user has access, False otherwise
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return False

            folder_id = await google_config.find_bonifatus_folder(user_email)
            if not folder_id:
                return False

            file_metadata = await self.get_document_metadata(drive_file_id)
            if not file_metadata:
                return False

            file_parents = self.drive_service.files().get(
                fileId=drive_file_id,
                fields='parents'
            ).execute()

            parents = file_parents.get('parents', [])
            has_access = folder_id in parents

            if not has_access:
                logger.warning(f"User {user_email} attempted access to unauthorized file: {drive_file_id}")

            return has_access

        except HttpError as e:
            logger.error(f"File access validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"File access validation error: {e}")
            return False

    async def update_document_name(self, drive_file_id: str, new_name: str) -> bool:
        """
        Update document name in Google Drive
        
        Returns True if successful, False otherwise
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return False

            self.drive_service.files().update(
                fileId=drive_file_id,
                body={'name': new_name}
            ).execute()

            logger.info(f"Document name updated: {drive_file_id} -> {new_name}")
            return True

        except HttpError as e:
            logger.error(f"Google Drive name update failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Document name update error: {e}")
            return False

    async def get_folder_storage_usage(self, user_email: str) -> int:
        """
        Calculate total storage used in user's Bonifatus folder
        
        Returns storage used in bytes
        """
        try:
            documents = await self.list_user_documents(user_email)
            if not documents:
                return 0

            total_size = sum(doc.get('size', 0) for doc in documents)
            logger.info(f"Storage usage for {user_email}: {total_size} bytes")
            return total_size

        except Exception as e:
            logger.error(f"Storage usage calculation error: {e}")
            return 0

    async def _ensure_user_folder(self, user_email: str) -> Optional[str]:
        """
        Ensure user has a Bonifatus folder, create if not exists
        
        Returns folder ID or None if creation fails
        """
        try:
            folder_id = await google_config.find_bonifatus_folder(user_email)
            if folder_id:
                return folder_id

            folder_id = await google_config.create_bonifatus_folder(user_email)
            return folder_id

        except Exception as e:
            logger.error(f"Failed to ensure user folder for {user_email}: {e}")
            return None

    async def get_service_health(self) -> Dict[str, Any]:
        """
        Get Google Drive service health status
        
        Returns health status dictionary
        """
        try:
            health_status = await google_config.get_health_status()
            return health_status

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "google_drive": {"status": "unhealthy", "error": str(e)},
                "google_vision": {"status": "unknown", "error": str(e)}
            }


# Global Google Drive service instance
google_drive_service = GoogleDriveService()