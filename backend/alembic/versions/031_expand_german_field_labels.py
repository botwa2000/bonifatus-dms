"""expand german field labels with common abbreviations

Revision ID: 031_expand_field_labels
Revises: 030_update_www_filter
Create Date: 2025-12-01 00:00:00

Add comprehensive German field labels including common abbreviations
that frequently appear in invoices, receipts, and business documents
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '031_expand_field_labels'
down_revision = '030_update_www_filter'
branch_labels = None
depends_on = None


def upgrade():
    # Add common German abbreviations and field labels
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        -- Common abbreviations
        ('de', 'Tel', 'Telephone abbreviation'),
        ('de', 'Tel.', 'Telephone abbreviation with period'),
        ('de', 'Fax', 'Fax abbreviation'),
        ('de', 'Fax.', 'Fax abbreviation with period'),
        ('de', 'Nr', 'Number abbreviation'),
        ('de', 'Nr.', 'Number abbreviation with period'),
        ('de', 'Str', 'Street abbreviation'),
        ('de', 'Str.', 'Street abbreviation with period'),

        -- Receipt/Invoice specific labels
        ('de', 'Beleg-Nr', 'Receipt number'),
        ('de', 'Beleg-Nr.', 'Receipt number with period'),
        ('de', 'Belegnummer', 'Receipt number (full)'),
        ('de', 'Rechnungs-Nr', 'Invoice number'),
        ('de', 'Rechnungs-Nr.', 'Invoice number with period'),
        ('de', 'Rechnungsnummer', 'Invoice number (full)'),
        ('de', 'Kunden-Nr', 'Customer number'),
        ('de', 'Kunden-Nr.', 'Customer number with period'),
        ('de', 'Kundennummer', 'Customer number (full)'),

        -- Date and time labels
        ('de', 'Datum', 'Date'),
        ('de', 'Uhrzeit', 'Time'),
        ('de', 'Zeit', 'Time (short)'),

        -- Amount labels
        ('de', 'Betrag', 'Amount'),
        ('de', 'Summe', 'Sum/Total'),
        ('de', 'Gesamt', 'Total'),
        ('de', 'Netto', 'Net amount'),
        ('de', 'Brutto', 'Gross amount'),
        ('de', 'Zwischensumme', 'Subtotal'),

        -- Tax labels
        ('de', 'USt', 'VAT abbreviation'),
        ('de', 'USt.', 'VAT abbreviation with period'),
        ('de', 'MwSt', 'VAT abbreviation (alt)'),
        ('de', 'MwSt.', 'VAT abbreviation with period (alt)'),
        ('de', 'Steuer', 'Tax'),
        ('de', 'Steuer-Nr', 'Tax number'),
        ('de', 'Steuernummer', 'Tax number (full)'),

        -- Payment labels
        ('de', 'Karte', 'Card'),
        ('de', 'EC-Karte', 'Debit card'),
        ('de', 'Kartennummer', 'Card number'),
        ('de', 'Karten-Nr', 'Card number abbrev'),
        ('de', 'Terminal', 'Terminal'),
        ('de', 'Terminal-ID', 'Terminal ID'),

        -- Authorization labels
        ('de', 'Autorisierung', 'Authorization'),
        ('de', 'Autorisierungscode', 'Authorization code'),
        ('de', 'Autorisierungsantwortcode', 'Authorization response code'),
        ('de', 'Trace', 'Trace'),
        ('de', 'Trace-Nr', 'Trace number'),

        -- Transaction labels
        ('de', 'Transaktion', 'Transaction'),
        ('de', 'Transaktions-Nr', 'Transaction number'),
        ('de', 'Transaktionsnummer', 'Transaction number (full)'),
        ('de', 'Vorgang', 'Process/Transaction'),
        ('de', 'Vorgangs-Nr', 'Process number'),

        -- Location labels
        ('de', 'Standort', 'Location'),
        ('de', 'Filiale', 'Branch'),
        ('de', 'Filialnummer', 'Branch number'),

        -- Signature labels
        ('de', 'Unterschrift', 'Signature'),
        ('de', 'Signatur', 'Signature'),

        -- Generic labels
        ('de', 'Code', 'Code'),
        ('de', 'ID', 'ID'),
        ('de', 'Kennung', 'Identifier'),
        ('de', 'Name', 'Name'),
        ('de', 'Typ', 'Type'),
        ('de', 'Art', 'Type/Kind')

        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # Add English field labels (comprehensive)
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        -- Common abbreviations
        ('en', 'Tel', 'Telephone abbreviation'),
        ('en', 'Tel.', 'Telephone abbreviation with period'),
        ('en', 'Phone', 'Phone'),
        ('en', 'Fax', 'Fax abbreviation'),
        ('en', 'Fax.', 'Fax abbreviation with period'),
        ('en', 'No', 'Number abbreviation'),
        ('en', 'No.', 'Number abbreviation with period'),
        ('en', 'Nr', 'Number abbreviation (German style)'),
        ('en', 'Nr.', 'Number abbreviation with period'),
        ('en', 'Ref', 'Reference'),
        ('en', 'Ref.', 'Reference with period'),
        ('en', 'St', 'Street abbreviation'),
        ('en', 'St.', 'Street abbreviation with period'),

        -- Receipt/Invoice specific labels
        ('en', 'Receipt No', 'Receipt number'),
        ('en', 'Receipt No.', 'Receipt number with period'),
        ('en', 'Receipt Number', 'Receipt number (full)'),
        ('en', 'Invoice No', 'Invoice number'),
        ('en', 'Invoice No.', 'Invoice number with period'),
        ('en', 'Invoice Number', 'Invoice number (full)'),
        ('en', 'Customer No', 'Customer number'),
        ('en', 'Customer No.', 'Customer number with period'),
        ('en', 'Customer Number', 'Customer number (full)'),
        ('en', 'Order No', 'Order number'),
        ('en', 'Order No.', 'Order number with period'),
        ('en', 'Order Number', 'Order number (full)'),

        -- Date and time labels
        ('en', 'Date', 'Date'),
        ('en', 'Time', 'Time'),
        ('en', 'Timestamp', 'Timestamp'),

        -- Amount labels
        ('en', 'Amount', 'Amount'),
        ('en', 'Total', 'Total'),
        ('en', 'Sum', 'Sum'),
        ('en', 'Subtotal', 'Subtotal'),
        ('en', 'Sub-total', 'Subtotal with hyphen'),
        ('en', 'Net', 'Net amount'),
        ('en', 'Gross', 'Gross amount'),

        -- Tax labels
        ('en', 'Tax', 'Tax'),
        ('en', 'VAT', 'VAT'),
        ('en', 'Sales Tax', 'Sales tax'),
        ('en', 'Tax ID', 'Tax identification'),
        ('en', 'Tax Number', 'Tax number'),
        ('en', 'TIN', 'Tax identification number'),
        ('en', 'EIN', 'Employer identification number'),

        -- Payment labels
        ('en', 'Card', 'Card'),
        ('en', 'Credit Card', 'Credit card'),
        ('en', 'Debit Card', 'Debit card'),
        ('en', 'Card Number', 'Card number'),
        ('en', 'Card No', 'Card number abbrev'),
        ('en', 'Card No.', 'Card number with period'),
        ('en', 'Terminal', 'Terminal'),
        ('en', 'Terminal ID', 'Terminal identification'),
        ('en', 'POS', 'Point of sale'),

        -- Authorization labels
        ('en', 'Authorization', 'Authorization'),
        ('en', 'Auth', 'Authorization abbreviation'),
        ('en', 'Auth Code', 'Authorization code'),
        ('en', 'Authorization Code', 'Authorization code (full)'),
        ('en', 'Approval Code', 'Approval code'),
        ('en', 'Response Code', 'Response code'),
        ('en', 'Trace', 'Trace'),
        ('en', 'Trace No', 'Trace number'),
        ('en', 'Trace Number', 'Trace number (full)'),

        -- Transaction labels
        ('en', 'Transaction', 'Transaction'),
        ('en', 'Transaction No', 'Transaction number'),
        ('en', 'Transaction Number', 'Transaction number (full)'),
        ('en', 'Reference', 'Reference'),
        ('en', 'Reference No', 'Reference number'),

        -- Location labels
        ('en', 'Location', 'Location'),
        ('en', 'Branch', 'Branch'),
        ('en', 'Store', 'Store'),
        ('en', 'Store No', 'Store number'),

        -- Signature labels
        ('en', 'Signature', 'Signature'),
        ('en', 'Signed', 'Signed'),

        -- Generic labels
        ('en', 'Code', 'Code'),
        ('en', 'ID', 'ID'),
        ('en', 'Identifier', 'Identifier'),
        ('en', 'Name', 'Name'),
        ('en', 'Type', 'Type'),
        ('en', 'Status', 'Status'),
        ('en', 'Description', 'Description'),
        ('en', 'Desc', 'Description abbreviation'),
        ('en', 'Desc.', 'Description with period')

        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # Add French field labels (comprehensive)
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        -- Common abbreviations
        ('fr', 'Tél', 'Telephone abbreviation'),
        ('fr', 'Tél.', 'Telephone abbreviation with period'),
        ('fr', 'Téléphone', 'Telephone (full)'),
        ('fr', 'Fax', 'Fax abbreviation'),
        ('fr', 'Fax.', 'Fax abbreviation with period'),
        ('fr', 'N°', 'Number abbreviation'),
        ('fr', 'Nº', 'Number abbreviation (alt)'),
        ('fr', 'No', 'Number abbreviation (short)'),
        ('fr', 'Numéro', 'Number (full)'),
        ('fr', 'Réf', 'Reference'),
        ('fr', 'Réf.', 'Reference with period'),
        ('fr', 'Référence', 'Reference (full)'),
        ('fr', 'Rue', 'Street'),

        -- Receipt/Invoice specific labels
        ('fr', 'N° de reçu', 'Receipt number'),
        ('fr', 'Numéro de reçu', 'Receipt number (full)'),
        ('fr', 'Reçu', 'Receipt'),
        ('fr', 'N° de facture', 'Invoice number'),
        ('fr', 'Numéro de facture', 'Invoice number (full)'),
        ('fr', 'Facture', 'Invoice'),
        ('fr', 'N° client', 'Customer number'),
        ('fr', 'Numéro client', 'Customer number (full)'),
        ('fr', 'Client', 'Customer'),
        ('fr', 'N° de commande', 'Order number'),
        ('fr', 'Numéro de commande', 'Order number (full)'),
        ('fr', 'Commande', 'Order'),

        -- Date and time labels
        ('fr', 'Date', 'Date'),
        ('fr', 'Heure', 'Time'),
        ('fr', 'Horodatage', 'Timestamp'),
        ('fr', 'Temps', 'Time (alt)'),

        -- Amount labels
        ('fr', 'Montant', 'Amount'),
        ('fr', 'Total', 'Total'),
        ('fr', 'Somme', 'Sum'),
        ('fr', 'Sous-total', 'Subtotal'),
        ('fr', 'Net', 'Net amount'),
        ('fr', 'Brut', 'Gross amount'),
        ('fr', 'TTC', 'Including tax'),
        ('fr', 'HT', 'Excluding tax'),

        -- Tax labels
        ('fr', 'TVA', 'VAT'),
        ('fr', 'Taxe', 'Tax'),
        ('fr', 'Impôt', 'Tax'),
        ('fr', 'N° TVA', 'VAT number'),
        ('fr', 'Numéro TVA', 'VAT number (full)'),
        ('fr', 'Identifiant fiscal', 'Tax identifier'),

        -- Payment labels
        ('fr', 'Carte', 'Card'),
        ('fr', 'Carte bancaire', 'Bank card'),
        ('fr', 'Carte de crédit', 'Credit card'),
        ('fr', 'Carte de débit', 'Debit card'),
        ('fr', 'N° de carte', 'Card number'),
        ('fr', 'Numéro de carte', 'Card number (full)'),
        ('fr', 'Terminal', 'Terminal'),
        ('fr', 'Terminal ID', 'Terminal ID'),
        ('fr', 'TPE', 'Electronic payment terminal'),

        -- Authorization labels
        ('fr', 'Autorisation', 'Authorization'),
        ('fr', 'Code d''autorisation', 'Authorization code'),
        ('fr', 'Code d''approbation', 'Approval code'),
        ('fr', 'Code de réponse', 'Response code'),
        ('fr', 'Trace', 'Trace'),
        ('fr', 'N° de trace', 'Trace number'),
        ('fr', 'Numéro de trace', 'Trace number (full)'),

        -- Transaction labels
        ('fr', 'Transaction', 'Transaction'),
        ('fr', 'N° de transaction', 'Transaction number'),
        ('fr', 'Numéro de transaction', 'Transaction number (full)'),
        ('fr', 'Opération', 'Operation'),
        ('fr', 'N° d''opération', 'Operation number'),

        -- Location labels
        ('fr', 'Emplacement', 'Location'),
        ('fr', 'Agence', 'Branch/Agency'),
        ('fr', 'Magasin', 'Store'),
        ('fr', 'N° de magasin', 'Store number'),
        ('fr', 'Succursale', 'Branch'),

        -- Signature labels
        ('fr', 'Signature', 'Signature'),
        ('fr', 'Signé', 'Signed'),

        -- Generic labels
        ('fr', 'Code', 'Code'),
        ('fr', 'ID', 'ID'),
        ('fr', 'Identifiant', 'Identifier'),
        ('fr', 'Nom', 'Name'),
        ('fr', 'Type', 'Type'),
        ('fr', 'Statut', 'Status'),
        ('fr', 'Description', 'Description'),
        ('fr', 'Desc', 'Description abbreviation'),
        ('fr', 'Desc.', 'Description with period')

        ON CONFLICT (language, label_text) DO NOTHING;
    """)

    # Add Russian field labels (comprehensive)
    op.execute("""
        INSERT INTO entity_field_labels (language, label_text, description) VALUES
        -- Common abbreviations
        ('ru', 'Тел', 'Telephone abbreviation'),
        ('ru', 'Тел.', 'Telephone abbreviation with period'),
        ('ru', 'Телефон', 'Telephone (full)'),
        ('ru', 'Факс', 'Fax'),
        ('ru', 'Факс.', 'Fax with period'),
        ('ru', '№', 'Number symbol'),
        ('ru', 'Номер', 'Number'),
        ('ru', 'Реф', 'Reference abbreviation'),
        ('ru', 'Реф.', 'Reference with period'),
        ('ru', 'Ссылка', 'Reference'),
        ('ru', 'Ул', 'Street abbreviation'),
        ('ru', 'Ул.', 'Street with period'),
        ('ru', 'Улица', 'Street (full)'),

        -- Receipt/Invoice specific labels
        ('ru', 'Чек', 'Receipt'),
        ('ru', 'Чек №', 'Receipt number'),
        ('ru', 'Номер чека', 'Receipt number (full)'),
        ('ru', 'Счет', 'Invoice'),
        ('ru', 'Счет №', 'Invoice number'),
        ('ru', 'Номер счета', 'Invoice number (full)'),
        ('ru', 'Счет-фактура', 'Invoice (formal)'),
        ('ru', 'Клиент', 'Customer'),
        ('ru', 'Номер клиента', 'Customer number'),
        ('ru', 'Заказ', 'Order'),
        ('ru', 'Заказ №', 'Order number'),
        ('ru', 'Номер заказа', 'Order number (full)'),

        -- Date and time labels
        ('ru', 'Дата', 'Date'),
        ('ru', 'Время', 'Time'),
        ('ru', 'Дата и время', 'Date and time'),
        ('ru', 'Временная метка', 'Timestamp'),

        -- Amount labels
        ('ru', 'Сумма', 'Amount/Sum'),
        ('ru', 'Итого', 'Total'),
        ('ru', 'Всего', 'Total (alt)'),
        ('ru', 'Промежуточный итог', 'Subtotal'),
        ('ru', 'Промежут. итог', 'Subtotal abbreviated'),
        ('ru', 'Нетто', 'Net'),
        ('ru', 'Брутто', 'Gross'),
        ('ru', 'К оплате', 'To pay'),

        -- Tax labels
        ('ru', 'НДС', 'VAT'),
        ('ru', 'Налог', 'Tax'),
        ('ru', 'Налоги', 'Taxes (plural)'),
        ('ru', 'ИНН', 'Tax identification number'),
        ('ru', 'КПП', 'Tax registration reason code'),
        ('ru', 'Налоговый номер', 'Tax number'),

        -- Payment labels
        ('ru', 'Карта', 'Card'),
        ('ru', 'Банковская карта', 'Bank card'),
        ('ru', 'Кредитная карта', 'Credit card'),
        ('ru', 'Дебетовая карта', 'Debit card'),
        ('ru', 'Номер карты', 'Card number'),
        ('ru', 'Терминал', 'Terminal'),
        ('ru', 'Терминал ID', 'Terminal ID'),
        ('ru', 'POS', 'Point of sale'),
        ('ru', 'ПОС', 'POS (Cyrillic)'),

        -- Authorization labels
        ('ru', 'Авторизация', 'Authorization'),
        ('ru', 'Код авторизации', 'Authorization code'),
        ('ru', 'Код подтверждения', 'Approval code'),
        ('ru', 'Код ответа', 'Response code'),
        ('ru', 'Трассировка', 'Trace'),
        ('ru', 'Номер трассировки', 'Trace number'),

        -- Transaction labels
        ('ru', 'Транзакция', 'Transaction'),
        ('ru', 'Операция', 'Operation'),
        ('ru', 'Номер транзакции', 'Transaction number'),
        ('ru', 'Номер операции', 'Operation number'),
        ('ru', 'Ссылка на транзакцию', 'Transaction reference'),

        -- Location labels
        ('ru', 'Местоположение', 'Location'),
        ('ru', 'Филиал', 'Branch'),
        ('ru', 'Отделение', 'Branch/Office'),
        ('ru', 'Магазин', 'Store'),
        ('ru', 'Номер магазина', 'Store number'),

        -- Signature labels
        ('ru', 'Подпись', 'Signature'),
        ('ru', 'Подписано', 'Signed'),

        -- Generic labels
        ('ru', 'Код', 'Code'),
        ('ru', 'ID', 'ID'),
        ('ru', 'Идентификатор', 'Identifier'),
        ('ru', 'Имя', 'Name'),
        ('ru', 'Название', 'Name/Title'),
        ('ru', 'Наименование', 'Name (formal)'),
        ('ru', 'Тип', 'Type'),
        ('ru', 'Статус', 'Status'),
        ('ru', 'Описание', 'Description'),
        ('ru', 'Опис', 'Description abbreviation'),
        ('ru', 'Опис.', 'Description with period')

        ON CONFLICT (language, label_text) DO NOTHING;
    """)


