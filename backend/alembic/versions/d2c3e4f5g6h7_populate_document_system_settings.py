"""Populate document management system settings

Revision ID: d2c3e4f5g6h7
Revises: c1a2b3d4e5f6
Create Date: 2025-09-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'd2c3e4f5g6h7'
down_revision = 'c1a2b3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insert document management system settings"""
    
    now = datetime.utcnow()
    
    # Define system settings for document management
    document_settings = [
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'default_documents_page_size',
            'setting_value': '20',
            'data_type': 'integer',
            'description': 'Default number of documents per page in listings',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'default_documents_sort_field',
            'setting_value': 'created_at',
            'data_type': 'string',
            'description': 'Default sort field for document listings',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'default_documents_sort_order',
            'setting_value': 'desc',
            'data_type': 'string',
            'description': 'Default sort order for document listings',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'max_batch_operation_size',
            'setting_value': '50',
            'data_type': 'integer',
            'description': 'Maximum number of documents in batch operations',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'allowed_batch_operations',
            'setting_value': 'delete,update_category,reprocess,export',
            'data_type': 'string',
            'description': 'Comma-separated list of allowed batch operations',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'allowed_sort_fields',
            'setting_value': 'created_at,updated_at,title,file_size,processing_status',
            'data_type': 'string',
            'description': 'Comma-separated list of allowed sort fields',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'allowed_sort_orders',
            'setting_value': 'asc,desc',
            'data_type': 'string',
            'description': 'Comma-separated list of allowed sort orders',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'supported_document_types',
            'setting_value': 'pdf,doc,docx,txt,jpg,jpeg,png,tiff,bmp',
            'data_type': 'string',
            'description': 'Comma-separated list of supported document file types',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'ocr_language_hints',
            'setting_value': 'en,de,ru',
            'data_type': 'string',
            'description': 'Comma-separated list of OCR language hints',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'document_processing_timeout_seconds',
            'setting_value': '300',
            'data_type': 'integer',
            'description': 'Timeout for document processing in seconds',
            'is_public': False,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'enable_ai_categorization',
            'setting_value': 'true',
            'data_type': 'boolean',
            'description': 'Enable AI-powered document categorization',
            'is_public': True,
            'category': 'ai_features',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'ai_confidence_threshold',
            'setting_value': '75',
            'data_type': 'integer',
            'description': 'Minimum AI confidence score for auto-categorization',
            'is_public': True,
            'category': 'ai_features',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'enable_keyword_extraction',
            'setting_value': 'true',
            'data_type': 'boolean',
            'description': 'Enable automatic keyword extraction from documents',
            'is_public': True,
            'category': 'ai_features',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'max_keywords_per_document',
            'setting_value': '20',
            'data_type': 'integer',
            'description': 'Maximum number of keywords to extract per document',
            'is_public': True,
            'category': 'ai_features',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'enable_language_detection',
            'setting_value': 'true',
            'data_type': 'boolean',
            'description': 'Enable automatic language detection for documents',
            'is_public': True,
            'category': 'ai_features',
            'created_at': now,
            'updated_at': now
        }
    ]
    
    # Insert document management settings using raw SQL
    for setting in document_settings:
        op.execute(f"""
            INSERT INTO system_settings (
                id, setting_key, setting_value, data_type, description, 
                is_public, category, created_at, updated_at
            ) VALUES (
                '{setting['id']}', '{setting['setting_key']}', '{setting['setting_value']}', 
                '{setting['data_type']}', '{setting['description']}', {setting['is_public']}, 
                '{setting['category']}', '{setting['created_at']}', '{setting['updated_at']}'
            )
        """)


def downgrade() -> None:
    """Remove document management system settings"""
    document_settings_to_remove = [
        'default_documents_page_size', 'default_documents_sort_field', 'default_documents_sort_order',
        'max_batch_operation_size', 'allowed_batch_operations', 'allowed_sort_fields', 
        'allowed_sort_orders', 'supported_document_types', 'ocr_language_hints',
        'document_processing_timeout_seconds', 'enable_ai_categorization', 'ai_confidence_threshold',
        'enable_keyword_extraction', 'max_keywords_per_document', 'enable_language_detection'
    ]
    
    for setting_key in document_settings_to_remove:
        op.execute(f"DELETE FROM system_settings WHERE setting_key = '{setting_key}'")