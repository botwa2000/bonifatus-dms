#!/usr/bin/env python3
"""
Normalize all default keyword weights to a consistent baseline.

Sets all system default keywords to weight 2.0 for consistency.
This provides a balanced starting point that can be adjusted up or down.
"""
import sys
import os
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from app.core.config import settings

def normalize_keyword_weights():
    """Set all default keywords to weight 2.0"""
    engine = create_engine(settings.database.database_url)

    with engine.connect() as conn:
        # Get count of keywords before update
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM category_keywords
            WHERE is_system_default = true
        """))
        total_keywords = result.scalar()

        print(f"Normalizing {total_keywords} system default keywords to weight 2.0...")
        print("-" * 80)

        # Update all system default keywords to weight 2.0
        result = conn.execute(text("""
            UPDATE category_keywords
            SET weight = 2.0
            WHERE is_system_default = true
            RETURNING keyword, language_code
        """))

        updated_keywords = result.fetchall()

        for keyword, lang in updated_keywords:
            print(f"✓ Normalized '{keyword}' ({lang}) -> weight: 2.0")

        conn.commit()
        print("-" * 80)
        print(f"Successfully normalized {len(updated_keywords)} keywords to weight 2.0!")

if __name__ == '__main__':
    normalize_keyword_weights()
