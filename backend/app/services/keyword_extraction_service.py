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
        - Min length 2 characters

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        tokens = re.findall(r'\b[a-zа-яäöüß]{2,}\b', text, re.IGNORECASE)
        return tokens

    def filter_tokens(
        self,
        tokens: List[str],
        stop_words: set,
        max_length: int = 50
    ) -> List[str]:
        """
        Filter tokens to remove stop words and apply length limit

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

            if token_lower in stop_words:
                continue

            if len(token) > max_length:
                continue

            if re.match(r'^\d+$', token):
                continue

            filtered.append(token_lower)

        return filtered

    def extract_keywords(
        self,
        text: str,
        db: Session,
        language: str = 'en',
        max_keywords: int = 50,
        min_frequency: int = 1
    ) -> List[Tuple[str, int, float]]:
        """
        Extract keywords from text using frequency analysis

        Args:
            text: Document text
            db: Database session for loading stop words
            language: Language code for stop word filtering
            max_keywords: Maximum number of keywords to return
            min_frequency: Minimum frequency for a keyword

        Returns:
            List of tuples (keyword, frequency, relevance_score)
            Sorted by relevance (highest first)
        """
        try:
            if not text or len(text.strip()) < 10:
                logger.warning("Text too short for keyword extraction")
                return []

            stop_words = self.get_stop_words(db, language)

            normalized_text = self.normalize_text(text)

            tokens = self.tokenize(normalized_text)

            filtered_tokens = self.filter_tokens(tokens, stop_words)

            if not filtered_tokens:
                logger.warning("No keywords after filtering")
                return []

            frequency = Counter(filtered_tokens)

            total_tokens = len(filtered_tokens)
            max_freq = max(frequency.values())

            keywords = []
            for word, count in frequency.most_common(max_keywords):
                if count < min_frequency:
                    continue

                relevance = (count / max_freq) * 100

                keywords.append((word, count, relevance))

            logger.info(f"Extracted {len(keywords)} keywords from {total_tokens} tokens (lang: {language})")

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
