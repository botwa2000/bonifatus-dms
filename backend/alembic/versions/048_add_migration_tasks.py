"""Add migration_tasks table for cloud storage provider migration tracking

Revision ID: 048_add_migration_tasks
Revises: 047_provider_email_templates
Create Date: 2025-12-26 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '048_add_migration_tasks'
down_revision = '047_provider_email_templates'
branch_labels = None
depends_on = None


def upgrade():
    """Create migration_tasks table for tracking provider migrations"""

    op.create_table(
        'migration_tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Provider information
        sa.Column('from_provider', sa.String(50), nullable=False),
        sa.Column('to_provider', sa.String(50), nullable=False),

        # Progress tracking
        sa.Column('total_documents', sa.Integer, nullable=False, server_default='0'),
        sa.Column('processed_documents', sa.Integer, nullable=False, server_default='0'),
        sa.Column('successful_documents', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failed_documents', sa.Integer, nullable=False, server_default='0'),

        # Status tracking
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('current_document_name', sa.String(500), nullable=True),

        # Detailed results
        sa.Column('results', JSONB, nullable=True),

        # Folder deletion tracking
        sa.Column('folder_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('folder_deletion_attempted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('folder_deletion_error', sa.Text, nullable=True),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Error tracking
        sa.Column('error_message', sa.Text, nullable=True),

        # Celery task ID
        sa.Column('celery_task_id', sa.String(255), nullable=True),

        # Timestamps (from TimestampMixin)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'partial', 'failed')",
            name='check_migration_status'
        ),
    )

    # Create indexes
    op.create_index('idx_migration_user_status', 'migration_tasks', ['user_id', 'status'])
    op.create_index('idx_migration_celery_task', 'migration_tasks', ['celery_task_id'])
    op.create_index('idx_migration_providers', 'migration_tasks', ['from_provider', 'to_provider'])
    op.create_index('idx_migration_created', 'migration_tasks', ['created_at'])


def downgrade():
    """Drop migration_tasks table"""

    # Drop indexes first
    op.drop_index('idx_migration_created', 'migration_tasks')
    op.drop_index('idx_migration_providers', 'migration_tasks')
    op.drop_index('idx_migration_celery_task', 'migration_tasks')
    op.drop_index('idx_migration_user_status', 'migration_tasks')

    # Drop table
    op.drop_table('migration_tasks')
