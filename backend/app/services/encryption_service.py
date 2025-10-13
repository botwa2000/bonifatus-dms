# backend/app/services/encryption_service.py
"""
Encryption service for field-level data protection
Implements AES-256 encryption using Fernet for sensitive data
"""

import os
import logging
from typing import Optional
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
        Initialize encryption with key from environment or parameter
        
        Args:
            encryption_key: Optional 32-byte base64 key, reads from env if not provided
        """
        if self._initialized:
            return
            
        key = encryption_key or os.getenv('ENCRYPTION_KEY')
        
        if not key:
            logger.warning("No encryption key provided, generating temporary key")
            key = Fernet.generate_key().decode()
            logger.warning(f"Generated key (save to env): {key}")
        
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
            self._initialized = True
            logger.info("Encryption service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
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