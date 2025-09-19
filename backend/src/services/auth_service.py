# backend/src/services/auth_service.py
"""
Bonifatus DMS - Authentication Service
JWT token management, user authentication, and Google OAuth integration
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
import secrets
import logging
from datetime import datetime, timedelta
from jose import JWTError, jwt

from src.database.models import User, UserTier
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    """Service for authentication and JWT token management"""

    def __init__(self, db: Session):
        self.db = db

    def create_or_update_user_from_google(
        self, google_id: str, email: str, full_name: str, avatar_url: Optional[str] = None
    ) -> User:
        """
        Create new user or update existing user from Google OAuth data
        THIS IS SYNCHRONOUS - No async needed for database operations
        """
        try:
            # Check if user already exists
            user = self.db.query(User).filter(User.google_id == google_id).first()

            if user:
                # Update existing user
                user.email = email
                user.full_name = full_name
                user.avatar_url = avatar_url
                user.last_login_at = datetime.utcnow()
                
                logger.info(f"Updated existing user: {user.id}")
            else:
                # Create new user
                user = User(
                    google_id=google_id,
                    email=email,
                    full_name=full_name,
                    avatar_url=avatar_url,
                    tier=UserTier.FREE,
                    is_active=True,
                    is_verified=True,
                    google_drive_connected=True,
                    last_login_at=datetime.utcnow(),
                )

                self.db.add(user)
                logger.info(f"Created new user: {email}")

            self.db.commit()
            self.db.refresh(user)
            return user

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create/update user from Google: {e}")
            raise

    def create_user_tokens(self, user: User) -> tuple[str, str]:
        """
        Create JWT access and refresh tokens for user
        THIS IS SYNCHRONOUS
        """
        try:
            # Create access token payload
            access_payload = {
                "sub": str(user.id),
                "email": user.email,
                "type": "access",
                "exp": datetime.utcnow()
                + timedelta(minutes=settings.security.access_token_expire_minutes),
                "iat": datetime.utcnow(),
                "jti": secrets.token_urlsafe(16),  # JWT ID for token tracking
            }

            # Create refresh token payload
            refresh_payload = {
                "sub": str(user.id),
                "type": "refresh",
                "exp": datetime.utcnow()
                + timedelta(days=settings.security.refresh_token_expire_days),
                "iat": datetime.utcnow(),
                "jti": secrets.token_urlsafe(32),
            }

            # Generate tokens
            access_token = jwt.encode(
                access_payload,
                settings.secret_key,
                algorithm=settings.security.algorithm,
            )

            refresh_token = jwt.encode(
                refresh_payload,
                settings.secret_key,
                algorithm=settings.security.algorithm,
            )

            logger.info(f"Generated tokens for user {user.id}")
            return access_token, refresh_token

        except Exception as e:
            logger.error(f"Failed to create tokens for user {user.id}: {e}")
            raise

    def get_current_user(self, token: str) -> Optional[User]:
        """
        Validate JWT token and return current user
        THIS IS SYNCHRONOUS - Remove async
        """
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.security.algorithm],
            )

            # Verify token type
            if payload.get("type") != "access":
                logger.warning("Invalid token type provided")
                return None

            # Get user ID from payload
            user_id = payload.get("sub")
            if not user_id:
                logger.warning("No user ID in token payload")
                return None

            # Get user from database
            user = (
                self.db.query(User)
                .filter(User.id == int(user_id), User.is_active == True)
                .first()
            )

            if not user:
                logger.warning(f"User {user_id} not found or inactive")
                return None

            return user

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

    def validate_refresh_token(self, token: str) -> Optional[User]:
        """
        Validate refresh token and return user
        THIS IS SYNCHRONOUS
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.security.algorithm],
            )

            if payload.get("type") != "refresh":
                logger.warning("Invalid token type for refresh")
                return None

            user_id = payload.get("sub")
            if not user_id:
                return None

            user = (
                self.db.query(User)
                .filter(User.id == int(user_id), User.is_active == True)
                .first()
            )

            return user

        except JWTError as e:
            logger.warning(f"Refresh token validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Refresh token validation error: {e}")
            return None

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get user statistics
        THIS IS SYNCHRONOUS
        """
        try:
            # Get document count
            doc_count = self.db.execute(
                text("SELECT COUNT(*) FROM documents WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).scalar()

            # Get category count
            category_count = self.db.execute(
                text("SELECT COUNT(*) FROM categories WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).scalar()

            return {
                "documents": {"total": doc_count or 0},
                "categories": {"custom_categories": category_count or 0}
            }

        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            return {
                "documents": {"total": 0},
                "categories": {"custom_categories": 0}
            }