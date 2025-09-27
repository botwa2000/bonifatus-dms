# backend/app/services/auth_service.py
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth_schemas import TokenData, UserCreate, UserResponse

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
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        
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
                user.last_login_at = datetime.utcnow()
                user.last_login_ip = ip_address
                db.commit()
                
        finally:
            db.close()

    async def logout_user(self, user_id: str, ip_address: str) -> None:
        """Handle user logout operations"""
        logger.info(f"User {user_id} logged out from IP: {ip_address}")

    def generate_tokens(self, user: User) -> Dict[str, str]:
        """Generate access and refresh tokens for user"""
        access_token = self.create_access_token(data={"sub": str(user.id)})
        refresh_token = self.create_refresh_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }


auth_service = AuthService()