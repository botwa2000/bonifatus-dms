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
        stopwords: set = None,
        rejected_entities: List[Dict] = None
    ) -> List[Tuple[str, int, float]]:
        """
        Extract keywords using HYBRID approach with TF-IDF scoring:
        1. Load category keywords FIRST (these must NEVER be filtered)
        2. Filter stopwords BUT preserve category keywords
        3. Extract keywords with TF-IDF relevance scoring
        4. Convert rejected entities to keywords (if provided)
        5. Update corpus statistics for ML learning

        This ensures important classification terms like "rechnung", "invoice" are
        ALWAYS extracted even if they appear only once or in stopwords.

        Args:
            text: Document text
            db: Database session for loading stop words and category keywords
            language: Language code for stop word filtering and tokenization
            max_keywords: Maximum number of keywords to return (default: 50)
            min_frequency: Minimum frequency for a keyword
            user_id: User ID to get their category keywords and personalized IDF scores
            stopwords: Optional pre-loaded stopwords set (if None, loads from db for language)
            rejected_entities: List of entities rejected by quality service (e.g., low-confidence ORGs)
                              Format: [{'entity_value': 'PATIENT', 'entity_type': 'ORGANIZATION', 'confidence': 0.65}, ...]

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
            if stop_words:
                sample_stopwords = list(stop_words)[:10]
                logger.info(f"[KEYWORD EXTRACTION] Sample stop words: {sample_stopwords}")

            normalized_text = self.normalize_text(text)
            tokens = self.tokenize(normalized_text)
            logger.info(f"[KEYWORD EXTRACTION] Tokenized {len(tokens)} total tokens from text")

            # STEP 3: Filter stopwords BUT preserve category keywords
            # Category keywords MUST be kept even if they appear in stopwords!
            filtered_tokens = []
            preserved_category_keywords = set()
            filtered_out_stopwords = []

            for token in tokens:
                if token in category_keywords_set:
                    # Keep category keyword even if it's a stopword!
                    filtered_tokens.append(token)
                    preserved_category_keywords.add(token)
                elif token not in stop_words:
                    # Keep non-stopword
                    filtered_tokens.append(token)
                else:
                    # This is a stop word - track what we're filtering
                    filtered_out_stopwords.append(token)

            if filtered_out_stopwords:
                logger.info(f"[KEYWORD EXTRACTION] Filtered out {len(filtered_out_stopwords)} stop words: {filtered_out_stopwords[:20]}")

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

                    # Calculate TF-IDF relevance
                    tf = count / total_tokens
                    idf = self._calculate_idf(word, language, user_id, db)
                    tfidf_score = tf * idf
                    relevance = tfidf_score * 100

                    # Boost relevance for category matches (1.5x multiplier)
                    relevance = min(relevance * 1.5, 150.0)

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

                # Calculate TF-IDF relevance
                tf = count / total_tokens
                idf = self._calculate_idf(word, language, user_id, db)
                tfidf_score = tf * idf
                relevance = tfidf_score * 100

                # Defensive check: ensure relevance calculation succeeded
                if relevance is None or not isinstance(relevance, (int, float)):
                    logger.warning(f"Skipping keyword '{word}' with invalid relevance: relevance={repr(relevance)}, type={type(relevance).__name__ if relevance is not None else 'NoneType'}, count={count}, tf={tf}, idf={idf}")
                    continue

                keywords.append((word, count, relevance))
                extracted_words.add(word)

            # Priority 3: Convert rejected entities to keywords (if confidence in conversion range)
            entity_conversions = 0
            if rejected_entities:
                from app.database.models import KeywordExtractionConfig

                # Load entity-to-keyword conversion thresholds
                min_conf_result = db.query(KeywordExtractionConfig).filter(
                    KeywordExtractionConfig.config_key == 'org_to_keyword_min_confidence'
                ).first()
                min_confidence = min_conf_result.config_value if min_conf_result else 0.50

                max_conf_result = db.query(KeywordExtractionConfig).filter(
                    KeywordExtractionConfig.config_key == 'org_to_keyword_max_confidence'
                ).first()
                max_confidence = max_conf_result.config_value if max_conf_result else 0.85

                logger.info(f"[ENTITY→KEYWORD] Processing {len(rejected_entities)} rejected entities (conversion range: {min_confidence}-{max_confidence})")

                for entity in rejected_entities:
                    entity_value = entity.get('entity_value', '').strip()
                    entity_type = entity.get('entity_type', '')
                    confidence = entity.get('confidence', 0.0)

                    # Only convert ORG entities in the confidence range
                    if entity_type != 'ORGANIZATION':
                        continue

                    if confidence < min_confidence or confidence >= max_confidence:
                        continue

                    # Normalize entity value to keyword format (lowercase)
                    keyword = entity_value.lower()

                    # Skip if already extracted or too short
                    if keyword in extracted_words or len(keyword) < 3:
                        continue

                    # Calculate synthetic relevance based on confidence
                    # Map confidence 0.50-0.85 to relevance 20-50
                    relevance = 20 + ((confidence - min_confidence) / (max_confidence - min_confidence)) * 30

                    # Add as keyword with frequency=1 (entity appeared once)
                    keywords.append((keyword, 1, relevance))
                    extracted_words.add(keyword)
                    entity_conversions += 1

                logger.info(f"[ENTITY→KEYWORD] Converted {entity_conversions} rejected ORG entities to keywords")

            # Sort by relevance (category keywords will be highest due to 1.5x boost)
            keywords.sort(key=lambda x: x[2], reverse=True)

            # Update corpus statistics for ML learning (after successful extraction)
            self._update_corpus_stats(filtered_tokens, language, user_id, db)

            logger.info(f"[KEYWORD EXTRACTION] Extracted {len(keywords)} keywords from {total_tokens} tokens (lang: {language}, category_matches: {category_matches}, entity_conversions: {entity_conversions})")

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

    def _calculate_idf(
        self,
        word: str,
        language: str,
        user_id: str,
        db: Session
    ) -> float:
        """
        Calculate hybrid IDF score blending global and user corpus statistics

        IDF formula: log((N + smoothing) / (df + smoothing))
        Hybrid blend: alpha * global_idf + (1-alpha) * user_idf

        Alpha decay: Starts at 0.7 (favor global patterns), decays to 0.3 as user uploads more docs

        Args:
            word: Word to calculate IDF for
            language: Language code
            user_id: User ID (None = global only)
            db: Database session

        Returns:
            IDF score (higher = rarer word = more important)
        """
        import math
        from app.database.models import (
            KeywordExtractionConfig,
            GlobalCorpusStats,
            UserCorpusStats
        )

        try:
            # Load config
            config_query = db.query(KeywordExtractionConfig)
            tfidf_enabled = config_query.filter(
                KeywordExtractionConfig.config_key == 'tfidf_enabled'
            ).first()

            # If TF-IDF disabled, return neutral score
            if not tfidf_enabled or tfidf_enabled.config_value == 0.0:
                return 1.0

            smoothing = config_query.filter(
                KeywordExtractionConfig.config_key == 'tfidf_smoothing'
            ).first()
            smoothing = smoothing.config_value if smoothing else 1.0

            # Calculate global IDF
            global_stat = db.query(GlobalCorpusStats).filter(
                GlobalCorpusStats.word == word.lower(),
                GlobalCorpusStats.language == language
            ).first()

            if global_stat and global_stat.total_documents > 0:
                global_idf = math.log(
                    (global_stat.total_documents + smoothing) /
                    (global_stat.document_count + smoothing)
                )
            else:
                # Unknown word = high IDF (rare, likely domain-specific)
                global_idf = 5.0

            # If no user context, return global IDF only
            if not user_id:
                return global_idf

            # Calculate user IDF
            user_stat = db.query(UserCorpusStats).filter(
                UserCorpusStats.user_id == user_id,
                UserCorpusStats.word == word.lower(),
                UserCorpusStats.language == language
            ).first()

            if user_stat and user_stat.total_documents > 0:
                user_idf = math.log(
                    (user_stat.total_documents + smoothing) /
                    (user_stat.document_count + smoothing)
                )
            else:
                # New word for user = high IDF
                user_idf = 5.0

            # Calculate hybrid blending alpha (decays as user uploads more)
            user_total_docs = user_stat.total_documents if user_stat else 0

            alpha_initial = config_query.filter(
                KeywordExtractionConfig.config_key == 'ml_blend_alpha_initial'
            ).first()
            alpha_initial = alpha_initial.config_value if alpha_initial else 0.7

            alpha_decay = config_query.filter(
                KeywordExtractionConfig.config_key == 'ml_blend_alpha_decay'
            ).first()
            alpha_decay = alpha_decay.config_value if alpha_decay else 0.01

            alpha_min = config_query.filter(
                KeywordExtractionConfig.config_key == 'ml_blend_alpha_min'
            ).first()
            alpha_min = alpha_min.config_value if alpha_min else 0.3

            # Alpha decay formula: starts high (favor global), decays to min (favor user patterns)
            alpha = max(alpha_min, alpha_initial - (alpha_decay * user_total_docs))

            # Blend global and user IDF
            hybrid_idf = alpha * global_idf + (1 - alpha) * user_idf

            logger.debug(f"[TF-IDF] '{word}': global_idf={global_idf:.3f}, user_idf={user_idf:.3f}, alpha={alpha:.2f}, hybrid_idf={hybrid_idf:.3f}")

            return hybrid_idf

        except Exception as e:
            logger.error(f"Failed to calculate IDF for '{word}': {e}")
            return 1.0  # Fallback to neutral score

    def _update_corpus_stats(
        self,
        words: List[str],
        language: str,
        user_id: str,
        db: Session
    ):
        """
        Update both global and user corpus statistics after document processing

        For each unique word:
        - Increment document_count (how many docs contain this word)
        - Increment total_documents (total docs processed)

        Args:
            words: List of all words from the document (may contain duplicates)
            language: Language code
            user_id: User ID (None = global only)
            db: Database session
        """
        from app.database.models import (
            GlobalCorpusStats,
            UserCorpusStats,
            KeywordExtractionConfig
        )
        from sqlalchemy import func
        import uuid

        try:
            # Check privacy settings for global contribution
            config_query = db.query(KeywordExtractionConfig)
            min_users = config_query.filter(
                KeywordExtractionConfig.config_key == 'global_ml_min_users'
            ).first()
            min_users = int(min_users.config_value) if min_users else 5

            # Count unique users (privacy check)
            from app.database.models import User
            total_users = db.query(func.count(User.id)).scalar()

            # Get unique words from document
            unique_words = set(word.lower() for word in words if word and len(word) >= 2)

            # Update GLOBAL corpus stats (if privacy threshold met)
            if total_users >= min_users:
                for word in unique_words:
                    global_stat = db.query(GlobalCorpusStats).filter(
                        GlobalCorpusStats.word == word,
                        GlobalCorpusStats.language == language
                    ).first()

                    if global_stat:
                        # Word exists: increment counts
                        global_stat.document_count += 1
                        global_stat.total_documents += 1
                    else:
                        # New word: create entry
                        new_stat = GlobalCorpusStats(
                            word=word,
                            language=language,
                            document_count=1,
                            total_documents=1
                        )
                        db.add(new_stat)

            # Update USER corpus stats (always, regardless of privacy settings)
            if user_id:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

                for word in unique_words:
                    user_stat = db.query(UserCorpusStats).filter(
                        UserCorpusStats.user_id == user_uuid,
                        UserCorpusStats.word == word,
                        UserCorpusStats.language == language
                    ).first()

                    if user_stat:
                        # Word exists: increment counts
                        user_stat.document_count += 1
                        user_stat.total_documents += 1
                    else:
                        # New word: create entry
                        new_stat = UserCorpusStats(
                            user_id=user_uuid,
                            word=word,
                            language=language,
                            document_count=1,
                            total_documents=1
                        )
                        db.add(new_stat)

            db.commit()
            logger.info(f"[CORPUS] Updated stats for {len(unique_words)} unique words (lang: {language}, user: {user_id or 'global'})")

        except Exception as e:
            logger.error(f"Failed to update corpus stats: {e}")
            db.rollback()

    def reset_user_learning(
        self,
        user_id: str,
        db: Session
    ):
        """
        Clear user's learning history (corpus stats and training data)

        Called when user resets their categories to start fresh.
        Global corpus stats are NOT affected (shared across all users).

        Args:
            user_id: User ID to reset
            db: Database session
        """
        from app.database.models import (
            UserCorpusStats,
            KeywordTrainingData
        )
        import uuid

        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

            # Delete user corpus stats
            deleted_corpus = db.query(UserCorpusStats).filter(
                UserCorpusStats.user_id == user_uuid
            ).delete()

            # Delete user training data
            deleted_training = db.query(KeywordTrainingData).filter(
                KeywordTrainingData.user_id == user_uuid
            ).delete()

            db.commit()

            logger.info(f"[RESET] Cleared user learning for user {user_id}: {deleted_corpus} corpus entries, {deleted_training} training entries")

        except Exception as e:
            logger.error(f"Failed to reset user learning for {user_id}: {e}")
            db.rollback()
            raise

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
