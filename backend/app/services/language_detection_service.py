# backend/app/services/language_detection_service.py
"""
Language detection service - database-driven, scalable for any language
"""

import logging
import re
from typing import Dict, Optional
from collections import defaultdict
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.database.models import LanguageDetectionPattern
from app.services.config_service import config_service

logger = logging.getLogger(__name__)


class LanguageDetectionService:
    """Database-driven language detection service"""
    
    def __init__(self):
        self._patterns_cache: Dict[str, list] = {}
        self._cache_loaded = False
    
    async def detect_language(
        self,
        text: str,
        session: Optional[Session] = None
    ) -> str:
        """
        Detect document language using database patterns
        
        Args:
            text: Text to analyze
            session: Optional database session
            
        Returns:
            Language code (e.g., 'en', 'de', 'ru')
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            # Load patterns if not cached
            if not self._cache_loaded:
                await self._load_patterns(session)
            
            if not self._patterns_cache:
                # No patterns loaded, use fallback
                fallback = await config_service.get_setting('fallback_language', 'en', session)
                logger.warning(f"No language detection patterns loaded, using fallback: {fallback}")
                return fallback
            
            # Prepare text for analysis
            text_lower = text.lower()
            
            # Calculate scores for each language
            language_scores = defaultdict(float)
            
            for lang_code, patterns in self._patterns_cache.items():
                for pattern_data in patterns:
                    pattern = pattern_data['pattern']
                    pattern_type = pattern_data['pattern_type']
                    weight = pattern_data['weight']
                    
                    if pattern_type == 'common_word':
                        # Count occurrences of common words (with word boundaries)
                        regex = r'\b' + re.escape(pattern) + r'\b'
                        matches = len(re.findall(regex, text_lower))
                        language_scores[lang_code] += matches * weight
                    
                    elif pattern_type == 'character_set':
                        # Count occurrences of language-specific characters
                        matches = text_lower.count(pattern)
                        language_scores[lang_code] += matches * weight
                    
                    elif pattern_type == 'grammar':
                        # Pattern-based grammar detection (e.g., word endings)
                        # Can be extended for more complex patterns
                        if pattern in text_lower:
                            language_scores[lang_code] += weight
            
            # Get language with highest score
            if language_scores:
                detected_lang = max(language_scores, key=language_scores.get)
                max_score = language_scores[detected_lang]
                
                # Log scores for debugging
                logger.info(f"Language detection scores: {dict(language_scores)}")
                logger.info(f"Detected language: {detected_lang} (score: {max_score})")
                
                # Require minimum score threshold
                min_score = await config_service.get_setting('min_language_detection_score', 10.0, session)
                
                if max_score >= min_score:
                    return detected_lang
            
            # Fallback if no clear winner
            fallback = await config_service.get_setting('fallback_language', 'en', session)
            logger.info(f"Language detection inconclusive, using fallback: {fallback}")
            return fallback
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            # Return fallback on error
            fallback = await config_service.get_setting('fallback_language', 'en', session)
            return fallback
        finally:
            if close_session:
                session.close()
    
    async def _load_patterns(self, session: Session):
        """Load language detection patterns from database"""
        try:
            result = session.execute(
                select(
                    LanguageDetectionPattern.language_code,
                    LanguageDetectionPattern.pattern,
                    LanguageDetectionPattern.pattern_type,
                    LanguageDetectionPattern.weight
                ).where(
                    LanguageDetectionPattern.is_active == True
                ).order_by(
                    LanguageDetectionPattern.language_code,
                    LanguageDetectionPattern.weight.desc()
                )
            )

            # Group patterns by language
            for row in result:
                lang_code = row[0]
                if lang_code not in self._patterns_cache:
                    self._patterns_cache[lang_code] = []

                self._patterns_cache[lang_code].append({
                    'pattern': row[1],
                    'pattern_type': row[2],
                    'weight': row[3]
                })

            self._cache_loaded = True
            logger.info(f"Loaded language detection patterns for: {list(self._patterns_cache.keys())}")

        except Exception as e:
            logger.error(f"Failed to load language detection patterns: {e}", exc_info=True)
            # Roll back the transaction to prevent "InFailedSqlTransaction" errors
            # on subsequent queries in the same session
            session.rollback()
            logger.info("Transaction rolled back after pattern loading failure")
    
    async def get_supported_languages(self, session: Optional[Session] = None) -> list:
        """Get list of supported languages"""
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            result = session.execute(
                text("""
                    SELECT DISTINCT language_code
                    FROM language_detection_patterns
                    WHERE is_active = true
                    ORDER BY language_code
                """)
            )
            
            languages = [row[0] for row in result]
            return languages
            
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return ['en']  # Fallback
        finally:
            if close_session:
                session.close()
    
    async def add_language_pattern(
        self,
        language_code: str,
        pattern: str,
        pattern_type: str,
        weight: float = 1.0,
        session: Optional[Session] = None
    ):
        """Add a new language detection pattern"""
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            import uuid
            from datetime import datetime, timezone
            
            session.execute(
                text("""
                    INSERT INTO language_detection_patterns 
                    (id, language_code, pattern, pattern_type, weight, is_active, created_at, updated_at)
                    VALUES (:id, :lang, :pattern, :ptype, :weight, true, :created, :updated)
                    ON CONFLICT (language_code, pattern) DO UPDATE
                    SET weight = :weight, updated_at = :updated
                """),
                {
                    'id': str(uuid.uuid4()),
                    'lang': language_code,
                    'pattern': pattern,
                    'ptype': pattern_type,
                    'weight': weight,
                    'created': datetime.now(timezone.utc),
                    'updated': datetime.now(timezone.utc)
                }
            )
            session.commit()
            
            # Clear cache to reload
            self._cache_loaded = False
            self._patterns_cache = {}
            
            logger.info(f"Added language pattern: {language_code} - {pattern}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add language pattern: {e}")
        finally:
            if close_session:
                session.close()
    
    def clear_cache(self):
        """Clear patterns cache"""
        self._patterns_cache = {}
        self._cache_loaded = False
        logger.info("Language detection cache cleared")


# Global instance
language_detection_service = LanguageDetectionService()