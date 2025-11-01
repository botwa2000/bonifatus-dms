"""
Keyword Management Service for Bonifatus DMS
Handles CRUD operations for category keywords with overlap detection
"""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_

from app.database.models import CategoryKeyword, Category

logger = logging.getLogger(__name__)


class KeywordManagementService:
    """Service for managing category keywords"""

    def list_keywords(
        self,
        category_id: str,
        language_code: Optional[str] = None,
        session: Session = None
    ) -> List[Dict]:
        """
        Get all keywords for a category, optionally filtered by language

        Args:
            category_id: Category UUID
            language_code: Optional language code filter (e.g., 'en', 'de', 'ru').
                          If None, returns keywords in ALL languages.
            session: Database session

        Returns:
            List of keyword dictionaries with metadata
        """
        try:
            # Build query
            query = session.query(CategoryKeyword).filter(
                CategoryKeyword.category_id == category_id
            )

            # Apply language filter if specified
            if language_code:
                query = query.filter(CategoryKeyword.language_code == language_code)

            # Order by language, weight, keyword
            keywords = query.order_by(
                CategoryKeyword.language_code,
                CategoryKeyword.weight.desc(),
                CategoryKeyword.keyword
            ).all()

            return [{
                'id': str(keyword.id),
                'keyword': keyword.keyword,
                'language_code': keyword.language_code,
                'weight': keyword.weight,
                'match_count': keyword.match_count,
                'last_matched_at': keyword.last_matched_at.isoformat() if keyword.last_matched_at else None,
                'is_system_default': keyword.is_system_default,
                'created_at': keyword.created_at.isoformat() if keyword.created_at else None
            } for keyword in keywords]

        except Exception as e:
            logger.error(f"Failed to list keywords: {e}")
            raise

    def add_keyword(
        self,
        category_id: str,
        keyword: str,
        language_code: str,
        weight: float = 1.0,
        user_id: str = None,
        session: Session = None
    ) -> Dict:
        """
        Add new keyword to a category

        Args:
            category_id: Category UUID
            keyword: Keyword text
            language_code: Language code
            weight: Keyword weight (0.1-10.0)
            user_id: User ID (for authorization check)
            session: Database session

        Returns:
            Created keyword dictionary

        Raises:
            ValueError: If validation fails
            PermissionError: If user doesn't own category
        """
        try:
            # Validate category ownership
            category = session.query(Category).filter(Category.id == category_id).first()
            if not category:
                raise ValueError("Category not found")

            if user_id and str(category.user_id) != user_id and not category.is_system:
                raise PermissionError("Not authorized to modify this category")

            # Validate keyword
            keyword_clean = self._validate_and_clean_keyword(keyword)

            # Validate weight
            if not (0.1 <= weight <= 10.0):
                raise ValueError("Weight must be between 0.1 and 10.0")

            # Check for duplicates (case-insensitive)
            existing = session.query(CategoryKeyword).filter(
                and_(
                    CategoryKeyword.category_id == category_id,
                    func.lower(CategoryKeyword.keyword) == keyword_clean.lower(),
                    CategoryKeyword.language_code == language_code
                )
            ).first()

            if existing:
                raise ValueError(f"Keyword '{keyword_clean}' already exists for this category and language")

            # Create new keyword
            new_keyword = CategoryKeyword(
                id=uuid.uuid4(),
                category_id=category_id,
                keyword=keyword_clean,
                language_code=language_code,
                weight=weight,
                match_count=0,
                is_system_default=False,
                created_at=datetime.utcnow()
            )

            session.add(new_keyword)
            session.commit()

            logger.info(f"Added keyword '{keyword_clean}' to category {category_id} (lang: {language_code})")

            return {
                'id': str(new_keyword.id),
                'keyword': new_keyword.keyword,
                'language_code': new_keyword.language_code,
                'weight': new_keyword.weight,
                'match_count': 0,
                'last_matched_at': None,
                'is_system_default': False,
                'created_at': new_keyword.created_at.isoformat()
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add keyword: {e}")
            raise

    def update_keyword_weight(
        self,
        keyword_id: str,
        weight: float,
        user_id: str,
        session: Session
    ) -> Dict:
        """
        Update keyword weight

        Args:
            keyword_id: Keyword UUID
            weight: New weight (0.1-10.0)
            user_id: User ID (for authorization)
            session: Database session

        Returns:
            Updated keyword dictionary
        """
        try:
            # Validate weight
            if not (0.1 <= weight <= 10.0):
                raise ValueError("Weight must be between 0.1 and 10.0")

            # Get keyword with category check
            keyword = session.query(CategoryKeyword).filter(
                CategoryKeyword.id == keyword_id
            ).first()

            if not keyword:
                raise ValueError("Keyword not found")

            # Check ownership
            category = session.query(Category).filter(
                Category.id == keyword.category_id
            ).first()

            if str(category.user_id) != user_id and not category.is_system:
                raise PermissionError("Not authorized to modify this keyword")

            # Update weight
            old_weight = keyword.weight
            keyword.weight = weight
            keyword.last_updated = datetime.utcnow()

            session.commit()

            logger.info(f"Updated keyword '{keyword.keyword}' weight: {old_weight} -> {weight}")

            return {
                'id': str(keyword.id),
                'keyword': keyword.keyword,
                'language_code': keyword.language_code,
                'weight': keyword.weight,
                'match_count': keyword.match_count,
                'last_matched_at': keyword.last_matched_at.isoformat() if keyword.last_matched_at else None,
                'is_system_default': keyword.is_system_default,
                'created_at': keyword.created_at.isoformat() if keyword.created_at else None
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update keyword weight: {e}")
            raise

    def delete_keyword(
        self,
        keyword_id: str,
        user_id: str,
        session: Session
    ) -> bool:
        """
        Delete a custom keyword (system keywords protected)

        Args:
            keyword_id: Keyword UUID
            user_id: User ID (for authorization)
            session: Database session

        Returns:
            True if deleted

        Raises:
            ValueError: If keyword is system default
            PermissionError: If user doesn't own category
        """
        try:
            keyword = session.query(CategoryKeyword).filter(
                CategoryKeyword.id == keyword_id
            ).first()

            if not keyword:
                raise ValueError("Keyword not found")

            # Protect system keywords
            if keyword.is_system_default:
                raise ValueError("Cannot delete system default keywords")

            # Check ownership
            category = session.query(Category).filter(
                Category.id == keyword.category_id
            ).first()

            if str(category.user_id) != user_id and not category.is_system:
                raise PermissionError("Not authorized to delete this keyword")

            keyword_text = keyword.keyword
            session.delete(keyword)
            session.commit()

            logger.info(f"Deleted keyword '{keyword_text}' (id: {keyword_id})")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete keyword: {e}")
            raise

    def detect_overlaps(
        self,
        user_id: str,
        language_code: str,
        session: Session
    ) -> List[Dict]:
        """
        Detect keyword overlaps across user's categories

        Args:
            user_id: User ID
            language_code: Language to check
            session: Database session

        Returns:
            List of overlap dictionaries with severity levels
        """
        try:
            # Get all keywords for user's categories in specified language
            overlaps_query = text("""
                WITH keyword_usage AS (
                    SELECT
                        LOWER(ck.keyword) as keyword_lower,
                        ck.keyword as keyword_original,
                        ck.category_id,
                        c.reference_key,
                        ck.weight,
                        ck.match_count,
                        ck.is_system_default
                    FROM category_keywords ck
                    JOIN categories c ON c.id = ck.category_id
                    WHERE c.user_id = :user_id
                        AND ck.language_code = :language_code
                        AND c.is_active = true
                ),
                overlapping_keywords AS (
                    SELECT keyword_lower, COUNT(DISTINCT category_id) as category_count
                    FROM keyword_usage
                    GROUP BY keyword_lower
                    HAVING COUNT(DISTINCT category_id) > 1
                )
                SELECT
                    ku.keyword_original,
                    ku.keyword_lower,
                    ku.category_id,
                    ku.reference_key,
                    ku.weight,
                    ku.match_count,
                    ku.is_system_default
                FROM keyword_usage ku
                JOIN overlapping_keywords ok ON ok.keyword_lower = ku.keyword_lower
                ORDER BY ku.keyword_lower, ku.weight DESC
            """)

            results = session.execute(overlaps_query, {
                'user_id': user_id,
                'language_code': language_code
            }).fetchall()

            # Group by keyword
            overlaps_dict: Dict[str, List] = {}
            for row in results:
                keyword_lower = row.keyword_lower
                if keyword_lower not in overlaps_dict:
                    overlaps_dict[keyword_lower] = {
                        'keyword': row.keyword_original,
                        'categories': []
                    }

                overlaps_dict[keyword_lower]['categories'].append({
                    'category_id': str(row.category_id),
                    'reference_key': row.reference_key,
                    'weight': float(row.weight),
                    'match_count': row.match_count,
                    'is_system_default': row.is_system_default
                })

            # Calculate severity for each overlap
            overlaps_list = []
            for keyword_lower, data in overlaps_dict.items():
                categories = data['categories']
                weights = [c['weight'] for c in categories]

                # Calculate severity
                severity = self._calculate_overlap_severity(weights)

                overlaps_list.append({
                    'keyword': data['keyword'],
                    'categories': categories,
                    'severity': severity,
                    'category_count': len(categories)
                })

            # Sort by severity (high -> medium -> low)
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            overlaps_list.sort(key=lambda x: (severity_order[x['severity']], -x['category_count']))

            logger.info(f"Found {len(overlaps_list)} keyword overlaps for user {user_id} (lang: {language_code})")
            return overlaps_list

        except Exception as e:
            logger.error(f"Failed to detect overlaps: {e}")
            raise

    def _validate_and_clean_keyword(self, keyword: str) -> str:
        """
        Validate and clean keyword text

        Args:
            keyword: Raw keyword text

        Returns:
            Cleaned keyword

        Raises:
            ValueError: If validation fails
        """
        if not keyword:
            raise ValueError("Keyword cannot be empty")

        # Strip whitespace
        cleaned = keyword.strip()

        # Check length
        if len(cleaned) < 2:
            raise ValueError("Keyword must be at least 2 characters")

        if len(cleaned) > 200:
            raise ValueError("Keyword cannot exceed 200 characters")

        # Check allowed characters (letters, numbers, spaces, hyphens, underscores)
        import re
        if not re.match(r'^[\w\s\-]+$', cleaned, re.UNICODE):
            raise ValueError("Keyword contains invalid characters (only letters, numbers, spaces, hyphens allowed)")

        return cleaned

    def _calculate_overlap_severity(self, weights: List[float]) -> str:
        """
        Calculate severity level for keyword overlap

        Args:
            weights: List of weights from different categories

        Returns:
            'high', 'medium', or 'low'
        """
        if len(weights) < 2:
            return 'low'

        weights_sorted = sorted(weights, reverse=True)
        max_weight = weights_sorted[0]
        second_weight = weights_sorted[1]

        # Calculate weight difference
        if max_weight == 0:
            diff_ratio = 0
        else:
            diff_ratio = abs(max_weight - second_weight) / max_weight

        # High risk: weights are very similar (diff < 20%)
        if diff_ratio < 0.2:
            return 'high'
        # Medium risk: weights are somewhat different (diff 20-50%)
        elif diff_ratio < 0.5:
            return 'medium'
        # Low risk: weights are very different (diff > 50%)
        else:
            return 'low'


keyword_management_service = KeywordManagementService()
