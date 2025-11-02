"""cleanup duplicate categories per user

Revision ID: 014_cleanup_duplicates
Revises: 013_german_keywords
Create Date: 2025-11-02 10:00:00.000000

"""
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '014_cleanup_duplicates'
down_revision = '013_german_keywords'
branch_labels = None
depends_on = None


def upgrade():
    """
    Clean up duplicate categories for each user
    Keep only one category per (user_id, reference_key) combination

    This fixes the fundamental issue where each category translation was being
    treated as a separate category instead of one category with multiple translations.
    """

    conn = op.get_bind()

    print("\n=== Cleaning Up Duplicate Categories ===\n")

    # Step 1: Identify duplicate categories
    print("Step 1: Identifying duplicate categories...")

    result = conn.execute(text("""
        SELECT user_id, reference_key, COUNT(*) as count
        FROM categories
        WHERE user_id IS NOT NULL
        GROUP BY user_id, reference_key
        HAVING COUNT(*) > 1
        ORDER BY user_id, reference_key
    """))

    duplicates = result.fetchall()

    if not duplicates:
        print("  ✓ No duplicate categories found - database is clean!")
        return

    print(f"  Found {len(duplicates)} sets of duplicates:")
    for row in duplicates:
        print(f"    User {row[0]}: {row[2]} copies of '{row[1]}'")

    # Step 2: For each duplicate, keep the oldest and delete the rest
    print("\nStep 2: Removing duplicate categories...")

    total_deleted = 0

    for user_id, ref_key, count in duplicates:
        # Get all category IDs for this (user_id, reference_key) combination, ordered by created_at
        result = conn.execute(text("""
            SELECT id, created_at
            FROM categories
            WHERE user_id = :user_id AND reference_key = :ref_key
            ORDER BY created_at ASC
        """), {'user_id': str(user_id), 'ref_key': ref_key})

        category_ids = [row[0] for row in result]

        if len(category_ids) <= 1:
            continue

        # Keep the first (oldest) category, delete the rest
        keep_id = str(category_ids[0])
        delete_ids = [str(cid) for cid in category_ids[1:]]

        print(f"  User {user_id}, {ref_key}: Keeping {keep_id}, deleting {len(delete_ids)} duplicates")

        # Move documents from duplicate categories to the one we're keeping
        for delete_id in delete_ids:
            result = conn.execute(text("""
                UPDATE documents
                SET category_id = :keep_id
                WHERE category_id = :delete_id
            """), {'keep_id': keep_id, 'delete_id': delete_id})

            if result.rowcount > 0:
                print(f"    Moved {result.rowcount} documents from {delete_id} to {keep_id}")

        # Delete duplicate categories (cascade will delete translations and keywords)
        for delete_id in delete_ids:
            conn.execute(text("""
                DELETE FROM categories WHERE id = :id
            """), {'id': delete_id})
            total_deleted += 1

    print(f"\n✓ Cleanup complete: Deleted {total_deleted} duplicate categories")

    # Step 3: Verify cleanup
    print("\nStep 3: Verifying cleanup...")

    result = conn.execute(text("""
        SELECT user_id, reference_key, COUNT(*) as count
        FROM categories
        WHERE user_id IS NOT NULL
        GROUP BY user_id, reference_key
        HAVING COUNT(*) > 1
    """))

    remaining_duplicates = result.fetchall()

    if remaining_duplicates:
        print(f"  ⚠️  WARNING: Still found {len(remaining_duplicates)} duplicate sets after cleanup!")
        for row in remaining_duplicates:
            print(f"    User {row[0]}: {row[2]} copies of '{row[1]}'")
    else:
        print("  ✓ No duplicates remaining - cleanup successful!")

    # Step 4: Report final category counts per user
    print("\nStep 4: Final category counts:")

    result = conn.execute(text("""
        SELECT user_id, COUNT(*) as category_count
        FROM categories
        WHERE user_id IS NOT NULL
        GROUP BY user_id
        ORDER BY user_id
    """))

    for row in result:
        print(f"  User {row[0]}: {row[1]} categories")

    print("\n✓ Migration 014 completed: Duplicate categories cleaned up")
    print("  Each user now has exactly one category per reference_key")


def downgrade():
    """
    Cannot meaningfully downgrade this migration
    """
    print("⚠️  Migration 014 cleanup cannot be reversed")
    print("   Duplicate categories have been merged and deleted")
