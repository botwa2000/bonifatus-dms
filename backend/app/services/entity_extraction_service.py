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
from app.services.entity_quality_service import get_entity_quality_service

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
        db: Session = None,
        return_rejected: bool = False
    ):
        """
        Extract named entities from text using spaCy NER with database-driven filtering

        Args:
            text: Document text to analyze
            language: Language code
            extract_addresses: Whether to extract address patterns
            db: Database session for filtering rules (optional)
            return_rejected: If True, return dict with 'accepted' and 'rejected' lists

        Returns:
            If return_rejected=False: List of extracted and filtered entities
            If return_rejected=True: Dict with keys:
                - 'accepted': List of entities that passed filters
                - 'rejected': List of rejected ORG entities suitable for keyword conversion
                              (confidence 0.50-0.85, not blacklisted, not field labels)
        """
        entities = []

        if not text or len(text.strip()) < 10:
            if return_rejected:
                return {'accepted': [], 'rejected': []}
            return entities

        # Try spaCy NER (requires database for model configuration)
        model = self._get_model(language, db) if db else None
        if model:
            entities.extend(self._extract_with_spacy(text, model, language, db))

        # Pattern-based address extraction (works without spaCy)
        if extract_addresses:
            entities.extend(self._extract_addresses_pattern(text, language, db))

        # Pattern-based sender/recipient extraction from headers
        entities.extend(self._extract_from_headers(text, language, db))

        # Pattern-based email extraction
        entities.extend(self._extract_emails_pattern(text, db, language))

        # Pattern-based URL/website extraction
        entities.extend(self._extract_urls_pattern(text, db, language))

        logger.info(f"[ENTITY EXTRACTION] Extracted {len(entities)} entities from text (lang: {language})")

        # Apply database-driven filters if database session provided
        if db:
            result = self._filter_entities(entities, language, db, return_rejected=return_rejected)

            if return_rejected:
                # Result is a dict with 'accepted' and 'rejected' keys
                logger.info(f"[ENTITY FILTER] After filtering: {len(result['accepted'])} entities accepted, "
                           f"{len(result['rejected'])} ORG entities rejected for keyword conversion")
                return result
            else:
                # Result is a list of entities
                entities = result
                logger.info(f"[ENTITY FILTER] After filtering: {len(entities)} entities remain")

        # Return based on return_rejected flag
        if return_rejected:
            return {'accepted': entities, 'rejected': []}
        return entities

    def _extract_with_spacy(self, text: str, model, language: str, db: Optional[Session] = None) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER with quality-based confidence scoring"""
        entities = []

        try:
            # Limit text length for performance (first 5000 chars usually contain header info)
            text_sample = text[:5000]
            doc = model(text_sample)

            # Create quality service if db provided
            quality_service = get_entity_quality_service(db) if db else None
            logger.info(f"[QUALITY DEBUG] db provided: {db is not None}, quality_service created: {quality_service is not None}")

            for ent in doc.ents:
                entity_type = None

                # Extract spaCy's REAL confidence score (not hardcoded 0.85)
                # spaCy stores confidence in different ways depending on model
                if hasattr(ent, 'kb_id_') and hasattr(ent._, 'kb_score'):
                    # Entity linking confidence
                    base_confidence = float(ent._.kb_score)
                elif hasattr(doc, 'cats'):
                    # Text classification confidence
                    base_confidence = max(doc.cats.values()) if doc.cats else 0.85
                else:
                    # Fallback: use conservative estimate
                    # spaCy NER typically has 0.7-0.95 accuracy depending on entity type
                    base_confidence = 0.85

                # Map spaCy entity types to our schema
                if ent.label_ == "PERSON":
                    entity_type = "PERSON"
                elif ent.label_ == "ORG":
                    entity_type = "ORGANIZATION"
                elif ent.label_ in ("LOC", "GPE", "FAC"):  # Location, Geo-political entity, Facility
                    entity_type = "LOCATION"

                if entity_type:
                    entity_value = ent.text.strip()

                    # Calculate quality-based confidence using ML or rule-based
                    if quality_service:
                        calculated_confidence = quality_service.calculate_confidence(
                            entity_value=entity_value,
                            entity_type=entity_type,
                            base_confidence=base_confidence,
                            language=language
                        )
                        logger.info(f"[QUALITY DEBUG] Entity '{entity_value[:50]}': base={base_confidence:.2f}, calculated={calculated_confidence:.2f}")
                    else:
                        # No quality service, use base confidence
                        calculated_confidence = base_confidence
                        logger.warning(f"[QUALITY DEBUG] No quality service, using base confidence {base_confidence:.2f} for '{entity_value[:50]}'")

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

    def _extract_addresses_pattern(self, text: str, language: str, db: Optional[Session] = None) -> List[ExtractedEntity]:
        """
        Extract addresses using libpostal (primary) or regex patterns (fallback)

        libpostal: Free, open-source, handles 60+ countries and all languages
        Fallback: Database-driven regex patterns for common address formats
        """
        entities = []

        # Check if libpostal is enabled and available
        libpostal_enabled = False
        if db:
            try:
                from app.database.models import EntityQualityConfig
                libpostal_config = db.query(EntityQualityConfig).filter(
                    EntityQualityConfig.config_key == 'libpostal_enabled'
                ).first()
                libpostal_enabled = libpostal_config.config_value > 0.5 if libpostal_config else False
            except Exception as e:
                logger.warning(f"Failed to check libpostal config: {e}")

        # Try libpostal first (best accuracy)
        if libpostal_enabled:
            try:
                from postal.parser import parse_address
                entities.extend(self._extract_with_libpostal(text, language, db))
                logger.info(f"[ADDRESS] Extracted {len(entities)} addresses using libpostal")
                return entities  # libpostal found addresses, return them
            except ImportError:
                logger.warning("[ADDRESS] libpostal not available, using regex fallback")
            except Exception as e:
                logger.error(f"[ADDRESS] libpostal extraction failed: {e}, using regex fallback")

        # Fallback: Improved regex patterns with multi-language support
        entities.extend(self._extract_with_regex_patterns(text, language, db))
        logger.info(f"[ADDRESS] Extracted {len(entities)} addresses using regex patterns")
        return entities

    def _extract_with_libpostal(self, text: str, language: str, db: Optional[Session] = None) -> List[ExtractedEntity]:
        """Extract addresses using libpostal (high accuracy, all languages)"""
        from postal.parser import parse_address

        entities = []
        quality_service = get_entity_quality_service(db) if db else None

        # Load base confidence from database
        base_confidence = 0.90  # Default for libpostal
        if db:
            try:
                from app.database.models import EntityQualityConfig
                confidence_config = db.query(EntityQualityConfig).filter(
                    EntityQualityConfig.config_key == 'address_libpostal_confidence'
                ).first()
                if confidence_config:
                    base_confidence = confidence_config.config_value
            except Exception as e:
                logger.warning(f"Failed to load libpostal confidence: {e}")

        # Split text into potential address lines (addresses are usually on separate lines)
        lines = [line.strip() for line in text.split('\n') if 10 < len(line.strip()) < 300]

        for line in lines:
            try:
                parsed = parse_address(line)

                # Check if line contains address components
                address_components = {}
                for value, label in parsed:
                    if label in ('road', 'house_number', 'postcode', 'city', 'state_district', 'state'):
                        address_components[label] = value

                # Require at least 2 components for valid address
                if len(address_components) >= 2:
                    # Build full address from components
                    parts = []
                    if 'road' in address_components:
                        road = address_components['road']
                        number = address_components.get('house_number', '')
                        parts.append(f"{road} {number}".strip() if number else road)
                    if 'postcode' in address_components and 'city' in address_components:
                        parts.append(f"{address_components['postcode']} {address_components['city']}")
                    elif 'city' in address_components:
                        parts.append(address_components['city'])

                    if parts:
                        full_address = ', '.join(parts)

                        # Calculate quality-based confidence
                        if quality_service:
                            calculated_confidence = quality_service.calculate_confidence(
                                entity_value=full_address,
                                entity_type="ADDRESS",
                                base_confidence=base_confidence,
                                language=language
                            )
                        else:
                            calculated_confidence = base_confidence

                        entities.append(ExtractedEntity(
                            entity_type="ADDRESS",
                            entity_value=full_address,
                            confidence=calculated_confidence,
                            extraction_method="libpostal"
                        ))
                        logger.debug(f"[LIBPOSTAL] Extracted address: {full_address}")

            except Exception as e:
                logger.debug(f"[LIBPOSTAL] Failed to parse line: {line[:50]}: {e}")
                continue

        return entities

    def _extract_with_regex_patterns(self, text: str, language: str, db: Optional[Session] = None) -> List[ExtractedEntity]:
        """Extract addresses using improved regex patterns (fallback when libpostal unavailable)"""
        entities = []
        quality_service = get_entity_quality_service(db) if db else None

        # Load base confidence from database
        base_confidence_regex = 0.70  # Default for regex
        if db:
            try:
                from app.database.models import EntityQualityConfig
                confidence_config = db.query(EntityQualityConfig).filter(
                    EntityQualityConfig.config_key == 'address_regex_confidence'
                ).first()
                if confidence_config:
                    base_confidence_regex = confidence_config.config_value
            except Exception as e:
                logger.warning(f"Failed to load regex confidence: {e}")

        # Pattern 1: Postal code + City (works for DE, FR, CH, AT, etc.)
        # Examples: "61348 Bad Homburg", "75001 Paris", "8001 Zürich"
        postal_pattern = r'\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\s\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)\b'

        for match in re.finditer(postal_pattern, text):
            postal_code = match.group(1)
            city = match.group(2).strip()
            address_part = f"{postal_code} {city}"

            # Calculate quality-based confidence
            if quality_service:
                calculated_confidence = quality_service.calculate_confidence(
                    entity_value=address_part,
                    entity_type="ADDRESS",
                    base_confidence=base_confidence_regex,
                    language=language
                )
            else:
                calculated_confidence = base_confidence_regex

            entities.append(ExtractedEntity(
                entity_type="ADDRESS",
                entity_value=address_part,
                confidence=calculated_confidence,
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_postal"
            ))

        # Pattern 2: Street address (EXPANDED street types for all languages)
        # German: straße, strasse, str., weg, gasse, platz, allee, ring, promenade, damm, avenue
        # English: street, road, avenue, boulevard, drive, lane, way, court, place
        # French: rue, avenue, boulevard, place, chemin, allée
        street_types = {
            'de': r'(?:straße|strasse|str\.|weg|gasse|platz|allee|ring|promenade|damm|avenue)',
            'en': r'(?:street|st\.|road|rd\.|avenue|ave\.|boulevard|blvd\.|drive|dr\.|lane|ln\.|way|court|ct\.|place|pl\.)',
            'fr': r'(?:rue|avenue|av\.|boulevard|bd\.|place|pl\.|chemin|allée)',
            'ru': r'(?:улица|ул\.|проспект|пр\.|переулок|пер\.|площадь|пл\.)'
        }

        street_type_pattern = street_types.get(language, street_types['de'])

        # German format: "Wilhelminenstraße 9" or "9 Main Street"
        street_patterns = [
            rf'\b([A-ZÄÖÜ][a-zäöüß\-]+{street_type_pattern})\s+(\d+(?:\-\d+)?[a-z]?)\b',  # Street first
            rf'\b(\d+(?:\-\d+)?[a-z]?)\s+([A-Z][a-z\-]+\s+{street_type_pattern})\b'  # Number first
        ]

        for pattern in street_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                street = match.group(1)
                number = match.group(2)
                address_part = f"{street} {number}"

                # Calculate quality-based confidence
                if quality_service:
                    calculated_confidence = quality_service.calculate_confidence(
                        entity_value=address_part,
                        entity_type="ADDRESS",
                        base_confidence=base_confidence_regex,
                        language=language
                    )
                else:
                    calculated_confidence = base_confidence_regex

                entities.append(ExtractedEntity(
                    entity_type="ADDRESS",
                    entity_value=address_part,
                    confidence=calculated_confidence,
                    position_start=match.start(),
                    position_end=match.end(),
                    extraction_method="pattern_street"
                ))

        return entities

    def _extract_from_headers(self, text: str, language: str, db: Optional[Session] = None) -> List[ExtractedEntity]:
        """Extract sender/recipient from document headers using patterns with quality-based confidence"""
        entities = []

        # Create quality service if db provided
        quality_service = get_entity_quality_service(db) if db else None

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

                # Calculate quality-based confidence
                base_confidence = 0.80
                if quality_service:
                    calculated_confidence = quality_service.calculate_confidence(
                        entity_value=value,
                        entity_type=entity_type,
                        base_confidence=base_confidence,
                        language=language
                    )
                else:
                    calculated_confidence = base_confidence

                entities.append(ExtractedEntity(
                    entity_type=entity_type,
                    entity_value=value,
                    confidence=calculated_confidence,
                    position_start=match.start(),
                    position_end=match.end(),
                    extraction_method="pattern_header"
                ))

        return entities

    def _extract_emails_pattern(self, text: str, db: Optional[Session] = None, language: str = 'en') -> List[ExtractedEntity]:
        """Extract email addresses using regex pattern with quality-based confidence"""
        entities = []

        # Create quality service if db provided
        quality_service = get_entity_quality_service(db) if db else None

        # Email pattern (RFC 5322 simplified)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        for match in re.finditer(email_pattern, text):
            email = match.group(0)

            # Calculate quality-based confidence
            base_confidence = 0.95
            if quality_service:
                calculated_confidence = quality_service.calculate_confidence(
                    entity_value=email,
                    entity_type="EMAIL",
                    base_confidence=base_confidence,
                    language=language
                )
            else:
                calculated_confidence = base_confidence

            entities.append(ExtractedEntity(
                entity_type="EMAIL",
                entity_value=email,
                confidence=calculated_confidence,
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_email"
            ))

        return entities

    def _extract_urls_pattern(self, text: str, db: Optional[Session] = None, language: str = 'en') -> List[ExtractedEntity]:
        """Extract URLs and websites using regex pattern with quality-based confidence"""
        entities = []

        # Create quality service if db provided
        quality_service = get_entity_quality_service(db) if db else None

        # URL pattern (http/https URLs)
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'

        for match in re.finditer(url_pattern, text):
            url = match.group(0)

            # Calculate quality-based confidence
            base_confidence = 0.95
            if quality_service:
                calculated_confidence = quality_service.calculate_confidence(
                    entity_value=url,
                    entity_type="URL",
                    base_confidence=base_confidence,
                    language=language
                )
            else:
                calculated_confidence = base_confidence

            entities.append(ExtractedEntity(
                entity_type="URL",
                entity_value=url,
                confidence=calculated_confidence,
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_url"
            ))

        # Website pattern (www.example.com without http://)
        website_pattern = r'\bwww\.[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        for match in re.finditer(website_pattern, text):
            website = match.group(0)

            # Calculate quality-based confidence
            base_confidence = 0.90
            if quality_service:
                calculated_confidence = quality_service.calculate_confidence(
                    entity_value=website,
                    entity_type="URL",
                    base_confidence=base_confidence,
                    language=language
                )
            else:
                calculated_confidence = base_confidence

            entities.append(ExtractedEntity(
                entity_type="URL",
                entity_value=website,
                confidence=calculated_confidence,
                position_start=match.start(),
                position_end=match.end(),
                extraction_method="pattern_website"
            ))

        return entities

    def _filter_entities(
        self,
        entities: List[ExtractedEntity],
        language: str,
        db: Session,
        return_rejected: bool = False
    ):
        """
        Apply simplified filters using quality-based confidence scoring

        Filters applied:
        1. Field labels (IBAN, Tel, Nr, etc.) - still needed, these are labels not entities
        2. Confidence threshold (0.75) - now uses calculated confidence from quality service
        3. Blacklist - user-reported bad entities
        4. Collect rejected ORG entities for keyword conversion (if return_rejected=True)

        Note: Invalid pattern checks (repetitive chars, short strings, etc.) are now
        handled by the quality service's confidence calculation, avoiding duplication.

        Args:
            entities: Raw extracted entities with calculated confidence scores
            language: Language code
            db: Database session
            return_rejected: If True, return dict with 'accepted' and 'rejected' lists

        Returns:
            If return_rejected=False: Filtered entities list
            If return_rejected=True: Dict with 'accepted' and 'rejected' keys
        """
        if not entities:
            if return_rejected:
                return {'accepted': [], 'rejected': []}
            return entities

        # Load filtering rules from database
        field_labels = self._load_field_labels(db, language)
        blacklist = self._load_blacklist(db, language)

        # Load confidence thresholds from database (entity-type-specific)
        try:
            from app.database.models import EntityQualityConfig
            threshold_configs = db.query(EntityQualityConfig).filter(
                EntityQualityConfig.config_key.in_([
                    'address_confidence_threshold',
                    'email_confidence_threshold',
                    'url_confidence_threshold',
                    'confidence_threshold_organization'
                ])
            ).all()

            threshold_map = {config.config_key: config.config_value for config in threshold_configs}

            ADDRESS_THRESHOLD = threshold_map.get('address_confidence_threshold', 0.70)
            EMAIL_THRESHOLD = threshold_map.get('email_confidence_threshold', 0.75)
            URL_THRESHOLD = threshold_map.get('url_confidence_threshold', 0.75)
            ORG_CONFIDENCE_THRESHOLD = threshold_map.get('confidence_threshold_organization', 0.85)
            CONFIDENCE_THRESHOLD = 0.75  # Default fallback for other types
        except Exception as e:
            logger.warning(f"Failed to load confidence thresholds from database: {e}")
            ADDRESS_THRESHOLD = 0.70
            EMAIL_THRESHOLD = 0.75
            URL_THRESHOLD = 0.75
            ORG_CONFIDENCE_THRESHOLD = 0.85
            CONFIDENCE_THRESHOLD = 0.75

        filtered = []
        rejected_for_keywords = []  # Collect ORG entities suitable for keyword conversion
        removed_count = {
            'field_label': 0,
            'low_confidence': 0,
            'low_confidence_org': 0,  # Track ORG-specific removals separately
            'low_confidence_org_convertible': 0,  # ORG entities converted to keywords
            'blacklisted': 0
        }

        # Load keyword conversion threshold
        try:
            from app.database.models import KeywordExtractionConfig
            keyword_min_conf_result = db.query(KeywordExtractionConfig).filter(
                KeywordExtractionConfig.config_key == 'org_to_keyword_min_confidence'
            ).first()
            KEYWORD_MIN_CONFIDENCE = keyword_min_conf_result.config_value if keyword_min_conf_result else 0.50
        except Exception as e:
            logger.warning(f"Failed to load keyword conversion threshold: {e}")
            KEYWORD_MIN_CONFIDENCE = 0.50

        for entity in entities:
            # Normalize entity value (clean whitespace, line breaks, trailing field labels)
            normalized = self._normalize_entity_value(entity.entity_value, field_labels)
            entity.entity_value = normalized
            entity.normalized_value = normalized.lower()

            # Filter 1: Remove field labels (these are labels, not actual entities)
            if normalized in field_labels:
                removed_count['field_label'] += 1
                logger.debug(f"[ENTITY FILTER] Removed field label: {normalized}")
                continue

            # Filter 2: Remove low confidence entities (entity-type-specific thresholds)
            if entity.entity_type == 'ORGANIZATION':
                threshold = ORG_CONFIDENCE_THRESHOLD
            elif entity.entity_type == 'ADDRESS':
                threshold = ADDRESS_THRESHOLD
            elif entity.entity_type == 'EMAIL':
                threshold = EMAIL_THRESHOLD
            elif entity.entity_type == 'URL':
                threshold = URL_THRESHOLD
            else:
                threshold = CONFIDENCE_THRESHOLD

            if entity.confidence < threshold:
                # Special handling for ORG entities: check if suitable for keyword conversion
                if entity.entity_type == 'ORGANIZATION' and entity.confidence >= KEYWORD_MIN_CONFIDENCE:
                    # This ORG entity is rejected as entity but can be converted to keyword
                    rejected_for_keywords.append({
                        'entity_value': normalized,
                        'entity_type': entity.entity_type,
                        'confidence': entity.confidence
                    })
                    removed_count['low_confidence_org_convertible'] += 1
                    logger.debug(f"[ENTITY FILTER] Rejected ORG for keyword conversion: {normalized} "
                               f"(confidence: {entity.confidence:.2f}, threshold: {threshold})")
                elif entity.entity_type == 'ORGANIZATION':
                    removed_count['low_confidence_org'] += 1
                    logger.debug(f"[ENTITY FILTER] Removed low confidence ORG: {normalized} "
                               f"(confidence: {entity.confidence:.2f}, threshold: {threshold})")
                else:
                    removed_count['low_confidence'] += 1
                    logger.debug(f"[ENTITY FILTER] Removed low confidence: {normalized} "
                               f"(confidence: {entity.confidence:.2f}, threshold: {threshold})")
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
                       f"low_confidence_org={removed_count['low_confidence_org']}, "
                       f"low_confidence_org_convertible={removed_count['low_confidence_org_convertible']}, "
                       f"blacklisted={removed_count['blacklisted']}")

        if return_rejected:
            return {
                'accepted': filtered,
                'rejected': rejected_for_keywords
            }
        return filtered

    def _normalize_entity_value(self, value: str, field_labels: Set[str] = None) -> str:
        """
        Normalize entity value by cleaning whitespace, line breaks, and trailing field labels

        Args:
            value: Raw entity value
            field_labels: Set of field labels from database (language-specific)

        Returns:
            Cleaned entity value
        """
        # Remove line breaks and extra whitespace
        normalized = re.sub(r'\s+', ' ', value)
        # Remove leading/trailing whitespace
        normalized = normalized.strip()
        # Remove trailing punctuation
        normalized = re.sub(r'[.,;:!?]+$', '', normalized)

        # Remove trailing field labels from database (language-agnostic, database-driven)
        if field_labels:
            # Try each field label as a trailing suffix
            for label in field_labels:
                # Case-insensitive check for trailing label
                # Match: "Frankfurt am Main Tel" → "Frankfurt am Main"
                # Match: "Address Tel." → "Address"
                pattern = r'\s+' + re.escape(label) + r'\.?$'
                if re.search(pattern, normalized, re.IGNORECASE):
                    normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
                    normalized = normalized.strip()
                    break  # Only remove one trailing label

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
