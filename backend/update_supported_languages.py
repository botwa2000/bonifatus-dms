#!/usr/bin/env python3
"""
Update supported_languages system setting to include French
"""
import sys
sys.path.insert(0, '/app')

from app.database.connection import db_manager
from sqlalchemy import text

db = db_manager.session_local()
try:
    print("\n=== Updating Supported Languages ===\n")

    # Update supported_languages to include French
    result = db.execute(text("""
        UPDATE system_settings
        SET setting_value = 'en,de,ru,fr'
        WHERE setting_key = 'supported_languages'
        RETURNING setting_value
    """))
    updated = result.fetchone()

    if updated:
        print(f'✅ Updated supported_languages: {updated[0]}')
    else:
        print('⚠ supported_languages setting not found, inserting...')
        db.execute(text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, is_public, category)
            VALUES (gen_random_uuid(), 'supported_languages', 'en,de,ru,fr', 'string', true, 'general')
        """))
        print('✅ Inserted supported_languages: en,de,ru,fr')

    db.commit()
    print("\n✅ Complete!")

finally:
    db.close()
