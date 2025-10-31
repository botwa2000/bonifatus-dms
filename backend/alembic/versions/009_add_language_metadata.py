"""Add language metadata to system_settings

Revision ID: 009_language_metadata
Revises: 008_preferred_doc_langs
Create Date: 2025-10-31 00:00:00.000000
"""
from alembic import op
from sqlalchemy import text
import json

revision = '009_language_metadata'
down_revision = '008_preferred_doc_langs'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add language metadata to system_settings"""
    print("\n=== Adding Language Metadata to System Settings ===\n")
    conn = op.get_bind()

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
    result = conn.execute(text("""
        SELECT id FROM system_settings
        WHERE setting_key = 'language_metadata'
    """))
    existing = result.fetchone()

    if existing:
        # Update existing
        conn.execute(text("""
            UPDATE system_settings
            SET setting_value = :value,
                data_type = 'json',
                is_public = true
            WHERE setting_key = 'language_metadata'
        """), {"value": json.dumps(language_metadata)})
        print("   ✓ Updated existing language_metadata")
    else:
        # Insert new
        conn.execute(text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, is_public, category)
            VALUES (gen_random_uuid(), 'language_metadata', :value, 'json', true, 'general')
        """), {"value": json.dumps(language_metadata)})
        print("   ✓ Inserted new language_metadata")

    print("\n✅ Migration 009 complete!")


def downgrade() -> None:
    """Remove language metadata from system_settings"""
    conn = op.get_bind()
    conn.execute(text("""
        DELETE FROM system_settings
        WHERE setting_key = 'language_metadata'
    """))
