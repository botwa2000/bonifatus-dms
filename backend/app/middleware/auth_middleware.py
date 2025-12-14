# backend/app/middleware/auth_middleware.py
"""
Bonifatus DMS - Authentication Middleware
JWT token validation from httpOnly cookies (Phase 1 security implementation)
Activity tracking for inactivity timeout (30 minutes)
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.database.models import User
from app.database.connection import get_db
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Get current authenticated user from JWT token in httpOnly cookie or Authorization header

    Implements inactivity timeout:
    - Checks if user has been inactive for > 30 minutes
    - Updates last_activity_at on every API call (activity tracking)
    """

    # Priority 1: Check httpOnly cookie (Phase 1 security implementation)
    token = request.cookies.get("access_token")

    # Priority 2: Fallback to Authorization header for backwards compatibility
    if not token and credentials:
        token = credentials.credentials

    if not token:
        # Don't log for /auth/me endpoint - too noisy for public page checks
        if request.url.path != "/api/v1/auth/me":
            logger.warning(f"No authentication token found for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_current_user(token)

    if not user:
        logger.warning(f"Invalid token for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update activity timestamp and check inactivity
    from sqlalchemy.orm import Session
    db: Session = next(get_db())
    current_time = datetime.now(timezone.utc)

    try:
        db_user = db.query(User).filter(User.id == user.id).first()
        if db_user:
            # Store the old activity timestamp for checking
            last_activity = db_user.last_activity_at

            # Update activity timestamp IMMEDIATELY to mark this request as activity
            db_user.last_activity_at = current_time
            db.commit()

            # NOW check if user WAS inactive (before this request)
            # This prevents race condition where page refresh triggers logout
            if last_activity:
                inactive_seconds = (current_time - last_activity).total_seconds()
                inactive_minutes = inactive_seconds / 60

                # Only enforce inactivity if it's been longer than the timeout
                # Add 1 minute grace period to handle network delays and page loads
                if inactive_minutes > (settings.security.inactivity_timeout_minutes + 1):
                    db.close()
                    logger.warning(f"User {user.email} was inactive for {inactive_minutes:.1f} minutes - forcing logout")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Session expired due to inactivity ({settings.security.inactivity_timeout_minutes} minutes)",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
    except HTTPException:
        # Re-raise HTTP exceptions (like inactivity timeout)
        raise
    except Exception as e:
        logger.error(f"Failed to update last_activity_at for user {user.email}: {e}")
        db.rollback()
    finally:
        db.close()

    logger.info(f"Authenticated user {user.email} for {request.url.path}")
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (additional check for user status)"""
    
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return current_user


async def require_premium_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require user to have premium tier access"""

    # tier_id: 0=Free, 1=Starter, 2=Pro, 100=Admin
    if current_user.tier_id not in [2, 100]:  # Pro or Admin
        tier_name = current_user.tier.name if current_user.tier else "unknown"
        logger.warning(f"User {current_user.email} attempted premium access with tier: {tier_name}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for this feature"
        )

    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require user to have admin privileges"""

    # Check is_admin flag from database (preferred method after migration 006)
    if not current_user.is_admin:
        logger.warning(f"User {current_user.email} attempted admin access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )

    logger.info(f"Admin user {current_user.email} (role: {current_user.admin_role or 'none'}) authenticated")
    return current_user


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    
    # Check for forwarded headers first (when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


async def optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current user if token is provided, but don't require authentication"""
    
    # Check httpOnly cookie first
    token = request.cookies.get("access_token")
    
    # Fallback to Authorization header
    if not token and credentials:
        token = credentials.credentials
    
    if not token:
        return None

    try:
        user = await auth_service.get_current_user(token)
        
        if user and user.is_active:
            logger.info(f"Optional auth: User {user.email} authenticated for {request.url.path}")
            return user
            
    except Exception as e:
        logger.warning(f"Optional auth failed for {request.url.path}: {e}")
    
    return None