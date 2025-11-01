# backend/app/api/categories.py
"""
Bonifatus DMS - Categories API Endpoints
REST API for category management with full edit/delete capabilities
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.schemas.category_schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse,
    CategoryDeleteRequest, CategoryDeleteResponse, RestoreDefaultsResponse,
    KeywordResponse, KeywordListResponse, KeywordCreateRequest,
    KeywordUpdateRequest, KeywordOverlapResponse,
    ErrorResponse
)
from app.services.category_service import category_service
from app.services.keyword_management_service import keyword_management_service
from app.middleware.auth_middleware import get_current_active_user, get_client_ip
from app.database.models import User, UserSetting
from sqlalchemy import select
from app.database.connection import db_manager

async def get_user_language(user: User, session) -> str:
    """Get user's preferred interface language from settings"""
    try:
        user_setting = session.execute(
            select(UserSetting).where(
                UserSetting.user_id == user.id,
                UserSetting.setting_key == 'language'
            )
        ).scalar_one_or_none()
        
        if user_setting:
            return user_setting.setting_value
        
        # Default to English if not set
        return 'en'
    except Exception as e:
        logger.warning(f"Failed to get user language, defaulting to 'en': {e}")
        return 'en'

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

@router.get(
    "",
    response_model=CategoryListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_categories(
    include_system: bool = True,
    include_documents_count: bool = True,
    current_user: User = Depends(get_current_active_user)
) -> CategoryListResponse:
    """
    List all categories in user's preferred language
    
    Returns categories with translations in user's interface language only.
    Falls back to English if user's language not available.
    """
    session = db_manager.session_local()
    try:
        user_language = await get_user_language(current_user, session)
        
        # DEBUG LOGGING
        logger.info(f"Listing categories for user: {current_user.email}")
        logger.info(f"Detected user language: {user_language}")

        categories = await category_service.list_categories(
            user_id=str(current_user.id),
            user_language=user_language,
            include_system=include_system,
            include_documents_count=include_documents_count
        )
        
        logger.info(f"Categories listed for user: {current_user.email} (language: {user_language})")
        return categories

    except Exception as e:
        logger.error(f"List categories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve categories"
        )
    finally:
        session.close()


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        400: {"model": ErrorResponse, "description": "Invalid category data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def create_category(
    request: Request,
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_user)
) -> CategoryResponse:
    """
    Create new category with translations
    
    Accepts translations for multiple languages.
    At least one translation is required.
    """
    session = db_manager.session_local()
    try:
        ip_address = get_client_ip(request)
        user_language = await get_user_language(current_user, session)
        
        # DEBUG LOGGING
        logger.info(f"Creating category for user: {current_user.email}")
        logger.info(f"User language: {user_language}")
        logger.info(f"Category data: {category_data.dict()}")

        category = await category_service.create_category(
            user_id=str(current_user.id),
            user_email=current_user.email,
            user_language=user_language,
            category_data=category_data,
            ip_address=ip_address
        )
        
        logger.info(f"Category created: {category.id} by user {current_user.email}")
        return category

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Create category error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create category"
        )
    finally:
        session.close()


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Category not found"},
        400: {"model": ErrorResponse, "description": "Invalid category data"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_category(
    category_id: str,
    request: Request,
    category_data: CategoryUpdate,
    current_user: User = Depends(get_current_active_user)
) -> CategoryResponse:
    """
    Update category
    
    Updates category and/or translations.
    Only provided translations will be updated/added.
    """
    session = db_manager.session_local()
    try:
        ip_address = get_client_ip(request)
        user_language = await get_user_language(current_user, session)
        
        updated_category = await category_service.update_category(
            category_id=category_id,
            user_id=str(current_user.id),
            user_email=current_user.email,
            user_language=user_language,
            category_data=category_data,
            ip_address=ip_address
        )
        
        if not updated_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        logger.info(f"Category updated: {category_id} by user {current_user.email}")
        return updated_category

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update category error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update category"
        )
    finally:
        session.close()


