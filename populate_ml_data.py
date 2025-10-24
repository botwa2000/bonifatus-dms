import sys
sys.path.insert(0, '/app')
from sqlalchemy import create_engine, text
import uuid
from datetime import datetime, timezone

target_url = 'postgresql://bonifatus:BoniDoc2025SecurePassword@host.docker.internal:5432/bonifatus_dms'
engine = create_engine(target_url, connect_args={'sslmode': 'require'})

with engine.connect() as conn:
    now = datetime.now(timezone.utc)

    print('=== POPULATING ML DATA ===\n')

    # Stop Words
    print('1. Stop Words...')
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

    # N-gram Patterns
    print('\n2. N-gram Patterns...')
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

    conn.commit()

    # Verify
    print('\n3. Verification...')
    sw_count = conn.execute(text('SELECT COUNT(*) FROM stop_words')).scalar()
    ng_count = conn.execute(text('SELECT COUNT(*) FROM ngram_patterns')).scalar()
    print(f'   Stop words: {sw_count}')
    print(f'   N-gram patterns: {ng_count}')

engine.dispose()
print('\n✅ ML data populated successfully!')
