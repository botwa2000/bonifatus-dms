# backend/src/services/category_service.py - Fixed Architecture

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.database.models import Category, Document, User, DocumentStatus
from src.core.config import settings

logger = logging.getLogger(__name__)


class CategoryService:
    """Category management service - retrieves categories from database"""

    def __init__(self, db: Session):
        self.db = db

    async def get_user_categories(
        self,
        user_id: int,
        include_system: bool = True,
        include_user: bool = True,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """Get categories available to user (from database only)"""
        try:
            query = self.db.query(Category)

            conditions = []
            if include_system:
                conditions.append(Category.is_system_category == True)
            if include_user:
                conditions.append(
                    and_(
                        Category.user_id == user_id,
                        Category.is_system_category == False,
                    )
                )

            if conditions:
                query = query.filter(or_(*conditions))
            else:
                # If neither system nor user categories requested, return empty
                return []

            categories = query.order_by(
                Category.is_system_category.desc(),  # System categories first
                Category.name_en.asc(),
            ).all()

            # Format results with document counts
            formatted_categories = []
            for cat in categories:
                # Count documents in this category
                doc_count = (
                    self.db.query(Document)
                    .filter(
                        and_(
                            Document.category_id == cat.id,
                            Document.user_id == user_id,
                            Document.status == DocumentStatus.READY,
                        )
                    )
                    .count()
                )

                formatted_cat = {
                    "id": cat.id,
                    "name": cat.name_de if language == "de" else cat.name_en,
                    "name_en": cat.name_en,
                    "name_de": cat.name_de,
                    "description": (
                        cat.description_de if language == "de" else cat.description_en
                    ),
                    "description_en": cat.description_en,
                    "description_de": cat.description_de,
                    "color": cat.color,
                    "icon": cat.icon,
                    "keywords": cat.keywords.split(",") if cat.keywords else [],
                    "is_system_category": cat.is_system_category,
                    "document_count": doc_count,
                    "created_at": cat.created_at.isoformat(),
                    "last_used_at": (
                        cat.last_used_at.isoformat() if cat.last_used_at else None
                    ),
                }
                formatted_categories.append(formatted_cat)

            return formatted_categories

        except Exception as e:
            logger.error(f"Get user categories failed: {e}")
            return []

    async def initialize_default_categories(self) -> bool:
        """
        Initialize default system categories (compatibility method for tests)
        Note: Default categories are actually created by database connection initialization
        """
        try:
            # Check if system categories already exist
            existing_categories = self.db.query(Category).filter(
                Category.is_system_category == True
            ).count()
            
            if existing_categories > 0:
                logger.info("Default categories already exist")
                return True
            
            # If no system categories exist, they should be created by database initialization
            # This method is mainly for test compatibility
            logger.info("Default categories will be created by database initialization")
            return True
            
        except Exception as e:
            logger.error(f"Initialize default categories failed: {e}")
            return False

    async def create_user_category(
        self, user_id: int, category_data: Dict[str, Any]
    ) -> Optional[Category]:
        """Create user-defined category"""
        try:
            # Check user's category limit
            user_categories_count = (
                self.db.query(Category)
                .filter(
                    and_(
                        Category.user_id == user_id,
                        Category.is_system_category == False,
                    )
                )
                .count()
            )

            if user_categories_count >= 50:  # Limit user categories
                logger.warning(f"User {user_id} exceeded category limit")
                return None

            # Create category
            category = Category(
                user_id=user_id,
                name_en=category_data.get("name_en", ""),
                name_de=category_data.get("name_de", ""),
                description_en=category_data.get("description_en", ""),
                description_de=category_data.get("description_de", ""),
                color=category_data.get("color", "#808080"),
                icon=category_data.get("icon", "📁"),
                keywords=category_data.get("keywords", ""),
                is_system_category=False,
                created_at=datetime.utcnow(),
            )

            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)

            logger.info(f"Created user category {category.id} for user {user_id}")
            return category

        except Exception as e:
            self.db.rollback()
            logger.error(f"Create user category failed: {e}")
            return None

    async def update_category(
        self, category_id: int, user_id: int, updates: Dict[str, Any]
    ) -> Optional[Category]:
        """Update user category (system categories cannot be updated)"""
        try:
            category = (
                self.db.query(Category)
                .filter(
                    and_(
                        Category.id == category_id,
                        Category.user_id == user_id,
                        Category.is_system_category == False,
                    )
                )
                .first()
            )

            if not category:
                return None

            # Apply updates
            allowed_fields = [
                "name_en",
                "name_de",
                "description_en",
                "description_de",
                "color",
                "icon",
                "keywords",
            ]
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(category, field, value)

            category.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(category)

            logger.info(f"Updated category {category_id}")
            return category

        except Exception as e:
            self.db.rollback()
            logger.error(f"Update category failed: {e}")
            return None

    async def delete_category(self, category_id: int, user_id: int) -> bool:
        """Delete user category and reassign documents"""
        try:
            category = (
                self.db.query(Category)
                .filter(
                    and_(
                        Category.id == category_id,
                        Category.user_id == user_id,
                        Category.is_system_category == False,
                    )
                )
                .first()
            )

            if not category:
                return False

            # Find documents in this category
            documents_in_category = (
                self.db.query(Document)
                .filter(
                    and_(
                        Document.category_id == category_id, Document.user_id == user_id
                    )
                )
                .all()
            )

            # Reassign to default category or uncategorized
            default_category = (
                self.db.query(Category)
                .filter(
                    and_(
                        Category.is_system_category == True,
                        Category.name_en == "Archive",
                    )
                )
                .first()
            )

            for doc in documents_in_category:
                doc.category_id = default_category.id if default_category else None
                doc.updated_at = datetime.utcnow()

            # Delete category
            self.db.delete(category)
            self.db.commit()

            logger.info(
                f"Deleted category {category_id}, reassigned {len(documents_in_category)} documents"
            )
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Delete category failed: {e}")
            return False

    async def suggest_categories(
        self, text: str, user_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Suggest categories based on document content"""
        try:
            # Get all categories available to user (from database)
            categories = await self.get_user_categories(
                user_id, include_system=True, include_user=True
            )

            if not categories:
                return []

            # Score categories based on keyword matches
            category_scores = []
            text_lower = text.lower()

            for category in categories:
                score = 0
                keyword_matches = []

                # Check keyword matches
                for keyword in category["keywords"]:
                    keyword_lower = keyword.strip().lower()
                    if keyword_lower in text_lower:
                        score += 1
                        keyword_matches.append(keyword_lower)

                # Additional scoring based on category names
                if (
                    category["name_en"].lower() in text_lower
                    or category["name_de"].lower() in text_lower
                ):
                    score += 2

                if score > 0:
                    confidence = min(score / max(len(category["keywords"]), 1), 1.0)
                    category_scores.append(
                        {
                            "category_id": category["id"],
                            "name_en": category["name_en"],
                            "name_de": category["name_de"],
                            "color": category["color"],
                            "icon": category["icon"],
                            "confidence": confidence,
                            "matched_keywords": keyword_matches,
                        }
                    )

            # Sort by score and return top suggestions
            category_scores.sort(key=lambda x: x["confidence"], reverse=True)
            return category_scores[:limit]

        except Exception as e:
            logger.error(f"Category suggestion failed: {e}")
            return []

    async def get_category_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get category usage statistics for user"""
        try:
            # Get category document counts
            category_stats = (
                self.db.query(
                    Category.id,
                    Category.name_en,
                    Category.name_de,
                    Category.color,
                    Category.icon,
                    func.count(Document.id).label("document_count"),
                )
                .outerjoin(
                    Document,
                    and_(
                        Document.category_id == Category.id,
                        Document.user_id == user_id,
                        Document.status == DocumentStatus.READY,
                    ),
                )
                .filter(
                    or_(
                        Category.is_system_category == True, Category.user_id == user_id
                    )
                )
                .group_by(Category.id)
                .all()
            )

            # Format results
            formatted_stats = []
            total_documents = 0

            for stat in category_stats:
                doc_count = stat.document_count
                total_documents += doc_count

                formatted_stats.append(
                    {
                        "category_id": stat.id,
                        "name_en": stat.name_en,
                        "name_de": stat.name_de,
                        "color": stat.color,
                        "icon": stat.icon,
                        "document_count": doc_count,
                    }
                )

            # Calculate percentages
            for stat in formatted_stats:
                if total_documents > 0:
                    stat["percentage"] = (
                        stat["document_count"] / total_documents
                    ) * 100
                else:
                    stat["percentage"] = 0

            # Sort by document count
            formatted_stats.sort(key=lambda x: x["document_count"], reverse=True)

            return {
                "categories": formatted_stats,
                "total_documents": total_documents,
                "total_categories": len(formatted_stats),
            }

        except Exception as e:
            logger.error(f"Get category statistics failed: {e}")
            return {"categories": [], "total_documents": 0, "total_categories": 0}

    async def mark_category_used(self, category_id: int) -> None:
        """Mark category as recently used"""
        try:
            category = (
                self.db.query(Category).filter(Category.id == category_id).first()
            )
            if category:
                category.last_used_at = datetime.utcnow()
                self.db.commit()
        except Exception as e:
            logger.error(f"Mark category used failed: {e}")

    async def search_categories(
        self,
        user_id: int,
        query: str,
        include_system: bool = True,
        include_user: bool = True,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """Search categories by name, description, or keywords"""
        try:
            if not query.strip():
                return await self.get_user_categories(
                    user_id, include_system, include_user, language
                )

            base_query = self.db.query(Category)

            # Apply user/system filters
            conditions = []
            if include_system:
                conditions.append(Category.is_system_category == True)
            if include_user:
                conditions.append(
                    and_(
                        Category.user_id == user_id,
                        Category.is_system_category == False,
                    )
                )

            if conditions:
                base_query = base_query.filter(or_(*conditions))

            # Search in names, descriptions, and keywords
            search_term = f"%{query.lower()}%"
            search_conditions = [
                Category.name_en.ilike(search_term),
                Category.name_de.ilike(search_term),
                Category.description_en.ilike(search_term),
                Category.description_de.ilike(search_term),
                Category.keywords.ilike(search_term),
            ]

            categories = base_query.filter(or_(*search_conditions)).all()

            # Format and score results
            formatted_categories = []
            for cat in categories:
                # Calculate relevance score
                score = 0
                query_lower = query.lower()

                if (
                    query_lower in cat.name_en.lower()
                    or query_lower in cat.name_de.lower()
                ):
                    score += 10
                if (
                    query_lower in (cat.description_en or "").lower()
                    or query_lower in (cat.description_de or "").lower()
                ):
                    score += 5
                if cat.keywords and query_lower in cat.keywords.lower():
                    score += 3

                formatted_categories.append(
                    {
                        "id": cat.id,
                        "name": cat.name_de if language == "de" else cat.name_en,
                        "name_en": cat.name_en,
                        "name_de": cat.name_de,
                        "description": (
                            cat.description_de
                            if language == "de"
                            else cat.description_en
                        ),
                        "color": cat.color,
                        "icon": cat.icon,
                        "keywords": cat.keywords.split(",") if cat.keywords else [],
                        "is_system_category": cat.is_system_category,
                        "relevance_score": score,
                    }
                )

            # Sort by relevance
            formatted_categories.sort(key=lambda x: x["relevance_score"], reverse=True)

            return formatted_categories

        except Exception as e:
            logger.error(f"Search categories failed: {e}")
            return []
