# backend/app/services/ml_category_service.py
"""
ML-based category prediction service
Learns from user corrections to improve accuracy
"""

import logging
from typing import Optional, Dict, Tuple, List
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timezone

from app.database.connection import db_manager
from app.database.models import CategoryTermWeight, CategoryTrainingData, Category
from app.services.config_service import config_service

logger = logging.getLogger(__name__)


class MLCategoryService:
    """Machine learning category prediction service"""
    
    def __init__(self):
        self._category_weights_cache: Dict[str, Dict[str, float]] = {}
    
    async def predict_category(
        self,
        text: str,
        keywords: List[Dict],
        language_code: str,
        user_categories: List[Dict],
        session: Optional[Session] = None
    ) -> Tuple[Optional[str], float]:
        """
        Predict document category using ML-based term weighting
        
        Args:
            text: Document text
            keywords: Extracted keywords list
            language_code: Document language
            user_categories: User's available categories
            session: Optional database session
            
        Returns:
            Tuple of (category_id, confidence_score)
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            if not user_categories:
                return None, 0.0
            
            # Get confidence threshold
            threshold = await config_service.get_category_confidence_threshold(session)
            
            # Load category term weights for this language
            await self._load_category_weights(language_code, session)
            
            # Calculate scores for each category
            category_scores = {}
            text_lower = text.lower()
            
            for category in user_categories:
                cat_id = category['id']
                cat_key = f"{cat_id}_{language_code}"
                
                if cat_key not in self._category_weights_cache:
                    continue
                
                weights = self._category_weights_cache[cat_key]
                score = 0.0
                
                # Score based on keyword matches
                for keyword_data in keywords:
                    keyword = keyword_data['word']
                    if keyword in weights:
                        # Use learned weight * keyword relevance
                        score += weights[keyword] * keyword_data['relevance']
                
                # Boost score for direct term matches in text
                for term, weight in weights.items():
                    if term in text_lower:
                        count = text_lower.count(term)
                        score += weight * count * 0.5  # Additional boost
                
                # Apply training data correction
                correction_factor = await self._get_training_correction(
                    cat_id, language_code, session
                )
                score *= correction_factor
                
                category_scores[cat_id] = score
            
            # Get best category
            if not category_scores:
                return None, 0.0
            
            best_cat_id = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_cat_id]
            
            # Normalize confidence to 0-1 range
            max_possible_score = sum(weights.values() for weights in self._category_weights_cache.values())
            confidence = min(best_score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
            
            # Only return if confidence meets threshold
            if confidence >= threshold:
                logger.info(f"Predicted category '{best_cat_id}' with confidence {confidence:.2f}")
                return best_cat_id, confidence
            else:
                logger.info(f"No category prediction - best confidence {confidence:.2f} below threshold {threshold}")
                return None, confidence
            
        except Exception as e:
            logger.error(f"Category prediction failed: {e}")
            return None, 0.0
        finally:
            if close_session:
                session.close()
    
    async def _load_category_weights(self, language_code: str, session: Session):
        """Load category term weights for language"""
        result = session.execute(
            select(
                CategoryTermWeight.category_id,
                CategoryTermWeight.term,
                CategoryTermWeight.weight
            ).where(
                CategoryTermWeight.language_code == language_code
            )
        )
        
        for cat_id, term, weight in result:
            cache_key = f"{cat_id}_{language_code}"
            if cache_key not in self._category_weights_cache:
                self._category_weights_cache[cache_key] = {}
            
            self._category_weights_cache[cache_key][term] = weight
    
    async def _get_training_correction(
        self, 
        category_id: str, 
        language_code: str, 
        session: Session
    ) -> float:
        """Get correction factor based on training data accuracy"""
        result = session.execute(
            text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct
                FROM category_training_data
                WHERE suggested_category_id = :cat_id
                AND language_code = :lang
            """),
            {'cat_id': category_id, 'lang': language_code}
        ).first()
        
        if result and result[0] > 0:
            accuracy = result[1] / result[0]
            # Factor ranges from 0.5 (poor) to 1.5 (excellent)
            return 0.5 + accuracy
        
        return 1.0  # Neutral if no training data
    
    async def record_category_feedback(
        self,
        suggested_category_id: Optional[str],
        actual_category_id: str,
        confidence: Optional[float],
        text_sample: str,
        language_code: str,
        user_id: str,
        document_id: Optional[str] = None,
        session: Optional[Session] = None
    ):
        """Record user's category selection for ML learning"""
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            was_correct = (suggested_category_id == actual_category_id) if suggested_category_id else False
            
            training_data = CategoryTrainingData(
                id=uuid.uuid4(),
                document_id=uuid.UUID(document_id) if document_id else None,
                suggested_category_id=uuid.UUID(suggested_category_id) if suggested_category_id else None,
                actual_category_id=uuid.UUID(actual_category_id),
                was_correct=was_correct,
                confidence=confidence,
                text_sample=text_sample[:1000],  # Limit sample size
                language_code=language_code,
                user_id=uuid.UUID(user_id),
                created_at=datetime.now(timezone.utc)
            )
            
            session.add(training_data)
            session.commit()
            
            # If incorrect, learn from the mistake
            if not was_correct and text_sample:
                await self._update_category_weights(
                    actual_category_id, text_sample, language_code, session
                )
            
            logger.info(f"Recorded category feedback: correct={was_correct}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record category feedback: {e}")
        finally:
            if close_session:
                session.close()
    
    async def _update_category_weights(
        self,
        category_id: str,
        text_sample: str,
        language_code: str,
        session: Session
    ):
        """Update category term weights based on correct classification"""
        from app.services.ml_keyword_service import ml_keyword_service
        
        # Extract keywords from the correctly categorized text
        keywords = await ml_keyword_service.extract_keywords(
            text_sample, language_code, max_keywords=10, session=session
        )
        
        for keyword_data in keywords:
            keyword = keyword_data['word']
            relevance = keyword_data['relevance']
            
            # Check if term weight exists
            existing = session.execute(
                select(CategoryTermWeight).where(
                    CategoryTermWeight.category_id == uuid.UUID(category_id),
                    CategoryTermWeight.term == keyword,
                    CategoryTermWeight.language_code == language_code
                )
            ).scalar_one_or_none()
            
            if existing:
                # Increase weight for existing term
                new_weight = existing.weight * 1.1  # 10% boost
                new_weight = min(new_weight, 5.0)  # Cap at 5.0
                
                session.execute(
                    text("""
                        UPDATE category_term_weights
                        SET weight = :weight,
                            document_frequency = document_frequency + 1,
                            last_updated = :now
                        WHERE id = :id
                    """),
                    {
                        'id': str(existing.id),
                        'weight': new_weight,
                        'now': datetime.now(timezone.utc)
                    }
                )
            else:
                # Add new term weight
                new_weight = CategoryTermWeight(
                    id=uuid.uuid4(),
                    category_id=uuid.UUID(category_id),
                    term=keyword,
                    language_code=language_code,
                    weight=relevance,
                    document_frequency=1,
                    last_updated=datetime.now(timezone.utc)
                )
                session.add(new_weight)
        
        session.commit()
        
        # Clear cache to reload updated weights
        cache_key = f"{category_id}_{language_code}"
        if cache_key in self._category_weights_cache:
            del self._category_weights_cache[cache_key]
        
        logger.info(f"Updated category weights for '{category_id}' based on training")
    
    def clear_cache(self):
        """Clear category weights cache"""
        self._category_weights_cache = {}
        logger.info("ML category service cache cleared")


# Global instance
ml_category_service = MLCategoryService()