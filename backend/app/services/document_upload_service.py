# backend/app/services/document_upload_service.py
"""
Complete document upload service with Google Drive storage
Production-ready implementation with comprehensive error handling
"""

import logging
import json
import uuid as uuid_lib
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database.connection import db_manager
from app.database.models import (
    Document,
    DocumentCategory,
    Category,
    CategoryTranslation,
    User,
    AuditLog
)
from app.services.drive_service import drive_service
from app.services.document_storage_service import document_storage_service
from app.services.ml_learning_service import ml_learning_service
from app.services.config_service import config_service

logger = logging.getLogger(__name__)


class DocumentUploadService:
    """Handles complete document upload workflow"""
    
    async def confirm_upload(
        self,
        temp_id: str,
        temp_data: Dict,
        title: str,
        category_ids: List[str],
        confirmed_keywords: List[str],
        description: Optional[str],
        user_id: str,
        user_email: str,
        language_code: str,
        primary_category_id: Optional[str] = None,
        custom_filename: Optional[str] = None,
        batch_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict:
        """
        Confirm document upload and store permanently
        
        Args:
            temp_id: Temporary upload ID
            temp_data: Temporary storage data from analysis
            title: Document title (user-confirmed)
            category_ids: Selected category IDs (1-5 categories)
            confirmed_keywords: User-confirmed keywords
            description: Optional description
            user_id: User ID
            user_email: User email
            language_code: Document language
            primary_category_id: Explicitly set primary category (optional)
            custom_filename: User-edited filename (optional)
            batch_id: Batch upload ID (optional)
            session: Optional database session
            
        Returns:
            Document upload result with all metadata
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            # Extract data from temp storage
            file_content = temp_data['file_content']
            original_filename = temp_data['file_name']
            mime_type = temp_data['mime_type']
            analysis_result = temp_data['analysis_result']

            # Use detected language from analysis result (more accurate than user preference)
            detected_language = analysis_result.get('detected_language', language_code)
            if detected_language:
                language_code = detected_language
                logger.info(f"[UPLOAD DEBUG] Using detected language: {language_code}")

            # Determine primary category first to get category code for filename
            if primary_category_id:
                if primary_category_id not in category_ids:
                    raise ValueError("Primary category must be in selected categories")
                category_ids_ordered = [primary_category_id] + [
                    cid for cid in category_ids if cid != primary_category_id
                ]
            else:
                category_ids_ordered = category_ids

            # Get category code for standardized filename using ORM
            primary_cat_id = category_ids_ordered[0]
            primary_category = session.query(Category).filter(Category.id == primary_cat_id).first()
            category_code = primary_category.category_code if primary_category else 'OTH'
            logger.info(f"[FILENAME DEBUG] Primary category: {primary_category.reference_key if primary_category else 'None'}, code: {category_code}")

            # Get document date for filename (or None to use current timestamp)
            document_date = analysis_result.get('document_date')
            logger.info(f"[FILENAME DEBUG] Document date: {document_date}")

            # Get user's timezone setting (default to UTC if not set)
            from app.database.models import UserSetting
            timezone_setting = session.query(UserSetting).filter(
                and_(
                    UserSetting.user_id == user_id,
                    UserSetting.setting_key == 'timezone'
                )
            ).first()
            user_timezone = timezone_setting.setting_value if timezone_setting else 'UTC'
            logger.info(f"[FILENAME DEBUG] User timezone: {user_timezone}")

            # Get standardized filename (user may have edited it)
            if custom_filename:
                logger.info(f"[FILENAME DEBUG] Using custom filename: {custom_filename}")
                standardized_filename = custom_filename
            else:
                standardized_filename = self._generate_standardized_filename(
                    original_filename=original_filename,
                    category_code=category_code,
                    document_date=document_date,
                    user_timezone=user_timezone
                )
                logger.info(f"[FILENAME DEBUG] Generated standardized filename: {standardized_filename}")
            
            # Validate filename length
            max_length = await config_service.get_setting('max_filename_length', 200, session)
            if len(standardized_filename) > max_length:
                raise ValueError(f"Filename exceeds maximum length of {max_length} characters")
            
            # Validate filename characters
            if not self._validate_filename(standardized_filename):
                raise ValueError("Filename contains invalid characters")

            # Calculate file hash for storage (duplicate check happens earlier in /analyze endpoint)
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Validate category count
            max_categories = await config_service.get_setting('max_categories_per_document', 5, session)
            if len(category_ids) > max_categories:
                raise ValueError(f"Maximum {max_categories} categories allowed per document")
            
            # Validate categories exist and user has access using ORM
            for cat_id in category_ids_ordered:
                cat_exists = session.query(Category).filter(
                    and_(
                        Category.id == cat_id,
                        or_(
                            Category.user_id == user_id,
                            Category.is_system == True
                        )
                    )
                ).first()

                if not cat_exists:
                    raise ValueError(f"Category {cat_id} not found or access denied")
            
            # Get user and determine active storage provider
            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                logger.error(f"User {user_id} not found")
                raise ValueError("User not found")

            # Determine storage provider (use active_storage_provider or default to google_drive)
            storage_provider = user.active_storage_provider or 'google_drive'

            # Provider-agnostic token field mapping (add new providers here)
            provider_token_fields = {
                'google_drive': 'drive_refresh_token_encrypted',
                'onedrive': 'onedrive_refresh_token_encrypted',
                'dropbox': 'dropbox_refresh_token_encrypted',
                'box': 'box_refresh_token_encrypted'
            }

            # Get the appropriate refresh token based on provider
            token_field = provider_token_fields.get(storage_provider)
            if not token_field:
                raise ValueError(f"Unsupported storage provider: {storage_provider}")

            refresh_token_encrypted = getattr(user, token_field, None)
            if not refresh_token_encrypted:
                provider_display_names = {
                    'google_drive': 'Google Drive',
                    'onedrive': 'OneDrive',
                    'dropbox': 'Dropbox',
                    'box': 'Box'
                }
                provider_name = provider_display_names.get(storage_provider, storage_provider)
                logger.error(f"User {user_email} has not connected {provider_name}")
                raise ValueError(f"Please connect your {provider_name} account in Settings before uploading documents")

            # Get category info for folder structure
            category_translation = session.query(CategoryTranslation).filter(
                and_(
                    CategoryTranslation.category_id == primary_cat_id,
                    CategoryTranslation.language_code == language_code
                )
            ).first()

            category_name = category_translation.name if category_translation else primary_category.reference_key
            category_code_for_folder = primary_category.category_code

            # Get or create category folder using provider-agnostic folder management
            logger.info(f"Ensuring category folder exists: {category_name}")
            folder_map = document_storage_service.initialize_folder_structure(
                user=user,
                folder_names=[category_name],
                db=session
            )

            category_folder_id = folder_map.get(category_name)
            if not category_folder_id:
                logger.warning(f"Failed to get folder ID for category: {category_name}, uploading to root")

            # Upload using centralized document storage service (provider-agnostic)
            logger.info(f"Uploading to {storage_provider}: {standardized_filename} -> {category_name} ({category_code_for_folder})")

            # Convert bytes to BytesIO for upload
            from io import BytesIO
            file_io = BytesIO(file_content)

            # Use document_storage_service for provider-agnostic upload with category folder
            upload_result = document_storage_service.upload_document(
                user=user,
                file_content=file_io,
                filename=standardized_filename,
                mime_type=mime_type,
                db=session,
                folder_id=category_folder_id
            )

            if not upload_result:
                logger.error(f"{storage_provider} upload failed: No result returned")
                raise Exception(f"{storage_provider} upload failed")
            
            # Extract document date information
            doc_date = analysis_result.get('document_date')  # ISO string
            doc_date_type = analysis_result.get('document_date_type')
            doc_date_confidence = analysis_result.get('document_date_confidence')

            # Convert document_date from ISO string to date if available
            doc_date_value = None
            if doc_date:
                try:
                    from dateutil.parser import parse
                    doc_date_value = parse(doc_date).date()
                except:
                    logger.warning(f"Failed to parse document_date: {doc_date}")

            # Prepare keywords for storage (as JSON array of strings)
            keywords_json = json.dumps(confirmed_keywords) if confirmed_keywords else None

            # Create document record using ORM
            document = Document(
                user_id=uuid_lib.UUID(user_id),
                title=title,
                description=description,
                file_name=standardized_filename,
                original_filename=original_filename,
                file_size=len(file_content),
                mime_type=mime_type,
                file_hash=file_hash,
                storage_file_id=upload_result.file_id,
                storage_provider_type=storage_provider,
                web_view_link=getattr(upload_result, 'web_view_link', None),
                primary_language=language_code,
                extracted_text=analysis_result.get('extracted_text'),
                keywords=keywords_json,
                processing_status='completed',
                document_date=doc_date_value,
                document_date_type=doc_date_type,
                document_date_confidence=doc_date_confidence / 100.0 if doc_date_confidence else None,
                is_duplicate=False,
                duplicate_of_document_id=None,
                batch_id=uuid_lib.UUID(batch_id) if batch_id else None,
                is_deleted=False
            )

            session.add(document)
            session.flush()  # Flush to get the document ID for relationships

            logger.info(f"Creating document record: {document.id}")
            
            # Link categories (with primary designation) using ORM
            logger.info(f"Linking {len(category_ids_ordered)} categories")
            for idx, category_id in enumerate(category_ids_ordered):
                is_primary = (idx == 0)
                was_ai_suggested = (category_id == analysis_result.get('suggested_category_id'))

                doc_category = DocumentCategory(
                    document_id=document.id,
                    category_id=uuid_lib.UUID(category_id),
                    is_primary=is_primary,
                    assigned_by_ai=was_ai_suggested
                )
                session.add(doc_category)
            
            # Smart ML learning with multi-category support
            suggested_category_id = analysis_result.get('suggested_category_id')
            primary_category_id = uuid_lib.UUID(category_ids_ordered[0])
            secondary_category_ids = [uuid_lib.UUID(cid) for cid in category_ids_ordered[1:]]  # Categories 2-5
            document_keywords = [kw['word'] for kw in analysis_result.get('keywords', [])]

            logger.info(f"ML Learning: primary={primary_category_id}, secondary={len(secondary_category_ids)}, AI suggested={suggested_category_id}")

            # Use enhanced ML learning service with smart weight calculation
            ml_learning_service.learn_from_classification(
                document_id=document.id,
                document_keywords=document_keywords,
                primary_category_id=primary_category_id,
                secondary_category_ids=secondary_category_ids,
                language=language_code,
                user_id=uuid_lib.UUID(user_id),
                ai_predicted_category=uuid_lib.UUID(suggested_category_id) if suggested_category_id else None,
                ai_confidence=analysis_result.get('classification_confidence', 0) / 100.0 if analysis_result.get('classification_confidence') else None,
                session=session
            )

            # Store extracted entities (people, organizations, addresses)
            entities = analysis_result.get('entities', [])
            if entities:
                logger.info(f"Storing {len(entities)} extracted entities for document {document.id}")
                from app.database.models import DocumentEntity
                for entity in entities:
                    doc_entity = DocumentEntity(
                        document_id=document.id,
                        entity_type=entity['type'],
                        entity_value=entity['value'],
                        confidence=entity['confidence'],
                        extraction_method=entity['method'],
                        language_code=language_code
                    )
                    session.add(doc_entity)

            # Create audit log entry using ORM
            audit_log = AuditLog(
                user_id=uuid_lib.UUID(user_id),
                action='document_uploaded',
                resource_type='document',
                resource_id=document.id,
                new_values=f'{{"title": "{title}", "categories": {len(category_ids_ordered)}, "keywords": {len(confirmed_keywords)}, "entities": {len(entities)}}}',
                status='success'
            )
            session.add(audit_log)
            
            # Commit all changes
            session.commit()
            
            logger.info(f"Document uploaded successfully: {document.id} - {title}")

            # Get category names for response using ORM
            category_names = []
            for cat_id in category_ids_ordered:
                cat_id_uuid = uuid_lib.UUID(cat_id)

                # Try user's language first
                translation = session.query(CategoryTranslation).filter(
                    and_(
                        CategoryTranslation.category_id == cat_id_uuid,
                        CategoryTranslation.language_code == language_code
                    )
                ).first()

                if not translation:
                    # Fallback to English
                    translation = session.query(CategoryTranslation).filter(
                        and_(
                            CategoryTranslation.category_id == cat_id_uuid,
                            CategoryTranslation.language_code == 'en'
                        )
                    ).first()

                category_names.append(translation.name if translation else 'Unknown')

            # Build success response
            return {
                'success': True,
                'document_id': str(document.id),
                'title': title,
                'filename': standardized_filename,
                'original_filename': original_filename,
                'file_size': len(file_content),
                'category_ids': category_ids_ordered,
                'category_names': category_names,
                'primary_category_id': category_ids_ordered[0],
                'google_drive_file_id': drive_result['drive_file_id'],
                'web_view_link': drive_result.get('web_view_link'),
                'keywords_count': len(confirmed_keywords),
                'language': language_code,
                'created_at': document.created_at.isoformat()
            }
            
        except ValueError as e:
            session.rollback()
            logger.error(f"Validation error in document upload: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Document upload failed: {e}", exc_info=True)
            raise
        finally:
            if close_session:
                session.close()
    
    def _generate_standardized_filename(
        self,
        original_filename: str,
        category_code: str,
        document_date: Optional[str] = None,
        user_timezone: str = 'UTC'
    ) -> str:
        """
        Generate standardized filename following naming convention
        Pattern: YYYYMMDD_HHMMSS_CategoryCode_OriginalName.ext
        Example: 20251017_143022_TAX_invoice_2024.pdf

        Args:
            original_filename: Original uploaded filename
            category_code: 3-letter category code (e.g. 'BNK', 'TAX', 'INS')
            document_date: Extracted document date (ISO format) or None for current timestamp
            user_timezone: User's timezone (e.g. 'Europe/Berlin', 'America/New_York')

        Returns:
            Standardized filename (max 200 chars)
        """
        # Import timezone support
        from zoneinfo import ZoneInfo

        # Extract file extension
        extension = original_filename.split('.')[-1] if '.' in original_filename else 'pdf'

        # Clean original filename (remove extension and special chars)
        clean_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename

        # Transliterate Unicode characters to ASCII (ä→a, ü→u, ö→o, ß→ss, etc.)
        import unicodedata
        clean_name = unicodedata.normalize('NFKD', clean_name)
        clean_name = clean_name.encode('ascii', 'ignore').decode('ascii')

        clean_name = re.sub(r'[^\w\s-]', '', clean_name)
        clean_name = re.sub(r'\s+', '_', clean_name.strip())

        # Get user timezone (fallback to UTC if invalid)
        try:
            user_tz = ZoneInfo(user_timezone)
        except Exception:
            logger.warning(f"Invalid timezone '{user_timezone}', using UTC")
            user_tz = timezone.utc

        # Use document date if available, otherwise current timestamp
        if document_date:
            try:
                from dateutil.parser import parse
                doc_dt = parse(document_date)
                date_prefix = doc_dt.strftime('%Y%m%d')
                time_prefix = datetime.now(user_tz).strftime('%H%M%S')
            except:
                date_prefix = datetime.now(user_tz).strftime('%Y%m%d')
                time_prefix = datetime.now(user_tz).strftime('%H%M%S')
        else:
            now = datetime.now(user_tz)
            date_prefix = now.strftime('%Y%m%d')
            time_prefix = now.strftime('%H%M%S')

        # Calculate max length for original name component
        # Format: YYYYMMDD_HHMMSS_CAT_name.ext
        #         8 + 1 + 6 + 1 + 3 + 1 + name + 1 + ext = 21 + name + ext
        fixed_length = len(date_prefix) + 1 + len(time_prefix) + 1 + len(category_code) + 1 + 1 + len(extension)
        max_name_length = 200 - fixed_length

        if len(clean_name) > max_name_length:
            clean_name = clean_name[:max_name_length]

        # Build filename: YYYYMMDD_HHMMSS_CategoryCode_OriginalName.ext
        standardized = f"{date_prefix}_{time_prefix}_{category_code}_{clean_name}.{extension}"

        return standardized

    def _validate_filename(self, filename: str) -> bool:
        """
        Validate filename contains only safe characters
        Allows: alphanumeric, underscore, hyphen, dot
        """
        import string
        allowed_chars = string.ascii_letters + string.digits + '_-.'
        return all(c in allowed_chars for c in filename)


# Global instance
document_upload_service = DocumentUploadService()