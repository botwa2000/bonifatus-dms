"""Add unique constraints on keywords and stopwords

Revision ID: 016_unique_constraints
Revises: 015_ml_config
Create Date: 2025-11-06 21:00:00.000000

This migration adds unique constraints to prevent duplicates:
- stop_words: unique (word, language_code)
- category_keywords: unique (category_id, keyword, language_code)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '016_unique_constraints'
down_revision = '015_ml_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraints"""
    conn = op.get_bind()

    print("\n=== ADDING UNIQUE CONSTRAINTS ===\n")

    # 1. Add unique constraint to stop_words
    print("1. Adding unique constraint to stop_words (word, language_code)...")
    try:
        op.create_index(
            'idx_stopwords_word_lang_unique',
            'stop_words',
            ['word', 'language_code'],
            unique=True
        )
        print("   ✓ stop_words unique constraint added")
    except Exception as e:
        print(f"   ⚠ Could not add stop_words constraint (may have duplicates): {e}")
        print("   → Run deduplicate_stopwords.py first, then retry migration")

    # 2. Add unique constraint to category_keywords
    print("\n2. Adding unique constraint to category_keywords (category_id, keyword, language_code)...")
    try:
        op.create_index(
            'idx_category_keywords_cat_kw_lang_unique',
            'category_keywords',
            ['category_id', 'keyword', 'language_code'],
            unique=True
        )
        print("   ✓ category_keywords unique constraint added")
    except Exception as e:
        print(f"   ⚠ Could not add category_keywords constraint (may have duplicates): {e}")
        print("   → Run deduplication script first, then retry migration")

    print("\n✅ Unique constraints migration completed")


def downgrade() -> None:
    """Remove unique constraints"""
    print("\n=== REMOVING UNIQUE CONSTRAINTS ===\n")

    # Drop indexes
    op.drop_index('idx_category_keywords_cat_kw_lang_unique', table_name='category_keywords')
    print("   ✓ category_keywords unique constraint removed")

    op.drop_index('idx_stopwords_word_lang_unique', table_name='stop_words')
    print("   ✓ stop_words unique constraint removed")

    print("\n✅ Unique constraints removed")
