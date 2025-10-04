# backend/alembic/versions/ae442d52930d_populate_initial_system_categories.py
"""Populate initial system categories with dynamic translations

Revision ID: ae442d52930d
Revises: b7f3e21a4d5c
Create Date: 2025-09-21 10:15:23.456789
"""
from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime, timezone
import json

revision = 'ae442d52930d'
down_revision = 'b7f3e21a4d5c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc).isoformat()
    
    # Get available languages from system_settings
    result = conn.execute(sa.text(
        "SELECT setting_value FROM system_settings WHERE setting_key = 'available_languages'"
    )).fetchone()
    
    if result:
        available_languages = json.loads(result.setting_value)
    else:
        available_languages = ['en', 'de', 'ru']
    
    # Define default categories with all translations
    default_categories = [
        {
            'reference_key': 'category.insurance',
            'translations': {
                'en': {'name': 'Insurance', 'description': 'Insurance policies, claims, and related documents'},
                'de': {'name': 'Versicherung', 'description': 'Versicherungspolicen, Ansprüche und zugehörige Dokumente'},
                'ru': {'name': 'Страхование', 'description': 'Страховые полисы, претензии и сопутствующие документы'}
            },
            'color_hex': '#3B82F6',
            'icon_name': 'shield',
            'sort_order': 1
        },
        {
            'reference_key': 'category.legal',
            'translations': {
                'en': {'name': 'Legal', 'description': 'Legal documents, contracts, and agreements'},
                'de': {'name': 'Rechtsdokumente', 'description': 'Rechtsdokumente, Verträge und Vereinbarungen'},
                'ru': {'name': 'Юридические', 'description': 'Юридические документы, договоры и соглашения'}
            },
            'color_hex': '#8B5CF6',
            'icon_name': 'scales',
            'sort_order': 2
        },
        {
            'reference_key': 'category.real_estate',
            'translations': {
                'en': {'name': 'Real Estate', 'description': 'Property documents, deeds, and real estate transactions'},
                'de': {'name': 'Immobilien', 'description': 'Immobiliendokumente, Urkunden und Immobilientransaktionen'},
                'ru': {'name': 'Недвижимость', 'description': 'Документы на недвижимость, сделки и операции'}
            },
            'color_hex': '#10B981',
            'icon_name': 'home',
            'sort_order': 3
        },
        {
            'reference_key': 'category.banking',
            'translations': {
                'en': {'name': 'Banking', 'description': 'Bank statements, financial documents, and transactions'},
                'de': {'name': 'Banking', 'description': 'Kontoauszüge, Finanzdokumente und Transaktionen'},
                'ru': {'name': 'Банковские', 'description': 'Банковские выписки, финансовые документы и операции'}
            },
            'color_hex': '#F59E0B',
            'icon_name': 'bank',
            'sort_order': 4
        },
        {
            'reference_key': 'category.other',
            'translations': {
                'en': {'name': 'Other', 'description': 'Miscellaneous documents and files'},
                'de': {'name': 'Sonstige', 'description': 'Verschiedene Dokumente und Dateien'},
                'ru': {'name': 'Прочие', 'description': 'Разные документы и файлы'}
            },
            'color_hex': '#6B7280',
            'icon_name': 'folder',
            'sort_order': 5
        }
    ]
    
    for cat_data in default_categories:
        # Insert category
        category_id = str(uuid.uuid4())
        
        conn.execute(sa.text("""
            INSERT INTO categories (
                id, reference_key, color_hex, icon_name, is_system, 
                user_id, sort_order, is_active, created_at, updated_at
            ) VALUES (
                :id, :reference_key, :color_hex, :icon_name, true,
                NULL, :sort_order, true, :created_at, :updated_at
            )
        """), {
            'id': category_id,
            'reference_key': cat_data['reference_key'],
            'color_hex': cat_data['color_hex'],
            'icon_name': cat_data['icon_name'],
            'sort_order': cat_data['sort_order'],
            'created_at': now,
            'updated_at': now
        })
        
        # Insert translations only for available languages
        for lang_code in available_languages:
            if lang_code in cat_data['translations']:
                translation = cat_data['translations'][lang_code]
                
                conn.execute(sa.text("""
                    INSERT INTO category_translations (
                        id, category_id, language_code, name, description, created_at, updated_at
                    ) VALUES (
                        :id, :category_id, :language_code, :name, :description, :created_at, :updated_at
                    )
                """), {
                    'id': str(uuid.uuid4()),
                    'category_id': category_id,
                    'language_code': lang_code,
                    'name': translation['name'],
                    'description': translation['description'],
                    'created_at': now,
                    'updated_at': now
                })


def downgrade() -> None:
    conn = op.get_bind()
    
    # Delete translations for system categories
    conn.execute(sa.text("""
        DELETE FROM category_translations 
        WHERE category_id IN (
            SELECT id FROM categories WHERE is_system = true
        )
    """))
    
    # Delete system categories
    conn.execute(sa.text("DELETE FROM categories WHERE is_system = true"))