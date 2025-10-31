#!/usr/bin/env python3
"""
Add language metadata to system_settings for frontend display
"""
import sys
sys.path.insert(0, '/app')

from app.database.connection import db_manager
from sqlalchemy import text
import json

db = db_manager.session_local()
try:
    print("\n=== Adding Language Metadata to System Settings ===\n")

    # Language metadata with native names and English names
    language_metadata = {
        "en": {
            "code": "en",
            "name": "English",
            "native_name": "English"
        },
        "de": {
            "code": "de",
            "name": "German",
            "native_name": "Deutsch"
        },
        "ru": {
            "code": "ru",
            "name": "Russian",
            "native_name": "Русский"
        },
        "fr": {
            "code": "fr",
            "name": "French",
            "native_name": "Français"
        }
    }

    # Check if setting already exists
    result = db.execute(text("""
        SELECT id FROM system_settings
        WHERE setting_key = 'language_metadata'
    """))
    existing = result.fetchone()

    if existing:
        # Update existing
        db.execute(text("""
            UPDATE system_settings
            SET setting_value = :value,
                data_type = 'json',
                is_public = true
            WHERE setting_key = 'language_metadata'
        """), {"value": json.dumps(language_metadata)})
        print("✅ Updated existing language_metadata")
    else:
        # Insert new
        db.execute(text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, is_public, category)
            VALUES (gen_random_uuid(), 'language_metadata', :value, 'json', true, 'general')
        """), {"value": json.dumps(language_metadata)})
        print("✅ Inserted new language_metadata")

    db.commit()

    # Display the metadata
    print("\nLanguage metadata added:")
    for code, meta in language_metadata.items():
        print(f"  {code}: {meta['native_name']} ({meta['name']})")

    print("\n✅ Language metadata configuration complete!")

finally:
    db.close()
