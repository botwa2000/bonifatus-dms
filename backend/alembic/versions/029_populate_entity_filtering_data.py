"""populate entity filtering data

Revision ID: 029_entity_filtering_data
Revises: 028_entity_filtering
Create Date: 2025-11-29 00:00:00

Initial entity filtering data:
- Field labels (IBAN, BIC, etc.) for German, English, Russian, French
- Invalid patterns (tax IDs, codes, etc.)
- Default confidence thresholds
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '029_entity_filtering_data'
down_revision = '028_entity_filtering'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================
    # 0. SPACY MODEL CONFIGURATION (database-driven, no hardcoding)
    # ========================================

    # Store spaCy model mappings in system_settings for dynamic loading
    op.execute("""
        INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, category, is_public)
        VALUES (
            (SELECT COALESCE(MAX(id), 0) + 1 FROM system_settings),
            'spacy_model_mapping',
            '{"en": "en_core_web_md", "de": "de_core_news_md", "fr": "fr_core_news_md", "ru": "ru_core_news_md"}',
            'json',
            'spaCy NER model names per language (md = medium models for better accuracy)',
            'nlp',
            false
        )
        ON CONFLICT (setting_key) DO UPDATE SET
            setting_value = EXCLUDED.setting_value,
            description = EXCLUDED.description,
            updated_at = now();
    """)
    # ========================================
    # 1. FIELD LABELS (common banking/tax labels that should not be entities)
    # ========================================

    # German field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        ('de', 'IBAN', 'Banking field label'),
        ('de', 'BIC', 'Banking field label'),
        ('de', 'SWIFT', 'Banking field label'),
        ('de', 'USt-IdNr', 'Tax ID field label'),
        ('de', 'Steuernummer', 'Tax number field label'),
        ('de', 'HRB', 'Company register abbreviation'),
        ('de', 'AG', 'Company type abbreviation'),
        ('de', 'GmbH', 'Company type abbreviation (kept in org names)'),
        ('de', 'Geschäftsführer', 'Job title field label'),
        ('de', 'Vorstand', 'Job title field label'),
        ('de', 'Datum', 'Date field label'),
        ('de', 'Betrag', 'Amount field label'),
        ('de', 'Rechnung', 'Invoice field label'),
        ('de', 'Rechnungsnummer', 'Invoice number field label'),
        ('de', 'Betreff', 'Subject field label'),
        ('de', 'PLZ', 'Postal code abbreviation'),
        ('de', 'Tel', 'Telephone abbreviation'),
        ('de', 'Fax', 'Fax abbreviation'),
        ('de', 'E-Mail', 'Email field label'),
        ('de', 'Website', 'Website field label'),
        ('de', 'www', 'Web prefix'),
        ('de', 'http', 'Protocol prefix'),
        ('de', 'https', 'Protocol prefix')
        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # English field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        ('en', 'IBAN', 'Banking field label'),
        ('en', 'BIC', 'Banking field label'),
        ('en', 'SWIFT', 'Banking field label'),
        ('en', 'VAT', 'Tax ID field label'),
        ('en', 'Tax ID', 'Tax ID field label'),
        ('en', 'Company No', 'Company registration field'),
        ('en', 'Inc', 'Company type abbreviation'),
        ('en', 'LLC', 'Company type abbreviation'),
        ('en', 'Ltd', 'Company type abbreviation'),
        ('en', 'Date', 'Date field label'),
        ('en', 'Amount', 'Amount field label'),
        ('en', 'Invoice', 'Invoice field label'),
        ('en', 'Subject', 'Subject field label'),
        ('en', 'Tel', 'Telephone abbreviation'),
        ('en', 'Fax', 'Fax abbreviation'),
        ('en', 'Email', 'Email field label'),
        ('en', 'Website', 'Website field label'),
        ('en', 'www', 'Web prefix'),
        ('en', 'http', 'Protocol prefix'),
        ('en', 'https', 'Protocol prefix')
        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # Russian field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        ('ru', 'IBAN', 'Banking field label'),
        ('ru', 'BIC', 'Banking field label'),
        ('ru', 'SWIFT', 'Banking field label'),
        ('ru', 'ИНН', 'Tax ID field label'),
        ('ru', 'КПП', 'Tax registration field label'),
        ('ru', 'ОГРН', 'Company registration field label'),
        ('ru', 'ООО', 'Company type abbreviation'),
        ('ru', 'ЗАО', 'Company type abbreviation'),
        ('ru', 'ОАО', 'Company type abbreviation'),
        ('ru', 'Дата', 'Date field label'),
        ('ru', 'Сумма', 'Amount field label'),
        ('ru', 'Счет', 'Invoice field label'),
        ('ru', 'Тема', 'Subject field label'),
        ('ru', 'Тел', 'Telephone abbreviation'),
        ('ru', 'Факс', 'Fax abbreviation'),
        ('ru', 'www', 'Web prefix'),
        ('ru', 'http', 'Protocol prefix'),
        ('ru', 'https', 'Protocol prefix')
        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # French field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        ('fr', 'IBAN', 'Banking field label'),
        ('fr', 'BIC', 'Banking field label'),
        ('fr', 'SWIFT', 'Banking field label'),
        ('fr', 'TVA', 'VAT field label'),
        ('fr', 'SIRET', 'Company registration field'),
        ('fr', 'SIREN', 'Company registration field'),
        ('fr', 'SA', 'Company type abbreviation'),
        ('fr', 'SARL', 'Company type abbreviation'),
        ('fr', 'SAS', 'Company type abbreviation'),
        ('fr', 'Date', 'Date field label'),
        ('fr', 'Montant', 'Amount field label'),
        ('fr', 'Facture', 'Invoice field label'),
        ('fr', 'Objet', 'Subject field label'),
        ('fr', 'Tél', 'Telephone abbreviation'),
        ('fr', 'Fax', 'Fax abbreviation'),
        ('fr', 'Email', 'Email field label'),
        ('fr', 'Site web', 'Website field label'),
        ('fr', 'www', 'Web prefix'),
        ('fr', 'http', 'Protocol prefix'),
        ('fr', 'https', 'Protocol prefix')
        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # ========================================
    # 2. INVALID PATTERNS (regex to filter out)
    # ========================================

    # German invalid patterns
    op.execute("""
        INSERT INTO entity_invalid_patterns (language, entity_type, regex_pattern, description, enabled) VALUES
        -- Tax IDs and registration numbers
        ('de', 'ORGANIZATION', '^DE\\d{9,11}$', 'German VAT ID (DE123456789)', true),
        ('de', 'ORGANIZATION', '^\\d{2,3}/\\d{3,4}/\\d{4,5}$', 'German tax number format', true),
        ('de', 'ORGANIZATION', '^HRB\\s+\\w+$', 'Company register reference (HRB City)', true),
        ('de', 'ORGANIZATION', '^HRA\\s+\\w+$', 'Company register reference (HRA City)', true),

        -- Short alphanumeric codes (likely IDs, not organizations)
        ('de', 'ORGANIZATION', '^[A-Z0-9]{1,10}\\d+$', 'Short alphanumeric codes (OLNUE1, ABC123)', true),
        ('de', 'ORGANIZATION', '^[A-Z]{2,6}\\d{2,8}$', 'Letter-number codes (CKP2024-00008227)', true),

        -- Street addresses misidentified as organizations
        ('de', 'ORGANIZATION', '^.+\\s+(Straße|Strasse|Ring|Platz|Weg|Allee)\\s+\\d+$', 'Street addresses with numbers', true),
        ('de', 'ORGANIZATION', '^.+-Ring\\s+\\d+$', 'Street names ending in -Ring (Carl-Zeiss-Ring 9)', true),

        -- Pure numbers
        ('de', 'ORGANIZATION', '^\\d+$', 'Pure numeric values', true),
        ('de', 'ORGANIZATION', '^\\d+[.,]\\d+$', 'Decimal numbers', true),

        -- Single letters or very short strings
        ('de', 'ORGANIZATION', '^[A-Z]$', 'Single capital letters', true),
        ('de', 'ORGANIZATION', '^[A-Z]{1,2}$', '1-2 letter codes', true),

        -- Clean up location duplicates with newlines
        ('de', 'ADDRESS_COMPONENT', '\\n(www|http)', 'Addresses with web artifacts', true),
        ('de', 'LOCATION', '\\n', 'Locations with line breaks', true)
        ON CONFLICT (language, entity_type, regex_pattern) DO NOTHING;
    """)

    # English invalid patterns
    op.execute("""
        INSERT INTO entity_invalid_patterns (language, entity_type, regex_pattern, description, enabled) VALUES
        ('en', 'ORGANIZATION', '^[A-Z]{2}\\d{9,12}$', 'VAT/Tax ID format', true),
        ('en', 'ORGANIZATION', '^[A-Z0-9]{1,10}\\d+$', 'Short alphanumeric codes', true),
        ('en', 'ORGANIZATION', '^.+\\s+(Street|Road|Avenue|Lane|Drive)\\s+\\d+$', 'Street addresses', true),
        ('en', 'ORGANIZATION', '^\\d+$', 'Pure numeric values', true),
        ('en', 'ORGANIZATION', '^[A-Z]{1,2}$', '1-2 letter codes', true),
        ('en', 'ADDRESS_COMPONENT', '\\n(www|http)', 'Addresses with web artifacts', true),
        ('en', 'LOCATION', '\\n', 'Locations with line breaks', true)
        ON CONFLICT (language, entity_type, regex_pattern) DO NOTHING;
    """)

    # Russian invalid patterns
    op.execute("""
        INSERT INTO entity_invalid_patterns (language, entity_type, regex_pattern, description, enabled) VALUES
        ('ru', 'ORGANIZATION', '^\\d{10}$', 'INN (10 digits)', true),
        ('ru', 'ORGANIZATION', '^\\d{12}$', 'INN individual (12 digits)', true),
        ('ru', 'ORGANIZATION', '^\\d{13}$', 'OGRN (13 digits)', true),
        ('ru', 'ORGANIZATION', '^[A-Z0-9]{1,10}\\d+$', 'Short alphanumeric codes', true),
        ('ru', 'ORGANIZATION', '^\\d+$', 'Pure numeric values', true),
        ('ru', 'ADDRESS_COMPONENT', '\\n(www|http)', 'Addresses with web artifacts', true),
        ('ru', 'LOCATION', '\\n', 'Locations with line breaks', true)
        ON CONFLICT (language, entity_type, regex_pattern) DO NOTHING;
    """)

    # French invalid patterns
    op.execute("""
        INSERT INTO entity_invalid_patterns (language, entity_type, regex_pattern, description, enabled) VALUES
        ('fr', 'ORGANIZATION', '^FR\\d{11}$', 'French VAT ID', true),
        ('fr', 'ORGANIZATION', '^\\d{9}$', 'SIREN (9 digits)', true),
        ('fr', 'ORGANIZATION', '^\\d{14}$', 'SIRET (14 digits)', true),
        ('fr', 'ORGANIZATION', '^[A-Z0-9]{1,10}\\d+$', 'Short alphanumeric codes', true),
        ('fr', 'ORGANIZATION', '^.+\\s+(Rue|Avenue|Boulevard|Place)\\s+\\d+$', 'Street addresses', true),
        ('fr', 'ORGANIZATION', '^\\d+$', 'Pure numeric values', true),
        ('fr', 'ADDRESS_COMPONENT', '\\n(www|http)', 'Addresses with web artifacts', true),
        ('fr', 'LOCATION', '\\n', 'Locations with line breaks', true)
        ON CONFLICT (language, entity_type, regex_pattern) DO NOTHING;
    """)

    # ========================================
    # 3. CONFIDENCE THRESHOLDS
    # ========================================

    # Default thresholds for all languages
    for lang in ['de', 'en', 'ru', 'fr']:
        op.execute(f"""
            INSERT INTO entity_confidence_thresholds (language, entity_type, min_confidence, description) VALUES
            ('{lang}', 'ORGANIZATION', 0.70, 'Organizations need 70%+ confidence'),
            ('{lang}', 'PERSON', 0.65, 'Person names need 65%+ confidence'),
            ('{lang}', 'LOCATION', 0.70, 'Locations need 70%+ confidence'),
            ('{lang}', 'ADDRESS_COMPONENT', 0.60, 'Address components need 60%+ confidence (pattern-based are often accurate)')
            ON CONFLICT (language, entity_type) DO NOTHING;
        """)


def downgrade():
    # Clear all populated data
    op.execute("DELETE FROM entity_confidence_thresholds;")
    op.execute("DELETE FROM entity_invalid_patterns;")
    op.execute("DELETE FROM entity_field_labels;")
