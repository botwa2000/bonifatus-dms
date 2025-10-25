# backend/app/api/users.py
"""
Bonifatus DMS - User Management API Endpoints
REST API for user profile operations and settings management
"""

import logging
from typing import Optional, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from urllib.parse import urlencode

from app.schemas.user_schemas import (
    UserProfileUpdate, UserProfileResponse, UserStatistics,
    UserPreferences, UserPreferencesUpdate, AccountDeactivationRequest,
    AccountDeactivationResponse, UserDashboard, ErrorResponse
)
from app.services.user_service import user_service
from app.middleware.auth_middleware import get_current_active_user, get_client_ip
from app.database.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["user_management"])


@router.get(
    "/profile",
    response_model=UserProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserProfileResponse:
    """
    Get current user profile information
    
    Returns complete user profile with statistics and metadata
    """
    try:
        profile = await user_service.get_user_profile(str(current_user.id))
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        logger.info(f"Profile retrieved for user: {current_user.email}")
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve user profile"
        )


@router.put(
    "/profile",
    response_model=UserProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        400: {"model": ErrorResponse, "description": "Invalid profile data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_user_profile(
    request: Request,
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user)
) -> UserProfileResponse:
    """
    Update current user profile information
    
    Updates user profile fields and logs changes for audit trail
    """
    try:
        ip_address = get_client_ip(request)
        
        updated_profile = await user_service.update_user_profile(
            str(current_user.id), profile_update, ip_address
        )
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user profile"
            )
        
        logger.info(f"Profile updated for user: {current_user.email}")
        return updated_profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update user profile"
        )


@router.get(
    "/statistics",
    response_model=UserStatistics,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_user_statistics(
    current_user: User = Depends(get_current_active_user)
) -> UserStatistics:
    """
    Get user statistics and usage information
    
    Returns document count, storage usage, and activity metrics
    """
    try:
        statistics = await user_service.get_user_statistics(str(current_user.id))
        
        if not statistics:
            # Return empty statistics if none found
            statistics = UserStatistics(
                documents_count=0,
                categories_count=0,
                storage_used_mb=0,
                last_activity=None
            )
        
        logger.info(f"Statistics retrieved for user: {current_user.email}")
        return statistics
        
    except Exception as e:
        logger.error(f"Get user statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve user statistics"
        )


@router.get(
    "/preferences",
    response_model=UserPreferences,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_user_preferences(
    current_user: User = Depends(get_current_active_user)
) -> UserPreferences:
    """
    Get user preferences and settings
    
    Returns user preferences with defaults from system settings
    """
    try:
        preferences = await user_service.get_user_preferences(str(current_user.id))
        
        logger.info(f"Preferences retrieved for user: {current_user.email}")
        return preferences
        
    except Exception as e:
        logger.error(f"Get user preferences error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve user preferences"
        )


@router.put(
    "/preferences",
    response_model=UserPreferences,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        400: {"model": ErrorResponse, "description": "Invalid preferences data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_user_preferences(
    request: Request,
    preferences_update: UserPreferencesUpdate,
    current_user: User = Depends(get_current_active_user)
) -> UserPreferences:
    """
    Update user preferences and settings
    
    Updates user preferences and logs changes for audit trail
    """
    try:
        ip_address = get_client_ip(request)
        
        updated_preferences = await user_service.update_user_preferences(
            str(current_user.id), preferences_update, ip_address
        )
        
        if not updated_preferences:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user preferences"
            )
        
        logger.info(f"Preferences updated for user: {current_user.email}")
        return updated_preferences
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Update user preferences error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update user preferences"
        )


@router.post(
    "/preferences/reset",
    response_model=UserPreferences,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def reset_user_preferences(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> UserPreferences:
    """
    Reset user preferences to system default values
    
    Resets all user preferences to system defaults from database
    """
    try:
        ip_address = get_client_ip(request)
        
        updated_preferences = await user_service.reset_user_preferences_to_defaults(
            str(current_user.id), ip_address
        )
        
        if not updated_preferences:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset user preferences"
            )
        
        logger.info(f"Preferences reset for user: {current_user.email}")
        return updated_preferences
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset user preferences error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to reset user preferences"
        )


@router.get(
    "/dashboard",
    response_model=UserDashboard,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_user_dashboard(
    current_user: User = Depends(get_current_active_user)
) -> UserDashboard:
    """
    Get complete user dashboard data
    
    Returns profile, statistics, preferences, and recent activity
    """
    try:
        dashboard = await user_service.get_user_dashboard(str(current_user.id))
        
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User dashboard data not found"
            )
        
        logger.info(f"Dashboard retrieved for user: {current_user.email}")
        return dashboard
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve user dashboard"
        )


@router.post(
    "/deactivate",
    response_model=AccountDeactivationResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        400: {"model": ErrorResponse, "description": "Invalid deactivation request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def deactivate_user_account(
    request: Request,
    deactivation_request: AccountDeactivationRequest,
    current_user: User = Depends(get_current_active_user)
) -> AccountDeactivationResponse:
    """
    Deactivate current user account
    
    Deactivates user account and schedules data retention per system settings
    """
    try:
        ip_address = get_client_ip(request)
        
        deactivation_result = await user_service.deactivate_user_account(
            str(current_user.id), deactivation_request, ip_address
        )
        
        if not deactivation_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate user account"
            )
        
        logger.info(f"Account deactivated for user: {current_user.email}")
        return deactivation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deactivate user account error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to deactivate user account"
        )


