"""add facebook_id column to users table

Revision ID: 055_add_facebook_auth
Revises: 054_add_date_patterns_for_new_languages
Create Date: 2026-02-07 00:00:00.000000

Adds facebook_id column to users table for Facebook OAuth authentication.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '055_add_facebook_auth'
down_revision = '054_add_date_patterns_for_new_languages'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('facebook_id', sa.String(50), nullable=True))
    op.create_index('idx_user_facebook_id', 'users', ['facebook_id'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_user_facebook_id', table_name='users')
    op.drop_column('users', 'facebook_id')
