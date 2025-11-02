#!/usr/bin/env python3
"""
Fix keyword weights to improve classification accuracy.

Invoice-specific keywords should have higher weights than general banking terms.
"""
import sys
import os
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from app.database.config import get_database_url

def fix_keyword_weights():
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        # Define keyword weight adjustments
        # Higher weights for category-specific keywords
        # Lower weights for generic/shared keywords

        weight_updates = [
            # Invoice-specific keywords - HIGH weight (3.0)
            ('rechnung', 'de', 3.0),
            ('invoice', 'en', 3.0),
            ('faktura', 'de', 3.0),
            ('bill', 'en', 3.0),
            ('счет', 'ru', 3.0),  # Invoice in Russian

            # Tax-specific keywords - HIGH weight (3.0)
            ('steuer', 'de', 3.0),
            ('steuererklärung', 'de', 3.0),
            ('tax', 'en', 3.0),

            # Banking keywords - MEDIUM weight (1.5) - these are often in invoices too
            ('bank', 'en', 1.5),
            ('konto', 'de', 1.5),
            ('kontoauszug', 'de', 1.5),

            # Shared keywords - MEDIUM weight (1.5)
            ('payment', 'en', 1.5),
            ('zahlung', 'de', 1.5),
            ('amount', 'en', 1.5),
            ('betrag', 'de', 1.5),
        ]

        print("Updating keyword weights...")
        print("-" * 80)

        for keyword, lang, new_weight in weight_updates:
            result = conn.execute(text("""
                UPDATE category_keywords
                SET weight = :weight
                WHERE LOWER(keyword) = LOWER(:keyword)
                AND language_code = :lang
            """), {'weight': new_weight, 'keyword': keyword, 'lang': lang})

            if result.rowcount > 0:
                print(f"✓ Updated '{keyword}' ({lang}) -> weight: {new_weight}")
            else:
                print(f"  Skipped '{keyword}' ({lang}) - not found")

        conn.commit()
        print("-" * 80)
        print("Keyword weights updated successfully!")

if __name__ == '__main__':
    fix_keyword_weights()
