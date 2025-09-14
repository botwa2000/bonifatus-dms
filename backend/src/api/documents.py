# backend/src/api/documents.py
"""
Bonifatus DMS - Documents API
Document upload, processing, management, and search functionality
Google Drive integration with intelligent categorization
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    File,
    UploadFile,
    Query,
    Form,
    status,
    BackgroundTasks,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from src.database import get_db, Document, Category, DocumentStatus
from src.services.auth_service import AuthService
from src.services.document_service import DocumentService
from src.services.search_service import SearchService
from src.integrations.google_drive import GoogleDriveClient
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()

router = APIRouter()


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category_id: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Upload document to Google Drive with automatic processing
    """
    try:
        # Authenticate user
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Initialize services
        document_service = DocumentService(db)

        # Validate file and user limits
        validation_result = await document_service.validate_upload(
            user=user, file=file, max_size_mb=settings.app.max_file_size_mb
        )

        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["error"],
            )

        # Create initial document record
        document = await document_service.create_document_record(
            user_id=user.id,
            file=file,
            category_id=category_id,
            title=title,
            description=description,
            keywords=keywords.split(",") if keywords else None,
        )

        # Schedule background processing
        background_tasks.add_task(process_document_upload, document.id, file, user.id)

        return {
            "document_id": document.id,
            "filename": document.filename,
            "status": document.status.value,
            "message": "Upload initiated, processing in background",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upload failed"
        )


async def process_document_upload(document_id: int, file: UploadFile, user_id: int):
    """
    Background task to process uploaded document
    """
    db = next(get_db())

    try:
        document_service = DocumentService(db)
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            logger.error(f"Document {document_id} not found for processing")
            return

        # Update status to processing
        document.status = DocumentStatus.PROCESSING
        db.commit()

        # Upload to Google Drive
        drive_client = GoogleDriveClient(user_id, db)
        file.file.seek(0)  # Reset file pointer

        upload_result = await drive_client.upload_file(
            file_data=file.file.read(),
            filename=document.filename,
            mime_type=file.content_type,
            category_name=document.category.name_en if document.category else "General",
        )

        if upload_result:
            # Update document with Google Drive info
            document.google_drive_file_id = upload_result["file_id"]
            document.file_path = upload_result["file_path"]

            # Process document content
            await document_service.process_document_content(document)

            # AI categorization if no category assigned
            if not document.category_id:
                suggested_category = await document_service.suggest_category(document)
                if suggested_category:
                    document.ai_suggested_category = suggested_category["category_id"]
                    document.ai_confidence_score = suggested_category["confidence"]

            document.status = DocumentStatus.READY
            logger.info(f"Document {document_id} processed successfully")

        else:
            document.status = DocumentStatus.ERROR
            document.processing_error = "Failed to upload to Google Drive"
            logger.error(f"Document {document_id} upload to Drive failed")

        db.commit()

    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {e}")
        if document:
            document.status = DocumentStatus.ERROR
            document.processing_error = str(e)
            db.commit()

    finally:
        db.close()


