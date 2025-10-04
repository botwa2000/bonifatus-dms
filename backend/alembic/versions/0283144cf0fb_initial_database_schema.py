# backend/alembic/versions/0283144cf0fb_initial_database_schema.py
"""Initial database schema with dynamic multilingual support

Revision ID: 0283144cf0fb
Revises: 
Create Date: 2025-10-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0283144cf0fb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Localization strings table
    op.create_table('localization_strings',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('string_key', sa.String(length=100), nullable=False),
        sa.Column('language_code', sa.String(length=5), nullable=False),
        sa.Column('string_value', sa.Text(), nullable=False),
        sa.Column('context', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_localization_key_lang', 'localization_strings', ['string_key', 'language_code'])
    op.create_index('idx_localization_language', 'localization_strings', ['language_code'])
    op.create_index('idx_localization_key', 'localization_strings', ['string_key'])
    
    # System settings table
    op.create_table('system_settings',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('setting_key', sa.String(length=100), nullable=False),
        sa.Column('setting_value', sa.Text(), nullable=False),
        sa.Column('data_type', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('setting_key')
    )
    op.create_index('idx_system_setting_key', 'system_settings', ['setting_key'])
    op.create_index('idx_system_setting_category', 'system_settings', ['category'])
    
    # Users table
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('google_id', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('profile_picture', sa.Text(), nullable=True),
        sa.Column('tier', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_ip', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('google_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_index('idx_user_google_id', 'users', ['google_id'])
    op.create_index('idx_user_tier', 'users', ['tier'])
    
    # Categories table (dynamic multilingual)
    op.create_table('categories',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('reference_key', sa.String(length=100), nullable=False),
        sa.Column('color_hex', sa.String(length=7), nullable=False, server_default='#6B7280'),
        sa.Column('icon_name', sa.String(length=50), nullable=False, server_default='folder'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference_key')
    )
    op.create_index('idx_category_active', 'categories', ['is_active'])
    op.create_index('idx_category_system', 'categories', ['is_system'])
    op.create_index('idx_category_user_id', 'categories', ['user_id'])
    op.create_index('idx_category_reference_key', 'categories', ['reference_key'])
    
    # Category translations table
    op.create_table('category_translations',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', UUID(as_uuid=True), nullable=False),
        sa.Column('language_code', sa.String(length=5), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id', 'language_code', name='uq_category_language')
    )
    op.create_index('idx_category_trans_category_id', 'category_translations', ['category_id'])
    op.create_index('idx_category_trans_lang', 'category_translations', ['language_code'])
    
    # User settings table
    op.create_table('user_settings',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('setting_key', sa.String(length=100), nullable=False),
        sa.Column('setting_value', sa.Text(), nullable=False),
        sa.Column('data_type', sa.String(length=20), nullable=False, server_default='string'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_setting_user_key', 'user_settings', ['user_id', 'setting_key'])
    
    # Documents table
    op.create_table('documents',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('google_drive_file_id', sa.String(length=100), nullable=False),
        sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('primary_language', sa.String(length=5), nullable=True),
        sa.Column('detected_languages', sa.Text(), nullable=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('google_drive_file_id')
    )
    op.create_index('idx_document_category_id', 'documents', ['category_id'])
    op.create_index('idx_document_google_drive', 'documents', ['google_drive_file_id'])
    op.create_index('idx_document_status', 'documents', ['processing_status'])
    op.create_index('idx_document_user_id', 'documents', ['user_id'])
    op.create_index('idx_document_primary_lang', 'documents', ['primary_language'])
    
    # Audit logs table
    op.create_table('audit_logs',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_method', sa.String(length=10), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('old_values', sa.Text(), nullable=True),
        sa.Column('new_values', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('user_locale', sa.String(length=5), nullable=True),
        sa.Column('extra_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_timestamp', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_status', 'audit_logs', ['status'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    
    # Document languages table
    op.create_table('document_languages',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('language_code', sa.String(length=5), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('ai_category_suggestion', UUID(as_uuid=True), nullable=True),
        sa.Column('ai_confidence', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ai_category_suggestion'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_doc_lang_code', 'document_languages', ['language_code'])
    op.create_index('idx_doc_lang_document', 'document_languages', ['document_id'])
    op.create_index('idx_doc_lang_primary', 'document_languages', ['document_id', 'is_primary'])


def downgrade() -> None:
    op.drop_index('idx_doc_lang_primary', table_name='document_languages')
    op.drop_index('idx_doc_lang_document', table_name='document_languages')
    op.drop_index('idx_doc_lang_code', table_name='document_languages')
    op.drop_table('document_languages')
    
    op.drop_index('idx_audit_action', table_name='audit_logs')
    op.drop_index('idx_audit_status', table_name='audit_logs')
    op.drop_index('idx_audit_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_resource', table_name='audit_logs')
    op.drop_index('idx_audit_user_action', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index('idx_document_primary_lang', table_name='documents')
    op.drop_index('idx_document_user_id', table_name='documents')
    op.drop_index('idx_document_status', table_name='documents')
    op.drop_index('idx_document_google_drive', table_name='documents')
    op.drop_index('idx_document_category_id', table_name='documents')
    op.drop_table('documents')
    
    op.drop_index('idx_user_setting_user_key', table_name='user_settings')
    op.drop_table('user_settings')
    
    op.drop_index('idx_category_trans_lang', table_name='category_translations')
    op.drop_index('idx_category_trans_category_id', table_name='category_translations')
    op.drop_table('category_translations')
    
    op.drop_index('idx_category_reference_key', table_name='categories')
    op.drop_index('idx_category_user_id', table_name='categories')
    op.drop_index('idx_category_system', table_name='categories')
    op.drop_index('idx_category_active', table_name='categories')
    op.drop_table('categories')
    
    op.drop_index('idx_user_tier', table_name='users')
    op.drop_index('idx_user_google_id', table_name='users')
    op.drop_index('idx_user_email', table_name='users')
    op.drop_table('users')
    
    op.drop_index('idx_system_setting_category', table_name='system_settings')
    op.drop_index('idx_system_setting_key', table_name='system_settings')
    op.drop_table('system_settings')
    
    op.drop_index('idx_localization_key', table_name='localization_strings')
    op.drop_index('idx_localization_language', table_name='localization_strings')
    op.drop_index('idx_localization_key_lang', table_name='localization_strings')
    op.drop_table('localization_strings')