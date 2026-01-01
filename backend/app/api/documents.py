# backend/app/api/documents.py
"""
Bonifatus DMS - Document Management API Endpoints
REST API for document upload, processing, and management operations
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.schemas.document_schemas import (
    DocumentUploadResponse, DocumentResponse, DocumentUpdateRequest,
    DocumentListResponse, DocumentSearchRequest, DocumentStorageInfo,
    BatchOperationRequest, BatchOperationResponse, DocumentProcessingStatus,
    ErrorResponse
)
from app.services.document_service import document_service
from app.services.drive_service import drive_service
from app.services.document_analysis_service import DocumentAnalysisService
from app.middleware.auth_middleware import (
    get_current_active_user,
    get_client_ip,
    get_delegate_context,
    DelegateContext
)
from app.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["document_management"])


# Entity update models
class EntityUpdate(BaseModel):
    type: str
    value: str
    confidence: float = 1.0
    method: str = 'manual'


class EntityUpdateRequest(BaseModel):
    entities: List[EntityUpdate]


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file or quota exceeded"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Delegates cannot upload documents"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported file type"},
        500: {"model": ErrorResponse, "description": "Upload failed"}
    }
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    category_ids: str = Form(...),  # Comma-separated category IDs
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    delegate_ctx: DelegateContext = Depends(get_delegate_context)
) -> DocumentUploadResponse:
    """
    Upload document to Google Drive and process metadata

    Validates file type, size, and user storage quota before upload
    Note: Delegates with viewer role cannot upload documents
    """
    try:
        # Block delegates from uploading
        if delegate_ctx.is_acting_as_delegate:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Delegates cannot upload documents to another user's account"
            )

        ip_address = get_client_ip(request)

        # Check if any storage provider is connected
        if not current_user.active_storage_provider:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="STORAGE_PROVIDER_NOT_CONNECTED"  # Special code for frontend to handle
            )

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )

        file_content = await file.read()
        file_stream = io.BytesIO(file_content)

        # Parse category IDs from comma-separated string
        category_id_list = [cid.strip() for cid in category_ids.split(',') if cid.strip()]
        if not category_id_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one category must be selected"
            )
        
        upload_result = await document_service.upload_document(
            user_id=str(current_user.id),
            user_email=current_user.email,
            user_tier=current_user.tier.name if current_user.tier else "free",
            file_content=file_stream,
            filename=file.filename,
            category_ids=category_id_list,
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
        403: {"model": ErrorResponse, "description": "Delegate access denied"},
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
    include_own: bool = True,
    include_shared: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    delegate_ctx: DelegateContext = Depends(get_delegate_context)
) -> DocumentListResponse:
    """
    List user documents with search and filtering

    Supports full-text search, category filtering, and pagination

    Multi-source filtering (new):
    - include_own: Include user's own documents (default: true)
    - include_shared: Comma-separated owner user IDs to include shared documents from

    Legacy support:
    - X-Acting-As-User-Id header for single-owner delegate access
    """
    try:
        # Handle legacy single-owner delegate access via header
        if delegate_ctx.is_acting_as_delegate and not include_shared:
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
                str(delegate_ctx.effective_user_id), search_request
            )

            if not documents_result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve documents"
                )

            logger.info(f"Documents listed as delegate for owner: {delegate_ctx.owner_user.email}")
            return documents_result

        # New multi-source document fetching
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

        # Parse shared owner IDs
        shared_owner_ids = []
        if include_shared:
            shared_owner_ids = [
                owner_id.strip()
                for owner_id in include_shared.split(',')
                if owner_id.strip()
            ]

        documents_result = await document_service.search_documents_multi_source(
            current_user=current_user,
            search_request=search_request,
            include_own=include_own,
            shared_owner_ids=shared_owner_ids
        )

        if not documents_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents"
            )

        logger.info(
            f"Documents listed for user {current_user.email}: "
            f"own={include_own}, shared_sources={len(shared_owner_ids)}"
        )

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
        403: {"model": ErrorResponse, "description": "Delegate access denied"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_document(
    document_id: str,
    delegate_ctx: DelegateContext = Depends(get_delegate_context)
) -> DocumentResponse:
    """
    Get document details by ID

    Returns complete document metadata and processing status
    Delegates can access owner's documents using X-Acting-As-User-Id header
    """
    try:
        document = await document_service.get_document(
            document_id, str(delegate_ctx.effective_user_id)
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        if delegate_ctx.is_acting_as_delegate:
            logger.info(
                f"Document retrieved as delegate: {document_id} for owner {delegate_ctx.owner_user.email}"
            )
        else:
            logger.info(f"Document retrieved: {document_id} by user {delegate_ctx.effective_user_id}")

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
        403: {"model": ErrorResponse, "description": "Delegates cannot modify documents"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_document(
    document_id: str,
    request: Request,
    update_request: DocumentUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    delegate_ctx: DelegateContext = Depends(get_delegate_context)
) -> DocumentResponse:
    """
    Update document metadata

    Updates title, description, and category assignment
    Note: Delegates with viewer role cannot modify documents
    """
    try:
        # Block delegates from updating
        if delegate_ctx.is_acting_as_delegate and not delegate_ctx.can_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Delegates with viewer role cannot modify documents"
            )

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


@router.put(
    "/{document_id}/entities",
    responses={
        200: {"description": "Entities updated successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_document_entities(
    document_id: str,
    request: Request,
    entity_request: EntityUpdateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update document entities (add/remove/edit)

    Replaces all entities with the provided list
    """
    try:
        from app.database.connection import SessionLocal
        from app.database.models import Document, DocumentEntity
        import uuid

        db = SessionLocal()

        try:
            # Verify document belongs to user
            document = db.query(Document).filter(
                Document.id == uuid.UUID(document_id),
                Document.user_id == uuid.UUID(str(current_user.id)),
                Document.is_deleted == False
            ).first()

            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )

            # Delete existing entities
            db.query(DocumentEntity).filter(
                DocumentEntity.document_id == uuid.UUID(document_id)
            ).delete()

            # Add new entities
            for entity_data in entity_request.entities:
                entity = DocumentEntity(
                    document_id=uuid.UUID(document_id),
                    entity_type=entity_data.type,
                    entity_value=entity_data.value,
                    normalized_value=entity_data.value.lower(),
                    confidence=entity_data.confidence,
                    extraction_method=entity_data.method,
                    language_code=document.primary_language or 'en'
                )
                db.add(entity)

            db.commit()

            logger.info(f"Entities updated for document {document_id} by user {current_user.email}: {len(entity_request.entities)} entities")

            return {"success": True, "message": f"Updated {len(entity_request.entities)} entities"}

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update entities error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entity update service error"
        )