@router.get("/")
async def list_documents(
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query(
        "created_at", regex="^(created_at|updated_at|filename|file_size|view_count)$"
    ),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    List user's documents with filtering, search, and pagination
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        document_service = DocumentService(db)
        search_service = SearchService(db)

        # Build query filters
        filters = {
            "user_id": user.id,
            "category_id": category_id,
            "status": status,
            "page": page,
            "per_page": per_page,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

        # Perform search if query provided
        if search:
            results = await search_service.search_documents(
                user_id=user.id, query=search, filters=filters
            )
        else:
            results = await document_service.list_documents(filters)

        return {
            "documents": results["documents"],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": results["total"],
                "pages": (results["total"] + per_page - 1) // per_page,
            },
            "filters": {"category_id": category_id, "status": status, "search": search},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents",
        )


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get detailed document information
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        document = (
            db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user.id)
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Increment view count
        document.view_count += 1
        document.last_viewed_at = datetime.utcnow()
        db.commit()

        # Format response
        return {
            "id": document.id,
            "filename": document.filename,
            "original_filename": document.original_filename,
            "title": document.title,
            "description": document.description,
            "file_size_bytes": document.file_size_bytes,
            "mime_type": document.mime_type,
            "status": document.status.value,
            "category": (
                {
                    "id": document.category.id,
                    "name_en": document.category.name_en,
                    "name_de": document.category.name_de,
                    "color": document.category.color,
                }
                if document.category
                else None
            ),
            "extracted_keywords": document.extracted_keywords,
            "user_keywords": document.user_keywords,
            "language_detected": document.language_detected,
            "ai_confidence_score": document.ai_confidence_score,
            "notes": document.notes,
            "is_favorite": document.is_favorite,
            "view_count": document.view_count,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "last_viewed_at": (
                document.last_viewed_at.isoformat() if document.last_viewed_at else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document",
        )


@router.put("/{document_id}")
async def update_document(
    document_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category_id: Optional[int] = None,
    keywords: Optional[List[str]] = None,
    notes: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Update document metadata
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        document = (
            db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user.id)
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Update fields
        if title is not None:
            document.title = title
        if description is not None:
            document.description = description
        if category_id is not None:
            # Verify category belongs to user or is system category
            category = (
                db.query(Category)
                .filter(
                    Category.id == category_id,
                    (
                        (Category.user_id == user.id)
                        | (Category.is_system_category == True)
                    ),
                )
                .first()
            )
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category"
                )
            document.category_id = category_id
        if keywords is not None:
            document.user_keywords = keywords
        if notes is not None:
            document.notes = notes
        if is_favorite is not None:
            document.is_favorite = is_favorite

        document.updated_at = datetime.utcnow()
        db.commit()

        return {"message": "Document updated successfully", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update document failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document",
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    permanent: bool = Query(False, description="Permanently delete from Google Drive"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Delete document from system and optionally from Google Drive
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        document = (
            db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user.id)
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Delete from Google Drive if requested
        if permanent and document.google_drive_file_id:
            try:
                drive_client = GoogleDriveClient(user.id, db)
                await drive_client.delete_file(document.google_drive_file_id)
            except Exception as drive_error:
                logger.warning(f"Failed to delete from Google Drive: {drive_error}")
                # Continue with database deletion even if Drive deletion fails

        # Delete from database
        db.delete(document)

        # Update user statistics
        user.document_count = max(0, user.document_count - 1)
        user.storage_used_bytes = max(
            0, user.storage_used_bytes - document.file_size_bytes
        )

        db.commit()

        return {
            "message": "Document deleted successfully",
            "success": True,
            "deleted_from_drive": permanent,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get Google Drive download URL for document
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        document = (
            db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user.id)
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        if not document.google_drive_file_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document not available for download",
            )

        # Get download URL from Google Drive
        drive_client = GoogleDriveClient(user.id, db)
        download_url = await drive_client.get_download_url(
            document.google_drive_file_id
        )

        if not download_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL",
            )

        return {
            "download_url": download_url,
            "filename": document.original_filename,
            "file_size": document.file_size_bytes,
            "mime_type": document.mime_type,
            "expires_in": 3600,  # 1 hour expiration
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download document failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare download",
        )


@router.post("/search")
async def search_documents(
    query: str,
    category_ids: Optional[List[int]] = None,
    file_types: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Advanced document search with filters
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        search_service = SearchService(db)

        search_filters = {
            "user_id": user.id,
            "category_ids": category_ids,
            "file_types": file_types,
            "date_from": date_from,
            "date_to": date_to,
            "page": page,
            "per_page": per_page,
        }

        results = await search_service.advanced_search(query, search_filters)

        return {
            "results": results["documents"],
            "total": results["total"],
            "query": query,
            "search_time_ms": results["search_time_ms"],
            "suggestions": results.get("suggestions", []),
            "pagination": {
                "page": page,
                "per_page": per_page,
                "pages": (results["total"] + per_page - 1) // per_page,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed"
        )
