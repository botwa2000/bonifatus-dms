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

        for lang in ['de', 'en', 'ru', 'fr']:
            stop_words = db.query(StopWord).filter(
                StopWord.language_code == lang,
                StopWord.is_active == True
            ).all()

            print(f"\n{lang.upper()}: {len(stop_words)} stop words")
            if stop_words:
                words_list = sorted([sw.word for sw in stop_words])

                # For German, show ALL words to check completeness
                if lang == 'de':
                    print(f"  All German stopwords:")
                    for i in range(0, len(words_list), 10):
                        chunk = words_list[i:i+10]
                        print(f"    {', '.join(chunk)}")

                    # Check for missing critical words
                    critical_words = ['sehr', 'ihnen', 'diese', 'dieser', 'diesem', 'für']
                    missing = [w for w in critical_words if w not in words_list]
                    if missing:
                        print(f"\n  ⚠️  Missing critical German stopwords: {', '.join(missing)}")
                    else:
                        print(f"\n  ✅ All critical German stopwords present")
                else:
                    # For other languages, just show sample
                    print(f"  Sample: {', '.join(words_list[:30])}")
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


def check_category_standardization():
    """Verify all template categories are standardized with uniform structure"""
    db = db_manager.session_local()
    try:
        print_separator("CATEGORY STANDARDIZATION CHECK")

        # Check template categories (user_id IS NULL)
        result = db.execute(text("""
            SELECT reference_key, category_code, sort_order, is_system,
                   (SELECT COUNT(*) FROM category_translations ct WHERE ct.category_id = c.id) as translations,
                   (SELECT COUNT(*) FROM category_keywords ck WHERE ck.category_id = c.id) as keywords
            FROM categories c
            WHERE user_id IS NULL
            ORDER BY sort_order
        """))
        template_categories = result.fetchall()

        print(f"\nTemplate Categories: {len(template_categories)}")
        print("\n  Ref Key | Code | Sort | System | Translations | Keywords")
        print("  --------|------|------|--------|--------------|----------")

        all_valid = True
        for cat in template_categories:
            ref_key, code, sort_order, is_system, trans_count, kw_count = cat

            # Check if reference key is 3-letter format
            is_3letter = len(ref_key) == 3 and ref_key.isupper()
            status = "✅" if is_3letter and trans_count >= 4 and kw_count > 0 else "⚠️"

            print(f"  {status} {ref_key:7s} | {code:4s} | {sort_order:4d} | {is_system!s:6s} | {trans_count:12d} | {kw_count:8d}")

            if not is_3letter or trans_count < 4 or kw_count == 0:
                all_valid = False

        # Check for French translations
        result = db.execute(text("""
            SELECT c.reference_key, ct.language_code
            FROM categories c
            LEFT JOIN category_translations ct ON c.id = ct.category_id AND ct.language_code = 'fr'
            WHERE c.user_id IS NULL
            ORDER BY c.sort_order
        """))
        french_check = result.fetchall()

        print("\n  French Translations:")
        missing_french = []
        for ref_key, lang_code in french_check:
            if lang_code:
                print(f"    ✅ {ref_key}: Has French")
            else:
                print(f"    ❌ {ref_key}: Missing French")
                missing_french.append(ref_key)
                all_valid = False

        # Check current migration version
        result = db.execute(text("SELECT version_num FROM alembic_version"))
        version = result.fetchone()
        print(f"\n  Current Migration: {version[0]}")

        if all_valid:
            print("\n✅ All categories standardized correctly")
        else:
            print("\n⚠️ Some categories need standardization")
            if missing_french:
                print(f"  Missing French: {', '.join(missing_french)}")

    finally:
        db.close()


