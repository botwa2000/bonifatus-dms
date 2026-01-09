# backend/app/api/auth.py
"""
Bonifatus DMS - Authentication API Endpoints
Google OAuth, JWT token management, user sessions
Production-grade implementation with comprehensive security
"""

import logging
import time
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
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
from app.services.email_auth_service import EmailAuthService
from app.services.email_service import email_service
from app.middleware.auth_middleware import (
    get_current_active_user,
    get_current_admin_user,
    get_client_ip,
    optional_current_user
)
from app.database.models import User
from app.database.connection import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()
email_auth_service = EmailAuthService()

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
    import time
    callback_start = time.time()
    logger.info(f"[OAUTH CALLBACK DEBUG] 1. Received OAuth callback request, has_code: {code is not None}, has_state: {state is not None}, has_error: {error is not None}")

    try:
        # Handle OAuth cancellation or errors from Google
        if error or not code:
            logger.info(f"[OAUTH CALLBACK DEBUG] 2. OAuth cancelled/failed: error={error}, code_present={bool(code)}")
            logger.info(f"OAuth flow cancelled or failed: error={error}, code_present={bool(code)}")
            # Redirect to homepage instead of showing error
            redirect_url = f"{settings.app.app_frontend_url}/"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        logger.info(f"[OAUTH CALLBACK DEBUG] 2. OAuth code received, length: {len(code) if code else 0}")
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        logger.info(f"[OAUTH CALLBACK DEBUG] 3. Client info - IP: {ip_address}, UA: {user_agent[:50] if user_agent else 'unknown'}")

        # Extract tier selection from OAuth state parameter
        tier_id = None
        billing_cycle = None
        if state:
            try:
                logger.info(f"[OAUTH CALLBACK DEBUG] 4. Decoding OAuth state parameter ({time.time() - callback_start:.2f}s)")
                import json
                import base64
                state_data = json.loads(base64.b64decode(state).decode('utf-8'))
                tier_id = state_data.get('tier_id')
                billing_cycle = state_data.get('billing_cycle')
                logger.info(f"[OAUTH CALLBACK DEBUG] 5. State decoded - tier_id: {tier_id}, billing_cycle: {billing_cycle} ({time.time() - callback_start:.2f}s)")
                logger.info(f"OAuth state decoded - tier_id: {tier_id}, billing_cycle: {billing_cycle}")
            except Exception as e:
                logger.warning(f"[OAUTH CALLBACK DEBUG] 5. Failed to decode state: {e} ({time.time() - callback_start:.2f}s)")
                logger.warning(f"Failed to decode OAuth state: {e}")
                # Continue without tier selection - user will get free tier

        # Exchange authorization code for tokens
        logger.info(f"[OAUTH CALLBACK DEBUG] 6. Calling auth_service.authenticate_with_google_code ({time.time() - callback_start:.2f}s)")
        auth_result = await auth_service.authenticate_with_google_code(
            code,
            ip_address,
            user_agent,
            tier_id=tier_id
        )
        logger.info(f"[OAUTH CALLBACK DEBUG] 7. Auth service returned, success: {auth_result is not None} ({time.time() - callback_start:.2f}s)")

        if not auth_result:
            logger.warning(f"[OAUTH CALLBACK DEBUG] 8. Authentication failed, redirecting to login ({time.time() - callback_start:.2f}s)")
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

        logger.info(f"[OAUTH CALLBACK DEBUG] 9. Creating redirect response to: {redirect_url} ({time.time() - callback_start:.2f}s)")
        redirect_response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        # Set tokens in httpOnly cookies before redirect
        logger.info(f"[OAUTH CALLBACK DEBUG] 10. Setting cookies ({time.time() - callback_start:.2f}s)")
        redirect_response.set_cookie(
            key="access_token",
            value=auth_result["access_token"],
            httponly=True,
            secure=settings.security.cookie_secure,
            samesite="lax",
            domain=settings.security.cookie_domain,
            max_age=settings.security.access_token_expire_minutes * 60,  # Match token lifetime
            path="/"
        )

        redirect_response.set_cookie(
            key="refresh_token",
            value=auth_result["refresh_token"],
            httponly=True,
            secure=settings.security.cookie_secure,
            samesite="strict",
            domain=settings.security.cookie_domain,
            max_age=604800,  # 7 days
            path="/"
        )

        logger.info(f"[OAUTH CALLBACK DEBUG] 11. Cookies set, returning redirect response ({time.time() - callback_start:.2f}s)")
        logger.info(f"[OAuth] User {auth_result['email']} authenticated successfully")
        logger.info(f"[OAuth] Setting cookies: domain={settings.security.cookie_domain}, secure={settings.security.cookie_secure}, httponly=True")
        logger.info(f"[OAuth] Redirecting to: {redirect_url}")
        logger.info(f"[OAUTH CALLBACK DEBUG] 12. Total callback time: {time.time() - callback_start:.2f}s")

        return redirect_response

    except Exception as e:
        logger.error(f"[OAUTH CALLBACK DEBUG] EXCEPTION at {time.time() - callback_start:.2f}s: {e}")
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
        # Cookie domain from settings allows cross-subdomain access when configured with leading dot
        # SameSite=Lax for access token (allows navigation), Strict for refresh token (max security)

        response.set_cookie(
            key="access_token",
            value=auth_result["access_token"],
            httponly=True,
            secure=settings.security.cookie_secure,
            samesite="lax",  # Lax allows navigation while preventing CSRF
            domain=settings.security.cookie_domain,  # Accessible across configured domain
            max_age=settings.security.access_token_expire_minutes * 60,  # Match token lifetime
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=auth_result["refresh_token"],
            httponly=True,
            secure=settings.security.cookie_secure,
            samesite="strict",  # Strict for maximum security on refresh token
            domain=settings.security.cookie_domain,
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

        if settings.app.app_debug_logging:
            logger.debug(f"[REFRESH DEBUG] Starting token refresh from IP: {ip_address}")
            logger.debug(f"[REFRESH DEBUG] Refresh token source: {'body' if refresh_request.refresh_token else 'cookie'}")
            logger.debug(f"[REFRESH DEBUG] User agent: {user_agent}")

        refresh_result = await auth_service.refresh_access_token(
            refresh_token_value,
            ip_address,
            user_agent
        )

        if not refresh_result:
            if settings.app.app_debug_logging:
                logger.debug(f"[REFRESH DEBUG] ❌ Token refresh FAILED from IP: {ip_address}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        if settings.app.app_debug_logging:
            logger.debug(f"[REFRESH DEBUG] ✅ Token refresh successful for user: {refresh_result.get('email')}")

        # Set new access token in httpOnly cookie
        response.set_cookie(
            key="access_token",
            value=refresh_result["access_token"],
            httponly=True,
            secure=settings.security.cookie_secure,
            samesite="lax",
            domain=settings.security.cookie_domain,
            max_age=settings.security.access_token_expire_minutes * 60,  # Match token lifetime
            path="/"
        )

        if settings.app.app_debug_logging:
            logger.debug(f"[REFRESH DEBUG] ✅ Access token cookie SET with domain={settings.security.cookie_domain}, max_age={settings.security.access_token_expire_minutes * 60}, httponly=True")
            logger.debug(f"[REFRESH DEBUG] Access token refreshed for user {refresh_result.get('email')} from IP: {ip_address}")

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
            secure=settings.security.cookie_secure,
            samesite="lax",
            domain=settings.security.cookie_domain,
            max_age=0,
            path="/"
        )

        logout_response.set_cookie(
            key="refresh_token",
            value="",
            httponly=True,
            secure=settings.security.cookie_secure,
            samesite="strict",
            domain=settings.security.cookie_domain,
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


# ============================================================================
# EMAIL/PASSWORD AUTHENTICATION ENDPOINTS
# ============================================================================

from pydantic import EmailStr, Field
from app.services.email_auth_service import email_auth_service
from datetime import datetime, timezone

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=12, description="Password (min 12 characters)")
    full_name: str = Field(..., min_length=1, max_length=255)


class RegisterResponse(BaseModel):
    """User registration response"""
    success: bool
    message: str
    user_id: Optional[str] = None
    verification_code_id: Optional[str] = None
    errors: Optional[list] = None


class LoginEmailRequest(BaseModel):
    """Email/password login request"""
    email: EmailStr
    password: str
    remember_me: bool = False


class LoginEmailResponse(BaseModel):
    """Email/password login response"""
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[dict] = None
    requires_verification: Optional[bool] = None
    user_id: Optional[str] = None


class VerifyEmailRequest(BaseModel):
    """Email verification request"""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")


class VerifyEmailResponse(BaseModel):
    """Email verification response"""
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class ResendCodeRequest(BaseModel):
    """Resend verification code request"""
    email: EmailStr
    purpose: str = Field(..., pattern="^(registration|password_reset|email_change)$")


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    token: str = Field(..., min_length=64, max_length=64)
    new_password: str = Field(..., min_length=12)


class PasswordStrengthRequest(BaseModel):
    """Password strength check request"""
    password: str


class PasswordStrengthResponse(BaseModel):
    """Password strength check response"""
    valid: bool
    errors: list[str]


@router.post(
    "/email/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": RegisterResponse, "description": "Registration successful"},
        400: {"model": ErrorResponse, "description": "Invalid input or email already registered"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Register with Email/Password",
    description="Register new user with email and password (min 12 chars, mixed case, numbers, special chars)"
)
async def register_email(request_data: RegisterRequest, db = Depends(get_db)):
    """
    Register new user with email/password

    - **email**: Valid email address
    - **password**: Strong password (min 12 chars, uppercase, lowercase, digit, special char)
    - **full_name**: User's full name
    """
    from app.database.connection import get_db as get_db_func

    result = await email_auth_service.register_user(
        email=request_data.email,
        password=request_data.password,
        full_name=request_data.full_name,
        session=db
    )

    # Handle special cases (existing email)
    if not result['success']:
        # If user-friendly error (already registered), send email if needed
        if result.get('user_friendly'):
            # If unverified account, send verification email
            if result.get('requires_verification'):
                try:
                    from app.database.auth_models import EmailVerificationCode
                    from sqlalchemy import select

                    verification_code_id = result.get('verification_code_id')
                    if verification_code_id:
                        code_record = db.execute(
                            select(EmailVerificationCode).where(
                                EmailVerificationCode.id == verification_code_id
                            )
                        ).scalar_one_or_none()

                        if code_record:
                            await email_service.send_verification_code_email(
                                session=db,
                                to_email=result['email'],
                                user_name=request_data.full_name or result['email'],
                                verification_code=code_record.code
                            )
                            logger.info(f"Verification email sent to existing unverified user: {result['email']}")
                except Exception as e:
                    logger.error(f"Failed to send verification email: {e}")

            # Return user-friendly error with proper message
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    'message': result['message'],
                    'requires_verification': result.get('requires_verification', False),
                    'requires_login': result.get('requires_login', False),
                    'email': result.get('email')
                }
            )

        # Generic error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )

    # Send verification email with code for new registrations
    try:
        from app.database.models import User
        from app.database.auth_models import EmailVerificationCode
        from sqlalchemy import select

        # Get the verification code that was just created
        verification_code_id = result.get('verification_code_id')
        if verification_code_id:
            code_record = db.execute(
                select(EmailVerificationCode).where(
                    EmailVerificationCode.id == verification_code_id
                )
            ).scalar_one_or_none()

            if code_record:
                # Send verification email
                await email_service.send_verification_code_email(
                    session=db,
                    to_email=request_data.email,
                    user_name=request_data.full_name or request_data.email,
                    verification_code=code_record.code
                )
                logger.info(f"Verification email sent to: {request_data.email}")
            else:
                logger.error(f"Verification code not found for: {request_data.email}")
        else:
            logger.error(f"No verification_code_id returned for: {request_data.email}")
    except Exception as e:
        # Log error but don't fail the registration
        logger.error(f"Failed to send verification email to {request_data.email}: {e}")

    logger.info(f"New user registered: {request_data.email}")

    return RegisterResponse(**result)


