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
from app.services.tier_service import tier_service, TierLimitExceeded
from app.services.batch_processor_service import batch_processor_service

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
        logger.info(f"[DUPLICATE DEBUG] === Checking for duplicate (single file) ===")
        logger.info(f"[DUPLICATE DEBUG] Filename: {file.filename}")

        import hashlib
        from app.database.models import Document
        from sqlalchemy import and_

        file_hash = hashlib.sha256(file_content).hexdigest()
        logger.info(f"[DUPLICATE DEBUG] File hash (SHA-256): {file_hash}")
        logger.info(f"[DUPLICATE DEBUG] User ID: {current_user.id}")

        duplicate = session.query(Document).filter(
            and_(
                Document.file_hash == file_hash,
                Document.user_id == current_user.id,
                Document.is_deleted == False
            )
        ).first()

        if duplicate:
            logger.warning(f"[DUPLICATE DEBUG] ❌ DUPLICATE FOUND!")
            logger.warning(f"[DUPLICATE DEBUG] Existing document ID: {duplicate.id}")
            logger.warning(f"[DUPLICATE DEBUG] Existing document title: {duplicate.title}")
            logger.warning(f"[DUPLICATE DEBUG] Uploaded at: {duplicate.created_at}")
            logger.warning(f"[DUPLICATE DEBUG] Returning 409 Conflict")

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

        logger.info(f"[DUPLICATE DEBUG] ✅ No duplicate found, proceeding with analysis")

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
    import json
    import aiofiles
    import glob
    from pathlib import Path

    try:
        # Check in-memory storage first (single file uploads)
        if confirm_request.temp_id in temp_storage:
            temp_data = temp_storage[confirm_request.temp_id]
        else:
            # Check on disk for batch uploads
            metadata_files = glob.glob(f"/app/temp/batches/*/{confirm_request.temp_id}.json")

            if not metadata_files:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Analysis result not found or expired"
                )

            # Read metadata from disk
            metadata_path = Path(metadata_files[0])
            async with aiofiles.open(metadata_path, 'r') as f:
                metadata = json.loads(await f.read())

            # Read file content from disk
            file_path = metadata['file_path']
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()

            # Reconstruct temp_data structure
            temp_data = {
                'file_content': file_content,
                'file_name': metadata['file_name'],
                'mime_type': metadata['mime_type'],
                'user_id': metadata['user_id'],
                'expires_at': datetime.fromisoformat(metadata['expires_at']),
                'analysis_result': metadata['analysis_result']
            }

        # Verify ownership
        if temp_data['user_id'] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to confirm this upload"
            )

        # Check expiration
        if datetime.utcnow() > temp_data['expires_at']:
            if confirm_request.temp_id in temp_storage:
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

        # Update storage quota after successful upload
        file_size = len(temp_data['file_content'])
        await tier_service.update_storage_usage(
            user_id=str(current_user.id),
            file_size_bytes=file_size,
            session=session,
            increment=True
        )

        # Clean up temp storage immediately after successful confirmation
        if confirm_request.temp_id in temp_storage:
            # Single file upload - remove from memory
            del temp_storage[confirm_request.temp_id]
        else:
            # Batch upload - delete temp files from disk
            import glob
            import os
            from pathlib import Path

            # Find and delete metadata file
            metadata_files = glob.glob(f"/app/temp/batches/*/{confirm_request.temp_id}.json")
            for metadata_file in metadata_files:
                try:
                    # Get batch_id from path to potentially cleanup entire batch directory
                    batch_dir = Path(metadata_file).parent

                    # Delete metadata file
                    os.remove(metadata_file)
                    logger.info(f"Deleted temp metadata: {metadata_file}")

                    # Check if this was the last file in the batch
                    remaining_files = list(batch_dir.glob("*"))
                    if not remaining_files:
                        # All files confirmed, delete entire batch directory
                        import shutil
                        shutil.rmtree(batch_dir)
                        logger.info(f"Deleted empty batch directory: {batch_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {metadata_file}: {e}")

        logger.info(f"Document uploaded: {result['document_id']}, size: {file_size} bytes")

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

        # Validate batch size based on user's tier
        # Admin users have unlimited batch size
        if not current_user.is_admin:
            tier = await tier_service.get_user_tier(str(current_user.id), session)
            max_batch_size = tier.max_batch_upload_size if tier and tier.max_batch_upload_size else 10

            if len(files) > max_batch_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Batch size exceeds maximum of {max_batch_size} files for your tier. Please upgrade or upload fewer files."
                )

        # TIER ENFORCEMENT: Check bulk operations for multi-file uploads
        # Admin users bypass all tier restrictions
        if len(files) > 1 and not current_user.is_admin:
            has_bulk_ops = await tier_service.check_feature_access(
                user_id=str(current_user.id),
                feature='bulk_operations',
                session=session
            )
            if not has_bulk_ops:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bulk upload requires Starter plan or higher. Please upgrade or upload files one at a time."
                )

        # TIER ENFORCEMENT: Check document count limit
        # Admin users bypass document count limits
        if not current_user.is_admin:
            try:
                await tier_service.check_document_count_limit(
                    user_id=str(current_user.id),
                    session=session,
                    raise_on_exceed=True
                )
            except TierLimitExceeded as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{e.message}. Please upgrade your plan or delete some documents."
                )

        # TIER ENFORCEMENT: Check storage quota for all files
        # Admin users bypass storage quota limits
        total_size = 0
        file_sizes = []
        for file in files:
            # Read file to get size, then reset position
            content = await file.read()
            size = len(content)
            await file.seek(0)  # Reset to beginning
            file_sizes.append(size)
            total_size += size

        if not current_user.is_admin:
            try:
                await tier_service.check_storage_quota(
                    user_id=str(current_user.id),
                    file_size_bytes=total_size,
                    session=session,
                    raise_on_exceed=True
                )
            except TierLimitExceeded as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{e.message}. Please upgrade your plan or delete some documents to free up space."
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
                user_tier=current_user.tier.name if current_user.tier else "free",
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
        for idx, file_data in enumerate(files_data):
            logger.info(f"[DUPLICATE DEBUG] === Processing file {idx+1}/{len(files_data)} ===")
            try:
                # Check for duplicates BEFORE expensive analysis (saves time and resources)
                logger.info(f"[DUPLICATE DEBUG] Filename: {file_data['filename']}")

                import hashlib
                from app.database.models import Document
                from sqlalchemy import and_

                file_hash = hashlib.sha256(file_data['content']).hexdigest()
                logger.info(f"[DUPLICATE DEBUG] File hash: {file_hash}")
                logger.info(f"[DUPLICATE DEBUG] User ID: {current_user.id}")

                duplicate = session.query(Document).filter(
                    and_(
                        Document.file_hash == file_hash,
                        Document.user_id == current_user.id,
                        Document.is_deleted == False
                    )
                ).first()

                if duplicate:
                    logger.warning(f"[DUPLICATE DEBUG] ❌ DUPLICATE FOUND in batch!")
                    logger.warning(f"[DUPLICATE DEBUG] Existing document: {duplicate.title} (ID: {duplicate.id})")
                    logger.warning(f"[DUPLICATE DEBUG] Uploaded at: {duplicate.created_at}")

                    # Return error for this specific file in the batch
                    results.append({
                        'success': False,
                        'original_filename': file_data['filename'],
                        'error': f"This document has already been uploaded as '{duplicate.title}' on {duplicate.created_at.strftime('%Y-%m-%d')}",
                        'batch_id': batch_id,
                        'duplicate_of': {
                            'id': str(duplicate.id),
                            'title': duplicate.title,
                            'filename': duplicate.file_name,
                            'uploaded_at': duplicate.created_at.isoformat()
                        }
                    })
                    continue  # Skip analysis for this duplicate file

                logger.info(f"[DUPLICATE DEBUG] ✅ No duplicate, proceeding with analysis")

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


