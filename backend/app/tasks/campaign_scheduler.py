"""
Campaign Scheduler Background Task
Periodically checks for scheduled campaigns and sends to new recipients.
Uses the shared scheduler from email_poller to avoid multiple AsyncIOScheduler conflicts.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.triggers.interval import IntervalTrigger

from app.database.connection import db_manager
from app.database.models import MarketingCampaign

logger = logging.getLogger(__name__)

# Check interval in seconds (every 15 minutes)
SCHEDULER_CHECK_INTERVAL_SECONDS = 900

# Job ID for the campaign scheduler
CAMPAIGN_JOB_ID = 'campaign_scheduler'


def _is_campaign_due(schedule_cron: str, last_run: datetime | None) -> bool:
    """
    Check if a campaign is due to send based on its schedule config.

    Schedule format is JSON: {"type": "interval_days", "value": 7}
    Supported types:
      - interval_days: send every N days
      - weekday: send on specific day ("monday", "tuesday", etc.)
      - monthly_day: send on specific day of month
    """
    try:
        config = json.loads(schedule_cron)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Invalid schedule_cron: {schedule_cron}")
        return False

    schedule_type = config.get('type')
    value = config.get('value')
    now = datetime.now(timezone.utc)

    if schedule_type == 'interval_days':
        if not last_run:
            return True
        days_since = (now - last_run).total_seconds() / 86400
        return days_since >= value

    elif schedule_type == 'weekday':
        weekday_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2,
            'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6,
        }
        target_day = weekday_map.get(str(value).lower())
        if target_day is None:
            return False
        if now.weekday() != target_day:
            return False
        # Only send once per day
        if last_run and last_run.date() == now.date():
            return False
        return True

    elif schedule_type == 'monthly_day':
        # Send on specific day of month (e.g., 1st)
        if now.day != value:
            return False
        if last_run and last_run.month == now.month and last_run.year == now.year:
            return False
        return True

    return False


async def check_scheduled_campaigns():
    """
    Background task to check and send scheduled campaigns.
    Finds campaigns with schedule_enabled=True in draft/active status,
    checks if they're due, and sends to new recipients only.
    """
    logger.info("[CAMPAIGN SCHEDULER] Checking for scheduled campaigns...")

    try:
        db = next(db_manager.get_db_session())
        try:
            # Find campaigns that are scheduled and in a sendable state
            campaigns = db.query(MarketingCampaign).filter(
                MarketingCampaign.schedule_enabled == True,
                MarketingCampaign.status.in_(['draft', 'active']),
                MarketingCampaign.schedule_cron.isnot(None),
            ).all()

            if not campaigns:
                logger.info("[CAMPAIGN SCHEDULER] No scheduled campaigns found")
                return

            logger.info(f"[CAMPAIGN SCHEDULER] Found {len(campaigns)} scheduled campaign(s)")

            for campaign in campaigns:
                if _is_campaign_due(campaign.schedule_cron, campaign.last_scheduled_run):
                    logger.info(f"[CAMPAIGN SCHEDULER] Campaign '{campaign.name}' is due, triggering send")
                    try:
                        from app.services.campaign_service import campaign_service
                        result = await campaign_service.send_campaign(
                            db, campaign.id, campaign.created_by
                        )
                        campaign.last_scheduled_run = datetime.now(timezone.utc)
                        db.commit()
                        logger.info(f"[CAMPAIGN SCHEDULER] Campaign '{campaign.name}' scheduled send result: {result}")
                    except Exception as e:
                        logger.error(f"[CAMPAIGN SCHEDULER] Error sending campaign '{campaign.name}': {e}")
                else:
                    logger.info(f"[CAMPAIGN SCHEDULER] Campaign '{campaign.name}' not yet due")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[CAMPAIGN SCHEDULER] Error in scheduler task: {e}", exc_info=True)


def start_campaign_scheduler():
    """Start the campaign scheduler by adding job to the shared scheduler."""
    try:
        from app.tasks.email_poller import scheduler as shared_scheduler

        logger.info(f"Starting campaign scheduler with {SCHEDULER_CHECK_INTERVAL_SECONDS}s interval")

        shared_scheduler.add_job(
            check_scheduled_campaigns,
            trigger=IntervalTrigger(seconds=SCHEDULER_CHECK_INTERVAL_SECONDS),
            id=CAMPAIGN_JOB_ID,
            name='Check and send scheduled campaigns',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300,
        )

        logger.info("Campaign scheduler job registered on shared scheduler")

    except Exception as e:
        logger.error(f"Failed to start campaign scheduler: {e}", exc_info=True)


def stop_campaign_scheduler():
    """Remove campaign scheduler job from shared scheduler."""
    try:
        from app.tasks.email_poller import scheduler as shared_scheduler

        if shared_scheduler.running:
            shared_scheduler.remove_job(CAMPAIGN_JOB_ID)
            logger.info("Campaign scheduler job removed")
    except Exception as e:
        logger.error(f"Error stopping campaign scheduler: {e}")
