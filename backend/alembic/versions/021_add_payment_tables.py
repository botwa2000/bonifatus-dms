"""add payment integration tables and user billing fields

Revision ID: 021_payment_tables
Revises: 020_add_email_preferences
Create Date: 2025-11-15 00:00:00.000000

Adds:
1. payments table - Transaction history for all payments
2. subscriptions table - Active subscription tracking
3. discount_codes table - Promotional discount system
4. user_discount_redemptions table - Discount usage tracking
5. referrals table - Referral reward system
6. invoices table - Billing documentation and PDF storage
7. User billing fields - Stripe customer ID, subscription status, billing details
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = '021_payment_tables'
down_revision = '020_add_email_preferences'
branch_labels = None
depends_on = None


def upgrade():
    """Add payment integration tables and user billing fields"""
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    print("\n=== Adding Payment Integration Tables ===\n")

    # ============================================================
    # 1. Create currencies table
    # ============================================================
    print("1. Creating currencies table...")

    op.create_table(
        'currencies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(3), nullable=False, unique=True),  # ISO 4217 code
        sa.Column('symbol', sa.String(10), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('decimal_places', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('idx_currency_code', 'currencies', ['code'])
    op.create_index('idx_currency_active', 'currencies', ['is_active'])
    op.create_index('idx_currency_default', 'currencies', ['is_default'])

    # Populate default currencies
    default_currencies = [
        {'code': 'USD', 'symbol': '$', 'name': 'US Dollar', 'decimal_places': 2, 'is_default': True, 'sort_order': 1},
        {'code': 'EUR', 'symbol': '€', 'name': 'Euro', 'decimal_places': 2, 'is_default': False, 'sort_order': 2},
        {'code': 'GBP', 'symbol': '£', 'name': 'British Pound', 'decimal_places': 2, 'is_default': False, 'sort_order': 3},
        {'code': 'CHF', 'symbol': 'CHF', 'name': 'Swiss Franc', 'decimal_places': 2, 'is_default': False, 'sort_order': 4},
        {'code': 'CAD', 'symbol': 'C$', 'name': 'Canadian Dollar', 'decimal_places': 2, 'is_default': False, 'sort_order': 5},
        {'code': 'AUD', 'symbol': 'A$', 'name': 'Australian Dollar', 'decimal_places': 2, 'is_default': False, 'sort_order': 6},
    ]

    for currency in default_currencies:
        conn.execute(text("""
            INSERT INTO currencies (code, symbol, name, decimal_places, is_active, is_default, sort_order, created_at, updated_at)
            VALUES (:code, :symbol, :name, :decimal_places, true, :is_default, :sort_order, :now, :now)
        """), {**currency, 'now': now})

    print(f"   ✓ Created currencies table with {len(default_currencies)} default currencies")

    # ============================================================
    # 2. Add billing fields to users table
    # ============================================================
    print("2. Adding billing fields to users table...")

    op.add_column('users', sa.Column('stripe_customer_id', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('stripe_subscription_id', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('subscription_status', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('billing_cycle', sa.String(10), nullable=True))  # 'monthly' or 'yearly'
    op.add_column('users', sa.Column('subscription_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('subscription_ends_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('billing_email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('billing_name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('billing_address', JSONB, nullable=True))  # {line1, line2, city, state, postal_code, country}
    op.add_column('users', sa.Column('vat_id', sa.String(50), nullable=True))  # EU VAT ID
    op.add_column('users', sa.Column('tax_exempt', sa.Boolean(), nullable=False, server_default='false'))

    # Create indexes for billing fields
    op.create_index('idx_user_stripe_customer', 'users', ['stripe_customer_id'])
    op.create_index('idx_user_subscription_status', 'users', ['subscription_status'])

    print("   ✓ Added billing fields to users table")

    # ============================================================
    # 3. Create payments table
    # ============================================================
    print("3. Creating payments table...")

    op.create_table(
        'payments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(100), nullable=False, unique=True),
        sa.Column('stripe_invoice_id', sa.String(100), nullable=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('amount_refunded_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(20), nullable=False),  # succeeded, failed, pending, refunded, partially_refunded
        sa.Column('payment_method', sa.String(50), nullable=True),  # card, paypal, sepa_debit, etc
        sa.Column('card_brand', sa.String(20), nullable=True),  # visa, mastercard, amex
        sa.Column('card_last4', sa.String(4), nullable=True),
        sa.Column('card_exp_month', sa.Integer(), nullable=True),
        sa.Column('card_exp_year', sa.Integer(), nullable=True),
        sa.Column('failure_code', sa.String(50), nullable=True),
        sa.Column('failure_message', sa.Text(), nullable=True),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('payment_metadata', JSONB, nullable=True),  # Additional payment metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('idx_payment_user', 'payments', ['user_id'])
    op.create_index('idx_payment_stripe_intent', 'payments', ['stripe_payment_intent_id'])
    op.create_index('idx_payment_status', 'payments', ['status'])
    op.create_index('idx_payment_created', 'payments', ['created_at'])

    print("   ✓ Created payments table")

    # ============================================================
    # 4. Create subscriptions table
    # ============================================================
    print("4. Creating subscriptions table...")

    op.create_table(
        'subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tier_id', sa.Integer(), sa.ForeignKey('tier_plans.id'), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(100), nullable=False, unique=True),
        sa.Column('stripe_price_id', sa.String(100), nullable=False),
        sa.Column('billing_cycle', sa.String(10), nullable=False),  # 'monthly' or 'yearly'
        sa.Column('status', sa.String(20), nullable=False),  # active, past_due, canceled, unpaid, trialing, incomplete
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('idx_subscription_user', 'subscriptions', ['user_id'])
    op.create_index('idx_subscription_stripe', 'subscriptions', ['stripe_subscription_id'])
    op.create_index('idx_subscription_status', 'subscriptions', ['status'])
    op.create_index('idx_subscription_tier', 'subscriptions', ['tier_id'])
    op.create_index('idx_subscription_period_end', 'subscriptions', ['current_period_end'])

    print("   ✓ Created subscriptions table")

    # ============================================================
    # 5. Create discount_codes table
    # ============================================================
    print("5. Creating discount_codes table...")

    op.create_table(
        'discount_codes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('stripe_coupon_id', sa.String(100), nullable=True),
        sa.Column('stripe_promotion_code_id', sa.String(100), nullable=True),
        sa.Column('discount_type', sa.String(20), nullable=False),  # percentage, fixed_amount, free_months
        sa.Column('discount_value', sa.Integer(), nullable=False),  # For %, stored as whole number (25 = 25%), for fixed amount in cents
        sa.Column('currency', sa.String(3), nullable=True),  # Required for fixed_amount type
        sa.Column('duration', sa.String(20), nullable=False),  # once, repeating, forever
        sa.Column('duration_in_months', sa.Integer(), nullable=True),  # For repeating type
        sa.Column('max_redemptions', sa.Integer(), nullable=True),  # NULL = unlimited
        sa.Column('times_redeemed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applicable_tiers', JSONB, nullable=True),  # Array of tier IDs, NULL = all tiers
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('discount_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('idx_discount_code', 'discount_codes', ['code'])
    op.create_index('idx_discount_active', 'discount_codes', ['is_active'])
    op.create_index('idx_discount_valid', 'discount_codes', ['valid_from', 'valid_until'])

    print("   ✓ Created discount_codes table")

    # ============================================================
    # 6. Create user_discount_redemptions table
    # ============================================================
    print("6. Creating user_discount_redemptions table...")

    op.create_table(
        'user_discount_redemptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('discount_code_id', UUID(as_uuid=True), sa.ForeignKey('discount_codes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', UUID(as_uuid=True), sa.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('redeemed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('discount_amount_cents', sa.Integer(), nullable=True),  # Actual discount applied
        sa.Column('redemption_metadata', JSONB, nullable=True),
    )

    op.create_index('idx_redemption_user', 'user_discount_redemptions', ['user_id'])
    op.create_index('idx_redemption_discount', 'user_discount_redemptions', ['discount_code_id'])
    op.create_index('idx_redemption_subscription', 'user_discount_redemptions', ['subscription_id'])
    # Prevent duplicate redemptions
    op.create_index('idx_redemption_unique', 'user_discount_redemptions', ['user_id', 'discount_code_id'], unique=True)

    print("   ✓ Created user_discount_redemptions table")

    # ============================================================
    # 7. Create referrals table
    # ============================================================
    print("7. Creating referrals table...")

    op.create_table(
        'referrals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('referrer_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('referred_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('referral_code', sa.String(50), nullable=False, unique=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, completed, expired
        sa.Column('reward_type', sa.String(20), nullable=True),  # discount_code, free_months, credit
        sa.Column('reward_value', sa.Integer(), nullable=True),
        sa.Column('referrer_reward_granted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('referred_reward_granted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('referrer_discount_code_id', UUID(as_uuid=True), sa.ForeignKey('discount_codes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('referred_discount_code_id', UUID(as_uuid=True), sa.ForeignKey('discount_codes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('referral_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('idx_referral_referrer', 'referrals', ['referrer_user_id'])
    op.create_index('idx_referral_referred', 'referrals', ['referred_user_id'])
    op.create_index('idx_referral_code', 'referrals', ['referral_code'])
    op.create_index('idx_referral_status', 'referrals', ['status'])

    print("   ✓ Created referrals table")

    # ============================================================
    # 8. Create invoices table
    # ============================================================
    print("8. Creating invoices table...")

    op.create_table(
        'invoices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', UUID(as_uuid=True), sa.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('payment_id', UUID(as_uuid=True), sa.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(100), nullable=False, unique=True),
        sa.Column('invoice_number', sa.String(50), nullable=False, unique=True),
        sa.Column('status', sa.String(20), nullable=False),  # draft, open, paid, void, uncollectible
        sa.Column('amount_due_cents', sa.Integer(), nullable=False),
        sa.Column('amount_paid_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('amount_remaining_cents', sa.Integer(), nullable=False),
        sa.Column('subtotal_cents', sa.Integer(), nullable=False),
        sa.Column('tax_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('discount_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('billing_reason', sa.String(50), nullable=True),  # subscription_create, subscription_cycle, manual, etc
        sa.Column('tax_rate', sa.Float(), nullable=True),  # VAT rate applied
        sa.Column('tax_country', sa.String(2), nullable=True),  # ISO country code
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pdf_url', sa.String(500), nullable=True),  # Stripe hosted invoice PDF
        sa.Column('hosted_invoice_url', sa.String(500), nullable=True),  # Stripe hosted payment page
        sa.Column('line_items', JSONB, nullable=True),  # Array of invoice line items
        sa.Column('invoice_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_index('idx_invoice_user', 'invoices', ['user_id'])
    op.create_index('idx_invoice_subscription', 'invoices', ['subscription_id'])
    op.create_index('idx_invoice_payment', 'invoices', ['payment_id'])
    op.create_index('idx_invoice_stripe', 'invoices', ['stripe_invoice_id'])
    op.create_index('idx_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('idx_invoice_status', 'invoices', ['status'])
    op.create_index('idx_invoice_created', 'invoices', ['created_at'])
    op.create_index('idx_invoice_due', 'invoices', ['due_date'])

    print("   ✓ Created invoices table")

    print("\n=== Payment Integration Tables Migration Complete ===\n")


def downgrade():
    """Revert payment integration changes"""
    print("\n=== Reverting Payment Integration Tables ===\n")

    # Drop tables in reverse order (respecting foreign key constraints)
    print("1. Dropping invoices table...")
    op.drop_index('idx_invoice_due', table_name='invoices')
    op.drop_index('idx_invoice_created', table_name='invoices')
    op.drop_index('idx_invoice_status', table_name='invoices')
    op.drop_index('idx_invoice_number', table_name='invoices')
    op.drop_index('idx_invoice_stripe', table_name='invoices')
    op.drop_index('idx_invoice_payment', table_name='invoices')
    op.drop_index('idx_invoice_subscription', table_name='invoices')
    op.drop_index('idx_invoice_user', table_name='invoices')
    op.drop_table('invoices')

    print("2. Dropping referrals table...")
    op.drop_index('idx_referral_status', table_name='referrals')
    op.drop_index('idx_referral_code', table_name='referrals')
    op.drop_index('idx_referral_referred', table_name='referrals')
    op.drop_index('idx_referral_referrer', table_name='referrals')
    op.drop_table('referrals')

    print("3. Dropping user_discount_redemptions table...")
    op.drop_index('idx_redemption_unique', table_name='user_discount_redemptions')
    op.drop_index('idx_redemption_subscription', table_name='user_discount_redemptions')
    op.drop_index('idx_redemption_discount', table_name='user_discount_redemptions')
    op.drop_index('idx_redemption_user', table_name='user_discount_redemptions')
    op.drop_table('user_discount_redemptions')

    print("4. Dropping discount_codes table...")
    op.drop_index('idx_discount_valid', table_name='discount_codes')
    op.drop_index('idx_discount_active', table_name='discount_codes')
    op.drop_index('idx_discount_code', table_name='discount_codes')
    op.drop_table('discount_codes')

    print("5. Dropping subscriptions table...")
    op.drop_index('idx_subscription_period_end', table_name='subscriptions')
    op.drop_index('idx_subscription_tier', table_name='subscriptions')
    op.drop_index('idx_subscription_status', table_name='subscriptions')
    op.drop_index('idx_subscription_stripe', table_name='subscriptions')
    op.drop_index('idx_subscription_user', table_name='subscriptions')
    op.drop_table('subscriptions')

    print("6. Dropping payments table...")
    op.drop_index('idx_payment_created', table_name='payments')
    op.drop_index('idx_payment_status', table_name='payments')
    op.drop_index('idx_payment_stripe_intent', table_name='payments')
    op.drop_index('idx_payment_user', table_name='payments')
    op.drop_table('payments')

    print("7. Removing billing fields from users table...")
    op.drop_index('idx_user_subscription_status', table_name='users')
    op.drop_index('idx_user_stripe_customer', table_name='users')

    op.drop_column('users', 'tax_exempt')
    op.drop_column('users', 'vat_id')
    op.drop_column('users', 'billing_address')
    op.drop_column('users', 'billing_name')
    op.drop_column('users', 'billing_email')
    op.drop_column('users', 'cancel_at_period_end')
    op.drop_column('users', 'trial_ends_at')
    op.drop_column('users', 'subscription_ends_at')
    op.drop_column('users', 'subscription_started_at')
    op.drop_column('users', 'billing_cycle')
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'stripe_subscription_id')
    op.drop_column('users', 'stripe_customer_id')

    print("8. Dropping currencies table...")
    op.drop_index('idx_currency_default', table_name='currencies')
    op.drop_index('idx_currency_active', table_name='currencies')
    op.drop_index('idx_currency_code', table_name='currencies')
    op.drop_table('currencies')

    print("\n=== Payment Integration Tables Reverted ===\n")
