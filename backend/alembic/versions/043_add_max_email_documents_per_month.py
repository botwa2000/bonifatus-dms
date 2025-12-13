"""add max email documents per month to tier plans

Revision ID: 043_add_max_email_documents
Revises: 042_add_email_processing_to_user
Create Date: 2025-12-13 22:17:22.028951

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '043_add_max_email_documents'
down_revision = '042_add_email_processing_to_user'
branch_labels = None
depends_on = None


def upgrade():
    # Add max_email_documents_per_month column to tier_plans table
    op.add_column('tier_plans', sa.Column('max_email_documents_per_month', sa.Integer(), nullable=True))


def downgrade():
    # Remove max_email_documents_per_month column
    op.drop_column('tier_plans', 'max_email_documents_per_month')
