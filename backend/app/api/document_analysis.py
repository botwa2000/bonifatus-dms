# backend/app/api/document_analysis.py
"""
Document analysis API endpoints - database-driven, production-ready
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.services.document_analysis_service import document_analysis_service
from app.services.document_upload_service import document_upload_service
from app.services.auth_service import auth_service
from app.middleware.auth_middleware import get_current_active_user
from app.services.category_service import category_service
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/document-analysis", tags=["document_analysis"])


# Temporary file storage (in-memory)
temp_storage = {}


class ConfirmUploadRequest(BaseModel):
    temp_id: str
    title: str
    description: Optional[str] = None
    category_ids: list[str]  # Already supports multiple!
    primary_category_id: Optional[str] = None  # NEW: Explicitly set primary
    confirmed_keywords: list[str]


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Analyze uploaded document without storing permanently
    Returns extracted text, keywords, and suggested category
    """
    try:
        # Get allowed file types from database
        allowed_types = await config_service.get_allowed_mime_types(session)
        
        # Validate file type
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not supported"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Get max file size from database
        max_size = await config_service.get_max_file_size_bytes(session)
        
        # Validate file size
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum of {max_size / 1024 / 1024:.1f}MB"
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
        
        # Convert categories to dict format
        categories_list = [
            {
                'id': cat.id,
                'reference_key': cat.reference_key,
                'name': cat.name
            }
            for cat in user_categories
        ]
        
        # Analyze document with ML
        analysis_result = await document_analysis_service.analyze_document(
            file_content=file_content,
            file_name=file.filename,
            mime_type=file.content_type,
            user_categories=categories_list
        )
        
        # Generate temporary ID
        temp_id = str(uuid.uuid4())
        
        # Store temporarily (expires in 24 hours)
        temp_storage[temp_id] = {
            'file_content': file_content,
            'file_name': file.filename,
            'mime_type': file.content_type,
            'user_id': str(current_user.id),
            'expires_at': datetime.utcnow() + timedelta(hours=24),
            'analysis_result': analysis_result
        }
        
        # Clean up expired files
        _cleanup_expired_temp_files()
        
        logger.info(f"Document analyzed: {file.filename} (temp_id: {temp_id})")
        
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


@router.post("/confirm-upload")
async def confirm_upload(
    confirm_request: ConfirmUploadRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Confirm upload after user review and store document permanently
    """
    try:
        # Check if temp file exists
        if request.temp_id not in temp_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found or expired"
            )
        
        temp_data = temp_storage[request.temp_id]
        
        # Verify ownership
        if temp_data['user_id'] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to confirm this upload"
            )
        
        # Check expiration
        if datetime.utcnow() > temp_data['expires_at']:
            del temp_storage[request.temp_id]
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Analysis result has expired"
            )
        
        # Validate category IDs
        if not request.category_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one category must be selected"
            )
        
        # Get user language
        user_language = current_user.preferred_language or 'en'
        
        # Complete upload with Google Drive storage
        result = await document_upload_service.confirm_upload(
            temp_id=request.temp_id,
            temp_data=temp_data,
            title=request.title,
            category_ids=request.category_ids,
            confirmed_keywords=request.confirmed_keywords,
            description=request.description,
            user_id=str(current_user.id),
            user_email=current_user.email,
            language_code=user_language,
            session=session
        )
        
        # Remove from temporary storage
        del temp_storage[request.temp_id]
        
        logger.info(f"Document uploaded: {result['document_id']}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload confirmation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


def _cleanup_expired_temp_files():
    """Remove expired temporary files"""
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

@router.post("/analyze-batch")
async def analyze_batch(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Analyze multiple documents in batch
    Returns analysis results for all files
    """
    try:
        # Validate batch size
        max_batch_size = await config_service.get_setting('max_batch_upload_size', 10, session)
        
        if len(files) > max_batch_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch size exceeds maximum of {max_batch_size} files"
            )
        
        # Get allowed file types and max size
        allowed_types = await config_service.get_allowed_mime_types(session)
        max_size = await config_service.get_max_file_size_bytes(session)
        
        # Prepare files data
        files_data = []
        for file in files:
            # Validate type
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type {file.content_type} not supported: {file.filename}"
                )
            
            # Read content
            content = await file.read()
            
            # Validate size
            if len(content) > max_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} exceeds maximum size"
                )
            
            files_data.append({
                'content': content,
                'filename': file.filename,
                'mime_type': file.content_type
            })
        
        # Get user categories
        categories_response = await category_service.list_categories(
            user_id=str(current_user.id),
            user_language='en',
            include_system=True,
            include_documents_count=False
        )
        
        categories_list = [
            {'id': cat.id, 'reference_key': cat.reference_key, 'name': cat.name}
            for cat in categories_response.categories
        ]
        
        # Process batch
        from app.services.batch_upload_service import batch_upload_service
        
        batch_result = await batch_upload_service.analyze_batch(
            files_data=files_data,
            user_id=str(current_user.id),
            user_categories=categories_list,
            session=session
        )
        
        # Store temp data for each successful analysis
        for result in batch_result['results']:
            if result['success']:
                temp_storage[result['temp_id']] = {
                    'file_content': next(f['content'] for f in files_data if f['filename'] == result['original_filename']),
                    'file_name': result['original_filename'],
                    'standardized_filename': result['standardized_filename'],
                    'mime_type': next(f['mime_type'] for f in files_data if f['filename'] == result['original_filename']),
                    'user_id': str(current_user.id),
                    'batch_id': result['batch_id'],
                    'expires_at': datetime.utcnow() + timedelta(hours=24),
                    'analysis_result': result['analysis']
                }
        
        logger.info(f"Batch analyzed: {batch_result['batch_id']} - {batch_result['successful']}/{batch_result['total_files']} successful")
        
        return batch_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch analysis failed: {str(e)}"
        )