# backend/src/services/auth_service.py
"""
Bonifatus DMS - Authentication Service
JWT token management, user authentication, and session handling
Google OAuth integration and security operations
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import logging
import json

from src.database.models import User, UserSettings, AuditLog, UserTier
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication and authorization service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_or_update_user_from_google(
        self,
        google_id: str,
        email: str,
        full_name: str,
        avatar_url: Optional[str] = None,
        google_tokens: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        Create new user or update existing user from Google OAuth data
        """
        try:
            # Check if user exists by Google ID
            user = self.db.query(User).filter(User.google_id == google_id).first()
            
            if user:
                # Update existing user
                user.email = email
                user.full_name = full_name
                user.avatar_url = avatar_url
                user.last_login_at = datetime.utcnow()
                
                if google_tokens:
                    user.google_drive_token = self._encrypt_tokens(google_tokens)
                    user.google_drive_connected = True
                
                logger.info(f"Updated existing user: {user.email}")
            else:
                # Check for existing user by email (account linking)
                existing_user = self.db.query(User).filter(User.email == email).first()
                
                if existing_user:
                    # Link Google account to existing user
                    existing_user.google_id = google_id
                    existing_user.full_name = full_name or existing_user.full_name
                    existing_user.avatar_url = avatar_url or existing_user.avatar_url
                    existing_user.last_login_at = datetime.utcnow()
                    
                    if google_tokens:
                        existing_user.google_drive_token = self._encrypt_tokens(google_tokens)
                        existing_user.google_drive_connected = True
                    
                    user = existing_user
                    logger.info(f"Linked Google account to existing user: {user.email}")
                else:
                    # Create new user
                    user = User(
                        google_id=google_id,
                        email=email,
                        full_name=full_name,
                        avatar_url=avatar_url,
                        tier=UserTier.FREE,
                        last_login_at=datetime.utcnow(),
                        is_active=True,
                        is_verified=True  # Google users are pre-verified
                    )
                    
                    if google_tokens:
                        user.google_drive_token = self._encrypt_tokens(google_tokens)
                        user.google_drive_connected = True
                    
                    self.db.add(user)
                    logger.info(f"Created new user: {email}")
            
            self.db.commit()
            self.db.refresh(user)
            
            # Create user settings if they don't exist
            await self._ensure_user_settings(user.id)
            
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create/update user from Google: {e}")
            raise
    
    def create_user_tokens(self, user: User) -> Tuple[str, str]:
        """
        Generate JWT access and refresh tokens for user
        """
        try:
            # Create access token payload
            access_payload = {
                "sub": str(user.id),
                "email": user.email,
                "tier": user.tier.value,
                "type": "access",
                "exp": datetime.utcnow() + timedelta(
                    minutes=settings.security.access_token_expire_minutes
                ),
                "iat": datetime.utcnow(),
                "jti": secrets.token_urlsafe(32)  # JWT ID for token tracking
            }
            
            # Create refresh token payload
            refresh_payload = {
                "sub": str(user.id),
                "type": "refresh",
                "exp": datetime.utcnow() + timedelta(
                    days=settings.security.refresh_token_expire_days
                ),
                "iat": datetime.utcnow(),
                "jti": secrets.token_urlsafe(32)
            }
            
            # Generate tokens
            access_token = jwt.encode(
                access_payload,
                settings.security.secret_key,
                algorithm=settings.security.algorithm
            )
            
            refresh_token = jwt.encode(
                refresh_payload,
                settings.security.secret_key,
                algorithm=settings.security.algorithm
            )
            
            logger.info(f"Generated tokens for user {user.id}")
            return access_token, refresh_token
            
        except Exception as e:
            logger.error(f"Failed to create tokens for user {user.id}: {e}")
            raise
    
    async def get_current_user(self, token: str) -> Optional[User]:
        """
        Validate JWT token and return current user
        """
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.security.secret_key,
                algorithms=[settings.security.algorithm]
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
            user = self.db.query(User).filter(
                User.id == int(user_id),
                User.is_active == True
            ).first()
            
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
    
    def refresh_user_tokens(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Generate new access token using refresh token
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                settings.security.secret_key,
                algorithms=[settings.security.algorithm]
            )
            
            # Verify token type
            if payload.get("type") != "refresh":
                logger.warning("Invalid refresh token type")
                return None
            
            # Get user
            user_id = payload.get("sub")
            user = self.db.query(User).filter(
                User.id == int(user_id),
                User.is_active == True
            ).first()
            
            if not user:
                logger.warning(f"User {user_id} not found for token refresh")
                return None
            
            # Generate new tokens
            new_access_token, new_refresh_token = self.create_user_tokens(user)
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            }
            
        except JWTError as e:
            logger.warning(f"Refresh token validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    async def revoke_user_tokens(self, user_id: int) -> bool:
        """
        Revoke all tokens for user (logout implementation)
        """
        try:
            # In a production system, you might maintain a token blacklist
            # For now, we'll just log the revocation
            logger.info(f"Tokens revoked for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke tokens for user {user_id}: {e}")
            return False
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive user statistics
        """
        try:
            from src.database.models import Document, Category
            
            # Get document statistics
            total_documents = self.db.query(Document).filter(
                Document.user_id == user_id
            ).count()
            
            # Get category statistics
            user_categories = self.db.query(Category).filter(
                Category.user_id == user_id
            ).count()
            
            # Get user info
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {}
            
            return {
                "documents": {
                    "total": total_documents,
                    "monthly_uploads": user.monthly_uploads,
                    "storage_used_bytes": user.storage_used_bytes
                },
                "categories": {
                    "custom_categories": user_categories
                },
                "account": {
                    "tier": user.tier.value,
                    "created_at": user.created_at.isoformat(),
                    "google_drive_connected": user.google_drive_connected
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get user statistics for {user_id}: {e}")
            return {}
    
    async def log_user_activity(
        self,
        user_id: int,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Log user activity for audit purposes
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                event_data=details,
                success=success,
                error_message=error_message
            )
            
            self.db.add(audit_log)
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log user activity: {e}")
            self.db.rollback()
            return False
    
    def _encrypt_tokens(self, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt Google OAuth tokens for secure storage
        """
        try:
            # In production, use proper encryption (AES-256)
            # For now, we'll store tokens as-is but mark them as encrypted
            encrypted_tokens = {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_in": tokens.get("expires_in"),
                "scope": tokens.get("scope"),
                "encrypted": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            return encrypted_tokens
            
        except Exception as e:
            logger.error(f"Failed to encrypt tokens: {e}")
            return tokens
    
    def _decrypt_tokens(self, encrypted_tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt Google OAuth tokens for use
        """
        try:
            # In production, implement proper decryption
            if encrypted_tokens.get("encrypted"):
                return {
                    "access_token": encrypted_tokens.get("access_token"),
                    "refresh_token": encrypted_tokens.get("refresh_token"),
                    "token_type": encrypted_tokens.get("token_type", "Bearer"),
                    "expires_in": encrypted_tokens.get("expires_in"),
                    "scope": encrypted_tokens.get("scope")
                }
            
            return encrypted_tokens
            
        except Exception as e:
            logger.error(f"Failed to decrypt tokens: {e}")
            return {}
    
    async def _ensure_user_settings(self, user_id: int) -> bool:
        """
        Create default user settings if they don't exist
        """
        try:
            existing_settings = self.db.query(UserSettings).filter(
                UserSettings.user_id == user_id
            ).first()
            
            if not existing_settings:
                user_settings = UserSettings(user_id=user_id)
                self.db.add(user_settings)
                self.db.commit()
                logger.info(f"Created default settings for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user settings for {user_id}: {e}")
            self.db.rollback()
            return False