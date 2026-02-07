# backend/app/services/language_detection_service.py
"""
Language detection service using FastText and Lingua libraries
"""

import logging
from typing import Optional
from ftlangdetect import detect as fasttext_detect
from lingua import Language, LanguageDetectorBuilder

logger = logging.getLogger(__name__)


class LanguageDetectionService:
    """Hybrid language detection using FastText for speed and Lingua for accuracy"""

    def __init__(self):
        # Lingua detector for short texts (75 languages)
        self.lingua = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH,
            Language.GERMAN,
            Language.RUSSIAN,
            Language.FRENCH,
            Language.SPANISH,
            Language.ITALIAN,
            Language.DUTCH,
            Language.PORTUGUESE,
            Language.POLISH,
            Language.CZECH,
            Language.UKRAINIAN,
            Language.TURKISH
        ).build()

        # Thresholds
        self.SHORT_TEXT_THRESHOLD = 20  # words
        self.MIN_CONFIDENCE = 0.7

        logger.info("Language detection service initialized")

    async def detect_language(
        self,
        text: str,
        session: Optional[object] = None  # Kept for API compatibility
    ) -> str:
        """
        Detect document language

        Args:
            text: Text to analyze
            session: Unused (kept for backward compatibility)

        Returns:
            ISO 639-1 language code (e.g., 'en', 'de', 'ru')
        """
        if not text or not text.strip():
            return 'en'

        try:
            word_count = len(text.split())

            if word_count < self.SHORT_TEXT_THRESHOLD:
                # Short text: Use Lingua for better accuracy
                result = self.lingua.detect_language_of(text)
                if result:
                    lang_code = result.iso_code_639_1.name.lower()
                    logger.debug(f"Lingua detected: {lang_code} ({word_count} words)")
                    return lang_code
                return 'en'
            else:
                # Long text: Use FastText for speed
                # FastText requires single-line input (no newlines)
                text_sanitized = ' '.join(text.split())
                result = fasttext_detect(text_sanitized)
                lang_code = result['lang']
                confidence = result['score']

                if confidence >= self.MIN_CONFIDENCE:
                    logger.debug(f"FastText detected: {lang_code} (confidence: {confidence:.2f})")
                    return lang_code
                else:
                    # Low confidence: Fall back to Lingua
                    logger.debug(f"Low FastText confidence ({confidence:.2f}), using Lingua")
                    lingua_result = self.lingua.detect_language_of(text)
                    if lingua_result:
                        return lingua_result.iso_code_639_1.name.lower()
                    return lang_code

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return 'en'

    async def get_supported_languages(self, session: Optional[object] = None) -> list:
        """Get list of supported languages from database"""
        from app.database.connection import db_manager
        from app.database.models import SystemSetting
        from sqlalchemy import select

        db_session = session if session else db_manager.session_local()
        try:
            result = db_session.execute(
                select(SystemSetting.setting_value).where(
                    SystemSetting.setting_key == 'supported_languages'
                )
            ).scalar_one_or_none()

            if result:
                return [lang.strip() for lang in result.split(',')]
            else:
                logger.warning("supported_languages not found in DB, using fallback")
                return ['en']
        finally:
            if not session:
                db_session.close()


# Global instance
language_detection_service = LanguageDetectionService()
