"""Add marketing campaigns table

Revision ID: 056_add_marketing_campaigns
Revises: 055_add_facebook_auth
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '056_add_marketing_campaigns'
down_revision = '055_add_facebook_auth'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'marketing_campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('html_body', sa.Text(), nullable=False),
        sa.Column('audience_filter', sa.String(50), nullable=False, server_default='all'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('total_recipients', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_campaign_status', 'marketing_campaigns', ['status'])
    op.create_index('idx_campaign_created', 'marketing_campaigns', ['created_at'])


def downgrade():
    op.drop_index('idx_campaign_created', table_name='marketing_campaigns')
    op.drop_index('idx_campaign_status', table_name='marketing_campaigns')
    op.drop_table('marketing_campaigns')
