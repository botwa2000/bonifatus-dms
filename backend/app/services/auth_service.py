# backend/src/services/auth_service.py
"""
Bonifatus DMS - JWT Authentication Service
Token generation, validation, and Google OAuth integration
"""

import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.database.models import User, AuditLog
from app.database.connection import db_manager

logger = logging.getLogger(__name__)


class AuthService:
    """JWT authentication and Google OAuth integration service"""

    def __init__(self):
        self.secret_key = settings.security.security_secret_key
        self.algorithm = settings.security.algorithm
        self.access_token_expire_minutes = settings.security.access_token_expire_minutes
        self.refresh_token_expire_days = settings.security.refresh_token_expire_days
        self.default_user_tier = settings.security.default_user_tier
        self.google_oauth_issuers = settings.google_oauth_issuer_list

    def generate_access_token(self, user_id: str, email: str, tier: str = None) -> str:
        """Generate JWT access token with user claims"""
        try:
            if tier is None:
                tier = self.default_user_tier
                
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            payload = {
                "sub": user_id,
                "email": email,
                "tier": tier,
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access"
            }
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"Failed to generate access token: {e}")
            raise

    def generate_refresh_token(self, user_id: str) -> str:
        """Generate JWT refresh token with extended expiry"""
        try:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
            payload = {
                "sub": user_id,
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh"
            }
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"Failed to generate refresh token: {e}")
            raise

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type. Expected: {token_type}, Got: {payload.get('type')}")
                return None
                
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    async def verify_google_token(self, google_token: str) -> Optional[Dict[str, Any]]:
        """Verify Google OAuth ID token"""
        try:
            id_info = id_token.verify_oauth2_token(
                google_token, 
                requests.Request(), 
                settings.google.google_client_id
            )
            
            if id_info['iss'] not in self.google_oauth_issuers:
                logger.warning(f"Invalid Google token issuer: {id_info['iss']}")
                return None
                
            return {
                "google_id": id_info['sub'],
                "email": id_info['email'],
                "full_name": id_info.get('name', ''),
                "profile_picture": id_info.get('picture', ''),
                "email_verified": id_info.get('email_verified', False)
            }
        except ValueError as e:
            logger.error(f"Google token verification failed: {e}")
            return None

    async def authenticate_with_google(self, google_token: str, ip_address: str = None) -> Optional[Dict[str, str]]:
        """Authenticate user with Google OAuth and return JWT tokens"""
        session = db_manager.session_local()
        try:
            google_user_info = await self.verify_google_token(google_token)
            if not google_user_info:
                await self._log_auth_attempt(None, "google_auth_failed", "invalid_token", ip_address, session)
                return None

            if not google_user_info.get('email_verified'):
                await self._log_auth_attempt(None, "google_auth_failed", "email_not_verified", ip_address, session)
                return None

            user = await self._get_or_create_user(google_user_info, session)
            if not user:
                await self._log_auth_attempt(None, "user_creation_failed", "database_error", ip_address, session)
                return None

            if not user.is_active:
                await self._log_auth_attempt(str(user.id), "auth_failed", "user_inactive", ip_address, session)
                return None

            # Update last login
            user.last_login_at = datetime.utcnow()
            session.commit()

            # Generate tokens
            access_token = self.generate_access_token(str(user.id), user.email, user.tier)
            refresh_token = self.generate_refresh_token(str(user.id))

            await self._log_auth_attempt(str(user.id), "login_success", "google_oauth", ip_address, session)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user_id": str(user.id),
                "email": user.email,
                "tier": user.tier
            }

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    async def refresh_access_token(self, refresh_token: str, ip_address: str = None) -> Optional[Dict[str, str]]:
        """Generate new access token from refresh token"""
        session = db_manager.session_local()
        try:
            payload = self.verify_token(refresh_token, "refresh")
            if not payload:
                await self._log_auth_attempt(None, "token_refresh_failed", "invalid_token", ip_address, session)
                return None

            user_id = payload.get("sub")
            user = session.get(User, user_id)
            
            if not user or not user.is_active:
                await self._log_auth_attempt(user_id, "token_refresh_failed", "user_not_found", ip_address, session)
                return None

            access_token = self.generate_access_token(str(user.id), user.email, user.tier)
            
            await self._log_auth_attempt(str(user.id), "token_refresh_success", "refresh_token", ip_address, session)

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user_id": str(user.id),
                "email": user.email,
                "tier": user.tier
            }

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
        finally:
            session.close()

    async def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT access token"""
        session = db_manager.session_local()
        try:
            payload = self.verify_token(token, "access")
            if not payload:
                return None

            user_id = payload.get("sub")
            user = session.get(User, user_id)
            
            if not user or not user.is_active:
                return None

            return user

        except Exception as e:
            logger.error(f"Get current user error: {e}")
            return None
        finally:
            session.close()

    async def _get_or_create_user(self, google_user_info: Dict[str, Any], session: Session) -> Optional[User]:
        """Get existing user or create new user from Google info"""
        try:
            # Try to find existing user by Google ID
            stmt = select(User).where(User.google_id == google_user_info["google_id"])
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                # Update user info from Google
                user.email = google_user_info["email"]
                user.full_name = google_user_info["full_name"]
                user.profile_picture = google_user_info["profile_picture"]
                session.commit()
                return user

            # Try to find by email (user might have changed Google account)
            stmt = select(User).where(User.email == google_user_info["email"])
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                # Link Google account to existing user
                user.google_id = google_user_info["google_id"]
                user.full_name = google_user_info["full_name"]
                user.profile_picture = google_user_info["profile_picture"]
                session.commit()
                return user

            # Create new user
            user = User(
                google_id=google_user_info["google_id"],
                email=google_user_info["email"],
                full_name=google_user_info["full_name"],
                profile_picture=google_user_info["profile_picture"],
                tier=self.default_user_tier,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"Created new user: {user.email}")
            return user

        except Exception as e:
            logger.error(f"User creation/update error: {e}")
            session.rollback()
            return None

    async def _log_auth_attempt(self, user_id: str, action: str, status: str, ip_address: str, session: Session):
        """Log authentication attempt for audit trail"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="authentication",
                resource_id=user_id,
                ip_address=ip_address,
                status="success" if "success" in action else "failed",
                new_values=status,
                endpoint="/api/v1/auth"
            )
            session.add(audit_log)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log auth attempt: {e}")


# Global auth service instance
auth_service = AuthService()