import sys
sys.path.insert(0, '/app')
from sqlalchemy import create_engine, text
import uuid
from datetime import datetime, timezone

target_url = 'postgresql://bonifatus:BoniDoc2025SecurePassword@host.docker.internal:5432/bonifatus_dms'
engine = create_engine(target_url, connect_args={'sslmode': 'require'})

with engine.connect() as conn:
    now = datetime.now(timezone.utc)

    print('=== POPULATING DEFAULT DATA ===\n')

    # System Settings
    print('1. System Settings...')
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
    print(f'   ✓ Inserted {len(system_settings)} system settings')

    # Default Categories
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

    category_count = 0
    translation_count = 0
    for cat_data in default_categories_config:
        category_id = str(uuid.uuid4())

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

    conn.commit()

    # Verify
    print('\n3. Verification...')
    cats = conn.execute(text('SELECT category_code, reference_key, is_system FROM categories ORDER BY sort_order')).fetchall()
    for cat in cats:
        system_flag = ' [SYSTEM]' if cat[2] else ''
        print(f'   {cat[0]}: {cat[1]}{system_flag}')

engine.dispose()
print('\n✅ Default data populated successfully!')
