#!/usr/bin/env python3
"""
Initialize date extraction patterns in system_settings

This script populates the database with date patterns, month names, and date type keywords
for the date extraction service to function properly.

Usage:
    python backend/scripts/init_date_patterns.py

Supports languages: en, de, ru
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# Date regex patterns for each language
# Format: [regex_pattern, format_type]
# format_type: dmy, mdy, ymd, named_month

DATE_PATTERNS_EN = [
    # ISO format: YYYY-MM-DD
    [r'(\d{4})-(\d{1,2})-(\d{1,2})', 'ymd'],

    # US format: MM/DD/YYYY, M/D/YYYY
    [r'(\d{1,2})/(\d{1,2})/(\d{4})', 'mdy'],

    # Named months: January 15, 2024 | Jan 15, 2024
    [r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[\s,]+(\d{1,2})[\s,]+(\d{4})', 'named_month'],

    # Named months: 15 January 2024 | 15 Jan 2024
    [r'(\d{1,2})[\s]+of[\s]+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[\s,]+(\d{4})', 'dmy_named'],

    # UK format: DD/MM/YYYY
    [r'(\d{1,2})/(\d{1,2})/(\d{4})', 'dmy'],

    # Dot separator: DD.MM.YYYY
    [r'(\d{1,2})\.(\d{1,2})\.(\d{4})', 'dmy'],
]

DATE_PATTERNS_DE = [
    # German standard: DD.MM.YYYY
    [r'(\d{1,2})\.(\d{1,2})\.(\d{4})', 'dmy'],

    # ISO format: YYYY-MM-DD
    [r'(\d{4})-(\d{1,2})-(\d{1,2})', 'ymd'],

    # Named months: 15. Januar 2024
    [r'(\d{1,2})\.[\s]+(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Sept|Okt|Nov|Dez)[\s,]+(\d{4})', 'dmy_named'],

    # Alternative: DD/MM/YYYY
    [r'(\d{1,2})/(\d{1,2})/(\d{4})', 'dmy'],
]

DATE_PATTERNS_RU = [
    # Russian standard: DD.MM.YYYY
    [r'(\d{1,2})\.(\d{1,2})\.(\d{4})', 'dmy'],

    # ISO format: YYYY-MM-DD
    [r'(\d{4})-(\d{1,2})-(\d{1,2})', 'ymd'],

    # Named months: 15 января 2024
    [r'(\d{1,2})[\s]+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|янв|фев|мар|апр|май|июн|июл|авг|сен|сент|окт|ноя|дек)[\s,]+(\d{4})', 'dmy_named'],

    # Alternative with dots: DD.MM.YYYY г.
    [r'(\d{1,2})\.(\d{1,2})\.(\d{4})[\s]*г\.?', 'dmy'],

    # Alternative: DD/MM/YYYY
    [r'(\d{1,2})/(\d{1,2})/(\d{4})', 'dmy'],
]


# Month name mappings to numbers

MONTH_NAMES_EN = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}

MONTH_NAMES_DE = {
    "januar": 1, "jan": 1,
    "februar": 2, "feb": 2,
    "märz": 3, "mär": 3,
    "april": 4, "apr": 4,
    "mai": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12
}

MONTH_NAMES_RU = {
    "января": 1, "янв": 1,
    "февраля": 2, "фев": 2,
    "марта": 3, "мар": 3,
    "апреля": 4, "апр": 4,
    "мая": 5, "май": 5,
    "июня": 6, "июн": 6,
    "июля": 7, "июл": 7,
    "августа": 8, "авг": 8,
    "сентября": 9, "сен": 9, "сент": 9,
    "октября": 10, "окт": 10,
    "ноября": 11, "ноя": 11,
    "декабря": 12, "дек": 12
}


# Date type keywords - keywords that appear near dates to identify their type

DATE_TYPE_KEYWORDS_EN = {
    "invoice_date": [
        "invoice date", "bill date", "invoiced", "billed on",
        "date of invoice", "invoice issued", "billing date",
        "rechnung vom", "facture du"  # Common in multilingual invoices
    ],
    "due_date": [
        "due date", "payment due", "due by", "payable by",
        "pay by", "deadline", "expires on", "expiry date",
        "fällig am", "échéance"
    ],
    "signature_date": [
        "signature date", "signed on", "executed on", "signed",
        "date of signature", "signing date", "unterzeichnet am"
    ],
    "effective_date": [
        "effective date", "effective from", "commencing on",
        "start date", "begins on", "in effect from",
        "wirksam ab", "en vigueur"
    ],
    "expiry_date": [
        "expiry date", "expires on", "expiration date",
        "valid until", "valid through", "validity",
        "gültig bis", "valable jusqu'au"
    ],
    "tax_year": [
        "tax year", "fiscal year", "tax period", "fy",
        "for the year", "annual return", "steuerjahr",
        "année fiscale"
    ],
    "tax_period_start": [
        "period from", "start of period", "beginning",
        "von", "du"
    ],
    "tax_period_end": [
        "period to", "end of period", "ending",
        "bis", "au"
    ],
    "birth_date": [
        "date of birth", "birth date", "born on", "dob",
        "geboren am", "né le"
    ],
    "issue_date": [
        "issue date", "issued on", "date issued",
        "ausgestellt am", "délivré le"
    ]
}

DATE_TYPE_KEYWORDS_DE = {
    "invoice_date": [
        "rechnungsdatum", "rechnung vom", "datum der rechnung",
        "ausgestellt am", "rechnungsdatum", "fakturadatum",
        "invoice date", "bill date"
    ],
    "due_date": [
        "fälligkeitsdatum", "fällig am", "zahlbar bis",
        "zahlung bis", "zahlungsziel", "zahlungsfrist",
        "due date", "payment due"
    ],
    "signature_date": [
        "unterschriftsdatum", "unterzeichnet am", "datum der unterschrift",
        "signature date", "signed on"
    ],
    "effective_date": [
        "gültig ab", "wirksam ab", "in kraft ab",
        "startdatum", "beginn", "effective date"
    ],
    "expiry_date": [
        "ablaufdatum", "gültig bis", "verfallsdatum",
        "läuft ab am", "gültigkeit", "expiry date"
    ],
    "tax_year": [
        "steuerjahr", "geschäftsjahr", "veranlagungszeitraum",
        "für das jahr", "tax year", "fiscal year"
    ],
    "tax_period_start": [
        "zeitraum von", "beginn des zeitraums", "anfang",
        "von", "period from"
    ],
    "tax_period_end": [
        "zeitraum bis", "ende des zeitraums", "bis",
        "period to"
    ],
    "birth_date": [
        "geburtsdatum", "geboren am", "geb.",
        "date of birth", "dob"
    ],
    "issue_date": [
        "ausstellungsdatum", "ausgestellt am", "ausgabedatum",
        "issue date", "issued on"
    ]
}

DATE_TYPE_KEYWORDS_RU = {
    "invoice_date": [
        "дата счета", "дата выставления", "счет от",
        "выставлен", "дата счета-фактуры",
        "invoice date", "rechnungsdatum"
    ],
    "due_date": [
        "срок оплаты", "оплатить до", "срок платежа",
        "к оплате до", "due date", "fällig am"
    ],
    "signature_date": [
        "дата подписания", "подписан", "дата подписи",
        "signature date", "unterzeichnet am"
    ],
    "effective_date": [
        "дата вступления в силу", "действует с", "начало действия",
        "с даты", "effective date", "wirksam ab"
    ],
    "expiry_date": [
        "дата истечения", "действителен до", "срок действия",
        "истекает", "expiry date", "gültig bis"
    ],
    "tax_year": [
        "налоговый год", "отчетный год", "за год",
        "налоговый период", "tax year", "steuerjahr"
    ],
    "tax_period_start": [
        "период с", "начало периода", "с",
        "period from", "von"
    ],
    "tax_period_end": [
        "период по", "конец периода", "по",
        "period to", "bis"
    ],
    "birth_date": [
        "дата рождения", "родился", "дата рожд.",
        "date of birth", "geboren am"
    ],
    "issue_date": [
        "дата выдачи", "выдан", "дата выпуска",
        "issue date", "ausgestellt am"
    ]
}


def populate_date_patterns():
    """Populate system_settings with date extraction configuration"""

    try:
        # Create database connection
        database_url = settings.database.database_url
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        print("🚀 Starting date patterns initialization...")
        print(f"📊 Database: {settings.database.database_url.split('@')[1] if '@' in settings.database.database_url else 'local'}")
        print()

        configs = [
            # English patterns
            {
                'key': 'date_patterns_en',
                'value': json.dumps(DATE_PATTERNS_EN),
                'description': 'Date regex patterns for English (format: [pattern, format_type])',
                'category': 'date_extraction'
            },
            {
                'key': 'month_names_en',
                'value': json.dumps(MONTH_NAMES_EN),
                'description': 'English month name to number mapping',
                'category': 'date_extraction'
            },
            {
                'key': 'date_type_keywords_en',
                'value': json.dumps(DATE_TYPE_KEYWORDS_EN),
                'description': 'English keywords for date type identification',
                'category': 'date_extraction'
            },

            # German patterns
            {
                'key': 'date_patterns_de',
                'value': json.dumps(DATE_PATTERNS_DE),
                'description': 'Date regex patterns for German (format: [pattern, format_type])',
                'category': 'date_extraction'
            },
            {
                'key': 'month_names_de',
                'value': json.dumps(MONTH_NAMES_DE),
                'description': 'German month name to number mapping',
                'category': 'date_extraction'
            },
            {
                'key': 'date_type_keywords_de',
                'value': json.dumps(DATE_TYPE_KEYWORDS_DE),
                'description': 'German keywords for date type identification',
                'category': 'date_extraction'
            },

            # Russian patterns
            {
                'key': 'date_patterns_ru',
                'value': json.dumps(DATE_PATTERNS_RU),
                'description': 'Date regex patterns for Russian (format: [pattern, format_type])',
                'category': 'date_extraction'
            },
            {
                'key': 'month_names_ru',
                'value': json.dumps(MONTH_NAMES_RU),
                'description': 'Russian month name to number mapping',
                'category': 'date_extraction'
            },
            {
                'key': 'date_type_keywords_ru',
                'value': json.dumps(DATE_TYPE_KEYWORDS_RU),
                'description': 'Russian keywords for date type identification',
                'category': 'date_extraction'
            },
        ]

        inserted = 0
        updated = 0

        for config in configs:
            # Check if setting already exists
            result = session.execute(
                text("SELECT id FROM system_settings WHERE setting_key = :key"),
                {'key': config['key']}
            ).fetchone()

            if result:
                # Update existing
                session.execute(
                    text("""
                        UPDATE system_settings
                        SET setting_value = :value,
                            description = :description,
                            category = :category,
                            updated_at = NOW()
                        WHERE setting_key = :key
                    """),
                    {
                        'key': config['key'],
                        'value': config['value'],
                        'description': config['description'],
                        'category': config['category']
                    }
                )
                updated += 1
                print(f"✅ Updated: {config['key']}")
            else:
                # Insert new
                import uuid
                session.execute(
                    text("""
                        INSERT INTO system_settings
                        (id, setting_key, setting_value, description, category, created_at, updated_at)
                        VALUES
                        (:id, :key, :value, :description, :category, NOW(), NOW())
                    """),
                    {
                        'id': str(uuid.uuid4()),
                        'key': config['key'],
                        'value': config['value'],
                        'description': config['description'],
                        'category': config['category']
                    }
                )
                inserted += 1
                print(f"✨ Inserted: {config['key']}")

        session.commit()
        session.close()

        print()
        print("=" * 60)
        print("✅ Date patterns initialization complete!")
        print(f"📊 Statistics:")
        print(f"   - New settings inserted: {inserted}")
        print(f"   - Existing settings updated: {updated}")
        print(f"   - Total configurations: {len(configs)}")
        print()
        print("🎯 Supported features:")
        print("   - Languages: English, German, Russian")
        print("   - Date formats: ISO, US, UK, German, Russian")
        print("   - Date types: invoice_date, due_date, tax_year, and 8 more")
        print()
        print("📝 Next steps:")
        print("   1. Restart backend container to load new settings")
        print("   2. Upload a test document with dates")
        print("   3. Verify dates are extracted and stored correctly")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    populate_date_patterns()
