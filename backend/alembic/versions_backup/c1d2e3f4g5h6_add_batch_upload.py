# backend/alembic/versions/c1d2e3f4g5h6_add_batch_upload.py
"""Add batch upload tracking

Revision ID: c1d2e3f4g5h6
Revises: b0c1d2e3f4g5
Create Date: 2025-10-10 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c1d2e3f4g5h6'
down_revision = 'b0c1d2e3f4g5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch upload sessions
    op.create_table('upload_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_files', sa.Integer(), nullable=False),
        sa.Column('processed_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='processing'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_upload_batches_user', 'upload_batches', ['user_id', 'created_at'])
    
    # Add batch_id to documents table
    op.add_column('documents', sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_documents_batch', 'documents', 'upload_batches', ['batch_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_documents_batch', 'documents', ['batch_id'])


def downgrade() -> None:
    op.drop_index('idx_documents_batch', table_name='documents')
    op.drop_constraint('fk_documents_batch', 'documents', type_='foreignkey')
    op.drop_column('documents', 'batch_id')
    op.drop_table('upload_batches')