#!/usr/bin/env python3
"""
Database Query Test Script for Bonifatus DMS
Run this to inspect categories, keywords, and classification data
"""

import sys
sys.path.insert(0, '/app')

from app.database.connection import db_manager
from app.database.models import Category, CategoryTranslation, CategoryKeyword, StopWord, User
from sqlalchemy import text


def print_separator(title=""):
    """Print a separator line with optional title"""
    if title:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print('=' * 70)
    else:
        print('=' * 70)


def check_categories_and_keywords():
    """Query and display all categories with their keywords"""
    db = db_manager.session_local()
    try:
        print_separator("ACTIVE CATEGORIES AND KEYWORDS")

        categories = db.query(Category).filter(
            Category.is_active == True
        ).order_by(Category.sort_order).all()

        print(f"\nFound {len(categories)} active categories\n")

        for cat in categories:
            # Get German translation
            trans_de = db.query(CategoryTranslation).filter(
                CategoryTranslation.category_id == cat.id,
                CategoryTranslation.language_code == "de"
            ).first()

            # Get English translation
            trans_en = db.query(CategoryTranslation).filter(
                CategoryTranslation.category_id == cat.id,
                CategoryTranslation.language_code == "en"
            ).first()

            # Get German keywords
            keywords_de = db.query(CategoryKeyword).filter(
                CategoryKeyword.category_id == cat.id,
                CategoryKeyword.language_code == "de"
            ).order_by(CategoryKeyword.weight.desc()).all()

            # Get English keywords
            keywords_en = db.query(CategoryKeyword).filter(
                CategoryKeyword.category_id == cat.id,
                CategoryKeyword.language_code == "en"
            ).order_by(CategoryKeyword.weight.desc()).all()

            print(f"\n--- {cat.reference_key} ---")
            print(f"  ID: {cat.id}")
            print(f"  System: {cat.is_system}, User ID: {cat.user_id or 'None'}")
            print(f"  Code: {cat.category_code}, Color: {cat.color_hex}")

            de_name = trans_de.name if trans_de else "N/A"
            en_name = trans_en.name if trans_en else "N/A"
            print(f"  Names: DE='{de_name}', EN='{en_name}'")

            print(f"\n  German Keywords ({len(keywords_de)} total):")
            if keywords_de:
                for kw in keywords_de[:20]:  # Show top 20
                    print(f"    • {kw.keyword:<25} weight: {kw.weight:.1f}")
            else:
                print("    (none)")

            print(f"\n  English Keywords ({len(keywords_en)} total):")
            if keywords_en:
                for kw in keywords_en[:20]:  # Show top 20
                    print(f"    • {kw.keyword:<25} weight: {kw.weight:.1f}")
            else:
                print("    (none)")

    finally:
        db.close()


def check_stop_words():
    """Query and display stop words by language"""
    db = db_manager.session_local()
    try:
        print_separator("STOP WORDS")

        for lang in ['de', 'en', 'ru']:
            stop_words = db.query(StopWord).filter(
                StopWord.language_code == lang,
                StopWord.is_active == True
            ).all()

            print(f"\n{lang.upper()}: {len(stop_words)} stop words")
            if stop_words:
                words_list = [sw.word for sw in stop_words[:30]]
                print(f"  Sample: {', '.join(words_list)}")
                if len(stop_words) > 30:
                    print(f"  ... and {len(stop_words) - 30} more")

    finally:
        db.close()


def search_keyword(keyword, language='de'):
    """Search for a specific keyword across all categories"""
    db = db_manager.session_local()
    try:
        print_separator(f"SEARCH: '{keyword}' (language: {language})")

        results = db.query(CategoryKeyword, Category, CategoryTranslation).join(
            Category, CategoryKeyword.category_id == Category.id
        ).join(
            CategoryTranslation, Category.id == CategoryTranslation.category_id
        ).filter(
            CategoryKeyword.keyword.ilike(f"%{keyword}%"),
            CategoryKeyword.language_code == language,
            CategoryTranslation.language_code == language
        ).all()

        if results:
            print(f"\nFound {len(results)} matches:\n")
            for kw, cat, trans in results:
                print(f"  • '{kw.keyword}' (weight: {kw.weight:.1f}) → {trans.name} ({cat.reference_key})")
        else:
            print(f"\nNo matches found for '{keyword}' in {language} keywords")

    finally:
        db.close()


