"""add invoices and taxes categories with french translations

Revision ID: 010
Revises: 009
Create Date: 2025-10-31 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add Invoices and Taxes template categories with keywords
    Add French translations to all 7 template categories
    """

    # Create bind to execute raw SQL
    bind = op.get_bind()

    # Step 1: Add Invoices category (INV)
    print("Adding Invoices category...")
    bind.execute(sa.text("""
        INSERT INTO categories (id, name, reference_key, description, is_system, user_id, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'Invoices',
            'INV',
            'Bills, invoices, payment requests',
            true,
            NULL,
            :now,
            :now
        )
        ON CONFLICT (reference_key, COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid)) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Step 2: Add Taxes category (TAX)
    print("Adding Taxes category...")
    bind.execute(sa.text("""
        INSERT INTO categories (id, name, reference_key, description, is_system, user_id, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'Taxes',
            'TAX',
            'Tax returns, receipts, tax-related documents',
            true,
            NULL,
            :now,
            :now
        )
        ON CONFLICT (reference_key, COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid)) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Step 3: Add French translations for all 7 categories
    print("Adding French translations for all categories...")

    # Insurance (INS) - French
    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'fr',
            'Assurance',
            'Polices d''assurance, réclamations, documents de couverture',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'INS' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Legal (LEG) - French
    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'fr',
            'Juridique',
            'Contrats, accords, documents juridiques',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'LEG' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Real Estate (RES) - French
    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'fr',
            'Immobilier',
            'Documents immobiliers, actes, hypothèques',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'RES' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Banking (BNK) - French
    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'fr',
            'Banque',
            'Relevés bancaires, transactions, documents financiers',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'BNK' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Invoices (INV) - All languages
    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'de',
            'Rechnungen',
            'Rechnungen, Zahlungsaufforderungen',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'INV' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'ru',
            'Счета',
            'Счета, счета-фактуры, запросы на оплату',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'INV' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'fr',
            'Factures',
            'Factures, demandes de paiement',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'INV' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Taxes (TAX) - All languages
    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'de',
            'Steuern',
            'Steuererklärungen, Quittungen, steuerbezogene Dokumente',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'TAX' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'ru',
            'Налоги',
            'Налоговые декларации, квитанции, налоговые документы',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'TAX' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'fr',
            'Impôts',
            'Déclarations fiscales, reçus, documents fiscaux',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'TAX' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Other (OTH) - French
    bind.execute(sa.text("""
        INSERT INTO category_translations (id, category_id, language_code, name, description, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            'fr',
            'Autre',
            'Divers, catégorie par défaut',
            :now,
            :now
        FROM categories c
        WHERE c.reference_key = 'OTH' AND c.user_id IS NULL
        ON CONFLICT (category_id, language_code) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Step 4: Add category keywords for all categories
    print("Adding category keywords...")

    # Insurance keywords
    bind.execute(sa.text("""
        INSERT INTO category_keywords (id, category_id, keyword, weight, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, unnest(ARRAY['insurance', 'policy', 'coverage', 'premium', 'claim']), 1.0, :now, :now
        FROM categories c
        WHERE c.reference_key = 'INS' AND c.user_id IS NULL
        ON CONFLICT (category_id, keyword) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Legal keywords
    bind.execute(sa.text("""
        INSERT INTO category_keywords (id, category_id, keyword, weight, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, unnest(ARRAY['contract', 'agreement', 'legal', 'terms', 'conditions']), 1.0, :now, :now
        FROM categories c
        WHERE c.reference_key = 'LEG' AND c.user_id IS NULL
        ON CONFLICT (category_id, keyword) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Real Estate keywords
    bind.execute(sa.text("""
        INSERT INTO category_keywords (id, category_id, keyword, weight, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, unnest(ARRAY['property', 'real estate', 'mortgage', 'deed', 'lease', 'rent']), 1.0, :now, :now
        FROM categories c
        WHERE c.reference_key = 'RES' AND c.user_id IS NULL
        ON CONFLICT (category_id, keyword) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Banking keywords
    bind.execute(sa.text("""
        INSERT INTO category_keywords (id, category_id, keyword, weight, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, unnest(ARRAY['bank', 'account', 'statement', 'transaction', 'balance', 'payment']), 1.0, :now, :now
        FROM categories c
        WHERE c.reference_key = 'BNK' AND c.user_id IS NULL
        ON CONFLICT (category_id, keyword) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Invoices keywords (NEW)
    bind.execute(sa.text("""
        INSERT INTO category_keywords (id, category_id, keyword, weight, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, unnest(ARRAY['invoice', 'bill', 'payment', 'due', 'total', 'amount']), 1.0, :now, :now
        FROM categories c
        WHERE c.reference_key = 'INV' AND c.user_id IS NULL
        ON CONFLICT (category_id, keyword) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Taxes keywords (NEW)
    bind.execute(sa.text("""
        INSERT INTO category_keywords (id, category_id, keyword, weight, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, unnest(ARRAY['tax', 'receipt', 'deduction', 'return', 'fiscal', 'revenue']), 1.0, :now, :now
        FROM categories c
        WHERE c.reference_key = 'TAX' AND c.user_id IS NULL
        ON CONFLICT (category_id, keyword) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    # Other keywords
    bind.execute(sa.text("""
        INSERT INTO category_keywords (id, category_id, keyword, weight, created_at, updated_at)
        SELECT gen_random_uuid(), c.id, unnest(ARRAY['document', 'file', 'misc']), 1.0, :now, :now
        FROM categories c
        WHERE c.reference_key = 'OTH' AND c.user_id IS NULL
        ON CONFLICT (category_id, keyword) DO NOTHING
    """), {"now": datetime.now(timezone.utc)})

    print("✓ Migration 010 completed: Added Invoices and Taxes categories with full translations")


def downgrade():
    """
    Remove Invoices and Taxes categories and their translations
    """

    bind = op.get_bind()

    # Remove Invoices and Taxes categories (cascade will remove translations and keywords)
    bind.execute(sa.text("""
        DELETE FROM categories
        WHERE reference_key IN ('INV', 'TAX') AND user_id IS NULL
    """))

    # Remove French translations for other categories
    bind.execute(sa.text("""
        DELETE FROM category_translations
        WHERE language_code = 'fr'
        AND category_id IN (
            SELECT id FROM categories
            WHERE reference_key IN ('INS', 'LEG', 'RES', 'BNK', 'OTH')
            AND user_id IS NULL
        )
    """))

    print("✓ Migration 010 downgrade completed")
