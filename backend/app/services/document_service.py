# backend/app/services/document_service.py
"""
Bonifatus DMS - Document Management Service
Business logic for document operations with database-driven configuration
"""

import logging
import json
import mimetypes
import uuid
from uuid import UUID
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text, and_, or_

from app.database.models import Document, Category, DocumentCategory, CategoryTranslation, User, AuditLog, SystemSetting, UserSetting
from app.database.connection import db_manager
from app.services.drive_service import drive_service
from app.services.document_storage_service import document_storage_service
from app.services.provider_manager import ProviderManager
from app.services.tier_service import tier_service
from app.core.config import settings
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

    def _get_user_language(self, user_id: str, session: Session) -> str:
        """Get user's preferred interface language from settings"""
        try:
            user_setting = session.execute(
                select(UserSetting).where(
                    UserSetting.user_id == user_id,
                    UserSetting.setting_key == 'language'
                )
            ).scalar_one_or_none()

            if user_setting:
                return user_setting.setting_value

            # Default to English if not set
            return 'en'
        except Exception as e:
            logger.warning(f"Failed to get user language, defaulting to 'en': {e}")
            return 'en'

    def _get_document_categories(self, document_id: UUID, user_language: str, session: Session) -> List[Dict[str, any]]:
        """
        Get all categories for a document from junction table
        Returns list of category dicts with id, name, is_primary
        """
        from app.database.models import DocumentCategory
        from app.schemas.document_schemas import CategoryInfo

        try:
            # Query all categories for this document through junction table
            stmt = (
                select(DocumentCategory, Category, CategoryTranslation)
                .join(Category, Category.id == DocumentCategory.category_id)
                .outerjoin(CategoryTranslation, and_(
                    CategoryTranslation.category_id == Category.id,
                    CategoryTranslation.language_code == user_language
                ))
                .where(DocumentCategory.document_id == document_id)
                .order_by(DocumentCategory.is_primary.desc(), Category.reference_key)
            )

            results = session.execute(stmt).all()

            categories = []
            for doc_cat, category, category_translation in results:
                # Use translated name if available, otherwise fallback to English
                category_name = None
                if category_translation and category_translation.name:
                    category_name = category_translation.name
                else:
                    # Fallback to English translation
                    en_translation = session.execute(
                        select(CategoryTranslation).where(
                            CategoryTranslation.category_id == category.id,
                            CategoryTranslation.language_code == 'en'
                        )
                    ).scalar_one_or_none()
                    if en_translation:
                        category_name = en_translation.name
                    else:
                        category_name = category.reference_key  # Last resort

                categories.append({
                    "id": str(category.id),
                    "name": category_name,
                    "is_primary": doc_cat.is_primary
                })

            return categories

        except Exception as e:
            logger.error(f"Failed to get document categories: {e}")
            return []

    def _parse_keywords_to_list(self, keywords_str: Optional[str]) -> Optional[list]:
        """Parse keywords string to list of KeywordItem dicts"""
        if not keywords_str:
            return None

        try:
            # Try parsing as JSON first
            keywords_data = json.loads(keywords_str)
            if isinstance(keywords_data, list):
                return [
                    {"keyword": kw, "relevance": 1.0} if isinstance(kw, str)
                    else {"keyword": kw.get("keyword", ""), "relevance": kw.get("relevance", 1.0)}
                    for kw in keywords_data
                ]
        except (json.JSONDecodeError, ValueError):
            # If not JSON, try comma-separated string
            keywords_list = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            return [{"keyword": kw, "relevance": 1.0} for kw in keywords_list]

        return None

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

            # Get user object for provider-agnostic upload
            user = session.get(User, uuid.UUID(user_id))
            if not user:
                raise ValueError("User not found")

            # Check if any storage provider is connected
            # Uses ProviderManager to ensure consistency with provider_connections table
            if not ProviderManager.get_active_provider(session, user):
                raise ValueError("Please connect a storage provider in Settings before uploading documents")

            # Upload using centralized document storage service (provider-agnostic)
            upload_result = document_storage_service.upload_document(
                user=user,
                file_content=file_content,
                filename=standardized_filename,
                mime_type=mime_type,
                db=session
            )

            if not upload_result:
                raise Exception(f"Failed to upload to {user.active_storage_provider}")

            document_title = title or filename.rsplit('.', 1)[0]

            document = Document(
                title=document_title,
                description=description,
                file_name=standardized_filename,
                file_size=file_size,
                mime_type=mime_type,
                storage_file_id=upload_result.file_id,
                storage_provider_type=user.active_storage_provider,
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
                google_drive_file_id=document.storage_file_id,
                processing_status=document.processing_status,
                web_view_link=getattr(upload_result, 'web_view_link', None),
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
        """Get document by ID with user access validation (supports delegate access)"""
        session = db_manager.session_local()
        try:
            # Get user's preferred language
            user_language = self._get_user_language(user_id, session)

            # Query document with category using document_categories junction table (same as list view)
            from app.database.models import DocumentCategory
            stmt = (
                select(Document, Category, CategoryTranslation)
                .outerjoin(DocumentCategory, and_(
                    DocumentCategory.document_id == Document.id,
                    DocumentCategory.is_primary == True
                ))
                .outerjoin(Category, Category.id == DocumentCategory.category_id)
                .outerjoin(CategoryTranslation, and_(
                    CategoryTranslation.category_id == Category.id,
                    CategoryTranslation.language_code == user_language
                ))
                .where(
                    Document.id == document_id,
                    Document.user_id == user_id
                )
            )
            result = session.execute(stmt).first()

            # If document not found as owner, check if user has delegate access
            if not result:
                # Try to get document without user_id filter
                stmt_no_filter = (
                    select(Document, Category, CategoryTranslation)
                    .outerjoin(DocumentCategory, and_(
                        DocumentCategory.document_id == Document.id,
                        DocumentCategory.is_primary == True
                    ))
                    .outerjoin(Category, Category.id == DocumentCategory.category_id)
                    .outerjoin(CategoryTranslation, and_(
                        CategoryTranslation.category_id == Category.id,
                        CategoryTranslation.language_code == user_language
                    ))
                    .where(Document.id == document_id)
                )
                result = session.execute(stmt_no_filter).first()

                if not result:
                    logger.warning(f"[GET_DOCUMENT DEBUG] Document {document_id} does not exist")
                    return None

                # Check delegate access
                document_temp, _, _ = result
                from app.services.delegate_service import delegate_service
                from uuid import UUID
                has_access, role = await delegate_service.check_access(
                    delegate_user_id=UUID(user_id),
                    owner_user_id=UUID(str(document_temp.user_id))
                )

                if not has_access:
                    logger.warning(f"[GET_DOCUMENT DEBUG] User {user_id} has no access to document {document_id} owned by {document_temp.user_id}")
                    return None

                logger.info(f"[GET_DOCUMENT DEBUG] User {user_id} accessing shared document {document_id} as delegate (role: {role})")

            document, category, category_translation = result

            # Get category name from translation
            category_name = None
            if category_translation and category_translation.name:
                category_name = category_translation.name
            elif category:
                # Fallback to English if user's language not available
                en_translation = session.execute(
                    select(CategoryTranslation).where(
                        CategoryTranslation.category_id == category.id,
                        CategoryTranslation.language_code == 'en'
                    )
                ).scalar_one_or_none()
                if en_translation:
                    category_name = en_translation.name
                else:
                    category_name = category.reference_key  # Last resort fallback

            # Parse keywords
            parsed_keywords = self._parse_keywords_to_list(document.keywords)

            # Get all categories for this document
            all_categories = self._get_document_categories(document.id, user_language, session)

            # Get extracted entities
            from app.database.models import DocumentEntity
            from app.schemas.document_schemas import EntityItem
            entities_query = session.execute(
                select(DocumentEntity).where(DocumentEntity.document_id == document.id)
            ).scalars().all()

            parsed_entities = [
                EntityItem(
                    type=entity.entity_type,
                    value=entity.entity_value,
                    confidence=entity.confidence,
                    method=entity.extraction_method
                )
                for entity in entities_query
            ] if entities_query else None

            logger.info(f"[GET_DOCUMENT DEBUG] Document {document_id}:")
            logger.info(f"  - title: {document.title}")
            logger.info(f"  - category_id (from junction table): {category.id if category else None}")
            logger.info(f"  - category_name: {category_name}")
            logger.info(f"  - all_categories: {len(all_categories)} categories")
            logger.info(f"  - user_language: {user_language}")
            logger.info(f"  - keywords (raw): {document.keywords[:200] if document.keywords else 'None'}")
            logger.info(f"  - keywords (parsed count): {len(parsed_keywords) if parsed_keywords else 0}")
            logger.info(f"  - processing_status: {document.processing_status}")
            logger.info(f"  - primary_language: {document.primary_language}")

            # DEBUG: Log entities being returned
            if parsed_entities:
                logger.info(f"  - entities (count): {len(parsed_entities)}")
                entity_by_type = {}
                for e in parsed_entities:
                    if e.type not in entity_by_type:
                        entity_by_type[e.type] = []
                    entity_by_type[e.type].append(f"{e.value} ({e.confidence:.2f})")
                for entity_type, values in entity_by_type.items():
                    logger.info(f"    {entity_type}: {values}")
            else:
                logger.info(f"  - entities: None")

            return DocumentResponse(
                id=str(document.id),
                title=document.title,
                description=document.description,
                file_name=document.file_name,
                file_size=document.file_size,
                mime_type=document.mime_type,
                google_drive_file_id=document.storage_file_id,
                processing_status=document.processing_status,
                extracted_text=document.extracted_text,
                keywords=parsed_keywords,
                entities=parsed_entities,
                confidence_score=document.confidence_score,
                primary_language=document.primary_language,
                category_id=str(category.id) if category else None,
                category_name=category_name,
                categories=all_categories,
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
            # Convert string UUID to UUID object for session.get()
            try:
                doc_uuid = uuid.UUID(document_id)
            except ValueError:
                logger.warning(f"Invalid document ID format: {document_id}")
                return None

            document = session.get(Document, doc_uuid)
            if not document:
                return None

            # Convert user_id string to UUID for comparison
            try:
                user_uuid = uuid.UUID(user_id)
            except ValueError:
                logger.warning(f"Invalid user ID format: {user_id}")
                return None

            if document.user_id != user_uuid:
                return None

            old_values = {
                "title": document.title,
                "description": document.description,
                "keywords": document.keywords
            }

            update_data = update_request.dict(exclude_unset=True)
            new_values = {}

            # Special handling for categories - update junction table
            # Support both category_ids (new) and category_id (backward compat)
            category_ids_to_set = None
            if 'category_ids' in update_data and update_data['category_ids']:
                category_ids_to_set = update_data['category_ids']
                del update_data['category_ids']
            elif 'category_id' in update_data and update_data['category_id'] is not None:
                category_ids_to_set = [update_data['category_id']]
                del update_data['category_id']

            if category_ids_to_set:
                from app.database.models import DocumentCategory, User

                # Get old primary category before making changes
                old_primary_category = session.query(DocumentCategory).filter(
                    DocumentCategory.document_id == doc_uuid,
                    DocumentCategory.is_primary == True
                ).first()
                old_primary_id = str(old_primary_category.category_id) if old_primary_category else None

                logger.info(f"[UPDATE DEBUG] Updating categories for document {document_id}")
                logger.info(f"[UPDATE DEBUG] Old primary category: {old_primary_id}")
                logger.info(f"[UPDATE DEBUG] New categories: {category_ids_to_set}")

                # Remove old category assignments
                session.query(DocumentCategory).filter(
                    DocumentCategory.document_id == doc_uuid
                ).delete()

                # Add new category assignments (first is primary)
                try:
                    for idx, cat_id in enumerate(category_ids_to_set):
                        cat_uuid = uuid.UUID(cat_id)
                        is_primary = (idx == 0)

                        new_assignment = DocumentCategory(
                            document_id=doc_uuid,
                            category_id=cat_uuid,
                            is_primary=is_primary,
                            assigned_at=datetime.utcnow()
                        )
                        session.add(new_assignment)

                        if is_primary:
                            # Update backward-compatibility field
                            document.category_id = cat_uuid
                            new_primary_id = cat_id

                    new_values['category_ids'] = category_ids_to_set
                    logger.info(f"[UPDATE DEBUG] ✅ Categories updated: {len(category_ids_to_set)} assigned")

                    # Move file in Google Drive if primary category changed
                    if old_primary_id and old_primary_id != new_primary_id:
                        logger.info(f"[DRIVE MOVE] Primary category changed, moving file in Google Drive")
                        try:
                            # Get user's refresh token and main folder
                            user = session.get(User, user_uuid)
                            if user and user.google_refresh_token:
                                # Get new primary category info
                                new_category = session.get(Category, uuid.UUID(new_primary_id))
                                if new_category:
                                    # Get category folder ID
                                    new_folder_id = drive_service.get_or_create_category_folder(
                                        user.google_refresh_token,
                                        new_category.name,
                                        new_category.reference_key,
                                        user.google_drive_folder_id
                                    )

                                    # Move file to new category folder
                                    success = drive_service.move_document_to_folder(
                                        user.google_refresh_token,
                                        document.storage_file_id,
                                        new_folder_id
                                    )

                                    if success:
                                        logger.info(f"[DRIVE MOVE] ✅ File moved to {new_category.name} folder")
                                    else:
                                        logger.warning(f"[DRIVE MOVE] ⚠️ Failed to move file in Drive")
                            else:
                                logger.warning(f"[DRIVE MOVE] ⚠️ User refresh token not available")
                        except Exception as e:
                            logger.error(f"[DRIVE MOVE] ❌ Error moving file in Drive: {e}")

                except ValueError as e:
                    logger.error(f"[UPDATE DEBUG] ❌ Invalid category ID format: {e}")

            # Handle other fields
            for field, value in update_data.items():
                if hasattr(document, field) and value is not None:
                    # Special handling for keywords: convert list to JSON string
                    if field == 'keywords':
                        value = json.dumps(value)
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
        logger.info(f"[DELETE DEBUG] === Document Deletion Started ===")
        logger.info(f"[DELETE DEBUG] Document ID (raw): {document_id}")
        logger.info(f"[DELETE DEBUG] Document ID type: {type(document_id)}")
        logger.info(f"[DELETE DEBUG] User ID: {user_id}")

        session = db_manager.session_local()
        try:
            # Convert string UUID to UUID object for session.get()
            try:
                doc_uuid = uuid.UUID(document_id)
                logger.info(f"[DELETE DEBUG] Converted to UUID object: {doc_uuid}")
                logger.info(f"[DELETE DEBUG] UUID type: {type(doc_uuid)}")
            except ValueError as e:
                logger.error(f"[DELETE DEBUG] ❌ Invalid document ID format: {document_id}, error: {e}")
                return False

            logger.info(f"[DELETE DEBUG] Querying document with UUID: {doc_uuid}")
            document = session.get(Document, doc_uuid)

            if not document:
                logger.error(f"[DELETE DEBUG] ❌ Document not found in database: {doc_uuid}")
                return False

            logger.info(f"[DELETE DEBUG] ✅ Document found: {document.title}")
            logger.info(f"[DELETE DEBUG] Document user_id: {document.user_id}, Request user_id: {user_id}")
            logger.info(f"[DELETE DEBUG] Document user_id type: {type(document.user_id)}, Request user_id type: {type(user_id)}")

            # Convert user_id string to UUID for comparison
            try:
                user_uuid = uuid.UUID(user_id)
            except ValueError:
                logger.error(f"[DELETE DEBUG] ❌ Invalid user ID format: {user_id}")
                return False

            if document.user_id != user_uuid:
                logger.error(f"[DELETE DEBUG] ❌ User ID mismatch - document belongs to {document.user_id}, not {user_uuid}")
                return False

            logger.info(f"[DELETE DEBUG] ✅ User ID matches, proceeding with deletion")

            # Get user object for provider-agnostic deletion
            logger.info(f"[DELETE DEBUG] Fetching user object...")
            user = session.get(User, user_uuid)

            if user and user.active_storage_provider:
                logger.info(f"[DELETE DEBUG] User has active storage provider ({user.active_storage_provider}), deleting from storage...")
                try:
                    storage_success = document_storage_service.delete_document(
                        user=user,
                        file_id=document.storage_file_id,
                        db=session,
                        provider_type=document.storage_provider_type
                    )
                    if not storage_success:
                        logger.warning(f"[DELETE DEBUG] ⚠️  Failed to delete from {document.storage_provider_type}: {document.storage_file_id}")
                    else:
                        logger.info(f"[DELETE DEBUG] ✅ Deleted from {document.storage_provider_type}: {document.storage_file_id}")
                except Exception as e:
                    logger.warning(f"[DELETE DEBUG] ⚠️  Error deleting from storage: {e}")
            else:
                logger.warning(f"[DELETE DEBUG] ⚠️  User {user_id} has no active storage provider, skipping storage deletion")

            old_values = {
                "title": document.title,
                "storage_file_id": document.storage_file_id
            }

            # Store file size before deletion for quota update
            file_size = document.file_size

            logger.info(f"[DELETE DEBUG] Deleting document from database...")
            session.delete(document)
            session.commit()
            logger.info(f"[DELETE DEBUG] ✅ Document deleted from database")

            # NOTE: Monthly usage is NOT decremented on deletion
            # Monthly usage tracks consumption for the month, not current storage
            # Deleting documents does not reduce monthly page/volume consumption
            logger.info(f"[DELETE DEBUG] Document deleted (monthly usage not affected)")

            await self._log_document_action(
                user_id, "document_delete", "document", document_id,
                old_values, {}, ip_address, session
            )

            logger.info(f"[DELETE DEBUG] ✅✅✅ Document deletion completed successfully: {document_id}")
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
            # Get user's preferred language
            user_language = self._get_user_language(user_id, session)

            page = search_request.page or await self._get_system_setting("default_documents_page_size", 20)
            page_size = search_request.page_size or await self._get_system_setting("default_documents_page_size", 20)
            sort_by = search_request.sort_by or await self._get_system_setting("default_documents_sort_field", "created_at")
            sort_order = search_request.sort_order or await self._get_system_setting("default_documents_sort_order", "desc")

            # Join through document_categories to get the primary category
            # This supports the many-to-many relationship
            base_query = (
                select(Document, Category, CategoryTranslation)
                .outerjoin(DocumentCategory, and_(
                    DocumentCategory.document_id == Document.id,
                    DocumentCategory.is_primary == True
                ))
                .outerjoin(Category, Category.id == DocumentCategory.category_id)
                .outerjoin(CategoryTranslation, and_(
                    CategoryTranslation.category_id == Category.id,
                    CategoryTranslation.language_code == 'en'  # TODO: Use user's language preference
                ))
                .where(Document.user_id == user_id)
                .where(Document.is_deleted == False)
            )

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
                # Filter by documents that have this category using EXISTS subquery
                # This avoids joining document_categories twice
                from sqlalchemy.sql import exists
                try:
                    category_uuid = uuid.UUID(search_request.category_id)
                    logger.info(f"[CATEGORY FILTER] Applying category filter for category_id: {category_uuid}")
                    category_filter = exists(
                        select(1).select_from(DocumentCategory).where(
                            and_(
                                DocumentCategory.document_id == Document.id,
                                DocumentCategory.category_id == category_uuid
                            )
                        )
                    ).correlate(Document)
                    base_query = base_query.where(category_filter)
                    logger.info(f"[CATEGORY FILTER] Category filter applied successfully")
                except ValueError:
                    logger.warning(f"[CATEGORY FILTER] Invalid category_id format: {search_request.category_id}")

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

            if search_request.category_id:
                logger.info(f"[CATEGORY FILTER] Found {total_count} documents matching category filter")

            sort_column = getattr(Document, sort_by, Document.created_at)
            if sort_order == "desc":
                sort_column = sort_column.desc()

            offset = (page - 1) * page_size
            documents_stmt = base_query.order_by(sort_column).offset(offset).limit(page_size)
            results = session.execute(documents_stmt).all()

            documents = []
            for document, category, category_translation in results:
                # Use translated category name if available, otherwise fallback to category reference_key
                category_name = None
                if category_translation and category_translation.name:
                    category_name = category_translation.name
                elif category:
                    category_name = category.reference_key  # Fallback to reference key

                # Get all categories for this document
                all_categories = self._get_document_categories(document.id, user_language, session)

                documents.append(DocumentResponse(
                    id=str(document.id),
                    title=document.title,
                    description=document.description,
                    file_name=document.file_name,
                    file_size=document.file_size,
                    mime_type=document.mime_type,
                    google_drive_file_id=document.storage_file_id,
                    processing_status=document.processing_status,
                    extracted_text=document.extracted_text,
                    keywords=self._parse_keywords_to_list(document.keywords),
                    confidence_score=document.confidence_score,
                    primary_language=document.primary_language,
                    category_id=str(category.id) if category else None,
                    category_name=category_name,
                    categories=all_categories,
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

    async def search_documents_multi_source(
        self,
        current_user: User,
        search_request: DocumentSearchRequest,
        include_own: bool = True,
        shared_owner_ids: List[str] = []
    ) -> Optional[DocumentListResponse]:
        """
        Search documents from multiple sources (own + shared from delegates)

        Args:
            current_user: The current authenticated user
            search_request: Search filters and pagination
            include_own: Whether to include user's own documents
            shared_owner_ids: List of owner user IDs to fetch shared documents from

        Returns:
            Unified document list with owner metadata and permissions
        """
        from app.services.delegate_service import delegate_service

        all_documents = []
        total_from_sources = 0

        try:
            # Fetch own documents if requested
            if include_own:
                logger.info(f"[MULTI-SOURCE] Fetching own documents for user {current_user.id}")
                own_docs = await self.search_documents(str(current_user.id), search_request)

                if own_docs and own_docs.documents:
                    for doc in own_docs.documents:
                        # Add owner metadata for own documents
                        doc.owner_type = "own"
                        doc.owner_user_id = str(current_user.id)
                        doc.owner_name = current_user.full_name
                        doc.can_edit = True
                        doc.can_delete = True

                    all_documents.extend(own_docs.documents)
                    total_from_sources += own_docs.total_count
                    logger.info(f"[MULTI-SOURCE] Found {len(own_docs.documents)} own documents")

            # Fetch shared documents from each owner
            for owner_id in shared_owner_ids:
                try:
                    owner_uuid = UUID(owner_id)

                    # Validate delegate has active access to this owner
                    has_access, role = await delegate_service.check_access(
                        delegate_user_id=current_user.id,
                        owner_user_id=owner_uuid
                    )

                    if not has_access:
                        logger.warning(f"[MULTI-SOURCE] User {current_user.id} does not have access to owner {owner_id}")
                        continue

                    logger.info(f"[MULTI-SOURCE] Fetching shared documents from owner {owner_id} (role: {role})")
                    if settings.is_development and search_request.category_id:
                        logger.info(f"[MULTI-SOURCE] Category filter active: {search_request.category_id}")

                    # Fetch owner's documents
                    shared_docs = await self.search_documents(owner_id, search_request)

                    if settings.is_development and search_request.category_id:
                        doc_count = len(shared_docs.documents) if shared_docs else 0
                        logger.info(f"[MULTI-SOURCE] Found {doc_count} shared documents from owner {owner_id} matching category filter")

                    if shared_docs and shared_docs.documents:
                        # Get owner details for metadata
                        session = db_manager.session_local()
                        try:
                            owner_user = session.query(User).filter(User.id == owner_uuid).first()
                            owner_name = owner_user.full_name if owner_user else "Unknown Owner"
                        finally:
                            session.close()

                        # Add owner metadata for shared documents
                        for doc in shared_docs.documents:
                            doc.owner_type = "shared"
                            doc.owner_user_id = owner_id
                            doc.owner_name = owner_name
                            # Delegates with 'viewer' role cannot edit or delete
                            doc.can_edit = False if role == 'viewer' else True
                            doc.can_delete = False

                        all_documents.extend(shared_docs.documents)
                        total_from_sources += shared_docs.total_count
                        logger.info(f"[MULTI-SOURCE] Found {len(shared_docs.documents)} shared documents from owner {owner_id}")

                except ValueError:
                    logger.error(f"[MULTI-SOURCE] Invalid owner ID format: {owner_id}")
                    continue
                except Exception as e:
                    logger.error(f"[MULTI-SOURCE] Error fetching documents from owner {owner_id}: {e}")
                    continue

            # Sort combined results
            # By default, sort by created_at desc
            sort_by = search_request.sort_by or "created_at"
            sort_order = search_request.sort_order or "desc"

            if sort_by == "created_at":
                all_documents.sort(
                    key=lambda x: x.created_at if x.created_at else datetime.min,
                    reverse=(sort_order == "desc")
                )
            elif sort_by == "title":
                all_documents.sort(
                    key=lambda x: x.title.lower() if x.title else "",
                    reverse=(sort_order == "desc")
                )
            elif sort_by == "file_size":
                all_documents.sort(
                    key=lambda x: x.file_size if x.file_size else 0,
                    reverse=(sort_order == "desc")
                )
            elif sort_by == "category_name":
                all_documents.sort(
                    key=lambda x: x.category_name.lower() if x.category_name else "zzz",
                    reverse=(sort_order == "desc")
                )
            elif sort_by == "mime_type":
                all_documents.sort(
                    key=lambda x: x.mime_type.lower() if x.mime_type else "zzz",
                    reverse=(sort_order == "desc")
                )

            # Apply pagination to combined results
            page = search_request.page or 1
            page_size = search_request.page_size or 20

            total_count = len(all_documents)
            offset = (page - 1) * page_size
            paginated_documents = all_documents[offset:offset + page_size]

            total_pages = (total_count + page_size - 1) // page_size

            logger.info(f"[MULTI-SOURCE] Returning {len(paginated_documents)} documents (page {page}/{total_pages}, total: {total_count})")

            return DocumentListResponse(
                documents=paginated_documents,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )

        except Exception as e:
            logger.error(f"[MULTI-SOURCE] Error searching multi-source documents: {e}")
            return None

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