@router.delete(
    "/{category_id}",
    response_model=CategoryDeleteResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Category not found"},
        400: {"model": ErrorResponse, "description": "Invalid delete request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_category(
    category_id: str,
    request: Request,
    delete_request: CategoryDeleteRequest = None,
    current_user: User = Depends(get_current_active_user)
) -> CategoryDeleteResponse:
    """
    Delete category
    
    Deletes any category (system or user-created). Documents can be moved to another
    category or deleted permanently.
    """
    try:
        ip_address = get_client_ip(request)
        
        if delete_request is None:
            delete_request = CategoryDeleteRequest()
        
        result = await category_service.delete_category(
            category_id=category_id,
            user_id=str(current_user.id),
            user_email=current_user.email,
            delete_request=delete_request,
            ip_address=ip_address
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        logger.info(f"Category deleted: {category_id} by user {current_user.email}")
        return result

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete category error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete category"
        )


@router.post(
    "/restore-defaults",
    response_model=RestoreDefaultsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def restore_default_categories(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> RestoreDefaultsResponse:
    """
    Restore default system categories
    
    Recreates the 5 default categories (Insurance, Legal, Real Estate, Banking, Other).
    Only creates missing categories - existing categories are not affected.
    """
    try:
        ip_address = get_client_ip(request)
        
        result = await category_service.restore_default_categories(
            user_id=str(current_user.id),
            ip_address=ip_address
        )
        
        logger.info(f"Default categories restored by user: {current_user.email}")
        return result

    except Exception as e:
        logger.error(f"Restore defaults error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to restore default categories"
        )


@router.get(
    "/{category_id}/documents-count",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Category not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_category_documents_count(
    category_id: str,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Get document count for a category
    
    Returns the number of documents in the specified category for the current user.
    """
    try:
        count = await category_service.get_category_documents_count(
            category_id=category_id,
            user_id=str(current_user.id)
        )
        
        return {
            "category_id": category_id,
            "documents_count": count
        }

    except Exception as e:
        logger.error(f"Get documents count error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve document count"
        )


# ==================== KEYWORD MANAGEMENT ENDPOINTS ====================

@router.get(
    "/{category_id}/keywords",
    response_model=KeywordListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Category not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_category_keywords(
    category_id: str,
    language_code: str = None,
    current_user: User = Depends(get_current_active_user)
) -> KeywordListResponse:
    """
    Get all keywords for a category, optionally filtered by language

    If language_code is not specified, returns keywords in ALL languages.
    This allows the UI to display multi-language keywords properly.

    Returns list of keywords with weights, match statistics, and system flag.
    """
    try:
        session = db_manager.session_local()

        keywords = keyword_management_service.list_keywords(
            category_id=category_id,
            language_code=language_code,
            session=session
        )

        session.close()

        return KeywordListResponse(keywords=keywords)

    except Exception as e:
        logger.error(f"List keywords error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/{category_id}/keywords",
    response_model=KeywordResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Category not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def add_category_keyword(
    category_id: str,
    request: KeywordCreateRequest,
    current_user: User = Depends(get_current_active_user)
) -> KeywordResponse:
    """
    Add new keyword to a category

    Creates a new keyword with specified weight for document classification.
    Duplicate keywords (case-insensitive) are rejected.
    """
    try:
        session = db_manager.session_local()

        keyword = keyword_management_service.add_keyword(
            category_id=category_id,
            keyword=request.keyword,
            language_code=request.language_code,
            weight=request.weight,
            user_id=str(current_user.id),
            session=session
        )

        session.close()

        return KeywordResponse(**keyword)

    except ValueError as e:
        logger.warning(f"Keyword validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"Keyword permission denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Add keyword error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to add keyword"
        )


@router.put(
    "/{category_id}/keywords/{keyword_id}",
    response_model=KeywordResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Keyword not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_category_keyword(
    category_id: str,
    keyword_id: str,
    request: KeywordUpdateRequest,
    current_user: User = Depends(get_current_active_user)
) -> KeywordResponse:
    """
    Update keyword weight

    Adjusts the weight of a keyword to increase or decrease its importance
    in document classification. Both system and custom keywords can be adjusted.
    """
    try:
        session = db_manager.session_local()

        keyword = keyword_management_service.update_keyword_weight(
            keyword_id=keyword_id,
            weight=request.weight,
            user_id=str(current_user.id),
            session=session
        )

        session.close()

        return KeywordResponse(**keyword)

    except ValueError as e:
        logger.warning(f"Keyword update validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"Keyword update permission denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Update keyword error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update keyword"
        )


@router.delete(
    "/{category_id}/keywords/{keyword_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse, "description": "Cannot delete system keyword"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Keyword not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_category_keyword(
    category_id: str,
    keyword_id: str,
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    Delete a custom keyword

    Removes a user-created keyword from the category. System default keywords
    are protected and cannot be deleted.
    """
    try:
        session = db_manager.session_local()

        keyword_management_service.delete_keyword(
            keyword_id=keyword_id,
            user_id=str(current_user.id),
            session=session
        )

        session.close()

    except ValueError as e:
        logger.warning(f"Keyword delete validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"Keyword delete permission denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Delete keyword error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete keyword"
        )


@router.get(
    "/keywords/overlaps",
    response_model=KeywordOverlapResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_keyword_overlaps(
    language_code: str = 'en',
    current_user: User = Depends(get_current_active_user)
) -> KeywordOverlapResponse:
    """
    Detect keyword overlaps across user's categories

    Returns all keywords that appear in multiple categories with severity
    assessment (low/medium/high) based on weight differences.

    - High severity: Nearly identical weights (ambiguous classification)
    - Medium severity: Similar weights (potential confusion)
    - Low severity: Very different weights (clear winner)
    """
    try:
        session = db_manager.session_local()

        overlaps = keyword_management_service.detect_overlaps(
            user_id=str(current_user.id),
            language_code=language_code,
            session=session
        )

        session.close()

        return KeywordOverlapResponse(
            overlaps=overlaps,
            total_overlaps=len(overlaps)
        )

    except Exception as e:
        logger.error(f"Detect overlaps error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to detect keyword overlaps"
        )