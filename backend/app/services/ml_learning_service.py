"""
ML Learning Service for Bonifatus DMS
Handles weight adjustments based on user feedback
Updates category keyword weights when users confirm/correct classifications
"""

import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

logger = logging.getLogger(__name__)


class MLLearningService:
    """Service for ML weight adjustment based on user feedback"""

    def get_learning_config(self, db: Session) -> dict:
        """
        Load ML learning configuration from database
        Returns dict with boost/penalty parameters
        """
        try:
            from app.database.models import SystemSetting
            import json

            result = db.query(SystemSetting).filter(
                SystemSetting.setting_key == 'classification_config'
            ).first()

            if result:
                config = json.loads(result.setting_value)
                return config
            else:
                return {
                    'weight_boost_correct': 0.1,
                    'weight_penalty_incorrect': 0.05,
                    'weight_min': 0.1,
                    'weight_max': 10.0
                }

        except Exception as e:
            logger.error(f"Failed to load learning config: {e}")
            return {
                'weight_boost_correct': 0.1,
                'weight_penalty_incorrect': 0.05,
                'weight_min': 0.1,
                'weight_max': 10.0
            }

    def record_classification_decision(
        self,
        db: Session,
        document_id: UUID,
        suggested_category_id: Optional[UUID],
        actual_category_id: UUID,
        document_keywords: List[str],
        language: str,
        confidence: Optional[float] = None,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Record a classification decision for tracking and learning

        Args:
            db: Database session
            document_id: Document UUID
            suggested_category_id: AI-suggested category (None if no suggestion)
            actual_category_id: User's final choice
            document_keywords: Keywords that were used
            language: Document language
            confidence: Confidence score of suggestion
            user_id: User who made the decision

        Returns:
            True if recorded successfully
        """
        try:
            from app.database.models import CategoryTrainingData

            was_correct = (suggested_category_id == actual_category_id) if suggested_category_id else False

            training_data = CategoryTrainingData(
                document_id=document_id,
                suggested_category_id=suggested_category_id,
                actual_category_id=actual_category_id,
                was_correct=was_correct,
                confidence=confidence,
                text_sample=", ".join(document_keywords[:20]),
                language_code=language,
                user_id=user_id
            )

            db.add(training_data)
            db.commit()

            logger.info(f"Recorded classification decision: correct={was_correct}, category={actual_category_id}")

            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record classification decision: {e}")
            return False

    def adjust_weights_correct_suggestion(
        self,
        db: Session,
        category_id: UUID,
        matched_keywords: List[str],
        language: str
    ) -> int:
        """
        Boost weights for keywords when suggestion was correct

        Args:
            db: Database session
            category_id: Category that was correctly suggested
            matched_keywords: Keywords that matched
            language: Document language

        Returns:
            Number of keywords updated
        """
        try:
            from app.database.models import CategoryKeyword

            config = self.get_learning_config(db)
            boost_factor = 1.0 + config['weight_boost_correct']
            max_weight = config['weight_max']

            updated_count = 0

            for keyword in matched_keywords:
                keyword_lower = keyword.lower()

                existing = db.query(CategoryKeyword).filter(
                    CategoryKeyword.category_id == category_id,
                    CategoryKeyword.keyword == keyword_lower,
                    CategoryKeyword.language_code == language
                ).first()

                if existing:
                    new_weight = min(existing.weight * boost_factor, max_weight)
                    existing.weight = new_weight
                    existing.match_count += 1
                    existing.last_matched_at = datetime.utcnow()
                    updated_count += 1

            db.commit()

            logger.info(f"Boosted weights for {updated_count} keywords in category {category_id}")

            return updated_count

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to boost keyword weights: {e}")
            return 0

    def adjust_weights_incorrect_suggestion(
        self,
        db: Session,
        suggested_category_id: UUID,
        actual_category_id: UUID,
        matched_keywords: List[str],
        language: str
    ) -> int:
        """
        Penalize weights for incorrect suggestion, boost weights for correct category

        Args:
            db: Database session
            suggested_category_id: Category that was incorrectly suggested
            actual_category_id: Category that user selected
            matched_keywords: Keywords that led to wrong suggestion
            language: Document language

        Returns:
            Number of keywords updated
        """
        try:
            from app.database.models import CategoryKeyword

            config = self.get_learning_config(db)
            penalty_factor = 1.0 - config['weight_penalty_incorrect']
            min_weight = config['weight_min']

            updated_count = 0

            for keyword in matched_keywords:
                keyword_lower = keyword.lower()

                wrong_category_kw = db.query(CategoryKeyword).filter(
                    CategoryKeyword.category_id == suggested_category_id,
                    CategoryKeyword.keyword == keyword_lower,
                    CategoryKeyword.language_code == language
                ).first()

                if wrong_category_kw:
                    new_weight = max(wrong_category_kw.weight * penalty_factor, min_weight)
                    wrong_category_kw.weight = new_weight
                    updated_count += 1

            db.commit()

            logger.info(f"Penalized weights for {updated_count} keywords in incorrect category {suggested_category_id}")

            return updated_count

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to adjust keyword weights: {e}")
            return 0

    def learn_from_decision(
        self,
        db: Session,
        document_id: UUID,
        suggested_category_id: Optional[UUID],
        actual_category_id: UUID,
        matched_keywords: List[str],
        document_keywords: List[str],
        language: str,
        confidence: Optional[float] = None,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Complete learning workflow: record decision and adjust weights

        Args:
            db: Database session
            document_id: Document UUID
            suggested_category_id: AI-suggested category
            actual_category_id: User's final choice
            matched_keywords: Keywords that matched for suggestion
            document_keywords: All document keywords
            language: Document language
            confidence: Confidence score
            user_id: User who made the decision

        Returns:
            True if learning completed successfully
        """
        try:
            self.record_classification_decision(
                db,
                document_id,
                suggested_category_id,
                actual_category_id,
                document_keywords,
                language,
                confidence,
                user_id
            )

            if suggested_category_id == actual_category_id:
                self.adjust_weights_correct_suggestion(
                    db,
                    actual_category_id,
                    matched_keywords,
                    language
                )
                logger.info("Learning: Boosted weights for correct suggestion")

            elif suggested_category_id is not None:
                self.adjust_weights_incorrect_suggestion(
                    db,
                    suggested_category_id,
                    actual_category_id,
                    matched_keywords,
                    language
                )
                logger.info("Learning: Adjusted weights for incorrect suggestion")

            return True

        except Exception as e:
            logger.error(f"Learning workflow failed: {e}")
            return False


ml_learning_service = MLLearningService()
