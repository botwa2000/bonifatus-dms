"""Add document date fields for date extraction

Revision ID: n0o1p2q3r4s5
Revises: m9n0o1p2q3r4
Create Date: 2025-10-17 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'n0o1p2q3r4s5'
down_revision = 'l3m4n5o6p7q8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add document_date and document_date_confidence to documents table"""

    # Add document date fields
    op.add_column('documents', sa.Column('document_date', sa.Date(), nullable=True))
    op.add_column('documents', sa.Column('document_date_confidence', sa.Float(), nullable=True))
    op.add_column('documents', sa.Column('document_date_type', sa.String(50), nullable=True))

    # Add index for document_date for efficient date-based queries
    op.create_index('idx_document_date', 'documents', ['document_date'])


def downgrade() -> None:
    """Remove document date fields"""

    op.drop_index('idx_document_date', table_name='documents')
    op.drop_column('documents', 'document_date_type')
    op.drop_column('documents', 'document_date_confidence')
    op.drop_column('documents', 'document_date')
