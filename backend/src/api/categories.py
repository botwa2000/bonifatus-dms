# backend/src/api/categories.py
"""
Bonifatus DMS - Categories API
Document category management with multilingual support
System and user-defined categories with intelligent suggestions
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from src.database import get_db, Category, Document
from src.services.auth_service import AuthService
from src.services.category_service import CategoryService
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()

router = APIRouter()


@router.get("/")
async def list_categories(
    include_system: bool = Query(True, description="Include system categories"),
    include_user: bool = Query(True, description="Include user categories"), 
    language: str = Query("en", regex="^(en|de)$", description="Language for category names"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    List available categories for the user
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        category_service = CategoryService(db)
        categories = await category_service.get_user_categories(
            user_id=user.id,
            include_system=include_system,
            include_user=include_user,
            language=language
        )
        
        return {
            "categories": [
                {
                    "id": cat.id,
                    "name": cat.name_de if language == "de" else cat.name_en,
                    "description": cat.description_de if language == "de" else cat.description_en,
                    "color": cat.color,
                    "icon": cat.icon,
                    "is_system_category": cat.is_system_category,
                    "document_count": cat.document_count,
                    "keywords": cat.keywords.split(",") if cat.keywords else [],
                    "last_used_at": cat.last_used_at.isoformat() if cat.last_used_at else None,
                    "created_at": cat.created_at.isoformat()
                }
                for cat in categories
            ],
            "total": len(categories),
            "language": language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List categories failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )


@router.post("/")
async def create_category(
    name_en: str,
    name_de: str,
    description_en: Optional[str] = None,
    description_de: Optional[str] = None,
    color: str = "#6B7280",
    icon: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Create new user-defined category
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        category_service = CategoryService(db)
        
        # Validate category limits
        user_categories_count = db.query(Category).filter(
            Category.user_id == user.id,
            Category.is_system_category == False
        ).count()
        
        max_categories = 10 if user.tier.value == "free" else 50
        if user_categories_count >= max_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_categories} custom categories allowed for your tier"
            )
        
        # Check for duplicate names
        existing = db.query(Category).filter(
            Category.user_id == user.id,
            ((Category.name_en == name_en) | (Category.name_de == name_de))
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name already exists"
            )
        
        # Validate color format
        if not color.startswith("#") or len(color) != 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Color must be a valid hex color (e.g., #6B7280)"
            )
        
        # Create category
        category_data = {
            "user_id": user.id,
            "name_en": name_en,
            "name_de": name_de,
            "description_en": description_en,
            "description_de": description_de,
            "color": color,
            "icon": icon,
            "keywords": ",".join(keywords) if keywords else None,
            "is_system_category": False
        }
        
        category = await category_service.create_category(category_data)
        
        return {
            "id": category.id,
            "name_en": category.name_en,
            "name_de": category.name_de,
            "color": category.color,
            "message": "Category created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


@router.get("/{category_id}")
async def get_category(
    category_id: int,
    language: str = Query("en", regex="^(en|de)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get detailed category information
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        category = db.query(Category).filter(
            Category.id == category_id,
            ((Category.user_id == user.id) | (Category.is_system_category == True))
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Get recent documents in this category
        recent_documents = db.query(Document).filter(
            Document.category_id == category.id,
            Document.user_id == user.id
        ).order_by(Document.created_at.desc()).limit(5).all()
        
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
            "is_system_category": category.is_system_category,
            "keywords": category.keywords.split(",") if category.keywords else [],
            "document_count": category.document_count,
            "last_used_at": category.last_used_at.isoformat() if category.last_used_at else None,
            "created_at": category.created_at.isoformat(),
            "updated_at": category.updated_at.isoformat(),
            "recent_documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "title": doc.title,
                    "created_at": doc.created_at.isoformat()
                }
                for doc in recent_documents
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category"
        )


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    name_en: Optional[str] = None,
    name_de: Optional[str] = None,
    description_en: Optional[str] = None,
    description_de: Optional[str] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Update user-defined category
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.user_id == user.id,
            Category.is_system_category == False
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or cannot be modified"
            )
        
        # Validate color format if provided
        if color and (not color.startswith("#") or len(color) != 7):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Color must be a valid hex color (e.g., #6B7280)"
            )
        
        # Update fields
        if name_en is not None:
            # Check for duplicates
            existing = db.query(Category).filter(
                Category.user_id == user.id,
                Category.name_en == name_en,
                Category.id != category_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="English name already exists"
                )
            category.name_en = name_en
            
        if name_de is not None:
            # Check for duplicates
            existing = db.query(Category).filter(
                Category.user_id == user.id,
                Category.name_de == name_de,
                Category.id != category_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="German name already exists"
                )
            category.name_de = name_de
            
        if description_en is not None:
            category.description_en = description_en
        if description_de is not None:
            category.description_de = description_de
        if color is not None:
            category.color = color
        if icon is not None:
            category.icon = icon
        if keywords is not None:
            category.keywords = ",".join(keywords) if keywords else None
        
        category.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Category updated successfully", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    move_documents_to: Optional[int] = Query(None, description="Category ID to move documents to"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Delete user-defined category
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.user_id == user.id,
            Category.is_system_category == False
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or cannot be deleted"
            )
        
        # Check if category has documents
        document_count = db.query(Document).filter(
            Document.category_id == category_id,
            Document.user_id == user.id
        ).count()
        
        if document_count > 0:
            if move_documents_to:
                # Validate destination category
                dest_category = db.query(Category).filter(
                    Category.id == move_documents_to,
                    ((Category.user_id == user.id) | (Category.is_system_category == True))
                ).first()
                
                if not dest_category:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid destination category"
                    )
                
                # Move documents to new category
                db.query(Document).filter(
                    Document.category_id == category_id,
                    Document.user_id == user.id
                ).update({"category_id": move_documents_to})
                
                # Update document counts
                dest_category.document_count += document_count
                
            else:
                # Set documents to no category
                db.query(Document).filter(
                    Document.category_id == category_id,
                    Document.user_id == user.id
                ).update({"category_id": None})
        
        # Delete category
        db.delete(category)
        db.commit()
        
        return {
            "message": "Category deleted successfully",
            "success": True,
            "documents_moved": document_count if move_documents_to else 0,
            "documents_uncategorized": document_count if not move_documents_to else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete category failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )


@router.get("/{category_id}/documents")
async def list_category_documents(
    category_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|filename|view_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    List documents in a specific category
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        category = db.query(Category).filter(
            Category.id == category_id,
            ((Category.user_id == user.id) | (Category.is_system_category == True))
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Build query
        query = db.query(Document).filter(
            Document.category_id == category_id,
            Document.user_id == user.id
        )
        
        # Apply sorting
        sort_column = getattr(Document, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        documents = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "title": doc.title,
                    "file_size_bytes": doc.file_size_bytes,
                    "mime_type": doc.mime_type,
                    "status": doc.status.value,
                    "is_favorite": doc.is_favorite,
                    "view_count": doc.view_count,
                    "created_at": doc.created_at.isoformat(),
                    "last_viewed_at": doc.last_viewed_at.isoformat() if doc.last_viewed_at else None
                }
                for doc in documents
            ],
            "category": {
                "id": category.id,
                "name_en": category.name_en,
                "name_de": category.name_de,
                "color": category.color
            },
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List category documents failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category documents"
        )


@router.post("/suggest")
async def suggest_category(
    text: str,
    filename: Optional[str] = None,
    language: str = Query("en", regex="^(en|de)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered category suggestions for document content
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        category_service = CategoryService(db)
        suggestions = await category_service.suggest_categories(
            user_id=user.id,
            text=text,
            filename=filename,
            language=language
        )
        
        return {
            "suggestions": suggestions,
            "language": language,
            "text_length": len(text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category suggestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate category suggestions"
        )