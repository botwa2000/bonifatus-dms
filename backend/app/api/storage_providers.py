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
    return document_storage_service.is_provider_connected(user, provider_type)


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
        # Get all registered providers
        all_providers = ProviderFactory.get_available_providers()

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
            provider_list.append(provider_info)

        return {'providers': provider_list}

    except Exception as e:
        logger.error(f"Failed to get available providers: {e}")
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
        redirect_uri = f"{settings.app.app_frontend_url}/settings/{provider_type}/callback"

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
    try:
        # Validate state parameter
        expected_state = f"{current_user.id}:{provider_type}"
        if state != expected_state:
            raise HTTPException(status_code=400, detail="Invalid state parameter - possible CSRF attack")

        # Validate provider
        if not ProviderFactory.is_provider_available(provider_type):
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_type}")

        # Build redirect URI (must match the one used in authorization)
        redirect_uri = f"{settings.app.app_frontend_url}/settings/{provider_type}/callback"

        # Exchange code for tokens
        tokens = document_storage_service.exchange_code_for_tokens(
            provider_type=provider_type,
            code=code,
            redirect_uri=redirect_uri
        )

        # Encrypt refresh token
        refresh_token_encrypted = encrypt_token(tokens['refresh_token'])

        # Store tokens in database based on provider type
        if provider_type == 'google_drive':
            current_user.drive_refresh_token_encrypted = refresh_token_encrypted
            current_user.google_drive_enabled = True
            current_user.drive_permissions_granted_at = datetime.utcnow()
            if not current_user.active_storage_provider:
                current_user.active_storage_provider = 'google_drive'

        elif provider_type == 'onedrive':
            current_user.onedrive_refresh_token_encrypted = refresh_token_encrypted
            current_user.onedrive_enabled = True
            current_user.onedrive_connected_at = datetime.utcnow()
            if not current_user.active_storage_provider:
                current_user.active_storage_provider = 'onedrive'

        elif provider_type == 'dropbox':
            current_user.dropbox_refresh_token_encrypted = refresh_token_encrypted
            current_user.dropbox_enabled = True
            current_user.dropbox_connected_at = datetime.utcnow()
            if not current_user.active_storage_provider:
                current_user.active_storage_provider = 'dropbox'

        db.commit()
        logger.info(f"User {current_user.id} connected {provider_type} successfully")

        return {
            'success': True,
            'provider': provider_type,
            'message': f'{_format_provider_name(provider_type)} connected successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed for {provider_type}: {e}")
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
