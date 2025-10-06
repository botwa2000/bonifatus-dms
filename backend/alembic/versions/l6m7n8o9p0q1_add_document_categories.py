# backend/alembic/versions/l6m7n8o9p0q1_add_document_categories.py
"""Add document_categories many-to-many relationship

Revision ID: l6m7n8o9p0q1
Revises: k1l2m3n4o5p6
Create Date: 2025-10-06 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'l6m7n8o9p0q1'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Document Categories (many-to-many)
    op.create_table('document_categories',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', UUID(as_uuid=True), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('assigned_by_ai', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'category_id', name='uq_document_category')
    )
    op.create_index('idx_doc_cats_document', 'document_categories', ['document_id'])
    op.create_index('idx_doc_cats_category', 'document_categories', ['category_id'])
    op.create_index('idx_doc_cats_primary', 'document_categories', ['document_id', 'is_primary'])
    
    # Migrate existing data from documents.category_id to document_categories
    op.execute("""
        INSERT INTO document_categories (id, document_id, category_id, is_primary, assigned_at)
        SELECT gen_random_uuid(), id, category_id, true, created_at
        FROM documents
        WHERE category_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index('idx_doc_cats_primary', table_name='document_categories')
    op.drop_index('idx_doc_cats_category', table_name='document_categories')
    op.drop_index('idx_doc_cats_document', table_name='document_categories')
    op.drop_table('document_categories')