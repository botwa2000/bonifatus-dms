# backend/alembic/versions/h3c4d5e6f7g8_add_priority2_tables.py
"""Add priority 2 tables: collections, relationships, sharing

Revision ID: h3c4d5e6f7g8
Revises: g2b3c4d5e6f7
Create Date: 2025-10-04 12:03:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'h3c4d5e6f7g8'
down_revision = 'g2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Collections (Folders)
    op.create_table('collections',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color_hex', sa.String(length=7), nullable=False, server_default='#6B7280'),
        sa.Column('icon_name', sa.String(length=50), nullable=False, server_default='folder'),
        sa.Column('parent_collection_id', UUID(as_uuid=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_smart', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('smart_rules', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_collection_user', 'collections', ['user_id'])
    op.create_index('idx_collection_parent', 'collections', ['parent_collection_id'])
    op.create_index('idx_collection_smart', 'collections', ['is_smart'])
    
    # Collection Documents (many-to-many)
    op.create_table('collection_documents',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('collection_id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('added_by_rule', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collection_id', 'document_id', name='uq_collection_document')
    )
    op.create_index('idx_collection_docs_collection', 'collection_documents', ['collection_id'])
    op.create_index('idx_collection_docs_document', 'collection_documents', ['document_id'])
    
    # Document Relationships
    op.create_table('document_relationships',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('parent_document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('child_document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('relationship_metadata', sa.Text(), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['child_document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('parent_document_id != child_document_id', name='check_not_self_related'),
        sa.UniqueConstraint('parent_document_id', 'child_document_id', 'relationship_type', name='uq_doc_relationship')
    )
    op.create_index('idx_doc_rel_parent', 'document_relationships', ['parent_document_id'])
    op.create_index('idx_doc_rel_child', 'document_relationships', ['child_document_id'])
    op.create_index('idx_doc_rel_type', 'document_relationships', ['relationship_type'])
    
    # Document Shares
    op.create_table('document_shares',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('shared_by_user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('shared_with_email', sa.String(length=255), nullable=False),
        sa.Column('shared_with_user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('permission_level', sa.String(length=20), nullable=False),
        sa.Column('share_token', sa.String(length=255), nullable=True),
        sa.Column('share_url', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_with_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('share_token'),
        sa.CheckConstraint("permission_level IN ('view', 'comment', 'edit')", name='check_permission_level')
    )
    op.create_index('idx_doc_shares_doc', 'document_shares', ['document_id'])
    op.create_index('idx_doc_shares_by_user', 'document_shares', ['shared_by_user_id'])
    op.create_index('idx_doc_shares_with_email', 'document_shares', ['shared_with_email'])
    op.create_index('idx_doc_shares_token', 'document_shares', ['share_token'])
    op.create_index('idx_doc_shares_active', 'document_shares', ['is_active', 'expires_at'])


def downgrade() -> None:
    op.drop_index('idx_doc_shares_active', table_name='document_shares')
    op.drop_index('idx_doc_shares_token', table_name='document_shares')
    op.drop_index('idx_doc_shares_with_email', table_name='document_shares')
    op.drop_index('idx_doc_shares_by_user', table_name='document_shares')
    op.drop_index('idx_doc_shares_doc', table_name='document_shares')
    op.drop_table('document_shares')
    
    op.drop_index('idx_doc_rel_type', table_name='document_relationships')
    op.drop_index('idx_doc_rel_child', table_name='document_relationships')
    op.drop_index('idx_doc_rel_parent', table_name='document_relationships')
    op.drop_table('document_relationships')
    
    op.drop_index('idx_collection_docs_document', table_name='collection_documents')
    op.drop_index('idx_collection_docs_collection', table_name='collection_documents')
    op.drop_table('collection_documents')
    
    op.drop_index('idx_collection_smart', table_name='collections')
    op.drop_index('idx_collection_parent', table_name='collections')
    op.drop_index('idx_collection_user', table_name='collections')
    op.drop_table('collections')