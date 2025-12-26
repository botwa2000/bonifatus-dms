"""Document multi-provider support

Revision ID: 046_document_multi_provider
Revises: 045_add_multi_provider
Create Date: 2025-12-25 12:10:00.000000

This migration updates the documents table to support multiple cloud storage providers.

Changes:
- Rename google_drive_file_id to storage_file_id (generic across providers)
- Add storage_provider_type column to track which provider stores each document
- Update unique constraint to be composite: (storage_provider_type, storage_file_id)
- Backfill storage_provider_type to 'google_drive' for existing documents
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '046_document_multi_provider'
down_revision = '045_add_multi_provider'
branch_labels = None
depends_on = None


def upgrade():
    """
    Update documents table for multi-provider support.
    """
    # First, drop the unique constraint on google_drive_file_id
    # Note: Constraint name may vary, check your database
    try:
        op.drop_constraint('uq_documents_google_drive_file_id', 'documents', type_='unique')
    except Exception:
        # If constraint doesn't exist or has different name, try alternate names
        try:
            op.drop_constraint('documents_google_drive_file_id_key', 'documents', type_='unique')
        except Exception:
            # If still fails, constraint might not exist - that's okay
            pass

    # Rename column from google_drive_file_id to storage_file_id
    op.alter_column('documents', 'google_drive_file_id',
                    new_column_name='storage_file_id',
                    existing_type=sa.String(length=100),
                    existing_nullable=False)

    # Add storage_provider_type column (nullable first for backfill)
    op.add_column('documents', sa.Column('storage_provider_type', sa.String(length=50), nullable=True))

    # Backfill existing documents to use 'google_drive' as provider
    op.execute("""
        UPDATE documents
        SET storage_provider_type = 'google_drive'
        WHERE storage_provider_type IS NULL
    """)

    # Make storage_provider_type NOT NULL after backfill
    op.alter_column('documents', 'storage_provider_type',
                    existing_type=sa.String(length=50),
                    nullable=False)

    # Create composite unique constraint (allows same file_id across different providers)
    op.create_unique_constraint(
        'uq_documents_provider_file_id',
        'documents',
        ['storage_provider_type', 'storage_file_id']
    )

    # Create index for efficient provider queries
    op.create_index('idx_documents_storage_provider', 'documents', ['storage_provider_type'], unique=False)


def downgrade():
    """
    Revert documents table to Google Drive-only support.
    """
    # Drop the composite unique constraint
    op.drop_constraint('uq_documents_provider_file_id', 'documents', type_='unique')

    # Drop the index
    op.drop_index('idx_documents_storage_provider', table_name='documents')

    # Drop storage_provider_type column
    op.drop_column('documents', 'storage_provider_type')

    # Rename column back to google_drive_file_id
    op.alter_column('documents', 'storage_file_id',
                    new_column_name='google_drive_file_id',
                    existing_type=sa.String(length=100),
                    existing_nullable=False)

    # Recreate original unique constraint
    op.create_unique_constraint('uq_documents_google_drive_file_id', 'documents', ['google_drive_file_id'])
