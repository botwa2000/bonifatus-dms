"""Migrate existing 'sent' campaigns to 'active' status for reusability

The new campaign flow uses 'active' instead of terminal 'sent'.
This converts all existing sent campaigns so they can be re-sent,
edited, and scheduled.

Revision ID: 058_migrate_sent_campaigns_to_active
Revises: 057_add_campaign_sends_and_scheduling
"""
from alembic import op

revision = '058_migrate_sent_campaigns_to_active'
down_revision = '057_add_campaign_sends_and_scheduling'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE marketing_campaigns SET status = 'active' WHERE status = 'sent'")


def downgrade():
    op.execute("UPDATE marketing_campaigns SET status = 'sent' WHERE status = 'active'")
