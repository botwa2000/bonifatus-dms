# backend/app/services/translation_service.py
"""
Translation service supporting LibreTranslate and DeepL providers
"""

import logging
import httpx
from typing import Optional, Dict, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class TranslationService:
    """Multi-provider translation service with LibreTranslate and DeepL support"""

    def __init__(self):
        self.timeout = settings.translation.translation_timeout
        logger.info("Translation service initialized")

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        user_tier: Optional[str] = None
    ) -> Optional[str]:
        """
        Translate text using appropriate provider based on user tier

        Args:
            text: Text to translate
            source_lang: Source language code (ISO 639-1, e.g., 'en', 'de')
            target_lang: Target language code (ISO 639-1)
            user_tier: User tier ('free', 'paid', etc.) - determines provider

        Returns:
            Translated text or None if translation fails
        """
        if not text or not text.strip():
            return None

        if source_lang == target_lang:
            return text

        try:
            # Determine provider
            provider = self._get_provider(user_tier)

            logger.debug(
                f"Translating with {provider}: {source_lang} -> {target_lang} "
                f"({len(text)} chars)"
            )

            if provider == "deepl":
                return await self._translate_deepl(text, source_lang, target_lang)
            else:
                return await self._translate_libretranslate(text, source_lang, target_lang)

        except Exception as e:
            logger.error(f"Translation failed ({source_lang} -> {target_lang}): {e}")
            return None

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        user_tier: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Translate multiple texts

        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            user_tier: User tier for provider selection

        Returns:
            Dictionary mapping original text to translated text
        """
        results = {}
        for text in texts:
            translated = await self.translate(text, source_lang, target_lang, user_tier)
            results[text] = translated
        return results

    async def _translate_libretranslate(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Optional[str]:
        """
        Translate using LibreTranslate (self-hosted, free)

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated text or None
        """
        try:
            url = settings.translation.translation_libretranslate_url
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{url}/translate",
                    json={
                        "q": text,
                        "source": source_lang,
                        "target": target_lang
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("translatedText")

        except httpx.HTTPStatusError as e:
            logger.error(f"LibreTranslate HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"LibreTranslate translation error: {e}")
            return None

    async def _translate_deepl(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Optional[str]:
        """
        Translate using DeepL API (premium quality, paid)

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated text or None
        """
        try:
            api_key = settings.translation.translation_deepl_api_key
            if not api_key:
                logger.warning("DeepL API key not configured, falling back to LibreTranslate")
                return await self._translate_libretranslate(text, source_lang, target_lang)

            url = settings.translation.translation_deepl_url

            # DeepL expects uppercase language codes for some targets
            target_lang_upper = target_lang.upper()
            source_lang_upper = source_lang.upper()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    data={
                        "auth_key": api_key,
                        "text": text,
                        "source_lang": source_lang_upper,
                        "target_lang": target_lang_upper
                    }
                )
                response.raise_for_status()
                data = response.json()

                translations = data.get("translations", [])
                if translations:
                    return translations[0].get("text")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepL HTTP error: {e.response.status_code} - {e.response.text}")
            # Fall back to LibreTranslate on error
            logger.info("Falling back to LibreTranslate")
            return await self._translate_libretranslate(text, source_lang, target_lang)
        except Exception as e:
            logger.error(f"DeepL translation error: {e}")
            return await self._translate_libretranslate(text, source_lang, target_lang)

    async def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes from database

        Returns:
            List of ISO 639-1 language codes
        """
        from app.database.connection import db_manager
        from app.database.models import SystemSetting
        from sqlalchemy import select

        session = db_manager.session_local()
        try:
            result = session.execute(
                select(SystemSetting.setting_value).where(
                    SystemSetting.setting_key == 'supported_languages'
                )
            ).scalar_one_or_none()

            if result:
                return [lang.strip() for lang in result.split(',')]
            else:
                logger.warning("supported_languages not found in DB, using fallback")
                return ["en"]
        finally:
            session.close()

    def _get_provider(self, user_tier: Optional[str] = None) -> str:
        """
        Determine which translation provider to use

        Args:
            user_tier: User tier ('free', 'paid', etc.)

        Returns:
            Provider name: 'libretranslate' or 'deepl'
        """
        # Check for forced provider (development/testing only)
        force_provider = settings.translation.translation_force_provider
        if force_provider:
            logger.debug(f"Using forced provider: {force_provider}")
            return force_provider

        # Use configured provider from env var
        provider = settings.translation.translation_provider

        # Override for paid users if DeepL is available
        if user_tier == "paid" and settings.translation.translation_deepl_api_key:
            return "deepl"

        return provider


# Global instance
translation_service = TranslationService()
