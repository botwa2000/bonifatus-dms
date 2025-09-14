# backend/src/services/category_service.py
"""
Bonifatus DMS - Category Service
Category management and AI-powered categorization suggestions
Multilingual category support and intelligent keyword matching
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.database.models import Category, Document, User
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CategoryService:
    """Service for category management and AI categorization"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_user_categories(
        self,
        user_id: int,
        include_system: bool = True,
        include_user: bool = True,
        language: str = "en"
    ) -> List[Category]:
        """
        Get all categories available to a user
        """
        try:
            query = self.db.query(Category).filter(Category.is_active == True)
            
            # Build filter conditions
            conditions = []
            
            if include_system:
                conditions.append(Category.is_system_category == True)
            
            if include_user:
                conditions.append(
                    and_(
                        Category.user_id == user_id,
                        Category.is_system_category == False
                    )
                )
            
            if conditions:
                query = query.filter(or_(*conditions))
            else:
                # If neither system nor user categories requested, return empty
                return []
            
            # Order by system categories first, then by sort order
            query = query.order_by(
                Category.is_system_category.desc(),
                Category.sort_order.asc(),
                Category.name_en.asc()
            )
            
            categories = query.all()
            
            logger.info(f"Retrieved {len(categories)} categories for user {user_id}")
            return categories
            
        except Exception as e:
            logger.error(f"Failed to get user categories for {user_id}: {e}")
            return []
    
    async def create_category(self, category_data: Dict[str, Any]) -> Category:
        """
        Create new user-defined category
        """
        try:
            # Validate required fields
            required_fields = ["user_id", "name_en", "name_de"]
            for field in required_fields:
                if not category_data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            # Get next sort order for user
            max_sort_order = self.db.query(Category).filter(
                Category.user_id == category_data["user_id"]
            ).count()
            
            # Create category
            category = Category(
                user_id=category_data["user_id"],
                name_en=category_data["name_en"],
                name_de=category_data["name_de"],
                description_en=category_data.get("description_en"),
                description_de=category_data.get("description_de"),
                color=category_data.get("color", "#6B7280"),
                icon=category_data.get("icon"),
                keywords=category_data.get("keywords"),
                sort_order=max_sort_order + 1,
                is_system_category=False,
                is_active=True
            )
            
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
            
            logger.info(f"Created category {category.id} for user {category.user_id}")
            return category
            
        except Exception as e:
            logger.error(f"Failed to create category: {e}")
            self.db.rollback()
            raise
    
    async def update_category(
        self,
        category_id: int,
        user_id: int,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update user-defined category
        """
        try:
            category = self.db.query(Category).filter(
                and_(
                    Category.id == category_id,
                    Category.user_id == user_id,
                    Category.is_system_category == False
                )
            ).first()
            
            if not category:
                logger.warning(f"Category {category_id} not found for user {user_id}")
                return False
            
            # Update allowed fields
            updatable_fields = [
                "name_en", "name_de", "description_en", "description_de",
                "color", "icon", "keywords"
            ]
            
            updated = False
            for field, value in updates.items():
                if field in updatable_fields and hasattr(category, field):
                    setattr(category, field, value)
                    updated = True
            
            if updated:
                category.updated_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Updated category {category_id}")
            
            return updated
            
        except Exception as e:
            logger.error(f"Failed to update category {category_id}: {e}")
            self.db.rollback()
            return False
    
    async def delete_category(
        self,
        category_id: int,
        user_id: int,
        move_documents_to: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Delete user-defined category and handle associated documents
        """
        try:
            category = self.db.query(Category).filter(
                and_(
                    Category.id == category_id,
                    Category.user_id == user_id,
                    Category.is_system_category == False
                )
            ).first()
            
            if not category:
                return {
                    "success": False,
                    "error": "Category not found or cannot be deleted"
                }
            
            # Count documents in this category
            document_count = self.db.query(Document).filter(
                and_(
                    Document.category_id == category_id,
                    Document.user_id == user_id
                )
            ).count()
            
            # Handle documents
            if document_count > 0:
                if move_documents_to:
                    # Validate destination category
                    dest_category = self.db.query(Category).filter(
                        and_(
                            Category.id == move_documents_to,
                            or_(
                                Category.user_id == user_id,
                                Category.is_system_category == True
                            )
                        )
                    ).first()
                    
                    if not dest_category:
                        return {
                            "success": False,
                            "error": "Invalid destination category"
                        }
                    
                    # Move documents
                    self.db.query(Document).filter(
                        and_(
                            Document.category_id == category_id,
                            Document.user_id == user_id
                        )
                    ).update({"category_id": move_documents_to})
                    
                    # Update destination category count
                    dest_category.document_count += document_count
                    
                else:
                    # Remove category assignment from documents
                    self.db.query(Document).filter(
                        and_(
                            Document.category_id == category_id,
                            Document.user_id == user_id
                        )
                    ).update({"category_id": None})
            
            # Delete category
            self.db.delete(category)
            self.db.commit()
            
            logger.info(f"Deleted category {category_id} for user {user_id}")
            return {
                "success": True,
                "documents_moved": document_count if move_documents_to else 0,
                "documents_uncategorized": document_count if not move_documents_to else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to delete category {category_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def suggest_categories(
        self,
        user_id: int,
        text: str,
        filename: Optional[str] = None,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get AI-powered category suggestions for given text
        """
        try:
            if not text or len(text.strip()) < 10:
                return []
            
            # Get user's categories
            categories = await self.get_user_categories(
                user_id=user_id,
                include_system=True,
                include_user=True,
                language=language
            )
            
            if not categories:
                return []
            
            # Combine text sources
            combined_text = text
            if filename:
                combined_text = f"{filename} {text}"
            
            suggestions = []
            
            for category in categories:
                score = self._calculate_category_relevance(
                    combined_text, 
                    category, 
                    language
                )
                
                if score > 0.1:  # Minimum threshold
                    suggestion = {
                        "category_id": category.id,
                        "category_name": category.name_de if language == "de" else category.name_en,
                        "confidence": round(score, 3),
                        "is_system_category": category.is_system_category,
                        "color": category.color,
                        "matched_keywords": self._get_matching_keywords(
                            combined_text, 
                            category
                        )
                    }
                    suggestions.append(suggestion)
            
            # Sort by confidence score
            suggestions.sort(key=lambda x: x["confidence"], reverse=True)
            
            # Return top 5 suggestions
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Category suggestion failed for user {user_id}: {e}")
            return []
    
    async def get_category_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get category usage statistics for user
        """
        try:
            # Get category counts
            system_categories = self.db.query(Category).filter(
                Category.is_system_category == True
            ).count()
            
            user_categories = self.db.query(Category).filter(
                and_(
                    Category.user_id == user_id,
                    Category.is_system_category == False
                )
            ).count()
            
            # Get document distribution
            category_distribution = self.db.execute("""
                SELECT 
                    c.id,
                    c.name_en,
                    c.color,
                    c.is_system_category,
                    COUNT(d.id) as document_count
                FROM categories c
                LEFT JOIN documents d ON c.id = d.category_id AND d.user_id = :user_id
                WHERE (c.user_id = :user_id OR c.is_system_category = true)
                    AND c.is_active = true
                GROUP BY c.id, c.name_en, c.color, c.is_system_category
                ORDER BY document_count DESC
            """, {"user_id": user_id}).fetchall()
            
            # Format distribution data
            distribution = [
                {
                    "category_id": row.id,
                    "category_name": row.name_en,
                    "color": row.color,
                    "is_system": row.is_system_category,
                    "document_count": row.document_count
                }
                for row in category_distribution
            ]
            
            # Count uncategorized documents
            uncategorized_count = self.db.query(Document).filter(
                and_(
                    Document.user_id == user_id,
                    Document.category_id.is_(None)
                )
            ).count()
            
            return {
                "total_categories": system_categories + user_categories,
                "system_categories": system_categories,
                "user_categories": user_categories,
                "category_distribution": distribution,
                "uncategorized_documents": uncategorized_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get category statistics for user {user_id}: {e}")
            return {}
    
    async def reorder_categories(
        self,
        user_id: int,
        category_orders: List[Dict[str, int]]
    ) -> bool:
        """
        Reorder user categories by updating sort_order
        """
        try:
            for item in category_orders:
                category_id = item.get("category_id")
                new_order = item.get("sort_order")
                
                if category_id and new_order is not None:
                    category = self.db.query(Category).filter(
                        and_(
                            Category.id == category_id,
                            Category.user_id == user_id,
                            Category.is_system_category == False
                        )
                    ).first()
                    
                    if category:
                        category.sort_order = new_order
                        category.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Reordered categories for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reorder categories for user {user_id}: {e}")
            self.db.rollback()
            return False
    
    def _calculate_category_relevance(
        self,
        text: str,
        category: Category,
        language: str
    ) -> float:
        """
        Calculate relevance score between text and category
        """
        try:
            if not category.keywords:
                # Use category names as fallback keywords
                fallback_keywords = [
                    category.name_en.lower(),
                    category.name_de.lower()
                ]
                keywords = fallback_keywords
            else:
                keywords = [kw.strip().lower() for kw in category.keywords.split(",")]
            
            text_lower = text.lower()
            total_score = 0.0
            keyword_matches = 0
            
            for keyword in keywords:
                if keyword in text_lower:
                    keyword_matches += 1
                    
                    # Score based on keyword frequency and length
                    frequency = text_lower.count(keyword)
                    length_bonus = min(len(keyword) / 20, 1.0)  # Longer keywords get bonus
                    keyword_score = frequency * (1 + length_bonus)
                    
                    total_score += keyword_score
            
            # Normalize score
            if len(keywords) > 0:
                relevance = min(total_score / len(keywords), 1.0)
                
                # Apply match ratio bonus
                match_ratio = keyword_matches / len(keywords)
                relevance *= (0.5 + 0.5 * match_ratio)
                
                return relevance
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Category relevance calculation failed: {e}")
            return 0.0
    
    def _get_matching_keywords(self, text: str, category: Category) -> List[str]:
        """
        Get list of keywords that match between text and category
        """
        try:
            if not category.keywords:
                # Check category names
                matches = []
                text_lower = text.lower()
                
                if category.name_en.lower() in text_lower:
                    matches.append(category.name_en.lower())
                if category.name_de.lower() in text_lower:
                    matches.append(category.name_de.lower())
                
                return matches
            
            keywords = [kw.strip().lower() for kw in category.keywords.split(",")]
            text_lower = text.lower()
            
            matching = [kw for kw in keywords if kw in text_lower]
            return matching
            
        except Exception:
            return []