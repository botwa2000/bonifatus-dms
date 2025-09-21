# backend/app/api/documents.py
"""
Bonifatus DMS - Document Management API Endpoints
REST API for document upload, processing, and management operations
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import io

from app.schemas.document_schemas import (
    DocumentUploadResponse, DocumentResponse, DocumentUpdateRequest,
    DocumentListResponse, DocumentSearchRequest, DocumentStorageInfo,
    BatchOperationRequest, BatchOperationResponse, DocumentProcessingStatus,
    ErrorResponse
)
from app.services.document_service import document_service
from app.services.google_drive_service import google_drive_service
from app.middleware.auth_middleware import get_current_active_user, get_client_ip
from app.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["document_management"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file or quota exceeded"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        500: {"model": ErrorResponse, "description": "Upload failed"}
    }
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
) -> DocumentUploadResponse:
    """
    Upload document to Google Drive and process metadata
    
    Validates file type, size, and user storage quota before upload
    """
    try:
        ip_address = get_client_ip(request)
        
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )

        file_content = await file.read()
        file_stream = io.BytesIO(file_content)

        upload_result = await document_service.upload_document(
            user_id=str(current_user.id),
            user_email=current_user.email,
            user_tier=current_user.tier,
            file_content=file_stream,
            filename=file.filename,
            title=title,
            description=description,
            ip_address=ip_address
        )

        if not upload_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Document upload failed"
            )

        logger.info(f"Document uploaded successfully: {upload_result.id} by user {current_user.email}")
        return upload_result

    except ValueError as e:
        error_msg = str(e)
        if "file type" in error_msg.lower():
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        elif "file size" in error_msg.lower() or "large" in error_msg.lower():
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        elif "quota" in error_msg.lower() or "storage" in error_msg.lower():
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            
        raise HTTPException(status_code=status_code, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload service error"
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_documents(
    query: Optional[str] = None,
    category_id: Optional[str] = None,
    language: Optional[str] = None,
    processing_status: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
) -> DocumentListResponse:
    """
    List user documents with search and filtering
    
    Supports full-text search, category filtering, and pagination
    """
    try:
        search_request = DocumentSearchRequest(
            query=query,
            category_id=category_id,
            language=language,
            processing_status=processing_status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )

        documents_result = await document_service.search_documents(
            str(current_user.id), search_request
        )

        if not documents_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents"
            )

        logger.info(f"Documents listed for user: {current_user.email}")
        return documents_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document listing service error"
        )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> DocumentResponse:
    """
    Get document details by ID
    
    Returns complete document metadata and processing status
    """
    try:
        document = await document_service.get_document(document_id, str(current_user.id))

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        logger.info(f"Document retrieved: {document_id} by user {current_user.email}")
        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document retrieval service error"
        )


@router.put(
    "/{document_id}",
    response_model=DocumentResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid update data"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_document(
    document_id: str,
    request: Request,
    update_request: DocumentUpdateRequest,
    current_user: User = Depends(get_current_active_user)
) -> DocumentResponse:
    """
    Update document metadata
    
    Updates title, description, and category assignment
    """
    try:
        ip_address = get_client_ip(request)

        updated_document = await document_service.update_document(
            document_id, str(current_user.id), update_request, ip_address
        )

        if not updated_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or update failed"
            )

        logger.info(f"Document updated: {document_id} by user {current_user.email}")
        return updated_document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update document error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document update service error"
        )


@router.delete(
    "/{document_id}",
    responses={
        200: {"description": "Document deleted successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_document(
    document_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete document from system and Google Drive
    
    Permanently removes document and all associated data
    """
    try:
        ip_address = get_client_ip(request)

        success = await document_service.delete_document(
            document_id, str(current_user.id), ip_address
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or deletion failed"
            )

        logger.info(f"Document deleted: {document_id} by user {current_user.email}")
        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document deletion service error"
        )


@router.get(
    "/{document_id}/download",
    responses={
        200: {"description": "Document content", "content": {"application/octet-stream": {}}},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Download failed"}
    }
)
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Download document content from Google Drive
    
    Streams document content directly from Google Drive
    """
    try:
        document = await document_service.get_document(document_id, str(current_user.id))

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        file_content = await google_drive_service.download_document(document.google_drive_file_id)

        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document content not available"
            )

        logger.info(f"Document downloaded: {document_id} by user {current_user.email}")

        return StreamingResponse(
            io.BytesIO(file_content.read()),
            media_type=document.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{document.file_name}\""
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download document error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document download service error"
        )


@router.get(
    "/{document_id}/status",
    response_model=DocumentProcessingStatus,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_document_processing_status(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> DocumentProcessingStatus:
    """
    Get document processing status
    
    Returns current processing status and progress information
    """
    try:
        document = await document_service.get_document(document_id, str(current_user.id))

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        return DocumentProcessingStatus(
            document_id=document_id,
            processing_status=document.processing_status,
            progress_percentage=None,
            error_message=None,
            estimated_completion=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get processing status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Processing status service error"
        )


@router.get(
    "/storage/info",
    response_model=DocumentStorageInfo,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_storage_info(
    current_user: User = Depends(get_current_active_user)
) -> DocumentStorageInfo:
    """
    Get user storage usage and quota information
    
    Returns storage statistics and remaining quota
    """
    try:
        storage_info = await document_service.get_storage_info(
            str(current_user.id), current_user.tier
        )

        if not storage_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve storage information"
            )

        logger.info(f"Storage info retrieved for user: {current_user.email}")
        return storage_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get storage info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage info service error"
        )