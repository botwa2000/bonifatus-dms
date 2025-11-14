"""
Keyword Extraction Service for Bonifatus DMS
Extracts semantic keywords from document text for classification
Language-aware with stop word filtering from database
"""

import re
import logging
from typing import List, Tuple, Dict
from collections import Counter
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class KeywordExtractionService:
    """Service for extracting semantic keywords from document text"""

    def __init__(self):
        """Initialize keyword extraction service"""
        self._stop_words_cache: Dict[str, set] = {}

    def get_stop_words(self, db: Session, language: str) -> set:
        """
        Load stop words for a specific language from database

        Args:
            db: Database session
            language: Language code (en, de, ru, etc)

        Returns:
            Set of stop words for the language
        """
        if language in self._stop_words_cache:
            logger.debug(f"Using cached stop words for language: {language} ({len(self._stop_words_cache[language])} words)")
            return self._stop_words_cache[language]

        try:
            from app.database.models import StopWord

            logger.debug(f"Querying database for stop words, language: {language}")

            stop_words = db.query(StopWord).filter(
                StopWord.language_code == language,
                StopWord.is_active == True
            ).all()

            logger.debug(f"Query returned {len(stop_words)} stop word records for language: {language}")

            stop_word_set = {sw.word.lower() for sw in stop_words}

            self._stop_words_cache[language] = stop_word_set

            if len(stop_word_set) == 0:
                logger.warning(f"No stop words found in database for language: {language}. Keywords will not be filtered!")
            else:
                logger.info(f"Loaded {len(stop_word_set)} stop words for language: {language}")

            return stop_word_set

        except Exception as e:
            logger.error(f"Failed to load stop words from database for language '{language}': {e}", exc_info=True)
            return set()

    def clear_stop_words_cache(self):
        """Clear cached stop words (useful after database updates)"""
        self._stop_words_cache = {}

    def cleanse_text(self, text: str) -> str:
        """
        Cleanse text while preserving searchable content
        - Remove control characters
        - Normalize whitespace
        - Remove excessive punctuation (!!!, ???)
        - Preserve emails, URLs, numbers (valuable for search)

        Args:
            text: Raw text to cleanse

        Returns:
            Cleansed text
        """
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)

        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{3,}', '...', text)

        text = re.sub(r'\s+', ' ', text)

        text = text.strip()

        return text

    def normalize_text(self, text: str) -> str:
        """
        Normalize text for keyword extraction
        - Convert to lowercase for matching
        - Apply cleansing

        Args:
            text: Raw text to normalize

        Returns:
            Normalized text
        """
        text = self.cleanse_text(text)
        text = text.lower()
        return text

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words
        - Split on whitespace and punctuation
        - Keep words with letters
        - Min length 3 characters (reduced noise from OCR errors)

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        tokens = re.findall(r'\b[a-zа-яäöüß]{3,}\b', text, re.IGNORECASE)
        return tokens

    def filter_tokens(
        self,
        tokens: List[str],
        stop_words: set,
        max_length: int = 50
    ) -> List[str]:
        """
        Filter tokens to remove stop words and apply length limit
        Also filters likely OCR errors and low-quality tokens

        Args:
            tokens: List of tokens to filter
            stop_words: Set of stop words to remove
            max_length: Maximum keyword length (prevents full sentences)

        Returns:
            Filtered list of tokens
        """
        filtered = []

        for token in tokens:
            token_lower = token.lower()

            # Skip stop words
            if token_lower in stop_words:
                continue

            # Skip too long (likely full sentences/OCR errors)
            if len(token) > max_length:
                continue

            # Skip pure numbers
            if re.match(r'^\d+$', token):
                continue

            # Skip tokens with excessive repeated characters (OCR noise: 'mmm', 'aaa')
            if re.search(r'(.)\1{2,}', token_lower):
                continue

            # Skip tokens that are too short after validation (edge case safety)
            if len(token) < 3:
                continue

            filtered.append(token_lower)

        return filtered

    def extract_keywords(
        self,
        text: str,
        db: Session,
        language: str = 'en',
        max_keywords: int = 50,
        min_frequency: int = 2,
        user_id: str = None,
        stopwords: set = None
    ) -> List[Tuple[str, int, float]]:
        """
        Extract keywords using HYBRID approach with CORRECT order:
        1. Load category keywords FIRST (these must NEVER be filtered)
        2. Filter stopwords BUT preserve category keywords
        3. Extract keywords with priority scoring

        This ensures important classification terms like "rechnung", "invoice" are
        ALWAYS extracted even if they appear only once or in stopwords.

        Args:
            text: Document text
            db: Database session for loading stop words and category keywords
            language: Language code for stop word filtering and tokenization
            max_keywords: Maximum number of keywords to return (default: 1000)
            min_frequency: Minimum frequency for a keyword
            user_id: User ID to get their category keywords
            stopwords: Optional pre-loaded stopwords set (if None, loads from db for language)

        Returns:
            List of tuples (keyword, frequency, relevance_score)
            Sorted by relevance (highest first)
        """
        try:
            if not text or len(text.strip()) < 10:
                logger.warning("Text too short for keyword extraction")
                return []

            # STEP 1: Get category keywords FIRST (these must NEVER be filtered out)
            category_keywords_set = set()
            if user_id:
                from sqlalchemy import text as sql_text
                result = db.execute(sql_text("""
                    SELECT DISTINCT LOWER(ck.keyword)
                    FROM category_keywords ck
                    JOIN categories c ON ck.category_id = c.id
                    WHERE c.user_id = :user_id
                    AND ck.language_code = :lang
                """), {'user_id': user_id, 'lang': language})
                category_keywords_set = {row[0] for row in result}
                logger.info(f"[KEYWORD EXTRACTION] Loaded {len(category_keywords_set)} category keywords for user (lang={language})")
                if category_keywords_set:
                    logger.info(f"[KEYWORD EXTRACTION] Sample category keywords: {', '.join(list(category_keywords_set)[:10])}")

            # STEP 2: Load stopwords and tokenize
            stop_words = stopwords if stopwords is not None else self.get_stop_words(db, language)
            logger.info(f"[KEYWORD EXTRACTION] Loaded {len(stop_words)} stopwords for language '{language}'")

            normalized_text = self.normalize_text(text)
            tokens = self.tokenize(normalized_text)
            logger.info(f"[KEYWORD EXTRACTION] Tokenized {len(tokens)} total tokens from text")

            # STEP 3: Filter stopwords BUT preserve category keywords
            # Category keywords MUST be kept even if they appear in stopwords!
            filtered_tokens = []
            preserved_category_keywords = set()

            for token in tokens:
                if token in category_keywords_set:
                    # Keep category keyword even if it's a stopword!
                    filtered_tokens.append(token)
                    preserved_category_keywords.add(token)
                elif token not in stop_words:
                    # Keep non-stopword
                    filtered_tokens.append(token)

            logger.info(f"[KEYWORD EXTRACTION] After stopword filtering: {len(filtered_tokens)} tokens (preserved {len(preserved_category_keywords)} category keywords)")
            if preserved_category_keywords:
                logger.info(f"[KEYWORD EXTRACTION] Preserved category keywords found in text: {', '.join(preserved_category_keywords)}")

            # STEP 3.5: Spell check filter (preserve category keywords)
            # Remove obvious OCR garbage that aren't real words
            try:
                from app.services.ocr_service import ocr_service

                # Call new check_spelling API with set of unique tokens
                unique_tokens = set(filtered_tokens)
                misspelled = ocr_service.check_spelling(unique_tokens, language)

                spell_filtered_tokens = []
                ocr_garbage_count = 0

                for token in filtered_tokens:
                    # Always preserve category keywords (even if "misspelled")
                    if token in category_keywords_set:
                        spell_filtered_tokens.append(token)
                    # Keep words NOT in misspelled set
                    elif token not in misspelled:
                        spell_filtered_tokens.append(token)
                    # Also keep if it appears frequently (likely domain-specific term)
                    elif filtered_tokens.count(token) >= min_frequency * 2:
                        spell_filtered_tokens.append(token)
                    else:
                        ocr_garbage_count += 1

                filtered_tokens = spell_filtered_tokens
                logger.info(f"[KEYWORD EXTRACTION] After spell check: {len(filtered_tokens)} tokens (removed {ocr_garbage_count} OCR garbage words)")
            except Exception as e:
                logger.warning(f"[KEYWORD EXTRACTION] Spell check failed, continuing without it: {e}")

            if not filtered_tokens:
                logger.warning("No keywords after filtering")
                return []

            frequency = Counter(filtered_tokens)
            total_tokens = len(filtered_tokens)
            max_freq = max(frequency.values())

            # Adaptive min_frequency for short documents
            # Short documents (like invoices) naturally have low word repetition
            # Use min_frequency=1 for short docs to avoid empty keyword lists
            adaptive_min_frequency = 1 if total_tokens < 200 else min_frequency
            if adaptive_min_frequency != min_frequency:
                logger.info(f"[KEYWORD EXTRACTION] Short document detected ({total_tokens} tokens), using adaptive min_frequency={adaptive_min_frequency} instead of {min_frequency}")

            # STEP 4: Extract keywords with priority scoring
            keywords = []
            extracted_words = set()

            # Priority 1: Words that match category keywords (even if freq=1)
            category_matches = 0
            for word in frequency:
                if word in category_keywords_set:
                    count = frequency[word]
                    relevance = (count / max_freq) * 100
                    # Boost relevance for category matches
                    relevance = min(relevance * 1.5, 100.0)
                    keywords.append((word, count, relevance))
                    extracted_words.add(word)
                    category_matches += 1

            logger.info(f"[KEYWORD EXTRACTION] Found {category_matches} category keyword matches in document")

            # Priority 2: Top frequent words (up to max_keywords, skip already extracted)
            for word, count in frequency.most_common(max_keywords):
                # Skip if already extracted as category keyword
                if word in extracted_words:
                    continue

                # Defensive validation with detailed logging
                if not word or not isinstance(word, str):
                    logger.warning(f"Skipping keyword with invalid word: word={repr(word)}, type={type(word).__name__}, count={count}")
                    continue

                if count is None or not isinstance(count, int) or count < adaptive_min_frequency:
                    logger.debug(f"Skipping keyword '{word}' with low frequency: count={count}, min_required={adaptive_min_frequency}")
                    continue

                relevance = (count / max_freq) * 100

                # Defensive check: ensure relevance calculation succeeded
                if relevance is None or not isinstance(relevance, (int, float)):
                    logger.warning(f"Skipping keyword '{word}' with invalid relevance: relevance={repr(relevance)}, type={type(relevance).__name__ if relevance is not None else 'NoneType'}, count={count}, max_freq={max_freq}")
                    continue

                keywords.append((word, count, relevance))
                extracted_words.add(word)

            # Sort by relevance (category keywords will be highest due to 1.5x boost)
            keywords.sort(key=lambda x: x[2], reverse=True)

            logger.info(f"Extracted {len(keywords)} keywords from {total_tokens} tokens (lang: {language}, category_matches: {len([k for k in keywords if k[2] > 100])})")

            return keywords

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []

    def extract_phrases(
        self,
        text: str,
        db: Session,
        language: str = 'en',
        max_phrases: int = 20,
        ngram_size: int = 2
    ) -> List[Tuple[str, int]]:
        """
        Extract multi-word phrases (n-grams) from text

        Args:
            text: Document text
            db: Database session for loading stop words
            language: Language code
            max_phrases: Maximum number of phrases to return
            ngram_size: Number of words per phrase (2 = bigrams, 3 = trigrams)

        Returns:
            List of tuples (phrase, frequency)
        """
        try:
            if not text or len(text.strip()) < 20:
                return []

            stop_words = self.get_stop_words(db, language)

            normalized_text = self.normalize_text(text)
            tokens = self.tokenize(normalized_text)
            filtered_tokens = self.filter_tokens(tokens, stop_words, max_length=30)

            if len(filtered_tokens) < ngram_size:
                return []

            ngrams = []
            for i in range(len(filtered_tokens) - ngram_size + 1):
                phrase = ' '.join(filtered_tokens[i:i+ngram_size])
                ngrams.append(phrase)

            phrase_frequency = Counter(ngrams)

            phrases = phrase_frequency.most_common(max_phrases)

            logger.info(f"Extracted {len(phrases)} {ngram_size}-gram phrases (lang: {language})")

            return phrases

        except Exception as e:
            logger.error(f"Phrase extraction failed: {e}")
            return []

    def get_keyword_summary(
        self,
        keywords: List[Tuple[str, int, float]],
        top_n: int = 10
    ) -> str:
        """
        Generate a human-readable summary of top keywords

        Args:
            keywords: List of (keyword, frequency, relevance) tuples
            top_n: Number of top keywords to include

        Returns:
            Comma-separated string of top keywords
        """
        if not keywords:
            return ""

        top_keywords = [kw[0] for kw in keywords[:top_n]]
        return ", ".join(top_keywords)


keyword_extraction_service = KeywordExtractionService()
