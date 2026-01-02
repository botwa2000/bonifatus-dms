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
        'app.celery_app.migrate_provider_documents_task': {'queue': 'storage_migration'},
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
        batch_processor = BatchProcessorService()

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
    i = celery_app.control.inspect()

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


@celery_app.task(bind=True, name='app.celery_app.migrate_provider_documents_task')
def migrate_provider_documents_task(self, migration_id: str, user_id: str):
    """
    Celery task for migrating documents between cloud storage providers

    Args:
        migration_id: UUID of the MigrationTask
        user_id: UUID of the user

    Returns:
        dict: Migration result summary
    """
    import uuid
    import gc
    from datetime import datetime
    from io import BytesIO
    from app.database.connection import SessionLocal
    from app.database.models import MigrationTask, Document, User, Category, CategoryTranslation
    from sqlalchemy.orm import joinedload
    from app.services.storage.provider_factory import ProviderFactory
    from app.services.provider_manager import ProviderManager

    logger.info(f"[Migration] Starting migration task {migration_id} for user {user_id}")

    db = SessionLocal()
    try:
        # Load migration task
        migration = db.query(MigrationTask).filter(
            MigrationTask.id == uuid.UUID(migration_id)
        ).first()

        if not migration:
            raise ValueError(f"Migration task {migration_id} not found")

        # Load user
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Update status to processing
        migration.status = 'processing'
        migration.started_at = datetime.utcnow()
        migration.celery_task_id = self.request.id
        db.commit()

        # Initialize providers dynamically using ProviderFactory and ProviderManager
        from_provider_type = migration.from_provider
        to_provider_type = migration.to_provider

        # Create provider instances using factory (provider-agnostic)
        from_provider = ProviderFactory.create(from_provider_type)
        to_provider = ProviderFactory.create(to_provider_type)

        # Get tokens using ProviderManager (provider-agnostic)
        from_token = ProviderManager.get_token(db, user, from_provider_type)
        to_token = ProviderManager.get_token(db, user, to_provider_type)

        if not from_token:
            raise ValueError(f"User has not connected source provider: {from_provider_type}")
        if not to_token:
            raise ValueError(f"User has not connected target provider: {to_provider_type}")

        # Query all documents from the old provider
        documents = db.query(Document).filter(
            Document.user_id == uuid.UUID(user_id),
            Document.storage_provider_type == from_provider_type
        ).all()

        migration.total_documents = len(documents)
        db.commit()

        logger.info(f"[Migration] Found {len(documents)} documents to migrate")

        # Initialize folder structure on new provider
        # Helper function to get category name from translations
        def get_category_name(category):
            """Get category name from translations, preferring English"""
            if not category.translations:
                return category.reference_key  # Fallback to reference_key

            # Try to find English translation first
            for trans in category.translations:
                if trans.language_code == 'en':
                    return trans.name

            # If no English translation, use first available
            return category.translations[0].name if category.translations else category.reference_key

        categories = db.query(Category).options(joinedload(Category.translations)).filter(Category.user_id == uuid.UUID(user_id)).all()
        folder_names = [get_category_name(cat) for cat in categories]

        try:
            folder_map = to_provider.initialize_folder_structure(to_token, folder_names)
        except Exception as e:
            logger.error(f"[Migration] Failed to initialize folder structure: {e}")
            migration.status = 'failed'
            migration.error_message = f"Failed to initialize folder structure: {str(e)}"
            migration.completed_at = datetime.utcnow()
            db.commit()
            return {'status': 'failed', 'error': str(e)}

        # Migrate documents one by one
        results = []
        successful_count = 0
        failed_count = 0

        for idx, doc in enumerate(documents):
            migration.processed_documents = idx
            migration.current_document_name = doc.original_filename
            db.commit()

            # Update Celery task state for real-time progress
            self.update_state(
                state='PROCESSING',
                meta={
                    'migration_id': migration_id,
                    'total_documents': migration.total_documents,
                    'processed_documents': idx,
                    'successful_documents': successful_count,
                    'failed_documents': failed_count,
                    'current_document': doc.original_filename
                }
            )

            try:
                # Download from old provider
                logger.info(f"[Migration] Downloading document {doc.id}: {doc.original_filename}")
                file_content = from_provider.download_document(from_token, doc.storage_file_id)

                # Upload to new provider (get folder ID for category)
                category_folder_id = None
                if doc.category_id:
                    category = db.query(Category).options(joinedload(Category.translations)).filter(Category.id == doc.category_id).first()
                    if category:
                        category_name = get_category_name(category)
                        category_folder_id = folder_map.get(category_name)
                        logger.info(f"[Migration] Category '{category_name}' -> folder_id: {category_folder_id}")

                logger.info(f"[Migration] Uploading document to {to_provider_type}: {doc.original_filename}")
                file_stream = BytesIO(file_content)
                upload_result = to_provider.upload_document(
                    to_token,
                    file_stream,
                    doc.original_filename,
                    doc.mime_type,
                    category_folder_id
                )

                # Update document in database
                old_file_id = doc.storage_file_id
                doc.storage_file_id = upload_result.file_id
                doc.storage_provider_type = to_provider_type
                db.commit()

                successful_count += 1
                results.append({
                    'document_id': str(doc.id),
                    'filename': doc.original_filename,
                    'success': True,
                    'old_file_id': old_file_id,
                    'new_file_id': upload_result.file_id
                })

                logger.info(f"[Migration] Successfully migrated: {doc.original_filename}")

                # Memory cleanup
                del file_content
                del file_stream
                gc.collect()

            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                results.append({
                    'document_id': str(doc.id),
                    'filename': doc.original_filename,
                    'success': False,
                    'error': error_msg
                })
                logger.error(f"[Migration] Failed to migrate {doc.original_filename}: {error_msg}")
                # Continue to next document

        # Final counts
        migration.processed_documents = len(documents)
        migration.successful_documents = successful_count
        migration.failed_documents = failed_count
        migration.results = results
        migration.completed_at = datetime.utcnow()

        # Determine final status and handle folder deletion
        if failed_count == 0:
            # All successful - delete old provider folder
            migration.status = 'completed'
            migration.folder_deletion_attempted = True

            try:
                deletion_result = from_provider.delete_app_folder(from_token)
                migration.folder_deleted = deletion_result['success']
                if not deletion_result['success']:
                    migration.folder_deletion_error = deletion_result['message']
                logger.info(f"[Migration] Folder deletion result: {deletion_result}")
            except Exception as e:
                migration.folder_deletion_error = str(e)
                logger.error(f"[Migration] Folder deletion failed: {e}")

            # Disconnect old provider using ProviderManager (provider-agnostic)
            success = ProviderManager.disconnect_provider(db, user, from_provider_type)
            if success:
                logger.info(f"[Migration] Disconnected old provider: {from_provider_type}")
            else:
                logger.warning(f"[Migration] Old provider {from_provider_type} was already disconnected")

        elif failed_count == len(documents):
            # All failed - disconnect the new provider (rollback connection)
            migration.status = 'failed'
            migration.error_message = "All documents failed to migrate"

            logger.warning(f"[Migration] All documents failed - disconnecting new provider: {to_provider_type}")
            success = ProviderManager.disconnect_provider(db, user, to_provider_type)
            if success:
                logger.info(f"[Migration] Disconnected new provider {to_provider_type} after migration failure")
            else:
                logger.warning(f"[Migration] Failed to disconnect new provider {to_provider_type}")
        else:
            # Partial success
            migration.status = 'partial'

        db.commit()

        logger.info(f"[Migration] Migration {migration_id} completed: {successful_count} successful, {failed_count} failed")

        # Send email notification (in separate session to prevent rollback)
        try:
            from app.services.email_service import email_service
            _send_migration_email(user.email, user.full_name, migration, user.email_marketing_enabled)
        except Exception as e:
            logger.error(f"[Migration] Failed to send email notification: {e}")

        return {
            'migration_id': migration_id,
            'status': migration.status,
            'total_documents': migration.total_documents,
            'successful_documents': successful_count,
            'failed_documents': failed_count,
            'folder_deleted': migration.folder_deleted
        }

    except Exception as e:
        logger.error(f"[Migration] Migration {migration_id} failed: {str(e)}")

        # Update migration status to failed and disconnect new provider (rollback)
        try:
            migration.status = 'failed'
            migration.error_message = str(e)
            migration.completed_at = datetime.utcnow()
            db.commit()

            # Disconnect new provider since migration failed
            logger.warning(f"[Migration] Migration failed - disconnecting new provider: {to_provider_type}")
            success = ProviderManager.disconnect_provider(db, user, to_provider_type)
            if success:
                logger.info(f"[Migration] Disconnected new provider {to_provider_type} after migration exception")
            else:
                logger.warning(f"[Migration] Failed to disconnect new provider {to_provider_type}")
        except Exception as db_error:
            logger.error(f"[Migration] Failed to update migration status: {str(db_error)}")

        raise

    finally:
        db.close()


