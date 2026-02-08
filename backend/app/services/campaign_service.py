# backend/app/services/campaign_service.py
"""
Marketing campaign service for sending promotional emails to users.
Supports re-sendable campaigns with per-user send tracking.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import MarketingCampaign, CampaignSend, User, TierPlan
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

    def _base_eligible_query(self, session: Session, audience_filter: str):
        """Build base query for eligible recipients (active, marketing enabled, tier filter)."""
        query = session.query(User).filter(
            and_(
                User.is_active == True,
                User.email_marketing_enabled == True,
                User.email.isnot(None),
            )
        )
        if audience_filter in AUDIENCE_TIER_MAP:
            query = query.filter(User.tier_id == AUDIENCE_TIER_MAP[audience_filter])
        return query

    def get_eligible_recipients(
        self, session: Session, audience_filter: str
    ) -> List[Tuple[str, str, str]]:
        """
        Query users eligible for a campaign.
        Returns list of (email, full_name, tier_name) tuples.
        Logs marketing preference filter stats.
        """
        # Count total active users matching tier filter (before marketing check)
        total_query = session.query(func.count(User.id)).filter(
            and_(
                User.is_active == True,
                User.email.isnot(None),
            )
        )
        if audience_filter in AUDIENCE_TIER_MAP:
            total_query = total_query.filter(User.tier_id == AUDIENCE_TIER_MAP[audience_filter])
        total_active = total_query.scalar()

        # Get eligible recipients
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

        results = query.all()
        filtered_out = total_active - len(results)
        logger.info(
            f"[CAMPAIGN] Eligible recipients: {len(results)} "
            f"(filtered out {filtered_out} users with email_marketing_enabled=False, "
            f"audience_filter={audience_filter})"
        )
        return results

    def get_new_recipients(
        self, session: Session, campaign_id: UUID, audience_filter: str
    ) -> List:
        """Get eligible users who have NOT already been sent this campaign."""
        already_sent_subq = session.query(CampaignSend.user_id).filter(
            CampaignSend.campaign_id == campaign_id
        ).subquery()

        query = session.query(
            User.id,
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
                ~User.id.in_(already_sent_subq),
            )
        )
        if audience_filter in AUDIENCE_TIER_MAP:
            query = query.filter(User.tier_id == AUDIENCE_TIER_MAP[audience_filter])

        return query.all()

    def get_recipient_count(
        self, session: Session, audience_filter: str
    ) -> int:
        """Get count of eligible recipients for a given audience filter."""
        return self._base_eligible_query(session, audience_filter).count()

    def get_recipient_counts_detailed(
        self, session: Session, campaign_id: UUID, audience_filter: str
    ) -> dict:
        """Get detailed recipient counts: total eligible, already sent, new (unsent)."""
        total_eligible = self.get_recipient_count(session, audience_filter)
        already_sent = session.query(func.count(CampaignSend.id)).filter(
            CampaignSend.campaign_id == campaign_id
        ).scalar() or 0
        new_count = len(self.get_new_recipients(session, campaign_id, audience_filter))

        return {
            'total_eligible': total_eligible,
            'already_sent': already_sent,
            'new_recipients': new_count,
        }

    def get_campaign_send_history(
        self, session: Session, campaign_id: UUID,
        page: int = 1, page_size: int = 50
    ) -> dict:
        """Get paginated send history for a campaign."""
        query = session.query(CampaignSend).filter(
            CampaignSend.campaign_id == campaign_id
        ).order_by(CampaignSend.sent_at.desc())

        total = query.count()
        sends = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            'sends': [
                {
                    'id': str(s.id),
                    'user_id': str(s.user_id),
                    'user_email': s.user_email,
                    'sent_at': s.sent_at.isoformat(),
                    'status': s.status,
                    'error_message': s.error_message,
                }
                for s in sends
            ],
            'total': total,
            'page': page,
            'page_size': page_size,
        }

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
        Send a campaign to new eligible recipients (skips already-sent users).

        Updates campaign status throughout the process.
        Rate-limited to ~10 emails/second via asyncio.sleep.
        Campaign becomes 'active' after completion (re-sendable).
        """
        logger.info(f"[CAMPAIGN SEND] Looking up campaign {campaign_id}")
        campaign = session.query(MarketingCampaign).filter(
            MarketingCampaign.id == campaign_id
        ).first()

        if not campaign:
            logger.error(f"[CAMPAIGN SEND] Campaign {campaign_id} not found")
            return {'error': 'Campaign not found'}

        logger.info(f"[CAMPAIGN SEND] Campaign '{campaign.name}' status={campaign.status}")

        if campaign.status not in ('draft', 'active'):
            logger.warning(f"[CAMPAIGN SEND] Campaign not sendable: {campaign.status}")
            return {'error': f'Campaign is in "{campaign.status}" status, must be "draft" or "active" to send'}

        # Get only new recipients (exclude already-sent)
        new_recipients = self.get_new_recipients(session, campaign_id, campaign.audience_filter)
        logger.info(f"[CAMPAIGN SEND] Found {len(new_recipients)} new recipients (excluding already sent)")

        if not new_recipients:
            return {'error': 'No new recipients to send to (all eligible users already received this campaign)'}

        # Update campaign to sending
        campaign.status = 'sending'
        campaign.sent_at = campaign.sent_at or datetime.now(timezone.utc)
        campaign.error_message = None
        session.commit()

        from_email = settings.email.email_from_info
        from_name = settings.email.email_from_name

        sent = 0
        failed = 0

        try:
            for idx, (user_id, email, full_name, tier_name) in enumerate(new_recipients, 1):
                error_msg = None
                send_status = 'sent'
                try:
                    logger.info(f"[CAMPAIGN SEND] Sending {idx}/{len(new_recipients)} to {email}")
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
                        send_status = 'failed'
                        error_msg = 'Email service returned failure'
                        logger.warning(f"Campaign {campaign.name}: failed to send to {email}")

                except Exception as e:
                    failed += 1
                    send_status = 'failed'
                    error_msg = str(e)
                    logger.error(f"Campaign {campaign.name}: error sending to {email}: {e}")

                # Record the send
                campaign_send = CampaignSend(
                    campaign_id=campaign_id,
                    user_id=user_id,
                    user_email=email,
                    status=send_status,
                    error_message=error_msg,
                )
                session.add(campaign_send)

                # Rate limiting: ~10 emails/second
                await asyncio.sleep(0.1)

            # Campaign completed - set to active (re-sendable)
            campaign.status = 'active'
            # Update cumulative counts
            campaign.total_recipients = (campaign.total_recipients or 0) + len(new_recipients)
            campaign.sent_count = (campaign.sent_count or 0) + sent
            campaign.failed_count = (campaign.failed_count or 0) + failed
            campaign.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.info(
                f"Campaign '{campaign.name}' completed: "
                f"{sent} sent, {failed} failed out of {len(new_recipients)} new recipients"
            )

            return {
                'status': 'active',
                'new_recipients': len(new_recipients),
                'sent_count': sent,
                'failed_count': failed,
            }

        except Exception as e:
            campaign.status = 'failed'
            campaign.sent_count = (campaign.sent_count or 0) + sent
            campaign.failed_count = (campaign.failed_count or 0) + failed
            campaign.error_message = str(e)
            campaign.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.error(f"Campaign '{campaign.name}' failed: {e}")
            return {'error': str(e), 'sent_count': sent, 'failed_count': failed}


campaign_service = CampaignService()
