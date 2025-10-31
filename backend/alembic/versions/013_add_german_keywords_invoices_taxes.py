"""add german keywords for invoices and taxes categories

Revision ID: 013_add_german_keywords
Revises: 012_fix_reference_key
Create Date: 2025-10-31 21:00:00.000000

"""
from alembic import op
from sqlalchemy import text
from datetime import datetime, timezone
import uuid

# revision identifiers, used by Alembic.
revision = '013_add_german_keywords'
down_revision = '012_fix_reference_key'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add German keywords for Invoices (INV) and Taxes (TAX) categories
    These were missing from migration 010 which only added English keywords
    """

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    print("\n=== Adding German Keywords for INV and TAX ===\n")

    # German keywords for Invoices (INV)
    invoices_de_keywords = [
        'rechnung',
        'faktura',
        'zahlung',
        'betrag',
        'fällig',
        'summe'
    ]

    # German keywords for Taxes (TAX)
    taxes_de_keywords = [
        'steuer',
        'steuererklärung',
        'quittung',
        'abzug',
        'finanzamt',
        'umsatzsteuer'
    ]

    # Add German keywords for Invoices
    result = conn.execute(text("SELECT id FROM categories WHERE reference_key = 'INV' AND user_id IS NULL"))
    row = result.fetchone()
    if row:
        inv_id = str(row[0])
        added = 0
        for keyword in invoices_de_keywords:
            result = conn.execute(text("""
                INSERT INTO category_keywords (id, category_id, keyword, language_code, weight, match_count, is_system_default, created_at, last_updated)
                VALUES (:id, :category_id, :keyword, 'de', 1.0, 1, true, :now, :now)
                ON CONFLICT (category_id, lower(keyword), language_code) DO NOTHING
                RETURNING id
            """), {
                'id': str(uuid.uuid4()),
                'category_id': inv_id,
                'keyword': keyword.lower(),
                'now': now
            })
            if result.rowcount > 0:
                added += 1
        print(f"  ✓ Added {added} German keywords for Invoices (INV)")

    # Add German keywords for Taxes
    result = conn.execute(text("SELECT id FROM categories WHERE reference_key = 'TAX' AND user_id IS NULL"))
    row = result.fetchone()
    if row:
        tax_id = str(row[0])
        added = 0
        for keyword in taxes_de_keywords:
            result = conn.execute(text("""
                INSERT INTO category_keywords (id, category_id, keyword, language_code, weight, match_count, is_system_default, created_at, last_updated)
                VALUES (:id, :category_id, :keyword, 'de', 1.0, 1, true, :now, :now)
                ON CONFLICT (category_id, lower(keyword), language_code) DO NOTHING
                RETURNING id
            """), {
                'id': str(uuid.uuid4()),
                'category_id': tax_id,
                'keyword': keyword.lower(),
                'now': now
            })
            if result.rowcount > 0:
                added += 1
        print(f"  ✓ Added {added} German keywords for Taxes (TAX)")

    print("\n✓ Migration 013 completed: German keywords added for classification")


def downgrade():
    """
    Remove German keywords for INV and TAX categories
    """

    conn = op.get_bind()

    conn.execute(text("""
        DELETE FROM category_keywords
        WHERE language_code = 'de'
        AND category_id IN (
            SELECT id FROM categories
            WHERE reference_key IN ('INV', 'TAX')
            AND user_id IS NULL
        )
    """))

    print("✓ Migration 013 downgrade completed")