def _send_migration_email(user_email: str, user_name: str, migration: 'MigrationTask', marketing_enabled: bool):
    """
    Send migration completion email in a separate database session.

    Args:
        user_email: User's email address
        user_name: User's full name
        migration: MigrationTask instance
        marketing_enabled: Whether user accepts marketing emails
    """
    from app.services.email_service import email_service
    from app.database.connection import SessionLocal

    email_session = SessionLocal()
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if migration.status == 'completed':
                template_name = 'migration_completed'
            elif migration.status == 'partial':
                template_name = 'migration_partial'
            else:
                template_name = 'migration_failed'

            from app.core.config import settings
            dashboard_url = f"{settings.app.app_frontend_url}/settings"

            loop.run_until_complete(
                email_service.send_migration_notification(
                    session=email_session,
                    to_email=user_email,
                    user_name=user_name,
                    template_name=template_name,
                    from_provider=migration.from_provider,
                    to_provider=migration.to_provider,
                    successful_count=migration.successful_documents,
                    failed_count=migration.failed_documents,
                    total_count=migration.total_documents,
                    dashboard_url=dashboard_url,
                    error_message=migration.error_message or '',
                    user_can_receive_marketing=marketing_enabled
                )
            )
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"[Migration] Email sending failed: {e}")
    finally:
        email_session.close()
