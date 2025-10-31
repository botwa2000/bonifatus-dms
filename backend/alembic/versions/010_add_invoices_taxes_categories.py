"""add invoices and taxes categories with french translations

Revision ID: 010_invoices_taxes
Revises: 009_language_metadata
Create Date: 2025-10-31 14:30:00.000000

"""
from alembic import op
from sqlalchemy import text
from datetime import datetime, timezone
import uuid

# revision identifiers, used by Alembic.
revision = '010_invoices_taxes'
down_revision = '009_language_metadata'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add Invoices and Taxes template categories with keywords
    Add French translations to all 7 template categories
    """

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # Step 1: Add Invoices category (INV)
    print("Adding Invoices category...")
    invoices_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO categories (id, reference_key, category_code, color_hex, icon_name, is_system, user_id, sort_order, is_active, created_at, updated_at)
        VALUES (:id, 'INV', 'INV', '#10B981', 'receipt', true, NULL, 5, true, :now, :now)
        ON CONFLICT (reference_key) DO NOTHING
    """), {'id': invoices_id, 'now': now})

    # Get the actual ID if it already exists
    result = conn.execute(text("SELECT id FROM categories WHERE reference_key = 'INV' AND user_id IS NULL"))
    row = result.fetchone()
    if row:
        invoices_id = str(row[0])

    # Step 2: Add Taxes category (TAX)
    print("Adding Taxes category...")
    taxes_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO categories (id, reference_key, category_code, color_hex, icon_name, is_system, user_id, sort_order, is_active, created_at, updated_at)
        VALUES (:id, 'TAX', 'TAX', '#EF4444', 'calculator', true, NULL, 6, true, :now, :now)
        ON CONFLICT (reference_key) DO NOTHING
    """), {'id': taxes_id, 'now': now})

    # Get the actual ID if it already exists
    result = conn.execute(text("SELECT id FROM categories WHERE reference_key = 'TAX' AND user_id IS NULL"))
    row = result.fetchone()
    if row:
        taxes_id = str(row[0])

    # Step 3: Add translations for Invoices
    print("Adding translations for Invoices...")
    invoices_translations = {
        'en': {'name': 'Invoices', 'description': 'Bills, invoices, payment requests'},
        'de': {'name': 'Rechnungen', 'description': 'Rechnungen, Zahlungsaufforderungen'},
        'ru': {'name': 'Счета', 'description': 'Счета, счета-фактуры, запросы на оплату'},
        'fr': {'name': 'Factures', 'description': 'Factures, demandes de paiement'}
    }

    for lang_code, trans in invoices_translations.items():
        conn.execute(text("""
            INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
            VALUES (:id, :category_id, :language_code, :name, :description, :now, :now)
            ON CONFLICT (category_id, language_code) DO NOTHING
        """), {
            'id': str(uuid.uuid4()),
            'category_id': invoices_id,
            'language_code': lang_code,
            'name': trans['name'],
            'description': trans['description'],
            'now': now
        })

    # Step 4: Add translations for Taxes
    print("Adding translations for Taxes...")
    taxes_translations = {
        'en': {'name': 'Taxes', 'description': 'Tax returns, receipts, tax-related documents'},
        'de': {'name': 'Steuern', 'description': 'Steuererklärungen, Quittungen, steuerbezogene Dokumente'},
        'ru': {'name': 'Налоги', 'description': 'Налоговые декларации, квитанции, налоговые документы'},
        'fr': {'name': 'Impôts', 'description': 'Déclarations fiscales, reçus, documents fiscaux'}
    }

    for lang_code, trans in taxes_translations.items():
        conn.execute(text("""
            INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
            VALUES (:id, :category_id, :language_code, :name, :description, :now, :now)
            ON CONFLICT (category_id, language_code) DO NOTHING
        """), {
            'id': str(uuid.uuid4()),
            'category_id': taxes_id,
            'language_code': lang_code,
            'name': trans['name'],
            'description': trans['description'],
            'now': now
        })

    # Step 5: Add French translations for existing categories
    print("Adding French translations for existing categories...")

    french_translations = {
        'INS': {'name': 'Assurance', 'description': "Polices d'assurance, réclamations, documents de couverture"},
        'LEG': {'name': 'Juridique', 'description': 'Contrats, accords, documents juridiques'},
        'RES': {'name': 'Immobilier', 'description': 'Documents immobiliers, actes, hypothèques'},
        'BNK': {'name': 'Banque', 'description': 'Relevés bancaires, transactions, documents financiers'},
        'OTH': {'name': 'Autre', 'description': 'Divers, catégorie par défaut'}
    }

    for ref_key, trans in french_translations.items():
        result = conn.execute(text("SELECT id FROM categories WHERE reference_key = :ref_key AND user_id IS NULL"), {'ref_key': ref_key})
        row = result.fetchone()
        if row:
            category_id = str(row[0])
            conn.execute(text("""
                INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
                VALUES (:id, :category_id, 'fr', :name, :description, :now, :now)
                ON CONFLICT (category_id, language_code) DO NOTHING
            """), {
                'id': str(uuid.uuid4()),
                'category_id': category_id,
                'name': trans['name'],
                'description': trans['description'],
                'now': now
            })

    # Step 6: Add category keywords
    print("Adding category keywords...")

    keywords_map = {
        'INS': ['insurance', 'policy', 'coverage', 'premium', 'claim'],
        'LEG': ['contract', 'agreement', 'legal', 'terms', 'conditions'],
        'RES': ['property', 'real estate', 'mortgage', 'deed', 'lease', 'rent'],
        'BNK': ['bank', 'account', 'statement', 'transaction', 'balance', 'payment'],
        'INV': ['invoice', 'bill', 'payment', 'due', 'total', 'amount'],
        'TAX': ['tax', 'receipt', 'deduction', 'return', 'fiscal', 'revenue'],
        'OTH': ['document', 'file', 'misc']
    }

    for ref_key, keywords in keywords_map.items():
        result = conn.execute(text("SELECT id FROM categories WHERE reference_key = :ref_key AND user_id IS NULL"), {'ref_key': ref_key})
        row = result.fetchone()
        if row:
            category_id = str(row[0])
            for keyword in keywords:
                conn.execute(text("""
                    INSERT INTO category_keywords (id, category_id, keyword, language_code, weight, match_count, is_system_default, created_at, last_updated)
                    VALUES (:id, :category_id, :keyword, 'en', 1.0, 1, true, :now, :now)
                    ON CONFLICT (category_id, lower(keyword), language_code) DO NOTHING
                """), {
                    'id': str(uuid.uuid4()),
                    'category_id': category_id,
                    'keyword': keyword.lower(),
                    'now': now
                })

    print("✓ Migration 010 completed: Added Invoices and Taxes categories with full translations and keywords")


def downgrade():
    """
    Remove Invoices and Taxes categories and their translations
    """

    conn = op.get_bind()

    # Remove Invoices and Taxes categories (cascade will remove translations and keywords)
    conn.execute(text("""
        DELETE FROM categories
        WHERE reference_key IN ('INV', 'TAX') AND user_id IS NULL
    """))

    # Remove French translations for other categories
    conn.execute(text("""
        DELETE FROM category_translations
        WHERE language_code = 'fr'
        AND category_id IN (
            SELECT id FROM categories
            WHERE reference_key IN ('INS', 'LEG', 'RES', 'BNK', 'OTH')
            AND user_id IS NULL
        )
    """))

    print("✓ Migration 010 downgrade completed")
