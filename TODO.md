# Multi-Cloud Storage Provider Implementation Plan

**Status:** Planning Complete - Ready for Implementation

**Last Updated:** 2024-12-24

**Target:** Phase 1 - OneDrive Integration | Future: Dropbox, Box, and other providers

---

## Executive Summary

### Objective
Transform Bonifatus DMS from a Google Drive-only system to a multi-cloud platform supporting OneDrive, Dropbox, Box, and other cloud storage providers. Users can select their preferred provider, with seamless migration between providers.

### Business Requirements
- **OneDrive Integration (Phase 1):** Must-have feature for competitive positioning
- **Scalable Architecture:** Easy addition of future providers (Dropbox, Box, etc.)
- **Tier-Based Access:** Cloud provider options are Pro tier features
- **One Active Provider:** Users select one provider at a time, can switch with migration
- **Admin Control:** Admins manage which providers are available per tier
- **Migration Tool:** Seamless document transfer between providers

### Current State
- Google Drive is hardcoded throughout the application
- OAuth flow, document upload/download, credentials storage all Google-specific
- No abstraction layer for storage operations
- TierPlan model has basic feature flags but no provider management

---

## Current Architecture Analysis

### Google Drive Integration Points

**OAuth Flow (`google_drive_service.py`):**
- Lines 47-82: `get_authorization_url()` - Google-specific OAuth URL generation
- Lines 84-136: `exchange_code_for_tokens()` - Google token exchange
- Lines 138-192: `refresh_access_token()` - Google token refresh
- Uses `google-auth`, `google-auth-oauthlib`, `googleapiclient` libraries

**Document Operations (`google_drive_service.py`):**
- Lines 194-280: `upload_document()` - Creates folder, uploads to Google Drive
- Lines 282-328: `download_document()` - Downloads from Google Drive
- Lines 330-367: `delete_document()` - Deletes from Google Drive
- Lines 369-415: `update_document()` - Updates existing document
- Lines 417-466: `move_document()` - Moves between folders

**Credentials Storage (`User` model):**
- `drive_refresh_token_encrypted` - AES-256 encrypted Google refresh token
- Single field assumes single provider
- No provider type indicator

**Database Schema (`Document` model):**
- `google_drive_file_id` - Provider-specific file ID
- Hardcoded to Google Drive
- No provider type field

**Frontend Integration:**
- Settings page: Google Drive connection UI
- OAuth callback handler: Google-specific
- Document upload: Assumes Google Drive

---

## Solution Architecture

### 1. Storage Provider Abstraction Layer

Create abstract base class with standard interface for all providers:

```python
# backend/app/services/storage/base_provider.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from dataclasses import dataclass

@dataclass
class StorageFile:
    """Standardized file metadata across all providers"""
    file_id: str
    name: str
    size_bytes: int
    mime_type: str
    created_at: datetime
    modified_at: datetime
    provider_type: str  # 'google_drive', 'onedrive', 'dropbox', etc.
    provider_metadata: Dict[str, Any]  # Provider-specific fields

@dataclass
class UploadResult:
    """Standardized upload result"""
    file_id: str
    name: str
    size_bytes: int
    provider_type: str
    provider_url: Optional[str] = None

class StorageProvider(ABC):
    """Abstract base class for cloud storage providers"""

    def __init__(self, provider_type: str):
        self.provider_type = provider_type

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL for this provider"""
        pass

    @abstractmethod
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access/refresh tokens"""
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token_encrypted: str) -> str:
        """Refresh access token using encrypted refresh token"""
        pass

    @abstractmethod
    def upload_document(
        self,
        refresh_token_encrypted: str,
        file_content: BinaryIO,
        file_name: str,
        mime_type: str,
        folder_name: Optional[str] = None
    ) -> UploadResult:
        """Upload document to provider storage"""
        pass

    @abstractmethod
    def download_document(
        self,
        refresh_token_encrypted: str,
        file_id: str
    ) -> bytes:
        """Download document from provider storage"""
        pass

    @abstractmethod
    def delete_document(
        self,
        refresh_token_encrypted: str,
        file_id: str
    ) -> bool:
        """Delete document from provider storage"""
        pass

    @abstractmethod
    def update_document(
        self,
        refresh_token_encrypted: str,
        file_id: str,
        file_content: BinaryIO,
        file_name: Optional[str] = None
    ) -> UploadResult:
        """Update existing document"""
        pass

    @abstractmethod
    def move_document(
        self,
        refresh_token_encrypted: str,
        file_id: str,
        new_folder_name: str
    ) -> bool:
        """Move document to different folder"""
        pass

    @abstractmethod
    def get_file_metadata(
        self,
        refresh_token_encrypted: str,
        file_id: str
    ) -> StorageFile:
        """Get file metadata"""
        pass
```

### 2. Provider Factory Pattern

```python
# backend/app/services/storage/provider_factory.py
from typing import Optional
from app.services.storage.base_provider import StorageProvider
from app.services.storage.google_drive_provider import GoogleDriveProvider
from app.services.storage.onedrive_provider import OneDriveProvider
# Future: from app.services.storage.dropbox_provider import DropboxProvider

class ProviderFactory:
    """Factory for creating storage provider instances"""

    _providers = {
        'google_drive': GoogleDriveProvider,
        'onedrive': OneDriveProvider,
        # Future: 'dropbox': DropboxProvider,
        # Future: 'box': BoxProvider,
    }

    @classmethod
    def create(cls, provider_type: str) -> StorageProvider:
        """Create provider instance by type"""
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unknown provider type: {provider_type}")
        return provider_class()

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider types"""
        return list(cls._providers.keys())

    @classmethod
    def register_provider(cls, provider_type: str, provider_class):
        """Register new provider type (for extensibility)"""
        cls._providers[provider_type] = provider_class
```

### 3. OneDrive Provider Implementation

