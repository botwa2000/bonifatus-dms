"""
Email Polling Background Task
Periodically polls IMAP inbox for new emails and processes them
"""

import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.database.connection import db_manager
from app.services.email_processing_service import EmailProcessingService

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def poll_emails_task():
    """
    Background task to poll for new emails
    Runs periodically based on POLLING_INTERVAL_SECONDS
    """
    logger.info("Starting email polling task...")

    try:
        # Get database session
        db = next(db_manager.get_db_session())

        try:
            # Create email processing service
            email_service = EmailProcessingService(db)

            # Poll inbox
            processed_count = email_service.poll_inbox()

            logger.info(f"Email polling completed. Processed {processed_count} emails.")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in email polling task: {str(e)}", exc_info=True)


def start_email_poller():
    """
    Start the email polling scheduler
    Called during application startup
    """
    try:
        # Get polling interval from settings
        interval_seconds = settings.email_processing.polling_interval_seconds

        logger.info(f"Starting email poller with {interval_seconds}s interval")

        # Add job to scheduler
        scheduler.add_job(
            poll_emails_task,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id='email_poller',
            name='Poll IMAP inbox for document emails',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )

        # Start scheduler
        if not scheduler.running:
            scheduler.start()
            logger.info("Email poller started successfully")
        else:
            logger.warning("Email poller already running")

    except Exception as e:
        logger.error(f"Failed to start email poller: {str(e)}", exc_info=True)


def stop_email_poller():
    """
    Stop the email polling scheduler
    Called during application shutdown
    """
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Email poller stopped")
    except Exception as e:
        logger.error(f"Error stopping email poller: {str(e)}")


# For testing: run poll immediately
async def run_poll_now():
    """
    Run email polling immediately (for testing/manual trigger)
    """
    logger.info("Running immediate email poll...")
    await poll_emails_task()
