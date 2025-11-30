"""add entity filtering tables

Revision ID: 028_entity_filtering
Revises: 027_billing_cycle_email
Create Date: 2025-11-29 00:00:00

Entity Filtering Tables:
- entity_field_labels: Filter out common field labels (IBAN, BIC, etc.)
- entity_invalid_patterns: Filter out patterns like tax IDs, codes
- entity_confidence_thresholds: Minimum confidence per language/type
- entity_blacklist: User-reported incorrect extractions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '028_entity_filtering'
down_revision = '027_billing_cycle_email'
branch_labels = None
depends_on = None


def upgrade():
    # Create entity_field_labels table
    op.create_table(
        'entity_field_labels',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('label_text', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('language', 'label_text', name='uq_entity_field_label')
    )

    # Create entity_invalid_patterns table
    op.create_table(
        'entity_invalid_patterns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('regex_pattern', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('language', 'entity_type', 'regex_pattern', name='uq_entity_invalid_pattern')
    )

    # Create entity_confidence_thresholds table
    op.create_table(
        'entity_confidence_thresholds',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('min_confidence', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('language', 'entity_type', name='uq_entity_confidence_threshold')
    )

    # Create entity_blacklist table
    op.create_table(
        'entity_blacklist',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('entity_value', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('language', 'entity_value', 'entity_type', name='uq_entity_blacklist')
    )

    # Create indexes for better query performance
    op.create_index('idx_entity_field_labels_language', 'entity_field_labels', ['language'])
    op.create_index('idx_entity_invalid_patterns_language_type', 'entity_invalid_patterns', ['language', 'entity_type'])
    op.create_index('idx_entity_confidence_language_type', 'entity_confidence_thresholds', ['language', 'entity_type'])
    op.create_index('idx_entity_blacklist_language', 'entity_blacklist', ['language'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_entity_blacklist_language')
    op.drop_index('idx_entity_confidence_language_type')
    op.drop_index('idx_entity_invalid_patterns_language_type')
    op.drop_index('idx_entity_field_labels_language')

    # Drop tables
    op.drop_table('entity_blacklist')
    op.drop_table('entity_confidence_thresholds')
    op.drop_table('entity_invalid_patterns')
    op.drop_table('entity_field_labels')
