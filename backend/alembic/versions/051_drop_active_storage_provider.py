"""Drop active_storage_provider column (replaced by property)

Revision ID: 051_drop_active_storage_provider
Revises: 050_add_provider_connections
Create Date: 2026-01-03 12:00:00.000000

This migration drops the legacy active_storage_provider column from the users table.

The User model now uses a @property that queries the active ProviderConnection
instead of storing redundant data. This eliminates the sync issues where
User.active_storage_provider and ProviderConnection.is_active could get out of sync.

Clean architecture: One source of truth (ProviderConnection.is_active).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '051_drop_active_storage_provider'
down_revision = '050_add_provider_connections'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Drop the legacy active_storage_provider column.

    The User model now has an @property that returns the active provider
    from the ProviderConnection table.
    """
    op.drop_index('ix_users_active_storage_provider', table_name='users')
    op.drop_column('users', 'active_storage_provider')


def downgrade() -> None:
    """
    Restore the active_storage_provider column and sync from ProviderConnection.
    """
    # Recreate column
    op.add_column('users', sa.Column('active_storage_provider', sa.String(50), nullable=True))
    op.create_index('ix_users_active_storage_provider', 'users', ['active_storage_provider'])

    # Sync data from ProviderConnection back to User table
    op.execute("""
        UPDATE users u
        SET active_storage_provider = pc.provider_key
        FROM provider_connections pc
        WHERE pc.user_id = u.id
          AND pc.is_active = TRUE
    """)
