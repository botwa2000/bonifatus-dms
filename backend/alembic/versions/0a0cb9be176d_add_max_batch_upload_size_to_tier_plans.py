"""add_max_batch_upload_size_to_tier_plans

Revision ID: 0a0cb9be176d
Revises: 017_tier_system
Create Date: 2025-11-10 22:06:28.136680

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a0cb9be176d'
down_revision = '017_tier_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add max_batch_upload_size column to tier_plans table
    op.add_column('tier_plans', sa.Column('max_batch_upload_size', sa.Integer(), nullable=True, server_default='10'))

    # Set default values for existing tiers
    op.execute("UPDATE tier_plans SET max_batch_upload_size = 10 WHERE id = 0")  # Free
    op.execute("UPDATE tier_plans SET max_batch_upload_size = 20 WHERE id = 1")  # Starter
    op.execute("UPDATE tier_plans SET max_batch_upload_size = 50 WHERE id = 2")  # Pro
    op.execute("UPDATE tier_plans SET max_batch_upload_size = NULL WHERE id = 100")  # Admin (unlimited)


def downgrade() -> None:
    # Remove max_batch_upload_size column
    op.drop_column('tier_plans', 'max_batch_upload_size')