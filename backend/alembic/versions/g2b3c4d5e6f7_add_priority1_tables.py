# backend/alembic/versions/g2b3c4d5e6f7_add_priority1_tables.py
"""Add priority 1 tables: keywords, AI queue, quotas, entities, OCR

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2025-10-04 12:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'g2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keywords table
    op.create_table('keywords',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('keyword', sa.String(length=100), nullable=False),
        sa.Column('normalized_form', sa.String(length=100), nullable=False),
        sa.Column('language_code', sa.String(length=5), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('keyword')
    )
    op.create_index('idx_keyword_normalized', 'keywords', ['normalized_form'])
    op.create_index('idx_keyword_language', 'keywords', ['language_code'])
    op.create_index('idx_keyword_usage', 'keywords', ['usage_count'])
    
    # Document Keywords (many-to-many)
    op.create_table('document_keywords',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('keyword_id', UUID(as_uuid=True), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('is_auto_extracted', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_user_added', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('extraction_method', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('position_in_document', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['keyword_id'], ['keywords.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'keyword_id', name='uq_doc_keyword')
    )
    op.create_index('idx_doc_keywords_doc', 'document_keywords', ['document_id'])
    op.create_index('idx_doc_keywords_keyword', 'document_keywords', ['keyword_id'])
    op.create_index('idx_doc_keywords_relevance', 'document_keywords', [sa.text('relevance_score DESC')])
    
    # Document Entities
    op.create_table('document_entities',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_value', sa.Text(), nullable=False),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('position_start', sa.Integer(), nullable=True),
        sa.Column('position_end', sa.Integer(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('extraction_method', sa.String(length=50), nullable=True),
        sa.Column('language_code', sa.String(length=5), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_doc_entities_doc', 'document_entities', ['document_id'])
    op.create_index('idx_doc_entities_type', 'document_entities', ['entity_type'])
    op.create_index('idx_doc_entities_value', 'document_entities', ['entity_value'])
    
    # User Storage Quotas
    op.create_table('user_storage_quotas',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tier', sa.String(length=20), nullable=False),
        sa.Column('total_quota_bytes', sa.BigInteger(), nullable=False),
        sa.Column('used_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('largest_file_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('idx_user_quota_tier', 'user_storage_quotas', ['tier'])
    
    # OCR Results
    op.create_table('ocr_results',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('ocr_provider', sa.String(length=50), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('bounding_boxes', sa.Text(), nullable=True),
        sa.Column('detected_language', sa.String(length=5), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('provider_response', sa.Text(), nullable=True),
        sa.Column('cost_credits', sa.Numeric(10, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ocr_results_doc', 'ocr_results', ['document_id'])
    op.create_index('idx_ocr_results_page', 'ocr_results', ['document_id', 'page_number'])
    op.create_index('idx_ocr_results_provider', 'ocr_results', ['ocr_provider'])
    
    # AI Processing Queue
    op.create_table('ai_processing_queue',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_stack', sa.Text(), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_duration_ms', sa.Integer(), nullable=True),
        sa.Column('ai_provider', sa.String(length=50), nullable=True),
        sa.Column('ai_model', sa.String(length=100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('priority >= 1 AND priority <= 10', name='check_priority_range')
    )
    op.create_index('idx_ai_queue_status', 'ai_processing_queue', ['status', sa.text('priority DESC'), 'created_at'])
    op.create_index('idx_ai_queue_document', 'ai_processing_queue', ['document_id'])
    op.create_index('idx_ai_queue_task_type', 'ai_processing_queue', ['task_type', 'status'])


def downgrade() -> None:
    op.drop_index('idx_ai_queue_task_type', table_name='ai_processing_queue')
    op.drop_index('idx_ai_queue_document', table_name='ai_processing_queue')
    op.drop_index('idx_ai_queue_status', table_name='ai_processing_queue')
    op.drop_table('ai_processing_queue')
    
    op.drop_index('idx_ocr_results_provider', table_name='ocr_results')
    op.drop_index('idx_ocr_results_page', table_name='ocr_results')
    op.drop_index('idx_ocr_results_doc', table_name='ocr_results')
    op.drop_table('ocr_results')
    
    op.drop_index('idx_user_quota_tier', table_name='user_storage_quotas')
    op.drop_table('user_storage_quotas')
    
    op.drop_index('idx_doc_entities_value', table_name='document_entities')
    op.drop_index('idx_doc_entities_type', table_name='document_entities')
    op.drop_index('idx_doc_entities_doc', table_name='document_entities')
    op.drop_table('document_entities')
    
    op.drop_index('idx_doc_keywords_relevance', table_name='document_keywords')
    op.drop_index('idx_doc_keywords_keyword', table_name='document_keywords')
    op.drop_index('idx_doc_keywords_doc', table_name='document_keywords')
    op.drop_table('document_keywords')
    
    op.drop_index('idx_keyword_usage', table_name='keywords')
    op.drop_index('idx_keyword_language', table_name='keywords')
    op.drop_index('idx_keyword_normalized', table_name='keywords')
    op.drop_table('keywords')