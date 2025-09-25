# backend/app/api/auth.py
"""
Bonifatus DMS - Authentication API Endpoints
Google OAuth, JWT token management, user sessions
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse

from app.schemas.auth_schemas import (
    GoogleTokenRequest, 
    TokenResponse, 
    RefreshTokenRequest, 
    RefreshTokenResponse,
    UserResponse,
    ErrorResponse,
    GoogleOAuthConfigResponse
)
from app.services.auth_service import auth_service
from app.middleware.auth_middleware import get_current_active_user, get_client_ip
from app.database.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.get(
    "/google/config",
    response_model=GoogleOAuthConfigResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_google_oauth_config() -> GoogleOAuthConfigResponse:
    """
    Get Google OAuth configuration for frontend
    
    Returns client ID and redirect URI for OAuth flow initiation
    """
    try:
        return GoogleOAuthConfigResponse(
            google_client_id=settings.google.google_client_id,
            redirect_uri=settings.google.google_redirect_uri
        )
        
    except Exception as e:
        logger.error(f"Failed to get OAuth config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth configuration unavailable"
        )


@router.post(
    "/google/callback", 
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid Google token"},
        403: {"model": ErrorResponse, "description": "User account inactive"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def google_oauth_callback(
    request: Request,
    google_request: GoogleTokenRequest
) -> TokenResponse:
    """
    Complete Google OAuth flow and return JWT tokens
    
    Validates Google OAuth ID token and returns access/refresh tokens
    """
    try:
        ip_address = get_client_ip(request)
        
        auth_result = await auth_service.authenticate_with_google(
            google_request.google_token, 
            ip_address
        )
        
        if not auth_result:
            logger.warning(f"Google authentication failed from IP: {ip_address}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google authentication failed"
            )
        
        logger.info(f"User {auth_result['email']} authenticated successfully from IP: {ip_address}")
        
        return TokenResponse(**auth_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest
) -> RefreshTokenResponse:
    """
    Refresh JWT access token using refresh token
    
    Returns new access token with updated expiry
    """
    try:
        ip_address = get_client_ip(request)
        
        auth_result = await auth_service.refresh_access_token(
            refresh_request.refresh_token,
            ip_address
        )
        
        if not auth_result:
            logger.warning(f"Token refresh failed from IP: {ip_address}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        logger.info(f"Token refreshed for user {auth_result['email']} from IP: {ip_address}")
        
        return RefreshTokenResponse(**auth_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service error"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current authenticated user profile
    
    Returns user information based on valid JWT token
    """
    try:
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            tier=current_user.tier,
            is_active=current_user.is_active,
            is_admin=current_user.is_admin,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )
        
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve user profile"
        )


@router.delete(
    "/logout",
    responses={
        200: {"description": "Logout successful"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Logout current user and invalidate tokens
    
    Invalidates user session and clears authentication tokens
    """
    try:
        ip_address = get_client_ip(request)
        
        await auth_service.logout_user(current_user.id, ip_address)
        
        logger.info(f"User {current_user.email} logged out from IP: {ip_address}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Logout successful"}
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout service error"
        )