def check_migration_006():
    """Test migration 006: Multi-lingual and admin columns"""
    db = db_manager.session_local()
    try:
        print_separator("MIGRATION 006: Multi-Lingual & Admin")

        # Check categories.is_multi_lingual column
        result = db.execute(text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name='categories' AND column_name='is_multi_lingual'
        """))
        multi_lingual_col = result.fetchone()

        # Check users.is_admin column
        result = db.execute(text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='is_admin'
        """))
        admin_col = result.fetchone()

        # Check users.admin_role column
        result = db.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='admin_role'
        """))
        admin_role_col = result.fetchone()

        print("\nColumn Status:")
        print(f"  categories.is_multi_lingual: {'✅ EXISTS' if multi_lingual_col else '❌ MISSING'}")
        if multi_lingual_col:
            print(f"    Type: {multi_lingual_col[1]}, Default: {multi_lingual_col[2]}")

        print(f"\n  users.is_admin: {'✅ EXISTS' if admin_col else '❌ MISSING'}")
        if admin_col:
            print(f"    Type: {admin_col[1]}, Default: {admin_col[2]}")

        print(f"\n  users.admin_role: {'✅ EXISTS' if admin_role_col else '❌ MISSING'}")
        if admin_role_col:
            print(f"    Type: {admin_role_col[1]}")

        # Check current migration version
        result = db.execute(text("SELECT version_num FROM alembic_version"))
        version = result.fetchone()
        print(f"\nCurrent Migration: {version[0]}")

        if multi_lingual_col and admin_col and admin_role_col:
            print("\n✅ Migration 006 successfully applied")
        else:
            print("\n⚠ Migration 006 not yet applied or incomplete")

    finally:
        db.close()


def check_admin_users():
    """Display admin users and their roles"""
    db = db_manager.session_local()
    try:
        print_separator("ADMIN USERS")

        # Get all admin users
        result = db.execute(text("""
            SELECT email, is_admin, admin_role, created_at
            FROM users
            WHERE is_admin = true
            ORDER BY created_at
        """))
        admin_users = result.fetchall()

        if admin_users:
            print(f"\nFound {len(admin_users)} admin user(s):\n")
            for user in admin_users:
                print(f"  • {user[0]}")
                print(f"    Role: {user[2] or 'None'}")
                print(f"    Created: {user[3]}")
                print()
        else:
            print("\n⚠ No admin users found")
            print("  Expected: bonifatus.app@gmail.com")
            print("  (Will be set as admin on first login)\n")

        # Check if bonifatus.app@gmail.com exists (admin or not)
        result = db.execute(text("""
            SELECT email, is_admin, admin_role
            FROM users
            WHERE email = 'bonifatus.app@gmail.com'
        """))
        bonidoc_user = result.fetchone()

        if bonidoc_user:
            print("Bonifatus Admin Account:")
            print(f"  Email: {bonidoc_user[0]}")
            print(f"  Is Admin: {bonidoc_user[1]}")
            print(f"  Admin Role: {bonidoc_user[2] or 'Not set'}")
        else:
            print("Bonifatus Admin Account:")
            print("  ⚠ User not found (not yet registered)")

    finally:
        db.close()


def main():
    """Main function to run tests"""
    print("\n" + "=" * 70)
    print("  BONIFATUS DMS - DATABASE INSPECTION TOOL")
    print("=" * 70)

    # Check migration 006 status
    check_migration_006()

    # Check admin users
    check_admin_users()

    # Check categories and keywords
    check_categories_and_keywords()

    # Check stop words
    check_stop_words()

    # Example: Search for specific keywords
    print("\n")
    search_keyword("rechnung", "de")
    search_keyword("invoice", "en")
    search_keyword("volksbank", "de")

    print("\n" + "=" * 70)
    print("  INSPECTION COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
