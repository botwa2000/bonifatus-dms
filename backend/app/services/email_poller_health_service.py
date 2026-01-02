# backend/app/services/email_poller_health_service.py
"""
Bonifatus DMS - Email Poller Health Monitoring Service
Monitors email polling service status and provides diagnostics
"""

import logging
import imaplib
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EmailPollerHealthService:
    """
    Email poller health monitoring service

    Features:
    - IMAP connection health checks
    - Polling status monitoring
    - Manual poll triggering
    - Failure tracking and alerting
    """

    def __init__(self):
        self._last_check_time: Optional[datetime] = None
        self._last_status: Optional[Dict] = None
        self._last_successful_poll: Optional[datetime] = None
        self._last_poll_error: Optional[str] = None
        self._consecutive_failures = 0
        self._total_emails_processed = 0

    async def check_health(self) -> Dict:
        """
        Check email poller health status

        Returns:
            Dictionary with health status information
        """
        from app.core.config import settings
        from app.database.connection import db_manager
        from app.database.auth_models import EmailProcessingLog
        from sqlalchemy import func, desc

        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'Email Poller',
            'status': 'unknown',
            'imap_available': False,
            'imap_host': settings.email_processing.imap_host,
            'imap_port': settings.email_processing.imap_port,
            'polling_interval_seconds': settings.email_processing.polling_interval_seconds,
            'last_successful_poll': None,
            'last_poll_error': self._last_poll_error,
            'consecutive_failures': self._consecutive_failures,
            'total_emails_processed_today': 0,
            'recent_activity': []
        }

        try:
            # Test IMAP connection
            imap_host = settings.email_processing.imap_host
            imap_port = settings.email_processing.imap_port
            imap_user = settings.email_processing.imap_user
            imap_password = settings.email_processing.imap_password
            imap_use_ssl = settings.email_processing.imap_use_ssl

            logger.debug(f"Testing IMAP connection to {imap_host}:{imap_port}")

            try:
                if imap_use_ssl:
                    imap = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=10)
                else:
                    imap = imaplib.IMAP4(imap_host, imap_port, timeout=10)

                imap.login(imap_user, imap_password)
                imap.select('INBOX', readonly=True)

                # Get unread count
                _, messages = imap.search(None, 'UNSEEN')
                unread_count = len(messages[0].split()) if messages[0] else 0

                imap.close()
                imap.logout()

                status['imap_available'] = True
                status['unread_emails'] = unread_count
                logger.debug(f"IMAP connection successful, {unread_count} unread emails")

            except Exception as imap_error:
                logger.error(f"IMAP connection failed: {imap_error}")
                status['imap_available'] = False
                status['imap_error'] = str(imap_error)
                status['status'] = 'unhealthy'
                self._last_status = status
                self._last_check_time = datetime.utcnow()
                return status

            # Get recent processing logs
            db = next(db_manager.get_db_session())
            try:
                # Get today's email count
                today = datetime.utcnow().date()
                today_count = db.query(func.count(EmailProcessingLog.id)).filter(
                    func.date(EmailProcessingLog.received_at) == today,
                    EmailProcessingLog.status == 'completed'
                ).scalar()

                status['total_emails_processed_today'] = today_count or 0

                # Get last 5 processing logs (any user)
                recent_logs = db.query(EmailProcessingLog).order_by(
                    desc(EmailProcessingLog.received_at)
                ).limit(5).all()

                status['recent_activity'] = [
                    {
                        'received_at': log.received_at.isoformat(),
                        'status': log.status,
                        'sender_email': log.sender_email,
                        'documents_created': log.documents_created,
                        'rejection_reason': log.rejection_reason
                    }
                    for log in recent_logs
                ]

                # Get last successful poll time
                last_success = db.query(EmailProcessingLog).filter(
                    EmailProcessingLog.status == 'completed'
                ).order_by(desc(EmailProcessingLog.received_at)).first()

                if last_success:
                    self._last_successful_poll = last_success.received_at
                    status['last_successful_poll'] = last_success.received_at.isoformat()

                    # Check if polling is stale (no activity for 2x polling interval)
                    time_since_last = datetime.utcnow() - last_success.received_at
                    max_idle = timedelta(seconds=settings.email_processing.polling_interval_seconds * 2)

                    if time_since_last > max_idle:
                        status['warning'] = f'No emails processed in {int(time_since_last.total_seconds() / 60)} minutes'

            finally:
                db.close()

            # Determine overall status
            if status['imap_available']:
                if self._consecutive_failures > 0:
                    status['status'] = 'degraded'
                    status['warning'] = f'{self._consecutive_failures} recent poll failures'
                else:
                    status['status'] = 'healthy'
            else:
                status['status'] = 'unhealthy'

        except Exception as e:
            logger.error(f"Email poller health check error: {e}", exc_info=True)
            status['status'] = 'error'
            status['error'] = str(e)

        self._last_status = status
        self._last_check_time = datetime.utcnow()

        return status

    async def trigger_manual_poll(self) -> Dict:
        """
        Manually trigger an email poll immediately

        Returns:
            Dictionary with poll result
        """
        try:
            from app.tasks.email_poller import run_poll_now

            logger.info("Manual email poll triggered")

            # Run poll
            await run_poll_now()

            # Reset failure counter on successful manual poll
            self._consecutive_failures = 0
            self._last_poll_error = None

            # Get updated health status
            health = await self.check_health()

            return {
                'success': True,
                'message': 'Email poll completed successfully',
                'health': health
            }

        except Exception as e:
            logger.error(f"Manual email poll failed: {e}", exc_info=True)
            self._consecutive_failures += 1
            self._last_poll_error = str(e)

            return {
                'success': False,
                'error': str(e),
                'consecutive_failures': self._consecutive_failures
            }

    def record_poll_failure(self, error: str):
        """Record a polling failure for monitoring"""
        self._consecutive_failures += 1
        self._last_poll_error = error
        logger.error(f"Email poll failure #{self._consecutive_failures}: {error}")

    def record_poll_success(self, emails_processed: int):
        """Record a successful poll"""
        self._consecutive_failures = 0
        self._last_successful_poll = datetime.utcnow()
        self._last_poll_error = None
        self._total_emails_processed += emails_processed

    def get_last_status(self) -> Optional[Dict]:
        """Get cached health status without performing new check"""
        return self._last_status

    def should_send_alert(self) -> bool:
        """Check if admin should be alerted about failures"""
        # Alert on 3 consecutive failures
        return self._consecutive_failures >= 3


# Global service instance
email_poller_health_service = EmailPollerHealthService()
