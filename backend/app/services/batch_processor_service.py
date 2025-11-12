# backend/app/services/batch_processor_service.py
"""
Bonifatus DMS - Batch Processing Service
Handles asynchronous batch document processing with real-time progress tracking
"""

import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.database.models import UploadBatch
from app.services.document_analysis_service import document_analysis_service

logger = logging.getLogger(__name__)


class BatchProcessorService:
    """
    Service for processing document batches asynchronously

    Features:
    - Background task processing
    - Real-time progress updates
    - Individual file error handling
    - Database-backed status tracking
    """

    def __init__(self):
        self._processing_batches: Dict[str, asyncio.Task] = {}

    async def create_batch(
        self,
        user_id: str,
        total_files: int,
        session: Session
    ) -> str:
        """
        Create a new batch job

        Returns:
            batch_id (str): UUID of the created batch
        """
        batch = UploadBatch(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            total_files=total_files,
            status='pending',
            processed_files=0,
            successful_files=0,
            failed_files=0,
            current_file_index=0,
            results=[]
        )

        session.add(batch)
        session.commit()
        session.refresh(batch)

        logger.info(f"Created batch {batch.id} for user {user_id} with {total_files} files")

        return str(batch.id)

    async def start_batch_processing(
        self,
        batch_id: str,
        files_data: List[Dict],
        user_id: str
    ):
        """
        Start processing a batch in the background

        Args:
            batch_id: UUID of the batch
            files_data: List of {content, filename, mime_type}
            user_id: User ID for the batch
        """
        task = asyncio.create_task(
            self._process_batch(batch_id, files_data, user_id)
        )
        self._processing_batches[batch_id] = task

        logger.info(f"Started background processing for batch {batch_id}")

    async def _process_batch(
        self,
        batch_id: str,
        files_data: List[Dict],
        user_id: str
    ):
        """
        Background task to process all files in a batch
        """
        session = db_manager.session_local()

        try:
            # Update batch status to processing
            batch = session.query(UploadBatch).filter(
                UploadBatch.id == uuid.UUID(batch_id)
            ).first()

            if not batch:
                logger.error(f"Batch {batch_id} not found")
                return

            batch.status = 'processing'
            batch.started_at = datetime.utcnow()
            session.commit()

            results = []

            # Process each file
            for idx, file_data in enumerate(files_data):
                try:
                    # Update current progress
                    batch.current_file_index = idx + 1
                    batch.current_file_name = file_data['filename']
                    session.commit()

                    logger.info(f"[Batch {batch_id}] Processing file {idx+1}/{len(files_data)}: {file_data['filename']}")

                    # Check for duplicates
                    import hashlib
                    from app.database.models import Document
                    from sqlalchemy import and_

                    file_hash = hashlib.sha256(file_data['content']).hexdigest()
                    duplicate = session.query(Document).filter(
                        and_(
                            Document.file_hash == file_hash,
                            Document.user_id == uuid.UUID(user_id),
                            Document.is_deleted == False
                        )
                    ).first()

                    if duplicate:
                        logger.warning(f"[Batch {batch_id}] Duplicate found: {file_data['filename']}")
                        results.append({
                            'success': False,
                            'original_filename': file_data['filename'],
                            'error': f"This document has already been uploaded as '{duplicate.title}' on {duplicate.created_at.strftime('%Y-%m-%d')}",
                            'duplicate_of': {
                                'id': str(duplicate.id),
                                'title': duplicate.title,
                                'filename': duplicate.file_name
                            }
                        })
                        batch.failed_files += 1
                        batch.processed_files += 1
                        session.commit()
                        continue

                    # Analyze document
                    analysis_result = await document_analysis_service.analyze_document(
                        file_content=file_data['content'],
                        file_name=file_data['filename'],
                        mime_type=file_data['mime_type'],
                        db=session,
                        user_id=user_id
                    )

                    results.append({
                        'success': True,
                        'original_filename': file_data['filename'],
                        'document_id': analysis_result['temp_id'],
                        'title': analysis_result['title'],
                        'category': analysis_result.get('category'),
                        'language': analysis_result.get('language')
                    })

                    batch.successful_files += 1
                    batch.processed_files += 1

                    logger.info(f"[Batch {batch_id}] Successfully processed: {file_data['filename']}")

                except Exception as e:
                    logger.error(f"[Batch {batch_id}] Error processing {file_data['filename']}: {e}")
                    results.append({
                        'success': False,
                        'original_filename': file_data['filename'],
                        'error': str(e)
                    })
                    batch.failed_files += 1
                    batch.processed_files += 1

                # Update progress
                batch.results = results
                session.commit()

            # Mark batch as completed
            batch.status = 'completed'
            batch.completed_at = datetime.utcnow()
            batch.current_file_name = None
            session.commit()

            logger.info(f"[Batch {batch_id}] Completed: {batch.successful_files}/{batch.total_files} successful")

        except Exception as e:
            logger.error(f"[Batch {batch_id}] Fatal error: {e}")

            # Mark batch as failed
            batch = session.query(UploadBatch).filter(
                UploadBatch.id == uuid.UUID(batch_id)
            ).first()

            if batch:
                batch.status = 'failed'
                batch.error_message = str(e)
                batch.completed_at = datetime.utcnow()
                session.commit()

        finally:
            session.close()
            # Remove from active tasks
            self._processing_batches.pop(batch_id, None)

    async def get_batch_status(
        self,
        batch_id: str,
        user_id: str,
        session: Session
    ) -> Optional[Dict]:
        """
        Get current status of a batch

        Returns:
            Dictionary with batch status, progress, and results
        """
        try:
            batch = session.query(UploadBatch).filter(
                UploadBatch.id == uuid.UUID(batch_id),
                UploadBatch.user_id == uuid.UUID(user_id)
            ).first()

            if not batch:
                return None

            return {
                'batch_id': str(batch.id),
                'status': batch.status,
                'total_files': batch.total_files,
                'processed_files': batch.processed_files,
                'successful_files': batch.successful_files,
                'failed_files': batch.failed_files,
                'current_file_index': batch.current_file_index,
                'current_file_name': batch.current_file_name,
                'results': batch.results or [],
                'error_message': batch.error_message,
                'created_at': batch.created_at.isoformat() if batch.created_at else None,
                'started_at': batch.started_at.isoformat() if batch.started_at else None,
                'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
                'is_active': batch_id in self._processing_batches
            }
        except Exception as e:
            logger.error(f"Error getting batch status: {e}")
            return None


# Global service instance
batch_processor_service = BatchProcessorService()
