# backend/src/integrations/google_drive.py

import logging
import io
import json
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime, timedelta
import mimetypes
import asyncio
import aiohttp
from urllib.parse import urlencode, parse_qs, urlparse

from sqlalchemy.orm import Session
from src.database.models import User, Category
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleDriveClient:
    """Advanced Google Drive API client with full OAuth and file operations"""

    def __init__(self, db: Session = None, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self._user = None
        self._credentials = None
        self.service = None

        if self.db and self.user_id:
            self._user = self.db.query(User).filter(User.id == self.user_id).first()

    async def authenticate_user(self, auth_code: str) -> Dict[str, Any]:
        """Complete OAuth flow with Google Drive authorization code"""
        try:
            token_data = await self._exchange_code_for_tokens(auth_code)

            if not token_data.get("access_token"):
                return {"success": False, "error": "Failed to obtain access token"}

            user_info = await self._get_user_info(token_data["access_token"])

            if self._user:
                self._user.google_access_token = token_data["access_token"]
                self._user.google_refresh_token = token_data.get("refresh_token")
                self._user.google_token_expires_at = datetime.utcnow() + timedelta(
                    seconds=token_data.get("expires_in", 3600)
                )
                self._user.google_drive_connected = True
                self._user.google_user_email = user_info.get("email")
                self.db.commit()

            await self.initialize_user_folder()

            return {
                "success": True,
                "user_email": user_info.get("email"),
                "access_token": token_data["access_token"],
                "expires_in": token_data.get("expires_in", 3600),
            }

        except Exception as e:
            logger.error(
                f"Google Drive authentication failed for user {self.user_id}: {e}"
            )
            return {"success": False, "error": str(e)}

    async def refresh_access_token(self) -> bool:
        """Refresh expired Google access token"""
        try:
            if not self._user or not self._user.google_refresh_token:
                return False

            token_data = await self._refresh_token(self._user.google_refresh_token)

            if token_data.get("access_token"):
                self._user.google_access_token = token_data["access_token"]
                self._user.google_token_expires_at = datetime.utcnow() + timedelta(
                    seconds=token_data.get("expires_in", 3600)
                )
                self.db.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"Token refresh failed for user {self.user_id}: {e}")
            return False

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        user_id: int,
        category_name: str = "General",
        folder_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Upload file to Google Drive with resumable upload"""
        try:
            if not await self._ensure_valid_token():
                return None

            if not folder_id:
                folder_id = await self._get_or_create_category_folder(category_name)

            if not folder_id:
                logger.error(f"Failed to get folder for category {category_name}")
                return None

            upload_url = await self._create_resumable_upload(
                filename, mime_type, folder_id
            )

            if not upload_url:
                return None

            file_metadata = await self._perform_resumable_upload(
                upload_url, file_content
            )

            if file_metadata:
                logger.info(f"Successfully uploaded {filename} for user {user_id}")
                return {
                    "id": file_metadata["id"],
                    "name": file_metadata["name"],
                    "mimeType": file_metadata["mimeType"],
                    "size": file_metadata.get("size", len(file_content)),
                    "webViewLink": file_metadata.get("webViewLink"),
                    "webContentLink": file_metadata.get("webContentLink"),
                    "parents": file_metadata.get("parents", [folder_id]),
                    "createdTime": file_metadata.get("createdTime"),
                    "modifiedTime": file_metadata.get("modifiedTime"),
                }

            return None

        except Exception as e:
            logger.error(f"File upload failed for user {user_id}: {e}")
            return None

    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file content from Google Drive"""
        try:
            if not await self._ensure_valid_token():
                return None

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.read()
                    elif response.status == 403:
                        # Handle rate limiting
                        await asyncio.sleep(1)
                        async with session.get(url, headers=headers) as retry_response:
                            if retry_response.status == 200:
                                return await retry_response.read()

                    logger.error(f"Download failed with status {response.status}")
                    return None

        except Exception as e:
            logger.error(f"File download failed for {file_id}: {e}")
            return None

    async def get_download_url(self, file_id: str) -> Optional[str]:
        """Get temporary download URL for file"""
        try:
            if not await self._ensure_valid_token():
                return None

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=webContentLink,webViewLink"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        file_data = await response.json()
                        return file_data.get("webContentLink") or file_data.get(
                            "webViewLink"
                        )

            return None

        except Exception as e:
            logger.error(f"Get download URL failed for {file_id}: {e}")
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from Google Drive"""
        try:
            if not await self._ensure_valid_token():
                return False

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
                async with session.delete(url, headers=headers) as response:
                    if response.status in [200, 204, 404]:  # 404 means already deleted
                        logger.info(f"Deleted file {file_id} from Google Drive")
                        return True

                    logger.error(f"Delete failed with status {response.status}")
                    return False

        except Exception as e:
            logger.error(f"File deletion failed for {file_id}: {e}")
            return False

    async def move_file(self, file_id: str, new_folder_id: str) -> bool:
        """Move file to different folder"""
        try:
            if not await self._ensure_valid_token():
                return False

            current_parents = await self._get_file_parents(file_id)
            if not current_parents:
                return False

            headers = {
                "Authorization": f"Bearer {self._user.google_access_token}",
                "Content-Type": "application/json",
            }

            update_data = {
                "addParents": new_folder_id,
                "removeParents": ",".join(current_parents),
            }

            async with aiohttp.ClientSession() as session:
                url = (
                    f"https://www.googleapis.com/drive/v3/files/{file_id}?"
                    + urlencode(update_data)
                )
                async with session.patch(url, headers=headers) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Move file failed for {file_id}: {e}")
            return False

    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive file metadata"""
        try:
            if not await self._ensure_valid_token():
                return None

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}
            fields = "id,name,size,mimeType,createdTime,modifiedTime,webViewLink,webContentLink,parents,owners,permissions"

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields={fields}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()

            return None

        except Exception as e:
            logger.error(f"Get file metadata failed for {file_id}: {e}")
            return None

    async def list_files(
        self,
        folder_id: Optional[str] = None,
        page_size: int = 100,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files with advanced filtering"""
        try:
            if not await self._ensure_valid_token():
                return {"files": [], "nextPageToken": None}

            if not folder_id and self._user:
                folder_id = self._user.google_drive_folder_id

            q_parts = ["trashed=false"]

            if folder_id:
                q_parts.append(f"'{folder_id}' in parents")

            if query:
                q_parts.append(f"name contains '{query}'")

            params = {
                "q": " and ".join(q_parts),
                "pageSize": min(page_size, 1000),
                "fields": "files(id,name,size,mimeType,createdTime,modifiedTime,webViewLink),nextPageToken",
                "orderBy": "modifiedTime desc",
            }

            if page_token:
                params["pageToken"] = page_token

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files?" + urlencode(params)
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()

            return {"files": [], "nextPageToken": None}

        except Exception as e:
            logger.error(f"List files failed: {e}")
            return {"files": [], "nextPageToken": None}

    async def search_files(
        self, query: str, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Search files in user's Drive"""
        try:
            if not await self._ensure_valid_token():
                return []

            search_query = f"name contains '{query}' and trashed=false"

            if self._user and self._user.google_drive_folder_id:
                search_query += f" and '{self._user.google_drive_folder_id}' in parents"

            params = {
                "q": search_query,
                "pageSize": min(max_results, 1000),
                "fields": "files(id,name,size,mimeType,createdTime,modifiedTime,webViewLink)",
                "orderBy": "relevance",
            }

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files?" + urlencode(params)
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("files", [])

            return []

        except Exception as e:
            logger.error(f"Search files failed: {e}")
            return []

    async def get_storage_quota(self) -> Dict[str, Any]:
        """Get user's Google Drive storage quota information"""
        try:
            if not await self._ensure_valid_token():
                return {"limit": "0", "usage": "0"}

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = "https://www.googleapis.com/drive/v3/about?fields=storageQuota"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("storageQuota", {"limit": "0", "usage": "0"})

            return {"limit": "0", "usage": "0"}

        except Exception as e:
            logger.error(f"Get storage quota failed: {e}")
            return {"limit": "0", "usage": "0"}

    async def initialize_user_folder(self) -> bool:
        """Initialize Bonifatus DMS folder structure in user's Drive"""
        try:
            if not await self._ensure_valid_token():
                return False

            main_folder_id = await self._create_folder("Bonifatus DMS", None)

            if not main_folder_id:
                return False

            if self._user:
                self._user.google_drive_folder_id = main_folder_id
                self.db.commit()

            default_categories = await self._get_default_categories()

            for category in default_categories:
                await self._create_folder(category["name_en"], main_folder_id)

            logger.info(
                f"Initialized Google Drive folder structure for user {self.user_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Initialize user folder failed: {e}")
            return False

    async def check_connection(self) -> Dict[str, Any]:
        """Check Google Drive connection status"""
        try:
            if not self._user or not self._user.google_access_token:
                return {"connected": False, "error": "No access token"}

            if not await self._ensure_valid_token():
                return {"connected": False, "error": "Token refresh failed"}

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = "https://www.googleapis.com/drive/v3/about?fields=user"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        user_info = data.get("user", {})

                        storage_quota = await self.get_storage_quota()

                        return {
                            "connected": True,
                            "user_email": user_info.get("emailAddress"),
                            "user_name": user_info.get("displayName"),
                            "storage_quota": storage_quota,
                        }

            return {"connected": False, "error": "API request failed"}

        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return {"connected": False, "error": str(e)}

    async def sync_changes(self, page_token: Optional[str] = None) -> Dict[str, Any]:
        """Sync changes from Google Drive using Changes API"""
        try:
            if not await self._ensure_valid_token():
                return {"changes": [], "newStartPageToken": None}

            if not page_token:
                page_token = await self._get_start_page_token()

            params = {
                "pageToken": page_token,
                "fields": "changes(fileId,file(id,name,parents,trashed)),newStartPageToken,nextPageToken",
            }

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/changes?" + urlencode(
                    params
                )
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()

            return {"changes": [], "newStartPageToken": None}

        except Exception as e:
            logger.error(f"Sync changes failed: {e}")
            return {"changes": [], "newStartPageToken": None}

    async def share_file(
        self, file_id: str, email: str, role: str = "reader"
    ) -> Optional[Dict[str, Any]]:
        """Share file with another user"""
        try:
            if not await self._ensure_valid_token():
                return None

            permission_data = {"type": "user", "role": role, "emailAddress": email}

            headers = {
                "Authorization": f"Bearer {self._user.google_access_token}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
                async with session.post(
                    url, headers=headers, json=permission_data
                ) as response:
                    if response.status == 200:
                        return await response.json()

            return None

        except Exception as e:
            logger.error(f"Share file failed: {e}")
            return None

    # Private helper methods

    async def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token"""
        if not self._user or not self._user.google_access_token:
            return False

        if (
            self._user.google_token_expires_at
            and self._user.google_token_expires_at
            <= datetime.utcnow() + timedelta(minutes=5)
        ):
            return await self.refresh_access_token()

        return True

    async def _exchange_code_for_tokens(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        token_data = {
            "code": auth_code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://oauth2.googleapis.com/token", data=token_data
            ) as response:
                if response.status == 200:
                    return await response.json()

                error_data = await response.text()
                raise Exception(f"Token exchange failed: {error_data}")

    async def _refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        token_data = {
            "refresh_token": refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://oauth2.googleapis.com/token", data=token_data
            ) as response:
                if response.status == 200:
                    return await response.json()

                raise Exception(f"Token refresh failed: {response.status}")

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google"""
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/oauth2/v2/userinfo", headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()

                return {}

    async def _create_folder(
        self, name: str, parent_id: Optional[str]
    ) -> Optional[str]:
        """Create folder in Google Drive"""
        try:
            folder_metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }

            if parent_id:
                folder_metadata["parents"] = [parent_id]

            headers = {
                "Authorization": f"Bearer {self._user.google_access_token}",
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://www.googleapis.com/drive/v3/files",
                    headers=headers,
                    json=folder_metadata,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("id")

            return None

        except Exception as e:
            logger.error(f"Create folder failed: {e}")
            return None

    async def _get_or_create_category_folder(self, category_name: str) -> Optional[str]:
        """Get or create category folder"""
        try:
            if not self._user or not self._user.google_drive_folder_id:
                return None

            existing_folder = await self._find_folder(
                category_name, self._user.google_drive_folder_id
            )

            if existing_folder:
                return existing_folder

            return await self._create_folder(
                category_name, self._user.google_drive_folder_id
            )

        except Exception as e:
            logger.error(f"Get/create category folder failed: {e}")
            return None

    async def _find_folder(self, name: str, parent_id: str) -> Optional[str]:
        """Find folder by name in parent"""
        try:
            query = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"

            params = {"q": query, "fields": "files(id,name)"}

            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files?" + urlencode(params)
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        files = data.get("files", [])
                        if files:
                            return files[0]["id"]

            return None

        except Exception as e:
            logger.error(f"Find folder failed: {e}")
            return None

    async def _create_resumable_upload(
        self, filename: str, mime_type: str, folder_id: str
    ) -> Optional[str]:
        """Create resumable upload session"""
        try:
            file_metadata = {"name": filename, "parents": [folder_id]}

            headers = {
                "Authorization": f"Bearer {self._user.google_access_token}",
                "Content-Type": "application/json",
                "X-Upload-Content-Type": mime_type,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
                    headers=headers,
                    json=file_metadata,
                ) as response:
                    if response.status == 200:
                        return response.headers.get("Location")

            return None

        except Exception as e:
            logger.error(f"Create resumable upload failed: {e}")
            return None

    async def _perform_resumable_upload(
        self, upload_url: str, file_content: bytes
    ) -> Optional[Dict[str, Any]]:
        """Perform the actual resumable upload"""
        try:
            headers = {
                "Content-Range": f"bytes 0-{len(file_content)-1}/{len(file_content)}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.put(
                    upload_url, headers=headers, data=file_content
                ) as response:
                    if response.status == 200:
                        return await response.json()

            return None

        except Exception as e:
            logger.error(f"Resumable upload failed: {e}")
            return None

    async def _get_file_parents(self, file_id: str) -> List[str]:
        """Get current parent folders of a file"""
        try:
            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=parents"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("parents", [])

            return []

        except Exception as e:
            logger.error(f"Get file parents failed: {e}")
            return []

    async def _get_start_page_token(self) -> Optional[str]:
        """Get start page token for changes API"""
        try:
            headers = {"Authorization": f"Bearer {self._user.google_access_token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://www.googleapis.com/drive/v3/changes/startPageToken",
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("startPageToken")

            return None

        except Exception as e:
            logger.error(f"Get start page token failed: {e}")
            return None

    async def _get_default_categories(self) -> List[Dict[str, str]]:
        """Get default categories for folder creation from database"""
        if not self.db:
            logger.error("Database connection required for category retrieval")
            raise Exception("Database connection not available")

        try:
            categories = (
                self.db.query(Category).filter(Category.user_id.is_(None)).all()
            )

            if not categories:
                logger.warning("No system categories found in database")
                return []

            return [
                {"name_en": cat.name_en, "name_de": cat.name_de} for cat in categories
            ]

        except Exception as e:
            logger.error(f"Failed to retrieve categories from database: {e}")
            raise
