"""enhance email processing tracking

Revision ID: 041_enhance_email_tracking
Revises: 040_multi_auth_email
Create Date: 2025-12-13 12:00:00

Add enhanced tracking fields to email_processing_logs:
- Document ID linking for processed documents
- Email message ID and UID for deduplication
- Detailed error tracking (error_code, error_message)
- Notification tracking fields
- Processing metadata for AI results
- Enhanced attachment tracking (filenames)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '041_enhance_email_tracking'
down_revision = '040_multi_auth_email'
branch_labels = None
depends_on = None


def upgrade():
    # Add document ID foreign key to link processed emails with created documents
    op.add_column('email_processing_logs', sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_email_logs_document', 'email_processing_logs', 'documents', ['document_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_email_logs_document', 'email_processing_logs', ['document_id'])

    # Add email message tracking for deduplication
    op.add_column('email_processing_logs', sa.Column('email_message_id', sa.String(255), nullable=True))
    op.add_column('email_processing_logs', sa.Column('email_uid', sa.String(100), nullable=True))
    op.create_index('idx_email_logs_message_id', 'email_processing_logs', ['email_message_id'])
    op.create_index('idx_email_logs_uid', 'email_processing_logs', ['email_uid'])

    # Add enhanced error tracking
    op.add_column('email_processing_logs', sa.Column('error_code', sa.String(50), nullable=True))
    op.add_column('email_processing_logs', sa.Column('error_message', sa.Text(), nullable=True))

    # Add notification tracking
    op.add_column('email_processing_logs', sa.Column('confirmation_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('email_processing_logs', sa.Column('completion_notification_sent_at', sa.DateTime(timezone=True), nullable=True))

    # Add processing metadata for AI results and other context
    op.add_column('email_processing_logs', sa.Column('processing_metadata', postgresql.JSONB(), nullable=True))

    # Add attachment filenames array for better tracking
    op.add_column('email_processing_logs', sa.Column('attachment_filenames', postgresql.JSONB(), nullable=True))

    # Add processing timestamps for better monitoring
    op.add_column('email_processing_logs', sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('email_processing_logs', sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True))

    # Add use_count to allowed_senders for analytics
    op.add_column('allowed_senders', sa.Column('use_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    # Remove added columns in reverse order
    op.drop_column('allowed_senders', 'use_count')

    op.drop_column('email_processing_logs', 'processing_completed_at')
    op.drop_column('email_processing_logs', 'processing_started_at')
    op.drop_column('email_processing_logs', 'attachment_filenames')
    op.drop_column('email_processing_logs', 'processing_metadata')
    op.drop_column('email_processing_logs', 'completion_notification_sent_at')
    op.drop_column('email_processing_logs', 'confirmation_sent_at')
    op.drop_column('email_processing_logs', 'error_message')
    op.drop_column('email_processing_logs', 'error_code')

    op.drop_index('idx_email_logs_uid', 'email_processing_logs')
    op.drop_index('idx_email_logs_message_id', 'email_processing_logs')
    op.drop_column('email_processing_logs', 'email_uid')
    op.drop_column('email_processing_logs', 'email_message_id')

    op.drop_index('idx_email_logs_document', 'email_processing_logs')
    op.drop_constraint('fk_email_logs_document', 'email_processing_logs', type_='foreignkey')
    op.drop_column('email_processing_logs', 'document_id')
