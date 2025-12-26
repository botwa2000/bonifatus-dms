"""Add multi-provider storage support

Revision ID: 045_add_multi_provider
Revises: 044_add_missing_email_templates
Create Date: 2025-12-25 12:00:00.000000

This migration adds support for multiple cloud storage providers (OneDrive, Dropbox, Box, etc.)
in addition to the existing Google Drive integration.

Changes:
- Add active_storage_provider column to track user's selected provider
- Add OneDrive token columns (onedrive_refresh_token_encrypted, onedrive_enabled, onedrive_connected_at)
- Add Dropbox token columns for future use
- Add Box token columns for future use
- Backfill active_storage_provider to 'google_drive' for existing users
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '045_add_multi_provider'
down_revision = '044_add_missing_email_templates'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add multi-provider storage support to users table.
    """
    # Add active provider column
    op.add_column('users', sa.Column('active_storage_provider', sa.String(length=50), nullable=True))

    # Backfill existing users who have Google Drive connected
    op.execute("""
        UPDATE users
        SET active_storage_provider = 'google_drive'
        WHERE drive_refresh_token_encrypted IS NOT NULL
    """)

    # OneDrive columns
    op.add_column('users', sa.Column('onedrive_refresh_token_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('onedrive_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('onedrive_connected_at', sa.DateTime(timezone=True), nullable=True))

    # Dropbox columns (for future implementation)
    op.add_column('users', sa.Column('dropbox_refresh_token_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('dropbox_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('dropbox_connected_at', sa.DateTime(timezone=True), nullable=True))

    # Box columns (for future implementation)
    op.add_column('users', sa.Column('box_refresh_token_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('box_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('box_connected_at', sa.DateTime(timezone=True), nullable=True))

    # Create index for efficient provider queries
    op.create_index('idx_users_active_storage_provider', 'users', ['active_storage_provider'], unique=False)

    # Create index for OneDrive lookups
    op.create_index('idx_users_onedrive_enabled', 'users', ['onedrive_enabled'], unique=False)


def downgrade():
    """
    Remove multi-provider storage support.
    """
    # Drop indexes
    op.drop_index('idx_users_onedrive_enabled', table_name='users')
    op.drop_index('idx_users_active_storage_provider', table_name='users')

    # Drop Box columns
    op.drop_column('users', 'box_connected_at')
    op.drop_column('users', 'box_enabled')
    op.drop_column('users', 'box_refresh_token_encrypted')

    # Drop Dropbox columns
    op.drop_column('users', 'dropbox_connected_at')
    op.drop_column('users', 'dropbox_enabled')
    op.drop_column('users', 'dropbox_refresh_token_encrypted')

    # Drop OneDrive columns
    op.drop_column('users', 'onedrive_connected_at')
    op.drop_column('users', 'onedrive_enabled')
    op.drop_column('users', 'onedrive_refresh_token_encrypted')

    # Drop active provider column
    op.drop_column('users', 'active_storage_provider')
