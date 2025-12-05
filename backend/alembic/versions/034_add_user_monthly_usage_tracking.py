"""add user monthly usage tracking

Revision ID: 034_usage_tracking
Revises: 033_monthly_limits
Create Date: 2025-12-04 22:10:00.000000

Adds user_monthly_usage table to track actual usage against monthly limits:
- Pages processed
- Volume uploaded
- Translations used
- API calls made
- Automatic monthly period tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '034_usage_tracking'
down_revision = '033_monthly_limits'
branch_labels = None
depends_on = None


def upgrade():
    """Create user_monthly_usage tracking table"""
    print("\n=== Creating User Monthly Usage Tracking ===\n")

    # ============================================================
    # 1. Create user_monthly_usage table
    # ============================================================
    print("1. Creating user_monthly_usage table...")

    op.create_table(
        'user_monthly_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('month_period', sa.String(7), nullable=False),  # "2025-12"

        # Core usage metrics
        sa.Column('pages_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('volume_uploaded_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('documents_uploaded', sa.Integer(), nullable=False, server_default='0'),

        # Feature usage
        sa.Column('translations_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('api_calls_made', sa.Integer(), nullable=False, server_default='0'),

        # Period tracking
        sa.Column('period_start_date', sa.Date(), nullable=False),
        sa.Column('period_end_date', sa.Date(), nullable=False),

        # Timestamps
        sa.Column('last_updated_at', sa.DateTime(timezone=True),
                 server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                 server_default=sa.text('now()'), nullable=False),

        # Foreign key
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),

        # Unique constraint: one record per user per month
        sa.UniqueConstraint('user_id', 'month_period', name='uq_user_month_usage')
    )

    # ============================================================
    # 2. Create indexes for efficient queries
    # ============================================================
    print("2. Creating indexes...")

    op.create_index('idx_usage_user_month', 'user_monthly_usage',
                   ['user_id', 'month_period'])
    op.create_index('idx_usage_period', 'user_monthly_usage',
                   ['month_period'])
    op.create_index('idx_usage_updated', 'user_monthly_usage',
                   ['last_updated_at'])

    print("✓ User monthly usage tracking created")
    print("  - Tracks pages, volume, documents, translations, API calls")
    print("  - Automatic monthly period management")
    print("  - Indexed for fast queries")


def downgrade():
    """Remove user monthly usage tracking"""
    print("\n=== Removing User Monthly Usage Tracking ===\n")

    op.drop_index('idx_usage_updated', table_name='user_monthly_usage')
    op.drop_index('idx_usage_period', table_name='user_monthly_usage')
    op.drop_index('idx_usage_user_month', table_name='user_monthly_usage')
    op.drop_table('user_monthly_usage')

    print("✓ User monthly usage tracking removed")
