"""add cookie consent tables

Revision ID: 023_add_cookie_consent
Revises: 20251119_102400_add_stripe_customer_id
Create Date: 2025-11-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

revision = '023_add_cookie_consent'
down_revision = '20251119_102400_add_stripe_customer_id'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create cookie_categories table
    op.create_table(
        'cookie_categories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('category_key', sa.String(50), nullable=False, unique=True),
        sa.Column('is_required', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_enabled_by_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_cookie_category_key', 'cookie_categories', ['category_key'])
    op.create_index('idx_cookie_category_sort', 'cookie_categories', ['sort_order'])

    # Create cookie_category_translations table
    op.create_table(
        'cookie_category_translations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('cookie_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('language_code', sa.String(5), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_cookie_cat_trans_category', 'cookie_category_translations', ['category_id'])
    op.create_index('idx_cookie_cat_trans_lang', 'cookie_category_translations', ['language_code'])
    op.create_unique_constraint('uq_cookie_cat_trans', 'cookie_category_translations', ['category_id', 'language_code'])

    # Create cookie_definitions table
    op.create_table(
        'cookie_definitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('cookie_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cookie_name', sa.String(100), nullable=False),
        sa.Column('is_regex', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('domain', sa.String(200), nullable=True),
        sa.Column('expiration', sa.String(100), nullable=True),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_cookie_def_category', 'cookie_definitions', ['category_id'])
    op.create_index('idx_cookie_def_name', 'cookie_definitions', ['cookie_name'])
    op.create_index('idx_cookie_def_sort', 'cookie_definitions', ['sort_order'])

    # Create cookie_definition_translations table
    op.create_table(
        'cookie_definition_translations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('cookie_id', UUID(as_uuid=True), sa.ForeignKey('cookie_definitions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('language_code', sa.String(5), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_cookie_def_trans_cookie', 'cookie_definition_translations', ['cookie_id'])
    op.create_index('idx_cookie_def_trans_lang', 'cookie_definition_translations', ['language_code'])
    op.create_unique_constraint('uq_cookie_def_trans', 'cookie_definition_translations', ['cookie_id', 'language_code'])

    # Populate default cookie categories and translations
    op.execute("""
        -- Insert necessary cookies category
        WITH necessary_cat AS (
            INSERT INTO cookie_categories (id, category_key, is_required, is_enabled_by_default, sort_order, is_active)
            VALUES (gen_random_uuid(), 'necessary', true, true, 1, true)
            RETURNING id
        )
        INSERT INTO cookie_category_translations (id, category_id, language_code, title, description)
        SELECT
            gen_random_uuid(),
            id,
            lang.code,
            CASE lang.code
                WHEN 'en' THEN 'Strictly Necessary Cookies'
                WHEN 'de' THEN 'Unbedingt erforderliche Cookies'
                WHEN 'ru' THEN 'Строго необходимые cookies'
            END,
            CASE lang.code
                WHEN 'en' THEN 'These cookies are essential for the proper functioning of the website. Without these cookies, the website would not work properly. They enable core functionality such as security, network management, authentication, and accessibility.'
                WHEN 'de' THEN 'Diese Cookies sind für das ordnungsgemäße Funktionieren der Website unerlässlich. Ohne diese Cookies würde die Website nicht richtig funktionieren. Sie ermöglichen grundlegende Funktionen wie Sicherheit, Netzwerkverwaltung, Authentifizierung und Zugänglichkeit.'
                WHEN 'ru' THEN 'Эти файлы cookie необходимы для правильной работы веб-сайта. Без этих файлов cookie веб-сайт не будет работать должным образом. Они обеспечивают основные функции, такие как безопасность, управление сетью, аутентификация и доступность.'
            END
        FROM necessary_cat, (VALUES ('en'), ('de'), ('ru')) AS lang(code);

        -- Insert analytics cookies category
        WITH analytics_cat AS (
            INSERT INTO cookie_categories (id, category_key, is_required, is_enabled_by_default, sort_order, is_active)
            VALUES (gen_random_uuid(), 'analytics', false, false, 2, true)
            RETURNING id
        )
        INSERT INTO cookie_category_translations (id, category_id, language_code, title, description)
        SELECT
            gen_random_uuid(),
            id,
            lang.code,
            CASE lang.code
                WHEN 'en' THEN 'Analytics Cookies'
                WHEN 'de' THEN 'Analyse-Cookies'
                WHEN 'ru' THEN 'Аналитические cookies'
            END,
            CASE lang.code
                WHEN 'en' THEN 'These cookies collect information about how you use the website, which pages you visited and which links you clicked on. All of the data is anonymized and cannot be used to identify you.'
                WHEN 'de' THEN 'Diese Cookies sammeln Informationen darüber, wie Sie die Website nutzen, welche Seiten Sie besucht und welche Links Sie angeklickt haben. Alle Daten werden anonymisiert und können nicht zur Identifizierung verwendet werden.'
                WHEN 'ru' THEN 'Эти файлы cookie собирают информацию о том, как вы используете веб-сайт, какие страницы вы посетили и по каким ссылкам вы щелкнули. Все данные анонимизированы и не могут быть использованы для вашей идентификации.'
            END
        FROM analytics_cat, (VALUES ('en'), ('de'), ('ru')) AS lang(code);

        -- Insert functionality cookies category
        WITH functionality_cat AS (
            INSERT INTO cookie_categories (id, category_key, is_required, is_enabled_by_default, sort_order, is_active)
            VALUES (gen_random_uuid(), 'functionality', false, false, 3, true)
            RETURNING id
        )
        INSERT INTO cookie_category_translations (id, category_id, language_code, title, description)
        SELECT
            gen_random_uuid(),
            id,
            lang.code,
            CASE lang.code
                WHEN 'en' THEN 'Functionality Cookies'
                WHEN 'de' THEN 'Funktions-Cookies'
                WHEN 'ru' THEN 'Функциональные cookies'
            END,
            CASE lang.code
                WHEN 'en' THEN 'These cookies enable the website to provide enhanced functionality and personalization. They may be set by us or by third party providers whose services we have added to our pages.'
                WHEN 'de' THEN 'Diese Cookies ermöglichen der Website, erweiterte Funktionalität und Personalisierung bereitzustellen. Sie können von uns oder von Drittanbietern gesetzt werden, deren Dienste wir unseren Seiten hinzugefügt haben.'
                WHEN 'ru' THEN 'Эти файлы cookie позволяют веб-сайту предоставлять расширенную функциональность и персонализацию. Они могут быть установлены нами или сторонними поставщиками, чьи услуги мы добавили на наши страницы.'
            END
        FROM functionality_cat, (VALUES ('en'), ('de'), ('ru')) AS lang(code);
    """)

    # Populate default cookie definitions for necessary cookies
    op.execute("""
        -- Add authentication cookies
        WITH necessary_cat AS (
            SELECT id FROM cookie_categories WHERE category_key = 'necessary'
        ),
        access_token_cookie AS (
            INSERT INTO cookie_definitions (id, category_id, cookie_name, is_regex, domain, expiration, sort_order, is_active)
            SELECT gen_random_uuid(), id, 'access_token', false, 'bonidoc.com', '30 minutes', 1, true
            FROM necessary_cat
            RETURNING id
        )
        INSERT INTO cookie_definition_translations (id, cookie_id, language_code, description)
        SELECT
            gen_random_uuid(),
            id,
            lang.code,
            CASE lang.code
                WHEN 'en' THEN 'Authentication token for secure login'
                WHEN 'de' THEN 'Authentifizierungstoken für sichere Anmeldung'
                WHEN 'ru' THEN 'Токен аутентификации для безопасного входа'
            END
        FROM access_token_cookie, (VALUES ('en'), ('de'), ('ru')) AS lang(code);

        WITH necessary_cat AS (
            SELECT id FROM cookie_categories WHERE category_key = 'necessary'
        ),
        refresh_token_cookie AS (
            INSERT INTO cookie_definitions (id, category_id, cookie_name, is_regex, domain, expiration, sort_order, is_active)
            SELECT gen_random_uuid(), id, 'refresh_token', false, 'bonidoc.com', '30 days', 2, true
            FROM necessary_cat
            RETURNING id
        )
        INSERT INTO cookie_definition_translations (id, cookie_id, language_code, description)
        SELECT
            gen_random_uuid(),
            id,
            lang.code,
            CASE lang.code
                WHEN 'en' THEN 'Token to refresh authentication session'
                WHEN 'de' THEN 'Token zum Erneuern der Authentifizierungssitzung'
                WHEN 'ru' THEN 'Токен для обновления сеанса аутентификации'
            END
        FROM refresh_token_cookie, (VALUES ('en'), ('de'), ('ru')) AS lang(code);

        WITH necessary_cat AS (
            SELECT id FROM cookie_categories WHERE category_key = 'necessary'
        ),
        consent_cookie AS (
            INSERT INTO cookie_definitions (id, category_id, cookie_name, is_regex, domain, expiration, sort_order, is_active)
            SELECT gen_random_uuid(), id, 'cc_cookie', false, 'bonidoc.com', '1 year', 3, true
            FROM necessary_cat
            RETURNING id
        )
        INSERT INTO cookie_definition_translations (id, cookie_id, language_code, description)
        SELECT
            gen_random_uuid(),
            id,
            lang.code,
            CASE lang.code
                WHEN 'en' THEN 'Stores your cookie preferences'
                WHEN 'de' THEN 'Speichert Ihre Cookie-Einstellungen'
                WHEN 'ru' THEN 'Сохраняет ваши предпочтения cookie'
            END
        FROM consent_cookie, (VALUES ('en'), ('de'), ('ru')) AS lang(code);
    """)

    # Add system settings for cookie consent UI configuration
    op.execute("""
        INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, is_public, category)
        VALUES
        (
            gen_random_uuid(),
            'cookie_consent_modal_position',
            'bottom right',
            'string',
            'Position of cookie consent modal (bottom right, bottom left, top right, top left, center)',
            true,
            'cookie_consent'
        ),
        (
            gen_random_uuid(),
            'cookie_consent_auto_show',
            'true',
            'boolean',
            'Automatically show cookie consent on first visit',
            true,
            'cookie_consent'
        ),
        (
            gen_random_uuid(),
            'cookie_consent_revision',
            '1',
            'integer',
            'Cookie consent policy revision number (increment to re-prompt users)',
            true,
            'cookie_consent'
        );
    """)


def downgrade() -> None:
    # Remove system settings
    op.execute("DELETE FROM system_settings WHERE category = 'cookie_consent'")

    # Drop tables in reverse order (due to foreign keys)
    op.drop_table('cookie_definition_translations')
    op.drop_table('cookie_definitions')
    op.drop_table('cookie_category_translations')
    op.drop_table('cookie_categories')
