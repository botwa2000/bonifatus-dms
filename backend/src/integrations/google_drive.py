# backend/src/integrations/google_drive.py
"""
Bonifatus DMS - Google Drive Integration Client
Complete Google Drive API v3 integration for file operations
Folder management, file upload/download, and synchronization
"""

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, BinaryIO
import io
import json
import logging
from datetime import datetime

from src.database.models import User
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleDriveClient:
    """Google Drive API client for file operations"""
    
    def __init__(self, user_id: int, db: Session):
        self.user_id = user_id
        self.db = db
        self.service = None
        self._user = None
    
    async def _get_authenticated_service(self):
        """
        Get authenticated Google Drive service instance
        """
        try:
            if self.service:
                return self.service
            
            # Get user from database
            user = self.db.query(User).filter(User.id == self.user_id).first()
            if not user or not user.google_drive_token:
                logger.error(f"No Google Drive token for user {self.user_id}")
                return None
            
            self._user = user
            
            # Parse stored token
            token_data = user.google_drive_token
            if isinstance(token_data, str):
                token_data = json.loads(token_data)
            
            # Create credentials object
            credentials = Credentials(
                token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google.google_client_id,
                client_secret=settings.google.google_client_secret,
                scopes=settings.google.google_drive_scopes
            )
            
            # Refresh token if needed
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
                # Update stored token
                updated_token = {
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_type": "Bearer",
                    "expires_in": 3600
                }
                user.google_drive_token = updated_token
                self.db.commit()
                
                logger.info(f"Refreshed Google Drive token for user {self.user_id}")
            
            # Build service
            self.service = build("drive", "v3", credentials=credentials)
            return self.service
            
        except Exception as e:
            logger.error(f"Failed to authenticate Google Drive for user {self.user_id}: {e}")
            return None
    
    async def check_connection(self) -> Dict[str, Any]:
        """
        Check Google Drive connection status
        """
        try:
            service = await self._get_authenticated_service()
            if not service:
                return {
                    "connected": False,
                    "error": "No authentication available"
                }
            
            # Test connection with a simple API call
            about = service.about().get(fields="user,storageQuota").execute()
            
            return {
                "connected": True,
                "user_email": about["user"]["emailAddress"],
                "storage_quota": {
                    "limit": int(about["storageQuota"].get("limit", 0)),
                    "usage": int(about["storageQuota"].get("usage", 0)),
                    "usage_in_drive": int(about["storageQuota"].get("usageInDrive", 0))
                },
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except HttpError as e:
            logger.error(f"Google Drive API error for user {self.user_id}: {e}")
            return {
                "connected": False,
                "error": f"API Error: {e.resp.status}"
            }
        except Exception as e:
            logger.error(f"Google Drive connection check failed for user {self.user_id}: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def initialize_user_folder(self) -> bool:
        """
        Create Bonifatus DMS folder structure in user's Google Drive
        """
        try:
            service = await self._get_authenticated_service()
            if not service:
                return False
            
            # Check if main folder already exists
            if self._user and self._user.google_drive_folder_id:
                try:
                    service.files().get(fileId=self._user.google_drive_folder_id).execute()
                    logger.info(f"Bonifatus DMS folder already exists for user {self.user_id}")
                    return True
                except HttpError as e:
                    if e.resp.status == 404:
                        logger.warning(f"Stored folder ID invalid for user {self.user_id}, creating new")
                    else:
                        raise
            
            # Create main "Bonifatus DMS" folder
            main_folder_metadata = {
                "name": "Bonifatus DMS",
                "mimeType": "application/vnd.google-apps.folder",
                "description": "Document Management System - Organized by Categories"
            }
            
            main_folder = service.files().create(body=main_folder_metadata, fields="id").execute()
            main_folder_id = main_folder.get("id")
            
            if not main_folder_id:
                logger.error(f"Failed to create main folder for user {self.user_id}")
                return False
            
            # Create category subfolders
            default_categories = ["Finance", "Personal", "Business", "Legal", "Archive", "General"]
            
            for category_name in default_categories:
                category_folder_metadata = {
                    "name": category_name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [main_folder_id]
                }
                
                try:
                    service.files().create(body=category_folder_metadata, fields="id").execute()
                    logger.info(f"Created category folder '{category_name}' for user {self.user_id}")
                except HttpError as e:
                    logger.warning(f"Failed to create category folder '{category_name}': {e}")
            
            # Update user record with folder ID
            if self._user:
                self._user.google_drive_folder_id = main_folder_id
                self._user.google_drive_connected = True
                self.db.commit()
            
            logger.info(f"Initialized Google Drive folder structure for user {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive folder for user {self.user_id}: {e}")
            return False
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str,
        category_name: str = "General"
    ) -> Optional[Dict[str, Any]]:
        """
        Upload file to Google Drive in appropriate category folder
        """
        try:
            service = await self._get_authenticated_service()
            if not service:
                return None
            
            # Ensure user folder exists
            if not self._user or not self._user.google_drive_folder_id:
                if not await self.initialize_user_folder():
                    return None
            
            main_folder_id = self._user.google_drive_folder_id
            
            # Find or create category folder
            category_folder_id = await self._get_or_create_category_folder(
                service, category_name, main_folder_id
            )
            
            if not category_folder_id:
                logger.error(f"Failed to get category folder for {category_name}")
                return None
            
            # Prepare file metadata
            file_metadata = {
                "name": filename,
                "parents": [category_folder_id],
                "description": f"Uploaded via Bonifatus DMS on {datetime.utcnow().isoformat()}"
            }
            
            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(file_data),
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            file_result = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id,name,size,mimeType,createdTime,modifiedTime,webViewLink"
            ).execute()
            
            if file_result:
                logger.info(f"Successfully uploaded file {filename} for user {self.user_id}")
                return {
                    "file_id": file_result.get("id"),
                    "file_path": f"/{category_name}/{filename}",
                    "file_size": int(file_result.get("size", 0)),
                    "created_time": file_result.get("createdTime"),
                    "web_view_link": file_result.get("webViewLink")
                }
            
            return None
            
        except HttpError as e:
            logger.error(f"Google Drive upload error for user {self.user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"File upload failed for user {self.user_id}: {e}")
            return None
    
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Download file from Google Drive
        """
        try:
            service = await self._get_authenticated_service()
            if not service:
                return None
            
            # Get file
            request = service.files().get_media(fileId=file_id)
            file_data = io.BytesIO()
            
            downloader = MediaIoBaseDownload(file_data, request)
            done = False
            
            while not done:
                status, done = downloader.next_chunk()
            
            file_data.seek(0)
            return file_data.read()
            
        except HttpError as e:
            logger.error(f"Google Drive download error for file {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"File download failed for file {file_id}: {e}")
            return None
    
    async def get_download_url(self, file_id: str) -> Optional[str]:
        """
        Get temporary download URL for file
        """
        try:
            service = await self._get_authenticated_service()
            if not service:
                return None
            
            # Get file metadata with download link
            file_metadata = service.files().get(
                fileId=file_id,
                fields="webContentLink,webViewLink"
            ).execute()
            
            # Return direct download link if available
            return file_metadata.get("webContentLink") or file_metadata.get("webViewLink")
            
        except HttpError as e:
            logger.error(f"Failed to get download URL for file {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Get download URL failed for file {file_id}: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """
        Delete file from Google Drive
        """
        try:
            service = await self._get_authenticated_service()
            if not service:
                return False
            
            service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file {file_id} from Google Drive for user {self.user_id}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File {file_id} not found for deletion")
                return True  # Consider missing file as successfully deleted
            logger.error(f"Google Drive delete error for file {file_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"File deletion failed for file {file_id}: {e}")
            return False
    
    async def list_files(
        self,
        folder_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List files in Google Drive folder
        """
        try:
            service = await self._get_authenticated_service()
            if not service:
                return []
            
            # Use main folder if no specific folder provided
            if not folder_id and self._user:
                folder_id = self._user.google_drive_folder_id
            
            # Build query
            query = f"'{folder_id}' in parents and trashed=false" if folder_id else "trashed=false"
            
            results = service.files().list(
                q=query,
                pageSize=min(limit, 1000),
                fields="files(id,name,size,mimeType,createdTime,modifiedTime,parents)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get("files", [])
            
            return [
                {
                    "file_id": file_item.get("id"),
                    "name": file_item.get("name"),
                    "size": int(file_item.get("size", 0)) if file_item.get("size") else 0,
                    "mime_type": file_item.get("mimeType"),
                    "created_time": file_item.get("createdTime"),
                    "modified_time": file_item.get("modifiedTime"),
                    "parents": file_item.get("parents", [])
                }
                for file_item in files
            ]
            
        except HttpError as e:
            logger.error(f"Google Drive list files error for user {self.user_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"List files failed for user {self.user_id}: {e}")
            return []
    
    async def sync_changes(self, last_sync_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronize changes from Google Drive
        """
        try:
            service = await self._get_authenticated_service()
            if not service:
                return {"success": False, "error": "No authentication"}
            
            # Get changes since last sync
            if last_sync_token:
                changes_result = service.changes().list(
                    pageToken=last_sync_token,
                    fields="changes(file(id,name,size,mimeType,parents,trashed)),nextPageToken"
                ).execute()
            else:
                # Get initial sync token
                start_token = service.changes().getStartPageToken().execute()
                return {
                    "success": True,
                    "sync_token": start_token.get("startPageToken"),
                    "changes": []
                }
            
            changes = changes_result.get("changes", [])
            next_token = changes_result.get("nextPageToken")
            
            # Process changes
            processed_changes = []
            for change in changes:
                file_info = change.get("file")
                if file_info:
                    processed_changes.append({
                        "file_id": file_info.get("id"),
                        "name": file_info.get("name"),
                        "trashed": file_info.get("trashed", False),
                        "parents": file_info.get("parents", []),
                        "change_type": "deleted" if file_info.get("trashed") else "modified"
                    })
            
            return {
                "success": True,
                "sync_token": next_token,
                "changes": processed_changes
            }
            
        except HttpError as e:
            logger.error(f"Google Drive sync error for user {self.user_id}: {e}")
            return {"success": False, "error": f"API Error: {e.resp.status}"}
        except Exception as e:
            logger.error(f"Sync changes failed for user {self.user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_or_create_category_folder(
        self,
        service,
        category_name: str,
        parent_folder_id: str
    ) -> Optional[str]:
        """
        Get existing category folder or create new one
        """
        try:
            # Search for existing folder
            query = f"name='{category_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
            
            results = service.files().list(
                q=query,
                fields="files(id,name)"
            ).execute()
            
            existing_folders = results.get("files", [])
            
            if existing_folders:
                return existing_folders[0]["id"]
            
            # Create new category folder
            folder_metadata = {
                "name": category_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id]
            }
            
            folder = service.files().create(body=folder_metadata, fields="id").execute()
            return folder.get("id")
            
        except Exception as e:
            logger.error(f"Failed to get/create category folder '{category_name}': {e}")
            return None