@router.post(
    "/email/login",
    response_model=LoginEmailResponse,
    responses={
        200: {"model": LoginEmailResponse, "description": "Login successful"},
        401: {"model": ErrorResponse, "description": "Invalid credentials or account locked"},
        422: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Login with Email/Password",
    description="Authenticate user with email and password"
)
async def login_email(
    request_data: LoginEmailRequest,
    http_request: Request,
    response: Response,
    db = Depends(get_db)
):
    """
    Login with email/password

    - **email**: Registered email address
    - **password**: User password
    - **remember_me**: Keep user logged in for 30 days
    """
    # Get client info
    ip_address = get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "unknown")

    result = await email_auth_service.login_user(
        email=request_data.email,
        password=request_data.password,
        ip_address=ip_address,
        user_agent=user_agent,
        session=db
    )

    if not result['success']:
        # Return appropriate response
        if result.get('requires_verification'):
            return LoginEmailResponse(**result)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result
        )

    # Generate JWT tokens
    from app.services.session_service import session_service

    user = result['user']
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id)}
    )

    # Create session with refresh token
    session_result = await session_service.create_session(
        user_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
        session=db
    )

    # Set tokens in httpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.security.cookie_secure,
        samesite="lax",
        domain=settings.security.cookie_domain,
        max_age=settings.security.access_token_expire_minutes * 60,
        path="/"
    )

    response.set_cookie(
        key="refresh_token",
        value=session_result['refresh_token'],
        httponly=True,
        secure=settings.security.cookie_secure,
        samesite="strict",
        domain=settings.security.cookie_domain,
        max_age=604800,  # 7 days
        path="/"
    )

    logger.info(f"User logged in via email: {request_data.email}")

    return LoginEmailResponse(
        success=True,
        message="Login successful",
        access_token=access_token,
        refresh_token=session_result['refresh_token'],
        user={
            'id': str(user.id),
            'email': user.email,
            'full_name': user.full_name,
            'profile_picture': user.profile_picture,
            'tier_id': user.tier_id,
            'is_admin': user.is_admin
        }
    )


