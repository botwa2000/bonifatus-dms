"""
Storage provider management API endpoints.

Handles OAuth flows, provider connections, and multi-cloud storage management.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.connection import get_db
from app.database.models import User
from app.middleware.auth_middleware import get_current_active_user
from app.services.document_storage_service import document_storage_service
from app.services.storage.provider_factory import ProviderFactory
from app.core.config import settings
from app.core.security import encrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/storage", tags=["storage_providers"])


def _format_provider_name(provider_type: str) -> str:
    """Format provider type to display name."""
    name_map = {
        'google_drive': 'Google Drive',
        'onedrive': 'OneDrive',
        'dropbox': 'Dropbox',
        'box': 'Box'
    }
    return name_map.get(provider_type, provider_type.title())


def _is_provider_connected(user: User, provider_type: str) -> bool:
    """Check if user has connected a specific provider."""
    is_connected = document_storage_service.is_provider_connected(user, provider_type)
    logger.debug(f"🔍 Provider connection check - User: {user.id}, Provider: {provider_type}, Connected: {is_connected}")

    # Debug: Log the actual token status
    if provider_type == 'onedrive':
        logger.debug(f"🔍 OneDrive token encrypted: {user.onedrive_refresh_token_encrypted[:50] if user.onedrive_refresh_token_encrypted else 'None'}...")
        logger.debug(f"🔍 OneDrive enabled: {user.onedrive_enabled}")
        logger.debug(f"🔍 OneDrive connected_at: {user.onedrive_connected_at}")

    return is_connected


@router.get("/providers/available")
async def get_available_providers(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get list of all available storage providers with connection status.

    Returns provider information including:
    - type: Provider identifier
    - name: Display name
    - connected: Whether user has connected this provider
    - is_active: Whether this is the user's active provider
    - enabled: Whether this provider is enabled for user's tier
    """
    try:
        # Fetch fresh user data from database to get latest connection status
        fresh_user = db.query(User).filter(User.id == current_user.id).first()
        if not fresh_user:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"🔵 Getting available providers for user {fresh_user.id}")
        logger.debug(f"🔍 User active_storage_provider: {fresh_user.active_storage_provider}")

        # Get all registered providers
        all_providers = ProviderFactory.get_available_providers()
        logger.debug(f"🔍 Registered providers: {all_providers}")

        # For now, all providers are available (tier checking will be added later)
        # In production, this would call tier_service.get_available_providers()
        available_providers = all_providers

        provider_list = []
        for provider_type in available_providers:
            provider_info = {
                'type': provider_type,
                'name': _format_provider_name(provider_type),
                'connected': _is_provider_connected(fresh_user, provider_type),
                'is_active': fresh_user.active_storage_provider == provider_type,
                'enabled': True  # Will be tier-based later
            }
            logger.debug(f"📋 Provider info: {provider_info}")
            provider_list.append(provider_info)

        logger.info(f"✅ Returning {len(provider_list)} providers")
        return {'providers': provider_list}

    except Exception as e:
        logger.error(f"Failed to get available providers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve provider list")


