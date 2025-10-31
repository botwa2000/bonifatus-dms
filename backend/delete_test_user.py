#!/usr/bin/env python3
"""
Delete test user and all associated data for clean slate testing
Run this before registering a new user with the per-user category architecture
"""

import sys
from sqlalchemy import text
from app.database.connection import db_manager

def delete_test_user_data():
    """Delete all user data to start fresh"""
    session = db_manager.session_local()
    try:
        # Get user IDs before deletion
        result = session.execute(text("SELECT id, email FROM users"))
        users = result.fetchall()

        if not users:
            print("No users found in database")
            return

        print(f"Found {len(users)} users:")
        for user_id, email in users:
            print(f"  - {email} ({user_id})")

        confirm = input("\nAre you sure you want to DELETE ALL users and their data? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted")
            return

        # Delete in correct order to respect foreign keys
        print("\nDeleting user data...")

        # Documents (references categories)
        result = session.execute(text("DELETE FROM documents WHERE user_id IN (SELECT id FROM users)"))
        print(f"  Deleted {result.rowcount} documents")

        # Category keywords (references categories)
        result = session.execute(text("""
            DELETE FROM category_keywords
            WHERE category_id IN (SELECT id FROM categories WHERE user_id IS NOT NULL)
        """))
        print(f"  Deleted {result.rowcount} category keywords")

        # Category translations (references categories)
        result = session.execute(text("""
            DELETE FROM category_translations
            WHERE category_id IN (SELECT id FROM categories WHERE user_id IS NOT NULL)
        """))
        print(f"  Deleted {result.rowcount} category translations")

        # User categories (both system copies and custom)
        result = session.execute(text("DELETE FROM categories WHERE user_id IS NOT NULL"))
        print(f"  Deleted {result.rowcount} user categories")

        # User settings
        result = session.execute(text("DELETE FROM user_settings WHERE user_id IN (SELECT id FROM users)"))
        print(f"  Deleted {result.rowcount} user settings")

        # User sessions
        result = session.execute(text("DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users)"))
        print(f"  Deleted {result.rowcount} user sessions")

        # Audit logs
        result = session.execute(text("DELETE FROM audit_logs WHERE user_id IN (SELECT id FROM users)"))
        print(f"  Deleted {result.rowcount} audit logs")

        # Finally, delete users
        result = session.execute(text("DELETE FROM users"))
        print(f"  Deleted {result.rowcount} users")

        session.commit()
        print("\n✓ All user data deleted successfully!")
        print("\nYou can now register a new user with the per-user category architecture.")
        print("New users will automatically get personal copies of all 7 template categories.")

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Delete Test User Data")
    print("=" * 60)
    delete_test_user_data()
