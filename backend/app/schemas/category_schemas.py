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


# Keyword Management Schemas

class KeywordResponse(BaseModel):
    """Keyword response model"""
    id: str = Field(..., description="Keyword UUID")
    keyword: str = Field(..., description="Keyword text")
    language_code: str = Field(..., description="Language code (e.g., 'en', 'de', 'ru')")
    weight: float = Field(..., description="Keyword weight (0.1-10.0)")
    match_count: int = Field(..., description="Number of times keyword helped classify documents")
    last_matched_at: Optional[str] = Field(None, description="Last match timestamp (ISO format)")
    is_system_default: bool = Field(..., description="System default keyword flag")
    created_at: Optional[str] = Field(None, description="Creation timestamp (ISO format)")

    class Config:
        from_attributes = True


class KeywordListResponse(BaseModel):
    """List of keywords response"""
    keywords: List[KeywordResponse] = Field(..., description="List of keywords")


class KeywordCreateRequest(BaseModel):
    """Create new keyword request"""
    keyword: str = Field(..., min_length=2, max_length=200, description="Keyword text")
    language_code: str = Field(..., pattern="^[a-z]{2}$", description="Language code (e.g., 'en', 'de', 'ru')")
    weight: float = Field(1.0, ge=0.1, le=10.0, description="Keyword weight (default: 1.0)")


class KeywordUpdateRequest(BaseModel):
    """Update keyword weight request"""
    weight: float = Field(..., ge=0.1, le=10.0, description="New keyword weight")


class KeywordOverlapCategory(BaseModel):
    """Category information in overlap detection"""
    category_id: str = Field(..., description="Category UUID")
    reference_key: str = Field(..., description="Category reference key")
    weight: float = Field(..., description="Keyword weight in this category")
    match_count: int = Field(..., description="Match count in this category")
    is_system_default: bool = Field(..., description="System default flag")


class KeywordOverlap(BaseModel):
    """Keyword overlap detection result"""
    keyword: str = Field(..., description="Overlapping keyword")
    categories: List[KeywordOverlapCategory] = Field(..., description="Categories using this keyword")
    severity: str = Field(..., description="Overlap severity: 'low', 'medium', 'high'")
    category_count: int = Field(..., description="Number of categories using this keyword")


class KeywordOverlapResponse(BaseModel):
    """Keyword overlaps response"""
    overlaps: List[KeywordOverlap] = Field(..., description="List of keyword overlaps")
    total_overlaps: int = Field(..., description="Total number of overlapping keywords")