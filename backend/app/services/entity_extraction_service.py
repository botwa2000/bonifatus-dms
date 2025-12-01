"""
Entity Extraction Service for Bonifatus DMS
Extracts named entities (people, organizations, addresses) from documents using spaCy NER
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.services.entity_quality_service import entity_quality_service

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

    def _get_model_mapping(self, db: Session) -> dict:
        """
        Load spaCy model mapping from database (strictly database-driven)

        Args:
            db: Database session (required)

        Returns:
            Dictionary mapping language codes to model names

        Raises:
            Exception if database not available or setting not found
        """
        from app.database.models import SystemSetting
        import json

        result = db.execute(
            select(SystemSetting.setting_value).where(
                SystemSetting.setting_key == 'spacy_model_mapping'
            )
        ).scalar_one_or_none()

        if not result:
            raise ValueError("spacy_model_mapping not found in system_settings")

        return json.loads(result)

    def _get_model(self, language: str, db: Session):
        """
        Get or load spaCy model for language from database configuration

        Args:
            language: Language code (en, de, ru, fr)
            db: Database session (required)

        Returns:
            spaCy model or None if not available
        """
        if language in self._models:
            return self._models[language]

        if language in self._model_loading_attempted:
            return None

        try:
            import spacy

            # Load model mapping from database (no hardcoded values)
            model_map = self._get_model_mapping(db)

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
        extract_addresses: bool = True,
        db: Session = None
    ) -> List[ExtractedEntity]:
        """
        Extract named entities from text using spaCy NER with database-driven filtering

        Args:
            text: Document text to analyze
            language: Language code
            extract_addresses: Whether to extract address patterns
            db: Database session for filtering rules (optional)

        Returns:
            List of extracted and filtered entities
        """
        entities = []

        if not text or len(text.strip()) < 10:
            return entities

        # Try spaCy NER (requires database for model configuration)
        model = self._get_model(language, db) if db else None
        if model:
            entities.extend(self._extract_with_spacy(text, model, language))

        # Pattern-based address extraction (works without spaCy)
        if extract_addresses:
            entities.extend(self._extract_addresses_pattern(text, language))

        # Pattern-based sender/recipient extraction from headers
        entities.extend(self._extract_from_headers(text, language))

        # Pattern-based email extraction
        entities.extend(self._extract_emails_pattern(text))

        # Pattern-based URL/website extraction
        entities.extend(self._extract_urls_pattern(text))

        logger.info(f"[ENTITY EXTRACTION] Extracted {len(entities)} entities from text (lang: {language})")

        # Apply database-driven filters if database session provided
        if db:
            entities = self._filter_entities(entities, language, db)
            logger.info(f"[ENTITY FILTER] After filtering: {len(entities)} entities remain")

        return entities

    def _extract_with_spacy(self, text: str, model, language: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER with quality-based confidence scoring"""
        entities = []

        try:
            # Limit text length for performance (first 5000 chars usually contain header info)
            text_sample = text[:5000]
            doc = model(text_sample)

            for ent in doc.ents:
                entity_type = None
                base_confidence = 0.85  # spaCy base confidence

                # Map spaCy entity types to our schema
                if ent.label_ == "PERSON":
                    entity_type = "PERSON"
                elif ent.label_ == "ORG":
                    entity_type = "ORGANIZATION"
                elif ent.label_ in ("LOC", "GPE", "FAC"):  # Location, Geo-political entity, Facility
                    entity_type = "LOCATION"

                if entity_type:
                    entity_value = ent.text.strip()

                    # Calculate quality-based confidence
                    calculated_confidence = entity_quality_service.calculate_confidence(
                        entity_value=entity_value,
                        entity_type=entity_type,
                        base_confidence=base_confidence,
                        language=language
                    )

                    entities.append(ExtractedEntity(
                        entity_type=entity_type,
                        entity_value=entity_value,
                        confidence=calculated_confidence,
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

    def _extract_emails_pattern(self, text: str) -> List[ExtractedEntity]:
        """Extract email addresses using regex pattern"""
        entities = []

        # Email pattern (RFC 5322 simplified)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        for match in re.finditer(email_pattern, text):
            email = match.group(0)

            entities.append(ExtractedEntity(
                entity_type="EMAIL",
                entity_value=email,
                confidence=0.95,  # High confidence for pattern match
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_email"
            ))

        return entities

    def _extract_urls_pattern(self, text: str) -> List[ExtractedEntity]:
        """Extract URLs and websites using regex pattern"""
        entities = []

        # URL pattern (http/https URLs)
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'

        for match in re.finditer(url_pattern, text):
            url = match.group(0)

            entities.append(ExtractedEntity(
                entity_type="URL",
                entity_value=url,
                confidence=0.95,
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_url"
            ))

        # Website pattern (www.example.com without http://)
        website_pattern = r'\bwww\.[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        for match in re.finditer(website_pattern, text):
            website = match.group(0)

            entities.append(ExtractedEntity(
                entity_type="URL",
                entity_value=website,
                confidence=0.90,  # Slightly lower confidence than full URLs
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_website"
            ))

        return entities

    def _filter_entities(
        self,
        entities: List[ExtractedEntity],
        language: str,
        db: Session
    ) -> List[ExtractedEntity]:
        """
        Apply simplified filters using quality-based confidence scoring

        Filters applied:
        1. Field labels (IBAN, Tel, Nr, etc.) - still needed, these are labels not entities
        2. Confidence threshold (0.75) - now uses calculated confidence from quality service
        3. Blacklist - user-reported bad entities

        Note: Invalid pattern checks (repetitive chars, short strings, etc.) are now
        handled by the quality service's confidence calculation, avoiding duplication.

        Args:
            entities: Raw extracted entities with calculated confidence scores
            language: Language code
            db: Database session

        Returns:
            Filtered entities
        """
        if not entities:
            return entities

        # Load filtering rules from database
        field_labels = self._load_field_labels(db, language)
        blacklist = self._load_blacklist(db, language)

        # Unified confidence threshold (stricter than before)
        CONFIDENCE_THRESHOLD = 0.75

        filtered = []
        removed_count = {
            'field_label': 0,
            'low_confidence': 0,
            'blacklisted': 0
        }

        for entity in entities:
            # Normalize entity value (clean whitespace, line breaks)
            normalized = self._normalize_entity_value(entity.entity_value)
            entity.entity_value = normalized
            entity.normalized_value = normalized.lower()

            # Filter 1: Remove field labels (these are labels, not actual entities)
            if normalized in field_labels:
                removed_count['field_label'] += 1
                logger.debug(f"[ENTITY FILTER] Removed field label: {normalized}")
                continue

            # Filter 2: Remove low confidence entities (now using quality-based scoring)
            if entity.confidence < CONFIDENCE_THRESHOLD:
                removed_count['low_confidence'] += 1
                logger.debug(f"[ENTITY FILTER] Removed low confidence: {normalized} "
                           f"(confidence: {entity.confidence:.2f}, threshold: {CONFIDENCE_THRESHOLD})")
                continue

            # Filter 3: Remove blacklisted entities (user-reported bad entities)
            blacklist_key = (entity.entity_type, normalized.lower())
            if blacklist_key in blacklist:
                removed_count['blacklisted'] += 1
                logger.debug(f"[ENTITY FILTER] Removed blacklisted: {normalized}")
                continue

            # Entity passed all filters
            filtered.append(entity)

        # Log filtering summary
        total_removed = sum(removed_count.values())
        if total_removed > 0:
            logger.info(f"[ENTITY FILTER] Removed {total_removed} entities: "
                       f"field_labels={removed_count['field_label']}, "
                       f"low_confidence={removed_count['low_confidence']}, "
                       f"blacklisted={removed_count['blacklisted']}")

        return filtered

    def _normalize_entity_value(self, value: str) -> str:
        """Normalize entity value by cleaning whitespace and line breaks"""
        # Remove line breaks and extra whitespace
        normalized = re.sub(r'\s+', ' ', value)
        # Remove leading/trailing whitespace
        normalized = normalized.strip()
        # Remove trailing punctuation
        normalized = re.sub(r'[.,;:!?]+$', '', normalized)
        return normalized

    def _load_field_labels(self, db: Session, language: str) -> Set[str]:
        """Load field labels from database"""
        try:
            from app.database.models import SystemSetting
            result = db.execute(
                select(SystemSetting.setting_value).where(
                    SystemSetting.setting_key == f'entity_field_labels_{language}'
                )
            ).scalar_one_or_none()

            if result:
                import json
                return set(json.loads(result))

            # Fallback: query entity_field_labels table directly
            result = db.execute(
                select(db.text('label_text')).select_from(db.text('entity_field_labels')).where(
                    db.text(f"language = '{language}'")
                )
            ).fetchall()
            return {row[0] for row in result}

        except Exception as e:
            logger.warning(f"Failed to load field labels for {language}: {e}")
            return set()

    # NOTE: Removed _load_invalid_patterns, _load_confidence_thresholds, and _matches_invalid_pattern
    # These are now handled by entity_quality_service.calculate_confidence()
    # which provides unified quality scoring without duplication

    def _load_blacklist(self, db: Session, language: str) -> Set[Tuple[str, str]]:
        """Load blacklisted entities from database"""
        try:
            result = db.execute(
                db.text("""
                    SELECT entity_type, LOWER(entity_value)
                    FROM entity_blacklist
                    WHERE language = :language
                """),
                {"language": language}
            ).fetchall()
            return {(row[0], row[1]) for row in result}
        except Exception as e:
            logger.warning(f"Failed to load entity blacklist for {language}: {e}")
            return set()

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
