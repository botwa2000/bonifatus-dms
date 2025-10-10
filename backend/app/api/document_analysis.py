# backend/app/api/document_analysis.py
"""
Document analysis API endpoints.
Handles document analysis before final storage.
"""

import logging
import uuid
import tempfile
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.services.document_analysis_service import document_analysis_service
from app.middleware.auth_middleware import get_current_user
from app.services.category_service import category_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/document-analysis", tags=["document_analysis"])


# Allowed file types and max size
ALLOWED_MIME_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/jpg',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain'
]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Temporary file storage (in-memory for now)
# TODO: Use Redis or disk-based temp storage in production
temp_storage = {}


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """
    Analyze uploaded document without storing it permanently.
    Returns extracted text, keywords, and suggested category.
    
    This is step 1 of the upload process - user will review and confirm.
    """
    try:
        # Validate file type
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not supported. Allowed types: PDF, Images, Word, Excel, Text"
            )
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size {file_size} exceeds maximum of {MAX_FILE_SIZE} bytes (100MB)"
            )
        
        # Get user's categories
        categories_response = await category_service.list_categories(
            user_id=str(current_user.id),
            user_language='en',
            include_system=True,
            include_documents_count=False
        )
        
        user_categories = categories_response.categories
        
        if not user_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No categories found. Please create categories first."
            )
        
        # Convert categories to dict format for analysis
        categories_list = [
            {
                'id': cat.id,
                'reference_key': cat.reference_key,
                'name': cat.name
            }
            for cat in user_categories
        ]
        
        # Analyze document
        analysis_result = await document_analysis_service.analyze_document(
            file_content=file_content,
            file_name=file.filename,
            mime_type=file.content_type,
            user_categories=categories_list
        )
        
        # Generate temporary ID for this upload
        temp_id = str(uuid.uuid4())
        
        # Store file temporarily (expires in 24 hours)
        temp_storage[temp_id] = {
            'file_content': file_content,
            'file_name': file.filename,
            'mime_type': file.content_type,
            'user_id': str(current_user.id),
            'expires_at': datetime.utcnow() + timedelta(hours=24),
            'analysis_result': analysis_result
        }
        
        # Clean up expired temp files
        _cleanup_expired_temp_files()
        
        logger.info(f"Document analyzed successfully: {file.filename} (temp_id: {temp_id})")
        
        return {
            'temp_id': temp_id,
            'analysis': analysis_result,
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document analysis failed: {str(e)}"
        )


@router.get("/analyze/{temp_id}")
async def get_analysis_result(
    temp_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve analysis result for a temporary upload.
    Used if user navigates away and comes back to review page.
    """
    try:
        # Check if temp file exists
        if temp_id not in temp_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found or expired"
            )
        
        temp_data = temp_storage[temp_id]
        
        # Verify ownership
        if temp_data['user_id'] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this analysis"
            )
        
        # Check if expired
        if datetime.utcnow() > temp_data['expires_at']:
            del temp_storage[temp_id]
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Analysis result has expired"
            )
        
        return {
            'temp_id': temp_id,
            'analysis': temp_data['analysis_result'],
            'file_name': temp_data['file_name'],
            'expires_at': temp_data['expires_at'].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis result"
        )


@router.delete("/analyze/{temp_id}")
async def cancel_upload(
    temp_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel upload and remove temporary file.
    Called when user cancels the upload process.
    """
    try:
        if temp_id not in temp_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Temporary file not found"
            )
        
        temp_data = temp_storage[temp_id]
        
        # Verify ownership
        if temp_data['user_id'] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this upload"
            )
        
        # Remove from temporary storage
        del temp_storage[temp_id]
        
        logger.info(f"Upload cancelled: {temp_id}")
        
        return {
            'success': True,
            'message': 'Upload cancelled successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel upload"
        )


def _cleanup_expired_temp_files():
    """Remove expired temporary files from storage"""
    try:
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, data in temp_storage.items()
            if current_time > data['expires_at']
        ]
        
        for key in expired_keys:
            del temp_storage[key]
            logger.info(f"Removed expired temp file: {key}")
            
    except Exception as e:
        logger.error(f"Temp file cleanup failed: {e}")


@router.post("/confirm-upload")
async def confirm_upload(
    temp_id: str,
    title: str,
    description: Optional[str] = None,
    category_ids: list[str] = [],
    confirmed_keywords: list[str] = [],
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """
    Confirm upload after user review and store document permanently.
    This is step 2 of the upload process - final storage.
    
    TODO: Implement actual Google Drive storage and database insertion
    """
    try:
        # Check if temp file exists
        if temp_id not in temp_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Temporary file not found or expired"
            )
        
        temp_data = temp_storage[temp_id]
        
        # Verify ownership
        if temp_data['user_id'] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to confirm this upload"
            )
        
        # Validate category IDs
        if not category_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one category must be selected"
            )
        
        # TODO: Implement actual document storage
        # 1. Upload to Google Drive
        # 2. Store metadata in database
        # 3. Store keywords
        # 4. Create audit log entry
        
        # Remove from temporary storage
        del temp_storage[temp_id]
        
        logger.info(f"Document upload confirmed: {title} by user {current_user.id}")
        
        # Return mock response for now
        return {
            'success': True,
            'message': 'Document uploaded successfully',
            'document_id': str(uuid.uuid4()),  # Mock ID
            'title': title,
            'categories': category_ids,
            'keywords': confirmed_keywords
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm upload: {str(e)}"
        )