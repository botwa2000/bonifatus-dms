"""
Entity Quality Service for Bonifatus DMS
Provides quality scoring and validation for extracted entities
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class EntityQualityService:
    """Service for validating and scoring entity quality"""

    def __init__(self):
        """Initialize entity quality service with Hunspell dictionaries"""
        self._hunspell_cache = {}  # Cache Hunspell objects per language
        self._dict_paths = {
            'de': ('de_DE', 'de_DE'),
            'en': ('en_US', 'en_US'),
            'fr': ('fr_FR', 'fr_FR'),
            'ru': ('ru_RU', 'ru_RU')
        }

    def _get_hunspell(self, language: str):
        """Get or create Hunspell object for language"""
        if language in self._hunspell_cache:
            return self._hunspell_cache[language]

        if language not in self._dict_paths:
            return None

        try:
            from hunspell import Hunspell
            dict_file, aff_file = self._dict_paths[language]
            hobj = Hunspell(dict_file, hunspell_data_dir='/usr/share/hunspell')
            self._hunspell_cache[language] = hobj
            logger.info(f"✓ Loaded Hunspell dictionary for {language}")
            return hobj

        except Exception as e:
            logger.warning(f"Failed to load Hunspell for {language}: {e}")
            self._hunspell_cache[language] = None
            return None

    def validate_with_dictionary(self, text: str, language: str) -> bool:
        """
        Validate entity text using Hunspell dictionary

        Args:
            text: Entity text to validate
            language: Language code (de, en, fr, ru)

        Returns:
            True if at least 60% of words are valid in the language dictionary
        """
        try:
            hobj = self._get_hunspell(language)
            if not hobj:
                return True  # Skip validation if dictionary not available

            # Split entity into words (handle "Frankfurt am Main", "GmbH & Co. KG")
            words = re.findall(r'\b[A-Za-zäöüÄÖÜßàâéèêëïîôùûüÿçÀÂÉÈÊËÏÎÔÙÛÜŸÇ]+\b', text)

            if not words:
                return False  # No valid words found

            # Check how many words are valid
            valid_words = sum(1 for word in words if hobj.spell(word))
            validity_ratio = valid_words / len(words) if words else 0

            # At least 60% of words should be valid
            return validity_ratio >= 0.6

        except Exception as e:
            logger.debug(f"Dictionary validation error for '{text}': {e}")
            return True  # Don't filter if validation fails

    def calculate_length_factor(self, text: str, entity_type: str) -> float:
        """
        Calculate confidence multiplier based on entity length

        Args:
            text: Entity text
            entity_type: Type of entity (ORGANIZATION, PERSON, etc.)

        Returns:
            Confidence multiplier (0.0 to 1.0)
        """
        length = len(text)

        # Very short entities are suspicious
        if length < 2:
            return 0.1
        elif length == 2:
            return 0.3  # "DE", "AG" - usually not standalone entities
        elif length == 3:
            return 0.6  # "Tel", "Fax" - could be abbreviations

        # Very long entities are likely OCR errors
        elif length > 80:
            return 0.2
        elif length > 50:
            return 0.5

        # Optimal length range
        elif 5 <= length <= 40:
            return 1.0

        # Slightly short/long
        return 0.8

    def calculate_character_pattern_quality(self, text: str) -> float:
        """
        Calculate quality score based on character patterns

        Detects OCR artifacts, repetitive characters, unusual patterns

        Returns:
            Quality multiplier (0.0 to 1.0)
        """
        score = 1.0

        # 1. Repetitive characters (OCR artifacts)
        if re.search(r'(.)\1{5,}', text):  # 6+ same char in row
            return 0.1  # Severe penalty - almost certainly garbage
        elif re.search(r'(.)\1{4,}', text):  # 5+ same char
            score *= 0.3
        elif re.search(r'(.)\1{3,}', text):  # 4+ same char
            score *= 0.6

        # 2. Consonant/vowel ratio (readability check)
        vowels = len(re.findall(r'[aeiouäöüàâéèêëïîôùûüÿ]', text.lower()))
        consonants = len(re.findall(r'[bcdfghjklmnpqrstvwxyz]', text.lower()))
        total_letters = vowels + consonants

        if total_letters > 5:
            vowel_ratio = vowels / total_letters if total_letters > 0 else 0

            if vowel_ratio < 0.10:  # Too few vowels (e.g., "HHEHERRHEREROL")
                score *= 0.3
            elif vowel_ratio < 0.15:
                score *= 0.6
            elif vowel_ratio > 0.75:  # Too many vowels (suspicious)
                score *= 0.7

        # 3. Pure numeric or punctuation
        if re.match(r'^[0-9\W]+$', text):
            return 0.1  # Numbers/punctuation only

        # 4. Mixed case chaos (OCR artifacts)
        if len(text) > 5 and re.search(r'[a-z]{2,}[A-Z]{2,}[a-z]{2,}', text):
            score *= 0.5  # Random case mixing

        # 5. Excessive punctuation
        punct_count = len(re.findall(r'[^\w\s]', text))
        if punct_count > len(text) * 0.3:  # More than 30% punctuation
            score *= 0.5

        return score

    def calculate_entity_type_bonus(self, text: str, entity_type: str) -> float:
        """
        Calculate confidence bonus for entity type-specific patterns

        Args:
            text: Entity text
            entity_type: Type of entity

        Returns:
            Confidence multiplier (0.8 to 1.3)
        """
        # Known organization suffixes boost confidence
        if entity_type == 'ORGANIZATION':
            org_suffixes = [
                'GmbH', 'AG', 'KG', 'OHG', 'mbH',  # German
                'Inc', 'LLC', 'Ltd', 'Corp', 'Co',  # English
                'SA', 'SARL', 'SAS',  # French
                'ООО', 'ЗАО', 'ОАО'  # Russian
            ]
            if any(text.endswith(suffix) for suffix in org_suffixes):
                return 1.3  # Strong indicator of real organization

            # Organization-specific words
            org_words = ['GmbH', 'AG', 'KG', 'Bank', 'Verlag', 'Institut']
            if any(word in text for word in org_words):
                return 1.2

        # Person names are typically Title Case
        elif entity_type == 'PERSON':
            if text.istitle():  # "John Doe"
                return 1.2
            elif text.isupper() and len(text) > 8:  # "JOHN DOE" - less confident
                return 0.9

        # Locations should be title case
        elif entity_type == 'LOCATION':
            if text.istitle():
                return 1.1

        return 1.0  # Neutral

    def calculate_confidence(
        self,
        entity_value: str,
        entity_type: str,
        base_confidence: float,
        language: str
    ) -> float:
        """
        Calculate comprehensive confidence score based on multiple quality factors

        Args:
            entity_value: The extracted entity text
            entity_type: Type of entity (ORGANIZATION, PERSON, LOCATION, etc.)
            base_confidence: Base confidence from extraction method (e.g., 0.85 for spaCy)
            language: Language code for dictionary validation

        Returns:
            Final confidence score between 0.0 and 1.0
        """
        confidence = base_confidence

        # 1. Length factor
        length_factor = self.calculate_length_factor(entity_value, entity_type)
        confidence *= length_factor

        # 2. Character pattern quality
        pattern_quality = self.calculate_character_pattern_quality(entity_value)
        confidence *= pattern_quality

        # 3. Entity type-specific bonus
        type_bonus = self.calculate_entity_type_bonus(entity_value, entity_type)
        confidence *= type_bonus

        # 4. Dictionary validation (strong indicator)
        if self.validate_with_dictionary(entity_value, language):
            confidence *= 1.3  # Significant boost for valid words
        else:
            confidence *= 0.6  # Penalty for invalid words

        # Cap at 1.0
        return min(confidence, 1.0)


# Global service instance
entity_quality_service = EntityQualityService()
