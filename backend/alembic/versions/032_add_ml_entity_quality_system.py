"""add ml entity quality system

Revision ID: 032_ml_entity_quality
Revises: 031_expand_field_labels
Create Date: 2025-12-01 00:00:00

ML-Based Entity Quality System:
- entity_quality_config: Configurable weights/thresholds (replaces hardcoded values)
- entity_quality_training_data: Labeled examples for ML training
- entity_quality_models: Trained sklearn models (pickled)
- supported_languages: Dynamic language configuration
- entity_quality_features: Feature importance tracking
- entity_type_patterns: Type-specific patterns for confidence boosting (all languages)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '032_ml_entity_quality'
down_revision = '031_expand_field_labels'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create entity_quality_config table
    op.create_table(
        'entity_quality_config',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('config_key', sa.String(100), nullable=False, unique=True),
        sa.Column('config_value', sa.Float(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('idx_entity_quality_config_category', 'entity_quality_config', ['category'])

    # 2. Create entity_quality_training_data table
    op.create_table(
        'entity_quality_training_data',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entity_value', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('source', sa.String(50), nullable=False),  # user_blacklist, manual_label, auto_feedback
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL')
    )
    op.create_index('idx_training_data_language', 'entity_quality_training_data', ['language'])
    op.create_index('idx_training_data_source', 'entity_quality_training_data', ['source'])
    op.create_index('idx_training_data_is_valid', 'entity_quality_training_data', ['is_valid'])

    # 3. Create entity_quality_models table
    op.create_table(
        'entity_quality_models',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),  # LogisticRegression, RandomForest, etc.
        sa.Column('model_data', sa.LargeBinary(), nullable=False),  # Pickled sklearn model
        sa.Column('performance_metrics', postgresql.JSONB(), nullable=True),  # {accuracy, precision, recall, f1}
        sa.Column('training_samples_count', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('model_version', 'language', name='uq_model_version_language')
    )
    op.create_index('idx_models_language_active', 'entity_quality_models', ['language', 'is_active'])

    # 4. Create supported_languages table
    op.create_table(
        'supported_languages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('language_code', sa.String(10), nullable=False, unique=True),
        sa.Column('language_name', sa.String(100), nullable=False),
        sa.Column('hunspell_dict', sa.String(50), nullable=False),
        sa.Column('spacy_model', sa.String(100), nullable=False),
        sa.Column('ml_model_available', sa.Boolean(), default=False, nullable=False),
        sa.Column('stop_words_count', sa.Integer(), nullable=True),
        sa.Column('field_labels_count', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # 5. Create entity_quality_features table
    op.create_table(
        'entity_quality_features',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('feature_name', sa.String(100), nullable=False),
        sa.Column('feature_description', sa.Text(), nullable=True),
        sa.Column('importance_score', sa.Float(), nullable=True),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('feature_name', 'language', 'model_version', name='uq_feature_language_version')
    )
    op.create_index('idx_features_language', 'entity_quality_features', ['language'])

    # 6. Create entity_type_patterns table (no hardcoded patterns in code)
    op.create_table(
        'entity_type_patterns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('pattern_value', sa.String(100), nullable=False),
        sa.Column('pattern_type', sa.String(20), nullable=False),  # suffix, keyword, prefix
        sa.Column('config_key', sa.String(100), nullable=False),  # References entity_quality_config
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('entity_type', 'pattern_value', 'language', name='uq_pattern_value_language')
    )
    op.create_index('idx_type_patterns_entity_lang', 'entity_type_patterns', ['entity_type', 'language'])
    op.create_index('idx_type_patterns_active', 'entity_type_patterns', ['is_active'])

    # ==================== POPULATE DEFAULT DATA ====================

    # Populate entity_quality_config with default weights/thresholds
    op.execute("""
        INSERT INTO entity_quality_config (config_key, config_value, category, description, min_value, max_value)
        VALUES
        -- Length penalties
        ('length_very_short_penalty', 0.1, 'length', 'Penalty for entities < 2 chars', 0.0, 0.5),
        ('length_two_char_penalty', 0.3, 'length', 'Penalty for 2-char entities (e.g., AG, DE)', 0.0, 0.6),
        ('length_three_char_penalty', 0.6, 'length', 'Penalty for 3-char entities (e.g., Tel, Fax)', 0.0, 0.8),
        ('length_very_long_penalty', 0.2, 'length', 'Penalty for entities > 80 chars (OCR errors)', 0.0, 0.5),
        ('length_long_penalty', 0.5, 'length', 'Penalty for entities > 50 chars', 0.0, 0.8),
        ('length_optimal_bonus', 1.0, 'length', 'Bonus for optimal length 5-40 chars', 0.8, 1.2),

        -- Pattern penalties
        ('pattern_repetitive_severe', 0.1, 'pattern', 'Penalty for 6+ same char in row (OCR garbage)', 0.0, 0.3),
        ('pattern_repetitive_high', 0.3, 'pattern', 'Penalty for 5+ same char in row', 0.0, 0.5),
        ('pattern_repetitive_medium', 0.6, 'pattern', 'Penalty for 4+ same char in row', 0.0, 0.8),
        ('pattern_low_vowel_severe', 0.3, 'pattern', 'Penalty for vowel ratio < 0.10', 0.0, 0.5),
        ('pattern_low_vowel_medium', 0.6, 'pattern', 'Penalty for vowel ratio < 0.15', 0.0, 0.8),
        ('pattern_high_vowel_penalty', 0.7, 'pattern', 'Penalty for vowel ratio > 0.75', 0.0, 0.9),
        ('pattern_numeric_only', 0.1, 'pattern', 'Penalty for pure numeric/punctuation', 0.0, 0.3),
        ('pattern_mixed_case_penalty', 0.5, 'pattern', 'Penalty for random case mixing', 0.0, 0.8),
        ('pattern_excessive_punct', 0.5, 'pattern', 'Penalty for > 30% punctuation', 0.0, 0.8),

        -- Dictionary validation
        ('dict_all_valid_bonus', 1.3, 'dictionary', 'Bonus when all words valid in dictionary', 1.0, 1.5),
        ('dict_invalid_penalty', 0.6, 'dictionary', 'Penalty when < 60% words valid', 0.3, 0.8),
        ('dict_validation_threshold', 0.6, 'dictionary', 'Minimum ratio of valid words (60%)', 0.4, 0.8),

        -- Entity type bonuses
        ('type_org_suffix_strong', 1.3, 'entity_type', 'Strong org suffix bonus (GmbH, AG, Inc)', 1.0, 1.5),
        ('type_org_suffix_medium', 1.2, 'entity_type', 'Medium org suffix bonus (Bank, Verlag)', 1.0, 1.4),
        ('type_person_title_case', 1.2, 'entity_type', 'Person name title case bonus', 1.0, 1.4),
        ('type_person_uppercase_penalty', 0.9, 'entity_type', 'Person name all caps penalty', 0.7, 1.0),
        ('type_location_title_case', 1.1, 'entity_type', 'Location title case bonus', 1.0, 1.3),

        -- ML thresholds
        ('ml_confidence_threshold', 0.75, 'ml_threshold', 'Minimum confidence to keep entity', 0.5, 0.95),
        ('ml_training_min_samples', 100.0, 'ml_threshold', 'Minimum samples before auto-retrain', 50.0, 500.0),
        ('ml_test_split_ratio', 0.2, 'ml_threshold', 'Test set ratio for model evaluation', 0.1, 0.3),

        -- Threshold configs (for rule-based fallback only, ML learns these automatically)
        ('threshold_length_very_short', 2.0, 'threshold', 'Length below which entity is very short', 1.0, 5.0),
        ('threshold_length_short', 3.0, 'threshold', 'Length below which entity is short', 2.0, 5.0),
        ('threshold_length_optimal_min', 5.0, 'threshold', 'Minimum optimal length', 3.0, 10.0),
        ('threshold_length_optimal_max', 40.0, 'threshold', 'Maximum optimal length', 20.0, 60.0),
        ('threshold_length_long', 50.0, 'threshold', 'Length above which entity is long', 40.0, 80.0),
        ('threshold_length_very_long', 80.0, 'threshold', 'Length above which entity is very long', 60.0, 120.0),
        ('threshold_vowel_ratio_low', 0.15, 'threshold', 'Vowel ratio below which is suspicious', 0.1, 0.25),
        ('threshold_vowel_ratio_very_low', 0.10, 'threshold', 'Vowel ratio below which is very suspicious', 0.05, 0.15),
        ('threshold_vowel_ratio_high', 0.75, 'threshold', 'Vowel ratio above which is suspicious', 0.6, 0.9),
        ('threshold_special_char_high', 0.3, 'threshold', 'Special char ratio above which is excessive', 0.2, 0.5),
        ('threshold_repetitive_chars_medium', 4.0, 'threshold', 'Consecutive chars count for medium penalty', 3.0, 5.0),
        ('threshold_repetitive_chars_high', 5.0, 'threshold', 'Consecutive chars count for high penalty', 4.0, 6.0),
        ('threshold_repetitive_chars_severe', 6.0, 'threshold', 'Consecutive chars count for severe penalty', 5.0, 8.0),
        ('threshold_min_letters_for_vowel_check', 5.0, 'threshold', 'Min letters before checking vowel ratio', 3.0, 10.0),
        ('threshold_min_length_for_case_check', 5.0, 'threshold', 'Min length before checking mixed case', 3.0, 10.0),
        ('threshold_min_length_for_uppercase_penalty', 8.0, 'threshold', 'Min length for all-caps person penalty', 5.0, 15.0),
        ('fallback_multiplier', 0.8, 'threshold', 'Default multiplier when no specific rule applies', 0.5, 1.0)
    """)

    # Populate supported_languages
    op.execute("""
        INSERT INTO supported_languages
        (language_code, language_name, hunspell_dict, spacy_model, ml_model_available, stop_words_count, field_labels_count, is_active)
        VALUES
        ('de', 'German', 'de_DE', 'de_core_news_md', false, 204, 0, true),
        ('en', 'English', 'en_US', 'en_core_web_md', false, 129, 0, true),
        ('fr', 'French', 'fr_FR', 'fr_core_news_md', false, 184, 0, true),
        ('ru', 'Russian', 'ru_RU', 'ru_core_news_md', false, 211, 0, true)
    """)

    # Update stop_words_count and field_labels_count from existing tables
    op.execute("""
        UPDATE supported_languages sl
        SET stop_words_count = (
            SELECT COUNT(*)
            FROM stop_words sw
            WHERE sw.language_code = sl.language_code AND sw.is_active = true
        )
    """)

    op.execute("""
        UPDATE supported_languages sl
        SET field_labels_count = (
            SELECT COUNT(*)
            FROM entity_field_labels efl
            WHERE efl.language = sl.language_code
        )
    """)

    # Populate entity_type_patterns for all languages (NO hardcoded patterns in code)
    op.execute("""
        INSERT INTO entity_type_patterns (entity_type, pattern_value, pattern_type, config_key, language, is_active)
        VALUES
        -- German (de) - Organization patterns
        ('ORGANIZATION', 'GmbH', 'suffix', 'type_org_suffix_strong', 'de', true),
        ('ORGANIZATION', 'AG', 'suffix', 'type_org_suffix_strong', 'de', true),
        ('ORGANIZATION', 'KG', 'suffix', 'type_org_suffix_strong', 'de', true),
        ('ORGANIZATION', 'OHG', 'suffix', 'type_org_suffix_strong', 'de', true),
        ('ORGANIZATION', 'mbH', 'suffix', 'type_org_suffix_strong', 'de', true),
        ('ORGANIZATION', 'e.V.', 'suffix', 'type_org_suffix_strong', 'de', true),
        ('ORGANIZATION', 'UG', 'suffix', 'type_org_suffix_strong', 'de', true),
        ('ORGANIZATION', 'Bank', 'keyword', 'type_org_suffix_medium', 'de', true),
        ('ORGANIZATION', 'Verlag', 'keyword', 'type_org_suffix_medium', 'de', true),
        ('ORGANIZATION', 'Institut', 'keyword', 'type_org_suffix_medium', 'de', true),
        ('ORGANIZATION', 'Gesellschaft', 'keyword', 'type_org_suffix_medium', 'de', true),
        ('ORGANIZATION', 'Firma', 'keyword', 'type_org_suffix_medium', 'de', true),

        -- English (en) - Organization patterns
        ('ORGANIZATION', 'Inc', 'suffix', 'type_org_suffix_strong', 'en', true),
        ('ORGANIZATION', 'LLC', 'suffix', 'type_org_suffix_strong', 'en', true),
        ('ORGANIZATION', 'Ltd', 'suffix', 'type_org_suffix_strong', 'en', true),
        ('ORGANIZATION', 'Corp', 'suffix', 'type_org_suffix_strong', 'en', true),
        ('ORGANIZATION', 'Co', 'suffix', 'type_org_suffix_strong', 'en', true),
        ('ORGANIZATION', 'PLC', 'suffix', 'type_org_suffix_strong', 'en', true),
        ('ORGANIZATION', 'LLP', 'suffix', 'type_org_suffix_strong', 'en', true),
        ('ORGANIZATION', 'Bank', 'keyword', 'type_org_suffix_medium', 'en', true),
        ('ORGANIZATION', 'Company', 'keyword', 'type_org_suffix_medium', 'en', true),
        ('ORGANIZATION', 'Corporation', 'keyword', 'type_org_suffix_medium', 'en', true),
        ('ORGANIZATION', 'Institute', 'keyword', 'type_org_suffix_medium', 'en', true),
        ('ORGANIZATION', 'Foundation', 'keyword', 'type_org_suffix_medium', 'en', true),

        -- French (fr) - Organization patterns
        ('ORGANIZATION', 'SA', 'suffix', 'type_org_suffix_strong', 'fr', true),
        ('ORGANIZATION', 'SARL', 'suffix', 'type_org_suffix_strong', 'fr', true),
        ('ORGANIZATION', 'SAS', 'suffix', 'type_org_suffix_strong', 'fr', true),
        ('ORGANIZATION', 'EURL', 'suffix', 'type_org_suffix_strong', 'fr', true),
        ('ORGANIZATION', 'SNC', 'suffix', 'type_org_suffix_strong', 'fr', true),
        ('ORGANIZATION', 'SCI', 'suffix', 'type_org_suffix_strong', 'fr', true),
        ('ORGANIZATION', 'Banque', 'keyword', 'type_org_suffix_medium', 'fr', true),
        ('ORGANIZATION', 'Société', 'keyword', 'type_org_suffix_medium', 'fr', true),
        ('ORGANIZATION', 'Compagnie', 'keyword', 'type_org_suffix_medium', 'fr', true),
        ('ORGANIZATION', 'Institut', 'keyword', 'type_org_suffix_medium', 'fr', true),

        -- Russian (ru) - Organization patterns
        ('ORGANIZATION', 'ООО', 'suffix', 'type_org_suffix_strong', 'ru', true),
        ('ORGANIZATION', 'ЗАО', 'suffix', 'type_org_suffix_strong', 'ru', true),
        ('ORGANIZATION', 'ОАО', 'suffix', 'type_org_suffix_strong', 'ru', true),
        ('ORGANIZATION', 'ПАО', 'suffix', 'type_org_suffix_strong', 'ru', true),
        ('ORGANIZATION', 'ИП', 'suffix', 'type_org_suffix_strong', 'ru', true),
        ('ORGANIZATION', 'Банк', 'keyword', 'type_org_suffix_medium', 'ru', true),
        ('ORGANIZATION', 'Компания', 'keyword', 'type_org_suffix_medium', 'ru', true),
        ('ORGANIZATION', 'Общество', 'keyword', 'type_org_suffix_medium', 'ru', true)
    """)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('entity_type_patterns')
    op.drop_table('entity_quality_features')
    op.drop_table('supported_languages')
    op.drop_table('entity_quality_models')
    op.drop_table('entity_quality_training_data')
    op.drop_table('entity_quality_config')
