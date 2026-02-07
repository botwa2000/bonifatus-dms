"""add date patterns for FR, TR, ES, PT, IT languages

Revision ID: 054_add_date_patterns_for_new_languages
Revises: 053_add_tr_es_pt_it_languages
Create Date: 2026-02-07 00:00:00.000000

Adds date_patterns, month_names, and date_type_keywords system_settings entries
for French, Turkish, Spanish, Portuguese, and Italian.

Previously only EN, DE, RU had date extraction support (populated via init_date_patterns.py).
This migration brings all 8 supported languages to parity.
"""
from alembic import op
from sqlalchemy import text
import json
import uuid

# revision identifiers, used by Alembic.
revision = '054_add_date_patterns_for_new_languages'
down_revision = '053_add_tr_es_pt_it_languages'
branch_labels = None
depends_on = None

LANGUAGES = ['fr', 'tr', 'es', 'pt', 'it']

# ============================================================
# DATE PATTERNS
# Each entry: [regex_pattern, format_type]
# format_type: ymd, dmy, mdy, dmy_named, mdy_named, my_named
# ============================================================

# Shared patterns used by all 5 languages (European date conventions)
SHARED_PATTERNS = [
    # Compact format: YYYYMMDD (file names, bank statements)
    [r'(\d{4})(\d{2})(\d{2})', 'ymd'],
    # ISO format: YYYY-MM-DD
    [r'(\d{4})-(\d{1,2})-(\d{1,2})', 'ymd'],
    # European dot: DD.MM.YYYY
    [r'(\d{1,2})\.(\d{1,2})\.(\d{4})', 'dmy'],
    # Slash: DD/MM/YYYY
    [r'(\d{1,2})/(\d{1,2})/(\d{4})', 'dmy'],
]

DATE_PATTERNS = {
    'fr': SHARED_PATTERNS + [
        # Named month: 15 janvier 2024
        [r'(\d{1,2})[\s]+(janvier|f\u00e9vrier|mars|avril|mai|juin|juillet|ao\u00fbt|septembre|octobre|novembre|d\u00e9cembre|janv|f\u00e9vr|avr|juil|sept|oct|nov|d\u00e9c)[\s,]+(\d{4})', 'dmy_named'],
        # Month-year: janvier 2024
        [r'(janvier|f\u00e9vrier|mars|avril|mai|juin|juillet|ao\u00fbt|septembre|octobre|novembre|d\u00e9cembre|janv|f\u00e9vr|avr|juil|sept|oct|nov|d\u00e9c)[\s,]+(\d{4})', 'my_named'],
        # Dash: DD-MM-YYYY
        [r'(\d{1,2})-(\d{1,2})-(\d{4})', 'dmy'],
    ],
    'tr': SHARED_PATTERNS + [
        # Named month: 15 Ocak 2024
        [r'(\d{1,2})[\s]+(Ocak|\u015eubat|Mart|Nisan|May\u0131s|Haziran|Temmuz|A\u011fustos|Eyl\u00fcl|Ekim|Kas\u0131m|Aral\u0131k|Oca|\u015eub|Mar|Nis|May|Haz|Tem|A\u011fu|Eyl|Eki|Kas|Ara)[\s,]+(\d{4})', 'dmy_named'],
        # Month-year: Ocak 2024 / KASIM 2022
        [r'(Ocak|\u015eubat|Mart|Nisan|May\u0131s|Haziran|Temmuz|A\u011fustos|Eyl\u00fcl|Ekim|Kas\u0131m|Aral\u0131k|Oca|\u015eub|Mar|Nis|May|Haz|Tem|A\u011fu|Eyl|Eki|Kas|Ara)[\s,]+(\d{4})', 'my_named'],
        # Dash: DD-MM-YYYY
        [r'(\d{1,2})-(\d{1,2})-(\d{4})', 'dmy'],
    ],
    'es': SHARED_PATTERNS + [
        # Named month: 15 de enero de 2024
        [r'(\d{1,2})[\s]+(?:de[\s]+)?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|ene|feb|mar|abr|may|jun|jul|ago|sep|sept|oct|nov|dic)[\s]+(?:de[\s]+)?(\d{4})', 'dmy_named'],
        # Month-year: enero de 2024
        [r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|ene|feb|mar|abr|may|jun|jul|ago|sep|sept|oct|nov|dic)[\s]+(?:de[\s]+)?(\d{4})', 'my_named'],
        # Dash: DD-MM-YYYY
        [r'(\d{1,2})-(\d{1,2})-(\d{4})', 'dmy'],
    ],
    'pt': SHARED_PATTERNS + [
        # Named month: 15 de janeiro de 2024
        [r'(\d{1,2})[\s]+(?:de[\s]+)?(janeiro|fevereiro|mar\u00e7o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[\s]+(?:de[\s]+)?(\d{4})', 'dmy_named'],
        # Month-year: janeiro de 2024
        [r'(janeiro|fevereiro|mar\u00e7o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[\s]+(?:de[\s]+)?(\d{4})', 'my_named'],
        # Dash: DD-MM-YYYY
        [r'(\d{1,2})-(\d{1,2})-(\d{4})', 'dmy'],
    ],
    'it': SHARED_PATTERNS + [
        # Named month: 15 gennaio 2024
        [r'(\d{1,2})[\s]+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre|gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)[\s,]+(\d{4})', 'dmy_named'],
        # Month-year: gennaio 2024
        [r'(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre|gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)[\s,]+(\d{4})', 'my_named'],
        # Dash: DD-MM-YYYY
        [r'(\d{1,2})-(\d{1,2})-(\d{4})', 'dmy'],
    ],
}

