# backend/app/api/document_analysis.py
"""
Document analysis API endpoints - database-driven, production-ready
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.services.document_analysis_service import document_analysis_service
from app.services.document_upload_service import document_upload_service
from app.services.auth_service import auth_service
from app.middleware.auth_middleware import get_current_active_user, get_client_ip
from app.services.category_service import category_service
from app.services.config_service import config_service
from app.services.user_service import user_service

import io
from app.services.file_validation_service import file_validation_service
from app.services.captcha_service import captcha_service

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

        # Check for duplicates BEFORE expensive analysis (saves time and resources)
        import hashlib
        from app.database.models import Document
        from sqlalchemy import and_

        file_hash = hashlib.sha256(file_content).hexdigest()
        duplicate = session.query(Document).filter(
            and_(
                Document.file_hash == file_hash,
                Document.user_id == current_user.id,
                Document.is_deleted == False
            )
        ).first()

        if duplicate:
            logger.warning(f"Duplicate file upload attempted: {file.filename} (hash: {file_hash[:16]}...)")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "duplicate_file",
                    "message": f"This document has already been uploaded.",
                    "existing_document": {
                        "id": str(duplicate.id),
                        "title": duplicate.title,
                        "filename": duplicate.file_name,
                        "uploaded_at": duplicate.created_at.isoformat()
                    }
                }
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
        
        # Analyze document with ML
        analysis_result = await document_analysis_service.analyze_document(
            file_content=file_content,
            file_name=file.filename,
            mime_type=file.content_type,
            db=session,
            user_id=str(current_user.id)
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
        if confirm_request.temp_id not in temp_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found or expired"
            )

        temp_data = temp_storage[confirm_request.temp_id]
        
        # Verify ownership
        if temp_data['user_id'] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to confirm this upload"
            )
        
        # Check expiration
        if datetime.utcnow() > temp_data['expires_at']:
            del temp_storage[confirm_request.temp_id]
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Analysis result has expired"
            )

        # Validate category IDs
        if not confirm_request.category_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one category must be selected"
            )
        
        # Get user language from user preferences
        user_preferences = await user_service.get_user_preferences(str(current_user.id))
        user_language = user_preferences.language or 'en'
        
        # Complete upload with Google Drive storage
        result = await document_upload_service.confirm_upload(
            temp_id=confirm_request.temp_id,
            temp_data=temp_data,
            title=confirm_request.title,
            category_ids=confirm_request.category_ids,
            confirmed_keywords=confirm_request.confirmed_keywords,
            description=confirm_request.description,
            primary_category_id=confirm_request.primary_category_id,
            user_id=str(current_user.id),
            user_email=current_user.email,
            language_code=user_language,
            session=session
        )

        # Remove from temporary storage
        del temp_storage[confirm_request.temp_id]
        
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
    request: Request,
    files: List[UploadFile] = File(...),
    captcha_token: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Analyze multiple documents in batch with smart security validation
    Returns analysis results for all files
    """
    try:
        ip_address = get_client_ip(request)
        
        # Validate batch size
        max_batch_size = await config_service.get_setting('max_batch_upload_size', 10, session)
        
        if len(files) > max_batch_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch size exceeds maximum of {max_batch_size} files"
            )
        
        # Validate first file to check trust score and CAPTCHA requirement
        if files:
            first_file = files[0]
            file_content = await first_file.read()
            file_stream = io.BytesIO(file_content)
            
            validation_result = await file_validation_service.validate_upload(
                file_content=file_stream,
                filename=first_file.filename,
                user_id=str(current_user.id),
                user_tier=current_user.tier,
                ip_address=ip_address,
                session=session
            )
            
            # Reset file for processing
            await first_file.seek(0)
            
            if not validation_result.allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=validation_result.error_message
                )
            
            # Check if CAPTCHA is required
            if validation_result.captcha_required:
                if not captcha_token:
                    # Return special response telling frontend to show CAPTCHA
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error": "captcha_required",
                            "message": "Security verification required. Please complete the security check.",
                            "warnings": validation_result.warnings
                        }
                    )
                else:
                    # Verify CAPTCHA token
                    captcha_result = await captcha_service.verify_token(
                        token=captcha_token,
                        ip_address=ip_address
                    )
                    
                    if not captcha_result.get('success'):
                        error_message = captcha_service.format_error_message(
                            captcha_result.get('error-codes', [])
                        )
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Security verification failed: {error_message}"
                        )
            
            # Log warnings if any
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logger.warning(f"Upload warning for user {current_user.id}: {warning}")
        
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
        
        # Verify user has categories before processing
        categories_response = await category_service.list_categories(
            user_id=str(current_user.id),
            user_language='en',
            include_system=True,
            include_documents_count=False
        )

        if not categories_response.categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No categories found. Please create categories first."
            )

        # Create batch ID
        batch_id = str(uuid.uuid4())

        # Process each file
        results = []
        for file_data in files_data:
            try:
                # Analyze document
                analysis_result = await document_analysis_service.analyze_document(
                    file_content=file_data['content'],
                    file_name=file_data['filename'],
                    mime_type=file_data['mime_type'],
                    db=session,
                    user_id=str(current_user.id)
                )
                
                # Generate temporary ID
                temp_id = str(uuid.uuid4())
                
                # Store temporarily (expires in 24 hours)
                temp_storage[temp_id] = {
                    'file_content': file_data['content'],
                    'file_name': file_data['filename'],
                    'mime_type': file_data['mime_type'],
                    'user_id': str(current_user.id),
                    'expires_at': datetime.utcnow() + timedelta(hours=24),
                    'analysis_result': analysis_result,
                    'batch_id': batch_id
                }
                
                results.append({
                    'success': True,
                    'temp_id': temp_id,
                    'original_filename': file_data['filename'],
                    'standardized_filename': analysis_result.get('standardized_filename'),
                    'analysis': analysis_result,
                    'batch_id': batch_id
                })
                
            except Exception as e:
                logger.error(f"Failed to analyze {file_data['filename']}: {e}")
                results.append({
                    'success': False,
                    'original_filename': file_data['filename'],
                    'error': str(e),
                    'batch_id': batch_id
                })
        
        # Clean up expired files
        _cleanup_expired_temp_files()
        
        # Include storage info and warnings in response
        response_data = {
            'batch_id': batch_id,
            'total_files': len(files_data),
            'successful': len([r for r in results if r['success']]),
            'failed': len([r for r in results if not r['success']]),
            'results': results,
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        # Add storage info if available
        if validation_result.storage_info:
            response_data['storage_info'] = validation_result.storage_info
        
        # Add warnings if any
        if validation_result.warnings:
            response_data['warnings'] = validation_result.warnings
        
        logger.info(f"Batch analysis completed: {batch_id} ({response_data['successful']}/{response_data['total_files']} successful)")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch analysis failed: {str(e)}"
        )