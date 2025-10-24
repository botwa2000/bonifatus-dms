# backend/alembic/versions/i4d5e6f7g8h9_add_priority3_tables.py
"""Add priority 3 tables: tags, notifications, search history

Revision ID: i4d5e6f7g8h9
Revises: h3c4d5e6f7g8
Create Date: 2025-10-04 12:04:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'i4d5e6f7g8h9'
down_revision = 'h3c4d5e6f7g8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tags
    op.create_table('tags',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('color_hex', sa.String(length=7), nullable=False, server_default='#6B7280'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_tag_name')
    )
    op.create_index('idx_tags_user', 'tags', ['user_id'])
    op.create_index('idx_tags_usage', 'tags', ['usage_count'])
    
    # Document Tags (many-to-many)
    op.create_table('document_tags',
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', UUID(as_uuid=True), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id', 'tag_id')
    )
    op.create_index('idx_doc_tags_doc', 'document_tags', ['document_id'])
    op.create_index('idx_doc_tags_tag', 'document_tags', ['tag_id'])
    
    # Notifications
    op.create_table('notifications',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('action_url', sa.Text(), nullable=True),
        sa.Column('action_text', sa.String(length=100), nullable=True),
        sa.Column('related_document_id', UUID(as_uuid=True), nullable=True),
        sa.Column('related_user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name='check_priority')
    )
    op.create_index('idx_notifications_user', 'notifications', ['user_id', 'is_read', sa.text('created_at DESC')])
    op.create_index('idx_notifications_unread', 'notifications', ['user_id', 'is_read'], postgresql_where=sa.text('is_read = false'))
    op.create_index('idx_notifications_type', 'notifications', ['notification_type'])
    
    # Search History
    op.create_table('search_history',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('search_query', sa.Text(), nullable=False),
        sa.Column('search_type', sa.String(length=50), nullable=True),
        sa.Column('filters', sa.Text(), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('clicked_document_id', UUID(as_uuid=True), nullable=True),
        sa.Column('click_position', sa.Integer(), nullable=True),
        sa.Column('search_duration_ms', sa.Integer(), nullable=True),
        sa.Column('no_results_found', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['clicked_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_search_history_user', 'search_history', ['user_id', sa.text('created_at DESC')])
    op.create_index('idx_search_history_no_results', 'search_history', ['no_results_found'], postgresql_where=sa.text('no_results_found = true'))
    
    # Full-text search index on search_query
    op.execute("""
        CREATE INDEX idx_search_history_query ON search_history 
        USING gin(to_tsvector('english', search_query))
    """)


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS idx_search_history_query')
    
    op.drop_index('idx_search_history_no_results', table_name='search_history')
    op.drop_index('idx_search_history_user', table_name='search_history')
    op.drop_table('search_history')
    
    op.drop_index('idx_notifications_type', table_name='notifications')
    op.drop_index('idx_notifications_unread', table_name='notifications')
    op.drop_index('idx_notifications_user', table_name='notifications')
    op.drop_table('notifications')
    
    op.drop_index('idx_doc_tags_tag', table_name='document_tags')
    op.drop_index('idx_doc_tags_doc', table_name='document_tags')
    op.drop_table('document_tags')
    
    op.drop_index('idx_tags_usage', table_name='tags')
    op.drop_index('idx_tags_user', table_name='tags')
    op.drop_table('tags')