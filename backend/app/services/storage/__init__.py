"""
Multi-cloud storage provider package.

This package provides a unified interface for interacting with multiple
cloud storage providers (Google Drive, OneDrive, Dropbox, Box, etc.).
"""

from app.services.storage.base_provider import StorageProvider, UploadResult
from app.services.storage.provider_factory import ProviderFactory

__all__ = [
    'StorageProvider',
    'UploadResult',
    'ProviderFactory',
]
