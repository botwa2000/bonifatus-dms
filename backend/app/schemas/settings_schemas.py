# backend/app/schemas/settings_schemas.py
"""
Bonifatus DMS - Settings & Localization Schemas
Pydantic models for system settings and localization
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SystemSettingsResponse(BaseModel):
    """Public system settings response"""
    settings: Dict[str, Any] = Field(
        ...,
        description="Dictionary of public system settings",
        example={
            "default_language": "en",
            "available_languages": ["en", "de", "ru"],
            "default_theme": "light",
            "available_themes": ["light", "dark"],
            "max_file_size_mb": 50
        }
    )


class LocalizationResponse(BaseModel):
    """Localization strings response"""
    language_code: str = Field(..., description="ISO 639-1 language code", example="en")
    context: Optional[str] = Field(None, description="Context filter", example="navigation")
    strings: Dict[str, str] = Field(
        ...,
        description="Dictionary of localized strings",
        example={
            "nav.dashboard": "Dashboard",
            "nav.documents": "Documents",
            "nav.settings": "Settings"
        }
    )


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message")