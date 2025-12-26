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
        # Refresh user from database to get latest connection status
        db.refresh(current_user)

        logger.info(f"🔵 Getting available providers for user {current_user.id}")
        logger.debug(f"🔍 User active_storage_provider: {current_user.active_storage_provider}")

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
                'connected': _is_provider_connected(current_user, provider_type),
                'is_active': current_user.active_storage_provider == provider_type,
                'enabled': True  # Will be tier-based later
            }
            logger.debug(f"📋 Provider info: {provider_info}")
            provider_list.append(provider_info)

        logger.info(f"✅ Returning {len(provider_list)} providers")
        return {'providers': provider_list}

    except Exception as e:
        logger.error(f"Failed to get available providers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve provider list")


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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from storage provider.

    This endpoint is called after the user authorizes the app.
    It exchanges the authorization code for access and refresh tokens.

    Args:
        provider_type: Provider identifier
        code: Authorization code
        state: State parameter (should match user_id:provider_type)

    Returns:
        success: True if connection successful
        provider: Provider type
        message: Success message
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

        # Send email notification
        try:
            from app.services.email_service import email_service
            dashboard_url = f"{settings.app.app_frontend_url}/dashboard"
            await email_service.send_storage_provider_connected_notification(
                session=db,
                to_email=current_user.email,
                user_name=current_user.full_name,
                provider_name=_format_provider_name(provider_type),
                dashboard_url=dashboard_url,
                user_can_receive_marketing=current_user.email_marketing_enabled
            )
            logger.info(f"✅ Sent connection notification email to {current_user.email}")
        except Exception as email_error:
            logger.error(f"⚠️ Failed to send connection email: {email_error}", exc_info=True)
            # Don't fail the connection if email fails

        logger.info(f"✅ SUCCESS - User {current_user.id} connected {provider_type} successfully")

        return {
            'success': True,
            'provider': provider_type,
            'message': f'{_format_provider_name(provider_type)} connected successfully'
        }

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

        # Remove tokens based on provider type
        if provider_type == 'google_drive':
            current_user.drive_refresh_token_encrypted = None
            current_user.google_drive_enabled = False
            current_user.drive_permissions_granted_at = None

        elif provider_type == 'onedrive':
            current_user.onedrive_refresh_token_encrypted = None
            current_user.onedrive_enabled = False
            current_user.onedrive_connected_at = None

        elif provider_type == 'dropbox':
            current_user.dropbox_refresh_token_encrypted = None
            current_user.dropbox_enabled = False
            current_user.dropbox_connected_at = None

        # If this was the active provider, clear it
        if current_user.active_storage_provider == provider_type:
            current_user.active_storage_provider = None

        db.commit()
        logger.info(f"User {current_user.id} disconnected {provider_type}")

        # Cancel any in-progress upload batches
        try:
            from app.database.models import UploadBatch
            from sqlalchemy import update

            # Mark in-progress batches as failed
            stmt = update(UploadBatch).where(
                UploadBatch.user_id == current_user.id,
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

        # Send email notification
        try:
            from app.services.email_service import email_service
            dashboard_url = f"{settings.app.app_frontend_url}/settings"
            await email_service.send_storage_provider_disconnected_notification(
                session=db,
                to_email=current_user.email,
                user_name=current_user.full_name,
                provider_name=_format_provider_name(provider_type),
                dashboard_url=dashboard_url,
                user_can_receive_marketing=current_user.email_marketing_enabled
            )
            logger.info(f"✅ Sent disconnection notification email to {current_user.email}")
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