**Microsoft Graph API Integration:**
- API Endpoint: `https://graph.microsoft.com/v1.0`
- OAuth 2.0 flow with Microsoft Identity Platform
- Scopes: `Files.ReadWrite.All`, `offline_access`
- Token endpoint: `https://login.microsoftonline.com/common/oauth2/v2.0/token`

**Key Implementation Points:**

```python
# backend/app/services/storage/onedrive_provider.py
import requests
from typing import Dict, Any, BinaryIO, Optional
from app.services.storage.base_provider import StorageProvider, UploadResult, StorageFile
from app.core.config import settings
from app.services.encryption import decrypt_field
import logging

logger = logging.getLogger(__name__)

class OneDriveProvider(StorageProvider):
    """Microsoft OneDrive storage provider implementation"""

    def __init__(self):
        super().__init__(provider_type='onedrive')
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.auth_base_url = "https://login.microsoftonline.com/common/oauth2/v2.0"
        self.client_id = settings.onedrive.client_id
        self.client_secret = settings.onedrive.client_secret
        self.redirect_uri = settings.onedrive.redirect_uri
        self.scopes = "Files.ReadWrite.All offline_access"

    def get_authorization_url(self, state: str) -> str:
        """Generate OneDrive OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.scopes,
            'state': state,
            'response_mode': 'query'
        }
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_base_url}/authorize?{query_string}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for tokens"""
        token_url = f"{self.auth_base_url}/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return response.json()  # Contains access_token, refresh_token, expires_in

    def refresh_access_token(self, refresh_token_encrypted: str) -> str:
        """Refresh OneDrive access token"""
        refresh_token = decrypt_field(refresh_token_encrypted)
        token_url = f"{self.auth_base_url}/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return response.json()['access_token']

    def upload_document(
        self,
        refresh_token_encrypted: str,
        file_content: BinaryIO,
        file_name: str,
        mime_type: str,
        folder_name: Optional[str] = None
    ) -> UploadResult:
        """Upload document to OneDrive"""
        access_token = self.refresh_access_token(refresh_token_encrypted)
        headers = {'Authorization': f'Bearer {access_token}'}

        # Create folder if needed
        if folder_name:
            folder_id = self._ensure_folder_exists(access_token, folder_name)
            upload_url = f"{self.graph_base_url}/me/drive/items/{folder_id}:/{file_name}:/content"
        else:
            upload_url = f"{self.graph_base_url}/me/drive/root:/{file_name}:/content"

        # Upload file
        headers['Content-Type'] = mime_type
        file_content.seek(0)
        response = requests.put(upload_url, headers=headers, data=file_content)
        response.raise_for_status()

        result = response.json()
        return UploadResult(
            file_id=result['id'],
            name=result['name'],
            size_bytes=result['size'],
            provider_type=self.provider_type,
            provider_url=result.get('webUrl')
        )

    def download_document(self, refresh_token_encrypted: str, file_id: str) -> bytes:
        """Download document from OneDrive"""
        access_token = self.refresh_access_token(refresh_token_encrypted)
        download_url = f"{self.graph_base_url}/me/drive/items/{file_id}/content"
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(download_url, headers=headers)
        response.raise_for_status()
        return response.content

    def delete_document(self, refresh_token_encrypted: str, file_id: str) -> bool:
        """Delete document from OneDrive"""
        access_token = self.refresh_access_token(refresh_token_encrypted)
        delete_url = f"{self.graph_base_url}/me/drive/items/{file_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.delete(delete_url, headers=headers)
        response.raise_for_status()
        return True

    def _ensure_folder_exists(self, access_token: str, folder_name: str) -> str:
        """Ensure folder exists, create if needed, return folder ID"""
        headers = {'Authorization': f'Bearer {access_token}'}
        search_url = f"{self.graph_base_url}/me/drive/root/children"
        params = {'$filter': f"name eq '{folder_name}' and folder ne null"}
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()

        items = response.json().get('value', [])
        if items:
            return items[0]['id']

        # Create folder
        create_url = f"{self.graph_base_url}/me/drive/root/children"
        data = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'fail'
        }
        response = requests.post(create_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['id']
```

---

## Database Schema Changes

### Migration 1: Add Provider Support to User Model

```python
# backend/app/models/user.py

class User(Base):
    __tablename__ = "users"

    # ... existing fields ...

    # Active storage provider
    active_storage_provider = Column(
        String,
        default='google_drive',
        nullable=False,
        comment="Active cloud storage provider: google_drive, onedrive, dropbox, etc."
    )

    # Google Drive tokens (existing)
    drive_refresh_token_encrypted = Column(Text, nullable=True)

    # OneDrive tokens (new)
    onedrive_refresh_token_encrypted = Column(Text, nullable=True)
    onedrive_connected_at = Column(DateTime(timezone=True), nullable=True)

    # Dropbox tokens (future)
    dropbox_refresh_token_encrypted = Column(Text, nullable=True)
    dropbox_connected_at = Column(DateTime(timezone=True), nullable=True)

    # Box tokens (future)
    box_refresh_token_encrypted = Column(Text, nullable=True)
    box_connected_at = Column(DateTime(timezone=True), nullable=True)
```

**Migration File:**
```python
# backend/alembic/versions/XXX_add_multi_provider_support.py
def upgrade():
    # Add active_storage_provider column
    op.add_column('users', sa.Column('active_storage_provider', sa.String(), nullable=True))
    op.execute("UPDATE users SET active_storage_provider = 'google_drive' WHERE drive_refresh_token_encrypted IS NOT NULL")
    op.alter_column('users', 'active_storage_provider', nullable=False)

    # Add OneDrive token fields
    op.add_column('users', sa.Column('onedrive_refresh_token_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('onedrive_connected_at', sa.DateTime(timezone=True), nullable=True))

    # Add Dropbox token fields (for future)
    op.add_column('users', sa.Column('dropbox_refresh_token_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('dropbox_connected_at', sa.DateTime(timezone=True), nullable=True))

    # Add Box token fields (for future)
    op.add_column('users', sa.Column('box_refresh_token_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('box_connected_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column('users', 'box_connected_at')
    op.drop_column('users', 'box_refresh_token_encrypted')
    op.drop_column('users', 'dropbox_connected_at')
    op.drop_column('users', 'dropbox_refresh_token_encrypted')
    op.drop_column('users', 'onedrive_connected_at')
    op.drop_column('users', 'onedrive_refresh_token_encrypted')
    op.drop_column('users', 'active_storage_provider')
```

