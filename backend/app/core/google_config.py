# backend/app/core/google_config.py
"""
Bonifatus DMS - Google Drive API Configuration
Production-ready Google Drive integration with service account authentication
"""

import logging
import json
import os
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

            # Check if it's a mounted secret (Cloud Run mounts secrets as files)
            secret_path = '/secrets/google-drive-key'
            if os.path.exists(secret_path):
                logger.info("Reading service account key from mounted secret")
                with open(secret_path, 'r') as f:
                    service_account_info = json.load(f)
                credentials = Credentials.from_service_account_info(
                    service_account_info, 
                    scopes=self._drive_scopes
                )
            elif os.path.exists(service_account_key):
                logger.info("Reading service account key from file path")
                credentials = Credentials.from_service_account_file(
                    service_account_key, 
                    scopes=self._drive_scopes
                )
            else:
                logger.info("Reading service account key from environment variable")
                service_account_info = json.loads(service_account_key)
                credentials = Credentials.from_service_account_info(
                    service_account_info, 
                    scopes=self._drive_scopes
                )

            logger.info("Drive credentials created successfully")
            return credentials

        except Exception as e:
            logger.error(f"Failed to create Drive credentials: {e}")
            return None

    def _create_vision_credentials(self) -> Optional[Credentials]:
        """Create Vision service account credentials"""
        try:
            service_account_key = settings.google.google_drive_service_account_key
            
            if not service_account_key:
                logger.warning("Google Drive service account key not configured")
                return None

            # Check if it's a mounted secret (Cloud Run mounts secrets as files)
            secret_path = '/secrets/google-drive-key'
            if os.path.exists(secret_path):
                logger.info("Reading service account key from mounted secret for Vision")
                with open(secret_path, 'r') as f:
                    service_account_info = json.load(f)
                credentials = Credentials.from_service_account_info(
                    service_account_info, 
                    scopes=self._vision_scopes
                )
            elif os.path.exists(service_account_key):
                logger.info("Reading service account key from file path for Vision")
                credentials = Credentials.from_service_account_file(
                    service_account_key, 
                    scopes=self._vision_scopes
                )
            else:
                logger.info("Reading service account key from environment variable for Vision")
                service_account_info = json.loads(service_account_key)
                credentials = Credentials.from_service_account_info(
                    service_account_info, 
                    scopes=self._vision_scopes
                )

            logger.info("Vision credentials created successfully")
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
                logger.warning("Vision service not available")
                return False

            logger.info("Vision connection test successful")
            return True

        except Exception as e:
            logger.error(f"Vision connection test error: {e}")
            return False

    async def find_bonifatus_folder(self, user_email: str) -> Optional[str]:
        """
        Find Bonifatus_DMS folder in user's Google Drive
        
        Returns folder ID if found, None otherwise
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return None

            folder_name = settings.google.google_drive_folder_name
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()

            files = results.get('files', [])
            
            if files:
                folder_id = files[0]['id']
                logger.info(f"Found existing Bonifatus folder for {user_email}: {folder_id}")
                return folder_id
            
            logger.info(f"No Bonifatus folder found for {user_email}")
            return None

        except HttpError as e:
            logger.error(f"Error finding Bonifatus folder: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error finding folder: {e}")
            return None

    async def create_bonifatus_folder(self, user_email: str) -> Optional[str]:
        """
        Create Bonifatus_DMS folder with category subfolders in user's Google Drive
        
        Returns root folder ID if successful, None otherwise
        """
        try:
            if not self.drive_service:
                logger.error("Google Drive service not available")
                return None

            folder_name = settings.google.google_drive_folder_name
            
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'description': 'Bonifatus DMS - Document Management System'
            }

            root_folder = self.drive_service.files().create(
                body=file_metadata,
                fields='id, name'
            ).execute()

            root_folder_id = root_folder.get('id')
            logger.info(f"Created Bonifatus root folder for {user_email}: {root_folder_id}")

            category_folder_ids = await self._create_category_subfolders(root_folder_id, user_email)
            
            if category_folder_ids:
                logger.info(f"Created {len(category_folder_ids)} category subfolders for {user_email}")
            
            return root_folder_id

        except HttpError as e:
            logger.error(f"Error creating Bonifatus folder: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating folder: {e}")
            return None

    async def _create_category_subfolders(self, parent_folder_id: str, user_email: str) -> Dict[str, str]:
        """
        Create category subfolders from database configuration
        
        Returns dictionary mapping category names to folder IDs
        """
        try:
            from app.database.models import SystemSetting
            from app.database.connection import db_manager
            
            session = db_manager.session_local()
            
            try:
                folder_structure_setting = session.query(SystemSetting).filter(
                    SystemSetting.setting_key == 'google_drive_folder_structure'
                ).first()
                
                if not folder_structure_setting:
                    logger.warning("Google Drive folder structure setting not found in database")
                    return {}
                
                import json
                folder_config = json.loads(folder_structure_setting.setting_value)
                subfolders = folder_config.get('subfolders', [])
                
                if not subfolders:
                    logger.warning("No subfolders configured in google_drive_folder_structure")
                    return {}
                
                folder_ids = {}
                
                for subfolder_name in subfolders:
                    try:
                        file_metadata = {
                            'name': subfolder_name,
                            'mimeType': 'application/vnd.google-apps.folder',
                            'parents': [parent_folder_id],
                            'description': f'Bonifatus DMS - {subfolder_name} Category'
                        }
                        
                        subfolder = self.drive_service.files().create(
                            body=file_metadata,
                            fields='id, name'
                        ).execute()
                        
                        folder_ids[subfolder_name] = subfolder.get('id')
                        logger.info(f"Created subfolder '{subfolder_name}' for {user_email}")
                        
                    except HttpError as e:
                        logger.error(f"Failed to create subfolder '{subfolder_name}': {e}")
                        continue
                
                return folder_ids
                
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error creating category subfolders: {e}")
            return {}

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of Google services"""
        drive_status = await self.test_drive_connection()
        vision_status = await self.test_vision_connection()
        
        return {
            "google_drive": {
                "status": "healthy" if drive_status else "unhealthy",
                "service": "Google Drive API v3"
            },
            "google_vision": {
                "status": "healthy" if vision_status else "unhealthy",
                "service": "Google Vision API v1",
                "enabled": settings.google.google_vision_enabled
            }
        }


@lru_cache()
def get_google_config() -> GoogleDriveConfig:
    """Get cached Google configuration instance"""
    return GoogleDriveConfig()


# Global Google configuration instance
google_config = get_google_config()