# ============================================================
# MONTH NAMES -> number mapping (lowercase)
# ============================================================

MONTH_NAMES = {
    'fr': {
        "janvier": 1, "janv": 1,
        "f\u00e9vrier": 2, "f\u00e9vr": 2,
        "mars": 3,
        "avril": 4, "avr": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7, "juil": 7,
        "ao\u00fbt": 8,
        "septembre": 9, "sept": 9,
        "octobre": 10, "oct": 10,
        "novembre": 11, "nov": 11,
        "d\u00e9cembre": 12, "d\u00e9c": 12,
    },
    'tr': {
        "ocak": 1, "oca": 1,
        "\u015fubat": 2, "\u015fub": 2,
        "mart": 3, "mar": 3,
        "nisan": 4, "nis": 4,
        "may\u0131s": 5, "may": 5,
        "haziran": 6, "haz": 6,
        "temmuz": 7, "tem": 7,
        "a\u011fustos": 8, "a\u011fu": 8,
        "eyl\u00fcl": 9, "eyl": 9,
        "ekim": 10, "eki": 10,
        "kas\u0131m": 11, "kas": 11,
        "aral\u0131k": 12, "ara": 12,
    },
    'es': {
        "enero": 1, "ene": 1,
        "febrero": 2, "feb": 2,
        "marzo": 3, "mar": 3,
        "abril": 4, "abr": 4,
        "mayo": 5, "may": 5,
        "junio": 6, "jun": 6,
        "julio": 7, "jul": 7,
        "agosto": 8, "ago": 8,
        "septiembre": 9, "sep": 9, "sept": 9,
        "octubre": 10, "oct": 10,
        "noviembre": 11, "nov": 11,
        "diciembre": 12, "dic": 12,
    },
    'pt': {
        "janeiro": 1, "jan": 1,
        "fevereiro": 2, "fev": 2,
        "mar\u00e7o": 3, "mar": 3,
        "abril": 4, "abr": 4,
        "maio": 5, "mai": 5,
        "junho": 6, "jun": 6,
        "julho": 7, "jul": 7,
        "agosto": 8, "ago": 8,
        "setembro": 9, "set": 9,
        "outubro": 10, "out": 10,
        "novembro": 11, "nov": 11,
        "dezembro": 12, "dez": 12,
    },
    'it': {
        "gennaio": 1, "gen": 1,
        "febbraio": 2, "feb": 2,
        "marzo": 3, "mar": 3,
        "aprile": 4, "apr": 4,
        "maggio": 5, "mag": 5,
        "giugno": 6, "giu": 6,
        "luglio": 7, "lug": 7,
        "agosto": 8, "ago": 8,
        "settembre": 9, "set": 9,
        "ottobre": 10, "ott": 10,
        "novembre": 11, "nov": 11,
        "dicembre": 12, "dic": 12,
    },
}

