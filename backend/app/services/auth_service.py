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
from uuid import UUID

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

    def _copy_template_categories_to_user(self, user_id: UUID, db: Session) -> None:
        """
        Copy all template categories (user_id=NULL) to new user's workspace
        Creates personal copies of system categories with all translations and keywords

        IMPORTANT: Only copies if user has NO categories yet (prevents duplicates)
        """
        from app.database.models import Category, CategoryTranslation, CategoryKeyword
        from sqlalchemy import select, func

        try:
            # Check if user already has categories (prevent duplicates)
            existing_count = db.execute(
                select(func.count(Category.id)).where(Category.user_id == user_id)
            ).scalar()

            if existing_count > 0:
                logger.info(f"User {user_id} already has {existing_count} categories, skipping template copy")
                return

            # Get all template categories (user_id is NULL)
            template_categories = db.execute(
                select(Category).where(Category.user_id.is_(None))
            ).scalars().all()

            if not template_categories:
                logger.warning("No template categories found to copy")
                return

            # Map old category IDs to new category IDs
            category_id_map = {}

            # Copy each template category to user's workspace
            for template_cat in template_categories:
                # Create new category for user (no name/description - those are in translations)
                new_category = Category(
                    reference_key=template_cat.reference_key,
                    category_code=template_cat.category_code,
                    color_hex=template_cat.color_hex,
                    icon_name=template_cat.icon_name,
                    is_system=template_cat.is_system,
                    user_id=user_id,
                    sort_order=template_cat.sort_order,
                    is_active=template_cat.is_active,
                    is_multi_lingual=template_cat.is_multi_lingual
                )
                db.add(new_category)
                db.flush()  # Get the new ID

                # Store mapping for reference
                category_id_map[template_cat.id] = new_category.id

                # Copy translations
                translations = db.execute(
                    select(CategoryTranslation).where(
                        CategoryTranslation.category_id == template_cat.id
                    )
                ).scalars().all()

                for trans in translations:
                    new_translation = CategoryTranslation(
                        category_id=new_category.id,
                        language_code=trans.language_code,
                        name=trans.name,
                        description=trans.description
                    )
                    db.add(new_translation)

                # Copy keywords
                keywords = db.execute(
                    select(CategoryKeyword).where(
                        CategoryKeyword.category_id == template_cat.id
                    )
                ).scalars().all()

                for keyword in keywords:
                    new_keyword = CategoryKeyword(
                        category_id=new_category.id,
                        keyword=keyword.keyword,
                        language_code=keyword.language_code,
                        weight=keyword.weight,
                        match_count=keyword.match_count,
                        is_system_default=keyword.is_system_default
                    )
                    db.add(new_keyword)

            db.commit()
            logger.info(f"Copied {len(template_categories)} template categories to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to copy template categories to user {user_id}: {e}")
            db.rollback()
            raise

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
        from sqlalchemy.orm import joinedload

        token_data = self.verify_token(token)

        db = next(get_db())
        try:
            # Eagerly load tier relationship to avoid lazy loading issues
            user = db.query(User).options(joinedload(User.tier)).filter(User.id == token_data.user_id).first()

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
                tier_id=100 if user_create.email in settings.security.admin_emails else 0,  # 100=admin, 0=free
                preferred_doc_languages=["en"]  # Default to English
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            # Copy template categories to new user's workspace
            self._copy_template_categories_to_user(db_user.id, db)

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
                    "tier": user.tier.name if user.tier else "free",
                    "tier_id": user.tier_id,
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
                    
                    is_new_user = False
                    if not user:
                        # Determine tier based on admin status
                        is_admin = email in settings.security.admin_emails
                        user = User(
                            email=email,
                            full_name=full_name,
                            google_id=google_id,
                            profile_picture=profile_picture,
                            is_active=True,
                            is_admin=is_admin,
                            tier_id=100 if is_admin else 0,  # 100=admin, 0=free
                            preferred_doc_languages=["en"]  # Default to English
                        )
                        db.add(user)
                        is_new_user = True
                        logger.info(f"Creating new user: {email}")
                    else:
                        user.google_id = google_id
                        user.profile_picture = profile_picture
                        user.full_name = full_name

                        # Reactivate user if they were deactivated and are now authenticating again
                        if not user.is_active:
                            user.is_active = True
                            logger.info(f"Reactivating previously deactivated user: {email}")
                        else:
                            logger.info(f"Updating existing user: {email}")

                    user.last_login_at = datetime.now(timezone.utc)
                    user.last_login_ip = ip_address

                    db.commit()
                    db.refresh(user)

                    # Copy template categories to new user's workspace
                    if is_new_user:
                        self._copy_template_categories_to_user(user.id, db)

                    # Create session with refresh token
                    session_info = await session_service.create_session(
                        user_id=str(user.id),
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session=db
                    )

                    # Note: Google Drive connection is separate from authentication
                    # Users must explicitly connect Drive from Settings page
                    # Authentication OAuth only grants openid+email+profile scopes

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
                        "tier": user.tier.name if user.tier else "free",
                        "tier_id": user.tier_id,
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