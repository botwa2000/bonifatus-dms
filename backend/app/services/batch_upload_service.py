# backend/app/services/batch_upload_service.py
"""
Batch upload service - handle multiple documents efficiently
"""

import logging
import uuid
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.connection import db_manager
from app.services.document_analysis_service import document_analysis_service
from app.services.config_service import config_service

logger = logging.getLogger(__name__)


class BatchUploadService:
    """Handles batch document uploads"""
    
    async def analyze_batch(
        self,
        files_data: List[Dict],
        user_id: str,
        user_categories: List[Dict],
        session: Optional[Session] = None
    ) -> Dict:
        """
        Analyze multiple documents in batch
        
        Args:
            files_data: List of {content, filename, mime_type}
            user_id: User ID
            user_categories: Available categories
            session: Optional database session
            
        Returns:
            Batch analysis results
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            # Create batch record
            batch_id = uuid.uuid4()
            
            session.execute(
                text("""
                    INSERT INTO upload_batches (id, user_id, total_files, status, created_at)
                    VALUES (:id, :user_id, :total, 'processing', :created)
                """),
                {
                    'id': str(batch_id),
                    'user_id': user_id,
                    'total': len(files_data),
                    'created': datetime.now(timezone.utc)
                }
            )
            session.commit()
            
            # Get max concurrent analyses from config
            max_concurrent = await config_service.get_setting(
                'max_concurrent_analyses', 
                default=5, 
                session=session
            )
            
            # Analyze files in parallel (with concurrency limit)
            results = []
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def analyze_with_semaphore(file_data):
                async with semaphore:
                    return await self._analyze_single_file(
                        file_data, user_categories, batch_id, session
                    )
            
            # Create tasks
            tasks = [analyze_with_semaphore(file_data) for file_data in files_data]
            
            # Execute with progress tracking
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                
                # Update batch progress
                session.execute(
                    text("""
                        UPDATE upload_batches 
                        SET processed_files = processed_files + 1,
                            successful_files = successful_files + CASE WHEN :success THEN 1 ELSE 0 END,
                            failed_files = failed_files + CASE WHEN :success THEN 0 ELSE 1 END
                        WHERE id = :batch_id
                    """),
                    {
                        'batch_id': str(batch_id),
                        'success': result['success']
                    }
                )
                session.commit()
            
            # Mark batch as completed
            session.execute(
                text("""
                    UPDATE upload_batches 
                    SET status = 'completed', completed_at = :completed
                    WHERE id = :batch_id
                """),
                {
                    'batch_id': str(batch_id),
                    'completed': datetime.now(timezone.utc)
                }
            )
            session.commit()
            
            logger.info(f"Batch analysis completed: {batch_id} - {len(results)} files")
            
            return {
                'batch_id': str(batch_id),
                'total_files': len(files_data),
                'successful': sum(1 for r in results if r['success']),
                'failed': sum(1 for r in results if not r['success']),
                'results': results
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Batch analysis failed: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    async def _analyze_single_file(
        self,
        file_data: Dict,
        user_categories: List[Dict],
        batch_id: uuid.UUID,
        session: Session
    ) -> Dict:
        """Analyze single file in batch"""
        try:
            analysis = await document_analysis_service.analyze_document(
                file_content=file_data['content'],
                file_name=file_data['filename'],
                mime_type=file_data['mime_type'],
                user_categories=user_categories,
                db=session
            )
            
            # Get category code for filename
            suggested_cat_id = analysis.get('suggested_category_id')
            category_code = "UNC"  # Uncategorized default
            
            if suggested_cat_id:
                cat_match = next((c for c in user_categories if c['id'] == suggested_cat_id), None)
                if cat_match and 'category_code' in cat_match:
                    category_code = cat_match['category_code']
            
            # Use original filename for title (cleaned), not extracted text
            original_base = file_data['filename'].rsplit('.', 1)[0] if '.' in file_data['filename'] else file_data['filename']
            
            # Generate standardized filename
            standardized_filename = self._generate_standardized_filename(
                original_filename=file_data['filename'],
                suggested_title=original_base,  # Use cleaned original filename
                category_code=category_code
            )
            
            temp_id = str(uuid.uuid4())
            
            return {
                'success': True,
                'temp_id': temp_id,
                'original_filename': file_data['filename'],
                'standardized_filename': standardized_filename,
                'analysis': analysis,
                'batch_id': str(batch_id)
            }
            
        except Exception as e:
            logger.error(f"File analysis failed: {file_data['filename']} - {e}")
            return {
                'success': False,
                'original_filename': file_data['filename'],
                'error': str(e),
                'batch_id': str(batch_id)
            }
    
    def _generate_standardized_filename(
        self,
        original_filename: str,
        suggested_title: str,
        category_code: str = "UNC"
    ) -> str:
        """
        Generate standardized filename: YYYYMMDD_CODE_FileName.ext
        Max length: 200 chars
        """
        import re
        from datetime import datetime
        
        # Extract file extension
        extension = original_filename.split('.')[-1] if '.' in original_filename else 'pdf'
        
        # Use original filename base if suggested title is too short
        if not suggested_title or len(suggested_title.strip()) < 5:
            base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
            suggested_title = base_name
        
        # Clean filename - keep only alphanumeric, spaces, hyphens, underscores
        clean_name = re.sub(r'[^\w\s-]', '', suggested_title, flags=re.UNICODE)
        clean_name = re.sub(r'[\s_]+', '_', clean_name.strip())
        clean_name = clean_name.strip('_')
        
        if not clean_name:
            clean_name = "document"
        
        # Date prefix: YYYYMMDD
        date_prefix = datetime.now(timezone.utc).strftime('%Y%m%d')
        
        # Calculate available space: 200 - date(8) - underscores(2) - code(3) - extension
        max_name_length = 200 - 8 - 2 - len(category_code) - len(extension) - 1
        
        # Truncate name if needed
        if len(clean_name) > max_name_length:
            clean_name = clean_name[:max_name_length].rstrip('_')
        
        # Build filename: YYYYMMDD_CODE_FileName.ext
        standardized = f"{date_prefix}_{category_code}_{clean_name}.{extension}"
        
        return standardized


# Global instance
batch_upload_service = BatchUploadService()