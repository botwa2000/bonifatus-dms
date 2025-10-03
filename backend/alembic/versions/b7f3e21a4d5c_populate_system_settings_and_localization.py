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
down_revision = 'c1a2b3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.utcnow()
    
    # System Settings - Comprehensive configuration
    system_settings = [
        # Appearance Settings
        (str(uuid.uuid4()), 'default_theme', 'light', 'string', 'Default UI theme', True, 'appearance', now, now),
        (str(uuid.uuid4()), 'available_themes', '["light", "dark"]', 'json', 'Available UI themes', True, 'appearance', now, now),
        
        # Localization Settings
        (str(uuid.uuid4()), 'default_language', 'en', 'string', 'Default system language', True, 'localization', now, now),
        (str(uuid.uuid4()), 'available_languages', '["en", "de", "ru"]', 'json', 'Available UI languages', True, 'localization', now, now),
        
        # Upload Settings
        (str(uuid.uuid4()), 'max_file_size_mb', '50', 'integer', 'Maximum file upload size in MB', True, 'upload', now, now),
        (str(uuid.uuid4()), 'allowed_file_types', '["pdf", "doc", "docx", "jpg", "jpeg", "png", "txt", "tiff", "bmp"]', 'json', 'Allowed file types for upload', True, 'upload', now, now),
        
        # Pagination Settings
        (str(uuid.uuid4()), 'default_documents_page_size', '20', 'integer', 'Default number of documents per page', True, 'pagination', now, now),
        (str(uuid.uuid4()), 'available_page_sizes', '[10, 20, 50, 100]', 'json', 'Available pagination sizes', True, 'pagination', now, now),
        
        # Storage Settings
        (str(uuid.uuid4()), 'google_drive_folder_structure', '{"root": "Bonifatus_DMS", "subfolders": ["Insurance", "Legal", "Real Estate", "Banking", "Other"]}', 'json', 'Google Drive folder structure', False, 'storage', now, now),
        
        # Feature Flags
        (str(uuid.uuid4()), 'enable_ai_categorization', 'true', 'boolean', 'Enable AI-powered document categorization', True, 'features', now, now),
        (str(uuid.uuid4()), 'enable_ocr', 'true', 'boolean', 'Enable OCR text extraction', True, 'features', now, now),
        (str(uuid.uuid4()), 'enable_multilingual_support', 'true', 'boolean', 'Enable multilingual document processing', True, 'features', now, now),
        
        # UI Settings
        (str(uuid.uuid4()), 'show_welcome_banner', 'true', 'boolean', 'Show welcome banner for new users', True, 'ui', now, now),
        (str(uuid.uuid4()), 'enable_tooltips', 'true', 'boolean', 'Enable UI tooltips', True, 'ui', now, now),
        (str(uuid.uuid4()), 'default_view_mode', 'grid', 'string', 'Default document view mode (grid/list)', True, 'ui', now, now),
    ]
    
    # Localization Strings - Comprehensive multilingual UI
    localization_data = [
        # ===== NAVIGATION =====
        # English
        (str(uuid.uuid4()), 'nav.dashboard', 'en', 'Dashboard', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.documents', 'en', 'Documents', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.upload', 'en', 'Upload', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.categories', 'en', 'Categories', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.settings', 'en', 'Settings', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.search', 'en', 'Search', 'navigation', now, now),
        
        # German
        (str(uuid.uuid4()), 'nav.dashboard', 'de', 'Dashboard', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.documents', 'de', 'Dokumente', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.upload', 'de', 'Hochladen', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.categories', 'de', 'Kategorien', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.settings', 'de', 'Einstellungen', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.search', 'de', 'Suchen', 'navigation', now, now),
        
        # Russian
        (str(uuid.uuid4()), 'nav.dashboard', 'ru', 'Панель управления', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.documents', 'ru', 'Документы', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.upload', 'ru', 'Загрузить', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.categories', 'ru', 'Категории', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.settings', 'ru', 'Настройки', 'navigation', now, now),
        (str(uuid.uuid4()), 'nav.search', 'ru', 'Поиск', 'navigation', now, now),
        
        # ===== USER MENU =====
        # English
        (str(uuid.uuid4()), 'user.profile', 'en', 'Profile', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.account', 'en', 'Account Settings', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.preferences', 'en', 'Preferences', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.logout', 'en', 'Logout', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.help', 'en', 'Help & Support', 'user_menu', now, now),
        
        # German
        (str(uuid.uuid4()), 'user.profile', 'de', 'Profil', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.account', 'de', 'Kontoeinstellungen', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.preferences', 'de', 'Einstellungen', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.logout', 'de', 'Abmelden', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.help', 'de', 'Hilfe & Support', 'user_menu', now, now),
        
        # Russian
        (str(uuid.uuid4()), 'user.profile', 'ru', 'Профиль', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.account', 'ru', 'Настройки аккаунта', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.preferences', 'ru', 'Предпочтения', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.logout', 'ru', 'Выйти', 'user_menu', now, now),
        (str(uuid.uuid4()), 'user.help', 'ru', 'Помощь и поддержка', 'user_menu', now, now),
        
        # ===== THEME =====
        # English
        (str(uuid.uuid4()), 'theme.light', 'en', 'Light Mode', 'appearance', now, now),
        (str(uuid.uuid4()), 'theme.dark', 'en', 'Dark Mode', 'appearance', now, now),
        (str(uuid.uuid4()), 'theme.auto', 'en', 'Auto (System)', 'appearance', now, now),
        
        # German
        (str(uuid.uuid4()), 'theme.light', 'de', 'Heller Modus', 'appearance', now, now),
        (str(uuid.uuid4()), 'theme.dark', 'de', 'Dunkler Modus', 'appearance', now, now),
        (str(uuid.uuid4()), 'theme.auto', 'de', 'Automatisch', 'appearance', now, now),
        
        # Russian
        (str(uuid.uuid4()), 'theme.light', 'ru', 'Светлая тема', 'appearance', now, now),
        (str(uuid.uuid4()), 'theme.dark', 'ru', 'Темная тема', 'appearance', now, now),
        (str(uuid.uuid4()), 'theme.auto', 'ru', 'Авто', 'appearance', now, now),
        
        # ===== LANGUAGE =====
        # English
        (str(uuid.uuid4()), 'language.english', 'en', 'English', 'language', now, now),
        (str(uuid.uuid4()), 'language.german', 'en', 'German', 'language', now, now),
        (str(uuid.uuid4()), 'language.russian', 'en', 'Russian', 'language', now, now),
        
        # German
        (str(uuid.uuid4()), 'language.english', 'de', 'Englisch', 'language', now, now),
        (str(uuid.uuid4()), 'language.german', 'de', 'Deutsch', 'language', now, now),
        (str(uuid.uuid4()), 'language.russian', 'de', 'Russisch', 'language', now, now),
        
        # Russian
        (str(uuid.uuid4()), 'language.english', 'ru', 'Английский', 'language', now, now),
        (str(uuid.uuid4()), 'language.german', 'ru', 'Немецкий', 'language', now, now),
        (str(uuid.uuid4()), 'language.russian', 'ru', 'Русский', 'language', now, now),
        
        # ===== COMMON ACTIONS =====
        # English
        (str(uuid.uuid4()), 'action.save', 'en', 'Save', 'common', now, now),
        (str(uuid.uuid4()), 'action.cancel', 'en', 'Cancel', 'common', now, now),
        (str(uuid.uuid4()), 'action.delete', 'en', 'Delete', 'common', now, now),
        (str(uuid.uuid4()), 'action.edit', 'en', 'Edit', 'common', now, now),
        (str(uuid.uuid4()), 'action.download', 'en', 'Download', 'common', now, now),
        (str(uuid.uuid4()), 'action.share', 'en', 'Share', 'common', now, now),
        (str(uuid.uuid4()), 'action.close', 'en', 'Close', 'common', now, now),
        (str(uuid.uuid4()), 'action.confirm', 'en', 'Confirm', 'common', now, now),
        
        # German
        (str(uuid.uuid4()), 'action.save', 'de', 'Speichern', 'common', now, now),
        (str(uuid.uuid4()), 'action.cancel', 'de', 'Abbrechen', 'common', now, now),
        (str(uuid.uuid4()), 'action.delete', 'de', 'Löschen', 'common', now, now),
        (str(uuid.uuid4()), 'action.edit', 'de', 'Bearbeiten', 'common', now, now),
        (str(uuid.uuid4()), 'action.download', 'de', 'Herunterladen', 'common', now, now),
        (str(uuid.uuid4()), 'action.share', 'de', 'Teilen', 'common', now, now),
        (str(uuid.uuid4()), 'action.close', 'de', 'Schließen', 'common', now, now),
        (str(uuid.uuid4()), 'action.confirm', 'de', 'Bestätigen', 'common', now, now),
        
        # Russian
        (str(uuid.uuid4()), 'action.save', 'ru', 'Сохранить', 'common', now, now),
        (str(uuid.uuid4()), 'action.cancel', 'ru', 'Отмена', 'common', now, now),
        (str(uuid.uuid4()), 'action.delete', 'ru', 'Удалить', 'common', now, now),
        (str(uuid.uuid4()), 'action.edit', 'ru', 'Редактировать', 'common', now, now),
        (str(uuid.uuid4()), 'action.download', 'ru', 'Скачать', 'common', now, now),
        (str(uuid.uuid4()), 'action.share', 'ru', 'Поделиться', 'common', now, now),
        (str(uuid.uuid4()), 'action.close', 'ru', 'Закрыть', 'common', now, now),
        (str(uuid.uuid4()), 'action.confirm', 'ru', 'Подтвердить', 'common', now, now),
        
        # ===== DOCUMENT ACTIONS =====
        # English
        (str(uuid.uuid4()), 'document.upload', 'en', 'Upload Document', 'document', now, now),
        (str(uuid.uuid4()), 'document.view', 'en', 'View Document', 'document', now, now),
        (str(uuid.uuid4()), 'document.rename', 'en', 'Rename', 'document', now, now),
        (str(uuid.uuid4()), 'document.move', 'en', 'Move to Category', 'document', now, now),
        (str(uuid.uuid4()), 'document.processing', 'en', 'Processing', 'document', now, now),
        (str(uuid.uuid4()), 'document.processed', 'en', 'Processed', 'document', now, now),
        (str(uuid.uuid4()), 'document.failed', 'en', 'Processing Failed', 'document', now, now),
        
        # German
        (str(uuid.uuid4()), 'document.upload', 'de', 'Dokument hochladen', 'document', now, now),
        (str(uuid.uuid4()), 'document.view', 'de', 'Dokument anzeigen', 'document', now, now),
        (str(uuid.uuid4()), 'document.rename', 'de', 'Umbenennen', 'document', now, now),
        (str(uuid.uuid4()), 'document.move', 'de', 'In Kategorie verschieben', 'document', now, now),
        (str(uuid.uuid4()), 'document.processing', 'de', 'Wird verarbeitet', 'document', now, now),
        (str(uuid.uuid4()), 'document.processed', 'de', 'Verarbeitet', 'document', now, now),
        (str(uuid.uuid4()), 'document.failed', 'de', 'Verarbeitung fehlgeschlagen', 'document', now, now),
        
        # Russian
        (str(uuid.uuid4()), 'document.upload', 'ru', 'Загрузить документ', 'document', now, now),
        (str(uuid.uuid4()), 'document.view', 'ru', 'Просмотр документа', 'document', now, now),
        (str(uuid.uuid4()), 'document.rename', 'ru', 'Переименовать', 'document', now, now),
        (str(uuid.uuid4()), 'document.move', 'ru', 'Переместить в категорию', 'document', now, now),
        (str(uuid.uuid4()), 'document.processing', 'ru', 'Обработка', 'document', now, now),
        (str(uuid.uuid4()), 'document.processed', 'ru', 'Обработано', 'document', now, now),
        (str(uuid.uuid4()), 'document.failed', 'ru', 'Ошибка обработки', 'document', now, now),
        
        # ===== MESSAGES & NOTIFICATIONS =====
        # English
        (str(uuid.uuid4()), 'message.success', 'en', 'Success', 'message', now, now),
        (str(uuid.uuid4()), 'message.error', 'en', 'Error', 'message', now, now),
        (str(uuid.uuid4()), 'message.warning', 'en', 'Warning', 'message', now, now),
        (str(uuid.uuid4()), 'message.info', 'en', 'Information', 'message', now, now),
        (str(uuid.uuid4()), 'message.upload_success', 'en', 'Document uploaded successfully', 'message', now, now),
        (str(uuid.uuid4()), 'message.delete_confirm', 'en', 'Are you sure you want to delete this document?', 'message', now, now),
        
        # German
        (str(uuid.uuid4()), 'message.success', 'de', 'Erfolg', 'message', now, now),
        (str(uuid.uuid4()), 'message.error', 'de', 'Fehler', 'message', now, now),
        (str(uuid.uuid4()), 'message.warning', 'de', 'Warnung', 'message', now, now),
        (str(uuid.uuid4()), 'message.info', 'de', 'Information', 'message', now, now),
        (str(uuid.uuid4()), 'message.upload_success', 'de', 'Dokument erfolgreich hochgeladen', 'message', now, now),
        (str(uuid.uuid4()), 'message.delete_confirm', 'de', 'Möchten Sie dieses Dokument wirklich löschen?', 'message', now, now),
        
        # Russian
        (str(uuid.uuid4()), 'message.success', 'ru', 'Успешно', 'message', now, now),
        (str(uuid.uuid4()), 'message.error', 'ru', 'Ошибка', 'message', now, now),
        (str(uuid.uuid4()), 'message.warning', 'ru', 'Предупреждение', 'message', now, now),
        (str(uuid.uuid4()), 'message.info', 'ru', 'Информация', 'message', now, now),
        (str(uuid.uuid4()), 'message.upload_success', 'ru', 'Документ успешно загружен', 'message', now, now),
        (str(uuid.uuid4()), 'message.delete_confirm', 'ru', 'Вы уверены, что хотите удалить этот документ?', 'message', now, now),
    ]
    
    conn = op.get_bind()
    
    # Insert system settings with conflict handling
    for setting in system_settings:
        conn.execute(
            """
            INSERT INTO system_settings 
            (id, setting_key, setting_value, data_type, description, is_public, category, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (setting_key) DO NOTHING
            """,
            setting
        )
    
    # Bulk insert localization strings
    for loc in localization_data:
        conn.execute(
            """
            INSERT INTO localization_strings 
            (id, string_key, language_code, string_value, context, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            loc
        )


def downgrade() -> None:
    op.execute("DELETE FROM localization_strings WHERE context IN ('navigation', 'user_menu', 'appearance', 'language', 'common', 'document', 'message')")
    op.execute("DELETE FROM system_settings WHERE category IN ('appearance', 'localization', 'upload', 'pagination', 'storage', 'features', 'ui')")