# backend/src/integrations/__init__.py
"""
Bonifatus DMS - Integrations Module
External service integrations and API clients
Google Drive, OCR, and other third-party services
"""

from .google_drive import GoogleDriveClient

__all__ = ["GoogleDriveClient"]
