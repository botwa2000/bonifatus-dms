"""Add file_hash column to documents table

Revision ID: 003_add_file_hash
Revises: 002_populate_default_data
Create Date: 2025-10-24 18:15:00.000000

Adds file_hash column for file deduplication checks in trust scoring.
"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_file_hash'
down_revision = '002_populate_default_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add file_hash column"""
    print("=== ADDING FILE_HASH COLUMN ===")

    op.add_column('documents', sa.Column('file_hash', sa.String(64), nullable=True))
    op.create_index('idx_documents_file_hash', 'documents', ['file_hash'])

    print("✅ Added file_hash column with index")


def downgrade() -> None:
    """Remove file_hash column"""
    op.drop_index('idx_documents_file_hash', table_name='documents')
    op.drop_column('documents', 'file_hash')

    print("✅ Removed file_hash column")
