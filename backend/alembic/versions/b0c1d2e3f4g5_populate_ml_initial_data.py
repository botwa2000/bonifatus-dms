# backend/alembic/versions/b0c1d2e3f4g5_populate_ml_initial_data.py
"""Populate ML initial training data - scalable for future languages

Revision ID: b0c1d2e3f4g5
Revises: a9b8c7d6e5f4
Create Date: 2025-10-10 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import uuid
from datetime import datetime, timezone

revision = 'b0c1d2e3f4g5'
down_revision = 'a9b8c7d6e5f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)
    
    # ============================================================
    # 1. Move hardcoded values to system_settings
    # ============================================================
    
    file_config_settings = [
        {
            'id': str(uuid.uuid4()),
            'key': 'allowed_mime_types',
            'value': '["application/pdf", "image/jpeg", "image/png", "image/jpg", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/plain", "image/tiff", "image/bmp"]',
            'dtype': 'json',
            'desc': 'Allowed file MIME types for upload',
            'public': True,
            'cat': 'upload'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'max_file_size_bytes',
            'value': '104857600',
            'dtype': 'integer',
            'desc': 'Maximum file size in bytes (100MB default)',
            'public': True,
            'cat': 'upload'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'min_keyword_length',
            'value': '3',
            'dtype': 'integer',
            'desc': 'Minimum keyword length for extraction',
            'public': False,
            'cat': 'ml'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'max_keywords_per_document',
            'value': '20',
            'dtype': 'integer',
            'desc': 'Maximum keywords to extract per document',
            'public': False,
            'cat': 'ml'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'keyword_relevance_threshold',
            'value': '0.3',
            'dtype': 'float',
            'desc': 'Minimum relevance score for keyword extraction',
            'public': False,
            'cat': 'ml'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'spelling_correction_enabled',
            'value': 'true',
            'dtype': 'boolean',
            'desc': 'Enable automatic spelling correction for keywords',
            'public': False,
            'cat': 'ml'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'ngram_extraction_enabled',
            'value': 'true',
            'dtype': 'boolean',
            'desc': 'Enable n-gram (multi-word) keyword extraction',
            'public': False,
            'cat': 'ml'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'category_confidence_threshold',
            'value': '0.6',
            'dtype': 'float',
            'desc': 'Minimum confidence for automatic category suggestion',
            'public': False,
            'cat': 'ml'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'max_filename_length',
            'value': '200',
            'dtype': 'integer',
            'desc': 'Maximum filename length (characters)',
            'public': True,
            'cat': 'upload'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'filename_pattern',
            'value': '{title}_{timestamp}',
            'dtype': 'string',
            'desc': 'Filename pattern: {title}, {timestamp}, {category}, {language}',
            'public': False,
            'cat': 'upload'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'max_batch_upload_size',
            'value': '10',
            'dtype': 'integer',
            'desc': 'Maximum files per batch upload',
            'public': True,
            'cat': 'upload'
        },
        {
            'id': str(uuid.uuid4()),
            'key': 'max_categories_per_document',
            'value': '5',
            'dtype': 'integer',
            'desc': 'Maximum categories per document',
            'public': True,
            'cat': 'documents'
        }
    ]
    
    for setting in file_config_settings:
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
    
    # ============================================================
    # 2. Stop Words (Scalable: Easy to add new languages)
    # ============================================================
    
    stop_words_data = {
        'en': ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'where', 'when', 'why', 'how'],
        'de': ['der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer', 'eines', 'einem', 'einen', 'und', 'oder', 'aber', 'in', 'an', 'auf', 'für', 'mit', 'von', 'zu', 'bei', 'ist', 'sind', 'war', 'waren', 'sein', 'haben', 'hat', 'hatte', 'werden', 'wird', 'wurde', 'wurde', 'dieser', 'diese', 'dieses', 'jener', 'jene', 'jenes', 'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'was', 'welche', 'welcher', 'welches', 'wo', 'wann', 'warum', 'wie'],
        'ru': ['и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно', 'всю', 'между']
    }
    
    for lang, words in stop_words_data.items():
        for word in words:
            conn.execute(text("""
                INSERT INTO stop_words (id, word, language_code, is_active, created_at)
                VALUES (:id, :word, :lang, true, :created)
            """), {
                'id': str(uuid.uuid4()),
                'word': word.lower(),
                'lang': lang,
                'created': now
            })
    
    # ============================================================
    # 3. Common OCR Spelling Corrections (Per Language)
    # ============================================================
    
    spelling_corrections = [
        # English
        {'incorrect': 'fpotant', 'correct': 'important', 'lang': 'en', 'confidence': 0.95},
        {'incorrect': 'rateadjustment', 'correct': 'rate adjustment', 'lang': 'en', 'confidence': 0.9},
        {'incorrect': 'accuont', 'correct': 'account', 'lang': 'en', 'confidence': 0.9},
        {'incorrect': 'dcument', 'correct': 'document', 'lang': 'en', 'confidence': 0.9},
        {'incorrect': 'statment', 'correct': 'statement', 'lang': 'en', 'confidence': 0.9},
        {'incorrect': 'transactin', 'correct': 'transaction', 'lang': 'en', 'confidence': 0.9},
        {'incorrect': 'insurence', 'correct': 'insurance', 'lang': 'en', 'confidence': 0.9},
        {'incorrect': 'poilcy', 'correct': 'policy', 'lang': 'en', 'confidence': 0.9},
        {'incorrect': 'cnntract', 'correct': 'contract', 'lang': 'en', 'confidence': 0.9},
        {'incorrect': 'agrrement', 'correct': 'agreement', 'lang': 'en', 'confidence': 0.9},
        
        # German
        {'incorrect': 'versichernung', 'correct': 'versicherung', 'lang': 'de', 'confidence': 0.9},
        {'incorrect': 'vertag', 'correct': 'vertrag', 'lang': 'de', 'confidence': 0.9},
        {'incorrect': 'kuntn', 'correct': 'konto', 'lang': 'de', 'confidence': 0.9},
        {'incorrect': 'dckument', 'correct': 'dokument', 'lang': 'de', 'confidence': 0.9},
        
        # Russian
        {'incorrect': 'страхование', 'correct': 'страхование', 'lang': 'ru', 'confidence': 0.9},
        {'incorrect': 'дкумент', 'correct': 'документ', 'lang': 'ru', 'confidence': 0.9}
    ]
    
    for correction in spelling_corrections:
        conn.execute(text("""
            INSERT INTO spelling_corrections (id, incorrect_term, correct_term, language_code, confidence_score, usage_count, created_at, updated_at)
            VALUES (:id, :incorrect, :correct, :lang, :confidence, 0, :created, :updated)
        """), {
            'id': str(uuid.uuid4()),
            'incorrect': correction['incorrect'],
            'correct': correction['correct'],
            'lang': correction['lang'],
            'confidence': correction['confidence'],
            'created': now,
            'updated': now
        })
    
    # ============================================================
    # 4. Initial Category Term Weights (Language-Specific)
    # ============================================================
    
    # Get category IDs
    categories = {}
    result = conn.execute(text("SELECT id, reference_key FROM categories WHERE is_system = true"))
    for row in result:
        categories[row.reference_key] = str(row.id)
    
    # Category term weights per language
    category_terms = {
        'category.insurance': {
            'en': [('insurance', 3.0), ('policy', 2.8), ('coverage', 2.5), ('premium', 2.5), ('claim', 2.3), ('deductible', 2.0), ('policyholder', 2.0), ('insured', 1.8), ('liability', 1.8), ('beneficiary', 1.5), ('underwriter', 1.5), ('risk', 1.3), ('accident', 1.2), ('health insurance', 2.5), ('life insurance', 2.5), ('car insurance', 2.3), ('home insurance', 2.3), ('travel insurance', 2.0)],
            'de': [('versicherung', 3.0), ('police', 2.8), ('deckung', 2.5), ('prämie', 2.5), ('schaden', 2.3), ('selbstbeteiligung', 2.0), ('versicherungsnehmer', 2.0), ('versichert', 1.8), ('haftung', 1.8), ('begünstigter', 1.5), ('versicherer', 1.5), ('risiko', 1.3), ('unfall', 1.2), ('krankenversicherung', 2.5), ('lebensversicherung', 2.5), ('autoversicherung', 2.3), ('hausratversicherung', 2.3)],
            'ru': [('страхование', 3.0), ('полис', 2.8), ('покрытие', 2.5), ('премия', 2.5), ('претензия', 2.3), ('франшиза', 2.0), ('страхователь', 2.0), ('застрахованный', 1.8), ('ответственность', 1.8), ('выгодоприобретатель', 1.5), ('страховщик', 1.5), ('риск', 1.3), ('авария', 1.2), ('медицинская страховка', 2.5), ('страхование жизни', 2.5), ('автострахование', 2.3)]
        },
        'category.banking': {
            'en': [('bank', 3.0), ('account', 2.8), ('statement', 2.8), ('transaction', 2.5), ('balance', 2.5), ('payment', 2.3), ('transfer', 2.3), ('deposit', 2.0), ('withdrawal', 2.0), ('credit', 1.8), ('debit', 1.8), ('loan', 1.8), ('interest', 1.5), ('overdraft', 1.5), ('iban', 1.5), ('swift', 1.5), ('branch', 1.3), ('atm', 1.3), ('checking account', 2.3), ('savings account', 2.3), ('bank statement', 2.8), ('wire transfer', 2.3)],
            'de': [('bank', 3.0), ('konto', 2.8), ('kontoauszug', 2.8), ('transaktion', 2.5), ('saldo', 2.5), ('zahlung', 2.3), ('überweisung', 2.3), ('einzahlung', 2.0), ('auszahlung', 2.0), ('kredit', 1.8), ('lastschrift', 1.8), ('darlehen', 1.8), ('zinsen', 1.5), ('überziehung', 1.5), ('iban', 1.5), ('bic', 1.5), ('filiale', 1.3), ('geldautomat', 1.3), ('girokonto', 2.3), ('sparkonto', 2.3)],
            'ru': [('банк', 3.0), ('счет', 2.8), ('выписка', 2.8), ('транзакция', 2.5), ('баланс', 2.5), ('платеж', 2.3), ('перевод', 2.3), ('депозит', 2.0), ('снятие', 2.0), ('кредит', 1.8), ('дебет', 1.8), ('заем', 1.8), ('процент', 1.5), ('овердрафт', 1.5), ('iban', 1.5), ('swift', 1.5), ('отделение', 1.3), ('банкомат', 1.3), ('расчетный счет', 2.3), ('сберегательный счет', 2.3)]
        },
        'category.legal': {
            'en': [('contract', 3.0), ('agreement', 2.8), ('legal', 2.5), ('terms', 2.5), ('conditions', 2.3), ('clause', 2.0), ('parties', 2.0), ('obligations', 1.8), ('rights', 1.8), ('liability', 1.8), ('indemnity', 1.5), ('breach', 1.5), ('termination', 1.5), ('jurisdiction', 1.3), ('arbitration', 1.3), ('confidentiality', 1.5), ('service agreement', 2.5), ('employment contract', 2.5), ('lease agreement', 2.3)],
            'de': [('vertrag', 3.0), ('vereinbarung', 2.8), ('rechtlich', 2.5), ('bedingungen', 2.5), ('konditionen', 2.3), ('klausel', 2.0), ('parteien', 2.0), ('verpflichtungen', 1.8), ('rechte', 1.8), ('haftung', 1.8), ('entschädigung', 1.5), ('verletzung', 1.5), ('kündigung', 1.5), ('gerichtsbarkeit', 1.3), ('schiedsverfahren', 1.3), ('vertraulichkeit', 1.5), ('dienstleistungsvertrag', 2.5), ('arbeitsvertrag', 2.5)],
            'ru': [('контракт', 3.0), ('соглашение', 2.8), ('юридический', 2.5), ('условия', 2.5), ('положения', 2.3), ('пункт', 2.0), ('стороны', 2.0), ('обязательства', 1.8), ('права', 1.8), ('ответственность', 1.8), ('возмещение', 1.5), ('нарушение', 1.5), ('расторжение', 1.5), ('юрисдикция', 1.3), ('арбитраж', 1.3), ('конфиденциальность', 1.5)]
        },
        'category.real_estate': {
            'en': [('property', 3.0), ('real estate', 3.0), ('mortgage', 2.8), ('deed', 2.5), ('title', 2.5), ('lease', 2.3), ('rent', 2.3), ('tenant', 2.0), ('landlord', 2.0), ('apartment', 1.8), ('house', 1.8), ('building', 1.5), ('address', 1.5), ('ownership', 1.5), ('purchase', 1.3), ('sale', 1.3), ('appraisal', 1.5), ('zoning', 1.3), ('rental agreement', 2.5), ('property tax', 2.0)],
            'de': [('immobilie', 3.0), ('grundstück', 2.8), ('hypothek', 2.8), ('eigentum', 2.5), ('titel', 2.5), ('mietvertrag', 2.3), ('miete', 2.3), ('mieter', 2.0), ('vermieter', 2.0), ('wohnung', 1.8), ('haus', 1.8), ('gebäude', 1.5), ('adresse', 1.5), ('besitz', 1.5), ('kauf', 1.3), ('verkauf', 1.3), ('bewertung', 1.5), ('bebauungsplan', 1.3), ('grundsteuer', 2.0)],
            'ru': [('недвижимость', 3.0), ('собственность', 2.8), ('ипотека', 2.8), ('акт', 2.5), ('право собственности', 2.5), ('аренда', 2.3), ('арендная плата', 2.3), ('арендатор', 2.0), ('арендодатель', 2.0), ('квартира', 1.8), ('дом', 1.8), ('здание', 1.5), ('адрес', 1.5), ('владение', 1.5), ('покупка', 1.3), ('продажа', 1.3), ('оценка', 1.5)]
        }
    }
    
    for cat_key, lang_terms in category_terms.items():
        if cat_key in categories:
            cat_id = categories[cat_key]
            for lang, terms in lang_terms.items():
                for term, weight in terms:
                    conn.execute(text("""
                        INSERT INTO category_term_weights (id, category_id, term, language_code, weight, document_frequency, last_updated)
                        VALUES (:id, :cat_id, :term, :lang, :weight, 1, :updated)
                    """), {
                        'id': str(uuid.uuid4()),
                        'cat_id': cat_id,
                        'term': term.lower(),
                        'lang': lang,
                        'weight': weight,
                        'updated': now
                    })
    
    # ============================================================
    # 5. Important N-gram Patterns (Multi-word phrases)
    # ============================================================
    
    ngram_patterns = [
        # English
        {'pattern': 'account statement', 'type': 'banking', 'lang': 'en', 'score': 2.5},
        {'pattern': 'bank statement', 'type': 'banking', 'lang': 'en', 'score': 2.8},
        {'pattern': 'insurance policy', 'type': 'insurance', 'lang': 'en', 'score': 2.8},
        {'pattern': 'service agreement', 'type': 'legal', 'lang': 'en', 'score': 2.5},
        {'pattern': 'rental agreement', 'type': 'real_estate', 'lang': 'en', 'score': 2.5},
        {'pattern': 'property deed', 'type': 'real_estate', 'lang': 'en', 'score': 2.3},
        {'pattern': 'mortgage agreement', 'type': 'real_estate', 'lang': 'en', 'score': 2.5},
        {'pattern': 'employment contract', 'type': 'legal', 'lang': 'en', 'score': 2.5},
        
        # German
        {'pattern': 'kontoauszug', 'type': 'banking', 'lang': 'de', 'score': 2.8},
        {'pattern': 'versicherungspolice', 'type': 'insurance', 'lang': 'de', 'score': 2.8},
        {'pattern': 'mietvertrag', 'type': 'real_estate', 'lang': 'de', 'score': 2.5},
        {'pattern': 'arbeitsvertrag', 'type': 'legal', 'lang': 'de', 'score': 2.5},
        
        # Russian
        {'pattern': 'банковская выписка', 'type': 'banking', 'lang': 'ru', 'score': 2.8},
        {'pattern': 'страховой полис', 'type': 'insurance', 'lang': 'ru', 'score': 2.8},
        {'pattern': 'договор аренды', 'type': 'real_estate', 'lang': 'ru', 'score': 2.5},
        {'pattern': 'трудовой договор', 'type': 'legal', 'lang': 'ru', 'score': 2.5}
    ]
    
    for pattern in ngram_patterns:
        conn.execute(text("""
            INSERT INTO ngram_patterns (id, pattern, pattern_type, language_code, importance_score, usage_count, is_active, created_at, updated_at)
            VALUES (:id, :pattern, :type, :lang, :score, 0, true, :created, :updated)
        """), {
            'id': str(uuid.uuid4()),
            'pattern': pattern['pattern'],
            'type': pattern['type'],
            'lang': pattern['lang'],
            'score': pattern['score'],
            'created': now,
            'updated': now
        })


def downgrade() -> None:
    conn = op.get_bind()
    
    # Remove added system settings
    conn.execute(text("""
        DELETE FROM system_settings 
        WHERE setting_key IN (
            'allowed_mime_types', 'max_file_size_bytes', 'min_keyword_length',
            'max_keywords_per_document', 'keyword_relevance_threshold',
            'spelling_correction_enabled', 'ngram_extraction_enabled',
            'category_confidence_threshold'
        )
    """))
    
    # Clear ML training tables
    conn.execute(text("DELETE FROM ngram_patterns"))
    conn.execute(text("DELETE FROM category_term_weights"))
    conn.execute(text("DELETE FROM spelling_corrections"))
    conn.execute(text("DELETE FROM stop_words"))