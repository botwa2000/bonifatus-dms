# database/migrations/001_initial_schema.py
"""
Bonifatus DMS - Initial Database Schema Migration
Alembic migration for creating initial database structure
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial database schema"""
    
    # Create custom types
    user_tier = postgresql.ENUM('free', 'premium_trial', 'premium', 'admin', name='user_tier')
    document_status = postgresql.ENUM('uploading', 'processing', 'ready', 'error', 'archived', name='document_status')
    
    user_tier.create(op.get_bind())
    document_status.create(op.get_bind())
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('google_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('tier', user_tier, nullable=False, server_default='free'),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monthly_uploads', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_used_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trial_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('google_drive_token', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('google_drive_folder_id', sa.String(length=255), nullable=True),
        sa.Column('google_drive_connected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('theme', sa.String(length=20), nullable=False, server_default='light'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name_en', sa.String(length=100), nullable=False),
        sa.Column('name_de', sa.String(length=100), nullable=False),
        sa.Column('description_en', sa.Text(), nullable=True),
        sa.Column('description_de', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=False, server_default='#6B7280'),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_system_category', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('google_drive_file_id', sa.String(length=255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_extension', sa.String(length=10), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('status', document_status, nullable=False, server_default='uploading'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('extracted_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('language_detected', sa.String(length=10), nullable=True),
        sa.Column('ai_confidence_score', sa.Float(), nullable=True),
        sa.Column('ai_suggested_category', sa.Integer(), nullable=True),
        sa.Column('ai_extracted_entities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('google_drive_modified_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('auto_categorization_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ocr_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ai_suggestions_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_notifications', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('processing_notifications', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('weekly_summary', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_frequency_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('create_subfolder_structure', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('backup_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('documents_per_page', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('default_view_mode', sa.String(length=20), nullable=False, server_default='grid'),
        sa.Column('show_processing_details', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('analytics_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('improve_ai_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('data_retention_days', sa.Integer(), nullable=False, server_default='365'),
        sa.Column('max_upload_size_mb', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('concurrent_uploads', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('custom_categories_limit', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('free_tier_document_limit', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('premium_trial_document_limit', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('premium_document_limit', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('free_tier_monthly_uploads', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('premium_monthly_uploads', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_file_size_mb', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('max_concurrent_processing', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('ocr_monthly_limit', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('ai_processing_monthly_limit', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('ocr_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ai_categorization_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('google_drive_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('user_registration_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('maintenance_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('supported_languages', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='["en", "de"]'),
        sa.Column('google_api_rate_limit', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('session_timeout_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('database_backup_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_reporting_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('performance_monitoring_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=50), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_user_email', 'users', ['email'], unique=True)
    op.create_index('idx_user_google_id', 'users', ['google_id'], unique=True)
    op.create_index('idx_user_tier', 'users', ['tier'])
    op.create_index('idx_user_active', 'users', ['is_active'])
    op.create_index('idx_user_created', 'users', ['created_at'])
    
    op.create_index('idx_category_user', 'categories', ['user_id'])
    op.create_index('idx_category_system', 'categories', ['is_system_category'])
    op.create_index('idx_category_active', 'categories', ['is_active'])
    op.create_index('idx_category_sort', 'categories', ['sort_order'])
    
    op.create_index('idx_document_user', 'documents', ['user_id'])
    op.create_index('idx_document_category', 'documents', ['category_id'])
    op.create_index('idx_document_status', 'documents', ['status'])
    op.create_index('idx_document_google_id', 'documents', ['google_drive_file_id'], unique=True)
    op.create_index('idx_document_filename', 'documents', ['filename'])
    op.create_index('idx_document_created', 'documents', ['created_at'])
    op.create_index('idx_document_updated', 'documents', ['updated_at'])
    op.create_index('idx_document_favorite', 'documents', ['is_favorite'])
    
    op.create_index('idx_user_settings_user', 'user_settings', ['user_id'], unique=True)
    
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_success', 'audit_logs', ['success'])
    
    # Create GIN indexes for JSONB columns and full-text search
    op.execute('CREATE INDEX idx_document_keywords ON documents USING gin(extracted_keywords)')
    op.execute('CREATE INDEX idx_document_user_keywords ON documents USING gin(user_keywords)')
    op.execute("CREATE INDEX idx_document_text_search ON documents USING gin(to_tsvector('english', extracted_text))")
    op.execute("CREATE INDEX idx_document_title_search ON documents USING gin(to_tsvector('english', title))")


def downgrade():
    """Drop all tables and types"""
    
    # Drop indexes
    op.drop_index('idx_document_title_search')
    op.drop_index('idx_document_text_search') 
    op.drop_index('idx_document_user_keywords')
    op.drop_index('idx_document_keywords')
    op.drop_index('idx_audit_success')
    op.drop_index('idx_audit_created')
    op.drop_index('idx_audit_action')
    op.drop_index('idx_audit_user')
    op.drop_index('idx_user_settings_user')
    op.drop_index('idx_document_favorite')
    op.drop_index('idx_document_updated')
    op.drop_index('idx_document_created')
    op.drop_index('idx_document_filename')
    op.drop_index('idx_document_google_id')
    op.drop_index('idx_document_status')
    op.drop_index('idx_document_category')
    op.drop_index('idx_document_user')
    op.drop_index('idx_category_sort')
    op.drop_index('idx_category_active')
    op.drop_index('idx_category_system')
    op.drop_index('idx_category_user')
    op.drop_index('idx_user_created')
    op.drop_index('idx_user_active')
    op.drop_index('idx_user_tier')
    op.drop_index('idx_user_google_id')
    op.drop_index('idx_user_email')
    
    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('system_settings')
    op.drop_table('user_settings')
    op.drop_table('documents')
    op.drop_table('categories')
    op.drop_table('users')
    
    # Drop custom types
    sa.Enum(name='document_status').drop(op.get_bind(), checkfirst=False)
    sa.Enum(name='user_tier').drop(op.get_bind(), checkfirst=False)