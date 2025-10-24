# backend/app/services/document_upload_service.py
"""
Complete document upload service with Google Drive storage
Production-ready implementation with comprehensive error handling
"""

import logging
import uuid
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.connection import db_manager
from app.database.models import Document, DocumentCategory, Category, User
from app.services.google_drive_service import google_drive_service
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

            # Determine primary category first to get category code for filename
            if primary_category_id:
                if primary_category_id not in category_ids:
                    raise ValueError("Primary category must be in selected categories")
                category_ids_ordered = [primary_category_id] + [
                    cid for cid in category_ids if cid != primary_category_id
                ]
            else:
                category_ids_ordered = category_ids

            # Get category code for standardized filename
            primary_cat_id = category_ids_ordered[0]
            category_code_result = session.execute(
                text("SELECT category_code FROM categories WHERE id = :cat_id"),
                {'cat_id': primary_cat_id}
            ).scalar()
            category_code = category_code_result or 'OTH'

            # Get document date for filename (or None to use current timestamp)
            document_date = analysis_result.get('document_date')

            # Get standardized filename (user may have edited it)
            if custom_filename:
                standardized_filename = custom_filename
            else:
                standardized_filename = self._generate_standardized_filename(
                    original_filename=original_filename,
                    category_code=category_code,
                    document_date=document_date
                )
            
            # Validate filename length
            max_length = await config_service.get_setting('max_filename_length', 200, session)
            if len(standardized_filename) > max_length:
                raise ValueError(f"Filename exceeds maximum length of {max_length} characters")
            
            # Validate filename characters
            if not self._validate_filename(standardized_filename):
                raise ValueError("Filename contains invalid characters")
            
            # Calculate file hash for duplicate detection
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Check for duplicates
            duplicate = session.execute(
                text("""
                    SELECT id, title, filename 
                    FROM documents 
                    WHERE file_hash = :hash 
                    AND user_id = :user_id
                    LIMIT 1
                """),
                {'hash': file_hash, 'user_id': user_id}
            ).first()
            
            if duplicate:
                logger.warning(f"Duplicate document detected: {file_hash} - existing: {duplicate[1]}")
                # Optionally: return duplicate info or continue with upload
                # For now, we'll continue and mark as duplicate
            
            # Validate category count
            max_categories = await config_service.get_setting('max_categories_per_document', 5, session)
            if len(category_ids) > max_categories:
                raise ValueError(f"Maximum {max_categories} categories allowed per document")
            
            # Validate categories exist and user has access
            for cat_id in category_ids_ordered:
                cat_exists = session.execute(
                    text("""
                        SELECT id FROM categories 
                        WHERE id = :cat_id 
                        AND (user_id = :user_id OR is_system = true)
                    """),
                    {'cat_id': cat_id, 'user_id': user_id}
                ).first()
                
                if not cat_exists:
                    raise ValueError(f"Category {cat_id} not found or access denied")
            
            # Upload to Google Drive
            logger.info(f"Uploading to Google Drive: {standardized_filename}")
            drive_result = await google_drive_service.upload_file(
                file_content=file_content,
                filename=standardized_filename,
                mime_type=mime_type,
                user_email=user_email
            )
            
            if not drive_result.get('success'):
                error_msg = drive_result.get('error', 'Unknown error')
                logger.error(f"Google Drive upload failed: {error_msg}")
                raise Exception(f"Google Drive upload failed: {error_msg}")
            
            # Create document record
            document_id = uuid.uuid4()
            
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

            logger.info(f"Creating document record: {document_id}")
            session.execute(
                text("""
                    INSERT INTO documents (
                        id, user_id, title, description, filename, original_filename,
                        file_size, mime_type, file_hash, google_drive_file_id,
                        web_view_link, primary_language, processing_status,
                        document_date, document_date_type, document_date_confidence,
                        is_duplicate, duplicate_of_document_id, batch_id,
                        created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :title, :description, :filename, :original_filename,
                        :file_size, :mime_type, :file_hash, :google_drive_file_id,
                        :web_view_link, :primary_language, :processing_status,
                        :document_date, :document_date_type, :document_date_confidence,
                        :is_duplicate, :duplicate_of, :batch_id,
                        :created_at, :updated_at
                    )
                """),
                {
                    'id': str(document_id),
                    'user_id': user_id,
                    'title': title,
                    'description': description,
                    'filename': standardized_filename,
                    'original_filename': original_filename,
                    'file_size': len(file_content),
                    'mime_type': mime_type,
                    'file_hash': file_hash,
                    'google_drive_file_id': drive_result['file_id'],
                    'web_view_link': drive_result.get('web_view_link'),
                    'primary_language': language_code,
                    'processing_status': 'completed',
                    'document_date': doc_date_value,
                    'document_date_type': doc_date_type,
                    'document_date_confidence': doc_date_confidence / 100.0 if doc_date_confidence else None,
                    'is_duplicate': duplicate is not None,
                    'duplicate_of': str(duplicate[0]) if duplicate else None,
                    'batch_id': batch_id,
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }
            )
            
            # Link categories (with primary designation)
            logger.info(f"Linking {len(category_ids_ordered)} categories")
            for idx, category_id in enumerate(category_ids_ordered):
                is_primary = (idx == 0)
                was_ai_suggested = (category_id == analysis_result.get('suggested_category_id'))
                
                session.execute(
                    text("""
                        INSERT INTO document_categories (
                            id, document_id, category_id, is_primary, assigned_at, assigned_by_ai
                        ) VALUES (
                            :id, :doc_id, :cat_id, :is_primary, :assigned_at, :assigned_by_ai
                        )
                    """),
                    {
                        'id': str(uuid.uuid4()),
                        'doc_id': str(document_id),
                        'cat_id': category_id,
                        'is_primary': is_primary,
                        'assigned_at': datetime.now(timezone.utc),
                        'assigned_by_ai': was_ai_suggested
                    }
                )
            
            # Record ML feedback for category prediction learning
            suggested_category_id = analysis_result.get('suggested_category_id')
            actual_category_id = category_ids_ordered[0]  # Primary category
            matched_keywords = analysis_result.get('matched_keywords', [])
            document_keywords = [kw['word'] for kw in analysis_result.get('keywords', [])]

            logger.info(f"Recording ML feedback: suggested={suggested_category_id}, actual={actual_category_id}")

            # Use new ML learning service
            ml_learning_service.learn_from_decision(
                db=session,
                document_id=document_id,
                suggested_category_id=uuid.UUID(suggested_category_id) if suggested_category_id else None,
                actual_category_id=uuid.UUID(actual_category_id),
                matched_keywords=matched_keywords,
                document_keywords=document_keywords,
                language=language_code,
                confidence=analysis_result.get('classification_confidence', 0) / 100.0 if analysis_result.get('classification_confidence') else None
            )
            
            # Create audit log entry
            session.execute(
                text("""
                    INSERT INTO audit_logs (
                        id, user_id, action, resource_type, resource_id,
                        ip_address, new_values, created_at
                    ) VALUES (
                        :id, :user_id, 'document_uploaded', 'document', :resource_id,
                        null, :new_values, :created_at
                    )
                """),
                {
                    'id': str(uuid.uuid4()),
                    'user_id': user_id,
                    'resource_id': str(document_id),
                    'new_values': f'{{"title": "{title}", "categories": {len(category_ids_ordered)}, "keywords": {len(confirmed_keywords)}}}',
                    'created_at': datetime.now(timezone.utc)
                }
            )
            
            # Commit all changes
            session.commit()
            
            logger.info(f"Document uploaded successfully: {document_id} - {title}")
            
            # Get category names for response
            category_names = []
            for cat_id in category_ids_ordered:
                cat_name = session.execute(
                    text("""
                        SELECT ct.name 
                        FROM category_translations ct
                        JOIN categories c ON c.id = ct.category_id
                        WHERE ct.category_id = :cat_id 
                        AND ct.language_code = :lang
                        LIMIT 1
                    """),
                    {'cat_id': cat_id, 'lang': language_code}
                ).scalar()
                
                if not cat_name:
                    # Fallback to English
                    cat_name = session.execute(
                        text("""
                            SELECT name 
                            FROM category_translations
                            WHERE category_id = :cat_id 
                            AND language_code = 'en'
                            LIMIT 1
                        """),
                        {'cat_id': cat_id}
                    ).scalar()
                
                category_names.append(cat_name or 'Unknown')
            
            # Build success response
            return {
                'success': True,
                'document_id': str(document_id),
                'title': title,
                'filename': standardized_filename,
                'original_filename': original_filename,
                'file_size': len(file_content),
                'category_ids': category_ids_ordered,
                'category_names': category_names,
                'primary_category_id': category_ids_ordered[0],
                'google_drive_file_id': drive_result['file_id'],
                'web_view_link': drive_result.get('web_view_link'),
                'is_duplicate': duplicate is not None,
                'duplicate_of_id': str(duplicate[0]) if duplicate else None,
                'keywords_count': len(confirmed_keywords),
                'language': language_code,
                'created_at': datetime.now(timezone.utc).isoformat()
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
        document_date: Optional[str] = None
    ) -> str:
        """
        Generate standardized filename following naming convention
        Pattern: YYYYMMDD_HHMMSS_CategoryCode_OriginalName.ext
        Example: 20251017_143022_TAX_invoice_2024.pdf

        Args:
            original_filename: Original uploaded filename
            category_code: 3-letter category code (e.g. 'BNK', 'TAX', 'INS')
            document_date: Extracted document date (ISO format) or None for current timestamp

        Returns:
            Standardized filename (max 200 chars)
        """
        # Extract file extension
        extension = original_filename.split('.')[-1] if '.' in original_filename else 'pdf'

        # Clean original filename (remove extension and special chars)
        clean_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        clean_name = re.sub(r'[^\w\s-]', '', clean_name)
        clean_name = re.sub(r'\s+', '_', clean_name.strip())

        # Use document date if available, otherwise current timestamp
        if document_date:
            try:
                from dateutil.parser import parse
                doc_dt = parse(document_date)
                date_prefix = doc_dt.strftime('%Y%m%d')
                time_prefix = datetime.now(timezone.utc).strftime('%H%M%S')
            except:
                date_prefix = datetime.now(timezone.utc).strftime('%Y%m%d')
                time_prefix = datetime.now(timezone.utc).strftime('%H%M%S')
        else:
            now = datetime.now(timezone.utc)
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