@router.post(
    "/email/verify",
    response_model=VerifyEmailResponse,
    responses={
        200: {"model": VerifyEmailResponse, "description": "Email verified"},
        400: {"model": ErrorResponse, "description": "Invalid or expired code"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Verify Email with Code",
    description="Verify email address with 6-digit code sent via email"
)
async def verify_email(
    request_data: VerifyEmailRequest,
    response: Response,
    http_request: Request,
    db = Depends(get_db)
):
    """
    Verify email address with 6-digit code

    - **email**: Email address
    - **code**: 6-digit verification code
    """
    # Get client info
    ip_address = get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "unknown")

    result = await email_auth_service.verify_code(
        email=request_data.email,
        code=request_data.code,
        purpose='registration',
        session=db
    )

    if not result['valid']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'message': result['message']}
        )

    # Mark user as verified
    from app.database.models import User
    from sqlalchemy import select, update
    from uuid import UUID

    user_id = result.get('user_id')
    if user_id:
        db.execute(
            update(User)
            .where(User.id == UUID(user_id))
            .values(
                email_verified=True,
                email_verified_at=datetime.now(timezone.utc)
            )
        )
        db.commit()

        # Get user for token generation
        user = db.execute(
            select(User).where(User.id == UUID(user_id))
        ).scalar_one()

        # Generate tokens
        from app.services.session_service import session_service

        access_token = auth_service.create_access_token(
            data={"sub": str(user.id)}
        )

        session_result = await session_service.create_session(
            user_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
            session=db
        )

        # Set cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.security.cookie_secure,
            samesite="lax",
            domain=settings.security.cookie_domain,
            max_age=settings.security.access_token_expire_minutes * 60,
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=session_result['refresh_token'],
            httponly=True,
            secure=settings.security.cookie_secure,
            samesite="strict",
            domain=settings.security.cookie_domain,
            max_age=604800,
            path="/"
        )

        logger.info(f"Email verified: {request_data.email}")

        # Send welcome email to new user
        try:
            import asyncio
            dashboard_url = f"{settings.app.app_frontend_url}/dashboard"
            asyncio.create_task(
                email_service.send_user_created_notification(
                    session=db,
                    to_email=user.email,
                    user_name=user.full_name or user.email,
                    dashboard_url=dashboard_url,
                    user_can_receive_marketing=user.email_marketing_enabled if hasattr(user, 'email_marketing_enabled') else True
                )
            )
            logger.info(f"Queued welcome email for new user: {user.email}")
        except Exception as e:
            logger.error(f"Failed to queue welcome email for {user.email}: {e}")

        # Send admin notification emails (async, don't block response)
        try:
            from app.database.models import TierPlan
            from sqlalchemy import select as sql_select
            import asyncio

            # Get all admin users
            admin_users = db.execute(
                sql_select(User).where(User.is_admin == True)
            ).scalars().all()

            # Get tier name
            tier = db.execute(
                sql_select(TierPlan).where(TierPlan.id == user.tier_id)
            ).scalar_one_or_none()
            tier_name = tier.display_name if tier else "Free"

            # Send notification to each admin (don't await - run in background)
            registration_date = user.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            for admin in admin_users:
                asyncio.create_task(
                    email_service.send_admin_new_user_notification(
                        session=db,
                        admin_email=admin.email,
                        admin_name=admin.full_name or admin.email,
                        new_user_name=user.full_name or user.email,
                        new_user_id=user.id,
                        new_user_email=user.email,
                        tier_name=tier_name,
                        registration_date=registration_date
                    )
                )
            logger.info(f"Queued admin notifications for new user: {user.email}")
        except Exception as e:
            # Log error but don't fail the verification
            logger.error(f"Failed to send admin notifications for {user.email}: {e}")

        return VerifyEmailResponse(
            success=True,
            message="Email verified successfully",
            access_token=access_token,
            refresh_token=session_result['refresh_token']
        )

    return VerifyEmailResponse(
        success=True,
        message="Email verified successfully"
    )


