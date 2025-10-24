"""Populate default system data

Revision ID: 002_populate_default_data
Revises: 001_initial_schema
Create Date: 2025-10-24 16:01:00.000000

This migration populates:
- 5 system categories with translations (EN, DE, RU)
- 75 category keywords for classification
- 59 stop words for keyword filtering
- 10 n-gram patterns for phrase extraction
- 6 system settings
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import uuid
from datetime import datetime, timezone

revision = '002_populate_default_data'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Populate default data"""
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    print("=== POPULATING DEFAULT DATA ===\n")

    # 1. System Settings
    print("1. System Settings...")
    system_settings = [
        {'id': str(uuid.uuid4()), 'key': 'default_theme', 'value': 'light', 'dtype': 'string', 'desc': 'Default UI theme', 'public': True, 'cat': 'appearance'},
        {'id': str(uuid.uuid4()), 'key': 'available_themes', 'value': '["light", "dark"]', 'dtype': 'json', 'desc': 'Available UI themes', 'public': True, 'cat': 'appearance'},
        {'id': str(uuid.uuid4()), 'key': 'default_language', 'value': 'en', 'dtype': 'string', 'desc': 'Default system language', 'public': True, 'cat': 'localization'},
        {'id': str(uuid.uuid4()), 'key': 'available_languages', 'value': '["en", "de", "ru"]', 'dtype': 'json', 'desc': 'Available UI languages', 'public': True, 'cat': 'localization'},
        {'id': str(uuid.uuid4()), 'key': 'max_file_size_mb', 'value': '50', 'dtype': 'integer', 'desc': 'Maximum file upload size in MB', 'public': True, 'cat': 'upload'},
        {'id': str(uuid.uuid4()), 'key': 'storage_quota_free_bytes', 'value': '1073741824', 'dtype': 'integer', 'desc': '1 GB for free tier', 'public': False, 'cat': 'storage'},
    ]

    for setting in system_settings:
        conn.execute(text('''
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, is_public, category, created_at, updated_at)
            VALUES (:id, :key, :value, :dtype, :desc, :public, :cat, :created, :updated)
        '''), {
            'id': setting['id'], 'key': setting['key'], 'value': setting['value'],
            'dtype': setting['dtype'], 'desc': setting['desc'], 'public': setting['public'],
            'cat': setting['cat'], 'created': now, 'updated': now
        })
    print(f"   ✓ Inserted {len(system_settings)} system settings")

    # 2. Default Categories
    print('\n2. Default Categories...')
    default_categories_config = [
        {
            'reference_key': 'category.insurance',
            'category_code': 'INS',
            'translations': {
                'en': {'name': 'Insurance', 'description': 'Insurance policies, claims, and related documents'},
                'de': {'name': 'Versicherung', 'description': 'Versicherungspolicen, Ansprüche und zugehörige Dokumente'},
                'ru': {'name': 'Страхование', 'description': 'Страховые полисы, претензии и связанные документы'}
            },
            'color_hex': '#3B82F6',
            'icon_name': 'shield',
            'sort_order': 1
        },
        {
            'reference_key': 'category.legal',
            'category_code': 'LEG',
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
            'category_code': 'RES',
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
            'category_code': 'BNK',
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
            'category_code': 'OTH',
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

    category_ids = {}
    category_count = 0
    translation_count = 0
    for cat_data in default_categories_config:
        category_id = str(uuid.uuid4())
        category_ids[cat_data['reference_key']] = category_id

        conn.execute(text('''
            INSERT INTO categories (id, reference_key, category_code, color_hex, icon_name, is_system, user_id, sort_order, is_active, created_at, updated_at)
            VALUES (:id, :reference_key, :category_code, :color_hex, :icon_name, true, NULL, :sort_order, true, :created, :updated)
        '''), {
            'id': category_id,
            'reference_key': cat_data['reference_key'],
            'category_code': cat_data['category_code'],
            'color_hex': cat_data['color_hex'],
            'icon_name': cat_data['icon_name'],
            'sort_order': cat_data['sort_order'],
            'created': now,
            'updated': now
        })
        category_count += 1

        for lang_code, translation in cat_data['translations'].items():
            conn.execute(text('''
                INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
                VALUES (:id, :category_id, :language_code, :name, :description, :created, :updated)
            '''), {
                'id': str(uuid.uuid4()),
                'category_id': category_id,
                'language_code': lang_code,
                'name': translation['name'],
                'description': translation['description'],
                'created': now,
                'updated': now
            })
            translation_count += 1

    print(f'   ✓ Inserted {category_count} categories')
    print(f'   ✓ Inserted {translation_count} translations')

    # 3. Category Keywords for Classification
    print('\n3. Category Keywords...')
    category_terms = {
        'category.insurance': {
            'en': [('insurance', 3.0), ('policy', 2.8), ('coverage', 2.5), ('premium', 2.5), ('claim', 2.3)],
            'de': [('versicherung', 3.0), ('police', 2.8), ('deckung', 2.5), ('prämie', 2.5), ('schaden', 2.3)],
            'ru': [('страхование', 3.0), ('полис', 2.8), ('покрытие', 2.5), ('премия', 2.5), ('претензия', 2.3)]
        },
        'category.banking': {
            'en': [('bank', 3.0), ('account', 2.8), ('statement', 2.8), ('transaction', 2.5), ('balance', 2.5), ('payment', 2.3)],
            'de': [('bank', 3.0), ('konto', 2.8), ('kontoauszug', 2.8), ('transaktion', 2.5), ('saldo', 2.5), ('zahlung', 2.3)],
            'ru': [('банк', 3.0), ('счет', 2.8), ('выписка', 2.8), ('транзакция', 2.5), ('баланс', 2.5), ('платеж', 2.3)]
        },
        'category.legal': {
            'en': [('contract', 3.0), ('agreement', 2.8), ('legal', 2.5), ('terms', 2.5), ('conditions', 2.3)],
            'de': [('vertrag', 3.0), ('vereinbarung', 2.8), ('rechtlich', 2.5), ('bedingungen', 2.5), ('konditionen', 2.3)],
            'ru': [('контракт', 3.0), ('соглашение', 2.8), ('юридический', 2.5), ('условия', 2.5), ('положения', 2.3)]
        },
        'category.real_estate': {
            'en': [('property', 3.0), ('real estate', 3.0), ('mortgage', 2.8), ('deed', 2.5), ('lease', 2.3), ('rent', 2.3)],
            'de': [('immobilie', 3.0), ('grundstück', 2.8), ('hypothek', 2.8), ('eigentum', 2.5), ('mietvertrag', 2.3), ('miete', 2.3)],
            'ru': [('недвижимость', 3.0), ('собственность', 2.8), ('ипотека', 2.8), ('акт', 2.5), ('аренда', 2.3), ('арендная плата', 2.3)]
        },
        'category.other': {
            'en': [('document', 2.0), ('file', 2.0), ('misc', 1.5)],
            'de': [('dokument', 2.0), ('datei', 2.0), ('sonstige', 1.5)],
            'ru': [('документ', 2.0), ('файл', 2.0), ('прочие', 1.5)]
        }
    }

    keyword_count = 0
    for cat_key, lang_terms in category_terms.items():
        if cat_key in category_ids:
            cat_id = category_ids[cat_key]
            for lang, terms in lang_terms.items():
                for term, weight in terms:
                    conn.execute(text('''
                        INSERT INTO category_keywords (id, category_id, keyword, language_code, weight, match_count, is_system_default, created_at, last_updated)
                        VALUES (:id, :cat_id, :keyword, :lang, :weight, 1, true, :created, :updated)
                    '''), {
                        'id': str(uuid.uuid4()),
                        'cat_id': cat_id,
                        'keyword': term.lower(),
                        'lang': lang,
                        'weight': weight,
                        'created': now,
                        'updated': now
                    })
                    keyword_count += 1

    print(f'   ✓ Inserted {keyword_count} category keywords')

    # 4. Stop Words
    print('\n4. Stop Words...')
    stop_words_data = {
        'en': ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be'],
        'de': ['der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'und', 'oder', 'aber', 'in', 'an', 'auf', 'für', 'mit', 'von', 'zu', 'ist', 'sind'],
        'ru': ['и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да']
    }

    stop_word_count = 0
    for lang, words in stop_words_data.items():
        for word in words:
            conn.execute(text('''
                INSERT INTO stop_words (id, word, language_code, is_active, created_at)
                VALUES (:id, :word, :lang, true, :created)
            '''), {
                'id': str(uuid.uuid4()),
                'word': word.lower(),
                'lang': lang,
                'created': now
            })
            stop_word_count += 1

    print(f'   ✓ Inserted {stop_word_count} stop words')

    # 5. N-gram Patterns
    print('\n5. N-gram Patterns...')
    ngram_patterns = [
        {'pattern': 'account statement', 'type': 'banking', 'lang': 'en', 'score': 2.5},
        {'pattern': 'bank statement', 'type': 'banking', 'lang': 'en', 'score': 2.8},
        {'pattern': 'insurance policy', 'type': 'insurance', 'lang': 'en', 'score': 2.8},
        {'pattern': 'service agreement', 'type': 'legal', 'lang': 'en', 'score': 2.5},
        {'pattern': 'rental agreement', 'type': 'real_estate', 'lang': 'en', 'score': 2.5},
        {'pattern': 'kontoauszug', 'type': 'banking', 'lang': 'de', 'score': 2.8},
        {'pattern': 'versicherungspolice', 'type': 'insurance', 'lang': 'de', 'score': 2.8},
        {'pattern': 'mietvertrag', 'type': 'real_estate', 'lang': 'de', 'score': 2.5},
        {'pattern': 'банковская выписка', 'type': 'banking', 'lang': 'ru', 'score': 2.8},
        {'pattern': 'страховой полис', 'type': 'insurance', 'lang': 'ru', 'score': 2.8},
    ]

    for pattern in ngram_patterns:
        conn.execute(text('''
            INSERT INTO ngram_patterns (id, pattern, pattern_type, language_code, importance_score, usage_count, is_active, created_at, updated_at)
            VALUES (:id, :pattern, :type, :lang, :score, 0, true, :created, :updated)
        '''), {
            'id': str(uuid.uuid4()),
            'pattern': pattern['pattern'],
            'type': pattern['type'],
            'lang': pattern['lang'],
            'score': pattern['score'],
            'created': now,
            'updated': now
        })

    print(f'   ✓ Inserted {len(ngram_patterns)} n-gram patterns')

    print('\n✅ Default data populated successfully!')


def downgrade() -> None:
    """Remove default data"""
    conn = op.get_bind()

    conn.execute(text("DELETE FROM ngram_patterns"))
    conn.execute(text("DELETE FROM stop_words"))
    conn.execute(text("DELETE FROM category_keywords"))
    conn.execute(text("DELETE FROM category_translations"))
    conn.execute(text("DELETE FROM categories WHERE is_system = true"))
    conn.execute(text("DELETE FROM system_settings"))

    print("✅ Default data removed")
