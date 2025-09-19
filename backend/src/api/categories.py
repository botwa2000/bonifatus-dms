# backend/src/api/categories.py - Fixed API (No Initialization Calls)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from src.database import get_db
from src.services.auth_service import AuthService
from src.services.category_service import CategoryService

logger = logging.getLogger(__name__)
security = HTTPBearer()
router = APIRouter()

class CategoryCreate(BaseModel):
    name_en: str
    name_de: str
    description_en: Optional[str] = ""
    description_de: Optional[str] = ""
    color: Optional[str] = "#808080"
    icon: Optional[str] = "📁"
    keywords: Optional[str] = ""

class CategoryUpdate(BaseModel):
    name_en: Optional[str] = None
    name_de: Optional[str] = None
    description_en: Optional[str] = None
    description_de: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    keywords: Optional[str] = None

@router.get("/")
async def list_categories(
    include_system: bool = Query(True, description="Include system categories"),
    include_user: bool = Query(True, description="Include user categories"),
    language: str = Query("en", pattern="^(en|de)$", description="Language for category names"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """List available categories for the user"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        
        # Simply retrieve categories from database (no initialization)
        categories = await category_service.get_user_categories(
            user_id=user.id,
            include_system=include_system,
            include_user=include_user,
            language=language,
        )

        return {
            "categories": categories,
            "total": len(categories),
            "language": language
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List categories failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories",
        )

@router.post("/")
async def create_category(
    category_data: CategoryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Create user-defined category"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        category = await category_service.create_user_category(
            user_id=user.id,
            category_data=category_data.dict()
        )
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create category. You may have reached the limit of 50 user categories.",
            )

        return {
            "id": category.id,
            "name_en": category.name_en,
            "name_de": category.name_de,
            "color": category.color,
            "icon": category.icon,
            "message": "Category created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category",
        )

@router.get("/{category_id}")
async def get_category(
    category_id: int,
    language: str = Query("en", pattern="^(en|de)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Get specific category by ID"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        from src.database.models import Category
        category = db.query(Category).filter(Category.id == category_id).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        # Check access permissions
        if not category.is_system_category and category.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return {
            "id": category.id,
            "name": category.name_de if language == "de" else category.name_en,
            "name_en": category.name_en,
            "name_de": category.name_de,
            "description": category.description_de if language == "de" else category.description_en,
            "description_en": category.description_en,
            "description_de": category.description_de,
            "color": category.color,
            "icon": category.icon,
            "keywords": category.keywords.split(",") if category.keywords else [],
            "is_system_category": category.is_system_category,
            "created_at": category.created_at.isoformat(),
            "last_used_at": category.last_used_at.isoformat() if category.last_used_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category",
        )

@router.put("/{category_id}")
async def update_category(
    category_id: int,
    updates: CategoryUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Update user category (system categories cannot be updated)"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        category = await category_service.update_category(
            category_id, user.id, updates.dict(exclude_unset=True)
        )
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or cannot be updated",
            )

        return {
            "id": category.id,
            "message": "Category updated successfully",
            "updated_at": category.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category",
        )

@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Delete user category and reassign documents"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        success = await category_service.delete_category(category_id, user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or cannot be deleted",
            )

        return {"message": "Category deleted successfully. Documents have been reassigned."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category",
        )

@router.post("/suggest")
async def suggest_category(
    text: str = Query(..., min_length=10, description="Text content to analyze"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of suggestions"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Suggest categories based on document content"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        suggestions = await category_service.suggest_categories(text, user.id, limit)

        return {
            "suggestions": suggestions,
            "text_length": len(text),
            "total_suggestions": len(suggestions)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category suggestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate suggestions",
        )

@router.get("/statistics/usage")
async def get_category_statistics(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Get category usage statistics for user"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        statistics = await category_service.get_category_statistics(user.id)

        return statistics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get category statistics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )