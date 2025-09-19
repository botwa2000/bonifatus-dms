# backend/src/auth/dependencies.py
"""
Bonifatus DMS - Authentication Dependencies
FastAPI dependencies for authentication and authorization
JWT token validation and user tier checking
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging

from src.database import get_db, User, UserTier
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token
    CHANGED: Made synchronous - AuthService.get_current_user() is not async
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Require admin user privileges
    CHANGED: Made synchronous
    """
    if current_user.tier != UserTier.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    return current_user


def require_tier(required_tier: UserTier):
    """
    Dependency factory to require specific user tier or higher
    """

    def tier_dependency(current_user: User = Depends(get_current_user)) -> User:
        """CHANGED: Made synchronous"""
        # Define tier hierarchy
        tier_hierarchy = {
            UserTier.FREE: 0,
            UserTier.PREMIUM_TRIAL: 1,
            UserTier.PREMIUM: 2,
            UserTier.ADMIN: 3,
        }

        user_level = tier_hierarchy.get(current_user.tier, 0)
        required_level = tier_hierarchy.get(required_tier, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_tier.value} tier or higher",
            )

        return current_user

    return tier_dependency


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, None if not
    CHANGED: Made synchronous
    """
    if not credentials:
        return None

    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        return user if user and user.is_active else None
    except Exception:
        return None


def require_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Require verified user account
    CHANGED: Made synchronous
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account verification required",
        )

    return current_user


def require_google_drive_connected(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require Google Drive connection
    CHANGED: Made synchronous
    """
    if not current_user.google_drive_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Drive connection required",
        )

    return current_user
