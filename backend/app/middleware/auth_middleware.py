# backend/src/middleware/auth_middleware.py
"""
Bonifatus DMS - Authentication Middleware
JWT token validation for protected routes
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.config import settings
from src.database.models import User
from src.services.auth_service import auth_service

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Get current authenticated user from JWT token"""
    
    if not credentials:
        logger.warning(f"Missing authorization header for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user = await auth_service.get_current_user(token)
    
    if not user:
        logger.warning(f"Invalid token for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
    
    if current_user.tier not in ["premium", "trial"]:
        logger.warning(f"User {current_user.email} attempted premium access with tier: {current_user.tier}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for this feature"
        )
    
    return current_user


async def require_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require user to have admin privileges"""
    
    admin_emails = settings.admin_email_list
    
    if current_user.email not in admin_emails:
        logger.warning(f"User {current_user.email} attempted admin access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
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
    
    if not credentials:
        return None

    try:
        token = credentials.credentials
        user = await auth_service.get_current_user(token)
        
        if user and user.is_active:
            logger.info(f"Optional auth: User {user.email} authenticated for {request.url.path}")
            return user
            
    except Exception as e:
        logger.warning(f"Optional auth failed for {request.url.path}: {e}")
    
    return None