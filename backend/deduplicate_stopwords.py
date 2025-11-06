#!/usr/bin/env python3
"""
Deduplicate stop words and category keywords in the database
Removes duplicate stopwords per language and duplicate category keywords
"""
import sys
sys.path.insert(0, '/app')

from app.database.connection import db_manager
from app.database.models import StopWord, CategoryKeyword
from sqlalchemy import func
import uuid

def deduplicate_stopwords():
    """Remove duplicate stopwords per language"""
    db = db_manager.session_local()
    try:
        print("\n" + "=" * 70)
        print("  STOPWORD DEDUPLICATION")
        print("=" * 70)

        total_deleted = 0

        for lang in ['de', 'en', 'ru', 'fr']:
            print(f"\n{lang.upper()}:")

            # Get all stopwords for this language
            all_words = db.query(StopWord).filter(
                StopWord.language_code == lang
            ).all()

            before_count = len(all_words)
            print(f"  Before: {before_count} stopwords")

            # Group by word to find duplicates
            word_groups = {}
            for sw in all_words:
                word_lower = sw.word.lower()
                if word_lower not in word_groups:
                    word_groups[word_lower] = []
                word_groups[word_lower].append(sw)

            # Find duplicates
            duplicates = {word: entries for word, entries in word_groups.items() if len(entries) > 1}

            if duplicates:
                print(f"  Found {len(duplicates)} words with duplicates:")

                deleted_count = 0
                for word, entries in duplicates.items():
                    dup_count = len(entries)
                    print(f"    • '{word}' appears {dup_count} times")

                    # Keep the first entry, delete the rest
                    for entry in entries[1:]:
                        db.delete(entry)
                        deleted_count += 1

                db.commit()
                print(f"  ✅ Deleted {deleted_count} duplicate entries")
                total_deleted += deleted_count
            else:
                print(f"  ✅ No duplicates found")

            # Verify final count
            final_count = db.query(StopWord).filter(
                StopWord.language_code == lang
            ).count()
            print(f"  After: {final_count} unique stopwords")

            if before_count != final_count:
                print(f"  📊 Reduced by {before_count - final_count} entries")

        print(f"\n  Total stopwords deleted: {total_deleted}")

        print("\n" + "=" * 70)
        print("  STOPWORD DEDUPLICATION COMPLETE")
        print("=" * 70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during stopword deduplication: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def deduplicate_category_keywords():
    """Remove duplicate category keywords"""
    db = db_manager.session_local()
    try:
        print("\n" + "=" * 70)
        print("  CATEGORY KEYWORD DEDUPLICATION")
        print("=" * 70)

        # Get all category keywords
        all_keywords = db.query(CategoryKeyword).all()

        before_count = len(all_keywords)
        print(f"\nBefore: {before_count} category keywords")

        # Group by (category_id, keyword, language_code)
        keyword_groups = {}
        for kw in all_keywords:
            key = (str(kw.category_id), kw.keyword.lower(), kw.language_code)
            if key not in keyword_groups:
                keyword_groups[key] = []
            keyword_groups[key].append(kw)

        # Find duplicates
        duplicates = {key: entries for key, entries in keyword_groups.items() if len(entries) > 1}

        if duplicates:
            print(f"Found {len(duplicates)} keyword combinations with duplicates:")

            deleted_count = 0
            for (cat_id, keyword, lang), entries in duplicates.items():
                dup_count = len(entries)
                print(f"  • Category {cat_id[:8]}... / '{keyword}' / {lang}: {dup_count} times")

                # Keep the entry with highest weight, or first if weights are equal
                entries_sorted = sorted(entries, key=lambda e: (e.weight, e.match_count), reverse=True)
                keep_entry = entries_sorted[0]

                # Delete the rest
                for entry in entries_sorted[1:]:
                    db.delete(entry)
                    deleted_count += 1

            db.commit()
            print(f"\n✅ Deleted {deleted_count} duplicate category keyword entries")
        else:
            print("✅ No duplicates found")

        # Verify final count
        final_count = db.query(CategoryKeyword).count()
        print(f"After: {final_count} unique category keywords")

        if before_count != final_count:
            print(f"📊 Reduced by {before_count - final_count} entries")

        print("\n" + "=" * 70)
        print("  CATEGORY KEYWORD DEDUPLICATION COMPLETE")
        print("=" * 70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during category keyword deduplication: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    deduplicate_stopwords()
    deduplicate_category_keywords()