@router.delete(
    "/{document_id}",
    responses={
        200: {"description": "Document deleted successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Delegates cannot delete documents"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_document(
    document_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    delegate_ctx: DelegateContext = Depends(get_delegate_context)
):
    """
    Delete document from system and Google Drive

    Permanently removes document and all associated data
    Note: Delegates cannot delete documents
    """
    try:
        # Block delegates from deleting
        if delegate_ctx.is_acting_as_delegate and not delegate_ctx.can_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Delegates cannot delete documents"
            )

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

        # Get document owner's storage provider credentials (for delegate access)
        from app.database.connection import get_db as get_db_direct
        from app.database.models import Document as DocumentModel
        from app.services.document_storage_service import document_storage_service
        from sqlalchemy import select
        db_session = next(get_db_direct())

        # First get the document from DB to get owner's user_id
        doc_model = db_session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        ).scalar_one_or_none()

        if not doc_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Now get the owner
        owner = db_session.execute(
            select(User).where(User.id == doc_model.user_id)
        ).scalar_one_or_none()

        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document owner not found"
            )

        # Check if owner has any active storage provider using ProviderConnection
        if not document_storage_service.get_active_provider(owner):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The document owner has not connected a cloud storage provider. Please contact the document owner."
            )

        # Use provider-agnostic download service
        file_content_bytes = document_storage_service.download_document(
            user=owner,
            file_id=document.google_drive_file_id,
            db=db_session
        )

        if not file_content_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document content not available"
            )

        logger.info(f"Document downloaded: {document_id} by user {current_user.email} (owner: {owner.email})")

        return StreamingResponse(
            io.BytesIO(file_content_bytes),
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
    "/{document_id}/content",
    responses={
        200: {"description": "Document content for preview", "content": {"application/pdf": {}}},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Content retrieval failed"}
    }
)
async def get_document_content(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get document content for inline preview

    Returns document content with inline disposition for browser preview
    """
    try:
        document = await document_service.get_document(document_id, str(current_user.id))

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Get document owner's storage provider credentials (for delegate access)
        from app.database.connection import get_db as get_db_direct
        from app.database.models import Document as DocumentModel
        from app.services.document_storage_service import document_storage_service
        from sqlalchemy import select
        db_session = next(get_db_direct())

        # First get the document from DB to get owner's user_id
        doc_model = db_session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        ).scalar_one_or_none()

        if not doc_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Now get the owner
        owner = db_session.execute(
            select(User).where(User.id == doc_model.user_id)
        ).scalar_one_or_none()

        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document owner not found"
            )

        # Check if owner has any active storage provider using ProviderConnection
        if not document_storage_service.get_active_provider(owner):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The document owner has not connected a cloud storage provider. Please contact the document owner."
            )

        # Use provider-agnostic download service
        file_content_bytes = document_storage_service.download_document(
            user=owner,
            file_id=document.google_drive_file_id,
            db=db_session
        )

        if not file_content_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document content not available"
            )

        logger.info(f"Document content retrieved: {document_id} by user {current_user.email}")

        return StreamingResponse(
            io.BytesIO(file_content_bytes),
            media_type=document.mime_type,
            headers={
                "Content-Disposition": f"inline; filename=\"{document.file_name}\""
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document content error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document content service error"
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


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Document not found"},
        500: {"model": ErrorResponse, "description": "Reprocessing failed"}
    }
)
async def reprocess_document(
    document_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> DocumentResponse:
    """
    Reprocess document for classification and keyword extraction

    Triggers document analysis, classification, and keyword extraction
    """
    try:
        document = await document_service.get_document(document_id, str(current_user.id))

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Get document owner's storage provider credentials (for delegate access)
        from app.database.connection import get_db as get_db_direct
        from app.database.models import Document as DocumentModel
        from app.services.document_storage_service import document_storage_service
        from sqlalchemy import select
        db_session = next(get_db_direct())

        # First get the document from DB to get owner's user_id
        doc_model = db_session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        ).scalar_one_or_none()

        if not doc_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Now get the owner
        owner = db_session.execute(
            select(User).where(User.id == doc_model.user_id)
        ).scalar_one_or_none()

        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document owner not found"
            )

        # Check if owner has any active storage provider using ProviderConnection
        if not document_storage_service.get_active_provider(owner):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The document owner has not connected a cloud storage provider. Please contact the document owner."
            )

        # Download document content using provider-agnostic service
        file_content_bytes = document_storage_service.download_document(
            user=owner,
            file_id=document.google_drive_file_id,
            db=db_session
        )

        if not file_content_bytes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document content not available"
            )

        # Reprocess document with analysis service
        analysis_service = DocumentAnalysisService()
        await analysis_service.analyze_document(
            document_id=document_id,
            user_id=str(current_user.id),
            file_content=io.BytesIO(file_content_bytes),
            mime_type=document.mime_type
        )

        logger.info(f"Document reprocessed: {document_id} by user {current_user.email}")

        # Return updated document
        updated_document = await document_service.get_document(document_id, str(current_user.id))
        if not updated_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found after reprocessing"
            )

        return updated_document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reprocess document error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document reprocessing service error"
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
            str(current_user.id), current_user.tier.name if current_user.tier else "free"
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