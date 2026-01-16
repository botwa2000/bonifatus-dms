"""Add tier provider settings table

Revision ID: 052_add_tier_provider_settings
Revises: 051_drop_active_storage_provider
Create Date: 2026-01-16

This migration adds a table to configure which storage providers
are available for each subscription tier, allowing admin control
over provider availability per tier.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '052_add_tier_provider_settings'
down_revision = '051_drop_active_storage_provider'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tier_provider_settings table
    op.create_table(
        'tier_provider_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tier_id', sa.Integer(), nullable=False),
        sa.Column('provider_key', sa.String(50), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tier_id'], ['tier_plans.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tier_id', 'provider_key', name='uq_tier_provider')
    )

    # Create index for faster lookups
    op.create_index('idx_tier_provider_tier_id', 'tier_provider_settings', ['tier_id'])
    op.create_index('idx_tier_provider_provider_key', 'tier_provider_settings', ['provider_key'])

    # Populate with default settings based on current provider_registry.py configuration
    # Google Drive and OneDrive: available to all tiers (min_tier_id=0)
    # Dropbox: available to Starter and above (min_tier_id=1)
    # Box: available to Pro and above (min_tier_id=2)

    # Insert default settings for each tier
    op.execute("""
        INSERT INTO tier_provider_settings (tier_id, provider_key, is_enabled) VALUES
        -- Free tier (id=0)
        (0, 'google_drive', true),
        (0, 'onedrive', true),
        (0, 'dropbox', false),
        (0, 'box', false),
        -- Starter tier (id=1)
        (1, 'google_drive', true),
        (1, 'onedrive', true),
        (1, 'dropbox', true),
        (1, 'box', false),
        -- Pro tier (id=2)
        (2, 'google_drive', true),
        (2, 'onedrive', true),
        (2, 'dropbox', true),
        (2, 'box', true),
        -- Admin tier (id=100)
        (100, 'google_drive', true),
        (100, 'onedrive', true),
        (100, 'dropbox', true),
        (100, 'box', true)
    """)


def downgrade() -> None:
    op.drop_index('idx_tier_provider_provider_key', 'tier_provider_settings')
    op.drop_index('idx_tier_provider_tier_id', 'tier_provider_settings')
    op.drop_table('tier_provider_settings')
