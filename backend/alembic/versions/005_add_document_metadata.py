"""Add document metadata columns for enhanced features

Revision ID: 005_add_metadata
Revises: 004_keyword_unique
Create Date: 2025-01-26 10:00:00.000000

Adds columns for original filename tracking, Google Drive links,
and duplicate detection to improve UX and data integrity.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '005_add_metadata'
down_revision = '004_keyword_unique'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing document metadata columns"""
    print("=== ADDING DOCUMENT METADATA COLUMNS ===")

    # Add original_filename - preserves what user uploaded
    op.add_column('documents', sa.Column('original_filename', sa.String(255), nullable=True))
    print("✅ Added original_filename column")

    # Add web_view_link - Google Drive direct link
    op.add_column('documents', sa.Column('web_view_link', sa.String(500), nullable=True))
    print("✅ Added web_view_link column")

    # Add is_duplicate flag
    op.add_column('documents', sa.Column('is_duplicate', sa.Boolean, nullable=False, server_default='false'))
    print("✅ Added is_duplicate column")

    # Add duplicate_of_document_id - references original document
    op.add_column('documents', sa.Column(
        'duplicate_of_document_id',
        UUID(as_uuid=True),
        sa.ForeignKey('documents.id', ondelete='SET NULL'),
        nullable=True
    ))
    op.create_index('idx_documents_duplicate_of', 'documents', ['duplicate_of_document_id'])
    print("✅ Added duplicate_of_document_id column with foreign key and index")

    # Backfill original_filename from file_name for existing records
    op.execute("UPDATE documents SET original_filename = file_name WHERE original_filename IS NULL")
    print("✅ Backfilled original_filename for existing documents")

    print("=== MIGRATION COMPLETE ===")


def downgrade() -> None:
    """Remove document metadata columns"""
    op.drop_index('idx_documents_duplicate_of', table_name='documents')
    op.drop_column('documents', 'duplicate_of_document_id')
    op.drop_column('documents', 'is_duplicate')
    op.drop_column('documents', 'web_view_link')
    op.drop_column('documents', 'original_filename')
    print("✅ Removed document metadata columns")