@router.post(
    "/email/resend-code",
    responses={
        200: {"description": "Verification code sent"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Resend Verification Code",
    description="Resend verification code to email"
)
async def resend_verification_code(request_data: ResendCodeRequest, db = Depends(get_db)):
    """
    Resend verification code to email

    - **email**: Email address
    - **purpose**: Code purpose (registration, password_reset, email_change)
    """
    # Find user
    from app.database.models import User
    from sqlalchemy import select

    user = db.execute(
        select(User).where(User.email == request_data.email.lower())
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'message': 'User not found'}
        )

    # Generate new code
    result = await email_auth_service.generate_verification_code(
        user_id=str(user.id),
        email=request_data.email,
        purpose=request_data.purpose,
        session=db
    )

    # Send verification email with code
    try:
        from app.database.auth_models import EmailVerificationCode
        from sqlalchemy import select

        code_record = db.execute(
            select(EmailVerificationCode).where(
                EmailVerificationCode.id == result['code_id']
            )
        ).scalar_one_or_none()

        if code_record:
            await email_service.send_verification_code_email(
                session=db,
                to_email=request_data.email,
                user_name=user.full_name or user.email,
                verification_code=code_record.code
            )
            logger.info(f"Verification email sent to: {request_data.email}")
        else:
            logger.error(f"Verification code not found for: {request_data.email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {request_data.email}: {e}")

    logger.info(f"Verification code resent to: {request_data.email}")

    return {
        'success': True,
        'message': 'Verification code sent',
        'expires_at': result['expires_at']
    }


@router.post(
    "/email/forgot-password",
    responses={
        200: {"description": "Reset instructions sent"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Request Password Reset",
    description="Request password reset link via email"
)
async def forgot_password(request_data: ForgotPasswordRequest, db = Depends(get_db)):
    """
    Request password reset link

    - **email**: Registered email address
    """
    result = await email_auth_service.generate_password_reset_token(
        email=request_data.email,
        session=db
    )

    # Send password reset email if user exists
    if result:
        try:
            from app.database.models import User
            from sqlalchemy import select

            user = db.execute(
                select(User).where(User.id == result['user_id'])
            ).scalar_one_or_none()

            if user:
                # Build reset URL using configured frontend URL
                reset_url = f"{settings.app.app_frontend_url}/reset-password?token={result['token']}"

                await email_service.send_password_reset_email(
                    session=db,
                    to_email=request_data.email,
                    user_name=user.full_name or user.email,
                    reset_token=result['token'],
                    reset_url=reset_url
                )
                logger.info(f"Password reset email sent to: {request_data.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {request_data.email}: {e}")

    # Always return success (don't reveal if email exists)
    logger.info(f"Password reset requested for: {request_data.email}")

    return {
        'success': True,
        'message': 'If your email is registered, you will receive a password reset link'
    }


@router.post(
    "/email/reset-password",
    responses={
        200: {"description": "Password reset successful"},
        400: {"model": ErrorResponse, "description": "Invalid token or weak password"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Reset Password",
    description="Reset password using token from email"
)
async def reset_password(request_data: ResetPasswordRequest, db = Depends(get_db)):
    """
    Reset password with token

    - **token**: Password reset token from email (64 characters)
    - **new_password**: New strong password (min 12 chars)
    """
    result = await email_auth_service.reset_password(
        token=request_data.token,
        new_password=request_data.new_password,
        session=db
    )

    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result
        )

    logger.info("Password reset successful")

    return result


@router.post(
    "/email/check-password-strength",
    response_model=PasswordStrengthResponse,
    responses={
        200: {"model": PasswordStrengthResponse, "description": "Password strength validated"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Check Password Strength",
    description="Validate password meets security requirements"
)
async def check_password_strength(request_data: PasswordStrengthRequest):
    """
    Check password strength

    - **password**: Password to validate

    Returns validation result with specific error messages if password is weak.
    """
    result = email_auth_service.validate_password_strength(request_data.password)

    return PasswordStrengthResponse(**result)