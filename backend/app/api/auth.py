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
    ErrorResponse
)
from app.services.auth_service import auth_service
from app.middleware.auth_middleware import get_current_active_user, get_client_ip
from app.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


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
        403: {"model": ErrorResponse, "description": "User account inactive"}
    }
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current authenticated user information
    
    Returns user profile data for authenticated user
    """
    try:
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            full_name=current_user.full_name,
            profile_picture=current_user.profile_picture,
            tier=current_user.tier,
            is_active=current_user.is_active,
            last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
            created_at=current_user.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve user information"
        )


@router.post(
    "/logout",
    responses={
        200: {"description": "Successfully logged out"},
        401: {"model": ErrorResponse, "description": "Authentication required"}
    }
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Logout current user
    
    Invalidates current session (client should discard tokens)
    """
    try:
        ip_address = get_client_ip(request)
        
        # Log logout event for audit trail
        from app.database.connection import db_manager
        from app.database.models import AuditLog
        
        session = db_manager.session_local()
        try:
            audit_log = AuditLog(
                user_id=str(current_user.id),
                action="logout",
                resource_type="authentication",
                resource_id=str(current_user.id),
                ip_address=ip_address,
                status="success",
                endpoint="/api/v1/auth/logout"
            )
            session.add(audit_log)
            session.commit()
        finally:
            session.close()
        
        logger.info(f"User {current_user.email} logged out from IP: {ip_address}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Successfully logged out"}
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout service error"
        )


@router.get(
    "/verify",
    responses={
        200: {"description": "Token is valid"},
        401: {"model": ErrorResponse, "description": "Invalid token"}
    }
)
async def verify_token(
    current_user: User = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Verify JWT token validity
    
    Returns success if token is valid and user is active
    """
    try:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "valid": True,
                "user_id": str(current_user.id),
                "email": current_user.email,
                "tier": current_user.tier
            }
        )
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification service error"
        )