@router.post("/analyze-batch-async")
async def analyze_batch_async(
    request: Request,
    files: List[UploadFile] = File(...),
    captcha_token: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Analyze multiple documents asynchronously with progress tracking

    Returns immediately with batch_id, processes files in background.
    Use /batch-status/{batch_id} to poll for progress.
    """
    try:
        ip_address = get_client_ip(request)

        # Validate batch size based on user's tier
        if not current_user.is_admin:
            tier = await tier_service.get_user_tier(str(current_user.id), session)
            max_batch_size = tier.max_batch_upload_size if tier and tier.max_batch_upload_size else 10

            if len(files) > max_batch_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Batch size exceeds maximum of {max_batch_size} files for your tier"
                )

        # TIER ENFORCEMENT: Check bulk operations
        if len(files) > 1 and not current_user.is_admin:
            has_bulk_ops = await tier_service.check_feature_access(
                user_id=str(current_user.id),
                feature='bulk_operations',
                session=session
            )
            if not has_bulk_ops:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bulk upload requires Starter plan or higher"
                )

        # Verify user has categories BEFORE processing
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

        # Check document count limit
        if not current_user.is_admin:
            await tier_service.check_document_count_limit(
                user_id=str(current_user.id),
                session=session,
                raise_on_exceed=True
            )

        # Create batch record first to get batch_id
        batch_id = await batch_processor_service.create_batch(
            user_id=str(current_user.id),
            total_files=len(files),
            session=session
        )

        # Stream files to temporary disk storage
        import os
        import aiofiles
        from pathlib import Path

        temp_dir = Path(f"/app/temp/batches/{batch_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)

        file_paths = []
        total_size = 0

        for idx, file in enumerate(files):
            # Generate safe filename
            safe_filename = f"{idx}_{file.filename}"
            file_path = temp_dir / safe_filename

            # Stream file to disk
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
                total_size += len(content)

            file_paths.append({
                'path': str(file_path),
                'original_filename': file.filename,
                'mime_type': file.content_type,
                'size': len(content)
            })

        # Check storage quota AFTER calculating total size
        if not current_user.is_admin:
            await tier_service.check_storage_quota(
                user_id=str(current_user.id),
                file_size_bytes=total_size,
                session=session,
                raise_on_exceed=True
            )

        # Start background processing with file paths (non-blocking)
        await batch_processor_service.start_batch_processing(
            batch_id=batch_id,
            file_paths=file_paths,
            user_id=str(current_user.id)
        )

        logger.info(f"Async batch {batch_id} created with {len(file_paths)} files")

        return {
            'batch_id': batch_id,
            'status': 'pending',
            'total_files': len(file_paths),
            'message': 'Batch processing started. Use /batch-status/{batch_id} to check progress.'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Async batch creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/batch-status/{batch_id}")
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """
    Get current status and progress of a batch processing job

    Poll this endpoint to track real-time progress.
    """
    try:
        status_data = await batch_processor_service.get_batch_status(
            batch_id=batch_id,
            user_id=str(current_user.id),
            session=session
        )

        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch not found"
            )

        return status_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )