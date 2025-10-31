"""Add multi-lingual categories and admin user support

Revision ID: 006_multilingual_admin
Revises: 005_add_metadata
Create Date: 2025-10-30 21:00:00.000000

Changes:
- Add is_multi_lingual column to categories table (default TRUE)
- Add is_admin and admin_role columns to users table
- Set default admin user (bonifatus.app@gmail.com) when exists
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '006_multilingual_admin'
down_revision = '005_add_metadata'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add multi-lingual and admin columns"""
    print("\n=== Adding Multi-Lingual & Admin Support ===\n")
    conn = op.get_bind()

    # 1. Add is_multi_lingual to categories table
    print("1. Adding is_multi_lingual column to categories...")
    try:
        op.add_column('categories',
            sa.Column('is_multi_lingual', sa.Boolean(), nullable=False, server_default='true')
        )
        print("   ✓ is_multi_lingual column added (default: TRUE)")
    except Exception as e:
        if 'already exists' in str(e):
            print("   ⚠ is_multi_lingual column already exists (skipping)")
        else:
            raise

    # 2. Add admin columns to users table
    print("\n2. Adding admin columns to users...")

    # Check if is_admin column exists
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='users' AND column_name='is_admin'
    """))
    if not result.fetchone():
        op.add_column('users',
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false')
        )
        print("   ✓ is_admin column added (default: FALSE)")
    else:
        print("   ⚠ is_admin column already exists (skipping)")

    # Check if admin_role column exists
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='users' AND column_name='admin_role'
    """))
    if not result.fetchone():
        op.add_column('users',
            sa.Column('admin_role', sa.String(50), nullable=True)
        )
        print("   ✓ admin_role column added (nullable)")
    else:
        print("   ⚠ admin_role column already exists (skipping)")

    # 3. Set bonifatus.app@gmail.com as admin if user exists
    print("\n3. Setting admin user (bonifatus.app@gmail.com)...")

    result = conn.execute(
        text("SELECT id FROM users WHERE email = 'bonifatus.app@gmail.com'")
    )
    admin_user = result.fetchone()

    if admin_user:
        conn.execute(
            text("""
                UPDATE users
                SET is_admin = true, admin_role = 'super_admin'
                WHERE email = 'bonifatus.app@gmail.com'
            """)
        )
        print("   ✓ Admin user set (bonifatus.app@gmail.com)")
    else:
        print("   ⚠ Admin user not found (will be set on first login)")

    print("\n✅ Migration 006 complete!")
    print("   - Categories can now be multi-lingual or language-specific")
    print("   - Admin user support enabled")


def downgrade() -> None:
    """Remove multi-lingual and admin columns"""
    print("\n=== Removing Multi-Lingual & Admin Support ===\n")

    # Remove admin columns from users
    print("1. Removing admin columns from users...")
    op.drop_column('users', 'admin_role')
    op.drop_column('users', 'is_admin')
    print("   ✓ Admin columns removed")

    # Remove is_multi_lingual from categories
    print("\n2. Removing is_multi_lingual from categories...")
    op.drop_column('categories', 'is_multi_lingual')
    print("   ✓ is_multi_lingual column removed")

    print("\n✅ Migration 006 rollback complete")