### Migration 2: Update Document Model

```python
# backend/app/models/document.py

class Document(Base):
    __tablename__ = "documents"

    # ... existing fields ...

    # Rename google_drive_file_id to storage_file_id (backward compatible)
    storage_file_id = Column(
        String,
        nullable=False,
        comment="File ID in storage provider (formerly google_drive_file_id)"
    )

    # Add provider type
    storage_provider_type = Column(
        String,
        default='google_drive',
        nullable=False,
        comment="Storage provider: google_drive, onedrive, dropbox, etc."
    )

    # Keep old column name as alias for backward compatibility
    @hybrid_property
    def google_drive_file_id(self):
        return self.storage_file_id if self.storage_provider_type == 'google_drive' else None
```

**Migration File:**
```python
# backend/alembic/versions/XXX_update_document_storage_fields.py
def upgrade():
    # Rename google_drive_file_id to storage_file_id
    op.alter_column('documents', 'google_drive_file_id', new_column_name='storage_file_id')

    # Add storage_provider_type
    op.add_column('documents', sa.Column('storage_provider_type', sa.String(), nullable=True))
    op.execute("UPDATE documents SET storage_provider_type = 'google_drive'")
    op.alter_column('documents', 'storage_provider_type', nullable=False)

def downgrade():
    op.drop_column('documents', 'storage_provider_type')
    op.alter_column('documents', 'storage_file_id', new_column_name='google_drive_file_id')
```

### Migration 3: Provider Migration Tracking

```python
# backend/app/models/storage_migration.py

class StorageMigration(Base):
    __tablename__ = "storage_migrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Migration details
    from_provider = Column(String, nullable=False, comment="Source provider")
    to_provider = Column(String, nullable=False, comment="Destination provider")
    status = Column(
        String,
        nullable=False,
        default='pending',
        comment="pending, in_progress, completed, failed, cancelled"
    )

    # Progress tracking
    total_documents = Column(Integer, nullable=False, default=0)
    migrated_documents = Column(Integer, nullable=False, default=0)
    failed_documents = Column(Integer, nullable=False, default=0)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    failed_document_ids = Column(JSON, nullable=True, comment="Array of document IDs that failed")

    # Celery task ID for async processing
    celery_task_id = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="storage_migrations")

# Add to User model:
# storage_migrations = relationship("StorageMigration", back_populates="user", cascade="all, delete-orphan")
```

### Migration 4: Tier Provider Features

```python
# backend/app/models/tier_plan.py

class TierPlan(Base):
    __tablename__ = "tier_plans"

    # ... existing fields ...

    # Cloud provider features (new)
    google_drive_enabled = Column(Boolean, default=True, nullable=False, comment="Allow Google Drive")
    onedrive_enabled = Column(Boolean, default=False, nullable=False, comment="Allow OneDrive (Pro tier)")
    dropbox_enabled = Column(Boolean, default=False, nullable=False, comment="Allow Dropbox (future)")
    box_enabled = Column(Boolean, default=False, nullable=False, comment="Allow Box (future)")

    # Migration feature (Pro tier only)
    provider_migration_enabled = Column(Boolean, default=False, nullable=False, comment="Allow switching providers with migration")
```

**Default Tier Configuration:**
```python
# Free Tier:
google_drive_enabled = True
onedrive_enabled = False
dropbox_enabled = False
box_enabled = False
provider_migration_enabled = False

# Starter Tier:
google_drive_enabled = True
onedrive_enabled = True
dropbox_enabled = True
box_enabled = True
provider_migration_enabled = True

# Pro Tier:
google_drive_enabled = True
onedrive_enabled = True
dropbox_enabled = True
box_enabled = True
provider_migration_enabled = True
```

---

## Service Layer Refactoring

### 1. Refactor GoogleDriveService to GoogleDriveProvider

```python
# backend/app/services/storage/google_drive_provider.py
from app.services.storage.base_provider import StorageProvider, UploadResult, StorageFile
# ... move all GoogleDriveService logic here, implement abstract methods
```

### 2. Create Document Storage Service

```python
# backend/app/services/document_storage_service.py
from app.services.storage.provider_factory import ProviderFactory
from app.models.user import User
from typing import BinaryIO, Optional

class DocumentStorageService:
    """High-level document storage service using provider abstraction"""

    def upload_document(
        self,
        user: User,
        file_content: BinaryIO,
        file_name: str,
        mime_type: str,
        folder_name: Optional[str] = None
    ) -> UploadResult:
        """Upload document using user's active provider"""
        provider = ProviderFactory.create(user.active_storage_provider)
        refresh_token = self._get_refresh_token(user, user.active_storage_provider)

        return provider.upload_document(
            refresh_token_encrypted=refresh_token,
            file_content=file_content,
            file_name=file_name,
            mime_type=mime_type,
            folder_name=folder_name
        )

    def download_document(self, user: User, file_id: str, provider_type: str) -> bytes:
        """Download document using specified provider"""
        provider = ProviderFactory.create(provider_type)
        refresh_token = self._get_refresh_token(user, provider_type)

        return provider.download_document(
            refresh_token_encrypted=refresh_token,
            file_id=file_id
        )

    def _get_refresh_token(self, user: User, provider_type: str) -> str:
        """Get refresh token for provider"""
        if provider_type == 'google_drive':
            return user.drive_refresh_token_encrypted
        elif provider_type == 'onedrive':
            return user.onedrive_refresh_token_encrypted
        elif provider_type == 'dropbox':
            return user.dropbox_refresh_token_encrypted
        elif provider_type == 'box':
            return user.box_refresh_token_encrypted
        else:
            raise ValueError(f"Unknown provider: {provider_type}")
```