# ============================================================
# DATE TYPE KEYWORDS
# Keywords near dates to classify them (invoice date, due date, etc.)
# ============================================================

DATE_TYPE_KEYWORDS = {
    'fr': {
        "statement_date": [
            "relev\u00e9 de compte", "date du relev\u00e9", "solde au",
            "situation au", "arr\u00eat\u00e9 au", "p\u00e9riode du",
        ],
        "invoice_date": [
            "date de facture", "facture du", "factur\u00e9 le",
            "date d'\u00e9mission", "date de facturation",
        ],
        "due_date": [
            "date d'\u00e9ch\u00e9ance", "\u00e9ch\u00e9ance", "payable avant",
            "\u00e0 payer avant", "date limite de paiement", "exigible le",
        ],
        "effective_date": [
            "date d'effet", "en vigueur \u00e0 partir du", "prend effet le",
            "date de d\u00e9but", "commence le",
        ],
        "signature_date": [
            "date de signature", "sign\u00e9 le", "fait \u00e0",
            "date de conclusion",
        ],
        "tax_year": [
            "ann\u00e9e fiscale", "exercice fiscal", "ann\u00e9e d'imposition",
            "p\u00e9riode fiscale", "pour l'ann\u00e9e",
        ],
    },
    'tr': {
        "statement_date": [
            "hesap \u00f6zeti", "ekstre tarihi", "hesap d\u00f6k\u00fcm\u00fc",
            "bakiye tarihi", "hesap durumu",
        ],
        "invoice_date": [
            "fatura tarihi", "fatura d\u00f6nemi", "d\u00fczenleme tarihi",
            "fatura no", "belge tarihi",
        ],
        "due_date": [
            "son \u00f6deme tarihi", "vade tarihi", "\u00f6deme tarihi",
            "\u00f6deme son g\u00fcn\u00fc", "vade sonu",
        ],
        "effective_date": [
            "y\u00fcr\u00fcrl\u00fck tarihi", "ge\u00e7erlilik ba\u015flang\u0131c\u0131",
            "ba\u015flama tarihi", "ge\u00e7erli oldu\u011fu tarih",
        ],
        "signature_date": [
            "imza tarihi", "imzaland\u0131\u011f\u0131 tarih", "s\u00f6zle\u015fme tarihi",
        ],
        "tax_year": [
            "vergi y\u0131l\u0131", "mali y\u0131l", "vergi d\u00f6nemi",
            "beyanname d\u00f6nemi",
        ],
    },
    'es': {
        "statement_date": [
            "fecha del extracto", "extracto bancario", "saldo a",
            "estado de cuenta", "per\u00edodo del extracto",
        ],
        "invoice_date": [
            "fecha de factura", "fecha factura", "facturado el",
            "fecha de emisi\u00f3n", "fecha de expedici\u00f3n",
        ],
        "due_date": [
            "fecha de vencimiento", "vencimiento", "pagadero antes de",
            "fecha l\u00edmite de pago", "plazo de pago",
        ],
        "effective_date": [
            "fecha de vigencia", "vigente desde", "en vigor desde",
            "fecha de inicio", "comienza el",
        ],
        "signature_date": [
            "fecha de firma", "firmado el", "suscrito el",
            "otorgado el",
        ],
        "tax_year": [
            "a\u00f1o fiscal", "ejercicio fiscal", "per\u00edodo impositivo",
            "declaraci\u00f3n del a\u00f1o",
        ],
    },
    'pt': {
        "statement_date": [
            "data do extrato", "extrato banc\u00e1rio", "saldo em",
            "situa\u00e7\u00e3o em", "per\u00edodo do extrato",
        ],
        "invoice_date": [
            "data da fatura", "fatura de", "faturado em",
            "data de emiss\u00e3o",
        ],
        "due_date": [
            "data de vencimento", "vencimento", "pag\u00e1vel at\u00e9",
            "prazo de pagamento", "data limite de pagamento",
        ],
        "effective_date": [
            "data de vig\u00eancia", "em vigor desde", "data de in\u00edcio",
            "entra em vigor em",
        ],
        "signature_date": [
            "data de assinatura", "assinado em", "outorgado em",
        ],
        "tax_year": [
            "ano fiscal", "exerc\u00edcio fiscal", "per\u00edodo de tributa\u00e7\u00e3o",
            "declara\u00e7\u00e3o do ano",
        ],
    },
    'it': {
        "statement_date": [
            "data dell'estratto", "estratto conto", "saldo al",
            "situazione al", "periodo dell'estratto",
        ],
        "invoice_date": [
            "data fattura", "data della fattura", "fatturato il",
            "data di emissione",
        ],
        "due_date": [
            "data di scadenza", "scadenza", "pagabile entro",
            "termine di pagamento", "data ultimo pagamento",
        ],
        "effective_date": [
            "data di decorrenza", "in vigore dal", "data di inizio",
            "decorre dal",
        ],
        "signature_date": [
            "data di firma", "firmato il", "sottoscritto il",
            "stipulato il",
        ],
        "tax_year": [
            "anno fiscale", "esercizio fiscale", "periodo d'imposta",
            "dichiarazione dell'anno",
        ],
    },
}


