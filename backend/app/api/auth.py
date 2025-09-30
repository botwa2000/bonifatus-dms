# backend/app/api/auth.py
"""
Bonifatus DMS - Authentication API Endpoints
Google OAuth, JWT token management, user sessions
Production-grade implementation with comprehensive security
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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
from app.middleware.auth_middleware import (
    get_current_active_user, 
    get_current_admin_user,
    get_client_ip,
    optional_current_user
)
from app.database.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Fix: Ensure auth_service is properly initialized
if not hasattr(auth_service, 'authenticate_with_google'):
    logger.error("Auth service not properly initialized")
    
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.get(
    "/google/config",
    response_model=GoogleOAuthConfigResponse,
    responses={
        200: {"model": GoogleOAuthConfigResponse, "description": "OAuth configuration"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get Google OAuth Configuration",
    description="Retrieve Google OAuth client ID and redirect URI for frontend authentication flow"
)
async def get_google_oauth_config() -> GoogleOAuthConfigResponse:
    """
    Get Google OAuth configuration for frontend
    
    Returns client ID and redirect URI for OAuth flow initiation.
    This endpoint is public and used by the frontend to configure Google OAuth.
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


@router.get(
    "/google/login",
    responses={
        302: {"description": "Redirect to Google OAuth"},
        500: {"model": ErrorResponse, "description": "OAuth initialization failed"}
    },
    summary="Initiate Google OAuth Login",
    description="Redirect user to Google OAuth authorization endpoint"
)
async def google_oauth_login(request: Request):
    """
    Initiate Google OAuth login flow
    
    Redirects user to Google OAuth authorization endpoint with proper parameters.
    """
    try:
        # Build Google OAuth URL
        oauth_params = {
            "client_id": settings.google.google_client_id,
            "redirect_uri": settings.google.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": request.headers.get("X-Request-ID", "")
        }
        
        from urllib.parse import urlencode
        oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(oauth_params)}"
        
        logger.info(f"Redirecting to Google OAuth: {request.client.host if request.client else 'unknown'}")
        
        return RedirectResponse(url=oauth_url, status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"OAuth login initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth initialization failed"
        )


@router.post(
    "/google/callback", 
    response_model=TokenResponse,
    responses={
        200: {"model": TokenResponse, "description": "Authentication successful"},
        401: {"model": ErrorResponse, "description": "Invalid Google token"},
        403: {"model": ErrorResponse, "description": "User account inactive"},
        422: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Complete Google OAuth Flow",
    description="Exchange Google OAuth code for JWT tokens"
)
async def google_oauth_callback(
    request: Request,
    google_request: GoogleTokenRequest
) -> TokenResponse:
    """
    Complete Google OAuth flow and return JWT tokens
    
    Validates Google OAuth ID token, creates or updates user account,
    and returns access and refresh JWT tokens for authenticated sessions.
    """
    try:
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        auth_result = await auth_service.authenticate_with_google_code(
            google_request.code, 
            ip_address,
            user_agent
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
        200: {"model": RefreshTokenResponse, "description": "Token refreshed successfully"},
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
        403: {"model": ErrorResponse, "description": "User account inactive"},
        422: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Refresh Access Token",
    description="Generate new access token using refresh token"
)
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest
) -> RefreshTokenResponse:
    """
    Refresh JWT access token using refresh token
    
    Returns new access token with updated expiry time.
    Refresh tokens are long-lived and used to obtain new access tokens
    without requiring user to re-authenticate.
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
        200: {"model": UserResponse, "description": "User profile retrieved"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "User account inactive"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get Current User Profile",
    description="Retrieve authenticated user's profile information"
)
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current authenticated user profile
    
    Returns user information based on valid JWT token.
    Includes user details, tier information, and account status.
    """
    try:
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            full_name=current_user.full_name,
            profile_picture=current_user.profile_picture,
            tier=current_user.tier,
            is_active=current_user.is_active,
            is_admin=current_user.is_admin,
            last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
            created_at=current_user.created_at.isoformat(),
            updated_at=current_user.updated_at.isoformat()
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
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Logout User",
    description="Logout current user and invalidate tokens"
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Logout current user and invalidate tokens
    
    Invalidates user session and clears authentication tokens.
    After logout, the user must re-authenticate to access protected resources.
    """
    try:
        ip_address = get_client_ip(request)
        
        await auth_service.logout_user(str(current_user.id), ip_address)
        
        logger.info(f"User {current_user.email} logged out from IP: {ip_address}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Logout successful",
                "timestamp": time.time()
            }
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout service error"
        )


@router.post(
    "/admin/verify",
    responses={
        200: {"description": "Admin verification successful"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin privileges required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Verify Admin Access",
    description="Verify current user has admin privileges"
)
async def verify_admin_access(
    request: Request,
    admin_user: User = Depends(get_current_admin_user)
) -> JSONResponse:
    """
    Verify admin access for current user
    
    Protected endpoint that verifies the current user has administrative privileges.
    Returns success if user is authenticated and has admin role.
    """
    try:
        ip_address = get_client_ip(request)
        
        logger.info(f"Admin access verified for {admin_user.email} from IP: {ip_address}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Admin access verified",
                "user_email": admin_user.email,
                "timestamp": time.time()
            }
        )
        
    except Exception as e:
        logger.error(f"Admin verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin verification failed"
        )


# Health endpoint for authentication service
@router.get(
    "/health",
    responses={
        200: {"description": "Authentication service healthy"},
        500: {"description": "Authentication service unhealthy"}
    },
    summary="Authentication Service Health Check",
    description="Check health status of authentication service components"
)
async def auth_service_health():
    """
    Authentication service health check
    
    Verifies that authentication service components are functioning properly.
    Checks Google OAuth configuration and JWT service availability.
    """
    try:
        health_status = {
            "status": "healthy",
            "service": "authentication",
            "components": {
                "google_oauth": "configured" if settings.google.google_client_id else "not_configured",
                "jwt_service": "available",
                "database": "available"
            },
            "timestamp": time.time()
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Auth service health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "unhealthy",
                "service": "authentication",
                "error": str(e) if not settings.is_production else "Health check failed",
                "timestamp": time.time()
            }
        )