"""standardize category structure with uniform reference keys

Revision ID: 011_standardize_categories
Revises: 010_invoices_taxes
Create Date: 2025-10-31 15:00:00.000000

"""
from alembic import op
from sqlalchemy import text
from datetime import datetime, timezone
import uuid

# revision identifiers, used by Alembic.
revision = '011_standardize_categories'
down_revision = '010_invoices_taxes'
branch_labels = None
depends_on = None


def upgrade():
    """
    Standardize all template categories to use uniform 3-letter reference keys
    Ensure all categories have translations in all 4 languages and keywords
    """

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    print("\n=== Standardizing Category Structure ===\n")

    # Step 1: Update old reference_keys to use simple 3-letter codes
    print("Step 1: Updating reference keys to 3-letter codes...")

    old_to_new = {
        'category.insurance': 'INS',
        'category.legal': 'LEG',
        'category.real_estate': 'RES',
        'category.banking': 'BNK',
        'category.other': 'OTH'
    }

    for old_key, new_key in old_to_new.items():
        result = conn.execute(text("""
            UPDATE categories
            SET reference_key = :new_key
            WHERE reference_key = :old_key AND user_id IS NULL
        """), {'old_key': old_key, 'new_key': new_key})
        if result.rowcount > 0:
            print(f"  ✓ Updated {old_key} → {new_key}")

    # Step 2: Add French translations for all categories
    print("\nStep 2: Adding French translations...")

    french_translations = {
        'INS': {'name': 'Assurance', 'description': "Polices d'assurance, réclamations, documents de couverture"},
        'LEG': {'name': 'Juridique', 'description': 'Contrats, accords, documents juridiques'},
        'RES': {'name': 'Immobilier', 'description': 'Documents immobiliers, actes, hypothèques'},
        'BNK': {'name': 'Banque', 'description': 'Relevés bancaires, transactions, documents financiers'},
        'INV': {'name': 'Factures', 'description': 'Factures, demandes de paiement'},
        'TAX': {'name': 'Impôts', 'description': 'Déclarations fiscales, reçus, documents fiscaux'},
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
            print(f"  ✓ Added French translation for {ref_key}")

    # Step 3: Ensure all categories have keywords
    print("\nStep 3: Ensuring all categories have keywords...")

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
            keywords_added = 0
            for keyword in keywords:
                result = conn.execute(text("""
                    INSERT INTO category_keywords (id, category_id, keyword, language_code, weight, match_count, is_system_default, created_at, last_updated)
                    VALUES (:id, :category_id, :keyword, 'en', 1.0, 1, true, :now, :now)
                    ON CONFLICT (category_id, lower(keyword), language_code) DO NOTHING
                """), {
                    'id': str(uuid.uuid4()),
                    'category_id': category_id,
                    'keyword': keyword.lower(),
                    'now': now
                })
                if result.rowcount > 0:
                    keywords_added += 1
            if keywords_added > 0:
                print(f"  ✓ Added {keywords_added} keywords for {ref_key}")

    # Step 4: Verification
    print("\nStep 4: Verifying standardization...")

    result = conn.execute(text("""
        SELECT reference_key,
               (SELECT COUNT(*) FROM category_translations ct WHERE ct.category_id = c.id) as translations,
               (SELECT COUNT(*) FROM category_keywords ck WHERE ck.category_id = c.id) as keywords
        FROM categories c
        WHERE user_id IS NULL
        ORDER BY sort_order
    """))

    print("\n  Category | Translations | Keywords")
    print("  ---------|--------------|----------")
    for row in result:
        print(f"  {row[0]:8s} | {row[1]:12d} | {row[2]:8d}")

    print("\n✓ Migration 011 completed: All categories standardized with uniform structure")


def downgrade():
    """
    Revert reference keys back to old format (not recommended)
    """

    conn = op.get_bind()

    print("\n=== Reverting Category Standardization ===\n")

    # Revert reference keys
    new_to_old = {
        'INS': 'category.insurance',
        'LEG': 'category.legal',
        'RES': 'category.real_estate',
        'BNK': 'category.banking',
        'OTH': 'category.other'
    }

    for new_key, old_key in new_to_old.items():
        conn.execute(text("""
            UPDATE categories
            SET reference_key = :old_key
            WHERE reference_key = :new_key AND user_id IS NULL
        """), {'old_key': old_key, 'new_key': new_key})

    print("✓ Migration 011 downgrade completed")
