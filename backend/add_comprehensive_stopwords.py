#!/usr/bin/env python3
"""
Add comprehensive stop words for all languages (de, en, fr, ru)
Uses ON CONFLICT DO NOTHING to safely handle unique constraint
"""
import sys
sys.path.insert(0, '/app')

from app.database.connection import db_manager
from sqlalchemy import text
import uuid

# Comprehensive stopword lists - only commonly occurring words in documents
STOPWORDS_BY_LANGUAGE = {
    'de': [
        # Missing critical words from user documents
        'sehr', 'ihnen', 'diesem', 'diese', 'dieser', 'dieses',

        # Common German stopwords
        'alle', 'aller', 'alles', 'als', 'also', 'am', 'andere', 'anderen', 'anderer', 'anderes',
        'auch', 'aus', 'bis', 'bin', 'da', 'damit', 'dann', 'dass', 'daß', 'denn',
        'doch', 'durch', 'gegen', 'hab', 'habe', 'hatten', 'hier', 'ihm', 'ihn', 'im',
        'immer', 'ins', 'ja', 'jede', 'jedem', 'jeden', 'jedes', 'jener', 'jenen', 'jenem', 'jenes',
        'kann', 'konnte', 'könnten', 'machen', 'mehr', 'mein', 'meine', 'meinem', 'meinen',
        'meiner', 'meines', 'mich', 'mir', 'muss', 'musste', 'müssen', 'müsste', 'müssten',
        'nach', 'nein', 'nicht', 'nichts', 'noch', 'nun', 'nur', 'ob', 'ohne', 'schon',
        'sei', 'seit', 'selbst', 'sich', 'soll', 'sollte', 'sollten', 'sondern', 'um', 'über',
        'uns', 'unser', 'unsere', 'unserem', 'unseren', 'unserer', 'unseres',
        'unter', 'viel', 'viele', 'vom', 'vor', 'während', 'wann', 'wer', 'wieder',
        'wie', 'will', 'wo', 'würde', 'würden', 'zum', 'zur', 'zwischen',
        'ihre', 'ihrer', 'ihres', 'ihrem', 'deren', 'dessen', 'derer',
        'welche', 'welcher', 'welchen', 'welchem', 'welches',
        'gewesen', 'gemacht', 'gesagt', 'gehabt', 'gegeben', 'gekommen',
        'möchte', 'möchten', 'können', 'könnte', 'sollen', 'wollen', 'wollte', 'wollten',
        'eben', 'etwas', 'ganz', 'heute', 'irgend', 'jetzt', 'mal', 'man',
        'sonst', 'vielleicht', 'weg', 'weil', 'weiter', 'weitere', 'wenig', 'wenige', 'weniger',
        'wohl', 'worden', 'wurde', 'wurden', 'ein', 'eins', 'zwei', 'drei', 'erste', 'zweite',
    ],

    'en': [
        # Core English stopwords
        'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'than', 'because',
        'as', 'what', 'which', 'this', 'that', 'these', 'those',
        'am', 'is', 'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had',
        'having', 'do', 'does', 'did', 'doing', 'would', 'should', 'could', 'ought',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their', 'theirs',
        'me', 'my', 'myself', 'our', 'ours', 'ourselves',
        'your', 'yours', 'yourself', 'yourselves',
        'him', 'his', 'himself', 'her', 'hers', 'herself',
        'its', 'itself', 'themselves',
        'will', 'shall', 'may', 'might', 'must', 'can',
        'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
        'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under',
        'again', 'further', 'once', 'here', 'there', 'when', 'where',
        'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'too', 'very', 'just', 'now', 'until', 'while',
    ],

    'fr': [
        # French stopwords
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'd',
        'et', 'ou', 'où', 'mais', 'donc', 'car', 'ni', 'or',
        'dans', 'sur', 'sous', 'avec', 'sans', 'pour', 'par', 'en',
        'ce', 'cet', 'cette', 'ces', 'c', 'ç',
        'il', 'elle', 'on', 'ils', 'elles', 'lui', 'eux', 'leur', 'leurs',
        'je', 'j', 'tu', 'nous', 'vous', 'me', 'm', 'te', 't', 'se', 's',
        'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
        'notre', 'nos', 'votre', 'vos',
        'qui', 'que', 'quoi', 'dont', 'lequel', 'laquelle', 'lesquels', 'lesquelles',
        'est', 'sont', 'était', 'étaient', 'été', 'être',
        'sera', 'seront', 'serait', 'seraient',
        'a', 'ai', 'as', 'avons', 'avez', 'ont', 'avait', 'avaient', 'eu', 'avoir',
        'aura', 'auront', 'aurait', 'auraient',
        'fait', 'faire', 'fais', 'faisons', 'faites', 'font',
        'dit', 'dire', 'dis', 'disons', 'dites', 'disent',
        'tout', 'tous', 'toute', 'toutes', 'trop', 'très',
        'aucun', 'aucune', 'chaque', 'quelque', 'quelques',
        'même', 'mêmes', 'autre', 'autres',
        'si', 'oui', 'non', 'ne', 'n', 'pas', 'plus', 'jamais', 'rien', 'personne',
        'peut', 'peuvent', 'pouvoir', 'puis', 'pu',
        'doit', 'doivent', 'devoir', 'dû',
        'veux', 'veut', 'voulons', 'voulez', 'veulent', 'vouloir', 'voulu',
        'y', 'là', 'ici', 'ainsi', 'alors', 'aussi', 'avant', 'après',
        'beaucoup', 'bien', 'comme', 'comment', 'encore', 'entre', 'faut',
        'moins', 'parce', 'pendant', 'peu', 'plusieurs', 'pourquoi',
        'quand', 'quelqu', 'quel', 'quelle', 'quels', 'quelles',
        'seulement', 'suis', 'suivant', 'tant', 'toujours', 'vers', 'voilà', 'vos',
    ],

    'ru': [
        # Russian stopwords
        'а', 'без', 'более', 'больше', 'будет', 'будто', 'бы', 'был', 'была', 'были', 'было', 'быть',
        'в', 'вам', 'вас', 'весь', 'во', 'вот', 'все', 'всё', 'всего', 'всей', 'всем', 'всех', 'всею',
        'всю', 'вся', 'вы', 'да', 'даже', 'два', 'для', 'до', 'другой', 'его', 'ее', 'её', 'ей', 'ему',
        'если', 'есть', 'еще', 'ещё', 'же', 'за', 'зачем', 'здесь', 'и', 'из', 'или', 'им', 'иногда',
        'их', 'к', 'как', 'какая', 'какой', 'когда', 'кто', 'ли', 'либо', 'меня', 'мне', 'может', 'можно',
        'мой', 'моя', 'мы', 'на', 'над', 'надо', 'наш', 'наша', 'не', 'него', 'нее', 'неё', 'ней', 'нельзя',
        'нет', 'ни', 'нибудь', 'них', 'ничего', 'но', 'ну', 'о', 'об', 'один', 'одна', 'одни', 'одно',
        'он', 'она', 'они', 'оно', 'от', 'по', 'под', 'при', 'про', 'раз', 'разве', 'с', 'сам', 'свой',
        'свою', 'себе', 'себя', 'сейчас', 'со', 'совсем', 'так', 'такая', 'также', 'такие', 'такой',
        'там', 'тебе', 'тебя', 'тем', 'теперь', 'то', 'тобой', 'тобою', 'тогда', 'того', 'тоже', 'той',
        'только', 'том', 'ту', 'тут', 'ты', 'у', 'уже', 'хорошо', 'хоть', 'чего', 'чем', 'через', 'что',
        'чтоб', 'чтобы', 'чуть', 'эта', 'эти', 'этим', 'этих', 'это', 'этого', 'этой', 'этом', 'этот',
        'эту', 'я', 'мои', 'свои', 'твой', 'твоя', 'твои', 'ваш', 'ваша', 'ваши',
        'нас', 'вами', 'ними', 'ним', 'нём', 'нами', 'кем', 'чём', 'всем', 'всеми', 'нам', 'им',
        'лишь', 'много', 'немного', 'сколько', 'столько', 'некоторые', 'некоторых', 'которые', 'которых',
        'который', 'которая', 'которое', 'которого', 'которой', 'котором', 'которую',
    ],
}