@router.get(
    "/drive/status",
    responses={
        200: {"description": "Drive connection status"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_drive_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Get Google Drive connection status for current user

    Returns connection status, connected email, and permissions info
    """
    try:
        status_data = {
            "connected": current_user.google_drive_enabled,
            "email": current_user.email if current_user.google_drive_enabled else None,
            "connected_at": current_user.drive_permissions_granted_at.isoformat() if current_user.drive_permissions_granted_at else None,
            "token_expires_at": current_user.drive_token_expires_at.isoformat() if current_user.drive_token_expires_at else None
        }

        logger.info(f"Drive status retrieved for user: {current_user.email}")
        return status_data

    except Exception as e:
        logger.error(f"Get drive status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve Drive status"
        )


@router.get(
    "/drive/connect",
    responses={
        302: {"description": "Redirect to Google OAuth for Drive permissions"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "OAuth initialization failed"}
    }
)
async def connect_google_drive(
    current_user: User = Depends(get_current_active_user)
):
    """
    Initiate Google OAuth flow for Drive permissions

    Redirects user to Google OAuth with Drive API scope
    """
    try:
        # Build Google OAuth URL with Drive scope
        oauth_params = {
            "client_id": settings.google.google_client_id,
            "redirect_uri": f"{settings.app.app_frontend_url}/settings/drive/callback",
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive.file",  # Drive file scope
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
            "state": str(current_user.id),  # User ID for callback
            "login_hint": current_user.email  # Pre-fill email
        }

        oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(oauth_params)}"

        logger.info(f"Redirecting to Google Drive OAuth for user: {current_user.email}")
        return RedirectResponse(url=oauth_url, status_code=status.HTTP_302_FOUND)

    except Exception as e:
        logger.error(f"Drive OAuth initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth initialization failed"
        )


@router.post(
    "/drive/callback",
    responses={
        200: {"description": "Drive connection successful"},
        400: {"model": ErrorResponse, "description": "Invalid OAuth code"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def drive_oauth_callback(
    code: str,
    state: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Complete Google Drive OAuth flow and store refresh token

    Exchanges OAuth code for tokens and saves refresh token for Drive API access
    """
    try:
        # Verify state matches user ID
        if state != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state"
            )

        # Exchange code for tokens
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google.google_client_id,
                    "client_secret": settings.google.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [f"{settings.app.app_frontend_url}/settings/drive/callback"]
                }
            },
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )

        flow.redirect_uri = f"{settings.app.app_frontend_url}/settings/drive/callback"
        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Store encrypted refresh token
        from app.core.security import encrypt_token
        encrypted_token = encrypt_token(credentials.refresh_token)

        # Update user record and initialize folder structure
        from app.database.connection import db_manager
        from app.services.drive_service import drive_service

        session = db_manager.session_local()
        try:
            user = session.query(User).filter(User.id == current_user.id).first()
            user.drive_refresh_token_encrypted = encrypted_token
            user.drive_token_expires_at = credentials.expiry
            user.google_drive_enabled = True
            user.drive_permissions_granted_at = datetime.now(timezone.utc)
            session.commit()

            logger.info(f"Drive connected successfully for user: {current_user.email}")

            # Initialize folder structure in Google Drive
            try:
                folder_map = drive_service.initialize_folder_structure(
                    refresh_token_encrypted=encrypted_token,
                    session=session
                )
                logger.info(f"Initialized {len(folder_map)} folders in Drive for user: {current_user.email}")
            except Exception as folder_error:
                logger.error(f"Failed to initialize Drive folders: {folder_error}")
                # Don't fail the connection if folder creation fails
                # User can manually create folders or we can retry later

            return {
                "success": True,
                "message": "Google Drive connected successfully",
                "connected_at": user.drive_permissions_granted_at.isoformat()
            }
        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Drive OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect Google Drive"
        )


@router.post(
    "/drive/disconnect",
    responses={
        200: {"description": "Drive disconnected successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def disconnect_google_drive(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Disconnect Google Drive and revoke access

    Clears stored refresh token and disables Drive integration
    """
    try:
        from app.database.connection import db_manager
        session = db_manager.session_local()
        try:
            user = session.query(User).filter(User.id == current_user.id).first()
            user.drive_refresh_token_encrypted = None
            user.drive_token_expires_at = None
            user.google_drive_enabled = False
            user.drive_permissions_granted_at = None
            session.commit()

            logger.info(f"Drive disconnected for user: {current_user.email}")

            return {
                "success": True,
                "message": "Google Drive disconnected successfully"
            }
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Drive disconnect error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect Google Drive"
        )


@router.get(
    "/export",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def export_user_data(
    current_user: User = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Export user data for GDPR compliance
    
    Returns complete user data export
    """
    try:
        dashboard = await user_service.get_user_dashboard(str(current_user.id))
        
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User data not found for export"
            )
        
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "user_profile": dashboard.profile.dict(),
            "user_statistics": dashboard.statistics.dict(),
            "user_preferences": dashboard.preferences.dict(),
            "recent_activity": dashboard.recent_activity
        }
        
        logger.info(f"Data exported for user: {current_user.email}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename=user_data_export_{current_user.id}.json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export user data error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to export user data"
        )