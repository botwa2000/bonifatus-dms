#!/usr/bin/env python3
"""
Simple script to check French language configuration in database
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Get database connection from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n" + "="*70)
print("  FRENCH LANGUAGE CONFIGURATION CHECK")
print("="*70)

# Check supported_languages
print("\n1. SUPPORTED LANGUAGES:")
cur.execute("""
    SELECT setting_key, setting_value
    FROM system_settings
    WHERE setting_key = 'supported_languages'
""")
supported_langs = cur.fetchone()
if supported_langs:
    print(f"   Setting: {supported_langs['setting_value']}")
    langs = supported_langs['setting_value'].split(',')
    if 'fr' in langs:
        print("   ✅ French (fr) is included")
    else:
        print("   ❌ French (fr) is MISSING")
else:
    print("   ❌ supported_languages setting not found")

# Check language_metadata
print("\n2. LANGUAGE METADATA:")
cur.execute("""
    SELECT setting_key, setting_value
    FROM system_settings
    WHERE setting_key = 'language_metadata'
""")
lang_metadata = cur.fetchone()
if lang_metadata:
    metadata = json.loads(lang_metadata['setting_value'])
    print(f"   Found metadata for: {', '.join(metadata.keys())}")
    if 'fr' in metadata:
        print(f"   ✅ French metadata exists:")
        print(f"      - Code: {metadata['fr']['code']}")
        print(f"      - Name: {metadata['fr']['name']}")
        print(f"      - Native: {metadata['fr']['native_name']}")
    else:
        print("   ❌ French metadata MISSING")
else:
    print("   ❌ language_metadata setting not found")

# Check French category translations
print("\n3. FRENCH CATEGORY TRANSLATIONS:")
cur.execute("""
    SELECT c.reference_key, ct.name
    FROM categories c
    LEFT JOIN category_translations ct ON c.id = ct.category_id AND ct.language_code = 'fr'
    WHERE c.user_id IS NULL
    ORDER BY c.sort_order
""")
french_translations = cur.fetchall()
print(f"   Template categories: {len(french_translations)}")
missing_count = 0
for row in french_translations:
    if row['name']:
        print(f"   ✅ {row['reference_key']}: {row['name']}")
    else:
        print(f"   ❌ {row['reference_key']}: MISSING")
        missing_count += 1

if missing_count == 0:
    print("\n   ✅ All template categories have French translations")
else:
    print(f"\n   ⚠️  {missing_count} categories missing French translations")

# Check current migration
print("\n4. CURRENT MIGRATION:")
cur.execute("SELECT version_num FROM alembic_version")
version = cur.fetchone()
print(f"   Migration: {version['version_num']}")

print("\n" + "="*70)
print("  CHECK COMPLETE")
print("="*70 + "\n")

cur.close()
conn.close()
