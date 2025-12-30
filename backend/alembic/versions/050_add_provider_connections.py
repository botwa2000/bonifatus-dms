"""Add provider_connections table for centralized provider management

Revision ID: 050_add_provider_connections
Revises: 049_migration_email_templates
Create Date: 2025-12-30 00:00:00.000000

This migration creates a normalized provider_connections table to replace
provider-specific columns in the User table, enabling dynamic provider
management without schema changes for new providers.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '050_add_provider_connections'
down_revision = '049_migration_email_templates'
branch_labels = None
depends_on = None


def upgrade():
    """Create provider_connections table and migrate existing provider data"""

    # Create provider_connections table
    op.create_table(
        'provider_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider_key', sa.String(50), nullable=False),

        # Credentials (encrypted)
        sa.Column('refresh_token_encrypted', sa.Text, nullable=False),
        sa.Column('access_token_encrypted', sa.Text, nullable=True),

        # Status
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='false'),

        # Metadata
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=False, server_default=text('now()')),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),

        # Timestamps (from TimestampMixin)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=text('now()'), nullable=False),

        # Constraints
        sa.UniqueConstraint('user_id', 'provider_key', name='uq_user_provider'),
        sa.CheckConstraint(
            "provider_key IN ('google_drive', 'onedrive', 'dropbox', 'box')",
            name='check_provider_key'
        ),
    )

    # Create indexes
    op.create_index('idx_provider_connections_user_enabled', 'provider_connections', ['user_id', 'is_enabled'])
    op.create_index(
        'idx_provider_connections_active',
        'provider_connections',
        ['user_id', 'is_active'],
        postgresql_where=text('is_active = true')
    )
    op.create_index('idx_provider_connections_provider', 'provider_connections', ['provider_key'])

    # Migrate existing Google Drive connections
    op.execute("""
        INSERT INTO provider_connections
            (user_id, provider_key, refresh_token_encrypted, is_enabled, is_active, connected_at, created_at, updated_at)
        SELECT
            id,
            'google_drive',
            drive_refresh_token_encrypted,
            google_drive_enabled,
            (active_storage_provider = 'google_drive'),
            COALESCE(drive_permissions_granted_at, NOW()),
            NOW(),
            NOW()
        FROM users
        WHERE drive_refresh_token_encrypted IS NOT NULL
    """)

    # Migrate existing OneDrive connections
    op.execute("""
        INSERT INTO provider_connections
            (user_id, provider_key, refresh_token_encrypted, is_enabled, is_active, connected_at, created_at, updated_at)
        SELECT
            id,
            'onedrive',
            onedrive_refresh_token_encrypted,
            onedrive_enabled,
            (active_storage_provider = 'onedrive'),
            COALESCE(onedrive_connected_at, NOW()),
            NOW(),
            NOW()
        FROM users
        WHERE onedrive_refresh_token_encrypted IS NOT NULL
    """)


def downgrade():
    """Drop provider_connections table and restore data to User table columns"""

    # Restore Google Drive data to User table
    op.execute("""
        UPDATE users
        SET
            drive_refresh_token_encrypted = pc.refresh_token_encrypted,
            google_drive_enabled = pc.is_enabled,
            drive_permissions_granted_at = pc.connected_at
        FROM provider_connections pc
        WHERE users.id = pc.user_id
          AND pc.provider_key = 'google_drive'
    """)

    # Restore OneDrive data to User table
    op.execute("""
        UPDATE users
        SET
            onedrive_refresh_token_encrypted = pc.refresh_token_encrypted,
            onedrive_enabled = pc.is_enabled,
            onedrive_connected_at = pc.connected_at
        FROM provider_connections pc
        WHERE users.id = pc.user_id
          AND pc.provider_key = 'onedrive'
    """)

    # Restore active_storage_provider
    op.execute("""
        UPDATE users
        SET active_storage_provider = pc.provider_key
        FROM provider_connections pc
        WHERE users.id = pc.user_id
          AND pc.is_active = true
    """)

    # Drop indexes
    op.drop_index('idx_provider_connections_provider', 'provider_connections')
    op.drop_index('idx_provider_connections_active', 'provider_connections')
    op.drop_index('idx_provider_connections_user_enabled', 'provider_connections')

    # Drop table
    op.drop_table('provider_connections')
