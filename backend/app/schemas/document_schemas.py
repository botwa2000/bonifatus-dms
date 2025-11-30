# backend/app/schemas/document_schemas.py
"""
Bonifatus DMS - Document Management Schemas
Pydantic models for document operations and processing
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class DocumentUploadResponse(BaseModel):
    """Response model for document upload"""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    google_drive_file_id: str = Field(..., description="Google Drive file ID")
    processing_status: str = Field(..., description="Processing status")
    web_view_link: Optional[str] = Field(None, description="Google Drive view link")
    created_at: datetime = Field(..., description="Upload timestamp")


class KeywordItem(BaseModel):
    """Keyword with relevance score"""
    keyword: str = Field(..., description="Keyword text")
    relevance: float = Field(default=1.0, description="Keyword relevance score")


class EntityItem(BaseModel):
    """Extracted entity information"""
    type: str = Field(..., description="Entity type (ORGANIZATION, PERSON, LOCATION, etc.)")
    value: str = Field(..., description="Entity value/text")
    confidence: float = Field(..., description="Extraction confidence score")
    method: str = Field(..., description="Extraction method (spacy_ner, pattern_email, etc.)")


class CategoryInfo(BaseModel):
    """Category assignment information"""
    id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    is_primary: bool = Field(default=False, description="Is primary category")


class DocumentResponse(BaseModel):
    """Response model for document information"""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    google_drive_file_id: str = Field(..., description="Google Drive file ID")
    processing_status: str = Field(..., description="Processing status")
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    keywords: Optional[List[KeywordItem]] = Field(None, description="Extracted keywords")
    entities: Optional[List[EntityItem]] = Field(None, description="Extracted entities (people, organizations, locations, etc.)")
    confidence_score: Optional[int] = Field(None, description="AI confidence score")
    primary_language: Optional[str] = Field(None, description="Primary detected language")
    category_id: Optional[str] = Field(None, description="Assigned category ID (primary, backward compat)")
    category_name: Optional[str] = Field(None, description="Category name (primary, backward compat)")
    categories: Optional[List[CategoryInfo]] = Field(None, description="All assigned categories")
    web_view_link: Optional[str] = Field(None, description="Google Drive view link")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class DocumentUpdateRequest(BaseModel):
    """Request model for updating document metadata"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Document title")
    description: Optional[str] = Field(None, max_length=1000, description="Document description")
    category_id: Optional[str] = Field(None, description="Primary category ID (backward compat)")
    category_ids: Optional[List[str]] = Field(None, min_items=1, description="All category IDs (first is primary)")
    keywords: Optional[List[str]] = Field(None, description="Document keywords")

    @validator('title')
    def validate_title(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError('Title cannot be empty')
        return v.strip() if v else v


class DocumentListResponse(BaseModel):
    """Response model for document listing"""
    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total_count: int = Field(..., description="Total number of documents")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of documents per page")
    total_pages: int = Field(..., description="Total number of pages")


class DocumentSearchRequest(BaseModel):
    """Request model for document search"""
    query: Optional[str] = Field(None, min_length=1, max_length=500, description="Search query")
    category_id: Optional[str] = Field(None, description="Filter by category")
    language: Optional[str] = Field(None, description="Filter by language")
    processing_status: Optional[str] = Field(None, description="Filter by processing status")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    page: Optional[int] = Field(None, ge=1, description="Page number")
    page_size: Optional[int] = Field(None, ge=1, description="Page size")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(None, description="Sort order")


class DocumentProcessingStatus(BaseModel):
    """Document processing status information"""
    document_id: str = Field(..., description="Document ID")
    processing_status: str = Field(..., description="Current processing status")
    progress_percentage: Optional[int] = Field(None, ge=0, le=100, description="Processing progress")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


class DocumentLanguageInfo(BaseModel):
    """Document language detection information"""
    language_code: str = Field(..., description="ISO 639-1 language code")
    confidence_score: int = Field(..., ge=0, le=100, description="Detection confidence")
    is_primary: bool = Field(..., description="Is primary language")
    extracted_text: Optional[str] = Field(None, description="Language-specific extracted text")
    keywords: Optional[List[str]] = Field(None, description="Language-specific keywords")


class DocumentAnalysisResponse(BaseModel):
    """Response model for document analysis results"""
    document_id: str = Field(..., description="Document ID")
    languages: List[DocumentLanguageInfo] = Field(..., description="Detected languages")
    suggested_category_id: Optional[str] = Field(None, description="AI suggested category ID")
    suggested_category_name: Optional[str] = Field(None, description="AI suggested category name")
    ai_confidence: Optional[int] = Field(None, ge=0, le=100, description="AI categorization confidence")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")


class DocumentStorageInfo(BaseModel):
    """Document storage and quota information"""
    total_documents: int = Field(..., description="Total documents count")
    total_storage_bytes: int = Field(..., description="Total storage used in bytes")
    total_storage_mb: float = Field(..., description="Total storage used in MB")
    storage_limit_mb: int = Field(..., description="Storage limit in MB")
    storage_usage_percentage: float = Field(..., ge=0, le=100, description="Storage usage percentage")
    remaining_storage_mb: float = Field(..., description="Remaining storage in MB")


class BatchOperationRequest(BaseModel):
    """Request model for batch operations on documents"""
    document_ids: List[str] = Field(..., min_items=1, description="Document IDs")
    operation: str = Field(..., description="Batch operation type")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")


class BatchOperationResponse(BaseModel):
    """Response model for batch operations"""
    operation: str = Field(..., description="Operation type")
    total_requested: int = Field(..., description="Total documents requested")
    successful: int = Field(..., description="Successfully processed documents")
    failed: int = Field(..., description="Failed documents")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="Error details")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")


class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""
    category_ids: List[str] = Field(..., min_items=1, description="Category IDs (first is primary)")
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Document title")
    description: Optional[str] = Field(None, max_length=1000, description="Document description")


class DocumentUploadResponse(BaseModel):
    """Response model for document upload"""
    id: str = Field(..., description="Document UUID")
    title: str = Field(..., description="Document title")
    filename: str = Field(..., description="Standardized filename")
    original_filename: str = Field(..., description="Original uploaded filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    category_ids: List[str] = Field(..., description="Assigned category IDs")
    category_names: List[str] = Field(..., description="Category names")
    google_drive_file_id: str = Field(..., description="Google Drive file ID")
    web_view_link: Optional[str] = Field(None, description="Google Drive view link")
    processing_status: str = Field(..., description="Processing status")
    created_at: datetime = Field(..., description="Upload timestamp")


class DocumentCategoriesUpdateRequest(BaseModel):
    """Request model for updating document categories"""
    category_ids: List[str] = Field(..., min_items=1, description="New category IDs")
    primary_category_id: Optional[str] = Field(None, description="Primary category ID")