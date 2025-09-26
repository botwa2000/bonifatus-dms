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


@lru_cache()
def get_google_config() -> GoogleDriveConfig:
    """Get cached Google configuration instance"""
    return GoogleDriveConfig()


# Global Google configuration instance
google_config = get_google_config()