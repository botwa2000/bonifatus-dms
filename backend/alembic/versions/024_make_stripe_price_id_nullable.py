"""make stripe_price_id nullable

Revision ID: 024_nullable_price_id
Revises: 023_add_cookie_consent
Create Date: 2025-11-21 11:00:00.000000

Stripe doesn't always populate items data immediately, so stripe_price_id
can be None when the subscription webhook fires.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '024_nullable_price_id'
down_revision = '023_add_cookie_consent'
branch_labels = None
depends_on = None


def upgrade():
    """Make stripe_price_id nullable"""
    print("\n=== Making stripe_price_id nullable ===\n")
    
    op.alter_column('subscriptions', 'stripe_price_id',
                    existing_type=sa.String(100),
                    nullable=True)
    
    print("   ✓ stripe_price_id is now nullable")
    print("\n=== Migration Complete ===\n")


def downgrade():
    """Revert stripe_price_id to NOT NULL"""
    print("\n=== Reverting stripe_price_id to NOT NULL ===\n")
    
    # Set any NULL values to empty string before making NOT NULL
    op.execute("UPDATE subscriptions SET stripe_price_id = '' WHERE stripe_price_id IS NULL")
    
    op.alter_column('subscriptions', 'stripe_price_id',
                    existing_type=sa.String(100),
                    nullable=False)
    
    print("   ✓ stripe_price_id is now NOT NULL")
    print("\n=== Revert Complete ===\n")
