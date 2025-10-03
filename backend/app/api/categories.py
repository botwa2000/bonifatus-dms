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
    ErrorResponse
)
from app.services.category_service import category_service
from app.middleware.auth_middleware import get_current_active_user, get_client_ip
from app.database.models import User

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
    List all categories accessible to user
    
    Returns both system categories and user's custom categories.
    All categories are fully editable and deletable.
    """
    try:
        categories = await category_service.list_categories(
            user_id=str(current_user.id),
            include_system=include_system,
            include_documents_count=include_documents_count
        )
        
        logger.info(f"Categories listed for user: {current_user.email}")
        return categories

    except Exception as e:
        logger.error(f"List categories error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve categories"
        )


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
    Create new category
    
    Creates a new user category and syncs to Google Drive.
    """
    try:
        ip_address = get_client_ip(request)
        
        category = await category_service.create_category(
            user_id=str(current_user.id),
            user_email=current_user.email,
            category_data=category_data,
            ip_address=ip_address
        )
        
        logger.info(f"Category created: {category.id} by user {current_user.email}")
        return category

    except Exception as e:
        logger.error(f"Create category error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create category"
        )


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
    
    Updates any category (system or user-created). No restrictions on system categories.
    """
    try:
        ip_address = get_client_ip(request)
        
        updated_category = await category_service.update_category(
            category_id=category_id,
            user_id=str(current_user.id),
            user_email=current_user.email,
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