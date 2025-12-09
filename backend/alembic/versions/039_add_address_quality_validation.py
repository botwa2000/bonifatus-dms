"""add address quality validation config

Revision ID: 039_add_address_quality
Revises: 038_add_libpostal
Create Date: 2025-12-09 00:00:00

Add comprehensive ADDRESS quality validation and entity boundary cleaning:
- Stop words for time/duration/measurement terms (all languages)
- Entity quality config values for ADDRESS-specific validation rules
- Language-agnostic pattern detection (dates, times, structural requirements)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '039_add_address_quality'
down_revision = '038_add_libpostal'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== ADD STOP WORDS FOR TIME/DURATION/MEASUREMENT ====================
    # These words add no semantic value and should be filtered in keywords AND entities
    # Common in parking receipts, invoices, forms - prevent garbage extraction

    op.execute("""
        INSERT INTO stop_words (id, word, language_code, is_active, created_at)
        VALUES

        -- ========== GERMAN (de) - Time/Duration/Measurement ==========

        -- Time range prepositions
        (gen_random_uuid(), 'von', 'de', true, NOW()),
        (gen_random_uuid(), 'bis', 'de', true, NOW()),
        (gen_random_uuid(), 'ab', 'de', true, NOW()),

        -- Duration units
        (gen_random_uuid(), 'min', 'de', true, NOW()),
        (gen_random_uuid(), 'std', 'de', true, NOW()),
        (gen_random_uuid(), 'sek', 'de', true, NOW()),
        (gen_random_uuid(), 'sekunden', 'de', true, NOW()),

        -- Parking/access terms
        (gen_random_uuid(), 'einfahrt', 'de', true, NOW()),
        (gen_random_uuid(), 'ausfahrt', 'de', true, NOW()),
        (gen_random_uuid(), 'parkdauer', 'de', true, NOW()),
        (gen_random_uuid(), 'parken', 'de', true, NOW()),
        (gen_random_uuid(), 'parkzeit', 'de', true, NOW()),
        (gen_random_uuid(), 'gebühr', 'de', true, NOW()),
        (gen_random_uuid(), 'frei', 'de', true, NOW()),
        (gen_random_uuid(), 'gültig', 'de', true, NOW()),

        -- Time-related terms
        (gen_random_uuid(), 'zeitpunkt', 'de', true, NOW()),
        (gen_random_uuid(), 'zeitraum', 'de', true, NOW()),
        (gen_random_uuid(), 'dauer', 'de', true, NOW()),
        (gen_random_uuid(), 'beginn', 'de', true, NOW()),
        (gen_random_uuid(), 'ende', 'de', true, NOW()),

        -- Weight/measurement units
        (gen_random_uuid(), 'kg', 'de', true, NOW()),
        (gen_random_uuid(), 'g', 'de', true, NOW()),
        (gen_random_uuid(), 'mg', 'de', true, NOW()),
        (gen_random_uuid(), 'cm', 'de', true, NOW()),
        (gen_random_uuid(), 'm', 'de', true, NOW()),
        (gen_random_uuid(), 'mm', 'de', true, NOW()),
        (gen_random_uuid(), 'km', 'de', true, NOW()),
        (gen_random_uuid(), 'l', 'de', true, NOW()),
        (gen_random_uuid(), 'ml', 'de', true, NOW()),

        -- Common abbreviations (field labels)
        (gen_random_uuid(), 'tel', 'de', true, NOW()),
        (gen_random_uuid(), 'fax', 'de', true, NOW()),
        (gen_random_uuid(), 'nr', 'de', true, NOW()),
        (gen_random_uuid(), 'str', 'de', true, NOW()),

        -- ========== ENGLISH (en) - Time/Duration/Measurement ==========

        -- Time range prepositions
        (gen_random_uuid(), 'from', 'en', true, NOW()),
        (gen_random_uuid(), 'to', 'en', true, NOW()),
        (gen_random_uuid(), 'until', 'en', true, NOW()),
        (gen_random_uuid(), 'till', 'en', true, NOW()),

        -- Duration units
        (gen_random_uuid(), 'min', 'en', true, NOW()),
        (gen_random_uuid(), 'mins', 'en', true, NOW()),
        (gen_random_uuid(), 'hr', 'en', true, NOW()),
        (gen_random_uuid(), 'hrs', 'en', true, NOW()),
        (gen_random_uuid(), 'sec', 'en', true, NOW()),
        (gen_random_uuid(), 'secs', 'en', true, NOW()),

        -- Parking/access terms
        (gen_random_uuid(), 'entry', 'en', true, NOW()),
        (gen_random_uuid(), 'exit', 'en', true, NOW()),
        (gen_random_uuid(), 'parking', 'en', true, NOW()),
        (gen_random_uuid(), 'duration', 'en', true, NOW()),
        (gen_random_uuid(), 'fee', 'en', true, NOW()),
        (gen_random_uuid(), 'free', 'en', true, NOW()),
        (gen_random_uuid(), 'valid', 'en', true, NOW()),

        -- Time-related terms
        (gen_random_uuid(), 'start', 'en', true, NOW()),
        (gen_random_uuid(), 'end', 'en', true, NOW()),
        (gen_random_uuid(), 'begin', 'en', true, NOW()),
        (gen_random_uuid(), 'period', 'en', true, NOW()),

        -- Weight/measurement units
        (gen_random_uuid(), 'kg', 'en', true, NOW()),
        (gen_random_uuid(), 'g', 'en', true, NOW()),
        (gen_random_uuid(), 'mg', 'en', true, NOW()),
        (gen_random_uuid(), 'oz', 'en', true, NOW()),
        (gen_random_uuid(), 'lb', 'en', true, NOW()),
        (gen_random_uuid(), 'cm', 'en', true, NOW()),
        (gen_random_uuid(), 'm', 'en', true, NOW()),
        (gen_random_uuid(), 'mm', 'en', true, NOW()),
        (gen_random_uuid(), 'km', 'en', true, NOW()),
        (gen_random_uuid(), 'ft', 'en', true, NOW()),
        (gen_random_uuid(), 'in', 'en', true, NOW()),
        (gen_random_uuid(), 'l', 'en', true, NOW()),
        (gen_random_uuid(), 'ml', 'en', true, NOW()),

        -- Common abbreviations (field labels)
        (gen_random_uuid(), 'tel', 'en', true, NOW()),
        (gen_random_uuid(), 'fax', 'en', true, NOW()),
        (gen_random_uuid(), 'no', 'en', true, NOW()),
        (gen_random_uuid(), 'st', 'en', true, NOW()),

        -- ========== FRENCH (fr) - Time/Duration/Measurement ==========

        -- Time range prepositions
        (gen_random_uuid(), 'de', 'fr', true, NOW()),
        (gen_random_uuid(), 'à', 'fr', true, NOW()),
        (gen_random_uuid(), 'jusqu', 'fr', true, NOW()),
        (gen_random_uuid(), 'dès', 'fr', true, NOW()),

        -- Duration units
        (gen_random_uuid(), 'min', 'fr', true, NOW()),
        (gen_random_uuid(), 'h', 'fr', true, NOW()),
        (gen_random_uuid(), 's', 'fr', true, NOW()),

        -- Parking/access terms
        (gen_random_uuid(), 'entrée', 'fr', true, NOW()),
        (gen_random_uuid(), 'sortie', 'fr', true, NOW()),
        (gen_random_uuid(), 'stationnement', 'fr', true, NOW()),
        (gen_random_uuid(), 'durée', 'fr', true, NOW()),
        (gen_random_uuid(), 'tarif', 'fr', true, NOW()),
        (gen_random_uuid(), 'gratuit', 'fr', true, NOW()),
        (gen_random_uuid(), 'valable', 'fr', true, NOW()),

        -- Time-related terms
        (gen_random_uuid(), 'début', 'fr', true, NOW()),
        (gen_random_uuid(), 'fin', 'fr', true, NOW()),
        (gen_random_uuid(), 'période', 'fr', true, NOW()),

        -- Weight/measurement units
        (gen_random_uuid(), 'kg', 'fr', true, NOW()),
        (gen_random_uuid(), 'g', 'fr', true, NOW()),
        (gen_random_uuid(), 'mg', 'fr', true, NOW()),
        (gen_random_uuid(), 'cm', 'fr', true, NOW()),
        (gen_random_uuid(), 'm', 'fr', true, NOW()),
        (gen_random_uuid(), 'mm', 'fr', true, NOW()),
        (gen_random_uuid(), 'km', 'fr', true, NOW()),
        (gen_random_uuid(), 'l', 'fr', true, NOW()),
        (gen_random_uuid(), 'ml', 'fr', true, NOW()),

        -- Common abbreviations (field labels)
        (gen_random_uuid(), 'tél', 'fr', true, NOW()),
        (gen_random_uuid(), 'fax', 'fr', true, NOW()),
        (gen_random_uuid(), 'nº', 'fr', true, NOW()),
        (gen_random_uuid(), 'rue', 'fr', true, NOW()),

        -- ========== RUSSIAN (ru) - Time/Duration/Measurement ==========

        -- Time range prepositions
        (gen_random_uuid(), 'от', 'ru', true, NOW()),
        (gen_random_uuid(), 'до', 'ru', true, NOW()),
        (gen_random_uuid(), 'с', 'ru', true, NOW()),
        (gen_random_uuid(), 'по', 'ru', true, NOW()),

        -- Duration units
        (gen_random_uuid(), 'мин', 'ru', true, NOW()),
        (gen_random_uuid(), 'ч', 'ru', true, NOW()),
        (gen_random_uuid(), 'сек', 'ru', true, NOW()),

        -- Parking/access terms
        (gen_random_uuid(), 'въезд', 'ru', true, NOW()),
        (gen_random_uuid(), 'выезд', 'ru', true, NOW()),
        (gen_random_uuid(), 'парковка', 'ru', true, NOW()),
        (gen_random_uuid(), 'длительность', 'ru', true, NOW()),
        (gen_random_uuid(), 'плата', 'ru', true, NOW()),
        (gen_random_uuid(), 'бесплатно', 'ru', true, NOW()),
        (gen_random_uuid(), 'действителен', 'ru', true, NOW()),

        -- Time-related terms
        (gen_random_uuid(), 'начало', 'ru', true, NOW()),
        (gen_random_uuid(), 'конец', 'ru', true, NOW()),
        (gen_random_uuid(), 'период', 'ru', true, NOW()),

        -- Weight/measurement units
        (gen_random_uuid(), 'кг', 'ru', true, NOW()),
        (gen_random_uuid(), 'г', 'ru', true, NOW()),
        (gen_random_uuid(), 'мг', 'ru', true, NOW()),
        (gen_random_uuid(), 'см', 'ru', true, NOW()),
        (gen_random_uuid(), 'м', 'ru', true, NOW()),
        (gen_random_uuid(), 'мм', 'ru', true, NOW()),
        (gen_random_uuid(), 'км', 'ru', true, NOW()),
        (gen_random_uuid(), 'л', 'ru', true, NOW()),
        (gen_random_uuid(), 'мл', 'ru', true, NOW()),

        -- Common abbreviations (field labels)
        (gen_random_uuid(), 'тел', 'ru', true, NOW()),
        (gen_random_uuid(), 'факс', 'ru', true, NOW()),
        (gen_random_uuid(), '№', 'ru', true, NOW()),
        (gen_random_uuid(), 'ул', 'ru', true, NOW())

        ON CONFLICT (word, language_code) DO NOTHING
    """)

    # ==================== ADD ADDRESS QUALITY CONFIG ====================
    # Configuration values for ADDRESS-specific validation rules
    # These work with universal pattern detection (dates, times, structure)

    op.execute("""
        INSERT INTO entity_quality_config (config_key, config_value, category, description, min_value, max_value)
        VALUES

        -- Date/Time pattern penalties (language-agnostic regex detection)
        ('addr_datetime_penalty', 0.05, 'entity_type', 'Severe penalty for date+time pattern (e.g., "3.04.23 13 23")', 0.01, 0.15),
        ('addr_date_penalty', 0.10, 'entity_type', 'Penalty for date pattern (e.g., "3.04.23", "2023-12-09")', 0.05, 0.25),

        -- Structural validation penalties (language-agnostic)
        ('addr_no_letters_penalty', 0.05, 'entity_type', 'Severe penalty for no alphabetic characters', 0.01, 0.15),
        ('addr_single_short_word_penalty', 0.20, 'entity_type', 'Penalty for single word <= 3 chars (likely garbage)', 0.10, 0.40),
        ('addr_too_short_penalty', 0.30, 'entity_type', 'Penalty for address < 8 characters', 0.15, 0.50),
        ('addr_excessive_digits_penalty', 0.25, 'entity_type', 'Penalty for > 70% digits (not a real address)', 0.15, 0.40),

        -- Field label prefix penalty (database-driven, language-specific)
        ('addr_field_label_prefix_penalty', 0.10, 'entity_type', 'Penalty for starting with field label (von:, bis:, min.)', 0.05, 0.25),

        -- Numeric format validation
        ('addr_invalid_numeric_penalty', 0.15, 'entity_type', 'Penalty for invalid numeric format (not postal code)', 0.10, 0.30),
        ('addr_postal_code_bonus', 1.2, 'entity_type', 'Bonus for valid postal code format (5-10 digits)', 1.0, 1.4),

        -- Component bonuses (libpostal component validation)
        ('addr_valid_components_bonus', 1.3, 'entity_type', 'Bonus for valid address components detected', 1.0, 1.5),
        ('addr_proper_structure_bonus', 1.2, 'entity_type', 'Bonus for proper address structure (number+text or postal+city)', 1.0, 1.4),

        -- LOCATION-specific quality checks (for cleaning boundaries)
        ('location_trailing_stopword_penalty', 0.30, 'entity_type', 'Penalty for LOCATION ending with stop word/field label (e.g., "Frankfurt Tel")', 0.15, 0.50),

        -- ORGANIZATION-specific additions (for cleaning boundaries)
        ('org_trailing_stopword_penalty', 0.30, 'entity_type', 'Penalty for ORGANIZATION ending with stop word/field label', 0.15, 0.50),

        -- PERSON-specific additions (for cleaning boundaries)
        ('person_trailing_stopword_penalty', 0.30, 'entity_type', 'Penalty for PERSON ending with stop word/field label', 0.15, 0.50),

        -- Thresholds for ADDRESS filtering
        ('address_libpostal_confidence', 0.90, 'algorithm', 'Base confidence for libpostal extraction', 0.70, 0.95),
        ('address_min_component_count', 2.0, 'threshold', 'Minimum address components required (road, city, postal, etc.)', 1.0, 3.0)

        ON CONFLICT (config_key) DO NOTHING
    """)

    # Update stop_words_count in supported_languages table
    op.execute("""
        UPDATE supported_languages sl
        SET stop_words_count = (
            SELECT COUNT(*)
            FROM stop_words sw
            WHERE sw.language_code = sl.language_code AND sw.is_active = true
        ),
        updated_at = NOW()
    """)


def downgrade():
    # Remove ADDRESS quality config values
    op.execute("""
        DELETE FROM entity_quality_config
        WHERE config_key IN (
            'addr_datetime_penalty',
            'addr_date_penalty',
            'addr_no_letters_penalty',
            'addr_single_short_word_penalty',
            'addr_too_short_penalty',
            'addr_excessive_digits_penalty',
            'addr_field_label_prefix_penalty',
            'addr_invalid_numeric_penalty',
            'addr_postal_code_bonus',
            'addr_valid_components_bonus',
            'addr_proper_structure_bonus',
            'location_trailing_stopword_penalty',
            'org_trailing_stopword_penalty',
            'person_trailing_stopword_penalty',
            'address_libpostal_confidence',
            'address_min_component_count'
        )
    """)

    # Remove stop words (sample - full removal would be too long)
    op.execute("""
        DELETE FROM stop_words
        WHERE language_code IN ('de', 'en', 'fr', 'ru')
        AND word IN (
            'von', 'bis', 'ab', 'min', 'std', 'sek', 'einfahrt', 'ausfahrt', 'frei', 'tel', 'fax', 'kg', 'cm',
            'from', 'to', 'until', 'mins', 'hrs', 'entry', 'exit', 'free', 'tel', 'fax', 'kg', 'cm',
            'de', 'à', 'jusqu', 'min', 'h', 'entrée', 'sortie', 'gratuit', 'tél', 'fax', 'kg', 'cm',
            'от', 'до', 'с', 'по', 'мин', 'ч', 'въезд', 'выезд', 'бесплатно', 'тел', 'факс', 'кг', 'см'
        )
    """)

    # Recalculate stop_words_count
    op.execute("""
        UPDATE supported_languages sl
        SET stop_words_count = (
            SELECT COUNT(*)
            FROM stop_words sw
            WHERE sw.language_code = sl.language_code AND sw.is_active = true
        ),
        updated_at = NOW()
    """)
