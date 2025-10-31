#!/usr/bin/env python3
"""
Add French stop words to the database
"""
import sys
sys.path.insert(0, '/app')

from app.database.connection import db_manager
from app.database.models import StopWord
import uuid

# Common French stop words
FRENCH_STOP_WORDS = [
    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du',
    'et', 'ou', 'mais', 'donc', 'car', 'ni', 'or',
    'dans', 'sur', 'sous', 'avec', 'sans', 'pour', 'par',
    'ce', 'cet', 'cette', 'ces',
    'il', 'elle', 'on', 'ils', 'elles',
    'je', 'tu', 'nous', 'vous',
    'mon', 'ton', 'son', 'notre', 'votre', 'leur',
    'qui', 'que', 'quoi', 'dont', 'où',
    'est', 'sont', 'était', 'étaient', 'sera', 'seront',
    'a', 'ai', 'as', 'avons', 'avez', 'ont',
    'tout', 'tous', 'toute', 'toutes',
    'aucun', 'aucune', 'chaque', 'quelque'
]

def add_french_stopwords():
    """Add French stop words to database"""
    db = db_manager.session_local()
    try:
        # Check existing French stop words
        existing_count = db.query(StopWord).filter(
            StopWord.language_code == 'fr'
        ).count()

        print(f"\n=== Adding French Stop Words ===\n")
        print(f"Existing French stop words: {existing_count}")

        if existing_count > 0:
            print("French stop words already exist. Skipping.")
            return

        # Add French stop words
        added = 0
        for word in FRENCH_STOP_WORDS:
            stop_word = StopWord(
                id=uuid.uuid4(),
                language_code='fr',
                word=word.lower(),
                is_active=True
            )
            db.add(stop_word)
            added += 1

        db.commit()
        print(f"✅ Added {added} French stop words")

        # Verify
        final_count = db.query(StopWord).filter(
            StopWord.language_code == 'fr'
        ).count()
        print(f"Total French stop words in database: {final_count}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error adding French stop words: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_french_stopwords()