def add_stopwords_for_language(lang: str, words: list, conn):
    """Add stopwords for a specific language using ON CONFLICT DO NOTHING"""

    print(f"\n{lang.upper()}:")

    # Count existing stopwords
    result = conn.execute(text(
        "SELECT COUNT(*) FROM stop_words WHERE language_code = :lang"
    ), {"lang": lang})
    existing_count = result.fetchone()[0]

    print(f"  Before: {existing_count} stopwords")
    print(f"  Processing: {len(words)} stopwords")

    # Insert with ON CONFLICT DO NOTHING (safe for unique constraint)
    inserted = 0
    for word in words:
        word_lower = word.lower().strip()
        if not word_lower:
            continue

        try:
            result = conn.execute(text("""
                INSERT INTO stop_words (id, word, language_code, is_active, created_at)
                VALUES (gen_random_uuid(), :word, :lang, true, NOW())
                ON CONFLICT (word, language_code) DO NOTHING
            """), {"word": word_lower, "lang": lang})

            if result.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"    ⚠ Error inserting '{word_lower}': {e}")

    # Count final stopwords
    result = conn.execute(text(
        "SELECT COUNT(*) FROM stop_words WHERE language_code = :lang"
    ), {"lang": lang})
    final_count = result.fetchone()[0]

    print(f"  ✅ Inserted: {inserted} new stopwords")
    print(f"  ⏭️  Skipped: {len(words) - inserted} existing stopwords")
    print(f"  After: {final_count} total stopwords")

    return inserted


def add_all_stopwords():
    """Add comprehensive stopwords for all languages"""
    db = db_manager.session_local()
    try:
        print("\n" + "=" * 70)
        print("  ADD COMPREHENSIVE STOPWORDS FOR ALL LANGUAGES")
        print("=" * 70)

        conn = db.connection()
        total_inserted = 0

        for lang in ['de', 'en', 'fr', 'ru']:
            words = STOPWORDS_BY_LANGUAGE.get(lang, [])
            if words:
                inserted = add_stopwords_for_language(lang, words, conn)
                total_inserted += inserted

        db.commit()

        print("\n" + "=" * 70)
        print(f"  COMPLETE - Inserted {total_inserted} new stopwords")
        print("=" * 70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error adding stopwords: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_all_stopwords()
