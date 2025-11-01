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
                'min_confidence': 0.10,  # Lowered from 0.6 to 0.10 for better multi-language support
                'gap_threshold': 0.15,   # Lowered from 0.2 to 0.15
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
        language: str,
        is_multi_lingual: bool = False
    ) -> Dict[str, float]:
        """
        Get keywords and weights for a category

        Args:
            db: Database session
            category_id: Category UUID
            language: Language code
            is_multi_lingual: If True, load ALL keywords regardless of language

        Returns:
            Dict mapping keywords to weights
        """
        try:
            from app.database.models import CategoryKeyword

            query = db.query(CategoryKeyword).filter(
                CategoryKeyword.category_id == category_id
            )

            # For language-specific categories, filter by language
            if not is_multi_lingual:
                query = query.filter(CategoryKeyword.language_code == language)

            keywords = query.all()

            keyword_weights = {kw.keyword.lower(): kw.weight for kw in keywords}

            mode = "all languages" if is_multi_lingual else f"lang: {language}"
            logger.info(f"[CLASSIFICATION DEBUG] Loaded {len(keyword_weights)} keywords for category {category_id} ({mode}), is_multi_lingual={is_multi_lingual}")

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
            logger.debug(f"[SCORE DEBUG] Empty input: doc_kw={len(document_keywords)}, cat_kw={len(category_keywords)}")
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
            logger.debug(f"[SCORE DEBUG] No keyword matches found")
            return 0.0, []

        avg_weight = total_weight / len(matched_keywords)

        # Score formula: (matched_count * avg_weight) / total_doc_keywords
        score = (len(matched_keywords) * avg_weight) / len(document_keywords_lower)

        score = min(score, 1.0)

        logger.debug(f"[SCORE DEBUG] Score={score:.3f}, Matched={len(matched_keywords)}/{len(document_keywords_lower)}, AvgWeight={avg_weight:.2f}, TotalWeight={total_weight:.2f}")

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

            logger.info(f"[CLASSIFICATION DEBUG] === Starting classification ===")
            logger.info(f"[CLASSIFICATION DEBUG] Document keywords ({len(document_keywords)}): {document_keywords[:10]}{'...' if len(document_keywords) > 10 else ''}")
            logger.info(f"[CLASSIFICATION DEBUG] Language: {language}, User ID: {user_id}")

            query = db.query(Category).filter(Category.is_active == True)

            if user_id:
                query = query.filter(
                    (Category.user_id == user_id) | (Category.is_system == True)
                )
            else:
                query = query.filter(Category.is_system == True)

            categories = query.all()
            logger.info(f"[CLASSIFICATION DEBUG] Found {len(categories)} active categories to check")

            results = []

            for category in categories:
                # For multi-lingual categories, load ALL keywords regardless of language
                logger.info(f"[CLASSIFICATION DEBUG] Processing category {category.reference_key}, is_multi_lingual={category.is_multi_lingual}, requested_language={language}")
                category_keywords = self.get_category_keywords(
                    db,
                    category.id,
                    language,
                    is_multi_lingual=category.is_multi_lingual
                )

                if not category_keywords:
                    logger.info(f"[CLASSIFICATION DEBUG] No keywords found for category {category.reference_key}")
                    continue

                logger.info(f"[CLASSIFICATION DEBUG] Category {category.reference_key} keywords ({len(category_keywords)}): {list(category_keywords.keys())[:10]}{'...' if len(category_keywords) > 10 else ''}")

                score, matched_keywords = self.calculate_score(document_keywords, category_keywords)

                translation = db.query(CategoryTranslation).filter(
                    CategoryTranslation.category_id == category.id,
                    CategoryTranslation.language_code == language
                ).first()

                category_name = translation.name if translation else category.reference_key

                logger.info(f"[CLASSIFICATION DEBUG] Category {category.reference_key}: score={score:.3f}, matched={len(matched_keywords)}/{len(document_keywords)}, matched_kw={matched_keywords[:5]}{'...' if len(matched_keywords) > 5 else ''}")

                results.append((category.id, category_name, score, matched_keywords))

            results.sort(key=lambda x: x[2], reverse=True)

            logger.info(f"[CLASSIFICATION DEBUG] === Classification complete ===")
            logger.info(f"[CLASSIFICATION DEBUG] Top 3 results:")
            for i, (cat_id, cat_name, score, matched) in enumerate(results[:3], 1):
                logger.info(f"[CLASSIFICATION DEBUG]   {i}. {cat_name}: {score:.3f} ({len(matched)} matches)")

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
        logger.info(f"[CLASSIFICATION DEBUG] === Selecting primary category ===")

        if not classification_results:
            logger.info(f"[CLASSIFICATION DEBUG] No classification results to evaluate")
            return None

        config = self.get_classification_config(db)
        min_confidence = config['min_confidence']
        gap_threshold = config['gap_threshold']

        logger.info(f"[CLASSIFICATION DEBUG] Thresholds: min_confidence={min_confidence}, gap_threshold={gap_threshold}")

        top_category = classification_results[0]
        top_score = top_category[2]
        top_name = top_category[1]

        logger.info(f"[CLASSIFICATION DEBUG] Top candidate: {top_name} with score {top_score:.3f}")

        if top_score < min_confidence:
            logger.info(f"[CLASSIFICATION DEBUG] REJECTED: Top score {top_score:.3f} below minimum confidence {min_confidence}")
            return None

        if len(classification_results) > 1:
            second_category = classification_results[1]
            second_score = second_category[2]
            second_name = second_category[1]
            gap = top_score - second_score

            logger.info(f"[CLASSIFICATION DEBUG] Second candidate: {second_name} with score {second_score:.3f}, gap={gap:.3f}")

            if gap < gap_threshold:
                logger.info(f"[CLASSIFICATION DEBUG] REJECTED: Gap {gap:.3f} below threshold {gap_threshold}, ambiguous classification")
                return None

        logger.info(f"[CLASSIFICATION DEBUG] ACCEPTED: {top_name} as primary category")
        return top_category

    def get_other_category(
        self,
        db: Session,
        language: str = 'en'
    ) -> Optional[Tuple[UUID, str, float, List[str]]]:
        """
        Get the OTHER category as a fallback

        Args:
            db: Database session
            language: Language for category name

        Returns:
            Tuple of (category_id, category_name, 0.0, []) or None if OTHER category doesn't exist
        """
        try:
            from app.database.models import Category, CategoryTranslation

            # Fixed: reference_key is 'OTH' not 'category.other'
            other_category = db.query(Category).filter(
                Category.reference_key == 'OTH'
            ).first()

            if not other_category:
                logger.error("OTHER category not found in database (looking for reference_key='OTH')")
                return None

            translation = db.query(CategoryTranslation).filter(
                CategoryTranslation.category_id == other_category.id,
                CategoryTranslation.language_code == language
            ).first()

            category_name = translation.name if translation else "Other"

            logger.info(f"[FALLBACK DEBUG] Falling back to OTHER category: {category_name} (lang: {language})")
            return (other_category.id, category_name, 0.0, [])

        except Exception as e:
            logger.error(f"Failed to get OTHER category: {e}")
            return None

    def suggest_category(
        self,
        document_keywords: List[str],
        db: Session,
        language: str = 'en',
        user_id: Optional[UUID] = None,
        fallback_to_other: bool = True
    ) -> Optional[Tuple[UUID, str, float, List[str]]]:
        """
        Suggest a primary category for a document
        Falls back to OTHER category if no confident match is found (default behavior)

        Args:
            document_keywords: List of keywords from document
            db: Database session
            language: Document language
            user_id: User ID for custom categories
            fallback_to_other: If True, return OTHER category when no confident match found

        Returns:
            Tuple of (category_id, category_name, confidence, matched_keywords)
            Returns OTHER category if no confident match and fallback_to_other=True
            Returns None only if fallback_to_other=False or OTHER category doesn't exist
        """
        logger.info(f"[SUGGEST CATEGORY DEBUG] === Starting category suggestion ===")
        logger.info(f"[SUGGEST CATEGORY DEBUG] Language: {language}, Fallback to OTHER: {fallback_to_other}")

        classification_results = self.classify_document(
            document_keywords,
            db,
            language,
            user_id
        )

        primary_category = self.get_primary_category(classification_results, db)

        if primary_category:
            logger.info(f"[SUGGEST CATEGORY DEBUG] ✅ Suggested category: {primary_category[1]} ({primary_category[2]:.1%} confidence)")
            return primary_category

        # No confident match found
        logger.info(f"[SUGGEST CATEGORY DEBUG] ⚠️  No confident category match found")

        if fallback_to_other:
            logger.info(f"[SUGGEST CATEGORY DEBUG] Attempting fallback to OTHER category...")
            other = self.get_other_category(db, language)
            if other:
                logger.info(f"[SUGGEST CATEGORY DEBUG] ✅ Fallback successful: {other[1]}")
            else:
                logger.error(f"[SUGGEST CATEGORY DEBUG] ❌ Fallback failed: OTHER category not found!")
            return other

        logger.info(f"[SUGGEST CATEGORY DEBUG] No fallback requested, returning None")
        return None


classification_service = ClassificationService()
