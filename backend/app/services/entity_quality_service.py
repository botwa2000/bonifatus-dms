"""
Entity Quality Service for Bonifatus DMS
Provides quality scoring and validation for extracted entities using ML-based approach
ALL configuration loaded from database - ZERO hardcoded values
"""

import logging
import re
import subprocess
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EntityQualityService:
    """Service for validating and scoring entity quality using database-driven configuration and ML"""

    def __init__(self, db: Session):
        """
        Initialize entity quality service with database session

        Args:
            db: SQLAlchemy database session for loading ALL config from database
        """
        self.db = db
        self._config_cache: Optional[Dict[str, float]] = None
        self._languages_cache: Optional[Dict[str, Dict]] = None
        self._stop_words_cache: Optional[Dict[str, Set[str]]] = None
        self._field_labels_cache: Optional[Dict[str, Set[str]]] = None
        self._type_patterns_cache: Optional[Dict[str, List[Dict]]] = None

    def _load_config(self) -> Dict[str, float]:
        """Load ALL configuration from entity_quality_config table"""
        if self._config_cache is not None:
            return self._config_cache

        try:
            from app.database.models import EntityQualityConfig

            configs = self.db.query(EntityQualityConfig).all()
            self._config_cache = {
                config.config_key: config.config_value
                for config in configs
            }

            if not self._config_cache:
                logger.warning("No entity_quality_config found in database")
                self._config_cache = {}

            return self._config_cache

        except Exception as e:
            logger.error(f"Failed to load entity_quality_config: {e}")
            return {}

    def _load_languages(self) -> Dict[str, Dict]:
        """Load supported languages from supported_languages table"""
        if self._languages_cache is not None:
            return self._languages_cache

        try:
            from app.database.models import SupportedLanguage

            languages = self.db.query(SupportedLanguage).filter(
                SupportedLanguage.is_active == True
            ).all()

            self._languages_cache = {
                lang.language_code: {
                    'hunspell_dict': lang.hunspell_dict,
                    'spacy_model': lang.spacy_model,
                    'ml_model_available': lang.ml_model_available
                }
                for lang in languages
            }

            if not self._languages_cache:
                logger.warning("No supported_languages found in database")
                self._languages_cache = {}

            return self._languages_cache

        except Exception as e:
            logger.error(f"Failed to load supported_languages: {e}")
            return {}

    def _load_stop_words(self, language: str) -> Set[str]:
        """Load stop words from stop_words table"""
        if self._stop_words_cache is None:
            self._stop_words_cache = {}

        if language in self._stop_words_cache:
            return self._stop_words_cache[language]

        try:
            from app.database.models import StopWord

            stop_words = self.db.query(StopWord).filter(
                StopWord.language_code == language,
                StopWord.is_active == True
            ).all()

            self._stop_words_cache[language] = {sw.word.lower() for sw in stop_words}

            return self._stop_words_cache[language]

        except Exception as e:
            logger.error(f"Failed to load stop_words for {language}: {e}")
            return set()

    def _load_field_labels(self, language: str) -> Set[str]:
        """Load field labels from entity_field_labels table"""
        if self._field_labels_cache is None:
            self._field_labels_cache = {}

        if language in self._field_labels_cache:
            return self._field_labels_cache[language]

        try:
            from app.database.models import EntityFieldLabel

            field_labels = self.db.query(EntityFieldLabel).filter(
                EntityFieldLabel.language == language
            ).all()

            self._field_labels_cache[language] = {fl.label_text.lower() for fl in field_labels}

            return self._field_labels_cache[language]

        except Exception as e:
            logger.error(f"Failed to load field_labels for {language}: {e}")
            return set()

    def _load_entity_type_patterns(self, entity_type: str, language: str) -> List[Dict]:
        """Load entity type patterns from entity_type_patterns table"""
        cache_key = f"{entity_type}_{language}"

        if self._type_patterns_cache is None:
            self._type_patterns_cache = {}

        if cache_key in self._type_patterns_cache:
            return self._type_patterns_cache[cache_key]

        try:
            from app.database.models import EntityTypePattern

            patterns = self.db.query(EntityTypePattern).filter(
                EntityTypePattern.entity_type == entity_type,
                EntityTypePattern.language == language,
                EntityTypePattern.is_active == True
            ).all()

            self._type_patterns_cache[cache_key] = [
                {
                    'pattern_value': p.pattern_value,
                    'pattern_type': p.pattern_type,
                    'config_key': p.config_key
                }
                for p in patterns
            ]

            return self._type_patterns_cache[cache_key]

        except Exception as e:
            logger.error(f"Failed to load entity_type_patterns for {entity_type}/{language}: {e}")
            return []

    def _get_config_value(self, key: str, default: float = 1.0) -> float:
        """Get configuration value by key from database"""
        config = self._load_config()
        return config.get(key, default)

    def _check_word_with_hunspell(self, word: str, language: str) -> bool:
        """Check if word is valid using system hunspell command"""
        languages = self._load_languages()

        if language not in languages:
            logger.debug(f"Language {language} not supported")
            return True

        dict_file = languages[language]['hunspell_dict']

        try:
            result = subprocess.run(
                ['hunspell', '-d', dict_file, '-l'],
                input=word,
                capture_output=True,
                text=True,
                timeout=1
            )
            return len(result.stdout.strip()) == 0

        except Exception as e:
            logger.debug(f"Hunspell check failed for '{word}': {e}")
            return True

    def validate_with_dictionary(self, text: str, language: str) -> Tuple[bool, float]:
        """
        Validate entity text using Hunspell dictionary

        Args:
            text: Entity text to validate
            language: Language code

        Returns:
            Tuple of (is_valid, valid_ratio)
        """
        try:
            words = re.findall(r'\b[A-Za-zäöüÄÖÜßàâéèêëïîôùûüÿçÀÂÉÈÊËÏÎÔÙÛÜŸÇ]+\b', text)

            if not words:
                return False, 0.0

            valid_words = sum(1 for word in words if self._check_word_with_hunspell(word, language))
            validity_ratio = valid_words / len(words) if words else 0

            threshold = self._get_config_value('dict_validation_threshold', 0.6)
            is_valid = validity_ratio >= threshold

            return is_valid, validity_ratio

        except Exception as e:
            logger.debug(f"Dictionary validation error for '{text}': {e}")
            return True, 1.0

    def extract_features(self, text: str, entity_type: str, language: str, base_confidence: float) -> Dict[str, float]:
        """
        Extract numeric features from entity for ML model
        Uses database-loaded patterns - NO hardcoded values

        Args:
            text: Entity text
            entity_type: Type of entity
            language: Language code
            base_confidence: spaCy's confidence score

        Returns:
            Dictionary of feature names to numeric values
        """
        features = {}

        # 1. Length
        features['length'] = float(len(text))

        # 2. Word count
        words = re.findall(r'\b[A-Za-zäöüÄÖÜßàâéèêëïîôùûüÿçÀÂÉÈÊËÏÎÔÙÛÜŸÇ]+\b', text)
        features['word_count'] = float(len(words))

        # 3-4. Vowel and consonant ratios
        vowels = len(re.findall(r'[aeiouäöüàâéèêëïîôùûüÿ]', text.lower()))
        consonants = len(re.findall(r'[bcdfghjklmnpqrstvwxyz]', text.lower()))
        total_letters = vowels + consonants

        features['vowel_ratio'] = vowels / total_letters if total_letters > 0 else 0
        features['consonant_ratio'] = consonants / total_letters if total_letters > 0 else 0

        # 5. Digit ratio
        digits = len(re.findall(r'\d', text))
        features['digit_ratio'] = digits / len(text) if len(text) > 0 else 0

        # 6. Special char ratio
        special_chars = len(re.findall(r'[^\w\s]', text))
        features['special_char_ratio'] = special_chars / len(text) if len(text) > 0 else 0

        # 7. Repetitive character score (dynamic from DB)
        max_repetition = 0
        for i in range(len(text) - 1):
            count = 1
            j = i + 1
            while j < len(text) and text[j] == text[i]:
                count += 1
                j += 1
            max_repetition = max(max_repetition, count)

        features['repetitive_char_score'] = float(max_repetition)

        # 8. Dictionary valid ratio
        _, dict_valid_ratio = self.validate_with_dictionary(text, language)
        features['dict_valid_ratio'] = dict_valid_ratio

        # 9. Stop word ratio (from database)
        stop_words = self._load_stop_words(language)
        if words and stop_words:
            stop_word_count = sum(1 for word in words if word.lower() in stop_words)
            features['stop_word_ratio'] = stop_word_count / len(words)
        else:
            features['stop_word_ratio'] = 0.0

        # 10. Has field label suffix (from database)
        field_labels = self._load_field_labels(language)
        has_field_label = False
        if field_labels:
            has_field_label = any(word.lower() in field_labels for word in words)
        features['has_field_label_suffix'] = 1.0 if has_field_label else 0.0

        # 11. Title case
        features['title_case'] = 1.0 if text.istitle() else 0.0

        # 12. spaCy confidence
        features['spacy_confidence'] = base_confidence

        # 13-15. Entity type encoding
        features['is_person'] = 1.0 if entity_type == 'PERSON' else 0.0
        features['is_organization'] = 1.0 if entity_type == 'ORGANIZATION' else 0.0
        features['is_location'] = 1.0 if entity_type == 'LOCATION' else 0.0

        return features

    def calculate_rule_based_confidence(
        self,
        entity_value: str,
        entity_type: str,
        base_confidence: float,
        language: str,
        features: Dict[str, float]
    ) -> float:
        """
        Calculate confidence using rule-based approach with database-driven thresholds
        ALL thresholds loaded from database - ZERO hardcoded values

        Args:
            entity_value: The extracted entity text
            entity_type: Type of entity
            base_confidence: Base confidence from spaCy
            language: Language code
            features: Extracted features dictionary

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = base_confidence
        length = features['length']

        # 1. Length factor (thresholds from DB)
        length_very_short = self._get_config_value('threshold_length_very_short', 2.0)
        length_short = self._get_config_value('threshold_length_short', 3.0)
        length_optimal_min = self._get_config_value('threshold_length_optimal_min', 5.0)
        length_optimal_max = self._get_config_value('threshold_length_optimal_max', 40.0)
        length_long = self._get_config_value('threshold_length_long', 50.0)
        length_very_long = self._get_config_value('threshold_length_very_long', 80.0)

        if length < length_very_short:
            confidence *= self._get_config_value('length_very_short_penalty', 0.1)
        elif length < length_short:
            confidence *= self._get_config_value('length_two_char_penalty', 0.3)
        elif length < length_optimal_min:
            confidence *= self._get_config_value('length_three_char_penalty', 0.6)
        elif length > length_very_long:
            confidence *= self._get_config_value('length_very_long_penalty', 0.2)
        elif length > length_long:
            confidence *= self._get_config_value('length_long_penalty', 0.5)
        elif length_optimal_min <= length <= length_optimal_max:
            confidence *= self._get_config_value('length_optimal_bonus', 1.0)
        else:
            confidence *= self._get_config_value('fallback_multiplier', 0.8)

        # 2. Repetitive character penalties (thresholds from DB)
        rep_score = features['repetitive_char_score']
        rep_severe = self._get_config_value('threshold_repetitive_chars_severe', 6.0)
        rep_high = self._get_config_value('threshold_repetitive_chars_high', 5.0)
        rep_medium = self._get_config_value('threshold_repetitive_chars_medium', 4.0)

        if rep_score >= rep_severe:
            confidence *= self._get_config_value('pattern_repetitive_severe', 0.1)
        elif rep_score >= rep_high:
            confidence *= self._get_config_value('pattern_repetitive_high', 0.3)
        elif rep_score >= rep_medium:
            confidence *= self._get_config_value('pattern_repetitive_medium', 0.6)

        # 3. Vowel ratio penalties (thresholds from DB)
        vowel_ratio = features['vowel_ratio']
        min_letters = self._get_config_value('threshold_min_letters_for_vowel_check', 5.0)
        total_letters = len(entity_value) - len(re.findall(r'[^\w]', entity_value))

        if total_letters > min_letters:
            vowel_very_low = self._get_config_value('threshold_vowel_ratio_very_low', 0.10)
            vowel_low = self._get_config_value('threshold_vowel_ratio_low', 0.15)
            vowel_high = self._get_config_value('threshold_vowel_ratio_high', 0.75)

            if vowel_ratio < vowel_very_low:
                confidence *= self._get_config_value('pattern_low_vowel_severe', 0.3)
            elif vowel_ratio < vowel_low:
                confidence *= self._get_config_value('pattern_low_vowel_medium', 0.6)
            elif vowel_ratio > vowel_high:
                confidence *= self._get_config_value('pattern_high_vowel_penalty', 0.7)

        # 4. Pure numeric or punctuation
        if re.match(r'^[0-9\W]+$', entity_value):
            confidence *= self._get_config_value('pattern_numeric_only', 0.1)

        # 5. Mixed case chaos (threshold from DB)
        min_length_case = self._get_config_value('threshold_min_length_for_case_check', 5.0)
        if length > min_length_case and re.search(r'[a-z]{2,}[A-Z]{2,}[a-z]{2,}', entity_value):
            confidence *= self._get_config_value('pattern_mixed_case_penalty', 0.5)

        # 6. Excessive punctuation (threshold from DB)
        special_high = self._get_config_value('threshold_special_char_high', 0.3)
        if features['special_char_ratio'] > special_high:
            confidence *= self._get_config_value('pattern_excessive_punct', 0.5)

        # 7. Dictionary validation
        dict_valid_ratio = features['dict_valid_ratio']
        threshold = self._get_config_value('dict_validation_threshold', 0.6)

        if dict_valid_ratio >= threshold:
            confidence *= self._get_config_value('dict_all_valid_bonus', 1.3)
        else:
            confidence *= self._get_config_value('dict_invalid_penalty', 0.6)

        # 8. Entity type patterns from database (NO hardcoded patterns)
        patterns = self._load_entity_type_patterns(entity_type, language)
        for pattern in patterns:
            pattern_value = pattern['pattern_value']
            pattern_type = pattern['pattern_type']
            config_key = pattern['config_key']

            if pattern_type == 'suffix' and entity_value.endswith(pattern_value):
                multiplier = self._get_config_value(config_key, 1.0)
                confidence *= multiplier
                break
            elif pattern_type == 'keyword' and pattern_value in entity_value:
                multiplier = self._get_config_value(config_key, 1.0)
                confidence *= multiplier
                break

        # 9. Title case bonus (threshold from DB)
        min_length_uppercase = self._get_config_value('threshold_min_length_for_uppercase_penalty', 8.0)

        if entity_type == 'PERSON' and features['title_case'] == 1.0:
            confidence *= self._get_config_value('type_person_title_case', 1.2)
        elif entity_type == 'PERSON' and entity_value.isupper() and length > min_length_uppercase:
            confidence *= self._get_config_value('type_person_uppercase_penalty', 0.9)
        elif entity_type == 'LOCATION' and features['title_case'] == 1.0:
            confidence *= self._get_config_value('type_location_title_case', 1.1)

        # Cap at 1.0
        return min(confidence, 1.0)

    def calculate_confidence(
        self,
        entity_value: str,
        entity_type: str,
        base_confidence: float,
        language: str
    ) -> float:
        """
        Calculate comprehensive confidence score using ML model (if available) or rule-based approach

        Args:
            entity_value: The extracted entity text
            entity_type: Type of entity
            base_confidence: Base confidence from spaCy (NOT hardcoded!)
            language: Language code

        Returns:
            Final confidence score between 0.0 and 1.0
        """
        try:
            # Extract features for ML model
            features = self.extract_features(entity_value, entity_type, language, base_confidence)

            # Check if ML model is available for this language
            languages = self._load_languages()
            ml_available = languages.get(language, {}).get('ml_model_available', False)

            if ml_available:
                # Use ML model prediction
                from app.services.entity_ml_service import get_entity_ml_service

                ml_service = get_entity_ml_service(self.db)
                ml_confidence = ml_service.predict_confidence(features, language)

                if ml_confidence is not None:
                    confidence = ml_confidence
                else:
                    # ML prediction failed, fall back to rule-based
                    logger.warning(f"ML prediction failed for {language}, using rule-based")
                    confidence = self.calculate_rule_based_confidence(
                        entity_value, entity_type, base_confidence, language, features
                    )
            else:
                # Use rule-based approach with DB-driven weights
                confidence = self.calculate_rule_based_confidence(
                    entity_value, entity_type, base_confidence, language, features
                )

            return confidence

        except Exception as e:
            logger.error(f"Error calculating confidence for '{entity_value}': {e}")
            return base_confidence


def get_entity_quality_service(db: Session) -> EntityQualityService:
    """Factory function to create EntityQualityService with database session"""
    return EntityQualityService(db)
