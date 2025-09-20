# backend/src/api/categories.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from src.database import get_db
from src.database.models import Category
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
    keywords: Optional[List[str]] = []


class CategoryUpdate(BaseModel):
    name_en: Optional[str] = None
    name_de: Optional[str] = None
    description_en: Optional[str] = None
    description_de: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    keywords: Optional[List[str]] = None


@router.get("/")
def list_categories(
    include_system: bool = Query(True, description="Include system categories"),
    include_user: bool = Query(True, description="Include user categories"),
    language: str = Query(
        "en", pattern="^(en|de)$", description="Language for category names"
    ),
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
        
        if not category_service.db.query(Category).filter(Category.user_id.is_(None)).first():
            category_service.initialize_default_categories()

        categories = category_service.get_user_categories(
            user_id=user.id,
            include_system=include_system,
            include_user=include_user,
            language=language,
        )

        return {
            "categories": categories,
            "total": len(categories),
            "language": language,
            "filters": {
                "include_system": include_system,
                "include_user": include_user,
            },
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
def create_category(
    category_data: CategoryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Create new user category"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        
        category = category_service.create_user_category(
            user_id=user.id, category_data=category_data.model_dump()
        )

        return {
            "category": category,
            "message": "Category created successfully",
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
def get_category(
    category_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Get category details"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        from src.database.models import Category
        category = (
            db.query(Category)
            .filter(
                Category.id == category_id,
                (Category.user_id == user.id) | (Category.user_id.is_(None))
            )
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        category_service = CategoryService(db)
        document_count = category_service._get_category_document_count(category_id, user.id)

        return {
            "id": category.id,
            "name_en": category.name_en,
            "name_de": category.name_de,
            "description_en": category.description_en,
            "description_de": category.description_de,
            "color": category.color,
            "icon": category.icon,
            "keywords": category.keywords,
            "is_system": category.user_id is None,
            "document_count": document_count,
            "created_at": category.created_at.isoformat(),
            "updated_at": category.updated_at.isoformat() if category.updated_at else None,
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
def update_category(
    category_id: int,
    updates: CategoryUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Update user category"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
        
        success = category_service.update_category(category_id, user.id, update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or not owned by user",
            )

        return {"message": "Category updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category",
        )


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Delete user category"""
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        category_service = CategoryService(db)
        result = category_service.delete_category(category_id, user.id)
        
        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"],
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"],
                )

        return {
            "message": result["message"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category",
        )


@router.post("/suggest")
def suggest_category(
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
        suggestions = category_service.suggest_categories(text, user.id, limit)

        return {
            "suggestions": suggestions,
            "text_length": len(text),
            "total_suggestions": len(suggestions),
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
def get_category_statistics(
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
        statistics = category_service.get_category_statistics(user.id)

        return statistics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get category statistics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )