"""
Date Extraction Service for Bonifatus DMS
Extracts dates from document text with multi-language support
All patterns and keywords loaded dynamically from database
"""

import re
import logging
from typing import List, Tuple, Optional, Dict
from datetime import datetime, date
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DateExtractionService:
    """Service for extracting dates from document text"""

    def __init__(self):
        """Initialize date extraction service"""
        self._patterns_cache: Dict[str, List] = {}
        self._month_names_cache: Dict[str, Dict] = {}
        self._keywords_cache: Dict[str, Dict] = {}

    def get_date_patterns(self, db: Session, language: str) -> List[Tuple[str, str]]:
        """
        Load date patterns for a language from database
        Returns list of (regex_pattern, format_type) tuples
        """
        if language in self._patterns_cache:
            return self._patterns_cache[language]

        try:
            from app.database.models import SystemSetting
            import json

            result = db.query(SystemSetting).filter(
                SystemSetting.setting_key == f'date_patterns_{language}'
            ).first()

            if result:
                patterns = json.loads(result.setting_value)
                self._patterns_cache[language] = patterns
                logger.info(f"Loaded {len(patterns)} date patterns for language: {language}")
                return patterns
            else:
                logger.warning(f"No date patterns found for language: {language}")
                return []

        except Exception as e:
            logger.error(f"Failed to load date patterns: {e}")
            return []

    def get_month_names(self, db: Session, language: str) -> Dict[str, int]:
        """
        Load month name mappings for a language from database
        Returns dict mapping month names to numbers
        """
        if language in self._month_names_cache:
            return self._month_names_cache[language]

        try:
            from app.database.models import SystemSetting
            import json

            result = db.query(SystemSetting).filter(
                SystemSetting.setting_key == f'month_names_{language}'
            ).first()

            if result:
                month_map = json.loads(result.setting_value)
                self._month_names_cache[language] = month_map
                logger.info(f"Loaded month names for language: {language}")
                return month_map
            else:
                logger.warning(f"No month names found for language: {language}")
                return {}

        except Exception as e:
            logger.error(f"Failed to load month names: {e}")
            return {}

    def get_date_type_keywords(self, db: Session, language: str) -> Dict[str, List[str]]:
        """
        Load date type keywords for a language from database
        Returns dict mapping date types to keyword lists
        """
        if language in self._keywords_cache:
            return self._keywords_cache[language]

        try:
            from app.database.models import SystemSetting
            import json

            result = db.query(SystemSetting).filter(
                SystemSetting.setting_key == f'date_type_keywords_{language}'
            ).first()

            if result:
                keywords = json.loads(result.setting_value)
                self._keywords_cache[language] = keywords
                logger.info(f"Loaded date type keywords for language: {language}")
                return keywords
            else:
                logger.warning(f"No date type keywords found for language: {language}")
                return {}

        except Exception as e:
            logger.error(f"Failed to load date type keywords: {e}")
            return {}

    def clear_cache(self):
        """Clear all cached data (useful after database updates)"""
        self._patterns_cache = {}
        self._month_names_cache = {}
        self._keywords_cache = {}

    def parse_date(
        self,
        match: Tuple,
        format_type: str,
        month_names: Dict[str, int]
    ) -> Optional[date]:
        """
        Parse a date from regex match based on format type

        Args:
            match: Regex match groups
            format_type: Format identifier (mdy, dmy, ymd, etc)
            month_names: Month name to number mapping

        Returns:
            Parsed date object or None if invalid
        """
        try:
            if format_type == 'mdy':
                month, day, year = int(match[0]), int(match[1]), int(match[2])
            elif format_type == 'dmy':
                day, month, year = int(match[0]), int(match[1]), int(match[2])
            elif format_type == 'ymd':
                year, month, day = int(match[0]), int(match[1]), int(match[2])
            elif format_type == 'mdy_named':
                month_name = match[0].lower()
                month = month_names.get(month_name, 0)
                day = int(match[1])
                year = int(match[2])
            elif format_type == 'dmy_named':
                day = int(match[0])
                month_name = match[1].lower()
                month = month_names.get(month_name, 0)
                year = int(match[2])
            elif format_type == 'my_named':
                month_name = match[0].lower()
                month = month_names.get(month_name, 0)
                day = 1
                year = int(match[1])
            else:
                return None

            if year < 1900 or year > 2100:
                return None
            if month < 1 or month > 12:
                return None
            if day < 1 or day > 31:
                return None

            parsed_date = date(year, month, day)
            return parsed_date

        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse date: {e}")
            return None

    def identify_date_type(
        self,
        text: str,
        date_position: int,
        keywords: Dict[str, List[str]]
    ) -> str:
        """
        Identify the type of date based on surrounding context

        Args:
            text: Full document text
            date_position: Position of date in text
            keywords: Date type keyword mappings

        Returns:
            Date type identifier
        """
        context_before = text[max(0, date_position - 100):date_position].lower()
        context_after = text[date_position:min(len(text), date_position + 100)].lower()
        context = context_before + " " + context_after

        for date_type, keyword_list in keywords.items():
            for keyword in keyword_list:
                if keyword.lower() in context:
                    return date_type

        return 'unknown'

    def extract_dates(
        self,
        text: str,
        db: Session,
        language: str = 'en'
    ) -> List[Tuple[date, str, float, str]]:
        """
        Extract all dates from text with type identification

        Args:
            text: Document text
            db: Database session
            language: Language code

        Returns:
            List of tuples (date_value, date_type, confidence, extracted_text)
        """
        if not text:
            return []

        logger.info(f"[DATE DEBUG] Starting date extraction for language: {language}")
        patterns = self.get_date_patterns(db, language)
        month_names = self.get_month_names(db, language)
        keywords = self.get_date_type_keywords(db, language)

        if not patterns:
            logger.warning(f"No date patterns available for language: {language}")
            return []

        logger.info(f"[DATE DEBUG] Using {len(patterns)} date patterns for language: {language}")
        logger.info(f"[DATE DEBUG] Text sample (first 200 chars): {text[:200]}")

        dates_found = []

        for pattern_str, format_type in patterns:
            try:
                for match in re.finditer(pattern_str, text, re.IGNORECASE):
                    parsed_date = self.parse_date(match.groups(), format_type, month_names)

                    if parsed_date:
                        date_type = self.identify_date_type(text, match.start(), keywords)
                        extracted_text = match.group(0)
                        confidence = 0.9 if date_type != 'unknown' else 0.7

                        # DEBUG: Log each date found with context
                        context = text[max(0, match.start()-30):min(len(text), match.end()+30)]
                        logger.info(f"[DATE DEBUG] Found date: {parsed_date} | Type: {date_type} | "
                                  f"Confidence: {confidence} | Extracted: '{extracted_text}' | "
                                  f"Format: {format_type} | Context: '...{context}...'")

                        dates_found.append((parsed_date, date_type, confidence, extracted_text))
            except re.error as e:
                logger.error(f"Invalid regex pattern: {pattern_str} - {e}")
                continue

        dates_found.sort(key=lambda x: x[2], reverse=True)

        logger.info(f"Extracted {len(dates_found)} dates from text (lang: {language})")
        if dates_found:
            logger.info(f"[DATE DEBUG] Primary date selected: {dates_found[0][0]} (type: {dates_found[0][1]}, confidence: {dates_found[0][2]})")
        return dates_found

    def get_primary_date(
        self,
        dates: List[Tuple[date, str, float, str]]
    ) -> Optional[Tuple[date, str, float]]:
        """
        Select the primary document date from extracted dates
        Priority: invoice_date > signature_date > effective_date > highest confidence

        Args:
            dates: List of extracted dates

        Returns:
            Tuple of (date_value, date_type, confidence) or None
        """
        if not dates:
            return None

        priority_order = ['invoice_date', 'signature_date', 'effective_date', 'tax_year']

        for priority_type in priority_order:
            for date_val, date_type, confidence, _ in dates:
                if date_type == priority_type:
                    return (date_val, date_type, confidence)

        return (dates[0][0], dates[0][1], dates[0][2])

    def extract_primary_date(
        self,
        text: str,
        db: Session,
        language: str = 'en'
    ) -> Optional[Tuple[date, str, float]]:
        """
        Extract the primary document date

        Args:
            text: Document text
            db: Database session
            language: Language code (fallback to 'en')

        Returns:
            Tuple of (date_value, date_type, confidence) or None
        """
        all_dates = self.extract_dates(text, db, language)
        return self.get_primary_date(all_dates)


date_extraction_service = DateExtractionService()