def downgrade():
    # Remove added field labels for all languages
    op.execute("""
        DELETE FROM entity_field_labels
        WHERE language IN ('de', 'en', 'fr', 'ru')
        AND label_text IN (
            'Tel', 'Tel.', 'Fax', 'Fax.', 'Nr', 'Nr.', 'Str', 'Str.',
            'Beleg-Nr', 'Beleg-Nr.', 'Belegnummer', 'Rechnungs-Nr', 'Rechnungs-Nr.',
            'Rechnungsnummer', 'Kunden-Nr', 'Kunden-Nr.', 'Kundennummer',
            'Datum', 'Uhrzeit', 'Zeit', 'Betrag', 'Summe', 'Gesamt', 'Netto', 'Brutto',
            'Zwischensumme', 'USt', 'USt.', 'MwSt', 'MwSt.', 'Steuer', 'Steuer-Nr',
            'Steuernummer', 'Karte', 'EC-Karte', 'Kartennummer', 'Karten-Nr',
            'Terminal', 'Terminal-ID', 'Autorisierung', 'Autorisierungscode',
            'Autorisierungsantwortcode', 'Trace', 'Trace-Nr', 'Transaktion',
            'Transaktions-Nr', 'Transaktionsnummer', 'Vorgang', 'Vorgangs-Nr',
            'Standort', 'Filiale', 'Filialnummer', 'Unterschrift', 'Signatur',
            'Code', 'ID', 'Kennung', 'Name', 'Typ', 'Art',
            'No', 'No.', 'Receipt No', 'Invoice No', 'Customer No', 'Date', 'Time',
            'Amount', 'Total', 'Subtotal', 'Tax', 'VAT', 'Card', 'Authorization',
            'Auth', 'Type'
        );
    """)
