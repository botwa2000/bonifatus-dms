"""expand stopwords for all languages

Revision ID: 037_expand_stopwords
Revises: 036_tfidf_keywords
Create Date: 2025-12-06 00:00:00

Expand stopwords with form/template words for all languages:
- Form instructions (please, fill, check, etc.)
- Form field labels (name, date, phone, address, etc.)
- Generic descriptors (important, other, various, etc.)
- Question words (which, what, when, etc.)
- Polite/formal phrases
- Common verbs that add no semantic value in documents

Also adds configuration values for:
- Spell check thresholds (keyword extraction)
- Entity frequency penalty (entity quality)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '037_expand_stopwords'
down_revision = '036_tfidf_keywords'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== EXPAND STOPWORDS ====================

    # Add ~100 stopwords per language to filter out form/template words
    op.execute("""
        INSERT INTO stop_words (id, word, language_code, is_active, created_at)
        VALUES

        -- ========== GERMAN (de) - ~100 words ==========

        -- Form instructions
        (gen_random_uuid(), 'bitte', 'de', true, NOW()),
        (gen_random_uuid(), 'falls', 'de', true, NOW()),
        (gen_random_uuid(), 'siehe', 'de', true, NOW()),
        (gen_random_uuid(), 'ausfüllen', 'de', true, NOW()),
        (gen_random_uuid(), 'füllen', 'de', true, NOW()),
        (gen_random_uuid(), 'kreuzen', 'de', true, NOW()),
        (gen_random_uuid(), 'ankreuzen', 'de', true, NOW()),
        (gen_random_uuid(), 'nennen', 'de', true, NOW()),
        (gen_random_uuid(), 'widmen', 'de', true, NOW()),
        (gen_random_uuid(), 'eintragen', 'de', true, NOW()),
        (gen_random_uuid(), 'angeben', 'de', true, NOW()),

        -- Form field labels
        (gen_random_uuid(), 'name', 'de', true, NOW()),
        (gen_random_uuid(), 'vorname', 'de', true, NOW()),
        (gen_random_uuid(), 'nachname', 'de', true, NOW()),
        (gen_random_uuid(), 'straße', 'de', true, NOW()),
        (gen_random_uuid(), 'strasse', 'de', true, NOW()),
        (gen_random_uuid(), 'hausnummer', 'de', true, NOW()),
        (gen_random_uuid(), 'plz', 'de', true, NOW()),
        (gen_random_uuid(), 'postleitzahl', 'de', true, NOW()),
        (gen_random_uuid(), 'wohnort', 'de', true, NOW()),
        (gen_random_uuid(), 'ort', 'de', true, NOW()),
        (gen_random_uuid(), 'telefon', 'de', true, NOW()),
        (gen_random_uuid(), 'telefonnummer', 'de', true, NOW()),
        (gen_random_uuid(), 'email', 'de', true, NOW()),
        (gen_random_uuid(), 'adresse', 'de', true, NOW()),
        (gen_random_uuid(), 'geburtsdatum', 'de', true, NOW()),
        (gen_random_uuid(), 'größe', 'de', true, NOW()),
        (gen_random_uuid(), 'gewicht', 'de', true, NOW()),
        (gen_random_uuid(), 'beruf', 'de', true, NOW()),
        (gen_random_uuid(), 'tätigkeit', 'de', true, NOW()),
        (gen_random_uuid(), 'ausgeübte', 'de', true, NOW()),
        (gen_random_uuid(), 'datum', 'de', true, NOW()),
        (gen_random_uuid(), 'unterschrift', 'de', true, NOW()),
        (gen_random_uuid(), 'nummer', 'de', true, NOW()),

        -- Generic descriptors
        (gen_random_uuid(), 'wichtig', 'de', true, NOW()),
        (gen_random_uuid(), 'wichtige', 'de', true, NOW()),
        (gen_random_uuid(), 'wichtigste', 'de', true, NOW()),
        (gen_random_uuid(), 'weitere', 'de', true, NOW()),
        (gen_random_uuid(), 'weiteres', 'de', true, NOW()),
        (gen_random_uuid(), 'sonstige', 'de', true, NOW()),
        (gen_random_uuid(), 'sonstiges', 'de', true, NOW()),
        (gen_random_uuid(), 'verschiedene', 'de', true, NOW()),
        (gen_random_uuid(), 'diverse', 'de', true, NOW()),
        (gen_random_uuid(), 'angaben', 'de', true, NOW()),
        (gen_random_uuid(), 'wert', 'de', true, NOW()),
        (gen_random_uuid(), 'werte', 'de', true, NOW()),

        -- Question/instruction words
        (gen_random_uuid(), 'welche', 'de', true, NOW()),
        (gen_random_uuid(), 'welcher', 'de', true, NOW()),
        (gen_random_uuid(), 'welches', 'de', true, NOW()),
        (gen_random_uuid(), 'wann', 'de', true, NOW()),
        (gen_random_uuid(), 'warum', 'de', true, NOW()),
        (gen_random_uuid(), 'wieso', 'de', true, NOW()),
        (gen_random_uuid(), 'weshalb', 'de', true, NOW()),

        -- Polite/formal
        (gen_random_uuid(), 'sehr', 'de', true, NOW()),
        (gen_random_uuid(), 'geehrte', 'de', true, NOW()),
        (gen_random_uuid(), 'geehrter', 'de', true, NOW()),
        (gen_random_uuid(), 'herzlich', 'de', true, NOW()),
        (gen_random_uuid(), 'willkommen', 'de', true, NOW()),
        (gen_random_uuid(), 'dank', 'de', true, NOW()),
        (gen_random_uuid(), 'danke', 'de', true, NOW()),
        (gen_random_uuid(), 'gerne', 'de', true, NOW()),
        (gen_random_uuid(), 'besten', 'de', true, NOW()),

        -- Measurement/time
        (gen_random_uuid(), 'seit', 'de', true, NOW()),
        (gen_random_uuid(), 'jahren', 'de', true, NOW()),
        (gen_random_uuid(), 'tagen', 'de', true, NOW()),
        (gen_random_uuid(), 'wochen', 'de', true, NOW()),
        (gen_random_uuid(), 'monaten', 'de', true, NOW()),
        (gen_random_uuid(), 'stunden', 'de', true, NOW()),
        (gen_random_uuid(), 'minuten', 'de', true, NOW()),
        (gen_random_uuid(), 'etwa', 'de', true, NOW()),
        (gen_random_uuid(), 'circa', 'de', true, NOW()),
        (gen_random_uuid(), 'ca', 'de', true, NOW()),

        -- Common verbs (no semantic value)
        (gen_random_uuid(), 'gibt', 'de', true, NOW()),
        (gen_random_uuid(), 'geben', 'de', true, NOW()),
        (gen_random_uuid(), 'nehmen', 'de', true, NOW()),
        (gen_random_uuid(), 'kommen', 'de', true, NOW()),
        (gen_random_uuid(), 'haben', 'de', true, NOW()),
        (gen_random_uuid(), 'können', 'de', true, NOW()),
        (gen_random_uuid(), 'benötigen', 'de', true, NOW()),
        (gen_random_uuid(), 'vorlegen', 'de', true, NOW()),
        (gen_random_uuid(), 'sind', 'de', true, NOW()),
        (gen_random_uuid(), 'werden', 'de', true, NOW()),
        (gen_random_uuid(), 'wurden', 'de', true, NOW()),
        (gen_random_uuid(), 'wird', 'de', true, NOW()),
        (gen_random_uuid(), 'worden', 'de', true, NOW()),
        (gen_random_uuid(), 'sein', 'de', true, NOW()),
        (gen_random_uuid(), 'war', 'de', true, NOW()),
        (gen_random_uuid(), 'waren', 'de', true, NOW()),

        -- Document/form specific
        (gen_random_uuid(), 'patient', 'de', true, NOW()),
        (gen_random_uuid(), 'patientin', 'de', true, NOW()),
        (gen_random_uuid(), 'behandlung', 'de', true, NOW()),
        (gen_random_uuid(), 'liste', 'de', true, NOW()),
        (gen_random_uuid(), 'tabelle', 'de', true, NOW()),
        (gen_random_uuid(), 'erforderlich', 'de', true, NOW()),
        (gen_random_uuid(), 'vertraulich', 'de', true, NOW()),
        (gen_random_uuid(), 'selbstverständlich', 'de', true, NOW()),
        (gen_random_uuid(), 'behandelt', 'de', true, NOW()),
        (gen_random_uuid(), 'keine', 'de', true, NOW()),

        -- Abbreviations
        (gen_random_uuid(), 'bzw', 'de', true, NOW()),
        (gen_random_uuid(), 'usw', 'de', true, NOW()),
        (gen_random_uuid(), 'etc', 'de', true, NOW()),
        (gen_random_uuid(), 'inkl', 'de', true, NOW()),
        (gen_random_uuid(), 'exkl', 'de', true, NOW()),
        (gen_random_uuid(), 'ggf', 'de', true, NOW()),
        (gen_random_uuid(), 'evtl', 'de', true, NOW()),

        -- ========== ENGLISH (en) - ~100 words ==========

        -- Form instructions
        (gen_random_uuid(), 'please', 'en', true, NOW()),
        (gen_random_uuid(), 'fill', 'en', true, NOW()),
        (gen_random_uuid(), 'check', 'en', true, NOW()),
        (gen_random_uuid(), 'complete', 'en', true, NOW()),
        (gen_random_uuid(), 'provide', 'en', true, NOW()),
        (gen_random_uuid(), 'enter', 'en', true, NOW()),
        (gen_random_uuid(), 'specify', 'en', true, NOW()),
        (gen_random_uuid(), 'indicate', 'en', true, NOW()),
        (gen_random_uuid(), 'select', 'en', true, NOW()),

        -- Form field labels
        (gen_random_uuid(), 'name', 'en', true, NOW()),
        (gen_random_uuid(), 'firstname', 'en', true, NOW()),
        (gen_random_uuid(), 'lastname', 'en', true, NOW()),
        (gen_random_uuid(), 'street', 'en', true, NOW()),
        (gen_random_uuid(), 'address', 'en', true, NOW()),
        (gen_random_uuid(), 'city', 'en', true, NOW()),
        (gen_random_uuid(), 'zip', 'en', true, NOW()),
        (gen_random_uuid(), 'zipcode', 'en', true, NOW()),
        (gen_random_uuid(), 'postal', 'en', true, NOW()),
        (gen_random_uuid(), 'phone', 'en', true, NOW()),
        (gen_random_uuid(), 'telephone', 'en', true, NOW()),
        (gen_random_uuid(), 'email', 'en', true, NOW()),
        (gen_random_uuid(), 'date', 'en', true, NOW()),
        (gen_random_uuid(), 'birth', 'en', true, NOW()),
        (gen_random_uuid(), 'birthdate', 'en', true, NOW()),
        (gen_random_uuid(), 'height', 'en', true, NOW()),
        (gen_random_uuid(), 'weight', 'en', true, NOW()),
        (gen_random_uuid(), 'occupation', 'en', true, NOW()),
        (gen_random_uuid(), 'profession', 'en', true, NOW()),
        (gen_random_uuid(), 'signature', 'en', true, NOW()),
        (gen_random_uuid(), 'number', 'en', true, NOW()),

        -- Generic descriptors
        (gen_random_uuid(), 'important', 'en', true, NOW()),
        (gen_random_uuid(), 'additional', 'en', true, NOW()),
        (gen_random_uuid(), 'further', 'en', true, NOW()),
        (gen_random_uuid(), 'other', 'en', true, NOW()),
        (gen_random_uuid(), 'others', 'en', true, NOW()),
        (gen_random_uuid(), 'various', 'en', true, NOW()),
        (gen_random_uuid(), 'several', 'en', true, NOW()),
        (gen_random_uuid(), 'information', 'en', true, NOW()),
        (gen_random_uuid(), 'details', 'en', true, NOW()),
        (gen_random_uuid(), 'value', 'en', true, NOW()),
        (gen_random_uuid(), 'values', 'en', true, NOW()),

        -- Question words
        (gen_random_uuid(), 'which', 'en', true, NOW()),
        (gen_random_uuid(), 'what', 'en', true, NOW()),
        (gen_random_uuid(), 'when', 'en', true, NOW()),
        (gen_random_uuid(), 'where', 'en', true, NOW()),
        (gen_random_uuid(), 'why', 'en', true, NOW()),
        (gen_random_uuid(), 'how', 'en', true, NOW()),

        -- Polite/formal
        (gen_random_uuid(), 'dear', 'en', true, NOW()),
        (gen_random_uuid(), 'sincerely', 'en', true, NOW()),
        (gen_random_uuid(), 'regards', 'en', true, NOW()),
        (gen_random_uuid(), 'thank', 'en', true, NOW()),
        (gen_random_uuid(), 'thanks', 'en', true, NOW()),
        (gen_random_uuid(), 'welcome', 'en', true, NOW()),
        (gen_random_uuid(), 'best', 'en', true, NOW()),

        -- Measurement/time
        (gen_random_uuid(), 'since', 'en', true, NOW()),
        (gen_random_uuid(), 'years', 'en', true, NOW()),
        (gen_random_uuid(), 'days', 'en', true, NOW()),
        (gen_random_uuid(), 'weeks', 'en', true, NOW()),
        (gen_random_uuid(), 'months', 'en', true, NOW()),
        (gen_random_uuid(), 'hours', 'en', true, NOW()),
        (gen_random_uuid(), 'minutes', 'en', true, NOW()),
        (gen_random_uuid(), 'approximately', 'en', true, NOW()),
        (gen_random_uuid(), 'approx', 'en', true, NOW()),
        (gen_random_uuid(), 'circa', 'en', true, NOW()),

        -- Common verbs
        (gen_random_uuid(), 'give', 'en', true, NOW()),
        (gen_random_uuid(), 'take', 'en', true, NOW()),
        (gen_random_uuid(), 'come', 'en', true, NOW()),
        (gen_random_uuid(), 'need', 'en', true, NOW()),
        (gen_random_uuid(), 'require', 'en', true, NOW()),
        (gen_random_uuid(), 'submit', 'en', true, NOW()),

        -- Document specific
        (gen_random_uuid(), 'patient', 'en', true, NOW()),
        (gen_random_uuid(), 'treatment', 'en', true, NOW()),
        (gen_random_uuid(), 'list', 'en', true, NOW()),
        (gen_random_uuid(), 'table', 'en', true, NOW()),
        (gen_random_uuid(), 'required', 'en', true, NOW()),
        (gen_random_uuid(), 'confidential', 'en', true, NOW()),
        (gen_random_uuid(), 'none', 'en', true, NOW()),

        -- Abbreviations
        (gen_random_uuid(), 'etc', 'en', true, NOW()),
        (gen_random_uuid(), 'incl', 'en', true, NOW()),
        (gen_random_uuid(), 'excl', 'en', true, NOW()),
        (gen_random_uuid(), 'approx', 'en', true, NOW()),

        -- ========== FRENCH (fr) - ~100 words ==========

        -- Form instructions
        (gen_random_uuid(), 'veuillez', 'fr', true, NOW()),
        (gen_random_uuid(), 'remplir', 'fr', true, NOW()),
        (gen_random_uuid(), 'cocher', 'fr', true, NOW()),
        (gen_random_uuid(), 'indiquer', 'fr', true, NOW()),
        (gen_random_uuid(), 'fournir', 'fr', true, NOW()),
        (gen_random_uuid(), 'préciser', 'fr', true, NOW()),
        (gen_random_uuid(), 'saisir', 'fr', true, NOW()),

        -- Form field labels
        (gen_random_uuid(), 'nom', 'fr', true, NOW()),
        (gen_random_uuid(), 'prénom', 'fr', true, NOW()),
        (gen_random_uuid(), 'prenom', 'fr', true, NOW()),
        (gen_random_uuid(), 'rue', 'fr', true, NOW()),
        (gen_random_uuid(), 'adresse', 'fr', true, NOW()),
        (gen_random_uuid(), 'ville', 'fr', true, NOW()),
        (gen_random_uuid(), 'code', 'fr', true, NOW()),
        (gen_random_uuid(), 'postal', 'fr', true, NOW()),
        (gen_random_uuid(), 'téléphone', 'fr', true, NOW()),
        (gen_random_uuid(), 'telephone', 'fr', true, NOW()),
        (gen_random_uuid(), 'email', 'fr', true, NOW()),
        (gen_random_uuid(), 'courriel', 'fr', true, NOW()),
        (gen_random_uuid(), 'date', 'fr', true, NOW()),
        (gen_random_uuid(), 'naissance', 'fr', true, NOW()),
        (gen_random_uuid(), 'taille', 'fr', true, NOW()),
        (gen_random_uuid(), 'poids', 'fr', true, NOW()),
        (gen_random_uuid(), 'profession', 'fr', true, NOW()),
        (gen_random_uuid(), 'métier', 'fr', true, NOW()),
        (gen_random_uuid(), 'signature', 'fr', true, NOW()),
        (gen_random_uuid(), 'numéro', 'fr', true, NOW()),
        (gen_random_uuid(), 'numero', 'fr', true, NOW()),

        -- Generic descriptors
        (gen_random_uuid(), 'important', 'fr', true, NOW()),
        (gen_random_uuid(), 'importante', 'fr', true, NOW()),
        (gen_random_uuid(), 'importants', 'fr', true, NOW()),
        (gen_random_uuid(), 'supplémentaire', 'fr', true, NOW()),
        (gen_random_uuid(), 'autre', 'fr', true, NOW()),
        (gen_random_uuid(), 'autres', 'fr', true, NOW()),
        (gen_random_uuid(), 'divers', 'fr', true, NOW()),
        (gen_random_uuid(), 'diverses', 'fr', true, NOW()),
        (gen_random_uuid(), 'plusieurs', 'fr', true, NOW()),
        (gen_random_uuid(), 'informations', 'fr', true, NOW()),
        (gen_random_uuid(), 'renseignements', 'fr', true, NOW()),
        (gen_random_uuid(), 'valeur', 'fr', true, NOW()),
        (gen_random_uuid(), 'valeurs', 'fr', true, NOW()),

        -- Question words
        (gen_random_uuid(), 'quel', 'fr', true, NOW()),
        (gen_random_uuid(), 'quelle', 'fr', true, NOW()),
        (gen_random_uuid(), 'quels', 'fr', true, NOW()),
        (gen_random_uuid(), 'quelles', 'fr', true, NOW()),
        (gen_random_uuid(), 'quoi', 'fr', true, NOW()),
        (gen_random_uuid(), 'quand', 'fr', true, NOW()),
        (gen_random_uuid(), 'où', 'fr', true, NOW()),
        (gen_random_uuid(), 'pourquoi', 'fr', true, NOW()),
        (gen_random_uuid(), 'comment', 'fr', true, NOW()),

        -- Polite/formal
        (gen_random_uuid(), 'cher', 'fr', true, NOW()),
        (gen_random_uuid(), 'chère', 'fr', true, NOW()),
        (gen_random_uuid(), 'madame', 'fr', true, NOW()),
        (gen_random_uuid(), 'monsieur', 'fr', true, NOW()),
        (gen_random_uuid(), 'merci', 'fr', true, NOW()),
        (gen_random_uuid(), 'remerciements', 'fr', true, NOW()),
        (gen_random_uuid(), 'bienvenue', 'fr', true, NOW()),
        (gen_random_uuid(), 'cordialement', 'fr', true, NOW()),
        (gen_random_uuid(), 'sincèrement', 'fr', true, NOW()),

        -- Measurement/time
        (gen_random_uuid(), 'depuis', 'fr', true, NOW()),
        (gen_random_uuid(), 'ans', 'fr', true, NOW()),
        (gen_random_uuid(), 'jours', 'fr', true, NOW()),
        (gen_random_uuid(), 'semaines', 'fr', true, NOW()),
        (gen_random_uuid(), 'mois', 'fr', true, NOW()),
        (gen_random_uuid(), 'heures', 'fr', true, NOW()),
        (gen_random_uuid(), 'minutes', 'fr', true, NOW()),
        (gen_random_uuid(), 'environ', 'fr', true, NOW()),
        (gen_random_uuid(), 'approximativement', 'fr', true, NOW()),

        -- Common verbs
        (gen_random_uuid(), 'donner', 'fr', true, NOW()),
        (gen_random_uuid(), 'prendre', 'fr', true, NOW()),
        (gen_random_uuid(), 'venir', 'fr', true, NOW()),
        (gen_random_uuid(), 'avoir', 'fr', true, NOW()),
        (gen_random_uuid(), 'être', 'fr', true, NOW()),
        (gen_random_uuid(), 'besoin', 'fr', true, NOW()),
        (gen_random_uuid(), 'nécessaire', 'fr', true, NOW()),

        -- Document specific
        (gen_random_uuid(), 'patient', 'fr', true, NOW()),
        (gen_random_uuid(), 'patiente', 'fr', true, NOW()),
        (gen_random_uuid(), 'traitement', 'fr', true, NOW()),
        (gen_random_uuid(), 'liste', 'fr', true, NOW()),
        (gen_random_uuid(), 'tableau', 'fr', true, NOW()),
        (gen_random_uuid(), 'obligatoire', 'fr', true, NOW()),
        (gen_random_uuid(), 'confidentiel', 'fr', true, NOW()),
        (gen_random_uuid(), 'aucun', 'fr', true, NOW()),
        (gen_random_uuid(), 'aucune', 'fr', true, NOW()),

        -- Abbreviations
        (gen_random_uuid(), 'etc', 'fr', true, NOW()),

        -- ========== RUSSIAN (ru) - ~100 words ==========

        -- Form instructions
        (gen_random_uuid(), 'пожалуйста', 'ru', true, NOW()),
        (gen_random_uuid(), 'заполните', 'ru', true, NOW()),
        (gen_random_uuid(), 'укажите', 'ru', true, NOW()),
        (gen_random_uuid(), 'отметьте', 'ru', true, NOW()),
        (gen_random_uuid(), 'введите', 'ru', true, NOW()),
        (gen_random_uuid(), 'укажите', 'ru', true, NOW()),

        -- Form field labels
        (gen_random_uuid(), 'имя', 'ru', true, NOW()),
        (gen_random_uuid(), 'фамилия', 'ru', true, NOW()),
        (gen_random_uuid(), 'отчество', 'ru', true, NOW()),
        (gen_random_uuid(), 'улица', 'ru', true, NOW()),
        (gen_random_uuid(), 'адрес', 'ru', true, NOW()),
        (gen_random_uuid(), 'город', 'ru', true, NOW()),
        (gen_random_uuid(), 'индекс', 'ru', true, NOW()),
        (gen_random_uuid(), 'телефон', 'ru', true, NOW()),
        (gen_random_uuid(), 'почта', 'ru', true, NOW()),
        (gen_random_uuid(), 'дата', 'ru', true, NOW()),
        (gen_random_uuid(), 'рождения', 'ru', true, NOW()),
        (gen_random_uuid(), 'рост', 'ru', true, NOW()),
        (gen_random_uuid(), 'вес', 'ru', true, NOW()),
        (gen_random_uuid(), 'профессия', 'ru', true, NOW()),
        (gen_random_uuid(), 'подпись', 'ru', true, NOW()),
        (gen_random_uuid(), 'номер', 'ru', true, NOW()),

        -- Generic descriptors
        (gen_random_uuid(), 'важный', 'ru', true, NOW()),
        (gen_random_uuid(), 'важная', 'ru', true, NOW()),
        (gen_random_uuid(), 'важные', 'ru', true, NOW()),
        (gen_random_uuid(), 'дополнительный', 'ru', true, NOW()),
        (gen_random_uuid(), 'дополнительная', 'ru', true, NOW()),
        (gen_random_uuid(), 'другой', 'ru', true, NOW()),
        (gen_random_uuid(), 'другая', 'ru', true, NOW()),
        (gen_random_uuid(), 'другие', 'ru', true, NOW()),
        (gen_random_uuid(), 'различные', 'ru', true, NOW()),
        (gen_random_uuid(), 'несколько', 'ru', true, NOW()),
        (gen_random_uuid(), 'информация', 'ru', true, NOW()),
        (gen_random_uuid(), 'сведения', 'ru', true, NOW()),
        (gen_random_uuid(), 'значение', 'ru', true, NOW()),
        (gen_random_uuid(), 'значения', 'ru', true, NOW()),

        -- Question words
        (gen_random_uuid(), 'какой', 'ru', true, NOW()),
        (gen_random_uuid(), 'какая', 'ru', true, NOW()),
        (gen_random_uuid(), 'какие', 'ru', true, NOW()),
        (gen_random_uuid(), 'что', 'ru', true, NOW()),
        (gen_random_uuid(), 'когда', 'ru', true, NOW()),
        (gen_random_uuid(), 'где', 'ru', true, NOW()),
        (gen_random_uuid(), 'почему', 'ru', true, NOW()),
        (gen_random_uuid(), 'как', 'ru', true, NOW()),

        -- Polite/formal
        (gen_random_uuid(), 'уважаемый', 'ru', true, NOW()),
        (gen_random_uuid(), 'уважаемая', 'ru', true, NOW()),
        (gen_random_uuid(), 'спасибо', 'ru', true, NOW()),
        (gen_random_uuid(), 'благодарность', 'ru', true, NOW()),
        (gen_random_uuid(), 'добро', 'ru', true, NOW()),
        (gen_random_uuid(), 'пожаловать', 'ru', true, NOW()),

        -- Measurement/time
        (gen_random_uuid(), 'года', 'ru', true, NOW()),
        (gen_random_uuid(), 'лет', 'ru', true, NOW()),
        (gen_random_uuid(), 'дней', 'ru', true, NOW()),
        (gen_random_uuid(), 'недель', 'ru', true, NOW()),
        (gen_random_uuid(), 'месяцев', 'ru', true, NOW()),
        (gen_random_uuid(), 'часов', 'ru', true, NOW()),
        (gen_random_uuid(), 'минут', 'ru', true, NOW()),
        (gen_random_uuid(), 'примерно', 'ru', true, NOW()),
        (gen_random_uuid(), 'приблизительно', 'ru', true, NOW()),

        -- Common verbs
        (gen_random_uuid(), 'дать', 'ru', true, NOW()),
        (gen_random_uuid(), 'взять', 'ru', true, NOW()),
        (gen_random_uuid(), 'прийти', 'ru', true, NOW()),
        (gen_random_uuid(), 'иметь', 'ru', true, NOW()),
        (gen_random_uuid(), 'быть', 'ru', true, NOW()),
        (gen_random_uuid(), 'нужно', 'ru', true, NOW()),
        (gen_random_uuid(), 'необходимо', 'ru', true, NOW()),

        -- Document specific
        (gen_random_uuid(), 'пациент', 'ru', true, NOW()),
        (gen_random_uuid(), 'пациентка', 'ru', true, NOW()),
        (gen_random_uuid(), 'лечение', 'ru', true, NOW()),
        (gen_random_uuid(), 'список', 'ru', true, NOW()),
        (gen_random_uuid(), 'таблица', 'ru', true, NOW()),
        (gen_random_uuid(), 'обязательный', 'ru', true, NOW()),
        (gen_random_uuid(), 'конфиденциальный', 'ru', true, NOW()),
        (gen_random_uuid(), 'нет', 'ru', true, NOW()),
        (gen_random_uuid(), 'никакой', 'ru', true, NOW())

        ON CONFLICT (word, language_code) DO NOTHING
    """)

    # ==================== ADD CONFIG VALUES ====================

    # Add keyword extraction config values for spell check thresholds
    op.execute("""
        INSERT INTO keyword_extraction_config (config_key, config_value, category, description, min_value, max_value)
        VALUES
        -- Spell check configuration
        ('spell_check_enabled', 1.0, 'feature', 'Enable spell check filtering (1.0=on, 0.0=off)', 0.0, 1.0),
        ('spell_check_min_frequency', 1.0, 'threshold', 'Min frequency to bypass spell check (domain terms)', 1.0, 3.0),
        ('spell_check_frequency_multiplier', 2.0, 'algorithm', 'Frequency multiplier for spell check bypass (DEPRECATED - use spell_check_min_frequency)', 1.0, 3.0),

        -- Keyword extraction thresholds
        ('min_frequency_default', 1.0, 'threshold', 'Default minimum keyword frequency', 1.0, 3.0),
        ('min_frequency_short_doc_threshold', 200.0, 'threshold', 'Token count below which doc is considered short', 100.0, 500.0),
        ('max_keywords_default', 50.0, 'threshold', 'Maximum keywords to extract', 20.0, 100.0)

        ON CONFLICT (config_key) DO NOTHING
    """)

    # Add entity quality config values for frequency-based penalty
    op.execute("""
        INSERT INTO entity_quality_config (config_key, config_value, category, description, min_value, max_value)
        VALUES
        -- Frequency-based penalties (using global_corpus_stats)
        ('freq_check_enabled', 1.0, 'feature', 'Enable frequency-based entity filtering (1.0=on, 0.0=off)', 0.0, 1.0),
        ('freq_very_common_threshold', 700.0, 'threshold', 'Document count above which word is very common (>70% docs)', 500.0, 900.0),
        ('freq_common_threshold', 500.0, 'threshold', 'Document count above which word is common (>50% docs)', 300.0, 700.0),
        ('freq_very_common_penalty', 0.15, 'entity_type', 'Penalty for entities matching very common words (e.g., NAME, PATIENT)', 0.05, 0.3),
        ('freq_common_penalty', 0.5, 'entity_type', 'Penalty for entities matching common words', 0.3, 0.7),
        ('freq_corpus_total_docs', 1000.0, 'algorithm', 'Total documents in global corpus (for percentage calc)', 1000.0, 1000.0)

        ON CONFLICT (config_key) DO NOTHING
    """)


def downgrade():
    # Remove added stopwords (can't easily target specific ones, so this is approximate)
    # In practice, downgrade should rarely be used for stopwords
    op.execute("""
        DELETE FROM stop_words
        WHERE word IN (
            -- German sample
            'bitte', 'falls', 'keine', 'gibt', 'beruf', 'wichtige', 'angaben', 'ca',
            -- English sample
            'please', 'fill', 'check', 'occupation', 'value', 'values',
            -- French sample
            'veuillez', 'remplir', 'cocher', 'profession', 'valeur', 'valeurs',
            -- Russian sample
            'пожалуйста', 'заполните', 'профессия', 'значение'
        )
    """)

    # Remove config values
    op.execute("""
        DELETE FROM keyword_extraction_config
        WHERE config_key IN (
            'spell_check_enabled',
            'spell_check_min_frequency',
            'spell_check_frequency_multiplier',
            'min_frequency_default',
            'min_frequency_short_doc_threshold',
            'max_keywords_default'
        )
    """)

    op.execute("""
        DELETE FROM entity_quality_config
        WHERE config_key IN (
            'freq_check_enabled',
            'freq_very_common_threshold',
            'freq_common_threshold',
            'freq_very_common_penalty',
            'freq_common_penalty',
            'freq_corpus_total_docs'
        )
    """)
