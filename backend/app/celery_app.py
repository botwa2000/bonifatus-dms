"""
Celery application for async task processing

This module configures Celery for handling background tasks like document processing.
"""
import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import logging

logger = logging.getLogger(__name__)

# Get Redis URL from environment or use default
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Initialize Celery
celery_app = Celery(
    'bonifatus',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Celery Configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task execution settings
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store more metadata

    # Worker settings
    worker_prefetch_multiplier=1,  # Only fetch 1 task at a time
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,

    # Task routing
    task_routes={
        'app.celery_app.process_batch_task': {'queue': 'document_processing'},
    },

    # Queue settings
    task_default_queue='document_processing',
    task_default_exchange='document_processing',
    task_default_routing_key='document_processing',

    # Retry settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Requeue if worker crashes
)

# Task logging
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log when task starts"""
    logger.info(f"[Celery] Task {task.name}[{task_id}] starting")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """Log when task completes"""
    logger.info(f"[Celery] Task {task.name}[{task_id}] completed with state: {state}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """Log when task fails"""
    logger.error(f"[Celery] Task {sender.name}[{task_id}] failed: {exception}")


@celery_app.task(bind=True, name='app.celery_app.process_batch_task')
def process_batch_task(self, batch_id: str, file_paths: list, user_id: str):
    """
    Celery task for processing document batch

    Args:
        batch_id: UUID of the batch
        file_paths: List of {path, original_filename, mime_type, size, page_count}
        user_id: UUID of the user

    Returns:
        dict: Result summary
    """
    from app.services.batch_processor_service import BatchProcessorService
    from app.database.connection import DatabaseManager
    import asyncio

    logger.info(f"[Celery] Processing batch {batch_id} with {len(file_paths)} files")

    # Update task state to show progress
    self.update_state(
        state='PROCESSING',
        meta={
            'batch_id': batch_id,
            'total_files': len(file_paths),
            'processed_files': 0
        }
    )

    try:
        # Initialize services
        db_manager = DatabaseManager()
        batch_processor = BatchProcessorService(db_manager)

        # Run async batch processing in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Process the batch
            result = loop.run_until_complete(
                batch_processor._process_batch(batch_id, file_paths, user_id)
            )

            logger.info(f"[Celery] Batch {batch_id} completed successfully")

            return {
                'batch_id': batch_id,
                'status': 'completed',
                'total_files': len(file_paths),
                'message': 'Batch processing completed'
            }

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"[Celery] Batch {batch_id} failed: {str(e)}")

        # Update batch status to failed in database
        try:
            from app.database.connection import SessionLocal
            from app.database.models import UploadBatch
            import uuid

            db = SessionLocal()
            batch = db.query(UploadBatch).filter(
                UploadBatch.id == uuid.UUID(batch_id)
            ).first()

            if batch:
                batch.status = 'failed'
                batch.error_message = str(e)
                db.commit()
            db.close()
        except Exception as db_error:
            logger.error(f"[Celery] Failed to update batch status: {str(db_error)}")

        # Re-raise to mark Celery task as failed
        raise


# Helper function to get queue stats
def get_queue_stats():
    """Get current queue statistics"""
    from celery.task.control import inspect

    i = inspect(app=celery_app)

    # Get active tasks
    active = i.active()
    active_count = sum(len(tasks) for tasks in (active or {}).values())

    # Get reserved (queued) tasks
    reserved = i.reserved()
    reserved_count = sum(len(tasks) for tasks in (reserved or {}).values())

    # Get scheduled tasks
    scheduled = i.scheduled()
    scheduled_count = sum(len(tasks) for tasks in (scheduled or {}).values())

    return {
        'active_tasks': active_count,
        'queued_tasks': reserved_count,
        'scheduled_tasks': scheduled_count,
        'total_pending': reserved_count + scheduled_count
    }
