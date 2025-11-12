"""enhance upload_batches for async processing

Revision ID: 018_batch_jobs
Revises: 0a0cb9be176d
Create Date: 2025-11-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '018_batch_jobs'
down_revision = '0a0cb9be176d'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add new columns to existing upload_batches table
    op.add_column('upload_batches', sa.Column('results', JSONB, nullable=True))
    op.add_column('upload_batches', sa.Column('error_message', sa.Text, nullable=True))
    op.add_column('upload_batches', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('upload_batches', sa.Column('current_file_index', sa.Integer, nullable=False, server_default='0'))
    op.add_column('upload_batches', sa.Column('current_file_name', sa.String(500), nullable=True))

    # Update status column to allow more states
    # existing: 'processing' -> add: 'pending', 'completed', 'failed'

def downgrade() -> None:
    op.drop_column('upload_batches', 'current_file_name')
    op.drop_column('upload_batches', 'current_file_index')
    op.drop_column('upload_batches', 'started_at')
    op.drop_column('upload_batches', 'error_message')
    op.drop_column('upload_batches', 'results')
