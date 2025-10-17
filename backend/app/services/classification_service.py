"""
Classification Service for Bonifatus DMS
Scores documents against categories using keyword overlap
Thresholds and parameters loaded from database
"""

import logging
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from uuid import UUID

logger = logging.getLogger(__name__)


class ClassificationService:
    """Service for classifying documents into categories"""

    def __init__(self):
        """Initialize classification service"""
        self._config_cache: Optional[Dict] = None

    def get_classification_config(self, db: Session) -> Dict:
        """
        Load classification configuration from database
        Returns dict with thresholds and parameters
        """
        if self._config_cache is not None:
            return self._config_cache

        try:
            from app.database.models import SystemSetting
            import json

            defaults = {
                'min_confidence': 0.6,
                'gap_threshold': 0.2,
                'weight_boost_correct': 0.1,
                'weight_penalty_incorrect': 0.05,
                'weight_min': 0.1,
                'weight_max': 10.0
            }

            result = db.query(SystemSetting).filter(
                SystemSetting.setting_key == 'classification_config'
            ).first()

            if result:
                config = json.loads(result.setting_value)
                self._config_cache = {**defaults, **config}
                logger.info("Loaded classification config from database")
            else:
                self._config_cache = defaults
                logger.warning("Classification config not found in database, using defaults")

            return self._config_cache

        except Exception as e:
            logger.error(f"Failed to load classification config: {e}")
            return {
                'min_confidence': 0.6,
                'gap_threshold': 0.2,
                'weight_boost_correct': 0.1,
                'weight_penalty_incorrect': 0.05,
                'weight_min': 0.1,
                'weight_max': 10.0
            }

    def clear_config_cache(self):
        """Clear cached configuration (useful after database updates)"""
        self._config_cache = None

    def get_category_keywords(
        self,
        db: Session,
        category_id: UUID,
        language: str
    ) -> Dict[str, float]:
        """
        Get keywords and weights for a category in a specific language

        Args:
            db: Database session
            category_id: Category UUID
            language: Language code

        Returns:
            Dict mapping keywords to weights
        """
        try:
            from app.database.models import CategoryKeyword

            keywords = db.query(CategoryKeyword).filter(
                CategoryKeyword.category_id == category_id,
                CategoryKeyword.language_code == language
            ).all()

            keyword_weights = {kw.keyword.lower(): kw.weight for kw in keywords}

            logger.debug(f"Loaded {len(keyword_weights)} keywords for category {category_id} (lang: {language})")

            return keyword_weights

        except Exception as e:
            logger.error(f"Failed to load category keywords: {e}")
            return {}

    def calculate_score(
        self,
        document_keywords: List[str],
        category_keywords: Dict[str, float]
    ) -> Tuple[float, List[str]]:
        """
        Calculate similarity score between document and category

        Args:
            document_keywords: List of keywords from document
            category_keywords: Dict of category keywords with weights

        Returns:
            Tuple of (score, matched_keywords)
        """
        if not document_keywords or not category_keywords:
            return 0.0, []

        document_keywords_lower = [kw.lower() for kw in document_keywords]

        matched_keywords = []
        total_weight = 0.0

        for doc_keyword in document_keywords_lower:
            if doc_keyword in category_keywords:
                weight = category_keywords[doc_keyword]
                total_weight += weight
                matched_keywords.append(doc_keyword)

        if not matched_keywords:
            return 0.0, []

        avg_weight = total_weight / len(matched_keywords)

        score = (len(matched_keywords) * avg_weight) / len(document_keywords_lower)

        score = min(score, 1.0)

        logger.debug(f"Score: {score:.2f}, Matched: {len(matched_keywords)}/{len(document_keywords_lower)}")

        return score, matched_keywords

    def classify_document(
        self,
        document_keywords: List[str],
        db: Session,
        language: str = 'en',
        user_id: Optional[UUID] = None
    ) -> List[Tuple[UUID, str, float, List[str]]]:
        """
        Classify a document against all available categories

        Args:
            document_keywords: List of keywords extracted from document
            db: Database session
            language: Document language
            user_id: User ID for custom categories (optional)

        Returns:
            List of tuples (category_id, category_name, score, matched_keywords)
            Sorted by score (highest first)
        """
        try:
            from app.database.models import Category, CategoryTranslation

            query = db.query(Category).filter(Category.is_active == True)

            if user_id:
                query = query.filter(
                    (Category.user_id == user_id) | (Category.is_system == True)
                )
            else:
                query = query.filter(Category.is_system == True)

            categories = query.all()

            results = []

            for category in categories:
                category_keywords = self.get_category_keywords(db, category.id, language)

                if not category_keywords:
                    continue

                score, matched_keywords = self.calculate_score(document_keywords, category_keywords)

                translation = db.query(CategoryTranslation).filter(
                    CategoryTranslation.category_id == category.id,
                    CategoryTranslation.language_code == language
                ).first()

                category_name = translation.name if translation else category.reference_key

                results.append((category.id, category_name, score, matched_keywords))

            results.sort(key=lambda x: x[2], reverse=True)

            logger.info(f"Classified document against {len(categories)} categories (lang: {language})")

            return results

        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return []

    def get_primary_category(
        self,
        classification_results: List[Tuple[UUID, str, float, List[str]]],
        db: Session
    ) -> Optional[Tuple[UUID, str, float, List[str]]]:
        """
        Select primary category based on confidence thresholds

        Args:
            classification_results: Sorted list of classification results
            db: Database session for loading thresholds

        Returns:
            Tuple of (category_id, category_name, score, matched_keywords) or None
        """
        if not classification_results:
            return None

        config = self.get_classification_config(db)
        min_confidence = config['min_confidence']
        gap_threshold = config['gap_threshold']

        top_category = classification_results[0]
        top_score = top_category[2]

        if top_score < min_confidence:
            logger.info(f"Top score {top_score:.2f} below minimum confidence {min_confidence}")
            return None

        if len(classification_results) > 1:
            second_score = classification_results[1][2]
            gap = top_score - second_score

            if gap < gap_threshold:
                logger.info(f"Gap {gap:.2f} below threshold {gap_threshold}, ambiguous classification")
                return None

        return top_category

    def suggest_category(
        self,
        document_keywords: List[str],
        db: Session,
        language: str = 'en',
        user_id: Optional[UUID] = None
    ) -> Optional[Tuple[UUID, str, float, List[str]]]:
        """
        Suggest a primary category for a document

        Args:
            document_keywords: List of keywords from document
            db: Database session
            language: Document language
            user_id: User ID for custom categories

        Returns:
            Tuple of (category_id, category_name, confidence, matched_keywords) or None
        """
        classification_results = self.classify_document(
            document_keywords,
            db,
            language,
            user_id
        )

        primary_category = self.get_primary_category(classification_results, db)

        if primary_category:
            logger.info(f"Suggested category: {primary_category[1]} ({primary_category[2]:.1%} confidence)")
        else:
            logger.info("No category suggestion (low confidence or ambiguous)")

        return primary_category


classification_service = ClassificationService()
