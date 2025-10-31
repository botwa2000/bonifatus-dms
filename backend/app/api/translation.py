# backend/app/api/translation.py
"""
Bonifatus DMS - Translation API Endpoints
Admin-only endpoints for testing and managing translation services
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.middleware.auth_middleware import get_current_admin_user
from app.database.models import User
from app.services.translation_service import translation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/translation", tags=["translation"])


class TranslationTestRequest(BaseModel):
    """Request model for translation testing"""
    text: str = Field(..., description="Text to translate", min_length=1, max_length=5000)
    source_lang: str = Field(..., description="Source language code (ISO 639-1)", min_length=2, max_length=2)
    target_lang: str = Field(..., description="Target language code (ISO 639-1)", min_length=2, max_length=2)
    force_provider: Optional[str] = Field(None, description="Force specific provider (libretranslate or deepl)")


class TranslationTestResponse(BaseModel):
    """Response model for translation testing"""
    original_text: str
    translated_text: Optional[str]
    source_lang: str
    target_lang: str
    provider_used: str
    success: bool


@router.post(
    "/test",
    response_model=TranslationTestResponse,
    responses={
        200: {"model": TranslationTestResponse, "description": "Translation test successful"},
        403: {"description": "Admin privileges required"},
        500: {"description": "Translation service error"}
    }
)
async def test_translation(
    request: TranslationTestRequest,
    current_admin: User = Depends(get_current_admin_user)
) -> TranslationTestResponse:
    """
    Test translation service (Admin only)

    Allows administrators to test the translation service with different providers.
    Useful for verifying LibreTranslate and DeepL configuration.

    **Requires**: Admin privileges
    """
    try:
        logger.info(
            f"Admin {current_admin.email} testing translation: "
            f"{request.source_lang} -> {request.target_lang}"
        )

        # Determine provider
        provider_used = request.force_provider or translation_service._get_provider()

        # Temporarily override provider if requested
        original_force_provider = None
        if request.force_provider:
            from app.core.config import settings
            original_force_provider = settings.translation.translation_force_provider
            settings.translation.translation_force_provider = request.force_provider

        try:
            # Perform translation
            translated_text = await translation_service.translate(
                text=request.text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                user_tier=None  # No tier-based logic for admin tests
            )

            success = translated_text is not None

            logger.info(
                f"Translation test {'succeeded' if success else 'failed'} "
                f"(provider: {provider_used})"
            )

            return TranslationTestResponse(
                original_text=request.text,
                translated_text=translated_text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                provider_used=provider_used,
                success=success
            )

        finally:
            # Restore original force_provider setting
            if original_force_provider is not None:
                from app.core.config import settings
                settings.translation.translation_force_provider = original_force_provider

    except Exception as e:
        logger.error(f"Translation test error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation test failed: {str(e)}"
        )


@router.get(
    "/languages",
    responses={
        200: {"description": "List of supported language codes"},
        403: {"description": "Admin privileges required"}
    }
)
async def get_supported_languages(
    current_admin: User = Depends(get_current_admin_user)
) -> dict:
    """
    Get list of supported translation languages (Admin only)

    Returns ISO 639-1 language codes supported by the translation service.

    **Requires**: Admin privileges
    """
    try:
        languages = await translation_service.get_supported_languages()
        return {
            "languages": languages,
            "count": len(languages)
        }
    except Exception as e:
        logger.error(f"Get languages error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve supported languages"
        )
