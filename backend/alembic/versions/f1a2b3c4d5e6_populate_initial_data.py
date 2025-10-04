# backend/alembic/versions/f1a2b3c4d5e6_populate_initial_data.py
"""Populate initial system data

Revision ID: f1a2b3c4d5e6
Revises: 0283144cf0fb
Create Date: 2025-10-04 12:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import uuid
from datetime import datetime, timezone
import json

revision = 'f1a2b3c4d5e6'
down_revision = '0283144cf0fb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)
    
    # System Settings
    system_settings = [
        # Appearance
        {'id': str(uuid.uuid4()), 'key': 'default_theme', 'value': 'light', 'dtype': 'string', 'desc': 'Default UI theme', 'public': True, 'cat': 'appearance'},
        {'id': str(uuid.uuid4()), 'key': 'available_themes', 'value': '["light", "dark"]', 'dtype': 'json', 'desc': 'Available UI themes', 'public': True, 'cat': 'appearance'},
        
        # Localization
        {'id': str(uuid.uuid4()), 'key': 'default_language', 'value': 'en', 'dtype': 'string', 'desc': 'Default system language', 'public': True, 'cat': 'localization'},
        {'id': str(uuid.uuid4()), 'key': 'available_languages', 'value': '["en", "de", "ru"]', 'dtype': 'json', 'desc': 'Available UI languages', 'public': True, 'cat': 'localization'},
        
        # Upload
        {'id': str(uuid.uuid4()), 'key': 'max_file_size_mb', 'value': '50', 'dtype': 'integer', 'desc': 'Maximum file upload size in MB', 'public': True, 'cat': 'upload'},
        {'id': str(uuid.uuid4()), 'key': 'allowed_file_types', 'value': '["pdf", "doc", "docx", "jpg", "jpeg", "png", "txt", "tiff", "bmp"]', 'dtype': 'json', 'desc': 'Allowed file types', 'public': True, 'cat': 'upload'},
        
        # Documents
        {'id': str(uuid.uuid4()), 'key': 'default_documents_page_size', 'value': '20', 'dtype': 'integer', 'desc': 'Default pagination size', 'public': True, 'cat': 'documents'},
        {'id': str(uuid.uuid4()), 'key': 'default_documents_sort_field', 'value': 'created_at', 'dtype': 'string', 'desc': 'Default sort field', 'public': True, 'cat': 'documents'},
        {'id': str(uuid.uuid4()), 'key': 'default_documents_sort_order', 'value': 'desc', 'dtype': 'string', 'desc': 'Default sort order', 'public': True, 'cat': 'documents'},
        
        # Storage quotas by tier
        {'id': str(uuid.uuid4()), 'key': 'storage_quota_free_bytes', 'value': '1073741824', 'dtype': 'integer', 'desc': '1 GB for free tier', 'public': False, 'cat': 'storage'},
        {'id': str(uuid.uuid4()), 'key': 'storage_quota_premium_bytes', 'value': '10737418240', 'dtype': 'integer', 'desc': '10 GB for premium tier', 'public': False, 'cat': 'storage'},
        {'id': str(uuid.uuid4()), 'key': 'storage_quota_enterprise_bytes', 'value': '107374182400', 'dtype': 'integer', 'desc': '100 GB for enterprise tier', 'public': False, 'cat': 'storage'},
    ]
    
    for setting in system_settings:
        conn.execute(text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, is_public, category, created_at, updated_at)
            VALUES (:id, :key, :value, :dtype, :desc, :public, :cat, :created, :updated)
        """), {
            'id': setting['id'],
            'key': setting['key'],
            'value': setting['value'],
            'dtype': setting['dtype'],
            'desc': setting['desc'],
            'public': setting['public'],
            'cat': setting['cat'],
            'created': now,
            'updated': now
        })
    
    # Localization Strings (sample - add more as needed)
    localization_data = [
        # Navigation
        {'id': str(uuid.uuid4()), 'key': 'nav.dashboard', 'lang': 'en', 'value': 'Dashboard', 'ctx': 'navigation'},
        {'id': str(uuid.uuid4()), 'key': 'nav.dashboard', 'lang': 'de', 'value': 'Dashboard', 'ctx': 'navigation'},
        {'id': str(uuid.uuid4()), 'key': 'nav.dashboard', 'lang': 'ru', 'value': 'Панель управления', 'ctx': 'navigation'},
        
        {'id': str(uuid.uuid4()), 'key': 'nav.documents', 'lang': 'en', 'value': 'Documents', 'ctx': 'navigation'},
        {'id': str(uuid.uuid4()), 'key': 'nav.documents', 'lang': 'de', 'value': 'Dokumente', 'ctx': 'navigation'},
        {'id': str(uuid.uuid4()), 'key': 'nav.documents', 'lang': 'ru', 'value': 'Документы', 'ctx': 'navigation'},
        
        {'id': str(uuid.uuid4()), 'key': 'nav.categories', 'lang': 'en', 'value': 'Categories', 'ctx': 'navigation'},
        {'id': str(uuid.uuid4()), 'key': 'nav.categories', 'lang': 'de', 'value': 'Kategorien', 'ctx': 'navigation'},
        {'id': str(uuid.uuid4()), 'key': 'nav.categories', 'lang': 'ru', 'value': 'Категории', 'ctx': 'navigation'},
        
        # Theme
        {'id': str(uuid.uuid4()), 'key': 'theme.light', 'lang': 'en', 'value': 'Light', 'ctx': 'appearance'},
        {'id': str(uuid.uuid4()), 'key': 'theme.light', 'lang': 'de', 'value': 'Hell', 'ctx': 'appearance'},
        {'id': str(uuid.uuid4()), 'key': 'theme.light', 'lang': 'ru', 'value': 'Светлая', 'ctx': 'appearance'},
        
        {'id': str(uuid.uuid4()), 'key': 'theme.dark', 'lang': 'en', 'value': 'Dark', 'ctx': 'appearance'},
        {'id': str(uuid.uuid4()), 'key': 'theme.dark', 'lang': 'de', 'value': 'Dunkel', 'ctx': 'appearance'},
        {'id': str(uuid.uuid4()), 'key': 'theme.dark', 'lang': 'ru', 'value': 'Темная', 'ctx': 'appearance'},
    ]
    
    for loc in localization_data:
        conn.execute(text("""
            INSERT INTO localization_strings (id, string_key, language_code, string_value, context, created_at, updated_at)
            VALUES (:id, :key, :lang, :value, :ctx, :created, :updated)
        """), {
            'id': loc['id'],
            'key': loc['key'],
            'lang': loc['lang'],
            'value': loc['value'],
            'ctx': loc['ctx'],
            'created': now,
            'updated': now
        })
    
    # Default Categories
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
        category_id = str(uuid.uuid4())
        
        conn.execute(text("""
            INSERT INTO categories (id, reference_key, color_hex, icon_name, is_system, user_id, sort_order, is_active, created_at, updated_at)
            VALUES (:id, :reference_key, :color_hex, :icon_name, true, NULL, :sort_order, true, :created, :updated)
        """), {
            'id': category_id,
            'reference_key': cat_data['reference_key'],
            'color_hex': cat_data['color_hex'],
            'icon_name': cat_data['icon_name'],
            'sort_order': cat_data['sort_order'],
            'created': now,
            'updated': now
        })
        
        for lang_code, translation in cat_data['translations'].items():
            conn.execute(text("""
                INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
                VALUES (:id, :category_id, :language_code, :name, :description, :created, :updated)
            """), {
                'id': str(uuid.uuid4()),
                'category_id': category_id,
                'language_code': lang_code,
                'name': translation['name'],
                'description': translation['description'],
                'created': now,
                'updated': now
            })


def downgrade() -> None:
    conn = op.get_bind()
    
    conn.execute(text("DELETE FROM category_translations WHERE category_id IN (SELECT id FROM categories WHERE is_system = true)"))
    conn.execute(text("DELETE FROM categories WHERE is_system = true"))
    conn.execute(text("DELETE FROM localization_strings"))
    conn.execute(text("DELETE FROM system_settings"))