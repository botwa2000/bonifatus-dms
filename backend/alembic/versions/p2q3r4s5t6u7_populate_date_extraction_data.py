"""Populate date extraction patterns, month names, and keywords

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2025-10-17 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json

revision = 'p2q3r4s5t6u7'
down_revision = 'o1p2q3r4s5t6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Populate date extraction configuration data"""

    # Date patterns for English
    date_patterns_en = [
        [r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', 'mdy'],
        [r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b', 'ymd'],
        [r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b', 'mdy_named'],
        [r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})\b', 'dmy_named'],
    ]

    # Date patterns for German
    date_patterns_de = [
        [r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', 'dmy'],
        [r'\b(\d{1,2})\.\s+(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember),?\s+(\d{4})\b', 'dmy_named'],
        [r'\b(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+(\d{4})\b', 'my_named'],
    ]

    # Date patterns for Russian
    date_patterns_ru = [
        [r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', 'dmy'],
        [r'\b(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря),?\s+(\d{4})\b', 'dmy_named'],
        [r'\b(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})\b', 'my_named'],
    ]

    # Month names for English
    month_names_en = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    # Month names for German
    month_names_de = {
        'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5, 'juni': 6,
        'juli': 7, 'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12
    }

    # Month names for Russian
    month_names_ru = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
        'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }

    # Date type keywords for English
    date_type_keywords_en = {
        'invoice_date': ['invoice date', 'dated', 'bill date'],
        'due_date': ['due date', 'payment due', 'due by'],
        'expiry_date': ['expiry', 'expires', 'expiration date', 'valid until'],
        'signature_date': ['signed on', 'signature date', 'executed on'],
        'tax_year': ['tax year', 'fiscal year', 'for the year'],
        'effective_date': ['effective date', 'effective from', 'starting'],
    }

    # Date type keywords for German
    date_type_keywords_de = {
        'invoice_date': ['rechnungsdatum', 'datum', 'ausgestellt'],
        'due_date': ['fälligkeitsdatum', 'zahlbar bis', 'fällig am'],
        'expiry_date': ['ablaufdatum', 'gültig bis'],
        'signature_date': ['unterschriftsdatum', 'unterzeichnet am'],
        'tax_year': ['steuerjahr', 'geschäftsjahr'],
        'effective_date': ['wirksamkeitsdatum', 'gültig ab'],
    }

    # Date type keywords for Russian
    date_type_keywords_ru = {
        'invoice_date': ['дата счета', 'выставлен', 'от'],
        'due_date': ['срок оплаты', 'оплатить до'],
        'expiry_date': ['срок действия', 'истекает', 'действителен до'],
        'signature_date': ['дата подписания', 'подписано'],
        'tax_year': ['налоговый год', 'за год'],
        'effective_date': ['вступает в силу', 'действует с'],
    }

    # OCR supported languages mapping
    ocr_supported_languages = {
        'en': 'eng',
        'de': 'deu',
        'ru': 'rus'
    }

    # Insert all settings
    settings_data = [
        # Date patterns
        ('date_patterns_en', json.dumps(date_patterns_en), 'json', 'English date extraction patterns', False, 'date_extraction'),
        ('date_patterns_de', json.dumps(date_patterns_de), 'json', 'German date extraction patterns', False, 'date_extraction'),
        ('date_patterns_ru', json.dumps(date_patterns_ru), 'json', 'Russian date extraction patterns', False, 'date_extraction'),

        # Month names
        ('month_names_en', json.dumps(month_names_en), 'json', 'English month name mappings', False, 'date_extraction'),
        ('month_names_de', json.dumps(month_names_de), 'json', 'German month name mappings', False, 'date_extraction'),
        ('month_names_ru', json.dumps(month_names_ru), 'json', 'Russian month name mappings', False, 'date_extraction'),

        # Date type keywords
        ('date_type_keywords_en', json.dumps(date_type_keywords_en), 'json', 'English date type identification keywords', False, 'date_extraction'),
        ('date_type_keywords_de', json.dumps(date_type_keywords_de), 'json', 'German date type identification keywords', False, 'date_extraction'),
        ('date_type_keywords_ru', json.dumps(date_type_keywords_ru), 'json', 'Russian date type identification keywords', False, 'date_extraction'),

        # OCR configuration
        ('ocr_supported_languages', json.dumps(ocr_supported_languages), 'json', 'OCR language code mappings', False, 'ocr'),
    ]

    for setting_key, setting_value, data_type, description, is_public, category in settings_data:
        op.execute(f"""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, is_public, category, created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                '{setting_key}',
                '{setting_value.replace("'", "''")}',
                '{data_type}',
                '{description}',
                {is_public},
                '{category}',
                NOW(),
                NOW()
            )
            ON CONFLICT (setting_key) DO NOTHING
        """)


def downgrade() -> None:
    """Remove date extraction configuration data"""

    settings_to_remove = [
        'date_patterns_en', 'date_patterns_de', 'date_patterns_ru',
        'month_names_en', 'month_names_de', 'month_names_ru',
        'date_type_keywords_en', 'date_type_keywords_de', 'date_type_keywords_ru',
        'ocr_supported_languages'
    ]

    for setting_key in settings_to_remove:
        op.execute(f"DELETE FROM system_settings WHERE setting_key = '{setting_key}'")
