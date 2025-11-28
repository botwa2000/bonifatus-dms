import sys
import os
sys.path.insert(0, '/app')
from sqlalchemy import create_engine, text
import uuid
from datetime import datetime, timezone

# Use DATABASE_URL from environment or construct from parts
target_url = os.getenv('DATABASE_URL')
if not target_url:
    db_host = os.getenv('DB_HOST', 'postgres-bonifatus')
    db_port = os.getenv('DB_PORT', '5432')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'BoniDoc2025SecurePassword')
    db_name = os.getenv('DB_NAME', 'bonifatus_dms_dev')
    target_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

print(f"Connecting to database...\n")
engine = create_engine(target_url)

with engine.connect() as conn:
    now = datetime.now(timezone.utc)

    print('=== POPULATING ENHANCED CATEGORY KEYWORDS ===\n')

    # Get category IDs by reference_key (INS, BNK, LEG, etc.)
    categories = {}
    result = conn.execute(text("SELECT id, reference_key FROM categories WHERE user_id IS NULL"))
    for row in result:
        categories[row.reference_key] = str(row.id)

    print(f"Found {len(categories)} template categories: {list(categories.keys())}\n")

    # Comprehensive category keywords per language with weights
    # Higher weights (3.0-5.0) for very specific terms, lower (1.5-2.5) for general terms
    category_terms = {
        'INS': {  # Insurance
            'en': [
                ('insurance', 3.5), ('policy', 3.2), ('coverage', 3.0), ('premium', 3.0),
                ('claim', 2.8), ('insured', 2.8), ('policyholder', 2.5), ('deductible', 2.5),
                ('underwriter', 2.3), ('liability', 2.3), ('beneficiary', 2.0)
            ],
            'de': [
                ('versicherung', 3.5), ('police', 3.2), ('versicherungspolice', 3.2),
                ('deckung', 3.0), ('prämie', 3.0), ('schaden', 2.8), ('schadensfall', 2.8),
                ('versichert', 2.8), ('versicherungsnehmer', 2.5), ('selbstbehalt', 2.5),
                ('haftung', 2.3), ('begünstigter', 2.0)
            ],
            'ru': [
                ('страхование', 3.5), ('полис', 3.2), ('страховой полис', 3.2),
                ('покрытие', 3.0), ('премия', 3.0), ('претензия', 2.8), ('иск', 2.8),
                ('застрахованный', 2.8), ('страхователь', 2.5), ('франшиза', 2.5),
                ('ответственность', 2.3), ('выгодоприобретатель', 2.0)
            ],
            'fr': [
                ('assurance', 3.5), ('police', 3.2), ("police d'assurance", 3.2),
                ('couverture', 3.0), ('prime', 3.0), ('réclamation', 2.8), ('sinistre', 2.8),
                ('assuré', 2.8), ('souscripteur', 2.5), ('franchise', 2.5),
                ('responsabilité', 2.3), ('bénéficiaire', 2.0)
            ]
        },
        'BNK': {  # Banking - Keep specific to bank statements, avoid invoice overlap
            'en': [
                ('bank statement', 4.0), ('account statement', 4.0), ('iban', 3.8), ('bic', 3.8),
                ('swift', 3.5), ('account', 3.0), ('balance', 3.0), ('transaction', 2.8),
                ('deposit', 2.5), ('withdrawal', 2.5), ('overdraft', 2.3), ('credit', 2.0), ('debit', 2.0)
            ],
            'de': [
                ('kontoauszug', 4.0), ('bankauszug', 4.0), ('iban', 3.8), ('bic', 3.8),
                ('swift', 3.5), ('bankverbindung', 3.5), ('konto', 3.0), ('saldo', 3.0),
                ('transaktion', 2.8), ('überweisung', 2.8), ('einzahlung', 2.5),
                ('auszahlung', 2.5), ('überziehung', 2.3), ('lastschrift', 2.3)
            ],
            'ru': [
                ('выписка из счета', 4.0), ('банковская выписка', 4.0), ('iban', 3.8), ('bic', 3.8),
                ('swift', 3.5), ('счет', 3.0), ('баланс', 3.0), ('транзакция', 2.8),
                ('депозит', 2.5), ('снятие', 2.5), ('овердрафт', 2.3), ('кредит', 2.0), ('дебет', 2.0)
            ],
            'fr': [
                ('relevé bancaire', 4.0), ('relevé de compte', 4.0), ('iban', 3.8), ('bic', 3.8),
                ('swift', 3.5), ('compte', 3.0), ('solde', 3.0), ('transaction', 2.8),
                ('dépôt', 2.5), ('retrait', 2.5), ('découvert', 2.3), ('crédit', 2.0), ('débit', 2.0)
            ]
        },
        'LEG': {  # Legal
            'en': [
                ('contract', 3.5), ('agreement', 3.5), ('legal', 3.0), ('terms', 2.8),
                ('conditions', 2.8), ('clause', 2.5), ('party', 2.3), ('hereby', 2.3),
                ('whereas', 2.3), ('jurisdiction', 2.0), ('dispute', 2.0), ('arbitration', 2.0)
            ],
            'de': [
                ('vertrag', 3.5), ('vereinbarung', 3.5), ('rechtlich', 3.0), ('bedingungen', 2.8),
                ('konditionen', 2.8), ('klausel', 2.5), ('partei', 2.3), ('vertragspartei', 2.3),
                ('gerichtsbarkeit', 2.0), ('streitfall', 2.0), ('schiedsverfahren', 2.0)
            ],
            'ru': [
                ('контракт', 3.5), ('соглашение', 3.5), ('договор', 3.5), ('юридический', 3.0),
                ('условия', 2.8), ('положения', 2.8), ('пункт', 2.5), ('сторона', 2.3),
                ('юрисдикция', 2.0), ('спор', 2.0), ('арбитраж', 2.0)
            ],
            'fr': [
                ('contrat', 3.5), ('accord', 3.5), ('juridique', 3.0), ('conditions', 2.8),
                ('termes', 2.8), ('clause', 2.5), ('partie', 2.3), ('juridiction', 2.0),
                ('litige', 2.0), ('arbitrage', 2.0)
            ]
        },
        'RES': {  # Real Estate
            'en': [
                ('real estate', 4.0), ('property', 3.5), ('mortgage', 3.2), ('deed', 3.0),
                ('lease', 2.8), ('rent', 2.5), ('landlord', 2.5), ('tenant', 2.5),
                ('premises', 2.3), ('title', 2.3), ('escrow', 2.0)
            ],
            'de': [
                ('immobilie', 4.0), ('grundstück', 3.5), ('hypothek', 3.2), ('eigentum', 3.0),
                ('mietvertrag', 2.8), ('miete', 2.5), ('vermieter', 2.5), ('mieter', 2.5),
                ('räumlichkeiten', 2.3), ('grundbuch', 2.3), ('treuhand', 2.0)
            ],
            'ru': [
                ('недвижимость', 4.0), ('собственность', 3.5), ('ипотека', 3.2), ('акт', 3.0),
                ('аренда', 2.8), ('арендная плата', 2.5), ('арендодатель', 2.5), ('арендатор', 2.5),
                ('помещение', 2.3), ('правовой титул', 2.3), ('эскроу', 2.0)
            ],
            'fr': [
                ('immobilier', 4.0), ('propriété', 3.5), ('hypothèque', 3.2), ('acte', 3.0),
                ('bail', 2.8), ('loyer', 2.5), ('propriétaire', 2.5), ('locataire', 2.5),
                ('locaux', 2.3), ('titre', 2.3), ('séquestre', 2.0)
            ]
        },
        'INV': {  # Invoices - Comprehensive invoice keywords with high specificity
            'en': [
                ('invoice number', 5.0), ('invoice no', 5.0), ('bill', 4.0), ('invoice', 4.0),
                ('billing', 3.5), ('due date', 3.2), ('payment due', 3.2), ('amount due', 3.2),
                ('subtotal', 3.0), ('total amount', 3.0), ('line item', 2.8), ('quantity', 2.5),
                ('unit price', 2.5), ('payment terms', 2.5), ('net amount', 2.3), ('payable', 2.3)
            ],
            'de': [
                ('rechnung nr', 5.0), ('rechnungsnummer', 5.0), ('rechnung', 4.0), ('faktura', 4.0),
                ('rechnungsstellung', 3.5), ('fälligkeitsdatum', 3.2), ('zahlbar bis', 3.2),
                ('fälliger betrag', 3.2), ('gesamtpreis', 3.0), ('gesamtbetrag', 3.0),
                ('zwischensumme', 3.0), ('einzelpreis', 2.8), ('menge', 2.5), ('anzahl', 2.5),
                ('leistungen', 2.5), ('produkte', 2.5), ('zahlungsbedingungen', 2.5),
                ('nettobetrag', 2.3), ('zahlbar', 2.3), ('rechnungsbetrag', 2.8)
            ],
            'ru': [
                ('номер счета', 5.0), ('счет-фактура', 5.0), ('счет', 4.0), ('инвойс', 4.0),
                ('выставление счета', 3.5), ('срок оплаты', 3.2), ('к оплате', 3.2),
                ('сумма к оплате', 3.2), ('промежуточная сумма', 3.0), ('итого', 3.0),
                ('позиция', 2.8), ('количество', 2.5), ('цена за единицу', 2.5),
                ('условия оплаты', 2.5), ('чистая сумма', 2.3), ('подлежит оплате', 2.3)
            ],
            'fr': [
                ('numéro de facture', 5.0), ('facture n°', 5.0), ('facture', 4.0), ('facturation', 3.5),
                ('date d\'échéance', 3.2), ('montant dû', 3.2), ('à payer', 3.2),
                ('sous-total', 3.0), ('montant total', 3.0), ('ligne', 2.8), ('quantité', 2.5),
                ('prix unitaire', 2.5), ('conditions de paiement', 2.5),
                ('montant net', 2.3), ('payable', 2.3)
            ]
        },
        'TAX': {  # Taxes
            'en': [
                ('tax return', 4.5), ('vat', 4.0), ('tax', 3.5), ('fiscal', 3.2), ('deduction', 3.0),
                ('revenue', 2.8), ('taxable', 2.5), ('withholding', 2.5), ('refund', 2.3),
                ('assessment', 2.0), ('excise', 2.0)
            ],
            'de': [
                ('steuererklärung', 4.5), ('umsatzsteuer', 4.0), ('ust', 4.0), ('mwst', 4.0),
                ('steuer', 3.5), ('finanzamt', 3.2), ('abzug', 3.0), ('steuerpflichtig', 2.5),
                ('quellensteuer', 2.5), ('erstattung', 2.3), ('veranlagung', 2.0)
            ],
            'ru': [
                ('налоговая декларация', 4.5), ('ндс', 4.0), ('налог', 3.5), ('фискальный', 3.2),
                ('вычет', 3.0), ('доход', 2.8), ('налогооблагаемый', 2.5), ('удержание', 2.5),
                ('возврат', 2.3), ('оценка', 2.0), ('акциз', 2.0)
            ],
            'fr': [
                ('déclaration fiscale', 4.5), ('tva', 4.0), ('taxe', 3.5), ('impôt', 3.5),
                ('fiscal', 3.2), ('déduction', 3.0), ('revenu', 2.8), ('imposable', 2.5),
                ('retenue', 2.5), ('remboursement', 2.3), ('évaluation', 2.0)
            ]
        },
        'OTH': {  # Other - Keep general
            'en': [
                ('document', 2.0), ('file', 2.0), ('misc', 1.5), ('general', 1.5)
            ],
            'de': [
                ('dokument', 2.0), ('datei', 2.0), ('sonstige', 1.5), ('allgemein', 1.5)
            ],
            'ru': [
                ('документ', 2.0), ('файл', 2.0), ('прочие', 1.5), ('общий', 1.5)
            ],
            'fr': [
                ('document', 2.0), ('fichier', 2.0), ('divers', 1.5), ('général', 1.5)
            ]
        }
    }

    keyword_count = 0
    updated_count = 0
    skipped_count = 0

    for cat_key, lang_terms in category_terms.items():
        if cat_key in categories:
            cat_id = categories[cat_key]
            print(f"Processing {cat_key}...")
            for lang, terms in lang_terms.items():
                for term, weight in terms:
                    result = conn.execute(text('''
                        INSERT INTO category_keywords (id, category_id, keyword, language_code, weight, match_count, is_system_default, created_at, last_updated)
                        VALUES (:id, :cat_id, :keyword, :lang, :weight, 1, true, :created, :updated)
                        ON CONFLICT (category_id, lower(keyword), language_code)
                        DO UPDATE SET
                            weight = EXCLUDED.weight,
                            last_updated = EXCLUDED.last_updated
                        RETURNING (xmax = 0) AS inserted
                    '''), {
                        'id': str(uuid.uuid4()),
                        'cat_id': cat_id,
                        'keyword': term.lower(),
                        'lang': lang,
                        'weight': weight,
                        'created': now,
                        'updated': now
                    })
                    row = result.fetchone()
                    if row and row[0]:
                        keyword_count += 1
                    else:
                        updated_count += 1
        else:
            print(f"  ⚠️  Category {cat_key} not found, skipping...")
            skipped_count += 1

    conn.commit()
    print(f'\n✓ Inserted {keyword_count} new keywords')
    print(f'✓ Updated {updated_count} existing keywords')
    if skipped_count > 0:
        print(f'⚠️  Skipped {skipped_count} categories (not found)')

    # Verify
    print('\nKeywords per category (all languages):')
    for cat_key in category_terms.keys():
        if cat_key in categories:
            cat_id = categories[cat_key]
            count = conn.execute(text('SELECT COUNT(*) FROM category_keywords WHERE category_id = :cat_id'), {'cat_id': cat_id}).scalar()
            print(f'  {cat_key:5} - {count:3} keywords')

            # Show breakdown by language
            lang_breakdown = conn.execute(text('''
                SELECT language_code, COUNT(*)
                FROM category_keywords
                WHERE category_id = :cat_id
                GROUP BY language_code
                ORDER BY language_code
            '''), {'cat_id': cat_id})
            lang_counts = {row[0]: row[1] for row in lang_breakdown}
            print(f'        (en:{lang_counts.get("en", 0)}, de:{lang_counts.get("de", 0)}, ru:{lang_counts.get("ru", 0)}, fr:{lang_counts.get("fr", 0)})')

engine.dispose()
print('\n✅ Category keywords populated successfully!')
print('\nNext steps:')
print('1. Users can reset their categories to get these new keywords')
print('2. Existing documents will be reclassified with improved accuracy')
