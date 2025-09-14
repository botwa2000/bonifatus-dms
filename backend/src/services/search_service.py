# backend/src/services/search_service.py
"""
Bonifatus DMS - Search Service
Advanced document search with full-text search, filtering, and ranking
PostgreSQL full-text search integration with intelligent suggestions
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func, desc
from typing import List, Dict, Any, Optional
import re
import time
import logging
from datetime import datetime, timedelta

from src.database.models import Document, Category, User
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    """Service for document search and discovery operations"""

    def __init__(self, db: Session):
        self.db = db

    async def search_documents(
        self, user_id: int, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform basic document search with optional filters
        """
        try:
            start_time = time.time()

            # Build base query
            base_query = self.db.query(Document).filter(Document.user_id == user_id)

            # Apply search query
            if query and query.strip():
                search_conditions = self._build_search_conditions(query.strip())
                base_query = base_query.filter(search_conditions)

            # Apply additional filters
            if filters:
                base_query = self._apply_filters(base_query, filters)

            # Apply sorting
            sort_by = filters.get("sort_by", "relevance") if filters else "relevance"
            sort_order = filters.get("sort_order", "desc") if filters else "desc"
            base_query = self._apply_sorting(base_query, sort_by, sort_order, query)

            # Get total count
            total_count = base_query.count()

            # Apply pagination
            page = filters.get("page", 1) if filters else 1
            per_page = filters.get("per_page", 20) if filters else 20
            offset = (page - 1) * per_page

            documents = base_query.offset(offset).limit(per_page).all()

            # Calculate search time
            search_time_ms = int((time.time() - start_time) * 1000)

            # Format results
            formatted_documents = await self._format_search_results(documents, query)

            return {
                "documents": formatted_documents,
                "total": total_count,
                "search_time_ms": search_time_ms,
                "query": query,
            }

        except Exception as e:
            logger.error(f"Document search failed for user {user_id}: {e}")
            return {"documents": [], "total": 0, "search_time_ms": 0, "query": query}

    async def advanced_search(
        self, query: str, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform advanced search with complex filters and ranking
        """
        try:
            start_time = time.time()
            user_id = filters["user_id"]

            # Build complex search query
            base_query = self.db.query(Document).filter(Document.user_id == user_id)

            # Parse and apply search query
            if query and query.strip():
                parsed_query = self._parse_advanced_query(query.strip())
                search_conditions = self._build_advanced_search_conditions(parsed_query)
                base_query = base_query.filter(search_conditions)

            # Apply advanced filters
            base_query = self._apply_advanced_filters(base_query, filters)

            # Apply relevance ranking
            base_query = self._apply_relevance_ranking(base_query, query)

            # Get total count
            total_count = base_query.count()

            # Apply pagination
            page = filters.get("page", 1)
            per_page = filters.get("per_page", 20)
            offset = (page - 1) * per_page

            documents = base_query.offset(offset).limit(per_page).all()

            # Calculate search time
            search_time_ms = int((time.time() - start_time) * 1000)

            # Format results with highlighting
            formatted_documents = await self._format_search_results(
                documents, query, highlight=True
            )

            # Generate search suggestions
            suggestions = await self._generate_search_suggestions(user_id, query)

            return {
                "documents": formatted_documents,
                "total": total_count,
                "search_time_ms": search_time_ms,
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error(f"Advanced search failed: {e}")
            return {"documents": [], "total": 0, "search_time_ms": 0, "suggestions": []}

    async def get_search_suggestions(
        self, user_id: int, query: str, limit: int = 5
    ) -> List[str]:
        """
        Get search query suggestions based on user's documents
        """
        try:
            if not query or len(query.strip()) < 2:
                return []

            query_lower = query.lower().strip()
            suggestions = []

            # Get suggestions from document titles
            title_matches = (
                self.db.query(Document.title)
                .filter(
                    and_(
                        Document.user_id == user_id,
                        Document.title.ilike(f"%{query_lower}%"),
                        Document.title.isnot(None),
                    )
                )
                .distinct()
                .limit(limit)
                .all()
            )

            suggestions.extend([match.title for match in title_matches if match.title])

            # Get suggestions from extracted keywords
            keyword_matches = self.db.execute(
                text(
                    """
                    SELECT DISTINCT unnest(extracted_keywords) as keyword
                    FROM documents 
                    WHERE user_id = :user_id 
                    AND extracted_keywords IS NOT NULL
                    AND LOWER(unnest(extracted_keywords)) LIKE LOWER(:query)
                    LIMIT :limit
                """
                ),
                {"user_id": user_id, "query": f"%{query_lower}%", "limit": limit},
            ).fetchall()

            suggestions.extend([match.keyword for match in keyword_matches])

            # Get suggestions from category names
            category_matches = (
                self.db.query(Category)
                .filter(
                    and_(
                        or_(
                            Category.user_id == user_id,
                            Category.is_system_category == True,
                        ),
                        or_(
                            Category.name_en.ilike(f"%{query_lower}%"),
                            Category.name_de.ilike(f"%{query_lower}%"),
                        ),
                    )
                )
                .limit(limit)
                .all()
            )

            for category in category_matches:
                if query_lower in category.name_en.lower():
                    suggestions.append(category.name_en)
                if query_lower in category.name_de.lower():
                    suggestions.append(category.name_de)

            # Remove duplicates and limit results
            unique_suggestions = list(dict.fromkeys(suggestions))[:limit]

            return unique_suggestions

        except Exception as e:
            logger.error(f"Search suggestions failed for user {user_id}: {e}")
            return []

    async def get_popular_searches(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get popular search queries for user (requires search history tracking)
        """
        try:
            # Note: This would require a search_history table in production
            # For now, return suggestions based on document content

            # Get most common keywords from user's documents
            common_keywords = self.db.execute(
                text(
                    """
                    SELECT keyword, COUNT(*) as frequency
                    FROM (
                        SELECT unnest(extracted_keywords) as keyword
                        FROM documents 
                        WHERE user_id = :user_id 
                        AND extracted_keywords IS NOT NULL
                    ) keywords
                    GROUP BY keyword
                    ORDER BY frequency DESC
                    LIMIT :limit
                """
                ),
                {"user_id": user_id, "limit": limit},
            ).fetchall()

            popular_searches = [
                {
                    "query": keyword.keyword,
                    "frequency": keyword.frequency,
                    "type": "keyword",
                }
                for keyword in common_keywords
            ]

            return popular_searches

        except Exception as e:
            logger.error(f"Popular searches failed for user {user_id}: {e}")
            return []

    def _build_search_conditions(self, query: str):
        """
        Build SQL search conditions for basic search
        """
        # Clean query
        clean_query = re.sub(r"[^\w\s]", " ", query)
        search_terms = clean_query.split()

        conditions = []

        for term in search_terms:
            if len(term) >= 2:
                # Search in multiple fields
                term_conditions = or_(
                    Document.filename.ilike(f"%{term}%"),
                    Document.title.ilike(f"%{term}%"),
                    Document.description.ilike(f"%{term}%"),
                    Document.extracted_text.ilike(f"%{term}%"),
                    text(
                        "EXISTS (SELECT 1 FROM unnest(extracted_keywords) AS keyword WHERE keyword ILIKE :term)"
                    ).params(term=f"%{term}%"),
                    text(
                        "EXISTS (SELECT 1 FROM unnest(user_keywords) AS keyword WHERE keyword ILIKE :term)"
                    ).params(term=f"%{term}%"),
                )
                conditions.append(term_conditions)

        if conditions:
            return and_(*conditions)

        return text("1=1")  # Return all if no valid search terms

    def _parse_advanced_query(self, query: str) -> Dict[str, Any]:
        """
        Parse advanced search query with operators
        """
        parsed = {
            "must_have": [],
            "should_have": [],
            "must_not_have": [],
            "phrase_searches": [],
            "field_searches": {},
        }

        # Extract quoted phrases
        phrase_pattern = r'"([^"]*)"'
        phrases = re.findall(phrase_pattern, query)
        parsed["phrase_searches"] = phrases

        # Remove phrases from query for further processing
        query_without_phrases = re.sub(phrase_pattern, "", query)

        # Extract field searches (e.g., title:invoice, category:finance)
        field_pattern = r"(\w+):(\w+)"
        field_matches = re.findall(field_pattern, query_without_phrases)
        for field, value in field_matches:
            parsed["field_searches"][field] = value

        # Remove field searches from query
        query_without_fields = re.sub(field_pattern, "", query_without_phrases)

        # Process remaining terms
        terms = query_without_fields.split()
        for term in terms:
            term = term.strip()
            if term.startswith("+"):
                # Must have
                parsed["must_have"].append(term[1:])
            elif term.startswith("-"):
                # Must not have
                parsed["must_not_have"].append(term[1:])
            elif term:
                # Should have
                parsed["should_have"].append(term)

        return parsed

    def _build_advanced_search_conditions(self, parsed_query: Dict[str, Any]):
        """
        Build advanced search conditions from parsed query
        """
        conditions = []

        # Must have terms
        for term in parsed_query["must_have"]:
            conditions.append(
                or_(
                    Document.extracted_text.ilike(f"%{term}%"),
                    Document.title.ilike(f"%{term}%"),
                    Document.filename.ilike(f"%{term}%"),
                )
            )

        # Must not have terms
        for term in parsed_query["must_not_have"]:
            conditions.append(
                and_(
                    ~Document.extracted_text.ilike(f"%{term}%"),
                    ~Document.title.ilike(f"%{term}%"),
                    ~Document.filename.ilike(f"%{term}%"),
                )
            )

        # Phrase searches
        for phrase in parsed_query["phrase_searches"]:
            conditions.append(
                or_(
                    Document.extracted_text.ilike(f"%{phrase}%"),
                    Document.title.ilike(f"%{phrase}%"),
                )
            )

        # Field searches
        for field, value in parsed_query["field_searches"].items():
            if field == "title":
                conditions.append(Document.title.ilike(f"%{value}%"))
            elif field == "filename":
                conditions.append(Document.filename.ilike(f"%{value}%"))
            elif field == "category":
                # Join with categories table
                conditions.append(
                    text(
                        """EXISTS (
                        SELECT 1 FROM categories c 
                        WHERE c.id = documents.category_id 
                        AND (LOWER(c.name_en) LIKE LOWER(:value) OR LOWER(c.name_de) LIKE LOWER(:value))
                    )"""
                    ).params(value=f"%{value}%")
                )

        # Should have terms (at least one)
        if parsed_query["should_have"]:
            should_conditions = []
            for term in parsed_query["should_have"]:
                should_conditions.append(
                    or_(
                        Document.extracted_text.ilike(f"%{term}%"),
                        Document.title.ilike(f"%{term}%"),
                        Document.filename.ilike(f"%{term}%"),
                    )
                )
            if should_conditions:
                conditions.append(or_(*should_conditions))

        return and_(*conditions) if conditions else text("1=1")

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """
        Apply basic filters to search query
        """
        if filters.get("category_id"):
            query = query.filter(Document.category_id == filters["category_id"])

        if filters.get("status"):
            query = query.filter(Document.status == filters["status"])

        return query

    def _apply_advanced_filters(self, query, filters: Dict[str, Any]):
        """
        Apply advanced filters to search query
        """
        # Category filters
        if filters.get("category_ids"):
            query = query.filter(Document.category_id.in_(filters["category_ids"]))

        # File type filters
        if filters.get("file_types"):
            extensions = [
                f".{ft}" if not ft.startswith(".") else ft
                for ft in filters["file_types"]
            ]
            query = query.filter(Document.file_extension.in_(extensions))

        # Date range filters
        if filters.get("date_from"):
            try:
                date_from = datetime.fromisoformat(filters["date_from"])
                query = query.filter(Document.created_at >= date_from)
            except ValueError:
                logger.warning(f"Invalid date_from format: {filters['date_from']}")

        if filters.get("date_to"):
            try:
                date_to = datetime.fromisoformat(filters["date_to"])
                query = query.filter(Document.created_at <= date_to)
            except ValueError:
                logger.warning(f"Invalid date_to format: {filters['date_to']}")

        # File size filters
        if filters.get("min_size_bytes"):
            query = query.filter(Document.file_size_bytes >= filters["min_size_bytes"])

        if filters.get("max_size_bytes"):
            query = query.filter(Document.file_size_bytes <= filters["max_size_bytes"])

        # Favorite filter
        if filters.get("favorites_only"):
            query = query.filter(Document.is_favorite == True)

        return query

    def _apply_sorting(self, query, sort_by: str, sort_order: str, search_query: str):
        """
        Apply sorting to search results
        """
        if sort_by == "relevance" and search_query:
            # For relevance, we'll use a simple ranking based on title matches
            # In production, use full-text search ranking
            query = query.order_by(
                desc(
                    func.case(
                        [
                            (Document.title.ilike(f"%{search_query}%"), 3),
                            (Document.filename.ilike(f"%{search_query}%"), 2),
                        ],
                        else_=1,
                    )
                ),
                desc(Document.view_count),
                desc(Document.created_at),
            )
        else:
            # Standard sorting
            sort_column = getattr(Document, sort_by, Document.created_at)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)

        return query

    def _apply_relevance_ranking(self, query, search_query: str):
        """
        Apply relevance ranking to search results
        """
        if not search_query:
            return query.order_by(desc(Document.created_at))

        # Simple relevance ranking - in production use PostgreSQL full-text search
        return query.order_by(
            desc(
                func.case(
                    [
                        (Document.title.ilike(f"%{search_query}%"), 5),
                        (Document.filename.ilike(f"%{search_query}%"), 4),
                        (Document.description.ilike(f"%{search_query}%"), 3),
                        (Document.extracted_text.ilike(f"%{search_query}%"), 2),
                    ],
                    else_=1,
                )
            ),
            desc(Document.view_count),
            desc(Document.updated_at),
        )

    async def _format_search_results(
        self, documents: List[Document], query: str, highlight: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Format search results with optional highlighting
        """
        formatted_results = []

        for document in documents:
            result = {
                "id": document.id,
                "filename": document.filename,
                "original_filename": document.original_filename,
                "title": document.title,
                "description": document.description,
                "file_size_bytes": document.file_size_bytes,
                "mime_type": document.mime_type,
                "status": document.status.value,
                "category": (
                    {
                        "id": document.category.id,
                        "name_en": document.category.name_en,
                        "name_de": document.category.name_de,
                        "color": document.category.color,
                    }
                    if document.category
                    else None
                ),
                "extracted_keywords": document.extracted_keywords,
                "language_detected": document.language_detected,
                "is_favorite": document.is_favorite,
                "view_count": document.view_count,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
            }

            # Add highlighting if requested
            if highlight and query:
                result["highlighted_title"] = self._highlight_text(
                    document.title or "", query
                )
                result["highlighted_description"] = self._highlight_text(
                    document.description or "", query
                )

                # Add text excerpt with highlighting
                if document.extracted_text:
                    excerpt = self._generate_excerpt(document.extracted_text, query)
                    result["excerpt"] = self._highlight_text(excerpt, query)

            formatted_results.append(result)

        return formatted_results

    def _highlight_text(self, text: str, query: str, max_length: int = 200) -> str:
        """
        Highlight search terms in text
        """
        if not text or not query:
            return text[:max_length] + ("..." if len(text) > max_length else "")

        # Simple highlighting - wrap matches in <mark> tags
        highlighted = text
        query_terms = query.split()

        for term in query_terms:
            if len(term) >= 2:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                highlighted = pattern.sub(f"<mark>{term}</mark>", highlighted)

        if len(highlighted) > max_length:
            highlighted = highlighted[:max_length] + "..."

        return highlighted

    def _generate_excerpt(self, text: str, query: str, max_length: int = 300) -> str:
        """
        Generate text excerpt around search terms
        """
        if not text or not query:
            return text[:max_length] + ("..." if len(text) > max_length else "")

        query_terms = query.split()
        text_lower = text.lower()

        # Find first occurrence of any search term
        best_position = len(text)
        for term in query_terms:
            if len(term) >= 2:
                position = text_lower.find(term.lower())
                if position != -1 and position < best_position:
                    best_position = position

        if best_position == len(text):
            # No terms found, return beginning
            return text[:max_length] + ("..." if len(text) > max_length else "")

        # Extract excerpt around the found term
        start = max(0, best_position - max_length // 3)
        end = min(len(text), start + max_length)

        excerpt = text[start:end]

        # Add ellipsis if needed
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."

        return excerpt

    async def _generate_search_suggestions(self, user_id: int, query: str) -> List[str]:
        """
        Generate intelligent search suggestions
        """
        try:
            suggestions = await self.get_search_suggestions(user_id, query, limit=5)
            return suggestions
        except Exception as e:
            logger.error(f"Search suggestions generation failed: {e}")
            return []
