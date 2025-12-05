# backend/app/api/settings.py
"""
Bonifatus DMS - Settings & Localization API Endpoints
Public system settings and multilingual UI strings
"""

import logging
import json
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select
from pydantic import BaseModel

from app.schemas.settings_schemas import (
    SystemSettingsResponse,
    LocalizationResponse,
    ErrorResponse
)
from app.database.models import SystemSetting, LocalizationString, UserSetting, User, Currency, CookieCategory, CookieCategoryTranslation, CookieDefinition, CookieDefinitionTranslation
from app.database.connection import db_manager
from app.api.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class ThemePreference(BaseModel):
    value: str  # 'light' or 'dark'


@router.get(
    "",
    response_model=SystemSettingsResponse,
    responses={
        200: {"model": SystemSettingsResponse, "description": "Public system settings"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_public_system_settings() -> SystemSettingsResponse:
    """
    Get public system settings

    Returns all public system settings available to unauthenticated users.
    Used by frontend to configure UI options (languages, themes, etc.)

    Note: available_languages is dynamically generated from language_metadata keys
    to avoid maintaining duplicate hardcoded lists.
    """
    session = db_manager.session_local()
    try:
        stmt = select(SystemSetting).where(SystemSetting.is_public == True)
        settings = session.execute(stmt).scalars().all()

        settings_dict = {}
        for setting in settings:
            key = setting.setting_key
            value = setting.setting_value

            # Parse JSON values
            if setting.data_type == 'json':
                try:
                    settings_dict[key] = json.loads(value)
                except json.JSONDecodeError:
                    settings_dict[key] = value
            # Parse boolean values
            elif setting.data_type == 'boolean':
                settings_dict[key] = value.lower() in ('true', '1', 'yes')
            # Parse integer values
            elif setting.data_type == 'integer':
                try:
                    settings_dict[key] = int(value)
                except ValueError:
                    settings_dict[key] = value
            # String values
            else:
                settings_dict[key] = value

        # Override available_languages with keys from language_metadata
        # This ensures the language list is always in sync with defined languages
        if 'language_metadata' in settings_dict and isinstance(settings_dict['language_metadata'], dict):
            settings_dict['available_languages'] = list(settings_dict['language_metadata'].keys())
            logger.info(f"Derived available_languages from language_metadata: {settings_dict['available_languages']}")

        logger.info("Public system settings retrieved successfully")
        return SystemSettingsResponse(settings=settings_dict)

    except Exception as e:
        logger.error(f"Failed to retrieve public settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve system settings"
        )
    finally:
        session.close()


@router.get(
    "/localization/{language_code}",
    response_model=LocalizationResponse,
    responses={
        200: {"model": LocalizationResponse, "description": "Localization strings"},
        400: {"model": ErrorResponse, "description": "Invalid language code"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_localization_strings(
    language_code: str,
    context: str = Query(None, description="Filter by context (optional)")
) -> LocalizationResponse:
    """
    Get localization strings for specified language
    
    Returns all UI strings in the requested language.
    Optionally filter by context (navigation, user_menu, appearance, etc.)
    """
    session = db_manager.session_local()
    try:
        # Validate language code format
        if not language_code or len(language_code) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid language code"
            )
        
        # Build query
        stmt = select(LocalizationString).where(
            LocalizationString.language_code == language_code
        )
        
        if context:
            stmt = stmt.where(LocalizationString.context == context)
        
        strings = session.execute(stmt).scalars().all()
        
        # Build response dictionary
        strings_dict = {
            string.string_key: string.string_value
            for string in strings
        }
        
        logger.info(f"Localization strings retrieved for language: {language_code}, context: {context}")
        return LocalizationResponse(
            language_code=language_code,
            context=context,
            strings=strings_dict
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve localization strings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve localization strings"
        )
    finally:
        session.close()


# User-specific settings endpoints (must be BEFORE /{setting_key} catch-all)

@router.get("/theme")
async def get_user_theme(current_user: User = Depends(get_current_active_user)) -> Dict[str, str]:
    """Get user's theme preference (light/dark)"""
    logger.info(f"[THEME DEBUG] === GET Theme Request ===")
    logger.info(f"[THEME DEBUG] User: {current_user.email} (ID: {current_user.id})")

    session = db_manager.session_local()
    try:
        stmt = select(UserSetting).where(
            UserSetting.user_id == current_user.id,
            UserSetting.setting_key == 'theme'
        )
        logger.info(f"[THEME DEBUG] Querying user_settings for theme...")
        setting = session.execute(stmt).scalar_one_or_none()

        if setting:
            logger.info(f"[THEME DEBUG] ✅ Found theme: '{setting.setting_value}'")
            return {"value": setting.setting_value}

        # Default to light theme
        logger.info(f"[THEME DEBUG] ⚠️  No theme setting in DB, returning default: 'light'")
        return {"value": "light"}

    except Exception as e:
        logger.error(f"[THEME DEBUG] ❌ Error getting theme: {e}")
        return {"value": "light"}
    finally:
        session.close()


@router.put("/theme")
async def set_user_theme(
    theme: ThemePreference,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Set user's theme preference (light/dark)"""
    logger.info(f"[THEME DEBUG] === PUT Theme Request ===")
    logger.info(f"[THEME DEBUG] User: {current_user.email} (ID: {current_user.id})")
    logger.info(f"[THEME DEBUG] Requested theme: '{theme.value}'")

    if theme.value not in ('light', 'dark'):
        logger.error(f"[THEME DEBUG] ❌ Invalid theme value: '{theme.value}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Theme must be 'light' or 'dark'"
        )

    session = db_manager.session_local()
    try:
        # Check if setting exists
        stmt = select(UserSetting).where(
            UserSetting.user_id == current_user.id,
            UserSetting.setting_key == 'theme'
        )
        logger.info(f"[THEME DEBUG] Checking if theme setting exists...")
        setting = session.execute(stmt).scalar_one_or_none()

        if setting:
            # Update existing
            logger.info(f"[THEME DEBUG] Found existing setting, updating from '{setting.setting_value}' to '{theme.value}'")
            setting.setting_value = theme.value
        else:
            # Create new
            logger.info(f"[THEME DEBUG] No existing setting, creating new with value '{theme.value}'")
            setting = UserSetting(
                user_id=current_user.id,
                setting_key='theme',
                setting_value=theme.value
            )
            session.add(setting)

        logger.info(f"[THEME DEBUG] Committing to database...")
        session.commit()
        logger.info(f"[THEME DEBUG] ✅✅✅ Theme saved successfully: '{theme.value}'")
        logger.info(f"[THEME DEBUG] Saved theme for user {current_user.email}: {theme.value}")
        return {"value": theme.value, "message": "Theme saved successfully"}

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save user theme: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save theme preference"
        )
    finally:
        session.close()


@router.get(
    "/cookie-consent",
    summary="Get Cookie Consent Configuration",
    description="Get GDPR cookie consent configuration with categories, translations, and cookie definitions (public endpoint)"
)
async def get_cookie_consent_config(language: str = Query(default="en", description="Language code (en, de, ru, etc.)")):
    """
    Get cookie consent configuration for GDPR compliance

    Returns:
    - Cookie categories (necessary, analytics, functionality, etc.)
    - Translations for the specified language
    - Cookie definitions with descriptions
    - UI configuration settings

    This is a public endpoint that doesn't require authentication.
    """
    session = db_manager.session_local()

    try:
        # Get active cookie categories
        categories = session.query(CookieCategory).filter(
            CookieCategory.is_active == True
        ).order_by(CookieCategory.sort_order).all()

        # Get UI settings from system_settings
        ui_settings_query = session.query(SystemSetting).filter(
            SystemSetting.category == 'cookie_consent',
            SystemSetting.is_public == True
        ).all()

        ui_settings = {
            setting.setting_key.replace('cookie_consent_', ''): (
                setting.setting_value if setting.data_type == 'string'
                else json.loads(setting.setting_value) if setting.data_type == 'json'
                else setting.setting_value == 'true' if setting.data_type == 'boolean'
                else int(setting.setting_value) if setting.data_type == 'integer'
                else setting.setting_value
            )
            for setting in ui_settings_query
        }

        # Build category configuration
        categories_config = []
        for cat in categories:
            # Get translation for this category in requested language (fallback to English)
            translation = next(
                (t for t in cat.translations if t.language_code == language),
                next((t for t in cat.translations if t.language_code == 'en'), None)
            )

            if not translation:
                continue

            # Get cookie definitions for this category
            cookies_data = []
            for cookie in cat.cookies:
                if not cookie.is_active:
                    continue

                cookie_translation = next(
                    (t for t in cookie.translations if t.language_code == language),
                    next((t for t in cookie.translations if t.language_code == 'en'), None)
                )

                if cookie_translation:
                    cookies_data.append({
                        "name": cookie.cookie_name,
                        "is_regex": cookie.is_regex,
                        "domain": cookie.domain,
                        "expiration": cookie.expiration,
                        "description": cookie_translation.description
                    })

            categories_config.append({
                "key": cat.category_key,
                "title": translation.title,
                "description": translation.description,
                "is_required": cat.is_required,
                "is_enabled_by_default": cat.is_enabled_by_default,
                "cookies": cookies_data
            })

        return {
            "categories": categories_config,
            "ui_settings": ui_settings,
            "language": language
        }

    except Exception as e:
        logger.error(f"Error fetching cookie consent config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch cookie consent configuration"
        )
    finally:
        session.close()


@router.get(
    "/{setting_key}",
    responses={
        200: {"description": "Setting value"},
        404: {"model": ErrorResponse, "description": "Setting not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_single_setting(setting_key: str) -> Dict[str, Any]:
    """
    Get a single system setting by key
    
    Returns the value of a specific system setting.
    Used by frontend components that need individual settings.
    """
    session = db_manager.session_local()
    try:
        stmt = select(SystemSetting).where(SystemSetting.setting_key == setting_key)
        setting = session.execute(stmt).scalar_one_or_none()
        
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{setting_key}' not found"
            )
        
        # Parse value based on data_type
        value = setting.setting_value
        if setting.data_type == 'json':
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        elif setting.data_type == 'boolean':
            value = value.lower() in ('true', '1', 'yes')
        elif setting.data_type == 'integer':
            try:
                value = int(value)
            except ValueError:
                pass
        
        logger.info(f"Setting retrieved: {setting_key}")
        return {
            "setting_key": setting_key,
            "value": value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve setting '{setting_key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve setting"
        )
    finally:
        session.close()


@router.get(
    "/localization",
    response_model=Dict[str, LocalizationResponse],
    responses={
        200: {"description": "All localization strings for all languages"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_all_localizations() -> Dict[str, LocalizationResponse]:
    """
    Get all localization strings for all supported languages
    
    Returns complete localization dictionary for all languages.
    Use this endpoint for initial app load to cache all translations.
    """
    session = db_manager.session_local()
    try:
        stmt = select(LocalizationString)
        all_strings = session.execute(stmt).scalars().all()
        
        # Group by language
        languages_dict = {}
        for string in all_strings:
            lang = string.language_code
            if lang not in languages_dict:
                languages_dict[lang] = {}
            languages_dict[lang][string.string_key] = string.string_value
        
        # Build response
        response = {
            lang: LocalizationResponse(
                language_code=lang,
                context=None,
                strings=strings
            )
            for lang, strings in languages_dict.items()
        }
        
        logger.info(f"All localization strings retrieved for {len(response)} languages")
        return response
        
    except Exception as e:
        logger.error(f"Failed to retrieve all localizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve localization strings"
        )
    finally:
        session.close()


@router.get("/tiers/public")
async def get_public_tier_plans():
    """
    Get public tier plans for pricing page

    Returns all active and public tier plans with pricing and limits.
    This endpoint is unauthenticated and used for the homepage/pricing page.
    """
    session = db_manager.session_local()
    try:
        from app.database.models import TierPlan, Currency

        result = session.execute(
            select(TierPlan).where(
                TierPlan.is_active == True,
                TierPlan.is_public == True
            ).order_by(TierPlan.sort_order)
        )
        tiers = result.scalars().all()

        # Get currency symbols mapping
        currencies_result = session.execute(
            select(Currency).where(Currency.is_active == True)
        )
        currencies = currencies_result.scalars().all()
        currency_map = {curr.code: curr.symbol for curr in currencies}

        tier_list = []
        for tier in tiers:
            # Get currency symbol from currencies table
            currency_symbol = currency_map.get(tier.currency, tier.currency)

            tier_list.append({
                'id': tier.id,
                'name': tier.name,
                'display_name': tier.display_name,
                'description': tier.description,
                'price_monthly_cents': tier.price_monthly_cents,
                'price_yearly_cents': tier.price_yearly_cents,
                'currency': tier.currency,
                'currency_symbol': currency_symbol,
                'max_monthly_upload_bytes': tier.max_monthly_upload_bytes,
                'max_file_size_bytes': tier.max_file_size_bytes,
                'max_pages_per_month': tier.max_pages_per_month,
                'max_translations_per_month': tier.max_translations_per_month,
                'max_api_calls_per_month': tier.max_api_calls_per_month,
                'max_team_members': tier.max_team_members,
                'max_batch_upload_size': tier.max_batch_upload_size,
                'bulk_operations_enabled': tier.bulk_operations_enabled,
                'email_to_process_enabled': tier.email_to_process_enabled,
                'folder_to_process_enabled': tier.folder_to_process_enabled,
                'multi_user_enabled': tier.multi_user_enabled,
                'api_access_enabled': tier.api_access_enabled,
                'priority_support': tier.priority_support,
                'custom_categories_limit': tier.custom_categories_limit
            })

        return {'tiers': tier_list}

    except Exception as e:
        logger.error(f"Failed to retrieve public tier plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve tier plans"
        )
    finally:
        session.close()

@router.get(
    "/currencies/available",
    summary="Get Available Currencies",
    description="Get currencies with exchange rates set (public endpoint for currency selector)"
)
async def get_available_currencies():
    """
    Get currencies available for selection

    Returns only currencies that have exchange_rate set.
    This prevents users from selecting unconfigured currencies.

    Used by currency selector in the frontend header.
    """
    session = db_manager.session_local()

    try:
        # Only return currencies with exchange rates configured
        currencies = session.query(Currency).filter(
            Currency.is_active == True,
            Currency.exchange_rate.isnot(None)
        ).order_by(Currency.sort_order).all()

        return {
            "currencies": [
                {
                    "code": c.code,
                    "symbol": c.symbol,
                    "name": c.name,
                    "decimal_places": c.decimal_places,
                    "exchange_rate": float(c.exchange_rate),
                    "is_default": c.is_default
                }
                for c in currencies
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching available currencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch available currencies"
        )
    finally:
        session.close()
