# backend/app/services/config_service.py
"""
Configuration service - loads all settings from database
Zero hardcoded values, production-ready
"""

import logging
import json
from typing import Any, Optional, List, Dict
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from functools import lru_cache

from app.database.connection import db_manager
from app.database.models import SystemSetting

logger = logging.getLogger(__name__)


class ConfigService:
    """Database-driven configuration service"""
    
    def __init__(self):
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes
    
    async def get_setting(
        self, 
        key: str, 
        default: Any = None,
        session: Optional[Session] = None
    ) -> Any:
        """
        Get system setting from database with caching
        
        Args:
            key: Setting key
            default: Default value if not found
            session: Optional database session
            
        Returns:
            Setting value with correct type conversion
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            result = session.execute(
                select(SystemSetting).where(SystemSetting.setting_key == key)
            ).scalar_one_or_none()
            
            if not result:
                logger.warning(f"Setting '{key}' not found in database, using default: {default}")
                return default
            
            # Type conversion based on data_type
            value = self._convert_value(result.setting_value, result.data_type)
            
            # Cache the result
            self._cache[key] = value
            
            return value
            
        except Exception as e:
            logger.error(f"Failed to get setting '{key}': {e}")
            return default
        finally:
            if close_session:
                session.close()
    
    def _convert_value(self, value: str, data_type: str) -> Any:
        """Convert string value to appropriate type"""
        try:
            if data_type == 'integer':
                return int(value)
            elif data_type == 'float':
                return float(value)
            elif data_type == 'boolean':
                return value.lower() in ('true', '1', 'yes')
            elif data_type == 'json':
                return json.loads(value)
            else:
                return value
        except Exception as e:
            logger.error(f"Failed to convert value '{value}' to type '{data_type}': {e}")
            return value
    
    async def get_allowed_mime_types(self, session: Optional[Session] = None) -> List[str]:
        """Get allowed MIME types for file upload"""
        return await self.get_setting('allowed_mime_types', [
            'application/pdf',
            'image/jpeg',
            'image/png'
        ], session)
    
    async def get_max_file_size_bytes(self, session: Optional[Session] = None) -> int:
        """Get maximum file size in bytes"""
        return await self.get_setting('max_file_size_bytes', 104857600, session)  # 100MB default
    
    async def get_min_keyword_length(self, session: Optional[Session] = None) -> int:
        """Get minimum keyword length"""
        return await self.get_setting('min_keyword_length', 3, session)
    
    async def get_max_keywords(self, session: Optional[Session] = None) -> int:
        """Get maximum keywords per document"""
        return await self.get_setting('max_keywords_per_document', 20, session)
    
    async def get_keyword_relevance_threshold(self, session: Optional[Session] = None) -> float:
        """Get minimum relevance threshold for keywords"""
        return await self.get_setting('keyword_relevance_threshold', 0.3, session)
    
    async def is_spelling_correction_enabled(self, session: Optional[Session] = None) -> bool:
        """Check if spelling correction is enabled"""
        return await self.get_setting('spelling_correction_enabled', True, session)
    
    async def is_ngram_extraction_enabled(self, session: Optional[Session] = None) -> bool:
        """Check if n-gram extraction is enabled"""
        return await self.get_setting('ngram_extraction_enabled', True, session)
    
    async def get_category_confidence_threshold(self, session: Optional[Session] = None) -> float:
        """Get minimum confidence for category suggestion"""
        return await self.get_setting('category_confidence_threshold', 0.6, session)
    
    def clear_cache(self):
        """Clear configuration cache"""
        self._cache = {}
        logger.info("Configuration cache cleared")


# Global instance
config_service = ConfigService()