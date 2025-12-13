"""add email processing to user

Revision ID: 042_add_email_processing_to_user
Revises: 041_enhance_email_tracking
Create Date: 2025-12-13 13:29:05.603330

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '042_add_email_processing_to_user'
down_revision = '041_enhance_email_tracking'
branch_labels = None
depends_on = None


def upgrade():
    # Add email processing columns to users table
    op.add_column('users', sa.Column('email_processing_address', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('email_processing_enabled', sa.Boolean(), nullable=False, server_default='false'))

    # Create unique index on email_processing_address for faster lookups
    op.create_index('ix_users_email_processing_address', 'users', ['email_processing_address'], unique=True)


def downgrade():
    # Drop index and columns
    op.drop_index('ix_users_email_processing_address', table_name='users')
    op.drop_column('users', 'email_processing_enabled')
    op.drop_column('users', 'email_processing_address')
