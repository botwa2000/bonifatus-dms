# backend/app/schemas/category_schemas.py
"""
Bonifatus DMS - Category Schemas
Pydantic models for category operations and management
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator


class CategoryBase(BaseModel):
    """Base category model with multilingual fields"""
    name_en: str = Field(..., min_length=1, max_length=100, description="English name")
    name_de: str = Field(..., min_length=1, max_length=100, description="German name")
    name_ru: str = Field(..., min_length=1, max_length=100, description="Russian name")
    description_en: Optional[str] = Field(None, max_length=500, description="English description")
    description_de: Optional[str] = Field(None, max_length=500, description="German description")
    description_ru: Optional[str] = Field(None, max_length=500, description="Russian description")
    color_hex: str = Field(..., pattern="^#[0-9A-Fa-f]{6}$", description="Category color")
    icon_name: str = Field(..., min_length=1, max_length=50, description="Icon identifier")
    sort_order: Optional[int] = Field(0, ge=0, description="Display order")
    is_active: Optional[bool] = Field(True, description="Category active status")


class CategoryCreate(CategoryBase):
    """Create new category request"""
    pass


class CategoryUpdate(BaseModel):
    """Update category request - all fields optional"""
    name_en: Optional[str] = Field(None, min_length=1, max_length=100)
    name_de: Optional[str] = Field(None, min_length=1, max_length=100)
    name_ru: Optional[str] = Field(None, min_length=1, max_length=100)
    description_en: Optional[str] = Field(None, max_length=500)
    description_de: Optional[str] = Field(None, max_length=500)
    description_ru: Optional[str] = Field(None, max_length=500)
    color_hex: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icon_name: Optional[str] = Field(None, min_length=1, max_length=50)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    """Category response with metadata"""
    id: str = Field(..., description="Category UUID")
    is_system: bool = Field(..., description="System category flag (informational only)")
    user_id: Optional[str] = Field(None, description="Owner user ID (null for system)")
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
        description="Delete all documents permanently (DANGEROUS)"
    )


class CategoryDeleteResponse(BaseModel):
    """Delete category response"""
    success: bool = Field(..., description="Deletion success status")
    message: str = Field(..., description="Operation message")
    documents_moved: int = Field(0, description="Number of documents moved")
    documents_deleted: int = Field(0, description="Number of documents deleted")
    move_to_category_name: Optional[str] = Field(None, description="Target category name")


class RestoreDefaultsResponse(BaseModel):
    """Restore default categories response"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Operation message")
    categories_created: List[str] = Field(..., description="Names of created categories")
    categories_skipped: List[str] = Field(..., description="Names of existing categories")


class CategoryWithDocumentsResponse(CategoryResponse):
    """Category with document count and sync status"""
    documents_count: int = Field(0, description="Number of documents")
    google_drive_folder_id: Optional[str] = Field(None, description="Google Drive folder ID")
    sync_status: str = Field("unknown", description="Sync status: synced, pending, error")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message")