### 3. Provider Migration Service

```python
# backend/app/services/storage_migration_service.py
from app.models.storage_migration import StorageMigration
from app.models.document import Document
from app.services.document_storage_service import DocumentStorageService
from app.celery_app import celery_app
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class StorageMigrationService:
    """Handles migration of documents between storage providers"""

    def __init__(self, db):
        self.db = db
        self.storage_service = DocumentStorageService()

    def start_migration(self, user_id: str, from_provider: str, to_provider: str) -> StorageMigration:
        """Start async migration from one provider to another"""
        # Validate user has both providers connected
        user = self.db.query(User).filter(User.id == user_id).first()
        if not self._validate_providers(user, from_provider, to_provider):
            raise ValueError("Both providers must be connected before migration")

        # Count documents to migrate
        total_docs = self.db.query(Document).filter(
            Document.user_id == user_id,
            Document.storage_provider_type == from_provider
        ).count()

        # Create migration record
        migration = StorageMigration(
            user_id=user_id,
            from_provider=from_provider,
            to_provider=to_provider,
            status='pending',
            total_documents=total_docs,
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(migration)
        self.db.commit()

        # Start async Celery task
        task = migrate_documents_task.delay(str(migration.id))
        migration.celery_task_id = task.id
        self.db.commit()

        return migration

    def _validate_providers(self, user: User, from_provider: str, to_provider: str) -> bool:
        """Check user has both providers connected"""
        from_token = self._get_token(user, from_provider)
        to_token = self._get_token(user, to_provider)
        return from_token is not None and to_token is not None

    def _get_token(self, user: User, provider_type: str) -> Optional[str]:
        """Get refresh token for provider"""
        if provider_type == 'google_drive':
            return user.drive_refresh_token_encrypted
        elif provider_type == 'onedrive':
            return user.onedrive_refresh_token_encrypted
        # ... other providers
        return None

@celery_app.task(bind=True, max_retries=3)
def migrate_documents_task(self, migration_id: str):
    """Celery task to migrate documents in background"""
    db = next(get_db())
    migration = db.query(StorageMigration).filter(StorageMigration.id == migration_id).first()

    try:
        migration.status = 'in_progress'
        db.commit()

        # Get all documents for migration
        documents = db.query(Document).filter(
            Document.user_id == migration.user_id,
            Document.storage_provider_type == migration.from_provider
        ).all()

        user = db.query(User).filter(User.id == migration.user_id).first()
        storage_service = DocumentStorageService()

        for doc in documents:
            try:
                # Download from source provider
                file_content = storage_service.download_document(
                    user=user,
                    file_id=doc.storage_file_id,
                    provider_type=migration.from_provider
                )

                # Upload to destination provider
                from io import BytesIO
                upload_result = storage_service.upload_document(
                    user=user,
                    file_content=BytesIO(file_content),
                    file_name=doc.original_filename,
                    mime_type=doc.file_type,
                    folder_name=f"Bonifatus_DMS_{migration.to_provider}"
                )

                # Update document record
                doc.storage_file_id = upload_result.file_id
                doc.storage_provider_type = migration.to_provider

                # Delete from source provider
                provider = ProviderFactory.create(migration.from_provider)
                from_token = storage_service._get_refresh_token(user, migration.from_provider)
                provider.delete_document(from_token, doc.storage_file_id)

                migration.migrated_documents += 1
                db.commit()

                logger.info(f"Migrated document {doc.id}: {doc.original_filename}")

            except Exception as e:
                logger.error(f"Failed to migrate document {doc.id}: {str(e)}")
                migration.failed_documents += 1
                if migration.failed_document_ids is None:
                    migration.failed_document_ids = []
                migration.failed_document_ids.append(str(doc.id))
                db.commit()

        # Mark migration complete
        migration.status = 'completed'
        migration.completed_at = datetime.now(timezone.utc)

        # Update user's active provider
        user.active_storage_provider = migration.to_provider
        db.commit()

        logger.info(f"Migration {migration_id} completed: {migration.migrated_documents}/{migration.total_documents} successful")

    except Exception as e:
        migration.status = 'failed'
        migration.error_message = str(e)
        migration.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.error(f"Migration {migration_id} failed: {str(e)}")
        raise
```

---

## Tier Management Integration

### Update Tier Service

```python
# backend/app/services/tier_service.py

class TierService:
    # ... existing methods ...

    def get_available_providers(self, user: User) -> list[str]:
        """Get list of providers available to user based on tier"""
        tier = self.get_user_tier(user)
        providers = []

        if tier.google_drive_enabled:
            providers.append('google_drive')
        if tier.onedrive_enabled:
            providers.append('onedrive')
        if tier.dropbox_enabled:
            providers.append('dropbox')
        if tier.box_enabled:
            providers.append('box')

        return providers

    def can_use_provider(self, user: User, provider_type: str) -> bool:
        """Check if user's tier allows specific provider"""
        tier = self.get_user_tier(user)

        if provider_type == 'google_drive':
            return tier.google_drive_enabled
        elif provider_type == 'onedrive':
            return tier.onedrive_enabled
        elif provider_type == 'dropbox':
            return tier.dropbox_enabled
        elif provider_type == 'box':
            return tier.box_enabled

        return False

    def can_migrate_providers(self, user: User) -> bool:
        """Check if user can migrate between providers"""
        tier = self.get_user_tier(user)
        return tier.provider_migration_enabled
```

---

## API Endpoints

### 1. Provider Connection Endpoints

