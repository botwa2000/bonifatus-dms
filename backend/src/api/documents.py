# backend/src/api/documents.py
"""
Bonifatus DMS - Documents API
Document upload, processing, and CRUD operations
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
    document = None  # Initialize document variable to avoid UnboundLocalError
    
    try:
        # Authenticate user
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
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
        background_tasks.add_task(
            process_document_background, document.id, settings.database.database_url
        )

        return {
            "id": document.id,
            "filename": document.filename,
            "status": document.status.value,
            "message": "Document uploaded successfully. Processing in background.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        # Clean up document if it was created but processing failed
        if document and document.id:
            try:
                db.delete(document)
                db.commit()
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup document after error: {cleanup_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )


async def process_document_background(document_id: int, database_url: str):
    """
    Background task for document processing
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create new database session for background task
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found for processing")
            return

        # Update status to processing
        document.status = DocumentStatus.PROCESSING
        db.commit()

        # Initialize services
        document_service = DocumentService(db)
        google_drive = GoogleDriveClient()

        # Upload to Google Drive
        drive_file = await google_drive.upload_file(
            file_content=document.file_content,
            filename=document.filename,
            mime_type=document.mime_type,
            user_id=document.user_id,
        )

        if drive_file:
            # Update document with Drive information
            document.google_drive_file_id = drive_file["id"]
            document.google_drive_url = drive_file["webViewLink"]

            # Extract text and process
            await document_service.process_document_content(document)

            # AI categorization if no category specified
            if not document.category_id:
                suggested_category = await document_service.suggest_category(document)
                if suggested_category:
                    document.category_id = suggested_category["category_id"]
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
    List user's documents with filtering and pagination
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        document_service = DocumentService(db)

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

        # Get documents
        results = await document_service.list_documents(filters)

        return {
            "documents": results["documents"],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": results["total"],
                "pages": (results["total"] + per_page - 1) // per_page,
            },
            "filters": {"category_id": category_id, "status": status},
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
        user = auth_service.get_current_user(credentials.credentials)
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
            "extracted_text": document.extracted_text,
            "extracted_keywords": (
                document.extracted_keywords.split(",")
                if document.extracted_keywords
                else []
            ),
            "user_keywords": (
                document.user_keywords.split(",") if document.user_keywords else []
            ),
            "is_favorite": document.is_favorite,
            "view_count": document.view_count,
            "google_drive_url": document.google_drive_url,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "last_viewed_at": (
                document.last_viewed_at.isoformat() if document.last_viewed_at else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
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
    keywords: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Update document metadata
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
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
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if category_id is not None:
            # Validate category belongs to user
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
            update_data["category_id"] = category_id
        if keywords is not None:
            update_data["user_keywords"] = keywords
        if is_favorite is not None:
            update_data["is_favorite"] = is_favorite

        # Apply updates
        for field, value in update_data.items():
            setattr(document, field, value)

        document.updated_at = datetime.utcnow()
        db.commit()

        return {
            "id": document.id,
            "message": "Document updated successfully",
            "updated_fields": list(update_data.keys()),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document",
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Delete document from system and Google Drive
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
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

        # Delete from Google Drive if exists
        if document.google_drive_file_id:
            try:
                google_drive = GoogleDriveClient()
                await google_drive.delete_file(
                    file_id=document.google_drive_file_id, user_id=user.id
                )
            except Exception as e:
                logger.warning(f"Failed to delete from Google Drive: {e}")

        # Delete from database
        db.delete(document)
        db.commit()

        return {
            "message": "Document deleted successfully",
            "deleted_document_id": document_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
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
    Generate download URL for document
    """
    try:
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
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

        # Generate download URL
        google_drive = GoogleDriveClient()
        download_url = await google_drive.get_download_url(
            file_id=document.google_drive_file_id, user_id=user.id
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
