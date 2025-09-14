# backend/src/api/auth.py
"""
Bonifatus DMS - Authentication API
Google OAuth 2.0 authentication and JWT token management
Secure session handling with refresh tokens
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import httpx
import logging
from datetime import datetime, timedelta

from src.database import get_db, User, UserSettings
from src.core.config import get_settings
from src.services.auth_service import AuthService
from src.services.google_oauth_service import GoogleOAuthService
from src.integrations.google_drive import GoogleDriveClient

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()

router = APIRouter()


@router.post("/google/login")
async def google_login_initiate():
    """
    Initiate Google OAuth 2.0 login flow
    Returns authorization URL for frontend redirect
    """
    try:
        oauth_service = GoogleOAuthService()
        auth_url, state = oauth_service.get_authorization_url()
        
        return {
            "auth_url": auth_url,
            "state": state,
            "success": True
        }
    except Exception as e:
        logger.error(f"Failed to initiate Google login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google authentication"
        )


@router.post("/google/callback")
async def google_login_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth 2.0 callback
    Exchange authorization code for tokens and create/update user
    """
    try:
        oauth_service = GoogleOAuthService()
        auth_service = AuthService(db)
        
        # Verify state parameter for security
        if not oauth_service.verify_state(state):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state parameter"
            )
        
        # Exchange code for tokens
        token_response = await oauth_service.exchange_code_for_tokens(code)
        if not token_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )
        
        # Get user info from Google
        user_info = await oauth_service.get_user_info(token_response["access_token"])
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information"
            )
        
        # Create or update user in database
        user = await auth_service.create_or_update_user_from_google(
            google_id=user_info["id"],
            email=user_info["email"],
            full_name=user_info.get("name", ""),
            avatar_url=user_info.get("picture"),
            google_tokens=token_response
        )
        
        # Initialize Google Drive connection
        try:
            drive_client = GoogleDriveClient(user.id, db)
            folder_created = await drive_client.initialize_user_folder()
            if folder_created:
                user.google_drive_connected = True
                user.last_sync_at = datetime.utcnow()
                db.commit()
        except Exception as drive_error:
            logger.warning(f"Failed to initialize Google Drive for user {user.id}: {drive_error}")
            # Don't fail login if Drive setup fails
        
        # Generate JWT tokens
        access_token, refresh_token = auth_service.create_user_tokens(user)
        
        # Log successful login
        await auth_service.log_user_activity(
            user_id=user.id,
            action="google_login_success",
            details={"method": "google_oauth"}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.security.access_token_expire_minutes * 60,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "tier": user.tier.value,
                "avatar_url": user.avatar_url,
                "google_drive_connected": user.google_drive_connected
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google login callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/refresh")
async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        auth_service = AuthService(db)
        tokens = auth_service.refresh_user_tokens(refresh_token)
        
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer", 
            "expires_in": settings.security.access_token_expire_minutes * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout user and revoke tokens
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        
        if user:
            # Revoke refresh token
            await auth_service.revoke_user_tokens(user.id)
            
            # Log logout
            await auth_service.log_user_activity(
                user_id=user.id,
                action="logout",
                details={"method": "api"}
            )
        
        return {"message": "Successfully logged out", "success": True}
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me")
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Get user statistics
        stats = await auth_service.get_user_statistics(user.id)
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "tier": user.tier.value,
            "preferred_language": user.preferred_language,
            "timezone": user.timezone,
            "theme": user.theme,
            "google_drive_connected": user.google_drive_connected,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


@router.get("/google-drive/status")
async def get_google_drive_status(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Check Google Drive connection status
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        drive_client = GoogleDriveClient(user.id, db)
        connection_status = await drive_client.check_connection()
        
        return {
            "connected": connection_status["connected"],
            "folder_id": user.google_drive_folder_id,
            "last_sync": user.last_sync_at.isoformat() if user.last_sync_at else None,
            "storage_used": user.storage_used_bytes,
            "details": connection_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Drive status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check Google Drive status"
        )


@router.post("/google-drive/reconnect")
async def reconnect_google_drive(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Reconnect Google Drive if connection is lost
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Get new authorization URL for Drive reconnection
        oauth_service = GoogleOAuthService()
        auth_url, state = oauth_service.get_authorization_url(force_consent=True)
        
        return {
            "auth_url": auth_url,
            "state": state,
            "message": "Please re-authorize Google Drive access"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Drive reconnect failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Drive reconnection"
        )