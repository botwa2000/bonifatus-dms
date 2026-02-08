"""Add campaign_sends table and scheduling columns to marketing_campaigns

Revision ID: 057_add_campaign_sends_and_scheduling
Revises: 056_add_marketing_campaigns
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '057_add_campaign_sends_and_scheduling'
down_revision = '056_add_marketing_campaigns'
branch_labels = None
depends_on = None


def upgrade():
    # Add scheduling columns to marketing_campaigns
    op.add_column('marketing_campaigns', sa.Column('schedule_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('marketing_campaigns', sa.Column('schedule_cron', sa.Text(), nullable=True))
    op.add_column('marketing_campaigns', sa.Column('last_scheduled_run', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_campaign_schedule', 'marketing_campaigns', ['schedule_enabled', 'status'])

    # Create campaign_sends table
    op.create_table(
        'campaign_sends',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('marketing_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_email', sa.String(320), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='sent'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.UniqueConstraint('campaign_id', 'user_id', name='uq_campaign_send_user'),
    )
    op.create_index('idx_campaign_send_campaign', 'campaign_sends', ['campaign_id'])
    op.create_index('idx_campaign_send_user', 'campaign_sends', ['user_id'])
    op.create_index('idx_campaign_send_status', 'campaign_sends', ['status'])


def downgrade():
    op.drop_index('idx_campaign_send_status', table_name='campaign_sends')
    op.drop_index('idx_campaign_send_user', table_name='campaign_sends')
    op.drop_index('idx_campaign_send_campaign', table_name='campaign_sends')
    op.drop_table('campaign_sends')

    op.drop_index('idx_campaign_schedule', table_name='marketing_campaigns')
    op.drop_column('marketing_campaigns', 'last_scheduled_run')
    op.drop_column('marketing_campaigns', 'schedule_cron')
    op.drop_column('marketing_campaigns', 'schedule_enabled')
