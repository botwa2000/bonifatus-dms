# backend/app/services/document_service.py
"""
Bonifatus DMS - Document Management Service
Business logic for document operations with database-driven configuration
"""

import logging
import json
import mimetypes
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text, and_, or_

from app.database.models import Document, Category, User, AuditLog, SystemSetting
from app.database.connection import db_manager
from app.services.google_drive_service import google_drive_service
from app.schemas.document_schemas import (
    DocumentUploadResponse, DocumentResponse, DocumentUpdateRequest,
    DocumentListResponse, DocumentSearchRequest, DocumentStorageInfo,
    BatchOperationRequest, BatchOperationResponse, DocumentProcessingStatus
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Document management business logic service"""

    def __init__(self):
        self._system_settings_cache = {}
        self._cache_timestamp = None
        self._cache_ttl_seconds = 300

    def generate_document_filename(
        self,
        original_filename: str,
        category_code: str,
        upload_date: datetime
    ) -> str:
        """
        Generate standardized document filename
        Format: YYYY-MM-DD_HHMMSS_[CODE]_OriginalName.ext
        """
        name_parts = original_filename.rsplit('.', 1)
        base_name = name_parts[0] if len(name_parts) > 1 else original_filename
        extension = name_parts[1] if len(name_parts) > 1 else ''
        
        # Sanitize filename
        safe_name = base_name.replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
        
        # Generate timestamp
        date_str = upload_date.strftime('%Y-%m-%d')
        time_str = upload_date.strftime('%H%M%S')
        
        # Build filename
        filename = f"{date_str}_{time_str}_{category_code}_{safe_name}"
        if extension:
            filename = f"{filename}.{extension}"
        
        return filename

    async def _get_system_setting(self, key: str, default: Any = None) -> Any:
        """Get system setting from database with caching"""
        session = db_manager.session_local()
        try:
            if (self._cache_timestamp is None or 
                (datetime.utcnow() - self._cache_timestamp).total_seconds() > self._cache_ttl_seconds):
                await self._refresh_system_settings_cache(session)

            value = self._system_settings_cache.get(key, default)
            
            if isinstance(value, str):
                if value.lower() in ('true', 'false'):
                    return value.lower() == 'true'
                try:
                    return int(value)
                except ValueError:
                    try:
                        return float(value)
                    except ValueError:
                        return value
            
            return value

        except Exception as e:
            logger.error(f"Failed to get system setting {key}: {e}")
            return default
        finally:
            session.close()

    async def _refresh_system_settings_cache(self, session: Session):
        """Refresh system settings cache from database"""
        try:
            settings_stmt = select(SystemSetting)
            settings = session.execute(settings_stmt).scalars().all()
            
            self._system_settings_cache = {
                setting.setting_key: setting.setting_value 
                for setting in settings
            }
            self._cache_timestamp = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to refresh system settings cache: {e}")

    async def _validate_file_type(self, filename: str) -> bool:
        """Validate file type against supported types from database"""
        try:
            supported_types_str = await self._get_system_setting("supported_document_types", "")
            if not supported_types_str:
                return False
                
            supported_types = [ext.strip().lower() for ext in supported_types_str.split(",")]
            file_extension = filename.lower().split('.')[-1] if '.' in filename else ""
            
            return file_extension in supported_types
            
        except Exception as e:
            logger.error(f"File type validation error: {e}")
            return False

    async def _validate_file_size(self, file_size: int) -> bool:
        """Validate file size against maximum allowed from database"""
        try:
            max_size_mb = await self._get_system_setting("max_file_size_mb", 100)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            return file_size <= max_size_bytes
            
        except Exception as e:
            logger.error(f"File size validation error: {e}")
            return False

    async def _check_storage_quota(self, user_id: str, user_tier: str, additional_size: int) -> bool:
        """Check if user has enough storage quota for additional file"""
        try:
            current_usage = await self.get_user_storage_usage(user_id)
            
            storage_limit_key = f"storage_limit_{user_tier}_tier_mb"
            storage_limit_mb = await self._get_system_setting(storage_limit_key, 1024)
            storage_limit_bytes = storage_limit_mb * 1024 * 1024
            
            return (current_usage + additional_size) <= storage_limit_bytes
            
        except Exception as e:
            logger.error(f"Storage quota check error: {e}")
            return False

    async def upload_document(
        self,
        user_id: str,
        user_email: str,
        user_tier: str,
        file_content: BinaryIO,
        filename: str,
        category_ids: List[str],
        title: Optional[str] = None,
        description: Optional[str] = None,
        ip_address: str = None
    ) -> Optional[DocumentUploadResponse]:
        """Upload document with validation and processing"""
        session = db_manager.session_local()
        try:
            file_content.seek(0, 2)
            file_size = file_content.tell()
            file_content.seek(0)

            if not await self._validate_file_type(filename):
                raise ValueError("Unsupported file type")

            if not await self._validate_file_size(file_size):
                max_size_mb = await self._get_system_setting("max_file_size_mb", 100)
                raise ValueError(f"File size exceeds maximum allowed size of {max_size_mb}MB")

            if not await self._check_storage_quota(user_id, user_tier, file_size):
                raise ValueError("Storage quota exceeded")

            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'

            # Get primary category for filename and folder
            from app.database.models import Category
            primary_category = session.get(Category, category_ids[0])
            if not primary_category:
                raise ValueError("Primary category not found")
            
            # Generate standardized filename
            upload_date = datetime.utcnow()
            standardized_filename = self.generate_document_filename(
                filename,
                primary_category.category_code,
                upload_date
            )
            
            # Get category folder name (use English translation)
            category_folder = next(
                (t.name for t in primary_category.translations if t.language_code == 'en'),
                primary_category.translations[0].name if primary_category.translations else "Other"
            )

            drive_result = await google_drive_service.upload_document(
                file_content=file_content,
                filename=standardized_filename,
                user_email=user_email,
                mime_type=mime_type
            )
            
            if not drive_result:
                raise Exception("Failed to upload to Google Drive")

            document_title = title or filename.rsplit('.', 1)[0]
            
            document = Document(
                title=document_title,
                description=description,
                file_name=standardized_filename,
                file_size=file_size,
                mime_type=mime_type,
                google_drive_file_id=drive_result['drive_file_id'],
                processing_status="uploaded",
                user_id=user_id,
                category_id=category_ids[0]  # Primary category for backward compatibility
            )
            
            session.add(document)
            session.commit()
            session.refresh(document)

            from app.database.models import DocumentCategory
            for idx, category_id in enumerate(category_ids):
                doc_category = DocumentCategory(
                    document_id=document.id,
                    category_id=category_id,
                    is_primary=(idx == 0),
                    assigned_by_ai=False
                )
                session.add(doc_category)

            await self._log_document_action(
                user_id, "document_upload", "document", str(document.id),
                {}, {"filename": filename, "size": file_size}, ip_address, session
            )

            logger.info(f"Document uploaded successfully: {document.id} for user {user_email}")

            category_names = []
            for cat_id in category_ids:
                cat = session.get(Category, cat_id)
                if cat and cat.translations:
                    category_names.append(cat.translations[0].name)
            
            return DocumentUploadResponse(
                id=str(document.id),
                title=document.title,
                file_name=standardized_filename,
                file_size=document.file_size,
                mime_type=document.mime_type,
                google_drive_file_id=document.google_drive_file_id,
                processing_status=document.processing_status,
                web_view_link=drive_result.get('web_view_link'),
                created_at=document.created_at
            )

        except ValueError as e:
            session.rollback()
            logger.warning(f"Document upload validation failed: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Document upload error: {e}")
            return None
        finally:
            session.close()

    async def get_document(self, document_id: str, user_id: str) -> Optional[DocumentResponse]:
        """Get document by ID with user access validation"""
        session = db_manager.session_local()
        try:
            stmt = select(Document, Category).outerjoin(Category).where(
                Document.id == document_id,
                Document.user_id == user_id
            )
            result = session.execute(stmt).first()
            
            if not result:
                return None

            document, category = result
            
            return DocumentResponse(
                id=str(document.id),
                title=document.title,
                description=document.description,
                file_name=document.file_name,
                file_size=document.file_size,
                mime_type=document.mime_type,
                google_drive_file_id=document.google_drive_file_id,
                processing_status=document.processing_status,
                extracted_text=document.extracted_text,
                keywords=document.keywords,
                confidence_score=document.confidence_score,
                primary_language=document.primary_language,
                category_id=str(document.category_id) if document.category_id else None,
                category_name=category.name_en if category else None,
                web_view_link=None,
                created_at=document.created_at,
                updated_at=document.updated_at
            )

        except Exception as e:
            logger.error(f"Get document error: {e}")
            return None
        finally:
            session.close()

    async def update_document(
        self,
        document_id: str,
        user_id: str,
        update_request: DocumentUpdateRequest,
        ip_address: str = None
    ) -> Optional[DocumentResponse]:
        """Update document metadata"""
        session = db_manager.session_local()
        try:
            document = session.get(Document, document_id)
            if not document or document.user_id != user_id:
                return None

            old_values = {
                "title": document.title,
                "description": document.description,
                "category_id": str(document.category_id) if document.category_id else None
            }

            update_data = update_request.dict(exclude_unset=True)
            new_values = {}

            for field, value in update_data.items():
                if hasattr(document, field) and value is not None:
                    setattr(document, field, value)
                    new_values[field] = value

            document.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(document)

            await self._log_document_action(
                user_id, "document_update", "document", document_id,
                old_values, new_values, ip_address, session
            )

            return await self.get_document(document_id, user_id)

        except Exception as e:
            logger.error(f"Update document error: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    async def delete_document(self, document_id: str, user_id: str, ip_address: str = None) -> bool:
        """Delete document and remove from Google Drive"""
        session = db_manager.session_local()
        try:
            document = session.get(Document, document_id)
            if not document or document.user_id != user_id:
                return False

            drive_success = await google_drive_service.delete_document(document.google_drive_file_id)
            if not drive_success:
                logger.warning(f"Failed to delete from Google Drive: {document.google_drive_file_id}")

            old_values = {
                "title": document.title,
                "google_drive_file_id": document.google_drive_file_id
            }

            session.delete(document)
            session.commit()

            await self._log_document_action(
                user_id, "document_delete", "document", document_id,
                old_values, {}, ip_address, session
            )

            logger.info(f"Document deleted: {document_id}")
            return True

        except Exception as e:
            logger.error(f"Delete document error: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    async def search_documents(
        self,
        user_id: str,
        search_request: DocumentSearchRequest
    ) -> Optional[DocumentListResponse]:
        """Search documents with filters and pagination"""
        session = db_manager.session_local()
        try:
            page = search_request.page or await self._get_system_setting("default_documents_page_size", 20)
            page_size = search_request.page_size or await self._get_system_setting("default_documents_page_size", 20)
            sort_by = search_request.sort_by or await self._get_system_setting("default_documents_sort_field", "created_at")
            sort_order = search_request.sort_order or await self._get_system_setting("default_documents_sort_order", "desc")

            base_query = select(Document, Category).outerjoin(Category).where(Document.user_id == user_id)

            if search_request.query:
                search_term = f"%{search_request.query}%"
                base_query = base_query.where(
                    or_(
                        Document.title.ilike(search_term),
                        Document.description.ilike(search_term),
                        Document.extracted_text.ilike(search_term),
                        Document.keywords.ilike(search_term)
                    )
                )

            if search_request.category_id:
                base_query = base_query.where(Document.category_id == search_request.category_id)

            if search_request.language:
                base_query = base_query.where(Document.primary_language == search_request.language)

            if search_request.processing_status:
                base_query = base_query.where(Document.processing_status == search_request.processing_status)

            if search_request.date_from:
                base_query = base_query.where(Document.created_at >= search_request.date_from)

            if search_request.date_to:
                base_query = base_query.where(Document.created_at <= search_request.date_to)

            count_stmt = select(func.count()).select_from(base_query.subquery())
            total_count = session.execute(count_stmt).scalar()

            sort_column = getattr(Document, sort_by, Document.created_at)
            if sort_order == "desc":
                sort_column = sort_column.desc()

            offset = (page - 1) * page_size
            documents_stmt = base_query.order_by(sort_column).offset(offset).limit(page_size)
            results = session.execute(documents_stmt).all()

            documents = []
            for document, category in results:
                documents.append(DocumentResponse(
                    id=str(document.id),
                    title=document.title,
                    description=document.description,
                    file_name=document.file_name,
                    file_size=document.file_size,
                    mime_type=document.mime_type,
                    google_drive_file_id=document.google_drive_file_id,
                    processing_status=document.processing_status,
                    extracted_text=document.extracted_text,
                    keywords=document.keywords,
                    confidence_score=document.confidence_score,
                    primary_language=document.primary_language,
                    category_id=str(document.category_id) if document.category_id else None,
                    category_name=category.name_en if category else None,
                    web_view_link=None,
                    created_at=document.created_at,
                    updated_at=document.updated_at
                ))

            total_pages = (total_count + page_size - 1) // page_size

            return DocumentListResponse(
                documents=documents,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )

        except Exception as e:
            logger.error(f"Search documents error: {e}")
            return None
        finally:
            session.close()

    async def get_user_storage_usage(self, user_id: str) -> int:
        """Get total storage usage for user in bytes"""
        session = db_manager.session_local()
        try:
            stmt = select(func.coalesce(func.sum(Document.file_size), 0)).where(Document.user_id == user_id)
            return session.execute(stmt).scalar() or 0

        except Exception as e:
            logger.error(f"Storage usage calculation error: {e}")
            return 0
        finally:
            session.close()

    async def get_storage_info(self, user_id: str, user_tier: str) -> Optional[DocumentStorageInfo]:
        """Get comprehensive storage information for user"""
        session = db_manager.session_local()
        try:
            docs_count_stmt = select(func.count(Document.id)).where(Document.user_id == user_id)
            total_documents = session.execute(docs_count_stmt).scalar() or 0

            total_storage_bytes = await self.get_user_storage_usage(user_id)
            total_storage_mb = total_storage_bytes / (1024 * 1024)

            storage_limit_key = f"storage_limit_{user_tier}_tier_mb"
            storage_limit_mb = await self._get_system_setting(storage_limit_key, 1024)

            storage_usage_percentage = (total_storage_mb / storage_limit_mb * 100) if storage_limit_mb > 0 else 0
            remaining_storage_mb = max(0, storage_limit_mb - total_storage_mb)

            return DocumentStorageInfo(
                total_documents=total_documents,
                total_storage_bytes=total_storage_bytes,
                total_storage_mb=round(total_storage_mb, 2),
                storage_limit_mb=storage_limit_mb,
                storage_usage_percentage=min(100, round(storage_usage_percentage, 2)),
                remaining_storage_mb=round(remaining_storage_mb, 2)
            )

        except Exception as e:
            logger.error(f"Storage info error: {e}")
            return None
        finally:
            session.close()

    async def _log_document_action(
        self, user_id: str, action: str, resource_type: str, resource_id: str,
        old_values: Dict, new_values: Dict, ip_address: str, session: Session
    ):
        """Log document action for audit trail"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                old_values=json.dumps(old_values) if old_values else None,
                new_values=json.dumps(new_values) if new_values else None,
                status="success",
                endpoint="/api/v1/documents"
            )
            session.add(audit_log)
            session.commit()

        except Exception as e:
            logger.error(f"Failed to log document action: {e}")


# Global document service instance
document_service = DocumentService()