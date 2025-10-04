# backend/alembic/versions/j5e6f7g8h9i0_enhance_existing_tables.py
"""Enhance existing tables: add columns to documents and users

Revision ID: j5e6f7g8h9i0
Revises: i4d5e6f7g8h9
Create Date: 2025-10-04 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'j5e6f7g8h9i0'
down_revision = 'i4d5e6f7g8h9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enhance Documents table
    op.add_column('documents', sa.Column('file_hash', sa.String(length=64), nullable=True))
    op.add_column('documents', sa.Column('original_filename', sa.String(length=255), nullable=True))
    op.add_column('documents', sa.Column('thumbnail_url', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('preview_url', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('page_count', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('document_type', sa.String(length=50), nullable=True))
    op.add_column('documents', sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('documents', sa.Column('duplicate_of_document_id', UUID(as_uuid=True), nullable=True))
    op.add_column('documents', sa.Column('web_view_link', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('documents', sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add foreign key for duplicate_of_document_id
    op.create_foreign_key(
        'fk_documents_duplicate_of', 
        'documents', 
        'documents', 
        ['duplicate_of_document_id'], 
        ['id'], 
        ondelete='SET NULL'
    )
    
    # Create indexes for new columns
    op.create_index('idx_document_file_hash', 'documents', ['file_hash'])
    op.create_index('idx_document_type', 'documents', ['document_type'])
    op.create_index('idx_document_duplicate', 'documents', ['is_duplicate'])
    
    # Add full-text search vector column
    op.add_column('documents', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR(), nullable=True))
    
    # Create GIN index for full-text search
    op.execute("""
        CREATE INDEX idx_documents_search ON documents 
        USING gin(search_vector)
    """)
    
    # Create trigger to auto-update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION documents_search_vector_update() 
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.extracted_text, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER documents_search_vector_trigger
        BEFORE INSERT OR UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION documents_search_vector_update()
    """)
    
    # Update existing rows to populate search_vector
    op.execute("""
        UPDATE documents SET 
            search_vector = 
                setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(extracted_text, '')), 'C')
        WHERE search_vector IS NULL
    """)
    
    # Enhance Users table
    op.add_column('users', sa.Column('preferred_language', sa.String(length=5), nullable=False, server_default='en'))
    op.add_column('users', sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'))
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes for new user columns
    op.create_index('idx_user_preferred_language', 'users', ['preferred_language'])
    op.create_index('idx_user_last_activity', 'users', ['last_activity_at'])
    op.create_index('idx_user_onboarding', 'users', ['onboarding_completed'])


def downgrade() -> None:
    # Remove user indexes
    op.drop_index('idx_user_onboarding', table_name='users')
    op.drop_index('idx_user_last_activity', table_name='users')
    op.drop_index('idx_user_preferred_language', table_name='users')
    
    # Remove user columns
    op.drop_column('users', 'last_activity_at')
    op.drop_column('users', 'two_factor_enabled')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'onboarding_completed_at')
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'timezone')
    op.drop_column('users', 'preferred_language')
    
    # Remove search trigger and function
    op.execute('DROP TRIGGER IF EXISTS documents_search_vector_trigger ON documents')
    op.execute('DROP FUNCTION IF EXISTS documents_search_vector_update()')
    
    # Remove search index
    op.execute('DROP INDEX IF EXISTS idx_documents_search')
    
    # Remove document indexes
    op.drop_index('idx_document_duplicate', table_name='documents')
    op.drop_index('idx_document_type', table_name='documents')
    op.drop_index('idx_document_file_hash', table_name='documents')
    
    # Remove foreign key
    op.drop_constraint('fk_documents_duplicate_of', 'documents', type_='foreignkey')
    
    # Remove document columns
    op.drop_column('documents', 'search_vector')
    op.drop_column('documents', 'last_accessed_at')
    op.drop_column('documents', 'download_count')
    op.drop_column('documents', 'web_view_link')
    op.drop_column('documents', 'duplicate_of_document_id')
    op.drop_column('documents', 'is_duplicate')
    op.drop_column('documents', 'document_type')
    op.drop_column('documents', 'page_count')
    op.drop_column('documents', 'preview_url')
    op.drop_column('documents', 'thumbnail_url')
    op.drop_column('documents', 'original_filename')
    op.drop_column('documents', 'file_hash')