```python
# backend/app/api/storage_providers.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.services.storage.provider_factory import ProviderFactory
from app.services.tier_service import TierService

router = APIRouter(prefix="/api/v1/storage", tags=["storage"])

@router.get("/providers/available")
async def get_available_providers(
    current_user: User = Depends(get_current_user),
    tier_service: TierService = Depends()
):
    """Get list of providers available to user based on tier"""
    providers = tier_service.get_available_providers(current_user)

    return {
        'providers': [
            {
                'type': provider,
                'name': provider.replace('_', ' ').title(),
                'connected': _is_provider_connected(current_user, provider),
                'is_active': current_user.active_storage_provider == provider
            }
            for provider in providers
        ]
    }

@router.get("/providers/{provider_type}/authorize")
async def get_provider_authorization_url(
    provider_type: str,
    current_user: User = Depends(get_current_user),
    tier_service: TierService = Depends()
):
    """Get OAuth authorization URL for provider"""
    if not tier_service.can_use_provider(current_user, provider_type):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your tier does not include access to {provider_type}. Upgrade to Pro for multi-cloud support."
        )

    provider = ProviderFactory.create(provider_type)
    state = f"{current_user.id}:{provider_type}"
    auth_url = provider.get_authorization_url(state)

    return {'authorization_url': auth_url}

@router.post("/providers/{provider_type}/connect")
async def connect_provider(
    provider_type: str,
    code: str,
    current_user: User = Depends(get_current_user),
    tier_service: TierService = Depends(),
    db: Session = Depends(get_db)
):
    """Complete OAuth flow and save provider tokens"""
    if not tier_service.can_use_provider(current_user, provider_type):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your tier does not include access to {provider_type}"
        )

    provider = ProviderFactory.create(provider_type)
    tokens = provider.exchange_code_for_tokens(code)

    # Encrypt and save refresh token
    from app.services.encryption import encrypt_field
    encrypted_token = encrypt_field(tokens['refresh_token'])

    if provider_type == 'google_drive':
        current_user.drive_refresh_token_encrypted = encrypted_token
    elif provider_type == 'onedrive':
        current_user.onedrive_refresh_token_encrypted = encrypted_token
        current_user.onedrive_connected_at = datetime.now(timezone.utc)
    # ... other providers

    db.commit()

    return {'success': True, 'message': f'{provider_type} connected successfully'}

@router.post("/providers/{provider_type}/disconnect")
async def disconnect_provider(
    provider_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect provider (remove tokens)"""
    if current_user.active_storage_provider == provider_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disconnect active provider. Switch to another provider first."
        )

    if provider_type == 'google_drive':
        current_user.drive_refresh_token_encrypted = None
    elif provider_type == 'onedrive':
        current_user.onedrive_refresh_token_encrypted = None
        current_user.onedrive_connected_at = None
    # ... other providers

    db.commit()

    return {'success': True, 'message': f'{provider_type} disconnected'}

@router.post("/providers/{provider_type}/activate")
async def activate_provider(
    provider_type: str,
    current_user: User = Depends(get_current_user),
    tier_service: TierService = Depends(),
    db: Session = Depends(get_db)
):
    """Set provider as active (for new uploads)"""
    if not tier_service.can_use_provider(current_user, provider_type):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your tier does not include access to {provider_type}"
        )

    if not _is_provider_connected(current_user, provider_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please connect {provider_type} first"
        )

    current_user.active_storage_provider = provider_type
    db.commit()

    return {'success': True, 'message': f'{provider_type} is now your active provider'}

def _is_provider_connected(user: User, provider_type: str) -> bool:
    """Check if provider is connected"""
    if provider_type == 'google_drive':
        return user.drive_refresh_token_encrypted is not None
    elif provider_type == 'onedrive':
        return user.onedrive_refresh_token_encrypted is not None
    # ... other providers
    return False
```

### 2. Migration Endpoints

```python
# backend/app/api/storage_migration.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.services.storage_migration_service import StorageMigrationService
from app.models.storage_migration import StorageMigration

router = APIRouter(prefix="/api/v1/storage/migration", tags=["storage-migration"])

@router.post("/start")
async def start_migration(
    from_provider: str,
    to_provider: str,
    current_user: User = Depends(get_current_user),
    tier_service: TierService = Depends(),
    db: Session = Depends(get_db)
):
    """Start migration from one provider to another"""
    if not tier_service.can_migrate_providers(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider migration is a Pro tier feature. Please upgrade."
        )

    migration_service = StorageMigrationService(db)

    try:
        migration = migration_service.start_migration(
            user_id=str(current_user.id),
            from_provider=from_provider,
            to_provider=to_provider
        )

        return {
            'migration_id': str(migration.id),
            'status': migration.status,
            'total_documents': migration.total_documents,
            'message': f'Migration started. {migration.total_documents} documents will be transferred from {from_provider} to {to_provider}.'
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/status/{migration_id}")
async def get_migration_status(
    migration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get migration progress"""
    migration = db.query(StorageMigration).filter(
        StorageMigration.id == migration_id,
        StorageMigration.user_id == current_user.id
    ).first()

    if not migration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration not found")

    progress_percentage = 0
    if migration.total_documents > 0:
        progress_percentage = (migration.migrated_documents / migration.total_documents) * 100

    return {
        'migration_id': str(migration.id),
        'status': migration.status,
        'from_provider': migration.from_provider,
        'to_provider': migration.to_provider,
        'total_documents': migration.total_documents,
        'migrated_documents': migration.migrated_documents,
        'failed_documents': migration.failed_documents,
        'progress_percentage': round(progress_percentage, 2),
        'started_at': migration.started_at.isoformat() if migration.started_at else None,
        'completed_at': migration.completed_at.isoformat() if migration.completed_at else None,
        'error_message': migration.error_message
    }

@router.get("/history")
async def get_migration_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's migration history"""
    migrations = db.query(StorageMigration).filter(
        StorageMigration.user_id == current_user.id
    ).order_by(StorageMigration.started_at.desc()).limit(10).all()

    return {
        'migrations': [
            {
                'id': str(m.id),
                'from_provider': m.from_provider,
                'to_provider': m.to_provider,
                'status': m.status,
                'total_documents': m.total_documents,
                'migrated_documents': m.migrated_documents,
                'started_at': m.started_at.isoformat() if m.started_at else None,
                'completed_at': m.completed_at.isoformat() if m.completed_at else None
            }
            for m in migrations
        ]
    }
```

