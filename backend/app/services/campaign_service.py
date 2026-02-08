# backend/app/services/campaign_service.py
"""
Marketing campaign service for sending promotional emails to users
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import MarketingCampaign, User, TierPlan
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

# Tier ID to audience_filter mapping
AUDIENCE_TIER_MAP = {
    'free': 0,
    'starter': 1,
    'pro': 2,
}

UNSUBSCRIBE_FOOTER = """
<div style="text-align:center; padding:20px; color:#999; font-size:12px; border-top:1px solid #eee; margin-top:30px;">
  <p>This email was sent to {user_name} ({user_email}) because you signed up to
    <a href="{app_url}" style="color:#666;">BoniDoc</a>.
  </p>
  <p>If you no longer wish to receive these emails, you can
    <a href="{app_url}/settings" style="color:#666;">unsubscribe here</a>.
  </p>
</div>
"""


class CampaignService:
    """Service for managing and sending marketing email campaigns"""

    def __init__(self):
        self.email_service = EmailService()

    def get_eligible_recipients(
        self, session: Session, audience_filter: str
    ) -> List[Tuple[str, str, str]]:
        """
        Query users eligible for a campaign.

        Returns list of (email, full_name, tier_name) tuples.
        """
        query = session.query(
            User.email,
            User.full_name,
            TierPlan.name
        ).outerjoin(
            TierPlan, User.tier_id == TierPlan.id
        ).filter(
            and_(
                User.is_active == True,
                User.email_marketing_enabled == True,
                User.email.isnot(None),
            )
        )

        if audience_filter in AUDIENCE_TIER_MAP:
            query = query.filter(User.tier_id == AUDIENCE_TIER_MAP[audience_filter])

        return query.all()

    def get_recipient_count(
        self, session: Session, audience_filter: str
    ) -> int:
        """Get count of eligible recipients for a given audience filter."""
        query = session.query(User.id).filter(
            and_(
                User.is_active == True,
                User.email_marketing_enabled == True,
                User.email.isnot(None),
            )
        )

        if audience_filter in AUDIENCE_TIER_MAP:
            query = query.filter(User.tier_id == AUDIENCE_TIER_MAP[audience_filter])

        return query.count()

    def _render_template(
        self, template: str, user_name: str, user_email: str, tier_name: str
    ) -> str:
        """Replace template variables with actual values."""
        app_url = settings.app.app_frontend_url.rstrip('/')
        result = template
        result = result.replace('{{user_name}}', user_name or 'there')
        result = result.replace('{{user_email}}', user_email)
        result = result.replace('{{tier_name}}', tier_name or 'Free')
        result = result.replace('{{app_url}}', app_url)
        return result

    def _append_footer(
        self, html_body: str, user_name: str, user_email: str
    ) -> str:
        """Append unsubscribe footer to email body."""
        app_url = settings.app.app_frontend_url.rstrip('/')
        footer = UNSUBSCRIBE_FOOTER.format(
            user_name=user_name or 'there',
            user_email=user_email,
            app_url=app_url,
        )
        return html_body + footer

    def preview_campaign(self, html_body: str, subject: str) -> dict:
        """Render a preview with sample variable values."""
        sample_name = 'John Doe'
        sample_email = 'john@example.com'
        sample_tier = 'Free'

        rendered_body = self._render_template(html_body, sample_name, sample_email, sample_tier)
        rendered_body = self._append_footer(rendered_body, sample_name, sample_email)
        rendered_subject = self._render_template(subject, sample_name, sample_email, sample_tier)

        return {
            'subject': rendered_subject,
            'html_body': rendered_body,
        }

    async def send_campaign(
        self, session: Session, campaign_id: UUID, admin_user_id: UUID
    ) -> dict:
        """
        Send a campaign to all eligible recipients.

        Updates campaign status throughout the process.
        Rate-limited to ~10 emails/second via asyncio.sleep.
        """
        logger.info(f"[CAMPAIGN SEND] Looking up campaign {campaign_id}")
        campaign = session.query(MarketingCampaign).filter(
            MarketingCampaign.id == campaign_id
        ).first()

        if not campaign:
            logger.error(f"[CAMPAIGN SEND] Campaign {campaign_id} not found")
            return {'error': 'Campaign not found'}

        logger.info(f"[CAMPAIGN SEND] Campaign '{campaign.name}' status={campaign.status}")

        if campaign.status != 'draft':
            logger.warning(f"[CAMPAIGN SEND] Campaign not in draft status: {campaign.status}")
            return {'error': f'Campaign is in "{campaign.status}" status, must be "draft" to send'}

        # Get recipients
        recipients = self.get_eligible_recipients(session, campaign.audience_filter)
        logger.info(f"[CAMPAIGN SEND] Found {len(recipients)} eligible recipients")

        if not recipients:
            return {'error': 'No eligible recipients found'}

        # Update campaign to sending
        campaign.status = 'sending'
        campaign.total_recipients = len(recipients)
        campaign.sent_count = 0
        campaign.failed_count = 0
        campaign.sent_at = datetime.now(timezone.utc)
        campaign.error_message = None
        session.commit()

        from_email = settings.email.email_from_info
        from_name = settings.email.email_from_name

        sent = 0
        failed = 0

        try:
            for idx, (email, full_name, tier_name) in enumerate(recipients, 1):
                try:
                    logger.info(f"[CAMPAIGN SEND] Sending {idx}/{len(recipients)} to {email}")
                    # Render template for this user
                    rendered_subject = self._render_template(
                        campaign.subject, full_name, email, tier_name
                    )
                    rendered_body = self._render_template(
                        campaign.html_body, full_name, email, tier_name
                    )
                    rendered_body = self._append_footer(rendered_body, full_name, email)

                    success = await self.email_service.send_email(
                        to_email=email,
                        to_name=full_name,
                        subject=rendered_subject,
                        html_content=rendered_body,
                        from_email=from_email,
                        from_name=from_name,
                        reply_to=settings.email.email_from_info,
                    )

                    if success:
                        sent += 1
                    else:
                        failed += 1
                        logger.warning(f"Campaign {campaign.name}: failed to send to {email}")

                except Exception as e:
                    failed += 1
                    logger.error(f"Campaign {campaign.name}: error sending to {email}: {e}")

                # Rate limiting: ~10 emails/second
                await asyncio.sleep(0.1)

            # Campaign completed
            campaign.status = 'sent'
            campaign.sent_count = sent
            campaign.failed_count = failed
            campaign.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.info(
                f"Campaign '{campaign.name}' completed: "
                f"{sent} sent, {failed} failed out of {len(recipients)} recipients"
            )

            return {
                'status': 'sent',
                'total_recipients': len(recipients),
                'sent_count': sent,
                'failed_count': failed,
            }

        except Exception as e:
            campaign.status = 'failed'
            campaign.sent_count = sent
            campaign.failed_count = failed
            campaign.error_message = str(e)
            campaign.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.error(f"Campaign '{campaign.name}' failed: {e}")
            return {'error': str(e), 'sent_count': sent, 'failed_count': failed}


campaign_service = CampaignService()
