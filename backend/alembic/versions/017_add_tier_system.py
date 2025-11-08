"""add tier system with database-driven configuration

Revision ID: 017_tier_system
Revises: 016_add_unique_constraints
Create Date: 2025-11-08 15:00:00.000000

Adds:
1. tier_plans table for configurable tier features and pricing
2. Converts users.tier from String to Integer foreign key
3. Converts user_storage_quotas.tier to Integer foreign key
4. Populates default tier plans (Free, Starter, Pro, Admin)

Tier IDs:
- 0 = Free (default)
- 1 = Starter
- 2 = Pro
- 100 = Admin
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = '017_tier_system'
down_revision = '016_add_unique_constraints'
branch_labels = None
depends_on = None


def upgrade():
    """Add tier system with configurable plans"""
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    print("\n=== Adding Tier System ===\n")

    # ============================================================
    # 1. Create tier_plans table
    # ============================================================
    print("1. Creating tier_plans table...")

    op.create_table(
        'tier_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Pricing (in cents)
        sa.Column('price_monthly_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('price_yearly_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),

        # Storage limits
        sa.Column('storage_quota_bytes', sa.BigInteger(), nullable=False),
        sa.Column('max_file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('max_documents', sa.Integer(), nullable=True),

        # Feature flags
        sa.Column('bulk_operations_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('api_access_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('priority_support', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('custom_categories_limit', sa.Integer(), nullable=True),

        # Display
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    op.create_index('idx_tier_active', 'tier_plans', ['is_active', 'sort_order'])
    op.create_index('idx_tier_public', 'tier_plans', ['is_public'])

    # ============================================================
    # 2. Populate default tier plans
    # ============================================================
    print("2. Populating default tier plans...")

    tier_plans = [
        {
            'id': 0,
            'name': 'free',
            'display_name': 'Free',
            'description': 'Perfect for getting started with document management',
            'price_monthly_cents': 0,
            'price_yearly_cents': 0,
            'currency': 'USD',
            'storage_quota_bytes': 1 * 1024 * 1024 * 1024,  # 1 GB
            'max_file_size_bytes': 10 * 1024 * 1024,  # 10 MB
            'max_documents': 100,
            'bulk_operations_enabled': False,
            'api_access_enabled': False,
            'priority_support': False,
            'custom_categories_limit': 5,
            'sort_order': 0,
            'is_active': True,
            'is_public': True
        },
        {
            'id': 1,
            'name': 'starter',
            'display_name': 'Starter',
            'description': 'For individuals and small teams',
            'price_monthly_cents': 999,  # $9.99/month
            'price_yearly_cents': 9990,  # $99.90/year (2 months free)
            'currency': 'USD',
            'storage_quota_bytes': 10 * 1024 * 1024 * 1024,  # 10 GB
            'max_file_size_bytes': 50 * 1024 * 1024,  # 50 MB
            'max_documents': 1000,
            'bulk_operations_enabled': True,
            'api_access_enabled': False,
            'priority_support': False,
            'custom_categories_limit': 25,
            'sort_order': 1,
            'is_active': True,
            'is_public': True
        },
        {
            'id': 2,
            'name': 'pro',
            'display_name': 'Professional',
            'description': 'For power users and growing businesses',
            'price_monthly_cents': 2999,  # $29.99/month
            'price_yearly_cents': 29990,  # $299.90/year (2 months free)
            'currency': 'USD',
            'storage_quota_bytes': 100 * 1024 * 1024 * 1024,  # 100 GB
            'max_file_size_bytes': 200 * 1024 * 1024,  # 200 MB
            'max_documents': None,  # Unlimited
            'bulk_operations_enabled': True,
            'api_access_enabled': True,
            'priority_support': True,
            'custom_categories_limit': None,  # Unlimited
            'sort_order': 2,
            'is_active': True,
            'is_public': True
        },
        {
            'id': 100,
            'name': 'admin',
            'display_name': 'Administrator',
            'description': 'Full system access for administrators',
            'price_monthly_cents': 0,
            'price_yearly_cents': 0,
            'currency': 'USD',
            'storage_quota_bytes': 1000 * 1024 * 1024 * 1024,  # 1 TB
            'max_file_size_bytes': 500 * 1024 * 1024,  # 500 MB
            'max_documents': None,  # Unlimited
            'bulk_operations_enabled': True,
            'api_access_enabled': True,
            'priority_support': True,
            'custom_categories_limit': None,  # Unlimited
            'sort_order': 999,
            'is_active': True,
            'is_public': False  # Not shown on pricing page
        }
    ]

    for plan in tier_plans:
        conn.execute(text("""
            INSERT INTO tier_plans (
                id, name, display_name, description,
                price_monthly_cents, price_yearly_cents, currency,
                storage_quota_bytes, max_file_size_bytes, max_documents,
                bulk_operations_enabled, api_access_enabled, priority_support,
                custom_categories_limit, sort_order, is_active, is_public,
                created_at, updated_at
            ) VALUES (
                :id, :name, :display_name, :description,
                :price_monthly_cents, :price_yearly_cents, :currency,
                :storage_quota_bytes, :max_file_size_bytes, :max_documents,
                :bulk_operations_enabled, :api_access_enabled, :priority_support,
                :custom_categories_limit, :sort_order, :is_active, :is_public,
                :now, :now
            )
        """), {**plan, 'now': now})

    print(f"   ✓ Inserted {len(tier_plans)} tier plans")

    # ============================================================
    # 3. Migrate users table
    # ============================================================
    print("3. Migrating users table...")

    # Add new tier_id column
    op.add_column('users', sa.Column('tier_id', sa.Integer(), nullable=True))

    # Migrate existing data: map string tiers to integer IDs
    conn.execute(text("""
        UPDATE users
        SET tier_id = CASE
            WHEN tier = 'admin' THEN 100
            WHEN tier = 'pro' THEN 2
            WHEN tier = 'starter' THEN 1
            ELSE 0
        END
    """))

    # Make tier_id NOT NULL now that it's populated
    op.alter_column('users', 'tier_id', nullable=False, server_default='0')

    # Add foreign key constraint
    op.create_foreign_key('fk_users_tier_id', 'users', 'tier_plans', ['tier_id'], ['id'])

    # Drop old tier column and its index
    op.drop_index('idx_user_tier', table_name='users')
    op.drop_column('users', 'tier')

    # Create new index on tier_id
    op.create_index('idx_user_tier_id', 'users', ['tier_id'])

    print("   ✓ Users table migrated")

    # ============================================================
    # 4. Migrate user_storage_quotas table
    # ============================================================
    print("4. Migrating user_storage_quotas table...")

    # Add new tier_id column
    op.add_column('user_storage_quotas', sa.Column('tier_id', sa.Integer(), nullable=True))

    # Migrate existing data
    conn.execute(text("""
        UPDATE user_storage_quotas
        SET tier_id = CASE
            WHEN tier = 'admin' THEN 100
            WHEN tier = 'pro' THEN 2
            WHEN tier = 'starter' THEN 1
            ELSE 0
        END
    """))

    # Make tier_id NOT NULL now that it's populated
    op.alter_column('user_storage_quotas', 'tier_id', nullable=False)

    # Add foreign key constraint
    op.create_foreign_key('fk_user_storage_quotas_tier_id', 'user_storage_quotas', 'tier_plans', ['tier_id'], ['id'])

    # Drop old tier column and its index
    op.drop_index('idx_user_quota_tier', table_name='user_storage_quotas')
    op.drop_column('user_storage_quotas', 'tier')

    # Create new index on tier_id
    op.create_index('idx_user_quota_tier', 'user_storage_quotas', ['tier_id'])

    print("   ✓ User storage quotas table migrated")

    print("\n=== Tier System Migration Complete ===\n")


def downgrade():
    """Revert tier system changes"""
    conn = op.get_bind()

    print("\n=== Reverting Tier System ===\n")

    # 1. Restore users table
    op.add_column('users', sa.Column('tier', sa.String(20), nullable=True))

    conn.execute(text("""
        UPDATE users
        SET tier = CASE
            WHEN tier_id = 100 THEN 'admin'
            WHEN tier_id = 2 THEN 'pro'
            WHEN tier_id = 1 THEN 'starter'
            ELSE 'free'
        END
    """))

    op.alter_column('users', 'tier', nullable=False, server_default='free')
    op.create_index('idx_user_tier', 'users', ['tier'])

    op.drop_index('idx_user_tier_id', table_name='users')
    op.drop_constraint('fk_users_tier_id', 'users', type_='foreignkey')
    op.drop_column('users', 'tier_id')

    # 2. Restore user_storage_quotas table
    op.add_column('user_storage_quotas', sa.Column('tier', sa.String(20), nullable=True))

    conn.execute(text("""
        UPDATE user_storage_quotas
        SET tier = CASE
            WHEN tier_id = 100 THEN 'admin'
            WHEN tier_id = 2 THEN 'pro'
            WHEN tier_id = 1 THEN 'starter'
            ELSE 'free'
        END
    """))

    op.alter_column('user_storage_quotas', 'tier', nullable=False)
    op.create_index('idx_user_quota_tier', 'user_storage_quotas', ['tier'])

    op.drop_index('idx_user_quota_tier', table_name='user_storage_quotas')
    op.drop_constraint('fk_user_storage_quotas_tier_id', 'user_storage_quotas', type_='foreignkey')
    op.drop_column('user_storage_quotas', 'tier_id')

    # 3. Drop tier_plans table
    op.drop_index('idx_tier_public', table_name='tier_plans')
    op.drop_index('idx_tier_active', table_name='tier_plans')
    op.drop_table('tier_plans')

    print("\n=== Tier System Reverted ===\n")