@router.get("/providers/{provider_type}/connect-intent")
async def check_provider_connect_intent(
    provider_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Check if connecting this provider requires migration from another provider.

    This is called before the OAuth flow to determine if the user needs to
    choose between migrating existing documents or starting fresh.

    Args:
        provider_type: Provider identifier (google_drive, onedrive, etc.)

    Returns:
        needs_migration: Boolean indicating if migration is needed
        current_provider: Current active provider (if any)
        document_count: Number of documents on current provider
    """
    try:
        # Merge user into session
        current_user = db.merge(current_user)

        # Validate provider type
        if not ProviderFactory.is_provider_available(provider_type):
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {provider_type}"
            )

        # Check if user has another provider enabled
        current_provider = None
        if current_user.google_drive_enabled and provider_type != 'google_drive':
            current_provider = 'google_drive'
        elif current_user.onedrive_enabled and provider_type != 'onedrive':
            current_provider = 'onedrive'

        if not current_provider:
            return {
                'needs_migration': False,
                'current_provider': None,
                'document_count': 0
            }

        # Count documents on current provider
        from app.database.models import Document
        document_count = db.query(Document).filter(
            Document.user_id == current_user.id,
            Document.storage_provider_type == current_provider
        ).count()

        return {
            'needs_migration': True,
            'current_provider': current_provider,
            'document_count': document_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check connect intent for {provider_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check migration requirements")


@router.get("/providers/{provider_type}/authorize")
async def get_provider_authorization_url(
    provider_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get OAuth authorization URL for a storage provider.

    Args:
        provider_type: Provider identifier (google_drive, onedrive, etc.)

    Returns:
        authorization_url: URL to redirect user to for OAuth consent
    """
    try:
        # Validate provider type
        if not ProviderFactory.is_provider_available(provider_type):
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {provider_type}"
            )

        # TODO: Check tier access
        # has_access = await tier_service.can_use_provider(str(current_user.id), provider_type, db)
        # if not has_access:
        #     raise HTTPException(403, detail=f"{provider_type} requires Starter tier or higher")

        # Generate state parameter for CSRF protection
        state = f"{current_user.id}:{provider_type}"

        # Build redirect URI
        redirect_uri = f"{settings.app.app_frontend_url}/settings/storage/{provider_type}/callback"

        # Get authorization URL from provider
        auth_url = document_storage_service.get_authorization_url(
            provider_type=provider_type,
            state=state,
            redirect_uri=redirect_uri
        )

        return {
            'authorization_url': auth_url,
            'state': state
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate authorization URL for {provider_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")


@router.post("/providers/{provider_type}/callback")
async def provider_oauth_callback(
    provider_type: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    migration_choice: str = Query(None, description="Migration choice: 'migrate', 'fresh', or None"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from storage provider.

    This endpoint is called after the user authorizes the app.
    It exchanges the authorization code for access and refresh tokens.

    If migration_choice is provided and there's an existing provider with documents,
    the endpoint will either:
    - 'migrate': Create a migration task to move documents to the new provider
    - 'fresh': Disconnect the old provider and start fresh

    Args:
        provider_type: Provider identifier
        code: Authorization code
        state: State parameter (should match user_id:provider_type)
        migration_choice: Optional migration choice ('migrate' or 'fresh')

    Returns:
        success: True if connection successful
        provider: Provider type
        message: Success message
        migration_id: Optional UUID of migration task (if migration was initiated)
    """
    logger.info(f"🔵 OAuth callback START - Provider: {provider_type}, User: {current_user.id}, Code: {code[:10]}..., State: {state}")

    try:
        # Merge current_user into the db session to avoid "not persistent" error
        current_user = db.merge(current_user)

        # Validate state parameter
        expected_state = f"{current_user.id}:{provider_type}"
        logger.debug(f"🔍 Validating state - Expected: {expected_state}, Received: {state}")
        if state != expected_state:
            logger.error(f"❌ State validation failed - Expected: {expected_state}, Received: {state}")
            raise HTTPException(status_code=400, detail="Invalid state parameter - possible CSRF attack")

        # Validate provider
        if not ProviderFactory.is_provider_available(provider_type):
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_type}")

        # Build redirect URI (must match the one used in authorization)
        redirect_uri = f"{settings.app.app_frontend_url}/settings/storage/{provider_type}/callback"
        logger.debug(f"🔗 Redirect URI: {redirect_uri}")

        # Exchange code for tokens
        logger.info(f"🔄 Exchanging authorization code for tokens...")
        tokens = document_storage_service.exchange_code_for_tokens(
            provider_type=provider_type,
            code=code,
            redirect_uri=redirect_uri
        )
        logger.info(f"✅ Token exchange successful - Access token length: {len(tokens.get('access_token', ''))}, Has refresh token: {bool(tokens.get('refresh_token'))}")

        # Encrypt refresh token
        logger.debug(f"🔐 Encrypting refresh token...")
        refresh_token_encrypted = encrypt_token(tokens['refresh_token'])
        logger.debug(f"✅ Refresh token encrypted - Length: {len(refresh_token_encrypted)}")

        # Store tokens in database based on provider type
        logger.info(f"💾 Storing tokens for {provider_type} in database...")
        if provider_type == 'google_drive':
            current_user.drive_refresh_token_encrypted = refresh_token_encrypted
            current_user.google_drive_enabled = True
            current_user.drive_permissions_granted_at = datetime.utcnow()
            if not current_user.active_storage_provider:
                current_user.active_storage_provider = 'google_drive'
            logger.debug(f"✅ Google Drive fields updated - Enabled: {current_user.google_drive_enabled}, Active: {current_user.active_storage_provider}")

        elif provider_type == 'onedrive':
            logger.debug(f"💾 Setting OneDrive fields for user {current_user.id}...")
            logger.debug(f"🔍 Before - onedrive_enabled: {current_user.onedrive_enabled}, active_storage_provider: {current_user.active_storage_provider}")

            current_user.onedrive_refresh_token_encrypted = refresh_token_encrypted
            current_user.onedrive_enabled = True
            current_user.onedrive_connected_at = datetime.utcnow()
            if not current_user.active_storage_provider:
                current_user.active_storage_provider = 'onedrive'
                logger.debug(f"✅ Set active_storage_provider to 'onedrive' (was None)")
            else:
                logger.debug(f"ℹ️ active_storage_provider already set to: {current_user.active_storage_provider}")

            logger.debug(f"✅ OneDrive fields updated - Enabled: {current_user.onedrive_enabled}, Active: {current_user.active_storage_provider}")
            logger.debug(f"🔍 Token length: {len(refresh_token_encrypted)} chars")

        elif provider_type == 'dropbox':
            current_user.dropbox_refresh_token_encrypted = refresh_token_encrypted
            current_user.dropbox_enabled = True
            current_user.dropbox_connected_at = datetime.utcnow()
            if not current_user.active_storage_provider:
                current_user.active_storage_provider = 'dropbox'
            logger.debug(f"✅ Dropbox fields updated - Enabled: {current_user.dropbox_enabled}, Active: {current_user.active_storage_provider}")

        logger.info(f"💾 Committing database transaction...")
        db.commit()
        db.refresh(current_user)  # Refresh to get the latest state from database
        logger.info(f"✅ Database committed and refreshed")

        # Verify the data was actually saved
        if provider_type == 'onedrive':
            logger.debug(f"🔍 Post-commit verification:")
            logger.debug(f"  - onedrive_enabled: {current_user.onedrive_enabled}")
            logger.debug(f"  - onedrive_refresh_token_encrypted exists: {bool(current_user.onedrive_refresh_token_encrypted)}")
            logger.debug(f"  - onedrive_connected_at: {current_user.onedrive_connected_at}")
            logger.debug(f"  - active_storage_provider: {current_user.active_storage_provider}")

        # Initialize categories and folder structure if this is user's first storage provider
        try:
            from app.services.category_service import category_service
            from sqlalchemy import select, func
            from app.database.models import Category

            # Check if user has any categories
            category_count = db.execute(
                select(func.count(Category.id)).where(Category.user_id == current_user.id)
            ).scalar()

            logger.info(f"📁 User has {category_count} categories")

            if category_count == 0:
                logger.info(f"📋 Creating default categories for user {current_user.id}...")
                await category_service.restore_default_categories(
                    user_id=str(current_user.id),
                    ip_address=None
                )
                logger.info(f"✅ Default categories created")

            # Get category codes for folder initialization
            categories = db.execute(
                select(Category.category_code).where(
                    Category.user_id == current_user.id,
                    Category.is_active == True
                )
            ).scalars().all()

            category_codes = [cat for cat in categories if cat]
            logger.info(f"📂 Initializing {len(category_codes)} folders in {provider_type}...")

            # Initialize folder structure in the cloud storage
            folder_map = document_storage_service.initialize_folder_structure(
                user=current_user,
                folder_names=category_codes,
                provider_type=provider_type
            )
            logger.info(f"✅ Initialized {len(folder_map)} folders in {provider_type}")

        except Exception as init_error:
            logger.error(f"⚠️ Failed to initialize categories/folders: {init_error}", exc_info=True)
            # Don't fail the connection if folder initialization fails
            # User can manually create categories or we can retry later

        # Handle migration if user chose to migrate documents
        migration_id = None
        if migration_choice:
            logger.info(f"🔄 Migration choice: {migration_choice}")

            # Determine the old provider (the one being replaced)
            old_provider = None
            if current_user.google_drive_enabled and provider_type != 'google_drive':
                old_provider = 'google_drive'
            elif current_user.onedrive_enabled and provider_type != 'onedrive':
                old_provider = 'onedrive'

            if migration_choice == 'migrate' and old_provider:
                # Create migration task
                try:
                    from app.database.models import MigrationTask
                    import uuid

                    migration = MigrationTask(
                        id=uuid.uuid4(),
                        user_id=current_user.id,
                        from_provider=old_provider,
                        to_provider=provider_type,
                        status='pending'
                    )
                    db.add(migration)
                    db.commit()
                    db.refresh(migration)

                    migration_id = str(migration.id)
                    logger.info(f"✅ Created migration task: {migration_id}")

                    # Queue Celery task for async migration
                    from app.celery_app import migrate_provider_documents_task
                    task = migrate_provider_documents_task.delay(
                        migration_id=migration_id,
                        user_id=str(current_user.id)
                    )
                    logger.info(f"✅ Queued migration task: {task.id}")

                except Exception as migration_error:
                    logger.error(f"⚠️ Failed to create migration task: {migration_error}", exc_info=True)
                    # Don't fail the connection if migration creation fails

            elif migration_choice == 'fresh' and old_provider:
                # Disconnect old provider
                logger.info(f"🗑️ Disconnecting old provider: {old_provider}")
                try:
                    if old_provider == 'google_drive':
                        current_user.google_drive_enabled = False
                        current_user.drive_refresh_token_encrypted = None
                        current_user.google_drive_access_token_encrypted = None
                    elif old_provider == 'onedrive':
                        current_user.onedrive_enabled = False
                        current_user.onedrive_refresh_token_encrypted = None

                    # Update active provider to the new one
                    current_user.active_storage_provider = provider_type
                    db.commit()
                    logger.info(f"✅ Disconnected old provider: {old_provider}")
                except Exception as disconnect_error:
                    logger.error(f"⚠️ Failed to disconnect old provider: {disconnect_error}", exc_info=True)

        # Store user info before session cleanup
        user_email = current_user.email
        user_full_name = current_user.full_name
        user_marketing_enabled = current_user.email_marketing_enabled

        # Send email notification in a separate session to prevent rollback
        logger.info(f"📧 [EMAIL DEBUG] Starting email notification for provider connection...")
        logger.info(f"📧 [EMAIL DEBUG] User: {user_email}, Marketing enabled: {user_marketing_enabled}")
        try:
            from app.services.email_service import email_service
            from app.database.connection import SessionLocal

            logger.info(f"📧 [EMAIL DEBUG] Imports successful, creating session...")
            # Create a new session for email operation
            email_session = SessionLocal()
            logger.info(f"📧 [EMAIL DEBUG] Session created, preparing to send email...")
            try:
                dashboard_url = f"{settings.app.app_frontend_url}/dashboard"
                logger.info(f"📧 [EMAIL DEBUG] Calling send_storage_provider_connected_notification...")
                await email_service.send_storage_provider_connected_notification(
                    session=email_session,
                    to_email=user_email,
                    user_name=user_full_name,
                    provider_name=_format_provider_name(provider_type),
                    dashboard_url=dashboard_url,
                    user_can_receive_marketing=user_marketing_enabled
                )
                logger.info(f"✅ Sent connection notification email to {user_email}")
            finally:
                email_session.close()
                logger.info(f"📧 [EMAIL DEBUG] Email session closed")
        except Exception as email_error:
            logger.error(f"⚠️ Failed to send connection email: {email_error}", exc_info=True)
            # Don't fail the connection if email fails

        logger.info(f"✅ SUCCESS - User {current_user.id} connected {provider_type} successfully")

        response = {
            'success': True,
            'provider': provider_type,
            'message': f'{_format_provider_name(provider_type)} connected successfully'
        }

        # Add migration_id if migration was initiated
        if migration_id:
            response['migration_id'] = migration_id
            response['migration_status'] = 'pending'

        return response

    except HTTPException as he:
        logger.error(f"❌ HTTP Exception in OAuth callback - Status: {he.status_code}, Detail: {he.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ OAuth callback failed for {provider_type}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to complete OAuth connection")


@router.post("/providers/{provider_type}/activate")
async def activate_provider(
    provider_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Set a connected provider as the active storage provider.

    Args:
        provider_type: Provider to activate

    Returns:
        success: True if activation successful
        active_provider: The newly active provider
    """
    try:
        # Validate provider
        if not ProviderFactory.is_provider_available(provider_type):
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_type}")

        # Check if provider is connected
        if not _is_provider_connected(current_user, provider_type):
            raise HTTPException(
                status_code=400,
                detail=f"Please connect {_format_provider_name(provider_type)} before activating it"
            )

        # Set as active
        current_user.active_storage_provider = provider_type
        db.commit()

        logger.info(f"User {current_user.id} activated {provider_type}")

        return {
            'success': True,
            'active_provider': provider_type,
            'message': f'{_format_provider_name(provider_type)} is now your active storage provider'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate {provider_type}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to activate provider")


@router.post("/providers/{provider_type}/disconnect")
async def disconnect_provider(
    provider_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect a storage provider.

    This removes the stored tokens and disables the provider.
    If this is the active provider, the user will need to select a new one.

    Args:
        provider_type: Provider to disconnect

    Returns:
        success: True if disconnection successful
        message: Success message
    """
    try:
        # Validate provider
        if not ProviderFactory.is_provider_available(provider_type):
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_type}")

        # Check if provider is connected
        if not _is_provider_connected(current_user, provider_type):
            raise HTTPException(status_code=400, detail=f"Provider {provider_type} is not connected")

        # CRITICAL: Reload user from current session to ensure changes are tracked
        # current_user from auth middleware is detached from this session
        db_user = db.query(User).filter(User.id == current_user.id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Remove tokens based on provider type
        if provider_type == 'google_drive':
            db_user.drive_refresh_token_encrypted = None
            db_user.google_drive_enabled = False
            db_user.drive_permissions_granted_at = None

        elif provider_type == 'onedrive':
            db_user.onedrive_refresh_token_encrypted = None
            db_user.onedrive_enabled = False
            db_user.onedrive_connected_at = None

        elif provider_type == 'dropbox':
            db_user.dropbox_refresh_token_encrypted = None
            db_user.dropbox_enabled = False
            db_user.dropbox_connected_at = None

        # If this was the active provider, clear it
        if db_user.active_storage_provider == provider_type:
            db_user.active_storage_provider = None

        db.commit()
        logger.info(f"User {db_user.id} disconnected {provider_type}")

        # Store user info before session cleanup
        user_email = db_user.email
        user_full_name = db_user.full_name
        user_marketing_enabled = db_user.email_marketing_enabled
        user_id = db_user.id

        # Cancel any in-progress upload batches
        try:
            from app.database.models import UploadBatch
            from sqlalchemy import update

            # Mark in-progress batches as failed
            stmt = update(UploadBatch).where(
                UploadBatch.user_id == user_id,
                UploadBatch.status.in_(['processing', 'pending'])
            ).values(
                status='failed',
                error_message=f'Upload cancelled: {_format_provider_name(provider_type)} was disconnected'
            )
            result = db.execute(stmt)
            db.commit()

            if result.rowcount > 0:
                logger.info(f"⚠️ Cancelled {result.rowcount} in-progress upload batches due to provider disconnect")
        except Exception as batch_error:
            logger.error(f"⚠️ Failed to cancel in-progress batches: {batch_error}", exc_info=True)
            # Don't fail the disconnection if batch cleanup fails

        # Send email notification in a separate session to prevent rollback
        logger.info(f"📧 [EMAIL DEBUG] Starting email notification for provider disconnection...")
        logger.info(f"📧 [EMAIL DEBUG] User: {user_email}, Marketing enabled: {user_marketing_enabled}")
        try:
            from app.services.email_service import email_service
            from app.database.connection import SessionLocal

            logger.info(f"📧 [EMAIL DEBUG] Imports successful, creating session...")
            # Create a new session for email operation
            email_session = SessionLocal()
            logger.info(f"📧 [EMAIL DEBUG] Session created, preparing to send email...")
            try:
                dashboard_url = f"{settings.app.app_frontend_url}/settings"
                logger.info(f"📧 [EMAIL DEBUG] Calling send_storage_provider_disconnected_notification...")
                await email_service.send_storage_provider_disconnected_notification(
                    session=email_session,
                    to_email=user_email,
                    user_name=user_full_name,
                    provider_name=_format_provider_name(provider_type),
                    dashboard_url=dashboard_url,
                    user_can_receive_marketing=user_marketing_enabled
                )
                logger.info(f"✅ Sent disconnection notification email to {user_email}")
            finally:
                email_session.close()
                logger.info(f"📧 [EMAIL DEBUG] Email session closed")
        except Exception as email_error:
            logger.error(f"⚠️ Failed to send disconnection email: {email_error}", exc_info=True)
            # Don't fail the disconnection if email fails

        return {
            'success': True,
            'message': f'{_format_provider_name(provider_type)} disconnected successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect {provider_type}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to disconnect provider")


@router.get("/active-provider")
async def get_active_provider(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the user's currently active storage provider.

    Returns:
        active_provider: Provider type or null if none active
        provider_name: Display name of active provider
    """
    active = document_storage_service.get_active_provider(current_user)

    return {
        'active_provider': active,
        'provider_name': _format_provider_name(active) if active else None
    }


@router.get("/migration-status/{migration_id}")
async def get_migration_status(
    migration_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the status of a cloud storage provider migration task.

    This endpoint is polled by the frontend to show real-time progress
    during document migration.

    Args:
        migration_id: UUID of the migration task

    Returns:
        status: Migration status (pending, processing, completed, partial, failed)
        total_documents: Total number of documents to migrate
        processed_documents: Number of documents processed so far
        successful_documents: Number of successfully migrated documents
        failed_documents: Number of failed documents
        current_document: Name of document currently being processed
        results: Array of migration results (only when completed)
        folder_deleted: Whether the old provider's folder was deleted
    """
    try:
        from app.database.models import MigrationTask
        import uuid

        # Query migration task
        migration = db.query(MigrationTask).filter(
            MigrationTask.id == uuid.UUID(migration_id),
            MigrationTask.user_id == current_user.id  # Ensure user owns this migration
        ).first()

        if not migration:
            raise HTTPException(status_code=404, detail="Migration task not found")

        response = {
            'migration_id': str(migration.id),
            'status': migration.status,
            'from_provider': migration.from_provider,
            'to_provider': migration.to_provider,
            'total_documents': migration.total_documents,
            'processed_documents': migration.processed_documents,
            'successful_documents': migration.successful_documents,
            'failed_documents': migration.failed_documents,
            'current_document': migration.current_document_name,
            'started_at': migration.started_at.isoformat() if migration.started_at else None,
            'completed_at': migration.completed_at.isoformat() if migration.completed_at else None
        }

        # Include results only when migration is complete
        if migration.status in ['completed', 'partial', 'failed']:
            response['results'] = migration.results
            response['folder_deleted'] = migration.folder_deleted
            response['folder_deletion_attempted'] = migration.folder_deletion_attempted
            if migration.folder_deletion_error:
                response['folder_deletion_error'] = migration.folder_deletion_error

        # Include error message if failed
        if migration.error_message:
            response['error_message'] = migration.error_message

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get migration status for {migration_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve migration status")
