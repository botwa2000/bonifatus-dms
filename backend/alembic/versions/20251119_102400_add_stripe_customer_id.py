"""add stripe_customer_id to users

Revision ID: 20251119_102400
Revises: 20251118_220722
Create Date: 2025-11-19 10:24:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251119_102400'
down_revision = '20251118_220722'
branch_labels = None
depends_on = None


def upgrade():
    # Add stripe_customer_id column to users table
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(length=255), nullable=True))

    # Create unique constraint
    op.create_unique_constraint('uq_users_stripe_customer_id', 'users', ['stripe_customer_id'])

    # Create index for fast lookups
    op.create_index('idx_users_stripe_customer_id', 'users', ['stripe_customer_id'])


def downgrade():
    # Drop index
    op.drop_index('idx_users_stripe_customer_id', table_name='users')

    # Drop unique constraint
    op.drop_constraint('uq_users_stripe_customer_id', 'users', type_='unique')

    # Drop column
    op.drop_column('users', 'stripe_customer_id')