def upgrade():
    conn = op.get_bind()

    print("\n=== Adding Date Patterns for FR, TR, ES, PT, IT ===\n")

    setting_count = 0

    for lang in LANGUAGES:
        # 1. date_patterns_{lang}
        patterns_value = json.dumps(DATE_PATTERNS[lang])
        conn.execute(text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, category, is_public, created_at, updated_at)
            VALUES (:id, :key, :value, 'json', :desc, 'date_extraction', false, now(), now())
            ON CONFLICT (setting_key) DO UPDATE SET
                setting_value = EXCLUDED.setting_value,
                updated_at = now()
        """), {
            'id': str(uuid.uuid4()),
            'key': f'date_patterns_{lang}',
            'value': patterns_value,
            'desc': f'Date regex patterns for {lang.upper()} (format: [pattern, format_type])',
        })
        setting_count += 1
        print(f"   + date_patterns_{lang} ({len(DATE_PATTERNS[lang])} patterns)")

        # 2. month_names_{lang}
        months_value = json.dumps(MONTH_NAMES[lang])
        conn.execute(text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, category, is_public, created_at, updated_at)
            VALUES (:id, :key, :value, 'json', :desc, 'date_extraction', false, now(), now())
            ON CONFLICT (setting_key) DO UPDATE SET
                setting_value = EXCLUDED.setting_value,
                updated_at = now()
        """), {
            'id': str(uuid.uuid4()),
            'key': f'month_names_{lang}',
            'value': months_value,
            'desc': f'{lang.upper()} month name to number mapping',
        })
        setting_count += 1
        print(f"   + month_names_{lang} ({len(MONTH_NAMES[lang])} entries)")

        # 3. date_type_keywords_{lang}
        keywords_value = json.dumps(DATE_TYPE_KEYWORDS[lang])
        conn.execute(text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, category, is_public, created_at, updated_at)
            VALUES (:id, :key, :value, 'json', :desc, 'date_extraction', false, now(), now())
            ON CONFLICT (setting_key) DO UPDATE SET
                setting_value = EXCLUDED.setting_value,
                updated_at = now()
        """), {
            'id': str(uuid.uuid4()),
            'key': f'date_type_keywords_{lang}',
            'value': keywords_value,
            'desc': f'{lang.upper()} keywords for date type identification',
        })
        setting_count += 1
        print(f"   + date_type_keywords_{lang} ({len(DATE_TYPE_KEYWORDS[lang])} types)")

    print(f"\n   Total system_settings rows added/updated: {setting_count}")
    print("\n\u2705 Migration 054 complete! Date extraction now supports: EN, DE, RU, FR, TR, ES, PT, IT")


def downgrade():
    conn = op.get_bind()

    print("\n=== Removing Date Patterns for FR, TR, ES, PT, IT ===\n")

    for lang in LANGUAGES:
        for prefix in ['date_patterns', 'month_names', 'date_type_keywords']:
            conn.execute(text("""
                DELETE FROM system_settings WHERE setting_key = :key
            """), {'key': f'{prefix}_{lang}'})

    print("\u2705 Migration 054 downgrade complete.")
