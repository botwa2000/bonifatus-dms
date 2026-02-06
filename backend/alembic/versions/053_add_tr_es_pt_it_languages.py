"""add Turkish, Spanish, Portuguese, Italian language support

Revision ID: 053_add_tr_es_pt_it_languages
Revises: 052_add_tier_provider_settings
Create Date: 2026-02-06 00:00:00.000000

Adds full language support for 4 new languages:
- Turkish (tr), Spanish (es), Portuguese (pt), Italian (it)

Includes:
- supported_languages rows
- system_settings updates (available_languages, language_metadata, ocr_supported_languages, spacy_model_mapping)
- category_translations for all 7 categories
- category_keywords with weights
- stop_words (~100+ per language)
- ngram_patterns
- entity_field_labels
- entity_invalid_patterns
- entity_confidence_thresholds
- entity_type_patterns
"""
from alembic import op
from sqlalchemy import text
from datetime import datetime, timezone
import uuid
import json

# revision identifiers, used by Alembic.
revision = '053_add_tr_es_pt_it_languages'
down_revision = '052_add_tier_provider_settings'
branch_labels = None
depends_on = None

NEW_LANGUAGES = ['tr', 'es', 'pt', 'it']


def upgrade():
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    print("\n=== Adding Turkish, Spanish, Portuguese, Italian Language Support ===\n")

    # ==================== 1. SUPPORTED LANGUAGES ====================
    print("1. Adding supported_languages rows...")

    op.execute("""
        INSERT INTO supported_languages
        (language_code, language_name, hunspell_dict, spacy_model, ml_model_available, stop_words_count, field_labels_count, is_active)
        VALUES
        ('tr', 'Turkish', 'tr_TR', 'xx_ent_wiki_sm', false, 0, 0, true),
        ('es', 'Spanish', 'es_ES', 'es_core_news_md', false, 0, 0, true),
        ('pt', 'Portuguese', 'pt_BR', 'pt_core_news_md', false, 0, 0, true),
        ('it', 'Italian', 'it_IT', 'it_core_news_md', false, 0, 0, true)
        ON CONFLICT (language_code) DO NOTHING;
    """)
    print("   ✓ Added 4 supported languages")

    # ==================== 2. SYSTEM SETTINGS ====================
    print("\n2. Updating system_settings...")

    # 2a. available_languages
    op.execute("""
        UPDATE system_settings
        SET setting_value = '["en","de","ru","fr","tr","es","pt","it"]',
            updated_at = now()
        WHERE setting_key = 'available_languages';
    """)
    print("   ✓ Updated available_languages")

    # 2b. language_metadata
    result = conn.execute(text("""
        SELECT setting_value FROM system_settings WHERE setting_key = 'language_metadata'
    """))
    row = result.fetchone()
    if row:
        metadata = json.loads(row[0])
    else:
        metadata = {}

    metadata['tr'] = {"code": "tr", "name": "Turkish", "native_name": "Türkçe"}
    metadata['es'] = {"code": "es", "name": "Spanish", "native_name": "Español"}
    metadata['pt'] = {"code": "pt", "name": "Portuguese", "native_name": "Português"}
    metadata['it'] = {"code": "it", "name": "Italian", "native_name": "Italiano"}

    conn.execute(text("""
        UPDATE system_settings
        SET setting_value = :value, updated_at = now()
        WHERE setting_key = 'language_metadata'
    """), {"value": json.dumps(metadata)})
    print("   ✓ Updated language_metadata")

    # 2c. ocr_supported_languages
    result = conn.execute(text("""
        SELECT setting_value FROM system_settings WHERE setting_key = 'ocr_supported_languages'
    """))
    row = result.fetchone()
    if row:
        ocr_langs = json.loads(row[0])
    else:
        ocr_langs = {"en": "eng", "de": "deu", "ru": "rus", "fr": "fra"}

    ocr_langs['tr'] = 'tur'
    ocr_langs['es'] = 'spa'
    ocr_langs['pt'] = 'por'
    ocr_langs['it'] = 'ita'

    conn.execute(text("""
        INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, category, is_public)
        VALUES (gen_random_uuid(), 'ocr_supported_languages', :value, 'json', 'OCR language code mapping (ISO 639-1 to Tesseract)', 'ocr', false)
        ON CONFLICT (setting_key) DO UPDATE SET
            setting_value = EXCLUDED.setting_value,
            updated_at = now()
    """), {"value": json.dumps(ocr_langs)})
    print("   ✓ Updated ocr_supported_languages")

    # 2d. spacy_model_mapping
    result = conn.execute(text("""
        SELECT setting_value FROM system_settings WHERE setting_key = 'spacy_model_mapping'
    """))
    row = result.fetchone()
    if row:
        spacy_map = json.loads(row[0])
    else:
        spacy_map = {"en": "en_core_web_md", "de": "de_core_news_md", "fr": "fr_core_news_md", "ru": "ru_core_news_md"}

    spacy_map['tr'] = 'xx_ent_wiki_sm'
    spacy_map['es'] = 'es_core_news_md'
    spacy_map['pt'] = 'pt_core_news_md'
    spacy_map['it'] = 'it_core_news_md'

    conn.execute(text("""
        UPDATE system_settings
        SET setting_value = :value, updated_at = now()
        WHERE setting_key = 'spacy_model_mapping'
    """), {"value": json.dumps(spacy_map)})
    print("   ✓ Updated spacy_model_mapping")

    # ==================== 3. CATEGORY TRANSLATIONS ====================
    print("\n3. Adding category translations...")

    translations = {
        'INS': {
            'tr': {'name': 'Sigorta', 'description': 'Sigorta poliçeleri, tazminat talepleri ve ilgili belgeler'},
            'es': {'name': 'Seguros', 'description': 'Pólizas de seguro, reclamaciones y documentos relacionados'},
            'pt': {'name': 'Seguros', 'description': 'Apólices de seguro, sinistros e documentos relacionados'},
            'it': {'name': 'Assicurazione', 'description': 'Polizze assicurative, sinistri e documenti correlati'},
        },
        'LEG': {
            'tr': {'name': 'Hukuki', 'description': 'Sözleşmeler, anlaşmalar, hukuki belgeler'},
            'es': {'name': 'Jurídico', 'description': 'Contratos, acuerdos, documentos legales'},
            'pt': {'name': 'Jurídico', 'description': 'Contratos, acordos, documentos jurídicos'},
            'it': {'name': 'Legale', 'description': 'Contratti, accordi, documenti legali'},
        },
        'RES': {
            'tr': {'name': 'Gayrimenkul', 'description': 'Tapu, ipotek, kira sözleşmeleri'},
            'es': {'name': 'Inmobiliario', 'description': 'Documentos de propiedad, hipotecas, contratos de alquiler'},
            'pt': {'name': 'Imobiliário', 'description': 'Documentos de propriedade, hipotecas, contratos de arrendamento'},
            'it': {'name': 'Immobiliare', 'description': 'Documenti di proprietà, ipoteche, contratti di locazione'},
        },
        'BNK': {
            'tr': {'name': 'Bankacılık', 'description': 'Hesap özetleri, finansal belgeler ve işlemler'},
            'es': {'name': 'Banca', 'description': 'Extractos bancarios, documentos financieros y transacciones'},
            'pt': {'name': 'Bancário', 'description': 'Extratos bancários, documentos financeiros e transações'},
            'it': {'name': 'Banca', 'description': 'Estratti conto, documenti finanziari e transazioni'},
        },
        'OTH': {
            'tr': {'name': 'Diğer', 'description': 'Çeşitli belgeler ve dosyalar'},
            'es': {'name': 'Otros', 'description': 'Documentos y archivos diversos'},
            'pt': {'name': 'Outros', 'description': 'Documentos e ficheiros diversos'},
            'it': {'name': 'Altro', 'description': 'Documenti e file vari'},
        },
        'INV': {
            'tr': {'name': 'Faturalar', 'description': 'Faturalar, ödeme talepleri'},
            'es': {'name': 'Facturas', 'description': 'Facturas, solicitudes de pago'},
            'pt': {'name': 'Faturas', 'description': 'Faturas, pedidos de pagamento'},
            'it': {'name': 'Fatture', 'description': 'Fatture, richieste di pagamento'},
        },
        'TAX': {
            'tr': {'name': 'Vergiler', 'description': 'Vergi beyannameleri, makbuzlar, vergi belgeleri'},
            'es': {'name': 'Impuestos', 'description': 'Declaraciones fiscales, recibos, documentos fiscales'},
            'pt': {'name': 'Impostos', 'description': 'Declarações fiscais, recibos, documentos fiscais'},
            'it': {'name': 'Tasse', 'description': 'Dichiarazioni fiscali, ricevute, documenti fiscali'},
        },
    }

    translation_count = 0
    for ref_key, lang_translations in translations.items():
        result = conn.execute(text(
            "SELECT id FROM categories WHERE reference_key = :ref_key AND user_id IS NULL"
        ), {'ref_key': ref_key})
        row = result.fetchone()
        if row:
            category_id = str(row[0])
            for lang_code, trans in lang_translations.items():
                conn.execute(text("""
                    INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
                    VALUES (:id, :category_id, :language_code, :name, :description, :now, :now)
                    ON CONFLICT (category_id, language_code) DO NOTHING
                """), {
                    'id': str(uuid.uuid4()),
                    'category_id': category_id,
                    'language_code': lang_code,
                    'name': trans['name'],
                    'description': trans['description'],
                    'now': now
                })
                translation_count += 1
    print(f"   ✓ Added {translation_count} category translations")

    # ==================== 4. CATEGORY KEYWORDS ====================
    print("\n4. Adding category keywords...")

    category_keywords = {
        'INS': {
            'tr': [('sigorta', 3.0), ('poliçe', 2.8), ('teminat', 2.5), ('prim', 2.5), ('hasar', 2.3)],
            'es': [('seguro', 3.0), ('póliza', 2.8), ('cobertura', 2.5), ('prima', 2.5), ('siniestro', 2.3)],
            'pt': [('seguro', 3.0), ('apólice', 2.8), ('cobertura', 2.5), ('prémio', 2.5), ('sinistro', 2.3)],
            'it': [('assicurazione', 3.0), ('polizza', 2.8), ('copertura', 2.5), ('premio', 2.5), ('sinistro', 2.3)],
        },
        'LEG': {
            'tr': [('sözleşme', 3.0), ('anlaşma', 2.8), ('hukuki', 2.5), ('şartlar', 2.5), ('koşullar', 2.3)],
            'es': [('contrato', 3.0), ('acuerdo', 2.8), ('legal', 2.5), ('condiciones', 2.5), ('cláusula', 2.3)],
            'pt': [('contrato', 3.0), ('acordo', 2.8), ('jurídico', 2.5), ('condições', 2.5), ('cláusula', 2.3)],
            'it': [('contratto', 3.0), ('accordo', 2.8), ('legale', 2.5), ('condizioni', 2.5), ('clausola', 2.3)],
        },
        'RES': {
            'tr': [('gayrimenkul', 3.0), ('tapu', 2.8), ('ipotek', 2.8), ('kira', 2.3), ('mülk', 2.5)],
            'es': [('propiedad', 3.0), ('inmueble', 2.8), ('hipoteca', 2.8), ('alquiler', 2.3), ('arrendamiento', 2.5)],
            'pt': [('propriedade', 3.0), ('imóvel', 2.8), ('hipoteca', 2.8), ('aluguel', 2.3), ('arrendamento', 2.5)],
            'it': [('proprietà', 3.0), ('immobile', 2.8), ('ipoteca', 2.8), ('affitto', 2.3), ('locazione', 2.5)],
        },
        'BNK': {
            'tr': [('banka', 3.0), ('hesap', 2.8), ('ekstre', 2.8), ('işlem', 2.5), ('bakiye', 2.5), ('ödeme', 2.3)],
            'es': [('banco', 3.0), ('cuenta', 2.8), ('extracto', 2.8), ('transacción', 2.5), ('saldo', 2.5), ('pago', 2.3)],
            'pt': [('banco', 3.0), ('conta', 2.8), ('extrato', 2.8), ('transação', 2.5), ('saldo', 2.5), ('pagamento', 2.3)],
            'it': [('banca', 3.0), ('conto', 2.8), ('estratto', 2.8), ('transazione', 2.5), ('saldo', 2.5), ('pagamento', 2.3)],
        },
        'OTH': {
            'tr': [('belge', 2.0), ('dosya', 2.0), ('diğer', 1.5)],
            'es': [('documento', 2.0), ('archivo', 2.0), ('varios', 1.5)],
            'pt': [('documento', 2.0), ('ficheiro', 2.0), ('outros', 1.5)],
            'it': [('documento', 2.0), ('file', 2.0), ('altro', 1.5)],
        },
        'INV': {
            'tr': [('fatura', 3.0), ('ödeme', 2.5), ('tutar', 2.3), ('toplam', 2.0), ('vade', 2.0)],
            'es': [('factura', 3.0), ('pago', 2.5), ('importe', 2.3), ('total', 2.0), ('vencimiento', 2.0)],
            'pt': [('fatura', 3.0), ('pagamento', 2.5), ('valor', 2.3), ('total', 2.0), ('vencimento', 2.0)],
            'it': [('fattura', 3.0), ('pagamento', 2.5), ('importo', 2.3), ('totale', 2.0), ('scadenza', 2.0)],
        },
        'TAX': {
            'tr': [('vergi', 3.0), ('beyanname', 2.8), ('makbuz', 2.5), ('matrah', 2.3), ('kesinti', 2.0)],
            'es': [('impuesto', 3.0), ('declaración', 2.8), ('recibo', 2.5), ('fiscal', 2.3), ('deducción', 2.0)],
            'pt': [('imposto', 3.0), ('declaração', 2.8), ('recibo', 2.5), ('fiscal', 2.3), ('dedução', 2.0)],
            'it': [('imposta', 3.0), ('dichiarazione', 2.8), ('ricevuta', 2.5), ('fiscale', 2.3), ('detrazione', 2.0)],
        },
    }

    keyword_count = 0
    for ref_key, lang_keywords in category_keywords.items():
        result = conn.execute(text(
            "SELECT id FROM categories WHERE reference_key = :ref_key AND user_id IS NULL"
        ), {'ref_key': ref_key})
        row = result.fetchone()
        if row:
            category_id = str(row[0])
            for lang_code, keywords in lang_keywords.items():
                for keyword, weight in keywords:
                    conn.execute(text("""
                        INSERT INTO category_keywords (id, category_id, keyword, language_code, weight, match_count, is_system_default, created_at, last_updated)
                        VALUES (:id, :category_id, :keyword, :lang, :weight, 1, true, :now, :now)
                        ON CONFLICT (category_id, lower(keyword), language_code) DO NOTHING
                    """), {
                        'id': str(uuid.uuid4()),
                        'category_id': category_id,
                        'keyword': keyword.lower(),
                        'lang': lang_code,
                        'weight': weight,
                        'now': now
                    })
                    keyword_count += 1
    print(f"   ✓ Added {keyword_count} category keywords")

    # ==================== 5. STOP WORDS ====================
    print("\n5. Adding stop words...")

    op.execute("""
        INSERT INTO stop_words (id, word, language_code, is_active, created_at)
        VALUES

        -- ========== TURKISH (tr) ==========

        -- Core articles/prepositions/conjunctions
        (gen_random_uuid(), 'bir', 'tr', true, NOW()),
        (gen_random_uuid(), 'bu', 'tr', true, NOW()),
        (gen_random_uuid(), 'şu', 'tr', true, NOW()),
        (gen_random_uuid(), 'ile', 'tr', true, NOW()),
        (gen_random_uuid(), 'için', 'tr', true, NOW()),
        (gen_random_uuid(), 'gibi', 'tr', true, NOW()),
        (gen_random_uuid(), 'kadar', 'tr', true, NOW()),
        (gen_random_uuid(), 'daha', 'tr', true, NOW()),
        (gen_random_uuid(), 'çok', 'tr', true, NOW()),
        (gen_random_uuid(), 'ama', 'tr', true, NOW()),
        (gen_random_uuid(), 'fakat', 'tr', true, NOW()),
        (gen_random_uuid(), 'veya', 'tr', true, NOW()),
        (gen_random_uuid(), 'ancak', 'tr', true, NOW()),
        (gen_random_uuid(), 'hem', 'tr', true, NOW()),
        (gen_random_uuid(), 'her', 'tr', true, NOW()),
        (gen_random_uuid(), 'hiç', 'tr', true, NOW()),
        (gen_random_uuid(), 'var', 'tr', true, NOW()),
        (gen_random_uuid(), 'yok', 'tr', true, NOW()),
        (gen_random_uuid(), 'olan', 'tr', true, NOW()),
        (gen_random_uuid(), 'olarak', 'tr', true, NOW()),
        (gen_random_uuid(), 'değil', 'tr', true, NOW()),

        -- Form instructions
        (gen_random_uuid(), 'lütfen', 'tr', true, NOW()),
        (gen_random_uuid(), 'doldurunuz', 'tr', true, NOW()),
        (gen_random_uuid(), 'doldurun', 'tr', true, NOW()),
        (gen_random_uuid(), 'işaretleyiniz', 'tr', true, NOW()),
        (gen_random_uuid(), 'belirtiniz', 'tr', true, NOW()),
        (gen_random_uuid(), 'yazınız', 'tr', true, NOW()),
        (gen_random_uuid(), 'giriniz', 'tr', true, NOW()),
        (gen_random_uuid(), 'seçiniz', 'tr', true, NOW()),
        (gen_random_uuid(), 'bakınız', 'tr', true, NOW()),

        -- Form field labels
        (gen_random_uuid(), 'adı', 'tr', true, NOW()),
        (gen_random_uuid(), 'soyadı', 'tr', true, NOW()),
        (gen_random_uuid(), 'adres', 'tr', true, NOW()),
        (gen_random_uuid(), 'telefon', 'tr', true, NOW()),
        (gen_random_uuid(), 'tarih', 'tr', true, NOW()),
        (gen_random_uuid(), 'imza', 'tr', true, NOW()),
        (gen_random_uuid(), 'numara', 'tr', true, NOW()),
        (gen_random_uuid(), 'şehir', 'tr', true, NOW()),
        (gen_random_uuid(), 'ilçe', 'tr', true, NOW()),
        (gen_random_uuid(), 'posta', 'tr', true, NOW()),
        (gen_random_uuid(), 'doğum', 'tr', true, NOW()),
        (gen_random_uuid(), 'meslek', 'tr', true, NOW()),

        -- Generic descriptors
        (gen_random_uuid(), 'önemli', 'tr', true, NOW()),
        (gen_random_uuid(), 'gerekli', 'tr', true, NOW()),
        (gen_random_uuid(), 'zorunlu', 'tr', true, NOW()),
        (gen_random_uuid(), 'ek', 'tr', true, NOW()),
        (gen_random_uuid(), 'diğer', 'tr', true, NOW()),
        (gen_random_uuid(), 'çeşitli', 'tr', true, NOW()),
        (gen_random_uuid(), 'bilgi', 'tr', true, NOW()),
        (gen_random_uuid(), 'bilgiler', 'tr', true, NOW()),

        -- Common low-semantic verbs
        (gen_random_uuid(), 'olmak', 'tr', true, NOW()),
        (gen_random_uuid(), 'etmek', 'tr', true, NOW()),
        (gen_random_uuid(), 'yapmak', 'tr', true, NOW()),
        (gen_random_uuid(), 'vermek', 'tr', true, NOW()),
        (gen_random_uuid(), 'almak', 'tr', true, NOW()),
        (gen_random_uuid(), 'gelmek', 'tr', true, NOW()),
        (gen_random_uuid(), 'bulunmak', 'tr', true, NOW()),

        -- Measurement/time words
        (gen_random_uuid(), 'gün', 'tr', true, NOW()),
        (gen_random_uuid(), 'ay', 'tr', true, NOW()),
        (gen_random_uuid(), 'yıl', 'tr', true, NOW()),
        (gen_random_uuid(), 'saat', 'tr', true, NOW()),
        (gen_random_uuid(), 'adet', 'tr', true, NOW()),

        -- Document-specific generic terms
        (gen_random_uuid(), 'sayfa', 'tr', true, NOW()),
        (gen_random_uuid(), 'madde', 'tr', true, NOW()),
        (gen_random_uuid(), 'bent', 'tr', true, NOW()),
        (gen_random_uuid(), 'fıkra', 'tr', true, NOW()),
        (gen_random_uuid(), 'ekte', 'tr', true, NOW()),
        (gen_random_uuid(), 'ilişik', 'tr', true, NOW()),

        -- Pronouns/demonstratives
        (gen_random_uuid(), 'ben', 'tr', true, NOW()),
        (gen_random_uuid(), 'sen', 'tr', true, NOW()),
        (gen_random_uuid(), 'biz', 'tr', true, NOW()),
        (gen_random_uuid(), 'siz', 'tr', true, NOW()),
        (gen_random_uuid(), 'onlar', 'tr', true, NOW()),
        (gen_random_uuid(), 'hangi', 'tr', true, NOW()),
        (gen_random_uuid(), 'nasıl', 'tr', true, NOW()),
        (gen_random_uuid(), 'neden', 'tr', true, NOW()),
        (gen_random_uuid(), 'nerede', 'tr', true, NOW()),
        (gen_random_uuid(), 'aynı', 'tr', true, NOW()),
        (gen_random_uuid(), 'bazı', 'tr', true, NOW()),
        (gen_random_uuid(), 'bütün', 'tr', true, NOW()),
        (gen_random_uuid(), 'tüm', 'tr', true, NOW()),
        (gen_random_uuid(), 'hep', 'tr', true, NOW()),
        (gen_random_uuid(), 'kendi', 'tr', true, NOW()),
        (gen_random_uuid(), 'sonra', 'tr', true, NOW()),
        (gen_random_uuid(), 'önce', 'tr', true, NOW()),
        (gen_random_uuid(), 'üzerinde', 'tr', true, NOW()),
        (gen_random_uuid(), 'altında', 'tr', true, NOW()),
        (gen_random_uuid(), 'arasında', 'tr', true, NOW()),
        (gen_random_uuid(), 'karşı', 'tr', true, NOW()),
        (gen_random_uuid(), 'göre', 'tr', true, NOW()),
        (gen_random_uuid(), 'ilgili', 'tr', true, NOW()),
        (gen_random_uuid(), 'sadece', 'tr', true, NOW()),
        (gen_random_uuid(), 'bile', 'tr', true, NOW()),
        (gen_random_uuid(), 'zaten', 'tr', true, NOW()),
        (gen_random_uuid(), 'ise', 'tr', true, NOW()),
        (gen_random_uuid(), 'iken', 'tr', true, NOW()),
        (gen_random_uuid(), 'dolayı', 'tr', true, NOW()),
        (gen_random_uuid(), 'itibaren', 'tr', true, NOW()),
        (gen_random_uuid(), 'tarafından', 'tr', true, NOW()),

        -- ========== SPANISH (es) ==========

        -- Core articles/prepositions/conjunctions
        (gen_random_uuid(), 'el', 'es', true, NOW()),
        (gen_random_uuid(), 'la', 'es', true, NOW()),
        (gen_random_uuid(), 'los', 'es', true, NOW()),
        (gen_random_uuid(), 'las', 'es', true, NOW()),
        (gen_random_uuid(), 'un', 'es', true, NOW()),
        (gen_random_uuid(), 'una', 'es', true, NOW()),
        (gen_random_uuid(), 'unos', 'es', true, NOW()),
        (gen_random_uuid(), 'unas', 'es', true, NOW()),
        (gen_random_uuid(), 'del', 'es', true, NOW()),
        (gen_random_uuid(), 'al', 'es', true, NOW()),
        (gen_random_uuid(), 'en', 'es', true, NOW()),
        (gen_random_uuid(), 'de', 'es', true, NOW()),
        (gen_random_uuid(), 'con', 'es', true, NOW()),
        (gen_random_uuid(), 'por', 'es', true, NOW()),
        (gen_random_uuid(), 'para', 'es', true, NOW()),
        (gen_random_uuid(), 'sin', 'es', true, NOW()),
        (gen_random_uuid(), 'sobre', 'es', true, NOW()),
        (gen_random_uuid(), 'entre', 'es', true, NOW()),
        (gen_random_uuid(), 'hasta', 'es', true, NOW()),
        (gen_random_uuid(), 'desde', 'es', true, NOW()),
        (gen_random_uuid(), 'que', 'es', true, NOW()),
        (gen_random_uuid(), 'como', 'es', true, NOW()),
        (gen_random_uuid(), 'pero', 'es', true, NOW()),
        (gen_random_uuid(), 'más', 'es', true, NOW()),
        (gen_random_uuid(), 'muy', 'es', true, NOW()),
        (gen_random_uuid(), 'también', 'es', true, NOW()),
        (gen_random_uuid(), 'cada', 'es', true, NOW()),
        (gen_random_uuid(), 'otro', 'es', true, NOW()),
        (gen_random_uuid(), 'otra', 'es', true, NOW()),
        (gen_random_uuid(), 'otros', 'es', true, NOW()),
        (gen_random_uuid(), 'otras', 'es', true, NOW()),
        (gen_random_uuid(), 'este', 'es', true, NOW()),
        (gen_random_uuid(), 'esta', 'es', true, NOW()),
        (gen_random_uuid(), 'estos', 'es', true, NOW()),
        (gen_random_uuid(), 'estas', 'es', true, NOW()),
        (gen_random_uuid(), 'ese', 'es', true, NOW()),
        (gen_random_uuid(), 'esa', 'es', true, NOW()),
        (gen_random_uuid(), 'no', 'es', true, NOW()),
        (gen_random_uuid(), 'sí', 'es', true, NOW()),

        -- Form instructions
        (gen_random_uuid(), 'favor', 'es', true, NOW()),
        (gen_random_uuid(), 'rellenar', 'es', true, NOW()),
        (gen_random_uuid(), 'completar', 'es', true, NOW()),
        (gen_random_uuid(), 'marcar', 'es', true, NOW()),
        (gen_random_uuid(), 'indicar', 'es', true, NOW()),
        (gen_random_uuid(), 'escribir', 'es', true, NOW()),
        (gen_random_uuid(), 'seleccionar', 'es', true, NOW()),
        (gen_random_uuid(), 'véase', 'es', true, NOW()),

        -- Form field labels
        (gen_random_uuid(), 'nombre', 'es', true, NOW()),
        (gen_random_uuid(), 'apellido', 'es', true, NOW()),
        (gen_random_uuid(), 'apellidos', 'es', true, NOW()),
        (gen_random_uuid(), 'dirección', 'es', true, NOW()),
        (gen_random_uuid(), 'teléfono', 'es', true, NOW()),
        (gen_random_uuid(), 'fecha', 'es', true, NOW()),
        (gen_random_uuid(), 'firma', 'es', true, NOW()),
        (gen_random_uuid(), 'número', 'es', true, NOW()),
        (gen_random_uuid(), 'ciudad', 'es', true, NOW()),
        (gen_random_uuid(), 'código', 'es', true, NOW()),
        (gen_random_uuid(), 'postal', 'es', true, NOW()),
        (gen_random_uuid(), 'nacimiento', 'es', true, NOW()),
        (gen_random_uuid(), 'profesión', 'es', true, NOW()),

        -- Generic descriptors
        (gen_random_uuid(), 'importante', 'es', true, NOW()),
        (gen_random_uuid(), 'necesario', 'es', true, NOW()),
        (gen_random_uuid(), 'obligatorio', 'es', true, NOW()),
        (gen_random_uuid(), 'adicional', 'es', true, NOW()),
        (gen_random_uuid(), 'información', 'es', true, NOW()),
        (gen_random_uuid(), 'datos', 'es', true, NOW()),

        -- Common low-semantic verbs
        (gen_random_uuid(), 'ser', 'es', true, NOW()),
        (gen_random_uuid(), 'estar', 'es', true, NOW()),
        (gen_random_uuid(), 'haber', 'es', true, NOW()),
        (gen_random_uuid(), 'tener', 'es', true, NOW()),
        (gen_random_uuid(), 'hacer', 'es', true, NOW()),
        (gen_random_uuid(), 'poder', 'es', true, NOW()),
        (gen_random_uuid(), 'deber', 'es', true, NOW()),

        -- Measurement/time words
        (gen_random_uuid(), 'día', 'es', true, NOW()),
        (gen_random_uuid(), 'mes', 'es', true, NOW()),
        (gen_random_uuid(), 'año', 'es', true, NOW()),
        (gen_random_uuid(), 'hora', 'es', true, NOW()),

        -- Document-specific generic terms
        (gen_random_uuid(), 'página', 'es', true, NOW()),
        (gen_random_uuid(), 'artículo', 'es', true, NOW()),
        (gen_random_uuid(), 'apartado', 'es', true, NOW()),
        (gen_random_uuid(), 'anexo', 'es', true, NOW()),
        (gen_random_uuid(), 'adjunto', 'es', true, NOW()),

        -- Pronouns/demonstratives
        (gen_random_uuid(), 'yo', 'es', true, NOW()),
        (gen_random_uuid(), 'usted', 'es', true, NOW()),
        (gen_random_uuid(), 'nosotros', 'es', true, NOW()),
        (gen_random_uuid(), 'ellos', 'es', true, NOW()),
        (gen_random_uuid(), 'ellas', 'es', true, NOW()),
        (gen_random_uuid(), 'cuál', 'es', true, NOW()),
        (gen_random_uuid(), 'cuándo', 'es', true, NOW()),
        (gen_random_uuid(), 'dónde', 'es', true, NOW()),
        (gen_random_uuid(), 'cómo', 'es', true, NOW()),
        (gen_random_uuid(), 'qué', 'es', true, NOW()),
        (gen_random_uuid(), 'quién', 'es', true, NOW()),
        (gen_random_uuid(), 'todo', 'es', true, NOW()),
        (gen_random_uuid(), 'toda', 'es', true, NOW()),
        (gen_random_uuid(), 'todos', 'es', true, NOW()),
        (gen_random_uuid(), 'todas', 'es', true, NOW()),
        (gen_random_uuid(), 'mismo', 'es', true, NOW()),
        (gen_random_uuid(), 'misma', 'es', true, NOW()),
        (gen_random_uuid(), 'según', 'es', true, NOW()),
        (gen_random_uuid(), 'durante', 'es', true, NOW()),
        (gen_random_uuid(), 'antes', 'es', true, NOW()),
        (gen_random_uuid(), 'después', 'es', true, NOW()),
        (gen_random_uuid(), 'solo', 'es', true, NOW()),
        (gen_random_uuid(), 'ya', 'es', true, NOW()),
        (gen_random_uuid(), 'aquí', 'es', true, NOW()),
        (gen_random_uuid(), 'allí', 'es', true, NOW()),
        (gen_random_uuid(), 'siempre', 'es', true, NOW()),
        (gen_random_uuid(), 'nunca', 'es', true, NOW()),

        -- ========== PORTUGUESE (pt) ==========

        -- Core articles/prepositions/conjunctions
        (gen_random_uuid(), 'o', 'pt', true, NOW()),
        (gen_random_uuid(), 'a', 'pt', true, NOW()),
        (gen_random_uuid(), 'os', 'pt', true, NOW()),
        (gen_random_uuid(), 'as', 'pt', true, NOW()),
        (gen_random_uuid(), 'um', 'pt', true, NOW()),
        (gen_random_uuid(), 'uma', 'pt', true, NOW()),
        (gen_random_uuid(), 'uns', 'pt', true, NOW()),
        (gen_random_uuid(), 'umas', 'pt', true, NOW()),
        (gen_random_uuid(), 'do', 'pt', true, NOW()),
        (gen_random_uuid(), 'da', 'pt', true, NOW()),
        (gen_random_uuid(), 'dos', 'pt', true, NOW()),
        (gen_random_uuid(), 'das', 'pt', true, NOW()),
        (gen_random_uuid(), 'no', 'pt', true, NOW()),
        (gen_random_uuid(), 'na', 'pt', true, NOW()),
        (gen_random_uuid(), 'nos', 'pt', true, NOW()),
        (gen_random_uuid(), 'nas', 'pt', true, NOW()),
        (gen_random_uuid(), 'ao', 'pt', true, NOW()),
        (gen_random_uuid(), 'em', 'pt', true, NOW()),
        (gen_random_uuid(), 'de', 'pt', true, NOW()),
        (gen_random_uuid(), 'com', 'pt', true, NOW()),
        (gen_random_uuid(), 'por', 'pt', true, NOW()),
        (gen_random_uuid(), 'para', 'pt', true, NOW()),
        (gen_random_uuid(), 'sem', 'pt', true, NOW()),
        (gen_random_uuid(), 'sobre', 'pt', true, NOW()),
        (gen_random_uuid(), 'entre', 'pt', true, NOW()),
        (gen_random_uuid(), 'até', 'pt', true, NOW()),
        (gen_random_uuid(), 'desde', 'pt', true, NOW()),
        (gen_random_uuid(), 'que', 'pt', true, NOW()),
        (gen_random_uuid(), 'como', 'pt', true, NOW()),
        (gen_random_uuid(), 'mas', 'pt', true, NOW()),
        (gen_random_uuid(), 'mais', 'pt', true, NOW()),
        (gen_random_uuid(), 'muito', 'pt', true, NOW()),
        (gen_random_uuid(), 'também', 'pt', true, NOW()),
        (gen_random_uuid(), 'cada', 'pt', true, NOW()),
        (gen_random_uuid(), 'outro', 'pt', true, NOW()),
        (gen_random_uuid(), 'outra', 'pt', true, NOW()),
        (gen_random_uuid(), 'este', 'pt', true, NOW()),
        (gen_random_uuid(), 'esta', 'pt', true, NOW()),
        (gen_random_uuid(), 'esse', 'pt', true, NOW()),
        (gen_random_uuid(), 'essa', 'pt', true, NOW()),
        (gen_random_uuid(), 'não', 'pt', true, NOW()),
        (gen_random_uuid(), 'sim', 'pt', true, NOW()),

        -- Form instructions
        (gen_random_uuid(), 'favor', 'pt', true, NOW()),
        (gen_random_uuid(), 'preencher', 'pt', true, NOW()),
        (gen_random_uuid(), 'completar', 'pt', true, NOW()),
        (gen_random_uuid(), 'assinalar', 'pt', true, NOW()),
        (gen_random_uuid(), 'indicar', 'pt', true, NOW()),
        (gen_random_uuid(), 'escrever', 'pt', true, NOW()),
        (gen_random_uuid(), 'selecionar', 'pt', true, NOW()),
        (gen_random_uuid(), 'consultar', 'pt', true, NOW()),

        -- Form field labels
        (gen_random_uuid(), 'nome', 'pt', true, NOW()),
        (gen_random_uuid(), 'apelido', 'pt', true, NOW()),
        (gen_random_uuid(), 'morada', 'pt', true, NOW()),
        (gen_random_uuid(), 'telefone', 'pt', true, NOW()),
        (gen_random_uuid(), 'data', 'pt', true, NOW()),
        (gen_random_uuid(), 'assinatura', 'pt', true, NOW()),
        (gen_random_uuid(), 'número', 'pt', true, NOW()),
        (gen_random_uuid(), 'cidade', 'pt', true, NOW()),
        (gen_random_uuid(), 'código', 'pt', true, NOW()),
        (gen_random_uuid(), 'postal', 'pt', true, NOW()),
        (gen_random_uuid(), 'nascimento', 'pt', true, NOW()),
        (gen_random_uuid(), 'profissão', 'pt', true, NOW()),

        -- Generic descriptors
        (gen_random_uuid(), 'importante', 'pt', true, NOW()),
        (gen_random_uuid(), 'necessário', 'pt', true, NOW()),
        (gen_random_uuid(), 'obrigatório', 'pt', true, NOW()),
        (gen_random_uuid(), 'adicional', 'pt', true, NOW()),
        (gen_random_uuid(), 'informação', 'pt', true, NOW()),
        (gen_random_uuid(), 'dados', 'pt', true, NOW()),

        -- Common low-semantic verbs
        (gen_random_uuid(), 'ser', 'pt', true, NOW()),
        (gen_random_uuid(), 'estar', 'pt', true, NOW()),
        (gen_random_uuid(), 'haver', 'pt', true, NOW()),
        (gen_random_uuid(), 'ter', 'pt', true, NOW()),
        (gen_random_uuid(), 'fazer', 'pt', true, NOW()),
        (gen_random_uuid(), 'poder', 'pt', true, NOW()),
        (gen_random_uuid(), 'dever', 'pt', true, NOW()),

        -- Measurement/time words
        (gen_random_uuid(), 'dia', 'pt', true, NOW()),
        (gen_random_uuid(), 'mês', 'pt', true, NOW()),
        (gen_random_uuid(), 'ano', 'pt', true, NOW()),
        (gen_random_uuid(), 'hora', 'pt', true, NOW()),

        -- Document-specific generic terms
        (gen_random_uuid(), 'página', 'pt', true, NOW()),
        (gen_random_uuid(), 'artigo', 'pt', true, NOW()),
        (gen_random_uuid(), 'parágrafo', 'pt', true, NOW()),
        (gen_random_uuid(), 'anexo', 'pt', true, NOW()),

        -- Pronouns/demonstratives
        (gen_random_uuid(), 'eu', 'pt', true, NOW()),
        (gen_random_uuid(), 'você', 'pt', true, NOW()),
        (gen_random_uuid(), 'nós', 'pt', true, NOW()),
        (gen_random_uuid(), 'eles', 'pt', true, NOW()),
        (gen_random_uuid(), 'elas', 'pt', true, NOW()),
        (gen_random_uuid(), 'qual', 'pt', true, NOW()),
        (gen_random_uuid(), 'quando', 'pt', true, NOW()),
        (gen_random_uuid(), 'onde', 'pt', true, NOW()),
        (gen_random_uuid(), 'quem', 'pt', true, NOW()),
        (gen_random_uuid(), 'todo', 'pt', true, NOW()),
        (gen_random_uuid(), 'toda', 'pt', true, NOW()),
        (gen_random_uuid(), 'todos', 'pt', true, NOW()),
        (gen_random_uuid(), 'todas', 'pt', true, NOW()),
        (gen_random_uuid(), 'mesmo', 'pt', true, NOW()),
        (gen_random_uuid(), 'mesma', 'pt', true, NOW()),
        (gen_random_uuid(), 'segundo', 'pt', true, NOW()),
        (gen_random_uuid(), 'durante', 'pt', true, NOW()),
        (gen_random_uuid(), 'antes', 'pt', true, NOW()),
        (gen_random_uuid(), 'depois', 'pt', true, NOW()),
        (gen_random_uuid(), 'apenas', 'pt', true, NOW()),
        (gen_random_uuid(), 'já', 'pt', true, NOW()),
        (gen_random_uuid(), 'aqui', 'pt', true, NOW()),
        (gen_random_uuid(), 'ali', 'pt', true, NOW()),
        (gen_random_uuid(), 'sempre', 'pt', true, NOW()),
        (gen_random_uuid(), 'nunca', 'pt', true, NOW()),

        -- ========== ITALIAN (it) ==========

        -- Core articles/prepositions/conjunctions
        (gen_random_uuid(), 'il', 'it', true, NOW()),
        (gen_random_uuid(), 'lo', 'it', true, NOW()),
        (gen_random_uuid(), 'la', 'it', true, NOW()),
        (gen_random_uuid(), 'le', 'it', true, NOW()),
        (gen_random_uuid(), 'gli', 'it', true, NOW()),
        (gen_random_uuid(), 'un', 'it', true, NOW()),
        (gen_random_uuid(), 'uno', 'it', true, NOW()),
        (gen_random_uuid(), 'una', 'it', true, NOW()),
        (gen_random_uuid(), 'del', 'it', true, NOW()),
        (gen_random_uuid(), 'della', 'it', true, NOW()),
        (gen_random_uuid(), 'dei', 'it', true, NOW()),
        (gen_random_uuid(), 'delle', 'it', true, NOW()),
        (gen_random_uuid(), 'nel', 'it', true, NOW()),
        (gen_random_uuid(), 'nella', 'it', true, NOW()),
        (gen_random_uuid(), 'nei', 'it', true, NOW()),
        (gen_random_uuid(), 'nelle', 'it', true, NOW()),
        (gen_random_uuid(), 'al', 'it', true, NOW()),
        (gen_random_uuid(), 'alla', 'it', true, NOW()),
        (gen_random_uuid(), 'in', 'it', true, NOW()),
        (gen_random_uuid(), 'di', 'it', true, NOW()),
        (gen_random_uuid(), 'da', 'it', true, NOW()),
        (gen_random_uuid(), 'con', 'it', true, NOW()),
        (gen_random_uuid(), 'per', 'it', true, NOW()),
        (gen_random_uuid(), 'tra', 'it', true, NOW()),
        (gen_random_uuid(), 'fra', 'it', true, NOW()),
        (gen_random_uuid(), 'su', 'it', true, NOW()),
        (gen_random_uuid(), 'senza', 'it', true, NOW()),
        (gen_random_uuid(), 'sopra', 'it', true, NOW()),
        (gen_random_uuid(), 'sotto', 'it', true, NOW()),
        (gen_random_uuid(), 'fino', 'it', true, NOW()),
        (gen_random_uuid(), 'che', 'it', true, NOW()),
        (gen_random_uuid(), 'come', 'it', true, NOW()),
        (gen_random_uuid(), 'ma', 'it', true, NOW()),
        (gen_random_uuid(), 'più', 'it', true, NOW()),
        (gen_random_uuid(), 'molto', 'it', true, NOW()),
        (gen_random_uuid(), 'anche', 'it', true, NOW()),
        (gen_random_uuid(), 'ogni', 'it', true, NOW()),
        (gen_random_uuid(), 'altro', 'it', true, NOW()),
        (gen_random_uuid(), 'altra', 'it', true, NOW()),
        (gen_random_uuid(), 'altri', 'it', true, NOW()),
        (gen_random_uuid(), 'altre', 'it', true, NOW()),
        (gen_random_uuid(), 'questo', 'it', true, NOW()),
        (gen_random_uuid(), 'questa', 'it', true, NOW()),
        (gen_random_uuid(), 'quello', 'it', true, NOW()),
        (gen_random_uuid(), 'quella', 'it', true, NOW()),
        (gen_random_uuid(), 'non', 'it', true, NOW()),

        -- Form instructions
        (gen_random_uuid(), 'compilare', 'it', true, NOW()),
        (gen_random_uuid(), 'completare', 'it', true, NOW()),
        (gen_random_uuid(), 'barrare', 'it', true, NOW()),
        (gen_random_uuid(), 'indicare', 'it', true, NOW()),
        (gen_random_uuid(), 'scrivere', 'it', true, NOW()),
        (gen_random_uuid(), 'selezionare', 'it', true, NOW()),
        (gen_random_uuid(), 'consultare', 'it', true, NOW()),
        (gen_random_uuid(), 'pregasi', 'it', true, NOW()),

        -- Form field labels
        (gen_random_uuid(), 'nome', 'it', true, NOW()),
        (gen_random_uuid(), 'cognome', 'it', true, NOW()),
        (gen_random_uuid(), 'indirizzo', 'it', true, NOW()),
        (gen_random_uuid(), 'telefono', 'it', true, NOW()),
        (gen_random_uuid(), 'data', 'it', true, NOW()),
        (gen_random_uuid(), 'firma', 'it', true, NOW()),
        (gen_random_uuid(), 'numero', 'it', true, NOW()),
        (gen_random_uuid(), 'città', 'it', true, NOW()),
        (gen_random_uuid(), 'codice', 'it', true, NOW()),
        (gen_random_uuid(), 'postale', 'it', true, NOW()),
        (gen_random_uuid(), 'nascita', 'it', true, NOW()),
        (gen_random_uuid(), 'professione', 'it', true, NOW()),

        -- Generic descriptors
        (gen_random_uuid(), 'importante', 'it', true, NOW()),
        (gen_random_uuid(), 'necessario', 'it', true, NOW()),
        (gen_random_uuid(), 'obbligatorio', 'it', true, NOW()),
        (gen_random_uuid(), 'ulteriore', 'it', true, NOW()),
        (gen_random_uuid(), 'informazioni', 'it', true, NOW()),
        (gen_random_uuid(), 'dati', 'it', true, NOW()),

        -- Common low-semantic verbs
        (gen_random_uuid(), 'essere', 'it', true, NOW()),
        (gen_random_uuid(), 'avere', 'it', true, NOW()),
        (gen_random_uuid(), 'fare', 'it', true, NOW()),
        (gen_random_uuid(), 'potere', 'it', true, NOW()),
        (gen_random_uuid(), 'dovere', 'it', true, NOW()),
        (gen_random_uuid(), 'volere', 'it', true, NOW()),
        (gen_random_uuid(), 'stare', 'it', true, NOW()),

        -- Measurement/time words
        (gen_random_uuid(), 'giorno', 'it', true, NOW()),
        (gen_random_uuid(), 'mese', 'it', true, NOW()),
        (gen_random_uuid(), 'anno', 'it', true, NOW()),
        (gen_random_uuid(), 'ora', 'it', true, NOW()),

        -- Document-specific generic terms
        (gen_random_uuid(), 'pagina', 'it', true, NOW()),
        (gen_random_uuid(), 'articolo', 'it', true, NOW()),
        (gen_random_uuid(), 'comma', 'it', true, NOW()),
        (gen_random_uuid(), 'allegato', 'it', true, NOW()),

        -- Pronouns/demonstratives
        (gen_random_uuid(), 'io', 'it', true, NOW()),
        (gen_random_uuid(), 'tu', 'it', true, NOW()),
        (gen_random_uuid(), 'lui', 'it', true, NOW()),
        (gen_random_uuid(), 'lei', 'it', true, NOW()),
        (gen_random_uuid(), 'noi', 'it', true, NOW()),
        (gen_random_uuid(), 'voi', 'it', true, NOW()),
        (gen_random_uuid(), 'loro', 'it', true, NOW()),
        (gen_random_uuid(), 'quale', 'it', true, NOW()),
        (gen_random_uuid(), 'quando', 'it', true, NOW()),
        (gen_random_uuid(), 'dove', 'it', true, NOW()),
        (gen_random_uuid(), 'chi', 'it', true, NOW()),
        (gen_random_uuid(), 'tutto', 'it', true, NOW()),
        (gen_random_uuid(), 'tutta', 'it', true, NOW()),
        (gen_random_uuid(), 'tutti', 'it', true, NOW()),
        (gen_random_uuid(), 'tutte', 'it', true, NOW()),
        (gen_random_uuid(), 'stesso', 'it', true, NOW()),
        (gen_random_uuid(), 'stessa', 'it', true, NOW()),
        (gen_random_uuid(), 'secondo', 'it', true, NOW()),
        (gen_random_uuid(), 'durante', 'it', true, NOW()),
        (gen_random_uuid(), 'prima', 'it', true, NOW()),
        (gen_random_uuid(), 'dopo', 'it', true, NOW()),
        (gen_random_uuid(), 'solo', 'it', true, NOW()),
        (gen_random_uuid(), 'già', 'it', true, NOW()),
        (gen_random_uuid(), 'qui', 'it', true, NOW()),
        (gen_random_uuid(), 'sempre', 'it', true, NOW()),
        (gen_random_uuid(), 'mai', 'it', true, NOW())

        ON CONFLICT (word, language_code) DO NOTHING;
    """)
    print("   ✓ Added stop words for tr, es, pt, it")

    # ==================== 6. NGRAM PATTERNS ====================
    print("\n6. Adding n-gram patterns...")

    ngram_patterns = [
        # Turkish
        {'pattern': 'banka ekstresi', 'type': 'banking', 'lang': 'tr', 'score': 2.8},
        {'pattern': 'sigorta poliçesi', 'type': 'insurance', 'lang': 'tr', 'score': 2.8},
        {'pattern': 'kira sözleşmesi', 'type': 'real_estate', 'lang': 'tr', 'score': 2.5},
        # Spanish
        {'pattern': 'extracto bancario', 'type': 'banking', 'lang': 'es', 'score': 2.8},
        {'pattern': 'póliza de seguro', 'type': 'insurance', 'lang': 'es', 'score': 2.8},
        {'pattern': 'contrato de alquiler', 'type': 'real_estate', 'lang': 'es', 'score': 2.5},
        # Portuguese
        {'pattern': 'extrato bancário', 'type': 'banking', 'lang': 'pt', 'score': 2.8},
        {'pattern': 'apólice de seguro', 'type': 'insurance', 'lang': 'pt', 'score': 2.8},
        {'pattern': 'contrato de arrendamento', 'type': 'real_estate', 'lang': 'pt', 'score': 2.5},
        # Italian
        {'pattern': 'estratto conto', 'type': 'banking', 'lang': 'it', 'score': 2.8},
        {'pattern': 'polizza assicurativa', 'type': 'insurance', 'lang': 'it', 'score': 2.8},
        {'pattern': 'contratto di locazione', 'type': 'real_estate', 'lang': 'it', 'score': 2.5},
    ]

    for pattern in ngram_patterns:
        conn.execute(text("""
            INSERT INTO ngram_patterns (id, pattern, pattern_type, language_code, importance_score, usage_count, is_active, created_at, updated_at)
            VALUES (:id, :pattern, :type, :lang, :score, 0, true, :now, :now)
            ON CONFLICT DO NOTHING
        """), {
            'id': str(uuid.uuid4()),
            'pattern': pattern['pattern'],
            'type': pattern['type'],
            'lang': pattern['lang'],
            'score': pattern['score'],
            'now': now
        })
    print(f"   ✓ Added {len(ngram_patterns)} n-gram patterns")

    # ==================== 7. ENTITY FIELD LABELS ====================
    print("\n7. Adding entity field labels...")

    # Turkish field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        ('tr', 'IBAN', 'Banking field label'),
        ('tr', 'BIC', 'Banking field label'),
        ('tr', 'SWIFT', 'Banking field label'),
        ('tr', 'VKN', 'Tax identification number (Vergi Kimlik No)'),
        ('tr', 'TCKN', 'Turkish ID number (TC Kimlik No)'),
        ('tr', 'A.Ş.', 'Company type abbreviation (Anonim Şirketi)'),
        ('tr', 'Ltd.Şti.', 'Company type abbreviation (Limited Şirketi)'),
        ('tr', 'Tarih', 'Date field label'),
        ('tr', 'Tutar', 'Amount field label'),
        ('tr', 'Fatura', 'Invoice field label'),
        ('tr', 'Tel', 'Telephone abbreviation'),
        ('tr', 'Faks', 'Fax abbreviation'),
        ('tr', 'www', 'Web prefix'),
        ('tr', 'http', 'Protocol prefix'),
        ('tr', 'https', 'Protocol prefix')
        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # Spanish field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        ('es', 'IBAN', 'Banking field label'),
        ('es', 'BIC', 'Banking field label'),
        ('es', 'SWIFT', 'Banking field label'),
        ('es', 'NIF', 'Tax identification number (Número de Identificación Fiscal)'),
        ('es', 'CIF', 'Company identification (Código de Identificación Fiscal)'),
        ('es', 'S.A.', 'Company type abbreviation (Sociedad Anónima)'),
        ('es', 'S.L.', 'Company type abbreviation (Sociedad Limitada)'),
        ('es', 'Fecha', 'Date field label'),
        ('es', 'Importe', 'Amount field label'),
        ('es', 'Factura', 'Invoice field label'),
        ('es', 'Tel', 'Telephone abbreviation'),
        ('es', 'Fax', 'Fax abbreviation'),
        ('es', 'www', 'Web prefix'),
        ('es', 'http', 'Protocol prefix'),
        ('es', 'https', 'Protocol prefix')
        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # Portuguese field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        ('pt', 'IBAN', 'Banking field label'),
        ('pt', 'BIC', 'Banking field label'),
        ('pt', 'SWIFT', 'Banking field label'),
        ('pt', 'NIF', 'Tax identification number (Número de Identificação Fiscal)'),
        ('pt', 'NIPC', 'Company identification (Número de Identificação de Pessoa Coletiva)'),
        ('pt', 'Lda.', 'Company type abbreviation (Limitada)'),
        ('pt', 'S.A.', 'Company type abbreviation (Sociedade Anónima)'),
        ('pt', 'Data', 'Date field label'),
        ('pt', 'Valor', 'Amount field label'),
        ('pt', 'Fatura', 'Invoice field label'),
        ('pt', 'Tel', 'Telephone abbreviation'),
        ('pt', 'Fax', 'Fax abbreviation'),
        ('pt', 'www', 'Web prefix'),
        ('pt', 'http', 'Protocol prefix'),
        ('pt', 'https', 'Protocol prefix')
        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # Italian field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        ('it', 'IBAN', 'Banking field label'),
        ('it', 'BIC', 'Banking field label'),
        ('it', 'SWIFT', 'Banking field label'),
        ('it', 'P.IVA', 'VAT number (Partita IVA)'),
        ('it', 'C.F.', 'Tax code (Codice Fiscale)'),
        ('it', 'S.r.l.', 'Company type abbreviation (Società a responsabilità limitata)'),
        ('it', 'S.p.A.', 'Company type abbreviation (Società per Azioni)'),
        ('it', 'Data', 'Date field label'),
        ('it', 'Importo', 'Amount field label'),
        ('it', 'Fattura', 'Invoice field label'),
        ('it', 'Tel', 'Telephone abbreviation'),
        ('it', 'Fax', 'Fax abbreviation'),
        ('it', 'www', 'Web prefix'),
        ('it', 'http', 'Protocol prefix'),
        ('it', 'https', 'Protocol prefix')
        ON CONFLICT (language, label_text) DO NOTHING;
    """)
    print("   ✓ Added entity field labels for tr, es, pt, it")

    # ==================== 8. ENTITY INVALID PATTERNS ====================
    print("\n8. Adding entity invalid patterns...")

    # Turkish invalid patterns
    op.execute("""
        INSERT INTO entity_invalid_patterns (language, entity_type, regex_pattern, description, enabled) VALUES
        ('tr', 'ORGANIZATION', '^\\d{10}$', 'Turkish tax ID (VKN - 10 digits)', true),
        ('tr', 'ORGANIZATION', '^\\d{11}$', 'Turkish ID number (TCKN - 11 digits)', true),
        ('tr', 'ORGANIZATION', '^[A-Z0-9]{1,10}\\d+$', 'Short alphanumeric codes', true),
        ('tr', 'ORGANIZATION', '^.+\\s+(Sokak|Cadde|Bulvar|Mahallesi)\\s*\\d*$', 'Turkish street addresses', true),
        ('tr', 'ORGANIZATION', '^\\d+$', 'Pure numeric values', true),
        ('tr', 'ORGANIZATION', '^[A-Z]{1,2}$', '1-2 letter codes', true),
        ('tr', 'ADDRESS_COMPONENT', '(\\n|\\s)(www|http)', 'Addresses with web artifacts', true),
        ('tr', 'LOCATION', '\\n', 'Locations with line breaks', true)
        ON CONFLICT (language, entity_type, regex_pattern) DO NOTHING;
    """)

    # Spanish invalid patterns
    op.execute("""
        INSERT INTO entity_invalid_patterns (language, entity_type, regex_pattern, description, enabled) VALUES
        ('es', 'ORGANIZATION', '^[A-Z]\\d{8}$', 'Spanish NIF/CIF format', true),
        ('es', 'ORGANIZATION', '^[A-Z]\\d{7}[A-Z]$', 'Spanish CIF format variant', true),
        ('es', 'ORGANIZATION', '^[A-Z0-9]{1,10}\\d+$', 'Short alphanumeric codes', true),
        ('es', 'ORGANIZATION', '^.+\\s+(Calle|Avenida|Plaza|Paseo)\\s+\\d+$', 'Spanish street addresses', true),
        ('es', 'ORGANIZATION', '^\\d+$', 'Pure numeric values', true),
        ('es', 'ORGANIZATION', '^[A-Z]{1,2}$', '1-2 letter codes', true),
        ('es', 'ADDRESS_COMPONENT', '(\\n|\\s)(www|http)', 'Addresses with web artifacts', true),
        ('es', 'LOCATION', '\\n', 'Locations with line breaks', true)
        ON CONFLICT (language, entity_type, regex_pattern) DO NOTHING;
    """)

    # Portuguese invalid patterns
    op.execute("""
        INSERT INTO entity_invalid_patterns (language, entity_type, regex_pattern, description, enabled) VALUES
        ('pt', 'ORGANIZATION', '^\\d{9}$', 'Portuguese NIF (9 digits)', true),
        ('pt', 'ORGANIZATION', '^PT\\d{9}$', 'Portuguese VAT number', true),
        ('pt', 'ORGANIZATION', '^[A-Z0-9]{1,10}\\d+$', 'Short alphanumeric codes', true),
        ('pt', 'ORGANIZATION', '^.+\\s+(Rua|Avenida|Praça|Travessa)\\s+\\d+$', 'Portuguese street addresses', true),
        ('pt', 'ORGANIZATION', '^\\d+$', 'Pure numeric values', true),
        ('pt', 'ORGANIZATION', '^[A-Z]{1,2}$', '1-2 letter codes', true),
        ('pt', 'ADDRESS_COMPONENT', '(\\n|\\s)(www|http)', 'Addresses with web artifacts', true),
        ('pt', 'LOCATION', '\\n', 'Locations with line breaks', true)
        ON CONFLICT (language, entity_type, regex_pattern) DO NOTHING;
    """)

    # Italian invalid patterns
    op.execute("""
        INSERT INTO entity_invalid_patterns (language, entity_type, regex_pattern, description, enabled) VALUES
        ('it', 'ORGANIZATION', '^IT\\d{11}$', 'Italian P.IVA (Partita IVA)', true),
        ('it', 'ORGANIZATION', '^[A-Z]{6}\\d{2}[A-Z]\\d{2}[A-Z]\\d{3}[A-Z]$', 'Italian Codice Fiscale pattern', true),
        ('it', 'ORGANIZATION', '^[A-Z0-9]{1,10}\\d+$', 'Short alphanumeric codes', true),
        ('it', 'ORGANIZATION', '^.+\\s+(Via|Viale|Piazza|Corso)\\s+\\d+$', 'Italian street addresses', true),
        ('it', 'ORGANIZATION', '^\\d+$', 'Pure numeric values', true),
        ('it', 'ORGANIZATION', '^[A-Z]{1,2}$', '1-2 letter codes', true),
        ('it', 'ADDRESS_COMPONENT', '(\\n|\\s)(www|http)', 'Addresses with web artifacts', true),
        ('it', 'LOCATION', '\\n', 'Locations with line breaks', true)
        ON CONFLICT (language, entity_type, regex_pattern) DO NOTHING;
    """)
    print("   ✓ Added entity invalid patterns for tr, es, pt, it")

    # ==================== 9. ENTITY CONFIDENCE THRESHOLDS ====================
    print("\n9. Adding entity confidence thresholds...")

    for lang in NEW_LANGUAGES:
        op.execute(f"""
            INSERT INTO entity_confidence_thresholds (language, entity_type, min_confidence, description) VALUES
            ('{lang}', 'ORGANIZATION', 0.70, 'Organizations need 70%+ confidence'),
            ('{lang}', 'PERSON', 0.65, 'Person names need 65%+ confidence'),
            ('{lang}', 'LOCATION', 0.70, 'Locations need 70%+ confidence'),
            ('{lang}', 'ADDRESS_COMPONENT', 0.60, 'Address components need 60%+ confidence')
            ON CONFLICT (language, entity_type) DO NOTHING;
        """)
    print("   ✓ Added confidence thresholds for tr, es, pt, it")

    # ==================== 10. ENTITY TYPE PATTERNS ====================
    print("\n10. Adding entity type patterns...")

    op.execute("""
        INSERT INTO entity_type_patterns (entity_type, pattern_value, pattern_type, config_key, language, is_active)
        VALUES
        -- Turkish (tr) - Organization patterns
        ('ORGANIZATION', 'A.Ş.', 'suffix', 'type_org_suffix_strong', 'tr', true),
        ('ORGANIZATION', 'Ltd.Şti.', 'suffix', 'type_org_suffix_strong', 'tr', true),
        ('ORGANIZATION', 'Şti.', 'suffix', 'type_org_suffix_strong', 'tr', true),
        ('ORGANIZATION', 'Banka', 'keyword', 'type_org_suffix_medium', 'tr', true),
        ('ORGANIZATION', 'Şirket', 'keyword', 'type_org_suffix_medium', 'tr', true),
        ('ORGANIZATION', 'Holding', 'keyword', 'type_org_suffix_medium', 'tr', true),

        -- Spanish (es) - Organization patterns
        ('ORGANIZATION', 'S.A.', 'suffix', 'type_org_suffix_strong', 'es', true),
        ('ORGANIZATION', 'S.L.', 'suffix', 'type_org_suffix_strong', 'es', true),
        ('ORGANIZATION', 'S.L.U.', 'suffix', 'type_org_suffix_strong', 'es', true),
        ('ORGANIZATION', 'Banco', 'keyword', 'type_org_suffix_medium', 'es', true),
        ('ORGANIZATION', 'Empresa', 'keyword', 'type_org_suffix_medium', 'es', true),
        ('ORGANIZATION', 'Compañía', 'keyword', 'type_org_suffix_medium', 'es', true),

        -- Portuguese (pt) - Organization patterns
        ('ORGANIZATION', 'Lda.', 'suffix', 'type_org_suffix_strong', 'pt', true),
        ('ORGANIZATION', 'S.A.', 'suffix', 'type_org_suffix_strong', 'pt', true),
        ('ORGANIZATION', 'SGPS', 'suffix', 'type_org_suffix_strong', 'pt', true),
        ('ORGANIZATION', 'Banco', 'keyword', 'type_org_suffix_medium', 'pt', true),
        ('ORGANIZATION', 'Empresa', 'keyword', 'type_org_suffix_medium', 'pt', true),
        ('ORGANIZATION', 'Companhia', 'keyword', 'type_org_suffix_medium', 'pt', true),

        -- Italian (it) - Organization patterns
        ('ORGANIZATION', 'S.r.l.', 'suffix', 'type_org_suffix_strong', 'it', true),
        ('ORGANIZATION', 'S.p.A.', 'suffix', 'type_org_suffix_strong', 'it', true),
        ('ORGANIZATION', 'S.a.s.', 'suffix', 'type_org_suffix_strong', 'it', true),
        ('ORGANIZATION', 'Banca', 'keyword', 'type_org_suffix_medium', 'it', true),
        ('ORGANIZATION', 'Società', 'keyword', 'type_org_suffix_medium', 'it', true),
        ('ORGANIZATION', 'Impresa', 'keyword', 'type_org_suffix_medium', 'it', true)

        ON CONFLICT (entity_type, pattern_value, language) DO NOTHING;
    """)
    print("   ✓ Added entity type patterns for tr, es, pt, it")

    # ==================== 11. UPDATE COUNTS ====================
    print("\n11. Updating supported_languages counts...")

    op.execute("""
        UPDATE supported_languages sl
        SET stop_words_count = (
            SELECT COUNT(*)
            FROM stop_words sw
            WHERE sw.language_code = sl.language_code AND sw.is_active = true
        )
        WHERE sl.language_code IN ('tr', 'es', 'pt', 'it');
    """)

    op.execute("""
        UPDATE supported_languages sl
        SET field_labels_count = (
            SELECT COUNT(*)
            FROM entity_field_labels efl
            WHERE efl.language = sl.language_code
        )
        WHERE sl.language_code IN ('tr', 'es', 'pt', 'it');
    """)
    print("   ✓ Updated stop_words_count and field_labels_count")

    print("\n✅ Migration 053 complete! Added Turkish, Spanish, Portuguese, Italian language support.")


def downgrade():
    conn = op.get_bind()

    print("\n=== Removing Turkish, Spanish, Portuguese, Italian Language Support ===\n")

    # Remove entity type patterns
    op.execute("""
        DELETE FROM entity_type_patterns WHERE language IN ('tr', 'es', 'pt', 'it');
    """)

    # Remove entity confidence thresholds
    op.execute("""
        DELETE FROM entity_confidence_thresholds WHERE language IN ('tr', 'es', 'pt', 'it');
    """)

    # Remove entity invalid patterns
    op.execute("""
        DELETE FROM entity_invalid_patterns WHERE language IN ('tr', 'es', 'pt', 'it');
    """)

    # Remove entity field labels
    op.execute("""
        DELETE FROM entity_field_labels WHERE language IN ('tr', 'es', 'pt', 'it');
    """)

    # Remove ngram patterns
    op.execute("""
        DELETE FROM ngram_patterns WHERE language_code IN ('tr', 'es', 'pt', 'it');
    """)

    # Remove stop words
    op.execute("""
        DELETE FROM stop_words WHERE language_code IN ('tr', 'es', 'pt', 'it');
    """)

    # Remove category keywords
    op.execute("""
        DELETE FROM category_keywords WHERE language_code IN ('tr', 'es', 'pt', 'it');
    """)

    # Remove category translations
    op.execute("""
        DELETE FROM category_translations WHERE language_code IN ('tr', 'es', 'pt', 'it');
    """)

    # Remove supported languages
    op.execute("""
        DELETE FROM supported_languages WHERE language_code IN ('tr', 'es', 'pt', 'it');
    """)

    # Revert system settings
    op.execute("""
        UPDATE system_settings
        SET setting_value = '["en","de","ru","fr"]', updated_at = now()
        WHERE setting_key = 'available_languages';
    """)

    # Revert spacy_model_mapping
    op.execute("""
        UPDATE system_settings
        SET setting_value = '{"en": "en_core_web_md", "de": "de_core_news_md", "fr": "fr_core_news_md", "ru": "ru_core_news_md"}',
            updated_at = now()
        WHERE setting_key = 'spacy_model_mapping';
    """)

    # Revert ocr_supported_languages
    op.execute("""
        UPDATE system_settings
        SET setting_value = '{"en": "eng", "de": "deu", "ru": "rus", "fr": "fra"}',
            updated_at = now()
        WHERE setting_key = 'ocr_supported_languages';
    """)

    # Revert language_metadata
    conn.execute(text("""
        UPDATE system_settings
        SET setting_value = :value, updated_at = now()
        WHERE setting_key = 'language_metadata'
    """), {"value": json.dumps({
        "en": {"code": "en", "name": "English", "native_name": "English"},
        "de": {"code": "de", "name": "German", "native_name": "Deutsch"},
        "ru": {"code": "ru", "name": "Russian", "native_name": "Русский"},
        "fr": {"code": "fr", "name": "French", "native_name": "Français"}
    })})

    print("✅ Migration 053 downgrade complete.")
