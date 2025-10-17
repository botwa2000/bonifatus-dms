"""Add soft delete support to documents table

Revision ID: q1r2s3t4u5v6
Revises: p2q3r4s5t6u7
Create Date: 2025-10-17 22:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'q1r2s3t4u5v6'
down_revision = 'p2q3r4s5t6u7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add soft delete columns to documents table"""

    # Add is_deleted column (default False for all existing documents)
    op.add_column('documents',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false')
    )

    # Add deleted_at timestamp
    op.add_column('documents',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add deleted_by user reference
    op.add_column('documents',
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Create foreign key for deleted_by
    op.create_foreign_key(
        'fk_documents_deleted_by_users',
        'documents', 'users',
        ['deleted_by'], ['id'],
        ondelete='SET NULL'
    )

    # Create index on is_deleted for efficient filtering
    op.create_index('idx_documents_is_deleted', 'documents', ['is_deleted'])

    # Create composite index for user + is_deleted (common query pattern)
    op.create_index('idx_documents_user_not_deleted', 'documents', ['user_id', 'is_deleted'])


def downgrade() -> None:
    """Remove soft delete columns from documents table"""

    # Drop indexes
    op.drop_index('idx_documents_user_not_deleted', table_name='documents')
    op.drop_index('idx_documents_is_deleted', table_name='documents')

    # Drop foreign key
    op.drop_constraint('fk_documents_deleted_by_users', 'documents', type_='foreignkey')

    # Drop columns
    op.drop_column('documents', 'deleted_by')
    op.drop_column('documents', 'deleted_at')
    op.drop_column('documents', 'is_deleted')