---

## Frontend Changes

### 1. Settings Page - Cloud Storage Section

```typescript
// frontend/components/settings/CloudStorageSettings.tsx
import React, { useState, useEffect } from 'react';

interface Provider {
  type: string;
  name: string;
  connected: boolean;
  is_active: boolean;
}

export default function CloudStorageSettings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    const response = await fetch('/api/v1/storage/providers/available');
    const data = await response.json();
    setProviders(data.providers);
    setLoading(false);
  };

  const handleConnect = async (providerType: string) => {
    const response = await fetch(`/api/v1/storage/providers/${providerType}/authorize`);
    const data = await response.json();
    window.location.href = data.authorization_url;
  };

  const handleActivate = async (providerType: string) => {
    await fetch(`/api/v1/storage/providers/${providerType}/activate`, { method: 'POST' });
    fetchProviders();
  };

  const handleDisconnect = async (providerType: string) => {
    await fetch(`/api/v1/storage/providers/${providerType}/disconnect`, { method: 'POST' });
    fetchProviders();
  };

  return (
    <div className="cloud-storage-settings">
      <h2>Cloud Storage Providers</h2>
      <p>Connect and manage your cloud storage providers. Your active provider will be used for new uploads.</p>

      <div className="providers-list">
        {providers.map(provider => (
          <div key={provider.type} className="provider-card">
            <div className="provider-info">
              <h3>{provider.name}</h3>
              <span className={`status ${provider.connected ? 'connected' : 'disconnected'}`}>
                {provider.connected ? 'Connected' : 'Not Connected'}
              </span>
              {provider.is_active && <span className="badge active">Active</span>}
            </div>

            <div className="provider-actions">
              {!provider.connected && (
                <button onClick={() => handleConnect(provider.type)} className="btn-primary">
                  Connect {provider.name}
                </button>
              )}

              {provider.connected && !provider.is_active && (
                <>
                  <button onClick={() => handleActivate(provider.type)} className="btn-secondary">
                    Set as Active
                  </button>
                  <button onClick={() => handleDisconnect(provider.type)} className="btn-danger">
                    Disconnect
                  </button>
                </>
              )}

              {provider.is_active && (
                <span className="active-notice">This is your active storage provider</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 2. Migration UI Component

```typescript
// frontend/components/settings/ProviderMigration.tsx
import React, { useState } from 'react';

interface MigrationProps {
  availableProviders: Provider[];
  currentProvider: string;
}

export default function ProviderMigration({ availableProviders, currentProvider }: MigrationProps) {
  const [targetProvider, setTargetProvider] = useState('');
  const [migrationId, setMigrationId] = useState<string | null>(null);
  const [migrationStatus, setMigrationStatus] = useState<any>(null);

  const startMigration = async () => {
    const response = await fetch('/api/v1/storage/migration/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from_provider: currentProvider,
        to_provider: targetProvider
      })
    });

    const data = await response.json();
    setMigrationId(data.migration_id);
    pollMigrationStatus(data.migration_id);
  };

  const pollMigrationStatus = async (id: string) => {
    const interval = setInterval(async () => {
      const response = await fetch(`/api/v1/storage/migration/status/${id}`);
      const data = await response.json();
      setMigrationStatus(data);

      if (data.status === 'completed' || data.status === 'failed') {
        clearInterval(interval);
      }
    }, 2000);
  };

  const connectedProviders = availableProviders.filter(p => p.connected && p.type !== currentProvider);

  return (
    <div className="provider-migration">
      <h2>Migrate to Different Provider</h2>

      {!migrationId && (
        <div>
          <p>Move all your documents from {currentProvider} to a different provider.</p>

          <select value={targetProvider} onChange={e => setTargetProvider(e.target.value)}>
            <option value="">Select target provider</option>
            {connectedProviders.map(p => (
              <option key={p.type} value={p.type}>{p.name}</option>
            ))}
          </select>

          <button onClick={startMigration} disabled={!targetProvider} className="btn-primary">
            Start Migration
          </button>
        </div>
      )}

      {migrationStatus && (
        <div className="migration-progress">
          <h3>Migration Progress</h3>
          <p>Status: {migrationStatus.status}</p>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${migrationStatus.progress_percentage}%` }}
            />
          </div>
          <p>
            {migrationStatus.migrated_documents} / {migrationStatus.total_documents} documents migrated
          </p>
          {migrationStatus.failed_documents > 0 && (
            <p className="error">{migrationStatus.failed_documents} documents failed</p>
          )}
        </div>
      )}
    </div>
  );
}
```

### 3. OAuth Callback Handler

```typescript
// frontend/pages/oauth/callback.tsx
import { useRouter } from 'next/router';
import { useEffect } from 'react';

export default function OAuthCallback() {
  const router = useRouter();
  const { code, state } = router.query;

  useEffect(() => {
    if (code && state) {
      completeOAuth();
    }
  }, [code, state]);

  const completeOAuth = async () => {
    const [userId, providerType] = (state as string).split(':');

    try {
      await fetch(`/api/v1/storage/providers/${providerType}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });

      router.push('/settings?success=provider_connected');
    } catch (error) {
      router.push('/settings?error=connection_failed');
    }
  };

  return <div>Connecting provider...</div>;
}
```

---

## Configuration Changes

### Environment Variables

```bash
# backend/.env

