# backend/app/services/auth_service.py
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.database.connection import get_db
from app.database.models import User
from app.schemas.auth_schemas import TokenData, UserCreate, UserResponse

from app.services.session_service import session_service
from app.services.encryption_service import encryption_service

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for user management and JWT operations"""

    def __init__(self):
        self.secret_key = settings.security.security_secret_key
        self.algorithm = settings.security.algorithm
        self.access_token_expire_minutes = settings.security.access_token_expire_minutes
        self.refresh_token_expire_days = settings.security.refresh_token_expire_days

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access", "iat": datetime.now(timezone.utc)})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            
            if user_id is None:
                raise InvalidTokenError("Token missing user identifier")
            
            return TokenData(user_id=user_id)
            
        except InvalidTokenError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_current_user(self, token: str) -> User:
        """Get current user from JWT token"""
        token_data = self.verify_token(token)
        
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == token_data.user_id).first()
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return user
            
        finally:
            db.close()

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        db = next(get_db())
        try:
            user = db.query(User).filter(User.email == email).first()
            
            if not user or not self.verify_password(password, user.hashed_password):
                return None
            
            return user
            
        finally:
            db.close()

    async def create_user(self, user_create: UserCreate) -> User:
        """Create new user account"""
        db = next(get_db())
        try:
            existing_user = db.query(User).filter(User.email == user_create.email).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

            hashed_password = self.get_password_hash(user_create.password)
            
            db_user = User(
                email=user_create.email,
                full_name=user_create.full_name,
                hashed_password=hashed_password,
                is_active=True,
                is_admin=user_create.email in settings.security.admin_emails,
                tier=settings.security.default_user_tier
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            logger.info(f"User created: {db_user.email}")
            return db_user
            
        finally:
            db.close()

    async def update_last_login(self, user_id: str, ip_address: str) -> None:
        """Update user's last login timestamp and IP"""
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login_at = datetime.now(timezone.utc)
                user.last_login_ip = ip_address
                user.failed_login_attempts = 0
                db.commit()
                
        finally:
            db.close()

    async def logout_user(self, user_id: str, session_id: Optional[str] = None, ip_address: str = "") -> None:
        """Handle user logout - revoke session"""
        if session_id:
            await session_service.revoke_session(session_id, reason="user_logout")
            logger.info(f"User {user_id} logged out from IP: {ip_address}")
        else:
            await session_service.revoke_user_sessions(user_id, reason="user_logout")
            logger.info(f"All sessions revoked for user {user_id}")

    async def refresh_access_token(
        self, 
        refresh_token: str, 
        ip_address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate new access token using refresh token
        
        Args:
            refresh_token: Refresh token from client
            ip_address: Client IP address
            
        Returns:
            Dict with new access_token and user info, or None if invalid
        """
        try:
            session_info = await session_service.validate_session(refresh_token)
            
            if not session_info:
                logger.warning(f"Invalid refresh token from IP: {ip_address}")
                return None
            
            user_id = session_info['user_id']
            
            db = next(get_db())
            try:
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user or not user.is_active:
                    logger.warning(f"User {user_id} not found or inactive")
                    await session_service.revoke_session(session_info['session_id'], reason="user_inactive")
                    return None
                
                access_token = self.create_access_token(data={"sub": str(user.id)})
                
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user_id": str(user.id),
                    "email": user.email,
                    "tier": user.tier,
                    "expires_in": self.access_token_expire_minutes * 60
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None

    def generate_tokens(self, user: User) -> Dict[str, str]:
        """Generate access and refresh tokens for user"""
        access_token = self.create_access_token(data={"sub": str(user.id)})
        refresh_token = self.create_refresh_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def authenticate_with_google_code(
            self, 
            authorization_code: str,
            ip_address: str,
            user_agent: str
        ) -> Optional[Dict[str, Any]]:
            """
            Authenticate user with Google authorization code
            Exchanges code for ID token, verifies it, and creates/updates user
            """
            try:
                import httpx
                from google.oauth2 import id_token
                from google.auth.transport import requests as google_requests
                
                # Exchange authorization code for tokens
                token_url = "https://oauth2.googleapis.com/token"
                token_data = {
                    "code": authorization_code,
                    "client_id": settings.google.google_client_id,
                    "client_secret": settings.google.google_client_secret,
                    "redirect_uri": settings.google.google_redirect_uri,
                    "grant_type": "authorization_code"
                }
                
                async with httpx.AsyncClient() as client:
                    token_response = await client.post(token_url, data=token_data)
                    
                    if token_response.status_code != 200:
                        logger.error(f"Token exchange failed: {token_response.text}")
                        return None
                    
                    tokens = token_response.json()
                    google_id_token = tokens.get("id_token")
                    
                    if not google_id_token:
                        logger.error("No ID token in response")
                        return None
                
                # Verify ID token
                try:
                    id_info = id_token.verify_oauth2_token(
                        google_id_token,
                        google_requests.Request(),
                        settings.google.google_client_id
                    )
                    
                    if id_info.get("iss") not in settings.google.google_oauth_issuers:
                        logger.error(f"Invalid token issuer: {id_info.get('iss')}")
                        return None
                        
                except ValueError as e:
                    logger.error(f"Token verification failed: {e}")
                    return None
                
                # Extract user information
                google_id = id_info.get("sub")
                email = id_info.get("email")
                full_name = id_info.get("name", email.split("@")[0])
                profile_picture = id_info.get("picture")
                
                if not email or not google_id:
                    logger.error("Missing required user information")
                    return None
                
                # Get or create user
                db = next(get_db())
                try:
                    user = db.query(User).filter(User.email == email).first()
                    
                    if not user:
                        user = User(
                            email=email,
                            full_name=full_name,
                            google_id=google_id,
                            profile_picture=profile_picture,
                            is_active=True,
                            tier=settings.security.default_user_tier
                        )
                        db.add(user)
                        logger.info(f"Creating new user: {email}")
                    else:
                        user.google_id = google_id
                        user.profile_picture = profile_picture
                        user.full_name = full_name
                        logger.info(f"Updating existing user: {email}")
                    
                    user.last_login_at = datetime.now(timezone.utc)
                    user.last_login_ip = ip_address
                    
                    db.commit()
                    db.refresh(user)

                    # Create session with refresh token
                    session_info = await session_service.create_session(
                        user_id=str(user.id),
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session=db
                    )

                    # Generate short-lived access token
                    access_token = self.create_access_token(data={"sub": str(user.id)})

                    # Encrypt and store Google refresh token if provided
                    google_refresh_token = tokens.get('refresh_token')
                    if google_refresh_token:
                        encrypted_token = encryption_service.encrypt(google_refresh_token)
                        if encrypted_token:
                            user.drive_refresh_token_encrypted = encrypted_token
                            user.google_drive_enabled = True
                            user.drive_permissions_granted_at = datetime.now(timezone.utc)
                            db.commit()

                    if not user.is_active:
                        logger.warning(f"Inactive user attempted login: {email}")
                        return None
                    
                    # Generate JWT tokens
                    access_token = self.create_access_token(data={"sub": str(user.id)})
                    refresh_token = self.create_refresh_token(data={"sub": str(user.id)})
                    
                    return {
                        "access_token": access_token,
                        "refresh_token": session_info['refresh_token'],
                        "token_type": "bearer",
                        "user_id": str(user.id),
                        "email": user.email,
                        "full_name": user.full_name,
                        "profile_picture": user.profile_picture,
                        "tier": user.tier,
                        "is_active": user.is_active,
                        "session_id": session_info['session_id'],
                        "expires_in": self.access_token_expire_minutes * 60
                    }
                    
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Google authentication error: {e}")
                return None


auth_service = AuthService()