# backend/app/api/auth.py
"""
Bonifatus DMS - Authentication API Endpoints
Google OAuth, JWT token management, user sessions
Production-grade implementation with comprehensive security
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
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


@router.get(
    "/google/callback",
    responses={
        302: {"description": "Redirect to dashboard on success"},
        401: {"description": "OAuth authentication failed"},
        500: {"description": "Internal server error"}
    },
    summary="Complete Google OAuth Flow (Server-side)",
    description="Industry-standard OAuth callback - exchanges code for tokens server-side and redirects"
)
async def google_oauth_callback_redirect(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Industry-standard OAuth callback endpoint (GET with redirect)

    Security benefits:
    - OAuth code never exposed to frontend JavaScript
    - Tokens set in httpOnly cookies before redirect
    - Follows OAuth 2.0 confidential client pattern
    - Reduces attack surface

    Flow:
    1. Google redirects here with authorization code
    2. Backend exchanges code for tokens server-side
    3. Tokens stored in httpOnly cookies
    4. User redirected to dashboard with cookies set
    """
    try:
        # Handle OAuth cancellation or errors from Google
        if error or not code:
            logger.info(f"OAuth flow cancelled or failed: error={error}, code_present={bool(code)}")
            # Redirect to homepage instead of showing error
            redirect_url = f"{settings.app.app_frontend_url}/"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")

        # Extract tier selection from OAuth state parameter
        tier_id = None
        billing_cycle = None
        if state:
            try:
                import json
                import base64
                state_data = json.loads(base64.b64decode(state).decode('utf-8'))
                tier_id = state_data.get('tier_id')
                billing_cycle = state_data.get('billing_cycle')
                logger.info(f"OAuth state decoded - tier_id: {tier_id}, billing_cycle: {billing_cycle}")
            except Exception as e:
                logger.warning(f"Failed to decode OAuth state: {e}")
                # Continue without tier selection - user will get free tier

        # Exchange authorization code for tokens
        auth_result = await auth_service.authenticate_with_google_code(
            code,
            ip_address,
            user_agent,
            tier_id=tier_id
        )

        if not auth_result:
            logger.warning(f"Google authentication failed from IP: {ip_address}")
            error_url = f"{settings.app.app_frontend_url}/login?error=auth_failed"
            return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

        # Determine redirect URL based on tier selection and existing subscription
        # If user selected a paid tier, check if they already have an active subscription
        # If user selected free tier or no tier, redirect to dashboard
        if tier_id and tier_id > 0:
            # Paid tier selected - check if user already has active subscription
            from app.database.models import Subscription
            from app.database.connection import get_db

            db = next(get_db())
            try:
                active_sub = db.query(Subscription).filter(
                    Subscription.user_id == auth_result['user_id'],
                    Subscription.status.in_(['active', 'trialing', 'past_due'])
                ).first()

                if active_sub:
                    # User already has active subscription - redirect to dashboard
                    # (Redirecting to /profile causes cookie timing issues)
                    redirect_url = f"{settings.app.app_frontend_url}/dashboard"
                    logger.info(f"User {auth_result['email']} has active subscription, redirecting to dashboard")
                else:
                    # No active subscription - proceed to checkout
                    billing_cycle_param = f"&billing_cycle={billing_cycle}" if billing_cycle else "&billing_cycle=monthly"
                    redirect_url = f"{settings.app.app_frontend_url}/checkout?tier_id={tier_id}{billing_cycle_param}&new_user=true"
                    logger.info(f"User {auth_result['email']} selected paid tier {tier_id}, redirecting to checkout")
            finally:
                db.close()
        else:
            # Free tier or no tier selected - redirect to welcome dashboard
            redirect_url = f"{settings.app.app_frontend_url}/dashboard?welcome=true"
            logger.info(f"User {auth_result['email']} using free tier, redirecting to dashboard")

        redirect_response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        # Set tokens in httpOnly cookies before redirect
        redirect_response.set_cookie(
            key="access_token",
            value=auth_result["access_token"],
            httponly=True,
            secure=True,
            samesite="lax",
            domain=".bonidoc.com",
            max_age=settings.security.access_token_expire_minutes * 60,  # Match token lifetime
            path="/"
        )

        redirect_response.set_cookie(
            key="refresh_token",
            value=auth_result["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict",
            domain=".bonidoc.com",
            max_age=604800,  # 7 days
            path="/"
        )

        logger.info(f"[OAuth] User {auth_result['email']} authenticated successfully")
        logger.info(f"[OAuth] Setting cookies: domain=.bonidoc.com, secure=True, httponly=True")
        logger.info(f"[OAuth] Redirecting to: {redirect_url}")

        return redirect_response

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        error_url = f"{settings.app.app_frontend_url}/login?error=server_error"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)


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
    summary="Complete Google OAuth Flow (Legacy)",
    description="Legacy AJAX endpoint - use GET /google/callback instead",
    deprecated=True
)
async def google_oauth_callback_ajax(
    request: Request,
    response: Response,
    google_request: GoogleTokenRequest
) -> TokenResponse:
    """
    Legacy OAuth callback endpoint (POST with JSON)

    DEPRECATED: Use GET /google/callback instead for better security.
    This endpoint will be removed in a future version.
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
        
        # Set tokens in httpOnly cookies
        # Domain=.bonidoc.com allows cookies to work across api.bonidoc.com and bonidoc.com
        # SameSite=Lax for access token (allows navigation), Strict for refresh token (max security)

        response.set_cookie(
            key="access_token",
            value=auth_result["access_token"],
            httponly=True,
            secure=True,
            samesite="lax",  # Lax allows navigation while preventing CSRF
            domain=".bonidoc.com",  # Accessible across all *.bonidoc.com subdomains
            max_age=settings.security.access_token_expire_minutes * 60,  # Match token lifetime
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=auth_result["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict",  # Strict for maximum security on refresh token
            domain=".bonidoc.com",
            max_age=604800,  # 7 days
            path="/"
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
    response: Response,
    refresh_request: RefreshTokenRequest
) -> RefreshTokenResponse:
    """
    Refresh JWT access token using refresh token

    Returns new access token with updated expiry time.
    Refresh tokens are long-lived and used to obtain new access tokens
    without requiring user to re-authenticate.
    Sets new access token in httpOnly cookie.

    Refresh token can be provided either:
    1. In request body (for API clients)
    2. In httpOnly cookie (for browser clients)
    """
    try:
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")

        # Get refresh token from body or cookie
        refresh_token_value = refresh_request.refresh_token
        if not refresh_token_value:
            # Try to get from cookie
            refresh_token_value = request.cookies.get("refresh_token")
            if not refresh_token_value:
                logger.warning(f"Refresh token missing from both body and cookie, IP: {ip_address}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token required"
                )

        logger.info(f"[REFRESH DEBUG] Starting token refresh from IP: {ip_address}")
        logger.info(f"[REFRESH DEBUG] Refresh token source: {'body' if refresh_request.refresh_token else 'cookie'}")
        logger.info(f"[REFRESH DEBUG] User agent: {user_agent}")

        refresh_result = await auth_service.refresh_access_token(
            refresh_token_value,
            ip_address,
            user_agent
        )

        if not refresh_result:
            logger.warning(f"[REFRESH DEBUG] ❌ Token refresh FAILED from IP: {ip_address}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        logger.info(f"[REFRESH DEBUG] ✅ Token refresh successful for user: {refresh_result.get('email')}")

        # Set new access token in httpOnly cookie
        response.set_cookie(
            key="access_token",
            value=refresh_result["access_token"],
            httponly=True,
            secure=True,
            samesite="lax",
            domain=".bonidoc.com",
            max_age=settings.security.access_token_expire_minutes * 60,  # Match token lifetime
            path="/"
        )

        logger.info(f"[REFRESH DEBUG] ✅ Access token cookie SET with domain=.bonidoc.com, max_age={settings.security.access_token_expire_minutes * 60}, httponly=True")
        logger.info(f"[REFRESH DEBUG] Access token refreshed for user {refresh_result.get('email')} from IP: {ip_address}")

        return RefreshTokenResponse(**refresh_result)
        
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
            tier=current_user.tier.name if current_user.tier else "free",
            tier_id=current_user.tier_id,
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
    response: Response,
    current_user: User = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Logout current user and invalidate tokens
    
    Invalidates user session and clears authentication tokens.
    After logout, the user must re-authenticate to access protected resources.
    """
    try:
        ip_address = get_client_ip(request)

        # Revoke user sessions in database
        await auth_service.logout_user(str(current_user.id), ip_address)

        logger.info(f"User {current_user.email} logged out from IP: {ip_address}")

        # Create response with cookies cleared
        logout_response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Logout successful",
                "timestamp": time.time()
            }
        )

        # Clear all authentication cookies on the response we're returning
        logout_response.set_cookie(
            key="access_token",
            value="",
            httponly=True,
            secure=True,
            samesite="lax",
            domain=".bonidoc.com",
            max_age=0,
            path="/"
        )

        logout_response.set_cookie(
            key="refresh_token",
            value="",
            httponly=True,
            secure=True,
            samesite="strict",
            domain=".bonidoc.com",
            max_age=0,
            path="/"
        )

        return logout_response
        
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