"""add currency to subscriptions

Revision ID: 20251118_220722
Revises: 20251118_162718
Create Date: 2025-11-18 22:07:22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251118_220722'
down_revision = '20251118_162718'
branch_labels = None
depends_on = None


def upgrade():
    # Add currency and amount fields to subscriptions table
    op.add_column('subscriptions', sa.Column('currency', sa.String(3), nullable=True))
    op.add_column('subscriptions', sa.Column('amount_cents', sa.Integer, nullable=True))

    # Backfill existing subscriptions with tier currency and amount
    op.execute("""
        UPDATE subscriptions s
        SET
            currency = (SELECT currency FROM tier_plans WHERE id = s.tier_id),
            amount_cents = CASE
                WHEN s.billing_cycle = 'monthly' THEN (SELECT price_monthly_cents FROM tier_plans WHERE id = s.tier_id)
                WHEN s.billing_cycle = 'yearly' THEN (SELECT price_yearly_cents FROM tier_plans WHERE id = s.tier_id)
            END
        WHERE s.currency IS NULL
    """)


def downgrade():
    op.drop_column('subscriptions', 'amount_cents')
    op.drop_column('subscriptions', 'currency')
