# backend/src/auth/security.py
"""
Bonifatus DMS - Security Utilities
Password hashing, JWT token creation, and security helpers
Production-ready cryptographic operations
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import logging
from typing import Optional, Dict, Any

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


def hash_password(password: str) -> str:
    """
    Hash a password with bcrypt
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    """
    try:
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.security.access_token_expire_minutes
            )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "access",
                "jti": secrets.token_urlsafe(32),  # JWT ID for tracking
            }
        )

        encoded_jwt = jwt.encode(
            to_encode,
            settings.security.secret_key,
            algorithm=settings.security.algorithm,
        )

        return encoded_jwt

    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token
    """
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=settings.security.refresh_token_expire_days
        )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "type": "refresh",
                "jti": secrets.token_urlsafe(32),
            }
        )

        encoded_jwt = jwt.encode(
            to_encode,
            settings.security.secret_key,
            algorithm=settings.security.algorithm,
        )

        return encoded_jwt

    except Exception as e:
        logger.error(f"Refresh token creation failed: {e}")
        raise


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token
    """
    try:
        payload = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm],
        )
        return payload

    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return None


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password meets security requirements
    """
    requirements = {
        "min_length": settings.security.password_min_length,
        "require_uppercase": settings.security.password_require_uppercase,
        "require_lowercase": settings.security.password_require_lowercase,
        "require_numbers": settings.security.password_require_numbers,
        "require_symbols": settings.security.password_require_symbols,
    }

    errors = []

    # Check length
    if len(password) < requirements["min_length"]:
        errors.append(
            f"Password must be at least {requirements['min_length']} characters long"
        )

    # Check uppercase
    if requirements["require_uppercase"] and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    # Check lowercase
    if requirements["require_lowercase"] and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    # Check numbers
    if requirements["require_numbers"] and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")

    # Check symbols
    if requirements["require_symbols"]:
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in symbols for c in password):
            errors.append("Password must contain at least one special character")

    return {"valid": len(errors) == 0, "errors": errors, "requirements": requirements}


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token
    """
    return secrets.token_urlsafe(length)


def generate_csrf_token() -> str:
    """
    Generate CSRF protection token
    """
    return secrets.token_urlsafe(32)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks
    """
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
