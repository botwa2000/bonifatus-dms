"""update tier limits to monthly pages and volume

Revision ID: 033_monthly_limits
Revises: 032_add_ml_entity_quality_system
Create Date: 2025-12-04 22:00:00.000000

Changes:
1. Rename max_documents → max_pages_per_month (monthly page limit)
2. Rename storage_quota_bytes → max_monthly_upload_bytes (monthly volume limit)
3. Add email_to_process_enabled (auto-analyze from email)
4. Add folder_to_process_enabled (auto-analyze from folder)
5. Add multi_user_enabled (multi-user access feature)
6. Add max_team_members (team size limit)
7. Add max_translations_per_month (translation limit)
8. Add max_api_calls_per_month (API call limit)
9. Update existing tier data with new monthly limits

New Limits:
- Free: 50 pages/month, 100MB/month, 1 user
- Starter: 500 pages/month, 1GB/month, 3 users
- Pro: Unlimited pages, 10GB/month, 10 users
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '033_monthly_limits'
down_revision = '032_add_ml_entity_quality_system'
branch_labels = None
depends_on = None


def upgrade():
    """Update tier limits to monthly pages and volume"""
    conn = op.get_bind()

    print("\n=== Updating Tier Limits to Monthly System ===\n")

    # ============================================================
    # 1. Rename existing columns to reflect monthly limits
    # ============================================================
    print("1. Renaming columns to monthly limits...")

    # Rename max_documents → max_pages_per_month
    op.alter_column('tier_plans', 'max_documents',
                    new_column_name='max_pages_per_month',
                    existing_type=sa.Integer(),
                    existing_nullable=True)

    # Rename storage_quota_bytes → max_monthly_upload_bytes
    op.alter_column('tier_plans', 'storage_quota_bytes',
                    new_column_name='max_monthly_upload_bytes',
                    existing_type=sa.BigInteger(),
                    existing_nullable=False)

    # ============================================================
    # 2. Add new feature and limit columns
    # ============================================================
    print("2. Adding new feature columns...")

    # Email and folder processing features
    op.add_column('tier_plans',
                  sa.Column('email_to_process_enabled', sa.Boolean(),
                           nullable=False, server_default='false'))
    op.add_column('tier_plans',
                  sa.Column('folder_to_process_enabled', sa.Boolean(),
                           nullable=False, server_default='false'))

    # Multi-user features
    op.add_column('tier_plans',
                  sa.Column('multi_user_enabled', sa.Boolean(),
                           nullable=False, server_default='false'))
    op.add_column('tier_plans',
                  sa.Column('max_team_members', sa.Integer(),
                           nullable=True))  # NULL = unlimited

    # Additional monthly limits
    op.add_column('tier_plans',
                  sa.Column('max_translations_per_month', sa.Integer(),
                           nullable=True))  # NULL = unlimited
    op.add_column('tier_plans',
                  sa.Column('max_api_calls_per_month', sa.Integer(),
                           nullable=True))  # NULL = unlimited

    # ============================================================
    # 3. Update existing tier data with new monthly limits
    # ============================================================
    print("3. Updating tier data with new monthly limits...")

    # Free Tier (ID=0): 50 pages/month, 100MB/month
    conn.execute(text("""
        UPDATE tier_plans SET
            max_pages_per_month = 50,
            max_monthly_upload_bytes = 104857600,  -- 100 MB
            email_to_process_enabled = false,
            folder_to_process_enabled = false,
            multi_user_enabled = false,
            max_team_members = 1,
            max_translations_per_month = 10,
            max_api_calls_per_month = 0
        WHERE id = 0
    """))

    # Starter Tier (ID=1): 500 pages/month, 1GB/month
    conn.execute(text("""
        UPDATE tier_plans SET
            max_pages_per_month = 500,
            max_monthly_upload_bytes = 1073741824,  -- 1 GB
            email_to_process_enabled = true,
            folder_to_process_enabled = false,
            multi_user_enabled = false,
            max_team_members = 3,
            max_translations_per_month = 100,
            max_api_calls_per_month = 1000
        WHERE id = 1
    """))

    # Professional Tier (ID=2): Unlimited pages, 10GB/month
    conn.execute(text("""
        UPDATE tier_plans SET
            max_pages_per_month = NULL,  -- Unlimited
            max_monthly_upload_bytes = 10737418240,  -- 10 GB
            email_to_process_enabled = true,
            folder_to_process_enabled = true,
            multi_user_enabled = true,
            max_team_members = 10,
            max_translations_per_month = NULL,  -- Unlimited
            max_api_calls_per_month = 10000
        WHERE id = 2
    """))

    # Admin Tier (ID=100): Unlimited everything
    conn.execute(text("""
        UPDATE tier_plans SET
            max_pages_per_month = NULL,  -- Unlimited
            max_monthly_upload_bytes = 107374182400,  -- 100 GB
            email_to_process_enabled = true,
            folder_to_process_enabled = true,
            multi_user_enabled = true,
            max_team_members = NULL,  -- Unlimited
            max_translations_per_month = NULL,  -- Unlimited
            max_api_calls_per_month = NULL  -- Unlimited
        WHERE id = 100
    """))

    print("✓ Tier limits updated to monthly system")
    print("  - Free: 50 pages/month, 100MB/month, 1 user")
    print("  - Starter: 500 pages/month, 1GB/month, 3 users, email-to-process")
    print("  - Pro: Unlimited pages, 10GB/month, 10 users, folder-to-process, multi-user")
    print("  - Admin: Unlimited")


def downgrade():
    """Revert tier limits back to old system"""
    conn = op.get_bind()

    print("\n=== Reverting to old tier limit system ===\n")

    # Remove new columns
    op.drop_column('tier_plans', 'max_api_calls_per_month')
    op.drop_column('tier_plans', 'max_translations_per_month')
    op.drop_column('tier_plans', 'max_team_members')
    op.drop_column('tier_plans', 'multi_user_enabled')
    op.drop_column('tier_plans', 'folder_to_process_enabled')
    op.drop_column('tier_plans', 'email_to_process_enabled')

    # Rename columns back
    op.alter_column('tier_plans', 'max_monthly_upload_bytes',
                    new_column_name='storage_quota_bytes',
                    existing_type=sa.BigInteger(),
                    existing_nullable=False)

    op.alter_column('tier_plans', 'max_pages_per_month',
                    new_column_name='max_documents',
                    existing_type=sa.Integer(),
                    existing_nullable=True)

    # Restore old values
    conn.execute(text("""
        UPDATE tier_plans SET
            max_documents = 100,
            storage_quota_bytes = 1073741824  -- 1 GB
        WHERE id = 0
    """))

    conn.execute(text("""
        UPDATE tier_plans SET
            max_documents = 1000,
            storage_quota_bytes = 10737418240  -- 10 GB
        WHERE id = 1
    """))

    conn.execute(text("""
        UPDATE tier_plans SET
            max_documents = NULL,
            storage_quota_bytes = 107374182400  -- 100 GB
        WHERE id = 2
    """))

    print("✓ Reverted to old tier limit system")
