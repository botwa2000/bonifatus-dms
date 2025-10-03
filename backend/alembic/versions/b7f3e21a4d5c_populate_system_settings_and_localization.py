# backend/alembic/versions/b7f3e21a4d5c_populate_system_settings_and_localization.py

"""Populate system settings and localization strings

Revision ID: b7f3e21a4d5c
Revises: ae442d52930d
Create Date: 2025-10-03

"""
from alembic import op
import uuid
from datetime import datetime

revision = 'b7f3e21a4d5c'
down_revision = 'd2c3e4f5g6h7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import text
    
    now = datetime.utcnow()
    
    # System Settings - using proper SQLAlchemy text binding
    system_settings_sql = text("""
        INSERT INTO system_settings 
        (id, setting_key, setting_value, data_type, description, is_public, category, created_at, updated_at)
        VALUES (:id, :key, :value, :dtype, :desc, :public, :cat, :created, :updated)
        ON CONFLICT (setting_key) DO NOTHING
    """)
    
    system_settings = [
        {'id': str(uuid.uuid4()), 'key': 'default_theme', 'value': 'light', 'dtype': 'string', 'desc': 'Default UI theme', 'public': True, 'cat': 'appearance', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'available_themes', 'value': '["light", "dark"]', 'dtype': 'json', 'desc': 'Available UI themes', 'public': True, 'cat': 'appearance', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'default_language', 'value': 'en', 'dtype': 'string', 'desc': 'Default system language', 'public': True, 'cat': 'localization', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'available_languages', 'value': '["en", "de", "ru"]', 'dtype': 'json', 'desc': 'Available UI languages', 'public': True, 'cat': 'localization', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'max_file_size_mb', 'value': '50', 'dtype': 'integer', 'desc': 'Maximum file upload size in MB', 'public': True, 'cat': 'upload', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'allowed_file_types', 'value': '["pdf", "doc", "docx", "jpg", "jpeg", "png", "txt", "tiff", "bmp"]', 'dtype': 'json', 'desc': 'Allowed file types for upload', 'public': True, 'cat': 'upload', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'default_documents_page_size', 'value': '20', 'dtype': 'integer', 'desc': 'Default number of documents per page', 'public': True, 'cat': 'pagination', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'available_page_sizes', 'value': '[10, 20, 50, 100]', 'dtype': 'json', 'desc': 'Available pagination sizes', 'public': True, 'cat': 'pagination', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'google_drive_folder_structure', 'value': '{"root": "Bonifatus_DMS", "subfolders": ["Insurance", "Legal", "Real Estate", "Banking", "Other"]}', 'dtype': 'json', 'desc': 'Google Drive folder structure', 'public': False, 'cat': 'storage', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'enable_ai_categorization', 'value': 'true', 'dtype': 'boolean', 'desc': 'Enable AI-powered document categorization', 'public': True, 'cat': 'features', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'enable_ocr', 'value': 'true', 'dtype': 'boolean', 'desc': 'Enable OCR text extraction', 'public': True, 'cat': 'features', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'enable_multilingual_support', 'value': 'true', 'dtype': 'boolean', 'desc': 'Enable multilingual document processing', 'public': True, 'cat': 'features', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'show_welcome_banner', 'value': 'true', 'dtype': 'boolean', 'desc': 'Show welcome banner for new users', 'public': True, 'cat': 'ui', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'enable_tooltips', 'value': 'true', 'dtype': 'boolean', 'desc': 'Enable UI tooltips', 'public': True, 'cat': 'ui', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'default_view_mode', 'value': 'grid', 'dtype': 'string', 'desc': 'Default document view mode (grid/list)', 'public': True, 'cat': 'ui', 'created': now, 'updated': now},
    ]
    
    # Localization strings SQL
    localization_sql = text("""
        INSERT INTO localization_strings 
        (id, string_key, language_code, string_value, context, created_at, updated_at)
        VALUES (:id, :key, :lang, :value, :ctx, :created, :updated)
    """)
    
    localization_data = [
        # Navigation - English
        {'id': str(uuid.uuid4()), 'key': 'nav.dashboard', 'lang': 'en', 'value': 'Dashboard', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.documents', 'lang': 'en', 'value': 'Documents', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.upload', 'lang': 'en', 'value': 'Upload', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.categories', 'lang': 'en', 'value': 'Categories', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.settings', 'lang': 'en', 'value': 'Settings', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.search', 'lang': 'en', 'value': 'Search', 'ctx': 'navigation', 'created': now, 'updated': now},
        
        # Navigation - German
        {'id': str(uuid.uuid4()), 'key': 'nav.dashboard', 'lang': 'de', 'value': 'Dashboard', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.documents', 'lang': 'de', 'value': 'Dokumente', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.upload', 'lang': 'de', 'value': 'Hochladen', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.categories', 'lang': 'de', 'value': 'Kategorien', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.settings', 'lang': 'de', 'value': 'Einstellungen', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.search', 'lang': 'de', 'value': 'Suchen', 'ctx': 'navigation', 'created': now, 'updated': now},
        
        # Navigation - Russian
        {'id': str(uuid.uuid4()), 'key': 'nav.dashboard', 'lang': 'ru', 'value': 'Панель управления', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.documents', 'lang': 'ru', 'value': 'Документы', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.upload', 'lang': 'ru', 'value': 'Загрузить', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.categories', 'lang': 'ru', 'value': 'Категории', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.settings', 'lang': 'ru', 'value': 'Настройки', 'ctx': 'navigation', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'nav.search', 'lang': 'ru', 'value': 'Поиск', 'ctx': 'navigation', 'created': now, 'updated': now},
        
        # User Menu - All languages
        {'id': str(uuid.uuid4()), 'key': 'user.profile', 'lang': 'en', 'value': 'Profile', 'ctx': 'user_menu', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'user.profile', 'lang': 'de', 'value': 'Profil', 'ctx': 'user_menu', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'user.profile', 'lang': 'ru', 'value': 'Профиль', 'ctx': 'user_menu', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'user.logout', 'lang': 'en', 'value': 'Logout', 'ctx': 'user_menu', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'user.logout', 'lang': 'de', 'value': 'Abmelden', 'ctx': 'user_menu', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'user.logout', 'lang': 'ru', 'value': 'Выйти', 'ctx': 'user_menu', 'created': now, 'updated': now},
        
        # Theme - All languages
        {'id': str(uuid.uuid4()), 'key': 'theme.light', 'lang': 'en', 'value': 'Light Mode', 'ctx': 'appearance', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'theme.dark', 'lang': 'en', 'value': 'Dark Mode', 'ctx': 'appearance', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'theme.light', 'lang': 'de', 'value': 'Heller Modus', 'ctx': 'appearance', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'theme.dark', 'lang': 'de', 'value': 'Dunkler Modus', 'ctx': 'appearance', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'theme.light', 'lang': 'ru', 'value': 'Светлая тема', 'ctx': 'appearance', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'theme.dark', 'lang': 'ru', 'value': 'Темная тема', 'ctx': 'appearance', 'created': now, 'updated': now},
        
        # Language - All languages
        {'id': str(uuid.uuid4()), 'key': 'language.english', 'lang': 'en', 'value': 'English', 'ctx': 'language', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'language.german', 'lang': 'en', 'value': 'German', 'ctx': 'language', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'language.russian', 'lang': 'en', 'value': 'Russian', 'ctx': 'language', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'language.english', 'lang': 'de', 'value': 'Englisch', 'ctx': 'language', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'language.german', 'lang': 'de', 'value': 'Deutsch', 'ctx': 'language', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'language.russian', 'lang': 'de', 'value': 'Russisch', 'ctx': 'language', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'language.english', 'lang': 'ru', 'value': 'Английский', 'ctx': 'language', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'language.german', 'lang': 'ru', 'value': 'Немецкий', 'ctx': 'language', 'created': now, 'updated': now},
        {'id': str(uuid.uuid4()), 'key': 'language.russian', 'lang': 'ru', 'value': 'Русский', 'ctx': 'language', 'created': now, 'updated': now},
    ]
    
    conn = op.get_bind()
    
    # Execute inserts
    for setting in system_settings:
        conn.execute(system_settings_sql, setting)
    
    for loc in localization_data:
        conn.execute(localization_sql, loc)


def downgrade() -> None:
    op.execute("DELETE FROM localization_strings WHERE context IN ('navigation', 'user_menu', 'appearance', 'language', 'common', 'document', 'message')")
    op.execute("DELETE FROM system_settings WHERE category IN ('appearance', 'localization', 'upload', 'pagination', 'storage', 'features', 'ui')")