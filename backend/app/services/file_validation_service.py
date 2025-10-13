# backend/app/services/file_validation_service.py
"""
File validation service with multi-layer security checks
Validates file type, size, content, and performs malware detection
"""

import os
import io
import magic
import hashlib
import logging
from typing import Optional, List, Dict, BinaryIO, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import db_manager
from app.services.config_service import config_service
from app.services.trust_scoring_service import trust_scoring_service

logger = logging.getLogger(__name__)


class ValidationResult:
    """Structured validation result with warnings and requirements"""
    
    def __init__(
        self,
        allowed: bool,
        captcha_required: bool = False,
        warnings: Optional[List[str]] = None,
        storage_info: Optional[Dict] = None,
        error_message: Optional[str] = None
    ):
        self.allowed = allowed
        self.captcha_required = captcha_required
        self.warnings = warnings or []
        self.storage_info = storage_info or {}
        self.error_message = error_message


class FileValidationService:
    """Handle file validation with behavioral trust analysis"""
    
    # Allowed MIME types organized by category
    ALLOWED_MIME_TYPES = {
        'documents': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain',
            'text/csv',
            'application/rtf'
        ],
        'images': [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'image/tiff',
            'image/bmp'
        ],
        'archives': [
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed'
        ]
    }
    
    # File extensions mapped to MIME types
    ALLOWED_EXTENSIONS = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.rtf': 'application/rtf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.tiff': 'image/tiff',
        '.bmp': 'image/bmp',
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed',
        '.7z': 'application/x-7z-compressed'
    }
    
    # Suspicious patterns in file content (basic malware detection)
    SUSPICIOUS_PATTERNS = [
        b'<script',
        b'javascript:',
        b'eval(',
        b'exec(',
        b'<?php',
        b'<%',
        b'cmd.exe',
        b'powershell'
    ]

    def __init__(self):
        self._magic_mime = None
    
    def _get_magic_mime(self):
        """Lazy load python-magic for MIME type detection"""
        if self._magic_mime is None:
            try:
                self._magic_mime = magic.Magic(mime=True)
            except Exception as e:
                logger.warning(f"Failed to initialize python-magic: {e}")
                self._magic_mime = False
        return self._magic_mime
    
    async def validate_upload(
        self,
        file_content: BinaryIO,
        filename: str,
        user_id: str,
        user_tier: str,
        ip_address: Optional[str] = None,
        session: Optional[Session] = None
    ) -> ValidationResult:
        """
        Multi-layer validation with behavioral trust analysis
        Returns validation result with CAPTCHA requirement if needed
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            # Layer 1: Basic validation (always required)
            basic_result = await self._validate_basic(
                file_content, filename, session
            )
            if not basic_result.allowed:
                return basic_result
            
            # Layer 2: Storage quota check
            quota_result = await self._check_storage_quota(
                file_content, user_id, user_tier, session
            )
            if not quota_result.allowed:
                return quota_result
            
            # Layer 3: Content validation (malware patterns)
            content_result = await self._validate_content(file_content)
            if not content_result.allowed:
                return content_result
            
            # Layer 4: Behavioral trust analysis
            trust_score = await trust_scoring_service.calculate_trust_score(
                user_id, ip_address, session
            )
            
            # Determine if CAPTCHA is required based on trust score
            captcha_required = trust_score < 0.5
            
            # Compile all warnings
            all_warnings = (
                basic_result.warnings + 
                quota_result.warnings + 
                content_result.warnings
            )
            
            # Add trust-based warning if score is low
            if 0.3 <= trust_score < 0.5:
                all_warnings.append(
                    "Unusual upload pattern detected. Quick security check required."
                )
            elif trust_score < 0.3:
                all_warnings.append(
                    "Suspicious activity detected. Enhanced security verification required."
                )
            
            return ValidationResult(
                allowed=True,
                captcha_required=captcha_required,
                warnings=all_warnings,
                storage_info=quota_result.storage_info
            )
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return ValidationResult(
                allowed=False,
                error_message=f"Validation failed: {str(e)}"
            )
        finally:
            if close_session:
                session.close()
    
    async def _validate_basic(
        self,
        file_content: BinaryIO,
        filename: str,
        session: Session
    ) -> ValidationResult:
        """Validate file type, extension, and size"""
        warnings = []
        
        # Check file extension
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return ValidationResult(
                allowed=False,
                error_message=f"File type '{file_ext}' is not supported"
            )
        
        # Get file size
        file_content.seek(0, 2)
        file_size = file_content.tell()
        file_content.seek(0)
        
        # Validate file size
        max_size_mb = await config_service.get_setting(
            'max_file_size_mb', 100, session
        )
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            return ValidationResult(
                allowed=False,
                error_message=f"File size ({file_size / (1024*1024):.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
            )
        
        # Validate MIME type using python-magic
        magic_mime = self._get_magic_mime()
        if magic_mime:
            try:
                detected_mime = magic_mime.from_buffer(file_content.read(2048))
                file_content.seek(0)
                
                # Check if detected MIME matches extension
                expected_mime = self.ALLOWED_EXTENSIONS[file_ext]
                if detected_mime != expected_mime:
                    warnings.append(
                        f"File MIME type ({detected_mime}) doesn't match extension ({file_ext})"
                    )
            except Exception as e:
                logger.warning(f"MIME type detection failed: {e}")
        
        return ValidationResult(
            allowed=True,
            warnings=warnings
        )
    
    async def _check_storage_quota(
        self,
        file_content: BinaryIO,
        user_id: str,
        user_tier: str,
        session: Session
    ) -> ValidationResult:
        """Check user storage quota with friendly warnings"""
        warnings = []
        
        # Get file size
        file_content.seek(0, 2)
        file_size = file_content.tell()
        file_content.seek(0)
        
        # Get current storage usage
        result = session.execute(
            text("""
                SELECT COALESCE(SUM(file_size), 0) as total_size
                FROM documents
                WHERE user_id = :user_id
                AND is_deleted = false
            """),
            {'user_id': user_id}
        ).first()
        
        current_usage = result[0] if result else 0
        
        # Get storage limit for tier
        storage_limit_key = f"storage_limit_{user_tier}_tier_mb"
        storage_limit_mb = await config_service.get_setting(
            storage_limit_key, 1024, session
        )
        storage_limit_bytes = storage_limit_mb * 1024 * 1024
        
        # Calculate usage after upload
        new_usage = current_usage + file_size
        usage_percent = (new_usage / storage_limit_bytes) * 100
        
        # Storage info for response
        storage_info = {
            'current_usage_mb': current_usage / (1024 * 1024),
            'file_size_mb': file_size / (1024 * 1024),
            'new_usage_mb': new_usage / (1024 * 1024),
            'limit_mb': storage_limit_mb,
            'usage_percent': usage_percent,
            'tier': user_tier
        }
        
        # Check if quota exceeded
        if new_usage > storage_limit_bytes:
            return ValidationResult(
                allowed=False,
                error_message=f"Storage quota exceeded. You've used {usage_percent:.1f}% of your {storage_limit_mb}MB limit.",
                storage_info=storage_info
            )
        
        # Friendly warnings at thresholds
        if usage_percent >= 90:
            warnings.append(
                f"⚠️ You're at {usage_percent:.1f}% of your storage limit. "
                f"Consider upgrading or deleting old files."
            )
        elif usage_percent >= 80:
            warnings.append(
                f"📊 You've used {usage_percent:.1f}% of your {storage_limit_mb}MB storage."
            )
        
        return ValidationResult(
            allowed=True,
            warnings=warnings,
            storage_info=storage_info
        )
    
    async def _validate_content(self, file_content: BinaryIO) -> ValidationResult:
        """Scan file content for suspicious patterns"""
        try:
            # Read first 1MB for pattern detection
            file_content.seek(0)
            content_sample = file_content.read(1024 * 1024)
            file_content.seek(0)
            
            # Check for suspicious patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern in content_sample:
                    logger.warning(f"Suspicious pattern detected: {pattern}")
                    return ValidationResult(
                        allowed=False,
                        error_message="File contains potentially malicious content"
                    )
            
            return ValidationResult(allowed=True)
            
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return ValidationResult(
                allowed=False,
                error_message="Unable to validate file content"
            )
    
    def calculate_file_hash(self, file_content: BinaryIO) -> str:
        """Calculate SHA-256 hash of file for duplicate detection"""
        file_content.seek(0)
        file_hash = hashlib.sha256(file_content.read()).hexdigest()
        file_content.seek(0)
        return file_hash
    
    async def check_duplicate(
        self,
        file_hash: str,
        user_id: str,
        session: Session
    ) -> Optional[Dict]:
        """Check if file already exists for user"""
        result = session.execute(
            text("""
                SELECT id, title, filename, created_at
                FROM documents
                WHERE file_hash = :hash
                AND user_id = :user_id
                AND is_deleted = false
                LIMIT 1
            """),
            {'hash': file_hash, 'user_id': user_id}
        ).first()
        
        if result:
            return {
                'id': result[0],
                'title': result[1],
                'filename': result[2],
                'created_at': result[3]
            }
        return None


# Global service instance
file_validation_service = FileValidationService()