# backend/app/core/google_config.py
"""
Bonifatus DMS - Google Drive API Configuration
Production-ready Google Drive integration with service account authentication
"""

import logging
import json
from typing import Optional, Dict, Any
from functools import lru_cache
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleDriveConfig:
    """Google Drive API configuration and service management"""

    def __init__(self):
        self._drive_service = None
        self._vision_service = None
        self._credentials = None
        self._drive_scopes = ['https://www.googleapis.com/auth/drive.file']
        self._vision_scopes = ['https://www.googleapis.com/auth/cloud-vision']

    @property
    def drive_service(self):
        """Get or create Google Drive service instance"""
        if self._drive_service is None:
            self._drive_service = self._build_service('drive', 'v3', 'drive')
        return self._drive_service

    @property
    def vision_service(self):
        """Get or create Google Vision service instance"""
        if self._vision_service is None:
            self._vision_service = self._build_service('vision', 'v1', 'vision')
        return self._vision_service

    @property
    def drive_credentials(self):
        """Get Drive-specific credentials"""
        return self._create_drive_credentials()

    @property
    def vision_credentials(self):
        """Get Vision-specific credentials"""  
        return self._create_vision_credentials()

    def _create_drive_credentials(self) -> Optional[Credentials]:
        """Create Drive service account credentials"""
        try:
            service_account_key = settings.google.google_drive_service_account_key
            
            if not service_account_key:
                logger.error("Google Drive service account key not configured")
                return None

            # Check if it's a mounted secret path
            if service_account_key.startswith('/secrets/'):
                with open(service_account_key, 'r') as f:
                    service_account_info = json.load(f)
                credentials = Credentials.from_service_account_info(
                    service_account_info, 
                    scopes=self._drive_scopes
                )
            elif service_account_key.endswith('.json'):
                credentials = Credentials.from_service_account_file(
                    service_account_key, 
                    scopes=self._drive_scopes
                )
            else:
                service_account_info = json.loads(service_account_key)
                credentials = Credentials.from_service_account_info(
                    service_account_info, 
                    scopes=self._drive_scopes
                )

            return credentials

        except Exception as e:
            logger.error(f"Failed to create Drive credentials: {e}")
            return None

    def _create_vision_credentials(self) -> Optional[Credentials]:
        """Create Vision service account credentials"""
        try:
            service_account_key = settings.google.google_drive_service_account_key
            
            if not service_account_key:
                return None

            if service_account_key.endswith('.json'):
                credentials = Credentials.from_service_account_file(
                    service_account_key, 
                    scopes=self._vision_scopes
                )
            else:
                service_account_info = json.loads(service_account_key)
                credentials = Credentials.from_service_account_info(
                    service_account_info, 
                    scopes=self._vision_scopes
                )

            return credentials

        except Exception as e:
            logger.error(f"Failed to create Vision credentials: {e}")
            return None

    def _build_service(self, service_name: str, version: str, credentials_type: str = "drive"):
        """Build Google API service with error handling"""
        try:
            if credentials_type == "drive":
                credentials = self.drive_credentials
            else:
                credentials = self.vision_credentials
                
            if not credentials:
                logger.error(f"Cannot build {service_name} service: credentials not available")
                return None

            service = build(
                service_name, 
                version, 
                credentials=credentials,
                cache_discovery=False
            )
            
            logger.info(f"Google {service_name} service v{version} created successfully")
            return service

        except Exception as e:
            logger.error(f"Failed to build {service_name} service: {e}")
            return None

    async def test_drive_connection(self) -> bool:
        """Test Google Drive API connection"""
        try:
            if not self.drive_service:
                return False

            result = self.drive_service.about().get(fields='storageQuota').execute()
            logger.info("Drive connection test successful")
            return True

        except HttpError as e:
            logger.error(f"Drive connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Drive connection test error: {e}")
            return False

    async def test_vision_connection(self) -> bool:
        """Test Google Vision API connection"""
        try:
            if not settings.google.google_vision_enabled:
                logger.info("Google Vision API disabled in configuration")
                return True

            if not self.vision_service:
                return False

            # Simple test - just check if service is accessible
            logger.info("Vision connection test successful")
            return True

        except HttpError as e:
            logger.error(f"Vision connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Vision connection test error: {e}")
            return False

    async def create_bonifatus_folder(self, user_email: str) -> Optional[str]:
        """Create Bonifatus DMS folder in user's Drive"""
        try:
            folder_name = settings.google.google_drive_folder_name
            
            existing_folder = await self.find_bonifatus_folder(user_email)
            if existing_folder:
                logger.info(f"Bonifatus folder already exists: {existing_folder}")
                return existing_folder

            if not self.drive_service:
                logger.error("Drive service not available")
                return None

            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'description': 'Bonifatus DMS Document Storage'
            }

            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            folder_id = folder.get('id')
            logger.info(f"Created Bonifatus folder for {user_email}: {folder_id}")
            return folder_id

        except HttpError as e:
            logger.error(f"Failed to create Bonifatus folder: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating Bonifatus folder: {e}")
            return None

    async def find_bonifatus_folder(self, user_email: str) -> Optional[str]:
        """Find existing Bonifatus DMS folder"""
        try:
            folder_name = settings.google.google_drive_folder_name
            
            if not self.drive_service:
                logger.error("Drive service not available")
                return None
            
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)',
                pageSize=1
            ).execute()

            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                logger.info(f"Found existing Bonifatus folder: {folder_id}")
                return folder_id

            return None

        except HttpError as e:
            logger.error(f"Failed to find Bonifatus folder: {e}")
            return None
        except Exception as e:
            logger.error(f"Error finding Bonifatus folder: {e}")
            return None

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of Google services"""
        drive_healthy = await self.test_drive_connection()
        vision_healthy = await self.test_vision_connection()
        
        return {
            "google_drive": {
                "status": "healthy" if drive_healthy else "unhealthy",
                "credentials": "configured" if self.drive_credentials else "missing",
                "service": "available" if self.drive_service else "unavailable"
            },
            "google_vision": {
                "status": "healthy" if vision_healthy else "unhealthy",
                "enabled": settings.google.google_vision_enabled,
                "service": "available" if self.vision_service else "unavailable"
            }
        }


@lru_cache()
def get_google_config() -> GoogleDriveConfig:
    """Get cached Google Drive configuration instance"""
    return GoogleDriveConfig()


# Global Google configuration instance
google_config = get_google_config()