"""populate ml learning configuration and stopwords

Revision ID: 015_ml_config
Revises: 014_cleanup_duplicates
Create Date: 2025-11-04 15:00:00.000000

Populates:
1. ML learning parameters in system_settings table
2. Multilingual stopwords in stop_words table
3. All values configurable - no hardcoded constants in code

See ML_LEARNING_SYSTEM.md for complete documentation
"""
from alembic import op
from sqlalchemy import text
import uuid
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = '015_ml_config'
down_revision = '014_cleanup_duplicates'
branch_labels = None
depends_on = None


def upgrade():
    """Populate ML learning configuration and stopwords"""
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    print("\n=== Populating ML Learning Configuration ===\n")

    # ============================================================
    # 1. ML Learning Parameters in system_settings
    # ============================================================

    ml_settings = [
        {
            'key': 'ml_learning_enabled',
            'value': 'true',
            'dtype': 'boolean',
            'desc': 'Enable ML keyword learning from user classifications',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_primary_weight',
            'value': '1.0',
            'dtype': 'float',
            'desc': 'Weight boost for keywords in primary category',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_secondary_weight',
            'value': '0.3',
            'dtype': 'float',
            'desc': 'Weight boost for keywords in secondary categories (all equal)',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_correct_prediction_bonus',
            'value': '0.2',
            'dtype': 'float',
            'desc': 'Additional boost when AI prediction was correct (conservative reinforcement)',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_wrong_prediction_boost',
            'value': '0.5',
            'dtype': 'float',
            'desc': 'Additional boost when AI prediction was wrong (aggressive correction)',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_low_confidence_correct_multiplier',
            'value': '1.5',
            'dtype': 'float',
            'desc': 'Multiplier when AI correct prediction had low confidence (<50%)',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_high_confidence_wrong_multiplier',
            'value': '1.3',
            'dtype': 'float',
            'desc': 'Multiplier when AI wrong prediction had high confidence (>80%)',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_min_keywords_required',
            'value': '3',
            'dtype': 'integer',
            'desc': 'Minimum keywords required in document for learning',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_min_keyword_length',
            'value': '3',
            'dtype': 'integer',
            'desc': 'Minimum character length for keywords to learn',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_min_weight_differential',
            'value': '0.3',
            'dtype': 'float',
            'desc': 'Minimum weight gap between primary and other categories',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_max_weight',
            'value': '10.0',
            'dtype': 'float',
            'desc': 'Maximum weight cap for keywords',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_min_weight',
            'value': '0.1',
            'dtype': 'float',
            'desc': 'Minimum weight floor for keywords',
            'public': False,
            'cat': 'ml'
        },
        {
            'key': 'ml_learning_rate',
            'value': '1.0',
            'dtype': 'float',
            'desc': 'Global learning rate multiplier (for fine-tuning)',
            'public': False,
            'cat': 'ml'
        },
    ]

    for setting in ml_settings:
        conn.execute(text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, is_public, category, created_at, updated_at)
            VALUES (:id, :key, :value, :dtype, :desc, :public, :cat, :created, :updated)
            ON CONFLICT (setting_key) DO UPDATE
            SET setting_value = EXCLUDED.setting_value,
                description = EXCLUDED.description,
                updated_at = EXCLUDED.updated_at
        """), {
            'id': str(uuid.uuid4()),
            'key': setting['key'],
            'value': setting['value'],
            'dtype': setting['dtype'],
            'desc': setting['desc'],
            'public': setting['public'],
            'cat': setting['cat'],
            'created': now,
            'updated': now
        })

    print(f"✓ Inserted {len(ml_settings)} ML learning parameters")

    # ============================================================
    # 2. Multilingual Stop Words
    # ============================================================

    print("\n=== Populating Stop Words ===\n")

    # English stopwords
    stop_words_en = [
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
        'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
        'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
        'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'where', 'when',
        'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'only', 'own', 'same', 'than', 'too', 'very'
    ]

    # German stopwords
    stop_words_de = [
        'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer', 'eines',
        'einem', 'einen', 'und', 'oder', 'aber', 'in', 'an', 'auf', 'für', 'mit',
        'von', 'zu', 'bei', 'ist', 'sind', 'war', 'waren', 'sein', 'haben', 'hat',
        'hatte', 'werden', 'wird', 'wurde', 'dieser', 'diese', 'dieses', 'jener',
        'jene', 'jenes', 'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'was', 'welche',
        'welcher', 'welches', 'wo', 'wann', 'warum', 'wie'
    ]

    # Russian stopwords
    stop_words_ru = [
        'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то',
        'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за',
        'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет',
        'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если',
        'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять',
        'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они',
        'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была',
        'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет',
        'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем',
        'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее',
        'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при',
        'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот',
        'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве',
        'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда',
        'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно',
        'всю', 'между'
    ]

    # French stopwords (framework for future expansion)
    stop_words_fr = [
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'mais', 'dans',
        'sur', 'à', 'pour', 'avec', 'par', 'est', 'sont', 'était', 'étaient', 'être',
        'avoir', 'a', 'avait', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
        'ce', 'cet', 'cette', 'ces', 'qui', 'que', 'quoi', 'où', 'quand', 'pourquoi', 'comment'
    ]

    stop_words_data = {
        'en': stop_words_en,
        'de': stop_words_de,
        'ru': stop_words_ru,
        'fr': stop_words_fr
    }

    total_inserted = 0
    for lang, words in stop_words_data.items():
        for word in words:
            conn.execute(text("""
                INSERT INTO stop_words (id, word, language_code, is_active, created_at)
                VALUES (:id, :word, :lang, true, :created)
                ON CONFLICT DO NOTHING
            """), {
                'id': str(uuid.uuid4()),
                'word': word.lower(),
                'lang': lang,
                'created': now
            })
            total_inserted += 1

    print(f"✓ Inserted {len(stop_words_en)} English stopwords")
    print(f"✓ Inserted {len(stop_words_de)} German stopwords")
    print(f"✓ Inserted {len(stop_words_ru)} Russian stopwords")
    print(f"✓ Inserted {len(stop_words_fr)} French stopwords")
    print(f"✓ Total: {total_inserted} stopwords across {len(stop_words_data)} languages")

    print("\n✓ Migration 015 completed: ML learning system ready")
    print("  - All configuration values stored in database")
    print("  - No hardcoded values in source code")
    print("  - Easy to add new languages or adjust parameters")


def downgrade():
    """Remove ML learning configuration"""
    conn = op.get_bind()

    # Remove ML settings
    conn.execute(text("""
        DELETE FROM system_settings
        WHERE category = 'ml' AND setting_key LIKE 'ml_%'
    """))

    # Remove stopwords
    conn.execute(text("""
        DELETE FROM stop_words
    """))

    print("✓ Removed ML learning configuration")
