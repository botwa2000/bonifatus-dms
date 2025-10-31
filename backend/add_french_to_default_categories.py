#!/usr/bin/env python3
"""
Add French translations to default system categories
"""
import sys
sys.path.insert(0, '/app')

from app.database.connection import db_manager
from app.database.models import SystemSetting
from sqlalchemy import text
import json

db = db_manager.session_local()
try:
    print("\n=== Updating Default System Categories with French ===\n")

    # Get current config
    result = db.execute(text("""
        SELECT setting_value FROM system_settings
        WHERE setting_key = 'default_system_categories'
    """))
    config = result.fetchone()

    if not config:
        print("❌ default_system_categories not found")
        sys.exit(1)

    categories = json.loads(config[0])
    print(f"Found {len(categories)} default categories\n")

    # French translations for each category
    french_translations = {
        "category.insurance": {
            "name": "Assurance",
            "description": "Polices d'assurance et documents connexes"
        },
        "category.legal": {
            "name": "Juridique",
            "description": "Contrats et documents juridiques"
        },
        "category.real_estate": {
            "name": "Immobilier",
            "description": "Propriétés et documents immobiliers"
        },
        "category.banking": {
            "name": "Bancaire",
            "description": "Relevés bancaires et documents financiers"
        },
        "category.other": {
            "name": "Autre",
            "description": "Documents non catégorisés"
        }
    }

    # Add French translations
    updated = False
    for cat in categories:
        ref_key = cat['reference_key']
        if ref_key in french_translations:
            if 'fr' not in cat['translations']:
                cat['translations']['fr'] = french_translations[ref_key]
                print(f"✅ Added French to {ref_key}: {french_translations[ref_key]['name']}")
                updated = True
            else:
                print(f"⚠ {ref_key} already has French translation")

    if updated:
        # Update database
        db.execute(text("""
            UPDATE system_settings
            SET setting_value = :value
            WHERE setting_key = 'default_system_categories'
        """), {"value": json.dumps(categories)})

        db.commit()
        print("\n✅ Default categories updated with French translations!")
    else:
        print("\n⚠ No updates needed - all categories already have French")

finally:
    db.close()
