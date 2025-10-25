# backend/app/core/security.py
"""
Security utilities for encryption and token management
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from app.core.config import settings


def _get_encryption_key() -> bytes:
    """
    Derive encryption key from secret key

    Uses PBKDF2 to derive a Fernet-compatible key from the JWT secret
    """
    # Use JWT secret as password for key derivation
    password = settings.auth.jwt_secret_key.encode()

    # Use a fixed salt (in production, this should be from env var)
    # For now, derive from secret to ensure consistency
    salt = base64.b64encode(password[:16].ljust(16, b'0'))[:16]

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )

    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_token(token: str) -> str:
    """
    Encrypt a token (like refresh token) for secure storage

    Args:
        token: Plain text token to encrypt

    Returns:
        Base64-encoded encrypted token
    """
    if not token:
        raise ValueError("Token cannot be empty")

    key = _get_encryption_key()
    f = Fernet(key)

    encrypted = f.encrypt(token.encode())
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an encrypted token

    Args:
        encrypted_token: Base64-encoded encrypted token

    Returns:
        Decrypted plain text token
    """
    if not encrypted_token:
        raise ValueError("Encrypted token cannot be empty")

    key = _get_encryption_key()
    f = Fernet(key)

    encrypted_bytes = base64.b64decode(encrypted_token.encode())
    decrypted = f.decrypt(encrypted_bytes)
    return decrypted.decode('utf-8')
