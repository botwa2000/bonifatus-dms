"""add multi-user support with teams and cloud-agnostic sharing

Revision ID: 043_add_multi_user_support
Revises: 042_add_email_processing_to_user
Create Date: 2025-12-13 22:45:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

revision = '043_add_multi_user_support'
down_revision = '042_add_email_processing_to_user'
branch_labels = None
depends_on = None


def upgrade():
    # Add cloud-agnostic fields to users table
    op.add_column('users', sa.Column('cloud_provider', sa.String(50), nullable=True, server_default='google_drive'))
    op.add_column('users', sa.Column('cloud_app_folder_id', sa.String(255), nullable=True))

    # Migrate existing google_drive_file_id data to cloud_app_folder_id if needed
    # Users with Google Drive enabled should have their folder tracked

    # Add max_team_members to tier_plans
    op.add_column('tier_plans', sa.Column('max_team_members', sa.Integer, nullable=True, server_default='0'))

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('owner_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('idx_teams_owner_id', 'teams', ['owner_id'])

    # Create team_members table
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('team_id', sa.Integer, sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='viewer'),
        sa.Column('cloud_provider', sa.String(50), nullable=True),
        sa.Column('cloud_account_email', sa.String(255), nullable=True),
        sa.Column('invited_by', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('last_access_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_member')
    )
    op.create_index('idx_team_members_team_id', 'team_members', ['team_id'])
    op.create_index('idx_team_members_user_id', 'team_members', ['user_id'])
    op.create_index('idx_team_members_status', 'team_members', ['status'])

    # Create team_invitations table
    op.create_table(
        'team_invitations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('team_id', sa.Integer, sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('invited_by', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token', sa.String(255), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('idx_team_invitations_token', 'team_invitations', ['token'])
    op.create_index('idx_team_invitations_email', 'team_invitations', ['email'])

    # Create cloud_permissions table (tracks folder-level permissions)
    op.create_table(
        'cloud_permissions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('owner_user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('shared_with_user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('team_id', sa.Integer, sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=True),
        sa.Column('cloud_provider', sa.String(50), nullable=False),
        sa.Column('folder_id', sa.String(255), nullable=False),
        sa.Column('permission_id', sa.String(255), nullable=True),
        sa.Column('permission_role', sa.String(50), nullable=False, server_default='reader'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('idx_cloud_permissions_owner', 'cloud_permissions', ['owner_user_id'])
    op.create_index('idx_cloud_permissions_shared_with', 'cloud_permissions', ['shared_with_user_id'])
    op.create_index('idx_cloud_permissions_status', 'cloud_permissions', ['status'])

    # Create access_logs table (audit trail)
    op.create_table(
        'access_logs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('document_id', sa.Integer, sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('idx_access_logs_user_id', 'access_logs', ['user_id'])
    op.create_index('idx_access_logs_document_id', 'access_logs', ['document_id'])
    op.create_index('idx_access_logs_accessed_at', 'access_logs', ['accessed_at'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('access_logs')
    op.drop_table('cloud_permissions')
    op.drop_table('team_invitations')
    op.drop_table('team_members')
    op.drop_table('teams')

    # Remove columns from tier_plans
    op.drop_column('tier_plans', 'max_team_members')

    # Remove columns from users
    op.drop_column('users', 'cloud_app_folder_id')
    op.drop_column('users', 'cloud_provider')
