"""add user delegates and access logs

Revision ID: 043_add_user_delegates
Revises: 042_add_email_processing_to_user
Create Date: 2025-12-15 19:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '043_add_user_delegates'
down_revision = '042_add_email_processing_to_user'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_delegates table
    op.create_table('user_delegates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('delegate_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('delegate_email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='viewer', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),

        # Invitation management
        sa.Column('invitation_token', sa.String(length=100), nullable=True),
        sa.Column('invitation_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invitation_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invitation_accepted_at', sa.DateTime(timezone=True), nullable=True),

        # Access management
        sa.Column('access_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),

        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['delegate_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id']),
        sa.CheckConstraint("role IN ('viewer', 'editor', 'owner')", name='check_role'),
        sa.CheckConstraint("status IN ('pending', 'active', 'revoked')", name='check_status'),
        sa.CheckConstraint('owner_user_id != delegate_user_id', name='check_different_users'),
        sa.UniqueConstraint('owner_user_id', 'delegate_email', name='uq_owner_delegate_email'),
        sa.UniqueConstraint('invitation_token', name='uq_invitation_token')
    )

    # Create indexes for user_delegates
    op.create_index('idx_delegates_owner', 'user_delegates', ['owner_user_id'])
    op.create_index('idx_delegates_delegate_user', 'user_delegates', ['delegate_user_id'])
    op.create_index('idx_delegates_delegate_email', 'user_delegates', ['delegate_email'])
    op.create_index('idx_delegates_status', 'user_delegates', ['status'])
    op.create_index('idx_delegates_invitation_token', 'user_delegates', ['invitation_token'])
    op.create_index('idx_delegates_access_expires', 'user_delegates', ['access_expires_at'],
                    postgresql_where=sa.text('access_expires_at IS NOT NULL'))

    # Create delegate_access_logs table for audit trail
    op.create_table('delegate_access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('delegate_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['delegate_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.CheckConstraint("action IN ('view', 'download', 'search')", name='check_action')
    )

    # Create indexes for delegate_access_logs
    op.create_index('idx_access_logs_delegate', 'delegate_access_logs', ['delegate_user_id', 'accessed_at'])
    op.create_index('idx_access_logs_owner', 'delegate_access_logs', ['owner_user_id', 'accessed_at'])
    op.create_index('idx_access_logs_document', 'delegate_access_logs', ['document_id'])


def downgrade():
    # Drop delegate_access_logs table and its indexes
    op.drop_index('idx_access_logs_document', table_name='delegate_access_logs')
    op.drop_index('idx_access_logs_owner', table_name='delegate_access_logs')
    op.drop_index('idx_access_logs_delegate', table_name='delegate_access_logs')
    op.drop_table('delegate_access_logs')

    # Drop user_delegates table and its indexes
    op.drop_index('idx_delegates_access_expires', table_name='user_delegates')
    op.drop_index('idx_delegates_invitation_token', table_name='user_delegates')
    op.drop_index('idx_delegates_status', table_name='user_delegates')
    op.drop_index('idx_delegates_delegate_email', table_name='user_delegates')
    op.drop_index('idx_delegates_delegate_user', table_name='user_delegates')
    op.drop_index('idx_delegates_owner', table_name='user_delegates')
    op.drop_table('user_delegates')
