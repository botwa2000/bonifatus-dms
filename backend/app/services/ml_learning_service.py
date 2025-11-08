"""
ML Learning Service for Bonifatus DMS - Smart Keyword Learning
Implements intelligent weight adjustment with:
- Primary + Secondary category support
- Aggressive error correction for wrong predictions
- Differential preservation to maintain clear category boundaries
- Confidence-based learning rate modifiers
- Quality filtering for keywords

See ML_LEARNING_SYSTEM.md for complete design documentation
"""

import logging
import json
from typing import Optional, List, Dict, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from uuid import UUID
from datetime import datetime

logger = logging.getLogger(__name__)


class MLLearningService:
    """
    Service for intelligent ML weight adjustment based on user feedback

    Implements the smart learning strategy defined in ML_LEARNING_SYSTEM.md
    All configuration values loaded from database - NO hardcoded constants
    """

    def __init__(self):
        self._config_cache = None
        self._stopwords_cache = {}

    def _load_config(self, session: Session) -> Dict[str, any]:
        """Load ML learning configuration from database"""
        if self._config_cache:
            return self._config_cache

        try:
            from app.database.models import SystemSetting

            # Load all ML settings
            result = session.execute(
                select(SystemSetting).where(
                    SystemSetting.category == 'ml',
                    SystemSetting.setting_key.like('ml_%')
                )
            )

            config = {}
            for setting in result.scalars():
                key = setting.setting_key
                value = setting.setting_value

                # Parse by data type
                if setting.data_type == 'boolean':
                    config[key] = value.lower() == 'true'
                elif setting.data_type == 'integer':
                    config[key] = int(value)
                elif setting.data_type == 'float':
                    config[key] = float(value)
                else:
                    config[key] = value

            # Cache for session
            self._config_cache = config

            logger.info(f"Loaded {len(config)} ML configuration parameters from database")
            return config

        except Exception as e:
            logger.error(f"Failed to load ML config from database: {e}")
            # Return safe defaults if database fails
            return {
                'ml_learning_enabled': True,
                'ml_primary_weight': 1.0,
                'ml_secondary_weight': 0.3,
                'ml_correct_prediction_bonus': 0.2,
                'ml_wrong_prediction_boost': 0.5,
                'ml_wrong_prediction_penalty': 0.3,  # NEW: reduce weight in wrongly predicted category
                'ml_low_confidence_correct_multiplier': 1.5,
                'ml_high_confidence_wrong_multiplier': 1.3,
                'ml_min_keywords_required': 3,
                'ml_min_keyword_length': 3,
                'ml_min_weight_differential': 0.3,
                'ml_max_weight': 10.0,
                'ml_min_weight': 0.1,
                'ml_learning_rate': 1.0,
            }

    def _load_stopwords(self, session: Session, language: str) -> Set[str]:
        """Load stopwords from database for given language"""
        if language in self._stopwords_cache:
            return self._stopwords_cache[language]

        try:
            from app.database.models import StopWord

            result = session.execute(
                select(StopWord).where(
                    StopWord.language_code == language,
                    StopWord.is_active == True
                )
            )

            stopwords = {sw.word.lower() for sw in result.scalars()}
            self._stopwords_cache[language] = stopwords

            logger.info(f"Loaded {len(stopwords)} stopwords for language: {language}")
            return stopwords

        except Exception as e:
            logger.error(f"Failed to load stopwords for {language}: {e}")
            return set()

    def _filter_quality_keywords(
        self,
        keywords: List[str],
        language: str,
        session: Session,
        config: Dict
    ) -> List[str]:
        """
        Filter keywords based on quality criteria:
        - Remove stopwords
        - Remove too short keywords
        - Remove numeric-only keywords
        """
        stopwords = self._load_stopwords(session, language)
        min_length = config.get('ml_min_keyword_length', 3)

        filtered = []
        for kw in keywords:
            kw_lower = kw.lower().strip()

            # Skip empty
            if not kw_lower:
                continue

            # Skip too short
            if len(kw_lower) < min_length:
                continue

            # Skip stopwords
            if kw_lower in stopwords:
                continue

            # Skip numeric-only
            if kw_lower.isdigit():
                continue

            filtered.append(kw_lower)

        logger.info(f"Filtered keywords: {len(keywords)} → {len(filtered)} (removed {len(keywords) - len(filtered)})")
        return filtered

    def _calculate_weight_adjustment(
        self,
        is_primary: bool,
        ai_predicted_category: Optional[UUID],
        category_id: UUID,
        ai_confidence: Optional[float],
        config: Dict
    ) -> float:
        """
        Calculate weight adjustment for a keyword in a category

        Returns: Float adjustment to add to current weight
        """
        # Base weight by category role
        if is_primary:
            adjustment = config['ml_primary_weight']
        else:
            adjustment = config['ml_secondary_weight']

        # AI feedback bonus/boost (only for primary category)
        if is_primary and ai_predicted_category:
            if ai_predicted_category == category_id:
                # AI was correct - small reinforcement
                adjustment += config['ml_correct_prediction_bonus']

                # Low confidence correct? Learn more
                if ai_confidence and ai_confidence < 0.5:
                    adjustment *= config['ml_low_confidence_correct_multiplier']

            else:
                # AI was wrong - aggressive correction
                adjustment += config['ml_wrong_prediction_boost']

                # High confidence wrong? Learn even more
                if ai_confidence and ai_confidence > 0.8:
                    adjustment *= config['ml_high_confidence_wrong_multiplier']

        # Apply global learning rate
        adjustment *= config['ml_learning_rate']

        return adjustment

    def _ensure_differential_preservation(
        self,
        primary_category_id: UUID,
        keyword: str,
        language: str,
        primary_new_weight: float,
        session: Session,
        config: Dict
    ) -> float:
        """
        Ensure primary category maintains minimum weight differential over others

        Returns: Adjusted weight for primary category (may be boosted)
        """
        from app.database.models import CategoryKeyword

        min_differential = config['ml_min_weight_differential']

        # Get weights of this keyword in OTHER categories
        result = session.execute(
            select(CategoryKeyword).where(
                CategoryKeyword.keyword == keyword,
                CategoryKeyword.language_code == language,
                CategoryKeyword.category_id != primary_category_id
            )
        )

        other_keywords = result.scalars().all()

        if not other_keywords:
            # No overlap, no need for differential boost
            return primary_new_weight

        # Find highest weight in other categories
        max_other_weight = max(kw.weight for kw in other_keywords)

        # Check differential
        differential = primary_new_weight - max_other_weight

        if differential < min_differential:
            # Need to boost primary to maintain clear winner
            boost_needed = min_differential - differential
            primary_new_weight += boost_needed
            logger.info(f"Differential preservation: keyword '{keyword}' boosted by {boost_needed:.2f} to maintain {min_differential} gap")

        return primary_new_weight

    def _apply_weight_update(
        self,
        category_id: UUID,
        keyword: str,
        language: str,
        weight_adjustment: float,
        session: Session,
        config: Dict
    ) -> None:
        """Update or create CategoryKeyword with new weight"""
        from app.database.models import CategoryKeyword

        # Find existing keyword
        existing = session.execute(
            select(CategoryKeyword).where(
                CategoryKeyword.category_id == category_id,
                CategoryKeyword.keyword == keyword,
                CategoryKeyword.language_code == language
            )
        ).scalar_one_or_none()

        if existing:
            # Update existing
            new_weight = existing.weight + weight_adjustment

            # Clamp to bounds
            new_weight = max(config['ml_min_weight'], min(config['ml_max_weight'], new_weight))

            existing.weight = new_weight
            existing.match_count += 1
            existing.last_matched_at = datetime.utcnow()

            logger.debug(f"Updated keyword '{keyword}' in category {category_id}: {existing.weight - weight_adjustment:.2f} → {new_weight:.2f}")

        else:
            # Create new keyword
            new_weight = weight_adjustment

            # Clamp to bounds
            new_weight = max(config['ml_min_weight'], min(config['ml_max_weight'], new_weight))

            new_keyword = CategoryKeyword(
                category_id=category_id,
                keyword=keyword,
                language_code=language,
                weight=new_weight,
                match_count=1,
                last_matched_at=datetime.utcnow(),
                is_system_default=False  # Learned keywords are not system keywords
            )
            session.add(new_keyword)

            logger.debug(f"Created keyword '{keyword}' in category {category_id}: weight={new_weight:.2f}")

    def _apply_negative_learning(
        self,
        wrong_category_id: UUID,
        keywords: List[str],
        language: str,
        session: Session,
        config: Dict
    ) -> None:
        """
        Reduce weights for keywords in the wrongly predicted category

        This prevents keywords from accumulating in wrong categories
        """
        from app.database.models import CategoryKeyword

        penalty = config.get('ml_wrong_prediction_penalty', 0.3)

        for keyword in keywords:
            existing = session.execute(
                select(CategoryKeyword).where(
                    CategoryKeyword.category_id == wrong_category_id,
                    CategoryKeyword.keyword == keyword,
                    CategoryKeyword.language_code == language
                )
            ).scalar_one_or_none()

            if existing:
                # Reduce weight
                new_weight = existing.weight - penalty
                new_weight = max(config['ml_min_weight'], new_weight)

                existing.weight = new_weight
                logger.debug(f"[NEGATIVE LEARNING] Reduced '{keyword}' in wrong category: -{penalty:.2f} → {new_weight:.2f}")

    def _filter_distinctive_keywords(
        self,
        keywords: List[str],
        primary_category_id: UUID,
        language: str,
        session: Session,
        config: Dict
    ) -> List[str]:
        """
        Filter keywords to only those that are distinctive to the primary category

        A keyword is NOT distinctive if:
        - It already exists in multiple other categories with similar/higher weight
        - It's a generic term that appears across many categories

        Returns: List of distinctive keywords safe to learn
        """
        from app.database.models import CategoryKeyword
        from sqlalchemy import func

        distinctive = []
        min_differential = config.get('ml_min_weight_differential', 0.3)

        for keyword in keywords:
            # Get all categories that have this keyword
            other_categories = session.execute(
                select(CategoryKeyword).where(
                    CategoryKeyword.keyword == keyword,
                    CategoryKeyword.language_code == language,
                    CategoryKeyword.category_id != primary_category_id
                )
            ).scalars().all()

            if not other_categories:
                # Keyword doesn't exist in other categories - it's distinctive!
                distinctive.append(keyword)
                logger.debug(f"[DISTINCTIVE] '{keyword}': not in other categories ✓")
                continue

            # Check if keyword is too common (exists in many categories)
            if len(other_categories) >= 3:
                # Keyword appears in 3+ other categories - too generic
                logger.debug(f"[NOT DISTINCTIVE] '{keyword}': appears in {len(other_categories)} other categories ✗")
                continue

            # Check weight in other categories
            max_other_weight = max(kw.weight for kw in other_categories)

            # Get current weight in primary category (if exists)
            primary_kw = session.execute(
                select(CategoryKeyword).where(
                    CategoryKeyword.category_id == primary_category_id,
                    CategoryKeyword.keyword == keyword,
                    CategoryKeyword.language_code == language
                )
            ).scalar_one_or_none()

            current_primary_weight = primary_kw.weight if primary_kw else 1.0  # Default weight for new keywords

            # If keyword already has much higher weight elsewhere, don't learn it
            if max_other_weight > (current_primary_weight + min_differential):
                logger.debug(f"[NOT DISTINCTIVE] '{keyword}': stronger in other category ({max_other_weight:.2f} vs {current_primary_weight:.2f}) ✗")
                continue

            # Keyword is distinctive enough
            distinctive.append(keyword)
            logger.debug(f"[DISTINCTIVE] '{keyword}': acceptable weight differential ✓")

        return distinctive

    def learn_from_classification(
        self,
        document_id: UUID,
        document_keywords: List[str],
        primary_category_id: UUID,
        secondary_category_ids: List[UUID],
        language: str,
        user_id: UUID,
        ai_predicted_category: Optional[UUID] = None,
        ai_confidence: Optional[float] = None,
        session: Session = None
    ) -> bool:
        """
        Main entry point: Learn from document classification decision

        Args:
            document_id: Document UUID
            document_keywords: Keywords extracted from document
            primary_category_id: User's primary category choice
            secondary_category_ids: User's secondary category choices (0-4 categories)
            language: Document language
            user_id: User who made classification
            ai_predicted_category: What AI predicted (optional)
            ai_confidence: AI's confidence score 0-1 (optional)
            session: Database session

        Returns:
            True if learning completed successfully
        """
        try:
            # Load configuration
            config = self._load_config(session)

            if not config.get('ml_learning_enabled', True):
                logger.info("ML learning is disabled in configuration")
                return False

            # CRITICAL: Never learn keywords for "Other" category
            # "Other" is a fallback category and should not accumulate keywords
            from app.database.models import Category
            primary_category = session.get(Category, primary_category_id)
            if primary_category and primary_category.reference_key == 'OTH':
                logger.info(f"[ML LEARNING] Skipping learning for 'Other' category (reference_key=OTH)")
                return False

            # Also skip if any secondary categories are "Other"
            if secondary_category_ids:
                for sec_cat_id in secondary_category_ids:
                    sec_category = session.get(Category, sec_cat_id)
                    if sec_category and sec_category.reference_key == 'OTH':
                        logger.warning(f"[ML LEARNING] Skipping learning because 'Other' is in secondary categories")
                        return False

            # Filter quality keywords
            quality_keywords = self._filter_quality_keywords(
                document_keywords,
                language,
                session,
                config
            )

            min_required = config.get('ml_min_keywords_required', 3)
            if len(quality_keywords) < min_required:
                logger.info(f"Not enough quality keywords for learning: {len(quality_keywords)} < {min_required}")
                return False

            logger.info(f"Learning from {len(quality_keywords)} keywords for primary category only")

            # NEGATIVE LEARNING: If AI predicted wrong category, reduce weights there
            if ai_predicted_category and ai_predicted_category != primary_category_id:
                logger.info(f"[ML LEARNING] AI predicted wrong category - applying negative learning")
                self._apply_negative_learning(
                    wrong_category_id=ai_predicted_category,
                    keywords=quality_keywords,
                    language=language,
                    session=session,
                    config=config
                )

            # Filter keywords to only distinctive ones
            distinctive_keywords = self._filter_distinctive_keywords(
                keywords=quality_keywords,
                primary_category_id=primary_category_id,
                language=language,
                session=session,
                config=config
            )

            logger.info(f"[ML LEARNING] Filtered to {len(distinctive_keywords)} distinctive keywords from {len(quality_keywords)} total")

            if not distinctive_keywords:
                logger.warning(f"[ML LEARNING] No distinctive keywords to learn - skipping")
                return False

            # Process primary category ONLY with distinctive keywords
            for keyword in distinctive_keywords:
                # Calculate weight adjustment
                adjustment = self._calculate_weight_adjustment(
                    is_primary=True,
                    ai_predicted_category=ai_predicted_category,
                    category_id=primary_category_id,
                    ai_confidence=ai_confidence,
                    config=config
                )

                # Apply update
                self._apply_weight_update(
                    primary_category_id,
                    keyword,
                    language,
                    adjustment,
                    session,
                    config
                )

            # After primary updates, apply differential preservation
            session.flush()  # Ensure weights are updated before checking differentials

            for keyword in quality_keywords:
                # Get current weight after update
                from app.database.models import CategoryKeyword
                primary_kw = session.execute(
                    select(CategoryKeyword).where(
                        CategoryKeyword.category_id == primary_category_id,
                        CategoryKeyword.keyword == keyword,
                        CategoryKeyword.language_code == language
                    )
                ).scalar_one_or_none()

                if primary_kw:
                    adjusted_weight = self._ensure_differential_preservation(
                        primary_category_id,
                        keyword,
                        language,
                        primary_kw.weight,
                        session,
                        config
                    )

                    if adjusted_weight != primary_kw.weight:
                        primary_kw.weight = adjusted_weight

            # IMPORTANT: DO NOT learn keywords for secondary categories
            # Secondary categories are metadata tags, not classification targets
            # Learning keywords for them causes cross-contamination
            logger.info(f"[ML LEARNING] Skipping keyword learning for {len(secondary_category_ids)} secondary categories (metadata only)")

            # Log learning event
            self._log_learning_event(
                document_id=document_id,
                user_id=user_id,
                primary_category_id=primary_category_id,
                secondary_category_ids=secondary_category_ids,
                ai_predicted_category=ai_predicted_category,
                ai_confidence=ai_confidence,
                keywords_learned=distinctive_keywords,  # Log only distinctive keywords learned
                language=language,
                session=session
            )

            session.commit()

            logger.info(f"✓ Learning completed: {len(distinctive_keywords)} distinctive keywords learned for primary category only")
            return True

        except Exception as e:
            logger.error(f"Learning failed: {e}", exc_info=True)
            session.rollback()
            return False

    def _log_learning_event(
        self,
        document_id: UUID,
        user_id: UUID,
        primary_category_id: UUID,
        secondary_category_ids: List[UUID],
        ai_predicted_category: Optional[UUID],
        ai_confidence: Optional[float],
        keywords_learned: List[str],
        language: str,
        session: Session
    ) -> None:
        """Log the learning event for analytics"""
        try:
            from app.database.models import CategoryTrainingData

            was_correct = (ai_predicted_category == primary_category_id) if ai_predicted_category else None

            training_data = CategoryTrainingData(
                document_id=document_id,
                suggested_category_id=ai_predicted_category,
                actual_category_id=primary_category_id,
                was_correct=was_correct if was_correct is not None else False,
                confidence=ai_confidence,
                text_sample=", ".join(keywords_learned[:20]),
                language_code=language,
                user_id=user_id
            )

            session.add(training_data)

            logger.debug(f"Logged learning event: correct={was_correct}, keywords={len(keywords_learned)}")

        except Exception as e:
            logger.warning(f"Failed to log learning event: {e}")


# Singleton instance
ml_learning_service = MLLearningService()
