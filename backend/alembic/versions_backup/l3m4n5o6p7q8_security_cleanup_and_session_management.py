# backend/alembic/versions/l3m4n5o6p7q8_security_cleanup_and_session_management.py
"""Security cleanup and session management

Revision ID: l3m4n5o6p7q8
Revises: k1l2m3n4o5p6
Create Date: 2025-10-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

revision = 'l3m4n5o6p7q8'
down_revision = 'd3e4f5g6h7i8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop unused tables (technical debt removal)
    op.execute("DROP TABLE IF EXISTS spelling_corrections CASCADE")
    op.execute("DROP TABLE IF EXISTS ngram_patterns CASCADE")
    op.execute("DROP TABLE IF EXISTS keyword_training_data CASCADE")
    op.execute("DROP TABLE IF EXISTS category_training_data CASCADE")
    op.execute("DROP TABLE IF EXISTS language_detection_patterns CASCADE")
    op.execute("DROP TABLE IF EXISTS ocr_results CASCADE")
    
    # Rename category_term_weights to category_keywords
    op.rename_table('category_term_weights', 'category_keywords')
    
    # Rename columns in category_keywords table
    op.alter_column('category_keywords', 'term', new_column_name='keyword')
    op.alter_column('category_keywords', 'document_frequency', new_column_name='match_count')
    
    # Add new columns to category_keywords
    op.add_column('category_keywords', sa.Column('is_system_default', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('category_keywords', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('category_keywords', sa.Column('last_matched_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=64), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token_hash', name='uq_session_token')
    )
    
    # Create indexes for user_sessions
    op.create_index('idx_sessions_user', 'user_sessions', ['user_id', 'is_revoked', 'expires_at'])
    op.create_index('idx_sessions_token', 'user_sessions', ['refresh_token_hash'])
    op.create_index('idx_sessions_active', 'user_sessions', ['user_id', 'is_revoked'], 
                   postgresql_where=sa.text('is_revoked = false'))
    
    # Add security columns to users table
    op.add_column('users', sa.Column('drive_refresh_token_encrypted', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('drive_token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('google_drive_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('drive_permissions_granted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_ip_address', sa.String(length=45), nullable=True))
    op.add_column('users', sa.Column('last_user_agent', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('account_locked_until', sa.DateTime(timezone=True), nullable=True))
    
    # Add security columns to audit_logs table
    op.add_column('audit_logs', sa.Column('security_level', sa.String(length=20), nullable=True))
    op.add_column('audit_logs', sa.Column('security_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Create indexes for audit_logs security columns
    op.create_index('idx_audit_security', 'audit_logs', ['security_level', 'created_at'], 
                   postgresql_using='btree', postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_audit_suspicious', 'audit_logs', 
                   [sa.text("(security_flags->>'suspicious')")],
                   postgresql_where=sa.text("security_flags->>'suspicious' = 'true'"))


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_audit_suspicious', table_name='audit_logs')
    op.drop_index('idx_audit_security', table_name='audit_logs')
    
    # Remove audit_logs columns
    op.drop_column('audit_logs', 'security_flags')
    op.drop_column('audit_logs', 'security_level')
    
    # Remove users columns
    op.drop_column('users', 'account_locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_user_agent')
    op.drop_column('users', 'last_ip_address')
    op.drop_column('users', 'drive_permissions_granted_at')
    op.drop_column('users', 'google_drive_enabled')
    op.drop_column('users', 'drive_token_expires_at')
    op.drop_column('users', 'drive_refresh_token_encrypted')
    
    # Drop user_sessions indexes and table
    op.drop_index('idx_sessions_active', table_name='user_sessions')
    op.drop_index('idx_sessions_token', table_name='user_sessions')
    op.drop_index('idx_sessions_user', table_name='user_sessions')
    op.drop_table('user_sessions')
    
    # Remove category_keywords columns
    op.drop_column('category_keywords', 'last_matched_at')
    op.drop_column('category_keywords', 'created_at')
    op.drop_column('category_keywords', 'is_system_default')
    
    # Rename columns back
    op.alter_column('category_keywords', 'match_count', new_column_name='document_frequency')
    op.alter_column('category_keywords', 'keyword', new_column_name='term')
    
    # Rename table back
    op.rename_table('category_keywords', 'category_term_weights')
    
    # Note: We don't recreate dropped tables in downgrade as they contained technical debt