# OneDrive OAuth (Phase 1)
ONEDRIVE_CLIENT_ID=your_onedrive_client_id
ONEDRIVE_CLIENT_SECRET=your_onedrive_client_secret
ONEDRIVE_REDIRECT_URI=https://yourdomain.com/oauth/callback

# Dropbox OAuth (Future)
DROPBOX_APP_KEY=your_dropbox_app_key
DROPBOX_APP_SECRET=your_dropbox_app_secret
DROPBOX_REDIRECT_URI=https://yourdomain.com/oauth/callback

# Box OAuth (Future)
BOX_CLIENT_ID=your_box_client_id
BOX_CLIENT_SECRET=your_box_client_secret
BOX_REDIRECT_URI=https://yourdomain.com/oauth/callback
```

### Config File Updates

```python
# backend/app/core/config.py

class OneDriveSettings(BaseSettings):
    """OneDrive OAuth configuration"""

    onedrive_client_id: str = Field(..., env="ONEDRIVE_CLIENT_ID")
    onedrive_client_secret: str = Field(..., env="ONEDRIVE_CLIENT_SECRET")
    onedrive_redirect_uri: str = Field(..., env="ONEDRIVE_REDIRECT_URI")

    class Config:
        case_sensitive = False
        extra = "ignore"
        env_file = ".env"

class Settings(BaseSettings):
    # ... existing settings ...
    onedrive: OneDriveSettings = Field(default_factory=OneDriveSettings)
```

---

## Implementation Phases

### Phase 1: Foundation & Abstraction (Week 1-2)
**Goal:** Create provider abstraction layer and refactor Google Drive

**Tasks:**
1. Create `StorageProvider` abstract base class
2. Create `ProviderFactory`
3. Refactor `GoogleDriveService` to `GoogleDriveProvider` implementing abstract interface
4. Create `DocumentStorageService` using factory pattern
5. Database migration: Add `active_storage_provider` to User model
6. Database migration: Rename `google_drive_file_id` to `storage_file_id`, add `storage_provider_type`
7. Update all existing code to use `DocumentStorageService` instead of `GoogleDriveService`
8. Test thoroughly - ensure nothing breaks for existing users

**Testing:**
- All existing Google Drive functionality still works
- Document upload/download/delete works
- Delegate access still works
- No breaking changes for current users

---

### Phase 2: OneDrive Integration (Week 3-4)
**Goal:** Implement OneDrive provider and OAuth flow

**Tasks:**
1. Register app in Microsoft Azure Portal (get client ID/secret)
2. Implement `OneDriveProvider` class with all abstract methods
3. Add OneDrive config to `Settings` (client ID, secret, redirect URI)
4. Database migration: Add `onedrive_refresh_token_encrypted` to User model
5. Create API endpoints:
   - `GET /storage/providers/{provider}/authorize`
   - `POST /storage/providers/{provider}/connect`
   - `POST /storage/providers/{provider}/disconnect`
   - `POST /storage/providers/{provider}/activate`
6. Test OneDrive operations:
   - OAuth flow
   - Document upload to OneDrive
   - Document download from OneDrive
   - Document delete from OneDrive

**Testing:**
- OneDrive OAuth completes successfully
- Documents upload to OneDrive correctly
- Documents download from OneDrive
- Can switch between Google Drive and OneDrive as active provider
- Both providers work independently

---

### Phase 3: Tier Management & Provider Access (Week 5)
**Goal:** Integrate providers with tier system

**Tasks:**
1. Database migration: Add provider feature flags to `TierPlan`
   - `google_drive_enabled`
   - `onedrive_enabled`
   - `dropbox_enabled`
   - `box_enabled`
   - `provider_migration_enabled`
2. Update tier configurations:
   - Free: Google Drive only
   - Starter/Pro: All providers + migration
3. Implement `TierService` methods:
   - `get_available_providers(user)`
   - `can_use_provider(user, provider_type)`
   - `can_migrate_providers(user)`
4. Add permission checks to all provider endpoints
5. Frontend: Update pricing page to show multi-cloud as Pro feature
6. Frontend: Settings page shows available providers based on tier
7. Upgrade prompts for free users trying to access OneDrive

**Testing:**
- Free tier users only see Google Drive
- Pro tier users see all providers
- Upgrade prompts work correctly
- Permission checks prevent unauthorized access

---

### Phase 4: Migration Tool (Week 6-7)
**Goal:** Enable users to migrate documents between providers

**Tasks:**
1. Database migration: Create `StorageMigration` table
2. Implement `StorageMigrationService`
3. Implement Celery background task `migrate_documents_task`
4. Create migration API endpoints:
   - `POST /storage/migration/start`
   - `GET /storage/migration/status/{id}`
   - `GET /storage/migration/history`
5. Frontend: Migration UI component in Settings
6. Frontend: Real-time progress updates (polling or WebSocket)
7. Error handling and retry logic
8. Migration cancellation feature

**Testing:**
- Migrate 10 documents from Google Drive to OneDrive
- Migrate 100 documents (stress test)
- Test with large files (50+ MB)
- Test migration failure scenarios
- Test migration cancellation
- Verify all documents accessible after migration
- Verify source documents deleted after successful migration

---

### Phase 5: Production Deployment & Monitoring (Week 8)
**Goal:** Deploy to production with monitoring

**Tasks:**
1. Update documentation:
   - DEPLOYMENT_GUIDE.md
   - README.md
   - API documentation
2. Configure OneDrive OAuth in production Azure Portal
3. Set production environment variables
4. Run database migrations on production
5. Deploy backend changes
6. Deploy frontend changes
7. Monitor Celery workers for migration tasks
8. Set up monitoring/alerting:
   - Migration success/failure rates
   - Provider API errors
   - Token refresh failures
9. Create admin dashboard for monitoring provider usage
10. Load testing with real users

**Testing:**
- Smoke test all provider operations in production
- Monitor error logs for 48 hours
- Test OneDrive OAuth with real Microsoft accounts
- Migration monitoring and alerts working

---

## Future Phases (Post-OneDrive)

### Phase 6: Dropbox Integration
- Implement `DropboxProvider`
- Dropbox OAuth flow
- Database fields for Dropbox tokens
- Testing and production deployment

### Phase 7: Box Integration
- Implement `BoxProvider`
- Box OAuth flow
- Database fields for Box tokens
- Testing and production deployment

### Phase 8: Advanced Features
- Multi-provider support (documents across multiple providers simultaneously)
- Scheduled migrations (migrate overnight)
- Selective migration (migrate only certain documents)
- Cross-provider deduplication
- Provider cost analytics

---

## Security Considerations

### 1. Token Storage
- All refresh tokens MUST be encrypted with AES-256 before database storage
- Use existing `encrypt_field()` and `decrypt_field()` functions
- Never log refresh tokens or access tokens
- Tokens stored in separate columns per provider for isolation

### 2. OAuth Security
- Use PKCE (Proof Key for Code Exchange) for mobile apps (future)
- Validate state parameter to prevent CSRF attacks
- Use HTTPS for all OAuth redirects
- Short-lived access tokens (1 hour), long-lived refresh tokens

### 3. Provider API Security
- Rate limiting on provider API calls
- Exponential backoff on failures
- Token refresh before expiration (proactive refresh)
- Handle provider API quota limits gracefully

### 4. Migration Security
- Verify user owns both source and destination provider connections
- Atomic operations (rollback on failure)
- Audit trail for all migrations
- Prevent concurrent migrations for same user

### 5. Tier Enforcement
- Check tier permissions on every provider operation
- Cannot bypass tier limits via API
- Graceful degradation if user downgrades tier
- Clear upgrade prompts for feature access

---

## Testing Strategy

### Unit Tests
```python
# tests/test_storage_providers.py
def test_google_drive_provider_upload():
    provider = GoogleDriveProvider()
    # ... test upload logic

