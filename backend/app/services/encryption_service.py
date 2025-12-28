# backend/app/services/encryption_service.py
"""
Encryption service for field-level data protection
Implements AES-256 encryption using Fernet for sensitive data
"""

import os
import logging
from typing import Optional
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib

logger = logging.getLogger(__name__)


class EncryptionService:
    """Handle encryption/decryption of sensitive data"""
    
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialized = False
        
    def initialize(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with key from Docker Swarm secret or parameter

        Args:
            encryption_key: Optional 32-byte base64 key, reads from Docker Swarm secret if not provided

        Raises:
            RuntimeError: If APP_ENVIRONMENT not set
            ValueError: If encryption key secret not found or empty
        """
        if self._initialized:
            return

        key = encryption_key

        if not key:
            # Read from Docker Swarm secret (REQUIRED - no fallbacks)
            app_env = os.getenv('APP_ENVIRONMENT')
            if not app_env:
                raise RuntimeError(
                    "CRITICAL: APP_ENVIRONMENT environment variable must be set to 'development' or 'production'"
                )

            env_suffix = '_dev' if app_env == 'development' else '_prod'
            secret_path = Path(f"/run/secrets/encryption_key{env_suffix}")

            if not secret_path.exists():
                raise ValueError(
                    f"CRITICAL: Encryption key secret file '{secret_path}' not found. "
                    f"Ensure Docker secret 'encryption_key{env_suffix}' is created and mounted to this container."
                )

            try:
                key = secret_path.read_text().strip()
            except Exception as e:
                raise ValueError(
                    f"CRITICAL: Failed to read encryption key from {secret_path}: {e}"
                )

            if not key:
                raise ValueError(
                    f"CRITICAL: Encryption key secret file '{secret_path}' exists but is empty. "
                    f"Secret 'encryption_key{env_suffix}' must contain a valid Fernet key."
                )

            logger.info(f"Loaded encryption key from Docker Swarm secret: encryption_key{env_suffix}")

        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
            self._initialized = True
            logger.info("Encryption service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption with provided key: {e}")
            raise
    
    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: Text to encrypt
            
        Returns:
            Base64-encoded encrypted string or None if encryption fails
        """
        if not self._initialized:
            self.initialize()
            
        if not plaintext:
            return None
            
        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        Decrypt encrypted string
        
        Args:
            ciphertext: Encrypted text to decrypt
            
        Returns:
            Decrypted plaintext or None if decryption fails
        """
        if not self._initialized:
            self.initialize()
            
        if not ciphertext:
            return None
            
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Invalid encryption token - data may be corrupted")
            return None
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def hash_token(self, token: str) -> str:
        """
        Create SHA-256 hash of token for storage
        
        Args:
            token: Token to hash
            
        Returns:
            Hex-encoded hash (64 characters)
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate cryptographically secure random token
        
        Args:
            length: Token length in bytes
            
        Returns:
            URL-safe base64-encoded token
        """
        token_bytes = os.urandom(length)
        return base64.urlsafe_b64encode(token_bytes).decode().rstrip('=')
    
    @staticmethod
    def generate_encryption_key() -> str:
        """
        Generate new Fernet encryption key
        
        Returns:
            Base64-encoded 32-byte key suitable for ENCRYPTION_KEY env var
        """
        return Fernet.generate_key().decode()


# Global instance
encryption_service = EncryptionService()