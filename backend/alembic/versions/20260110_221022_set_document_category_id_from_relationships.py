"""set_document_category_id_from_relationships

Revision ID: 20260110_221022
Revises:
Create Date: 2026-01-10 22:10:22

This migration sets the category_id field for all existing documents based on
their primary DocumentCategory relationship. This is critical for migration
functionality to preserve folder structure when moving between cloud providers.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260110_221022'
down_revision = None  # Will be set automatically by alembic
branch_labels = None
depends_on = None


def upgrade():
    """
    Update all documents to set category_id based on their primary DocumentCategory relationship
    """
    # Use raw SQL for efficiency
    op.execute("""
        UPDATE documents
        SET category_id = dc.category_id
        FROM document_categories dc
        WHERE documents.id = dc.document_id
          AND dc.is_primary = true
          AND documents.category_id IS NULL;
    """)

    print("Updated documents.category_id from primary DocumentCategory relationships")


def downgrade():
    """
    Remove category_id values (set to NULL)

    Note: This downgrade is safe because DocumentCategory relationships are preserved
    """
    op.execute("""
        UPDATE documents
        SET category_id = NULL
        WHERE category_id IS NOT NULL;
    """)

    print("Cleared documents.category_id (relationships preserved in document_categories table)")
