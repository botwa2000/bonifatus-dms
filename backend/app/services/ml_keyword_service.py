# backend/app/services/ml_keyword_service.py
"""
ML-based keyword extraction service with learning capability
Learns from user corrections to improve over time
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from collections import Counter
from sqlalchemy import select, text
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timezone

from app.database.connection import db_manager
from app.database.models import (
    StopWord, SpellingCorrection, NgramPattern, 
    KeywordTrainingData, CategoryTermWeight
)
from app.services.config_service import config_service

logger = logging.getLogger(__name__)


class MLKeywordService:
    """Machine learning keyword extraction service"""
    
    def __init__(self):
        self._stop_words_cache: Dict[str, set] = {}
        self._spelling_cache: Dict[str, Dict[str, str]] = {}
        self._ngram_cache: Dict[str, List[Dict]] = {}
    
    async def extract_keywords(
        self,
        text: str,
        language_code: str,
        max_keywords: Optional[int] = None,
        session: Optional[Session] = None
    ) -> List[Dict[str, any]]:
        """
        Extract keywords from text with ML-based filtering and correction
        
        Args:
            text: Input text to extract keywords from
            language_code: Language of the text (en, de, ru, etc.)
            max_keywords: Maximum number of keywords to return
            session: Optional database session
            
        Returns:
            List of keyword dictionaries with word, count, relevance
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            # Get configuration
            if max_keywords is None:
                max_keywords = await config_service.get_max_keywords(session)
            
            min_length = await config_service.get_min_keyword_length(session)
            relevance_threshold = await config_service.get_keyword_relevance_threshold(session)
            spelling_enabled = await config_service.is_spelling_correction_enabled(session)
            ngram_enabled = await config_service.is_ngram_extraction_enabled(session)
            
            # Load stop words for this language
            stop_words = await self._get_stop_words(language_code, session)
            
            # Step 1: Extract n-grams if enabled
            ngrams = []
            if ngram_enabled:
                ngrams = await self._extract_ngrams(text, language_code, session)
            
            # Step 2: Tokenize and clean
            words = self._tokenize(text, min_length)
            
            # Step 3: Remove stop words
            words = [w for w in words if w not in stop_words]
            
            # Step 4: Apply spelling corrections if enabled
            if spelling_enabled:
                words = await self._apply_spelling_corrections(words, language_code, session)
            
            # Step 5: Count frequencies
            word_counts = Counter(words)
            
            # Step 6: Add n-grams to word counts
            for ngram_data in ngrams:
                ngram = ngram_data['pattern']
                if ngram in text.lower():
                    count = text.lower().count(ngram)
                    # N-grams get boosted score
                    word_counts[ngram] = count * ngram_data['score']
            
            # Step 7: Calculate relevance scores (TF-IDF inspired)
            total_words = len(words)
            keywords = []
            
            for word, count in word_counts.items():
                # Term frequency
                tf = count / total_words if total_words > 0 else 0
                
                # Get learned importance from training data
                learned_score = await self._get_learned_score(word, language_code, session)
                
                # Combined relevance score
                relevance = tf * (1 + learned_score)
                
                if relevance >= relevance_threshold:
                    keywords.append({
                        'word': word,
                        'count': count,
                        'relevance': round(relevance, 3)
                    })
            
            # Step 8: Sort by relevance and limit
            keywords.sort(key=lambda x: x['relevance'], reverse=True)
            keywords = keywords[:max_keywords]
            
            logger.info(f"Extracted {len(keywords)} keywords for language '{language_code}'")
            return keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
        finally:
            if close_session:
                session.close()
    
    def _tokenize(self, text: str, min_length: int) -> List[str]:
        """Tokenize text into words"""
        # Convert to lowercase and extract alphanumeric words
        words = re.findall(r'\b[a-zA-Z0-9äöüßÄÖÜа-яА-ЯёЁ]+\b', text.lower())
        
        # Filter by minimum length
        words = [w for w in words if len(w) >= min_length]
        
        return words
    
    async def _get_stop_words(self, language_code: str, session: Session) -> set:
        """Get stop words for language with caching"""
        if language_code in self._stop_words_cache:
            return self._stop_words_cache[language_code]
        
        result = session.execute(
            select(StopWord.word).where(
                StopWord.language_code == language_code,
                StopWord.is_active == True
            )
        )
        
        stop_words = {row[0] for row in result}
        self._stop_words_cache[language_code] = stop_words
        
        return stop_words
    
    async def _apply_spelling_corrections(
        self, 
        words: List[str], 
        language_code: str, 
        session: Session
    ) -> List[str]:
        """Apply learned spelling corrections"""
        # Load corrections for this language
        if language_code not in self._spelling_cache:
            result = session.execute(
                select(
                    SpellingCorrection.incorrect_term,
                    SpellingCorrection.correct_term
                ).where(
                    SpellingCorrection.language_code == language_code,
                    SpellingCorrection.confidence_score >= 0.7
                )
            )
            
            corrections = {row[0]: row[1] for row in result}
            self._spelling_cache[language_code] = corrections
        
        corrections = self._spelling_cache[language_code]
        
        # Apply corrections and update usage counts
        corrected_words = []
        for word in words:
            if word in corrections:
                corrected_word = corrections[word]
                corrected_words.append(corrected_word)
                
                # Update usage count
                session.execute(
                    text("""
                        UPDATE spelling_corrections 
                        SET usage_count = usage_count + 1,
                            last_used_at = :now
                        WHERE incorrect_term = :incorrect 
                        AND language_code = :lang
                    """),
                    {
                        'incorrect': word,
                        'lang': language_code,
                        'now': datetime.now(timezone.utc)
                    }
                )
            else:
                corrected_words.append(word)
        
        return corrected_words
    
    async def _extract_ngrams(
        self, 
        text: str, 
        language_code: str, 
        session: Session
    ) -> List[Dict]:
        """Extract important multi-word patterns"""
        if language_code not in self._ngram_cache:
            result = session.execute(
                select(
                    NgramPattern.pattern,
                    NgramPattern.importance_score
                ).where(
                    NgramPattern.language_code == language_code,
                    NgramPattern.is_active == True
                ).order_by(NgramPattern.importance_score.desc())
            )
            
            ngrams = [
                {'pattern': row[0], 'score': row[1]} 
                for row in result
            ]
            self._ngram_cache[language_code] = ngrams
        
        text_lower = text.lower()
        found_ngrams = []
        
        for ngram_data in self._ngram_cache[language_code]:
            pattern = ngram_data['pattern']
            if pattern in text_lower:
                found_ngrams.append(ngram_data)
                
                # Update usage count
                session.execute(
                    text("""
                        UPDATE ngram_patterns 
                        SET usage_count = usage_count + 1,
                            updated_at = :now
                        WHERE pattern = :pattern 
                        AND language_code = :lang
                    """),
                    {
                        'pattern': pattern,
                        'lang': language_code,
                        'now': datetime.now(timezone.utc)
                    }
                )
        
        return found_ngrams
    
    async def _get_learned_score(
        self, 
        keyword: str, 
        language_code: str, 
        session: Session
    ) -> float:
        """Get learned importance score from training data"""
        result = session.execute(
            text("""
                SELECT 
                    AVG(CASE WHEN was_accepted THEN relevance_score ELSE 0 END) as avg_score,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN was_accepted THEN 1 ELSE 0 END) as accepted_count
                FROM keyword_training_data
                WHERE keyword = :keyword
                AND language_code = :lang
            """),
            {'keyword': keyword, 'lang': language_code}
        ).first()
        
        if result and result[1] > 0:  # total_count > 0
            avg_score = result[0] or 0
            acceptance_rate = result[2] / result[1]  # accepted_count / total_count
            
            # Boost score based on acceptance rate
            learned_score = avg_score * acceptance_rate
            return learned_score
        
        return 0.0
    
    async def record_keyword_feedback(
        self,
        keyword: str,
        language_code: str,
        was_accepted: bool,
        relevance_score: Optional[float],
        user_id: str,
        document_type: Optional[str] = None,
        session: Optional[Session] = None
    ):
        """Record user feedback on keyword quality for ML learning"""
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            training_data = KeywordTrainingData(
                id=uuid.uuid4(),
                keyword=keyword,
                language_code=language_code,
                was_accepted=was_accepted,
                relevance_score=relevance_score,
                user_id=uuid.UUID(user_id),
                document_type=document_type,
                created_at=datetime.now(timezone.utc)
            )
            
            session.add(training_data)
            session.commit()
            
            logger.info(f"Recorded keyword feedback: '{keyword}' - accepted={was_accepted}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record keyword feedback: {e}")
        finally:
            if close_session:
                session.close()
    
    async def suggest_spelling_correction(
        self,
        incorrect_term: str,
        correct_term: str,
        language_code: str,
        session: Optional[Session] = None
    ):
        """Add a new spelling correction suggestion"""
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            # Check if correction already exists
            existing = session.execute(
                select(SpellingCorrection).where(
                    SpellingCorrection.incorrect_term == incorrect_term,
                    SpellingCorrection.language_code == language_code
                )
            ).scalar_one_or_none()
            
            if existing:
                # Update existing
                existing.correct_term = correct_term
                existing.confidence_score = min(existing.confidence_score + 0.1, 1.0)
                existing.usage_count += 1
            else:
                # Create new
                correction = SpellingCorrection(
                    id=uuid.uuid4(),
                    incorrect_term=incorrect_term,
                    correct_term=correct_term,
                    language_code=language_code,
                    confidence_score=0.5,  # Start with medium confidence
                    usage_count=1,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(correction)
            
            session.commit()
            
            # Clear cache to load new correction
            if language_code in self._spelling_cache:
                del self._spelling_cache[language_code]
            
            logger.info(f"Added spelling correction: '{incorrect_term}' -> '{correct_term}' ({language_code})")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add spelling correction: {e}")
        finally:
            if close_session:
                session.close()
    
    def clear_caches(self):
        """Clear all caches"""
        self._stop_words_cache = {}
        self._spelling_cache = {}
        self._ngram_cache = {}
        logger.info("ML keyword service caches cleared")


# Global instance
ml_keyword_service = MLKeywordService()