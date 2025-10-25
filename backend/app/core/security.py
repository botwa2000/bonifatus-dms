# backend/app/core/security.py
"""
Security utilities for encryption and token management

This module provides secure encryption/decryption functions using the
application's encryption service with a dedicated ENCRYPTION_KEY.
"""

from app.services.encryption_service import encryption_service


def encrypt_token(token: str) -> str:
    """
    Encrypt a token (like refresh token) for secure storage

    Uses the application's encryption service with dedicated ENCRYPTION_KEY
    from environment variables. This provides proper AES-256 encryption via Fernet.

    Args:
        token: Plain text token to encrypt

    Returns:
        Base64-encoded encrypted token

    Raises:
        ValueError: If token is empty
    """
    if not token:
        raise ValueError("Token cannot be empty")

    # Ensure encryption service is initialized with ENCRYPTION_KEY from env
    encryption_service.initialize()

    encrypted = encryption_service.encrypt(token)
    if not encrypted:
        raise RuntimeError("Token encryption failed")

    return encrypted


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an encrypted token

    Uses the application's encryption service with dedicated ENCRYPTION_KEY
    from environment variables. This provides proper AES-256 decryption via Fernet.

    Args:
        encrypted_token: Base64-encoded encrypted token

    Returns:
        Decrypted plain text token

    Raises:
        ValueError: If encrypted_token is empty
        RuntimeError: If decryption fails
    """
    if not encrypted_token:
        raise ValueError("Encrypted token cannot be empty")

    # Ensure encryption service is initialized with ENCRYPTION_KEY from env
    encryption_service.initialize()

    decrypted = encryption_service.decrypt(encrypted_token)
    if not decrypted:
        raise RuntimeError("Token decryption failed")

    return decrypted