def test_onedrive_provider_upload():
    provider = OneDriveProvider()
    # ... test upload logic

def test_provider_factory():
    provider = ProviderFactory.create('google_drive')
    assert isinstance(provider, GoogleDriveProvider)

    provider = ProviderFactory.create('onedrive')
    assert isinstance(provider, OneDriveProvider)

# tests/test_storage_migration.py
def test_migration_service_start():
    # ... test migration start logic

def test_migration_task():
    # ... test Celery task
```

### Integration Tests
```python
# tests/integration/test_provider_oauth.py
def test_google_drive_oauth_flow():
    # ... test full OAuth flow

def test_onedrive_oauth_flow():
    # ... test full OAuth flow

# tests/integration/test_document_operations.py
def test_upload_to_onedrive():
    # ... test full upload flow

def test_download_from_onedrive():
    # ... test full download flow

def test_migration_google_to_onedrive():
    # ... test full migration flow
```

### E2E Tests
```typescript
// e2e/storage-providers.spec.ts
test('connect OneDrive provider', async () => {
  // ... test UI flow
});

test('switch active provider', async () => {
  // ... test provider switching
});

test('migrate documents', async () => {
  // ... test migration UI
});
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All database migrations created and tested
- [ ] All environment variables configured (dev and prod)
- [ ] OneDrive app registered in Azure Portal
- [ ] OAuth redirect URIs whitelisted
- [ ] All tests passing (unit, integration, E2E)
- [ ] Code review completed
- [ ] Documentation updated

### Deployment Steps
1. [ ] Run database migrations on production
2. [ ] Deploy backend with new code
3. [ ] Deploy frontend with new UI
4. [ ] Verify Celery workers running
5. [ ] Test OneDrive OAuth flow in production
6. [ ] Test document upload to OneDrive
7. [ ] Test migration with test account
8. [ ] Monitor logs for errors
9. [ ] Enable feature for limited users (beta)
10. [ ] Gradually roll out to all users

### Post-Deployment Monitoring
- [ ] Monitor migration task success rates
- [ ] Monitor provider API error rates
- [ ] Monitor OAuth completion rates
- [ ] Check Celery queue length
- [ ] Monitor database performance
- [ ] User feedback collection

---

## Risk Assessment

### High Risk
- **Data Loss During Migration:** Mitigation - Verify upload before deleting source, keep migration logs
- **OAuth Token Compromise:** Mitigation - Encrypt all tokens, never log tokens, rotate encryption keys
- **Provider API Changes:** Mitigation - Version pinning, comprehensive error handling, fallback strategies

### Medium Risk
- **Migration Failures:** Mitigation - Retry logic, user notifications, manual recovery tools
- **Tier Bypass:** Mitigation - Enforce permissions on every API call, audit logs
- **Performance Degradation:** Mitigation - Async processing, rate limiting, caching

### Low Risk
- **UI Confusion:** Mitigation - Clear documentation, in-app tooltips, user onboarding
- **Provider Deprecation:** Mitigation - Support multiple providers, easy migration

---

## Success Metrics

### Technical Metrics
- Migration success rate > 98%
- Provider API error rate < 1%
- OAuth completion rate > 95%
- Average migration time < 5 minutes per 100 documents

### Business Metrics
- OneDrive adoption rate among Pro users
- Conversion rate from free to Pro (multi-cloud feature)
- User retention after migration feature launch
- Support ticket reduction (fewer Google Drive issues)

---

## Next Steps

1. **Review and approve this plan**
2. **Set up OneDrive app in Azure Portal**
3. **Start Phase 1: Foundation & Abstraction**
4. **Weekly progress reviews**
5. **Beta testing with select users after Phase 2**

---

**Implementation Owner:** Development Team
**Stakeholders:** Product, Engineering, Support
**Timeline:** 8 weeks for OneDrive Phase 1, then ongoing for additional providers
**Status:** Ready for approval and implementation
