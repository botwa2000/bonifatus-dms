"""Add preferred_doc_languages to users table

Revision ID: 008_preferred_doc_langs
Revises: 007_fix_invoices
Create Date: 2025-10-31 00:00:00.000000

Changes:
- Add preferred_doc_languages JSONB column to users table
- Initialize with user's current language preference as default
- Supports multi-language document processing preferences
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

revision = '008_preferred_doc_langs'
down_revision = '006_multilingual_admin'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add preferred_doc_languages column"""
    print("\n=== Adding Preferred Document Languages Column ===\n")
    conn = op.get_bind()

    # 1. Check if column already exists
    print("1. Checking if preferred_doc_languages column exists...")
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='users' AND column_name='preferred_doc_languages'
    """))

    if result.fetchone():
        print("   ⚠ preferred_doc_languages column already exists (skipping)")
    else:
        # 2. Add preferred_doc_languages column
        print("2. Adding preferred_doc_languages column...")
        op.add_column('users',
            sa.Column('preferred_doc_languages', JSONB, nullable=True)
        )
        print("   ✓ Column added")

        # 3. Initialize with user's current language from user_settings
        print("\n3. Initializing preferred_doc_languages...")
        result = conn.execute(text("""
            UPDATE users u
            SET preferred_doc_languages = COALESCE(
                (SELECT jsonb_build_array(setting_value)
                 FROM user_settings
                 WHERE user_id = u.id AND setting_key = 'language'
                 LIMIT 1),
                '["en"]'::jsonb
            )
            WHERE preferred_doc_languages IS NULL
        """))
        print(f"   ✓ Initialized {result.rowcount} users")

        # 4. Set NOT NULL constraint after initialization
        print("\n4. Setting NOT NULL constraint...")
        op.alter_column('users', 'preferred_doc_languages', nullable=False)
        print("   ✓ Column set to NOT NULL")

    # 5. Summary
    print("\n📊 Migration Status:")
    result = conn.execute(text("""
        SELECT
            COUNT(*) as total_users,
            COUNT(DISTINCT preferred_doc_languages) as unique_preferences
        FROM users
        WHERE preferred_doc_languages IS NOT NULL
    """))
    stats = result.fetchone()
    if stats:
        print(f"   Total users: {stats[0]}")
        print(f"   Unique language combinations: {stats[1]}")

    # Show sample data
    result = conn.execute(text("""
        SELECT u.email, us.setting_value as ui_lang, u.preferred_doc_languages
        FROM users u
        LEFT JOIN user_settings us ON u.id = us.user_id AND us.setting_key = 'language'
        LIMIT 5
    """))
    print("\n   Sample user preferences:")
    for row in result:
        ui_lang = row[1] if row[1] else 'not set'
        print(f"   - {row[0]}: UI={ui_lang}, Docs={row[2]}")

    print("\n✅ Migration 008 complete!")
    print("   - Users can now have different document processing languages")
    print("   - Default: User's current UI language")


def downgrade() -> None:
    """Remove preferred_doc_languages column"""
    print("\n=== Removing Preferred Document Languages Column ===\n")

    # Check if column exists before dropping
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='users' AND column_name='preferred_doc_languages'
    """))

    if result.fetchone():
        op.drop_column('users', 'preferred_doc_languages')
        print("   ✓ preferred_doc_languages column removed")
    else:
        print("   ⚠ preferred_doc_languages column does not exist (skipping)")

    print("\n✅ Migration 008 rollback complete")
