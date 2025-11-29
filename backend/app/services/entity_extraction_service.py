"""
Entity Extraction Service for Bonifatus DMS
Extracts named entities (people, organizations, addresses) from documents using spaCy NER
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Represents an extracted entity from document"""
    entity_type: str  # SENDER_NAME, RECIPIENT_NAME, SENDER_ADDRESS, etc.
    entity_value: str
    confidence: float
    position_start: int = None
    position_end: int = None
    extraction_method: str = "spacy_ner"
    normalized_value: str = None


class EntityExtractionService:
    """Service for extracting named entities from document text"""

    def __init__(self):
        """Initialize entity extraction service with lazy-loaded spaCy models"""
        self._models = {}  # Lazy-loaded spaCy models per language
        self._model_loading_attempted = set()  # Track which models we've tried to load

    def _get_model(self, language: str):
        """
        Get or load spaCy model for language

        Args:
            language: Language code (en, de, ru, fr)

        Returns:
            spaCy model or None if not available
        """
        if language in self._models:
            return self._models[language]

        if language in self._model_loading_attempted:
            return None

        try:
            import spacy

            # Map language codes to spaCy model names
            model_map = {
                'en': 'en_core_web_sm',
                'de': 'de_core_news_sm',
                'fr': 'fr_core_news_sm',
                'ru': 'ru_core_news_sm'
            }

            model_name = model_map.get(language)
            if not model_name:
                logger.warning(f"No spaCy model mapping for language: {language}")
                self._model_loading_attempted.add(language)
                return None

            logger.info(f"Loading spaCy model: {model_name}")
            model = spacy.load(model_name)
            self._models[language] = model
            logger.info(f"✓ Loaded spaCy model for {language}")
            return model

        except OSError as e:
            logger.warning(f"spaCy model not found for {language}: {e}")
            logger.info(f"To install: python -m spacy download {model_name}")
            self._model_loading_attempted.add(language)
            return None
        except Exception as e:
            logger.error(f"Failed to load spaCy model for {language}: {e}")
            self._model_loading_attempted.add(language)
            return None

    def extract_entities(
        self,
        text: str,
        language: str = 'en',
        extract_addresses: bool = True
    ) -> List[ExtractedEntity]:
        """
        Extract named entities from text using spaCy NER

        Args:
            text: Document text to analyze
            language: Language code
            extract_addresses: Whether to extract address patterns

        Returns:
            List of extracted entities
        """
        entities = []

        if not text or len(text.strip()) < 10:
            return entities

        # Try spaCy NER
        model = self._get_model(language)
        if model:
            entities.extend(self._extract_with_spacy(text, model, language))

        # Pattern-based address extraction (works without spaCy)
        if extract_addresses:
            entities.extend(self._extract_addresses_pattern(text, language))

        # Pattern-based sender/recipient extraction from headers
        entities.extend(self._extract_from_headers(text, language))

        logger.info(f"[ENTITY EXTRACTION] Extracted {len(entities)} entities from text (lang: {language})")
        return entities

    def _extract_with_spacy(self, text: str, model, language: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER"""
        entities = []

        try:
            # Limit text length for performance (first 5000 chars usually contain header info)
            text_sample = text[:5000]
            doc = model(text_sample)

            for ent in doc.ents:
                entity_type = None
                confidence = 0.85  # spaCy models generally have good confidence

                # Map spaCy entity types to our schema
                if ent.label_ == "PERSON":
                    entity_type = "PERSON"
                elif ent.label_ == "ORG":
                    entity_type = "ORGANIZATION"
                elif ent.label_ in ("LOC", "GPE", "FAC"):  # Location, Geo-political entity, Facility
                    entity_type = "LOCATION"

                if entity_type:
                    entities.append(ExtractedEntity(
                        entity_type=entity_type,
                        entity_value=ent.text.strip(),
                        confidence=confidence,
                        position_start=ent.start_char,
                        position_end=ent.end_char,
                        extraction_method="spacy_ner"
                    ))

            logger.debug(f"[ENTITY EXTRACTION] spaCy found {len(entities)} entities")

        except Exception as e:
            logger.error(f"spaCy entity extraction failed: {e}")

        return entities

    def _extract_addresses_pattern(self, text: str, language: str) -> List[ExtractedEntity]:
        """Extract addresses using regex patterns"""
        entities = []

        # Pattern for postal codes + city (works for DE, FR, CH, AT, etc.)
        # Examples: "61348 Bad Homburg", "75001 Paris", "8001 Zürich"
        postal_pattern = r'\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\s\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)\b'

        for match in re.finditer(postal_pattern, text):
            postal_code = match.group(1)
            city = match.group(2).strip()
            address_part = f"{postal_code} {city}"

            entities.append(ExtractedEntity(
                entity_type="ADDRESS_COMPONENT",
                entity_value=address_part,
                confidence=0.75,
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_postal"
            ))

        # Street address pattern (number + street name)
        # Examples: "FrolingstraBe 9", "Kaiser-Friedrich-Promenade 8-10"
        street_pattern = r'\b([A-ZÄÖÜ][a-zäöüß\-]+(?:straße|strasse|str\.|weg|gasse|platz|allee))\s+(\d+(?:\-\d+)?[a-z]?)\b'

        for match in re.finditer(street_pattern, text, re.IGNORECASE):
            street = match.group(1)
            number = match.group(2)
            address_part = f"{street} {number}"

            entities.append(ExtractedEntity(
                entity_type="ADDRESS_COMPONENT",
                entity_value=address_part,
                confidence=0.70,
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_street"
            ))

        return entities

    def _extract_from_headers(self, text: str, language: str) -> List[ExtractedEntity]:
        """Extract sender/recipient from document headers using patterns"""
        entities = []

        # Common header patterns across languages
        patterns = {
            'de': {
                'from': r'(?:Von|Absender|From):\s*([^\n]+)',
                'to': r'(?:An|Empfänger|To):\s*([^\n]+)',
                'invoice_to': r'(?:Rechnung an|Bill to|Invoice to):\s*([^\n]+)',
            },
            'en': {
                'from': r'(?:From|Sender):\s*([^\n]+)',
                'to': r'(?:To|Recipient):\s*([^\n]+)',
                'invoice_to': r'(?:Bill to|Invoice to):\s*([^\n]+)',
            },
            'fr': {
                'from': r'(?:De|Expéditeur):\s*([^\n]+)',
                'to': r'(?:À|Destinataire):\s*([^\n]+)',
            },
            'ru': {
                'from': r'(?:От|Отправитель):\s*([^\n]+)',
                'to': r'(?:Кому|Получатель):\s*([^\n]+)',
            }
        }

        lang_patterns = patterns.get(language, patterns['en'])

        # Extract first 1000 chars (headers usually at top)
        header_text = text[:1000]

        for pattern_type, pattern in lang_patterns.items():
            for match in re.finditer(pattern, header_text, re.IGNORECASE):
                value = match.group(1).strip()

                # Determine entity type
                if 'from' in pattern_type:
                    entity_type = "SENDER"
                elif 'to' in pattern_type or 'invoice' in pattern_type:
                    entity_type = "RECIPIENT"
                else:
                    entity_type = "HEADER_FIELD"

                entities.append(ExtractedEntity(
                    entity_type=entity_type,
                    entity_value=value,
                    confidence=0.80,
                    position_start=match.start(),
                    position_end=match.end(),
                    extraction_method="pattern_header"
                ))

        return entities

    def deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove duplicate entities, keeping highest confidence"""
        seen = {}

        for entity in entities:
            key = (entity.entity_type, entity.entity_value.lower())

            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity

        return list(seen.values())


# Global service instance
entity_extraction_service = EntityExtractionService()
