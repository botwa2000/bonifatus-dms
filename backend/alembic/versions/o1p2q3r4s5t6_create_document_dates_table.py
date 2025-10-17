"""Create document_dates table for secondary date extraction

Revision ID: o1p2q3r4s5t6
Revises: n0o1p2q3r4s5
Create Date: 2025-10-17 14:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'o1p2q3r4s5t6'
down_revision = 'n0o1p2q3r4s5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create document_dates table for storing multiple dates per document"""

    op.create_table('document_dates',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('date_type', sa.String(50), nullable=False),
        sa.Column('date_value', sa.Date(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('extracted_text', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for efficient queries
    op.create_index('idx_document_dates_document_id', 'document_dates', ['document_id'])
    op.create_index('idx_document_dates_date_type', 'document_dates', ['date_type'])
    op.create_index('idx_document_dates_date_value', 'document_dates', ['date_value'])


def downgrade() -> None:
    """Drop document_dates table"""

    op.drop_index('idx_document_dates_date_value', table_name='document_dates')
    op.drop_index('idx_document_dates_date_type', table_name='document_dates')
    op.drop_index('idx_document_dates_document_id', table_name='document_dates')
    op.drop_table('document_dates')