def check_per_user_architecture():
    """Verify per-user category architecture is working correctly"""
    db = db_manager.session_local()
    try:
        print_separator("PER-USER CATEGORY ARCHITECTURE CHECK")

        # Count template vs user categories
        result = db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE user_id IS NULL) as template_count,
                COUNT(*) FILTER (WHERE user_id IS NOT NULL) as user_count,
                COUNT(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) as unique_users
            FROM categories
        """))
        counts = result.fetchone()

        print(f"\n  Template Categories (user_id=NULL): {counts[0]}")
        print(f"  User Categories (user_id≠NULL): {counts[1]}")
        print(f"  Unique Users with Categories: {counts[2]}")

        # Check users
        result = db.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.fetchone()[0]
        print(f"\n  Total Users: {user_count}")

        # Check if users have their own category copies
        if user_count > 0:
            result = db.execute(text("""
                SELECT u.email, COUNT(c.id) as category_count
                FROM users u
                LEFT JOIN categories c ON u.id = c.user_id
                GROUP BY u.email
            """))
            user_categories = result.fetchall()

            print("\n  User Category Counts:")
            for email, cat_count in user_categories:
                expected = counts[0]  # Should match template count
                status = "✅" if cat_count == expected else "⚠️"
                print(f"    {status} {email}: {cat_count} categories (expected: {expected})")

        # Verify no duplicate reference_keys per user
        result = db.execute(text("""
            SELECT user_id, reference_key, COUNT(*) as dup_count
            FROM categories
            WHERE user_id IS NOT NULL
            GROUP BY user_id, reference_key
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()

        if duplicates:
            print("\n  ❌ Found duplicate reference_keys per user:")
            for user_id, ref_key, dup_count in duplicates:
                print(f"    User {user_id}: {ref_key} appears {dup_count} times")
        else:
            print("\n  ✅ No duplicate reference_keys per user")

        print("\n  Architecture Status:")
        if counts[0] == 7:
            print("    ✅ 7 template categories exist")
        else:
            print(f"    ⚠️ Expected 7 template categories, found {counts[0]}")

        if user_count == 0:
            print("    ℹ️ No users registered yet (clean slate)")
        elif counts[1] == user_count * counts[0]:
            print("    ✅ Each user has complete category set")
        else:
            print("    ⚠️ User category counts don't match expected")

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


def check_french_language_config():
    """Check if French is properly configured in system settings"""
    db = db_manager.session_local()
    try:
        print_separator("FRENCH LANGUAGE CONFIGURATION")

        # Check supported_languages
        result = db.execute(text("""
            SELECT setting_value FROM system_settings
            WHERE setting_key = 'supported_languages'
        """))
        row = result.fetchone()

        print("\n  1. SUPPORTED LANGUAGES:")
        if row:
            langs = row[0]
            print(f"     Current value: {langs}")
            lang_list = langs.split(',')
            if 'fr' in lang_list:
                print("     ✅ French (fr) is included")
            else:
                print("     ❌ French (fr) is MISSING")
        else:
            print("     ❌ supported_languages setting not found")

        # Check language_metadata
        result = db.execute(text("""
            SELECT setting_value FROM system_settings
            WHERE setting_key = 'language_metadata'
        """))
        row = result.fetchone()

        print("\n  2. LANGUAGE METADATA:")
        if row:
            import json
            metadata = json.loads(row[0])
            print(f"     Languages: {', '.join(metadata.keys())}")
            if 'fr' in metadata:
                print(f"     ✅ French metadata exists:")
                print(f"        - Code: {metadata['fr']['code']}")
                print(f"        - Name: {metadata['fr']['name']}")
                print(f"        - Native: {metadata['fr']['native_name']}")
            else:
                print("     ❌ French metadata MISSING")
        else:
            print("     ❌ language_metadata setting not found")

        # Check French translations for template categories
        result = db.execute(text("""
            SELECT c.reference_key, ct.name
            FROM categories c
            LEFT JOIN category_translations ct ON c.id = ct.category_id AND ct.language_code = 'fr'
            WHERE c.user_id IS NULL
            ORDER BY c.sort_order
        """))
        french_trans = result.fetchall()

        print("\n  3. FRENCH CATEGORY TRANSLATIONS:")
        missing_count = 0
        for ref_key, name in french_trans:
            if name:
                print(f"     ✅ {ref_key}: {name}")
            else:
                print(f"     ❌ {ref_key}: MISSING")
                missing_count += 1

        if missing_count > 0:
            print(f"\n     ⚠️  {missing_count} categories missing French translations")

    finally:
        db.close()


def main():
    """Main function to run tests"""
    print("\n" + "=" * 70)
    print("  BONIFATUS DMS - DATABASE INSPECTION TOOL")
    print("=" * 70)

    # Check stopwords (focused on German)
    check_stop_words()

    # COMMENTED OUT - Uncomment to run other checks
    # check_french_language_config()
    # check_migration_006()
    # check_category_standardization()
    # check_per_user_architecture()
    # check_admin_users()
    # check_categories_and_keywords()
    # search_keyword("rechnung", "de")
    # search_keyword("invoice", "en")
    # search_keyword("volksbank", "de")

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
