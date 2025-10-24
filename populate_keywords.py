import sys
sys.path.insert(0, '/app')
from sqlalchemy import create_engine, text
import uuid
from datetime import datetime, timezone

target_url = 'postgresql://bonifatus:BoniDoc2025SecurePassword@host.docker.internal:5432/bonifatus_dms'
engine = create_engine(target_url, connect_args={'sslmode': 'require'})

with engine.connect() as conn:
    now = datetime.now(timezone.utc)

    print('=== POPULATING CATEGORY KEYWORDS ===\n')

    # Get category IDs
    categories = {}
    result = conn.execute(text("SELECT id, reference_key FROM categories WHERE is_system = true"))
    for row in result:
        categories[row.reference_key] = str(row.id)

    # Category keywords per language
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
        if cat_key in categories:
            cat_id = categories[cat_key]
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

    conn.commit()
    print(f'✓ Inserted {keyword_count} category keywords')

    # Verify
    print('\nKeywords per category:')
    for cat_key in category_terms.keys():
        if cat_key in categories:
            cat_id = categories[cat_key]
            count = conn.execute(text('SELECT COUNT(*) FROM category_keywords WHERE category_id = :cat_id'), {'cat_id': cat_id}).scalar()
            ref_key = cat_key.split('.')[-1]
            print(f'  {ref_key:15} - {count} keywords')

engine.dispose()
print('\n✅ Category keywords populated successfully!')
