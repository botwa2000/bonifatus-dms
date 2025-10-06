# backend/app/schemas/category_schemas.py
"""
Bonifatus DMS - Category Schemas
Dynamic multilingual category models
"""

from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, validator


class CategoryTranslationInput(BaseModel):
    """Translation input for create/update operations"""
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")


class CategoryBase(BaseModel):
    """Base category model with dynamic translations"""
    translations: Dict[str, CategoryTranslationInput] = Field(
        ..., 
        description="Translations keyed by language code (e.g., {'en': {...}, 'de': {...}})",
        example={
            "en": {"name": "Insurance", "description": "Insurance documents"},
            "de": {"name": "Versicherung", "description": "Versicherungsdokumente"}
        }
    )
    color_hex: str = Field(..., pattern="^#[0-9A-Fa-f]{6}$", description="Category color")
    icon_name: str = Field(..., min_length=1, max_length=50, description="Icon identifier")
    sort_order: Optional[int] = Field(0, ge=0, description="Display order")
    is_active: Optional[bool] = Field(True, description="Category active status")
    
    @validator('translations')
    def validate_translations(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one translation is required')
        return v


class CategoryCreate(CategoryBase):
    """Create new category - requires translations"""
    pass


class CategoryUpdate(BaseModel):
    """Update category - all fields optional"""
    translations: Optional[Dict[str, CategoryTranslationInput]] = Field(
        None,
        description="Updated translations (only provided languages will be updated)"
    )
    color_hex: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icon_name: Optional[str] = Field(None, min_length=1, max_length=50)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """Category response - returns only user's preferred language"""
    id: str = Field(..., description="Category UUID")
    reference_key: str = Field(..., description="Unique reference key")
    category_code: str = Field(..., description="3-character category code")
    name: str = Field(..., description="Category name in user's language")
    description: Optional[str] = Field(None, description="Category description in user's language")
    color_hex: str = Field(..., description="Category color")
    icon_name: str = Field(..., description="Icon identifier")
    is_system: bool = Field(..., description="System category flag")
    user_id: Optional[str] = Field(None, description="Owner user ID")
    sort_order: int = Field(..., description="Display order")
    is_active: bool = Field(..., description="Category active status")
    documents_count: Optional[int] = Field(0, description="Number of documents")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """List of categories response"""
    categories: List[CategoryResponse] = Field(..., description="List of categories")
    total_count: int = Field(..., description="Total number of categories")


class CategoryDeleteRequest(BaseModel):
    """Delete category request with document handling"""
    move_to_category_id: Optional[str] = Field(
        None, 
        description="Move documents to this category (default: 'Other')"
    )
    delete_documents: bool = Field(
        False, 
        description="Delete all documents in category (dangerous)"
    )


class CategoryDeleteResponse(BaseModel):
    """Delete category response"""
    deleted_category_id: str = Field(..., description="Deleted category UUID")
    documents_moved: int = Field(..., description="Number of documents moved")
    documents_deleted: int = Field(..., description="Number of documents deleted")
    message: str = Field(..., description="Success message")


class RestoreDefaultsResponse(BaseModel):
    """Restore default categories response"""
    created: List[str] = Field(..., description="List of created category names")
    skipped: List[str] = Field(..., description="List of already existing category names")
    message: str = Field(..., description="Summary message")


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message")