"""add email preferences to users

Revision ID: 020_add_email_preferences
Revises: 019_add_email_templates
Create Date: 2025-11-15
"""
from alembic import op
import sqlalchemy as sa

revision = '020_add_email_preferences'
down_revision = '019_add_email_templates'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add email preferences column to users table
    op.add_column('users', sa.Column('email_marketing_enabled', sa.Boolean, nullable=False, server_default='true'))

def downgrade() -> None:
    op.drop_column('users', 'email_marketing_enabled')
