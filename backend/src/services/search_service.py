# backend/src/services/search_service.py

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func, desc, asc, case
from typing import List, Dict, Any, Optional, Tuple
import re
import time
import logging
from datetime import datetime, timedelta
import json

from src.database.models import Document, Category, User, SearchHistory
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    """Advanced search service with full-text search, filtering, and ranking"""

    def __init__(self, db: Session):
        self.db = db

    def search_documents(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform basic document search with optional filters"""
        start_time = time.time()

        try:
            query = self.db.query(Document).filter(
                Document.user_id == search_params["user_id"]
            )

            search_query = search_params.get("query", "").strip()

            if search_query:
                search_filter = or_(
                    Document.title.ilike(f"%{search_query}%"),
                    Document.filename.ilike(f"%{search_query}%"),
                    Document.extracted_text.ilike(f"%{search_query}%"),
                    Document.description.ilike(f"%{search_query}%"),
                    func.array_to_string(Document.extracted_keywords, " ").ilike(
                        f"%{search_query}%"
                    ),
                    func.array_to_string(Document.user_keywords, " ").ilike(
                        f"%{search_query}%"
                    ),
                )
                query = query.filter(search_filter)

            if search_params.get("category_id"):
                query = query.filter(
                    Document.category_id == search_params["category_id"]
                )

            if search_params.get("status"):
                query = query.filter(Document.status == search_params["status"])

            if search_params.get("language"):
                query = query.filter(
                    Document.language_detected == search_params["language"]
                )

            sort_by = search_params.get("sort_by", "relevance")
            sort_order = search_params.get("sort_order", "desc")

            if sort_by == "relevance" and search_query:
                query = query.order_by(desc(Document.updated_at))
            else:
                sort_column = getattr(Document, sort_by, Document.created_at)
                if sort_order == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))

            total = query.count()

            page = search_params.get("page", 1)
            per_page = search_params.get("per_page", 20)
            offset = (page - 1) * per_page

            documents = query.offset(offset).limit(per_page).all()

            formatted_documents = []
            for doc in documents:
                document_data = {
                    "id": doc.id,
                    "filename": doc.filename,
                    "title": doc.title,
                    "description": doc.description,
                    "file_size_bytes": doc.file_size_bytes,
                    "mime_type": doc.mime_type,
                    "status": doc.status.value,
                    "category": (
                        {
                            "id": doc.category.id,
                            "name_en": doc.category.name_en,
                            "name_de": doc.category.name_de,
                            "color": doc.category.color,
                        }
                        if doc.category
                        else None
                    ),
                    "extracted_keywords": doc.extracted_keywords,
                    "is_favorite": doc.is_favorite,
                    "view_count": doc.view_count,
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat(),
                }

                if search_query and doc.title:
                    highlighted_title = self._highlight_text(doc.title, search_query)
                    document_data["highlighted_title"] = highlighted_title

                formatted_documents.append(document_data)

            search_time_ms = int((time.time() - start_time) * 1000)

            if search_query:
                self._save_search_history(
                    search_params["user_id"], search_query, "documents", total
                )

            return {
                "documents": formatted_documents,
                "total": total,
                "search_time_ms": search_time_ms,
            }

        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return {"documents": [], "total": 0, "search_time_ms": 0}

    def advanced_search(self, query: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform advanced search with complex filters and ranking"""
        try:
            start_time = time.time()
            user_id = filters["user_id"]

            base_query = self.db.query(Document).filter(Document.user_id == user_id)

            if query and query.strip():
                parsed_query = self._parse_advanced_query(query.strip())
                search_conditions = self._build_advanced_search_conditions(parsed_query)
                base_query = base_query.filter(search_conditions)

            base_query = self._apply_advanced_filters(base_query, filters)
            base_query = self._apply_relevance_ranking(base_query, query)

            total_count = base_query.count()

            page = filters.get("page", 1)
            per_page = filters.get("per_page", 20)
            offset = (page - 1) * per_page

            documents = base_query.offset(offset).limit(per_page).all()

            search_time_ms = int((time.time() - start_time) * 1000)

            formatted_documents = self._format_search_results(
                documents, query, highlight=True
            )

            suggestions = self._generate_search_suggestions(user_id, query)

            return {
                "documents": formatted_documents,
                "total": total_count,
                "search_time_ms": search_time_ms,
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error(f"Advanced search failed: {e}")
            return {"documents": [], "total": 0, "search_time_ms": 0, "suggestions": []}

    def search_categories(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search available categories"""
        start_time = time.time()

        try:
            query = self.db.query(Category).filter(
                or_(
                    Category.user_id == search_params["user_id"],
                    Category.user_id.is_(None),
                )
            )

            search_query = search_params.get("query", "").strip()
            language = search_params.get("language", "en")

            if search_query:
                if language == "en":
                    search_filter = or_(
                        Category.name_en.ilike(f"%{search_query}%"),
                        Category.description_en.ilike(f"%{search_query}%"),
                        func.array_to_string(Category.keywords, " ").ilike(
                            f"%{search_query}%"
                        ),
                    )
                else:
                    search_filter = or_(
                        Category.name_de.ilike(f"%{search_query}%"),
                        Category.description_de.ilike(f"%{search_query}%"),
                        func.array_to_string(Category.keywords, " ").ilike(
                            f"%{search_query}%"
                        ),
                    )
                query = query.filter(search_filter)

            query = query.order_by(Category.name_en)

            limit = search_params.get("limit", 10)
            categories = query.limit(limit).all()

            formatted_categories = []
            for category in categories:
                document_count = self._get_category_document_count(
                    category.id, search_params["user_id"]
                )

                category_data = {
                    "id": category.id,
                    "name": category.name_en if language == "en" else category.name_de,
                    "name_en": category.name_en,
                    "name_de": category.name_de,
                    "description": (
                        category.description_en
                        if language == "en"
                        else category.description_de
                    ),
                    "color": category.color,
                    "icon": category.icon,
                    "keywords": category.keywords,
                    "is_system": category.user_id is None,
                    "document_count": document_count,
                }

                formatted_categories.append(category_data)

            search_time_ms = int((time.time() - start_time) * 1000)

            if search_query:
                self._save_search_history(
                    search_params["user_id"],
                    search_query,
                    "categories",
                    len(categories),
                )

            return {
                "categories": formatted_categories,
                "total": len(categories),
                "search_time_ms": search_time_ms,
            }

        except Exception as e:
            logger.error(f"Category search failed: {e}")
            return {"categories": [], "total": 0, "search_time_ms": 0}

    def global_search(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search across multiple entity types"""
        start_time = time.time()

        try:
            results = {}
            entities = search_params.get("entities", ["documents", "categories"])
            limit_per_entity = search_params.get("limit_per_entity", 5)

            if "documents" in entities:
                doc_search_params = {
                    "user_id": search_params["user_id"],
                    "query": search_params["query"],
                    "page": 1,
                    "per_page": limit_per_entity,
                }
                doc_results = self.search_documents(doc_search_params)
                results["documents"] = {
                    "results": doc_results["documents"],
                    "total": doc_results["total"],
                }

            if "categories" in entities:
                cat_search_params = {
                    "user_id": search_params["user_id"],
                    "query": search_params["query"],
                    "limit": limit_per_entity,
                }
                cat_results = self.search_categories(cat_search_params)
                results["categories"] = {
                    "results": cat_results["categories"],
                    "total": cat_results["total"],
                }

            search_time_ms = int((time.time() - start_time) * 1000)

            self._save_search_history(
                search_params["user_id"],
                search_params["query"],
                "global",
                sum(
                    entity_results.get("total", 0)
                    for entity_results in results.values()
                ),
            )

            return {
                "results": results,
                "search_time_ms": search_time_ms,
            }

        except Exception as e:
            logger.error(f"Global search failed: {e}")
            return {"results": {}, "search_time_ms": 0}

    def semantic_search(
        self, user_id: int, query: str, limit: int = 20
    ) -> Dict[str, Any]:
        """Perform semantic search using keyword similarity"""
        try:
            start_time = time.time()

            # Extract keywords from query
            query_keywords = self._extract_keywords_from_text(query.lower())

            if not query_keywords:
                return {"documents": [], "total": 0, "search_time_ms": 0}

            # Find documents with similar keywords
            base_query = self.db.query(Document).filter(Document.user_id == user_id)

            # Build semantic search conditions
            semantic_conditions = []
            for keyword in query_keywords:
                condition = or_(
                    func.array_to_string(Document.extracted_keywords, " ").ilike(
                        f"%{keyword}%"
                    ),
                    func.array_to_string(Document.user_keywords, " ").ilike(
                        f"%{keyword}%"
                    ),
                    Document.extracted_text.ilike(f"%{keyword}%"),
                    Document.title.ilike(f"%{keyword}%"),
                )
                semantic_conditions.append(condition)

            if semantic_conditions:
                base_query = base_query.filter(or_(*semantic_conditions))

            # Calculate relevance scores
            relevance_score = case(
                [
                    (Document.title.ilike(f"%{query}%"), 10),
                    (Document.filename.ilike(f"%{query}%"), 8),
                    (Document.description.ilike(f"%{query}%"), 6),
                    (Document.extracted_text.ilike(f"%{query}%"), 4),
                ],
                else_=2,
            )

            # Order by relevance
            base_query = base_query.order_by(
                desc(relevance_score), desc(Document.view_count)
            )

            documents = base_query.limit(limit).all()

            formatted_documents = self._format_search_results(
                documents, query, highlight=True
            )

            search_time_ms = int((time.time() - start_time) * 1000)

            return {
                "documents": formatted_documents,
                "total": len(documents),
                "search_time_ms": search_time_ms,
                "search_type": "semantic",
            }

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return {"documents": [], "total": 0, "search_time_ms": 0}

    def full_text_search(
        self, user_id: int, query: str, filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """PostgreSQL full-text search implementation"""
        try:
            start_time = time.time()

            # Use PostgreSQL full-text search capabilities
            search_vector = func.to_tsvector(
                "english",
                func.coalesce(Document.title, "")
                + " "
                + func.coalesce(Document.filename, "")
                + " "
                + func.coalesce(Document.extracted_text, "")
                + " "
                + func.coalesce(Document.description, ""),
            )

            search_query_ts = func.plainto_tsquery("english", query)

            base_query = (
                self.db.query(
                    Document, func.ts_rank(search_vector, search_query_ts).label("rank")
                )
                .filter(
                    Document.user_id == user_id, search_vector.op("@@")(search_query_ts)
                )
                .order_by(desc("rank"))
            )

            if filters:
                base_query = self._apply_advanced_filters(base_query, filters)

            total_count = base_query.count()

            page = filters.get("page", 1) if filters else 1
            per_page = filters.get("per_page", 20) if filters else 20
            offset = (page - 1) * per_page

            results = base_query.offset(offset).limit(per_page).all()

            formatted_documents = []
            for doc, rank in results:
                document_data = self._format_document_result(doc, query)
                document_data["relevance_score"] = float(rank) if rank else 0.0
                formatted_documents.append(document_data)

            search_time_ms = int((time.time() - start_time) * 1000)

            return {
                "documents": formatted_documents,
                "total": total_count,
                "search_time_ms": search_time_ms,
                "search_type": "full_text",
            }

        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            return {"documents": [], "total": 0, "search_time_ms": 0}

    def get_search_suggestions(
        self, user_id: int, query: str, entity: str = "documents", limit: int = 5
    ) -> List[str]:
        """Get search suggestions for auto-completion"""
        try:
            suggestions = []

            if entity in ["documents", "all"]:
                doc_suggestions = (
                    self.db.query(Document.title)
                    .filter(
                        Document.user_id == user_id,
                        Document.title.ilike(f"%{query}%"),
                        Document.title.isnot(None),
                    )
                    .distinct()
                    .limit(limit)
                    .all()
                )
                suggestions.extend([s[0] for s in doc_suggestions if s[0]])

            if entity in ["categories", "all"] and len(suggestions) < limit:
                remaining_limit = limit - len(suggestions)
                cat_suggestions = (
                    self.db.query(Category.name_en)
                    .filter(
                        or_(Category.user_id == user_id, Category.user_id.is_(None)),
                        Category.name_en.ilike(f"%{query}%"),
                    )
                    .distinct()
                    .limit(remaining_limit)
                    .all()
                )
                suggestions.extend([s[0] for s in cat_suggestions])

            return list(set(suggestions))[:limit]

        except Exception as e:
            logger.error(f"Get search suggestions failed: {e}")
            return []

    def get_search_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's search history"""
        try:
            history = (
                self.db.query(SearchHistory)
                .filter(SearchHistory.user_id == user_id)
                .order_by(desc(SearchHistory.created_at))
                .limit(limit)
                .all()
            )

            formatted_history = []
            for entry in history:
                formatted_history.append(
                    {
                        "id": entry.id,
                        "query": entry.query,
                        "entity_type": entry.entity_type,
                        "results_count": entry.results_count,
                        "created_at": entry.created_at.isoformat(),
                    }
                )

            return formatted_history

        except Exception as e:
            logger.error(f"Get search history failed: {e}")
            return []

    def get_popular_searches(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get popular search terms for user"""
        try:
            popular_queries = (
                self.db.query(
                    SearchHistory.query,
                    func.count(SearchHistory.query).label("frequency"),
                )
                .filter(SearchHistory.user_id == user_id)
                .group_by(SearchHistory.query)
                .order_by(desc("frequency"))
                .limit(limit)
                .all()
            )

            popular_searches = []
            for query, frequency in popular_queries:
                popular_searches.append(
                    {
                        "query": query,
                        "frequency": frequency,
                        "type": "query",
                    }
                )

            keywords_query = (
                self.db.query(
                    func.unnest(Document.extracted_keywords).label("keyword"),
                    func.count().label("frequency"),
                )
                .filter(Document.user_id == user_id)
                .group_by("keyword")
                .order_by(desc("frequency"))
                .limit(limit)
                .all()
            )

            for keyword, frequency in keywords_query:
                if len(popular_searches) < limit:
                    popular_searches.append(
                        {
                            "query": keyword,
                            "frequency": frequency,
                            "type": "keyword",
                        }
                    )

            return popular_searches

        except Exception as e:
            logger.error(f"Popular searches failed: {e}")
            return []

    def get_search_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get search analytics for user"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Total searches
            total_searches = (
                self.db.query(SearchHistory)
                .filter(
                    SearchHistory.user_id == user_id,
                    SearchHistory.created_at >= start_date,
                )
                .count()
            )

            # Top search terms
            top_searches = (
                self.db.query(
                    SearchHistory.query, func.count(SearchHistory.query).label("count")
                )
                .filter(
                    SearchHistory.user_id == user_id,
                    SearchHistory.created_at >= start_date,
                )
                .group_by(SearchHistory.query)
                .order_by(desc("count"))
                .limit(10)
                .all()
            )

            # Search trends by day
            daily_searches = (
                self.db.query(
                    func.date(SearchHistory.created_at).label("date"),
                    func.count().label("searches"),
                )
                .filter(
                    SearchHistory.user_id == user_id,
                    SearchHistory.created_at >= start_date,
                )
                .group_by(func.date(SearchHistory.created_at))
                .order_by("date")
                .all()
            )

            return {
                "total_searches": total_searches,
                "top_searches": [{"query": q, "count": c} for q, c in top_searches],
                "daily_trends": [
                    {"date": d.isoformat(), "searches": s} for d, s in daily_searches
                ],
                "period_days": days,
                "start_date": start_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Search analytics failed: {e}")
            return {"total_searches": 0, "top_searches": [], "daily_trends": []}

    def save_search_query(
        self, user_id: int, query: str, entity_type: str, results_count: int
    ):
        """Save search query for analytics"""
        self._save_search_history(user_id, query, entity_type, results_count)

    def clear_search_history(self, user_id: int) -> bool:
        """Clear user's search history"""
        try:
            self.db.query(SearchHistory).filter(
                SearchHistory.user_id == user_id
            ).delete()
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Clear search history failed: {e}")
            self.db.rollback()
            return False

    # Private helper methods

    def _parse_advanced_query(self, query: str) -> Dict[str, Any]:
        """Parse advanced search query with operators"""
        parsed = {
            "required_terms": [],
            "excluded_terms": [],
            "phrases": [],
            "field_searches": {},
            "should_have": [],
        }

        phrases = re.findall(r'"([^"]*)"', query)
        parsed["phrases"] = phrases

        query_without_quotes = re.sub(r'"[^"]*"', "", query)

        terms = query_without_quotes.split()
        for term in terms:
            if term.startswith("-"):
                parsed["excluded_terms"].append(term[1:])
            elif term.startswith("+"):
                parsed["required_terms"].append(term[1:])
            elif ":" in term:
                field, value = term.split(":", 1)
                parsed["field_searches"][field] = value
            else:
                parsed["should_have"].append(term)

        return parsed

    def _build_advanced_search_conditions(self, parsed_query: Dict[str, Any]):
        """Build advanced search conditions"""
        conditions = []

        for term in parsed_query["required_terms"]:
            term_conditions = or_(
                Document.title.ilike(f"%{term}%"),
                Document.filename.ilike(f"%{term}%"),
                Document.extracted_text.ilike(f"%{term}%"),
                Document.description.ilike(f"%{term}%"),
            )
            conditions.append(term_conditions)

        for phrase in parsed_query["phrases"]:
            phrase_conditions = or_(
                Document.title.ilike(f"%{phrase}%"),
                Document.extracted_text.ilike(f"%{phrase}%"),
                Document.description.ilike(f"%{phrase}%"),
            )
            conditions.append(phrase_conditions)

        for term in parsed_query["excluded_terms"]:
            exclude_conditions = and_(
                ~Document.title.ilike(f"%{term}%"),
                ~Document.filename.ilike(f"%{term}%"),
                ~Document.extracted_text.ilike(f"%{term}%"),
                ~Document.description.ilike(f"%{term}%"),
            )
            conditions.append(exclude_conditions)

        for field, value in parsed_query["field_searches"].items():
            if field == "title":
                conditions.append(Document.title.ilike(f"%{value}%"))
            elif field == "filename":
                conditions.append(Document.filename.ilike(f"%{value}%"))
            elif field == "type":
                conditions.append(Document.mime_type.ilike(f"%{value}%"))

        if parsed_query["should_have"]:
            should_conditions = []
            for term in parsed_query["should_have"]:
                should_conditions.append(
                    or_(
                        Document.title.ilike(f"%{term}%"),
                        Document.filename.ilike(f"%{term}%"),
                        Document.extracted_text.ilike(f"%{term}%"),
                        Document.description.ilike(f"%{term}%"),
                    )
                )
            if should_conditions:
                conditions.append(or_(*should_conditions))

        return and_(*conditions) if conditions else text("1=1")

    def _apply_advanced_filters(self, query, filters: Dict[str, Any]):
        """Apply advanced filters to query"""
        if filters.get("category_id"):
            query = query.filter(Document.category_id == filters["category_id"])

        if filters.get("mime_types"):
            mime_conditions = or_(
                *[
                    Document.mime_type.ilike(f"{mime}%")
                    for mime in filters["mime_types"]
                ]
            )
            query = query.filter(mime_conditions)

        if filters.get("date_from"):
            query = query.filter(Document.created_at >= filters["date_from"])

        if filters.get("date_to"):
            query = query.filter(Document.created_at <= filters["date_to"])

        if filters.get("file_size_min"):
            query = query.filter(Document.file_size_bytes >= filters["file_size_min"])

        if filters.get("file_size_max"):
            query = query.filter(Document.file_size_bytes <= filters["file_size_max"])

        if filters.get("language"):
            query = query.filter(Document.language_detected == filters["language"])

        if filters.get("is_favorite"):
            query = query.filter(Document.is_favorite == filters["is_favorite"])

        return query

    def _apply_relevance_ranking(self, query, search_query: str):
        """Apply relevance ranking to search results"""
        if not search_query:
            return query.order_by(desc(Document.updated_at))

        rank_expressions = []

        terms = search_query.lower().split()
        for term in terms:
            title_rank = case([(Document.title.ilike(f"%{term}%"), 3)], else_=0)
            filename_rank = case([(Document.filename.ilike(f"%{term}%"), 2)], else_=0)
            content_rank = case(
                [(Document.extracted_text.ilike(f"%{term}%"), 1)], else_=0
            )

            rank_expressions.extend([title_rank, filename_rank, content_rank])

        total_rank = sum(rank_expressions) if rank_expressions else 0
        return query.order_by(desc(total_rank), desc(Document.updated_at))

    def _format_search_results(
        self, documents: List[Document], query: str, highlight: bool = False
    ) -> List[Dict[str, Any]]:
        """Format search results with optional highlighting"""
        formatted_documents = []

        for doc in documents:
            document_data = {
                "id": doc.id,
                "filename": doc.filename,
                "title": doc.title,
                "description": doc.description,
                "file_size_bytes": doc.file_size_bytes,
                "mime_type": doc.mime_type,
                "status": doc.status.value,
                "category": (
                    {
                        "id": doc.category.id,
                        "name_en": doc.category.name_en,
                        "name_de": doc.category.name_de,
                        "color": doc.category.color,
                    }
                    if doc.category
                    else None
                ),
                "extracted_keywords": doc.extracted_keywords,
                "is_favorite": doc.is_favorite,
                "view_count": doc.view_count,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
                "score": getattr(doc, "relevance_score", 0.0),
            }

            if highlight and query:
                if doc.title:
                    document_data["highlighted_title"] = self._highlight_text(
                        doc.title, query
                    )
                if doc.description:
                    document_data["highlighted_description"] = self._highlight_text(
                        doc.description, query
                    )

            formatted_documents.append(document_data)

        return formatted_documents

    def _format_document_result(self, doc: Document, query: str) -> Dict[str, Any]:
        """Format single document result"""
        return {
            "id": doc.id,
            "filename": doc.filename,
            "title": doc.title,
            "description": doc.description,
            "file_size_bytes": doc.file_size_bytes,
            "mime_type": doc.mime_type,
            "status": doc.status.value,
            "category": (
                {
                    "id": doc.category.id,
                    "name_en": doc.category.name_en,
                    "name_de": doc.category.name_de,
                    "color": doc.category.color,
                }
                if doc.category
                else None
            ),
            "extracted_keywords": doc.extracted_keywords,
            "is_favorite": doc.is_favorite,
            "view_count": doc.view_count,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(),
            "highlighted_title": (
                self._highlight_text(doc.title, query) if doc.title else None
            ),
        }

    def _generate_search_suggestions(self, user_id: int, query: str) -> List[str]:
        """Generate search suggestions based on query"""
        suggestions = []

        try:
            query_lower = query.lower()

            similar_searches = (
                self.db.query(SearchHistory.query)
                .filter(
                    SearchHistory.user_id == user_id,
                    SearchHistory.query.ilike(f"%{query}%"),
                    SearchHistory.query != query,
                )
                .distinct()
                .limit(3)
                .all()
            )

            suggestions.extend([s[0] for s in similar_searches])

            keyword_suggestions = (
                self.db.query(func.unnest(Document.extracted_keywords))
                .filter(
                    Document.user_id == user_id,
                    func.unnest(Document.extracted_keywords).ilike(f"%{query}%"),
                )
                .distinct()
                .limit(5)
                .all()
            )

            suggestions.extend([s[0] for s in keyword_suggestions if s[0]])

            return list(set(suggestions))[:5]

        except Exception as e:
            logger.error(f"Generate search suggestions failed: {e}")
            return []

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from text for semantic search"""
        try:
            # Simple keyword extraction - remove common stop words
            stop_words = {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
                "will",
                "would",
                "could",
                "should",
                "may",
                "might",
                "must",
                "shall",
                "can",
            }

            words = re.findall(r"\b\w+\b", text.lower())
            keywords = [
                word for word in words if word not in stop_words and len(word) > 2
            ]

            return list(set(keywords))[:10]  # Return unique keywords, max 10

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []

    def _highlight_text(self, text: str, query: str) -> str:
        """Highlight search terms in text"""
        try:
            if not text or not query:
                return text

            pattern = re.compile(re.escape(query), re.IGNORECASE)
            return pattern.sub(f"<mark>{query}</mark>", text)

        except Exception:
            return text

    def _get_category_document_count(self, category_id: int, user_id: int) -> int:
        """Get document count for a category"""
        try:
            return (
                self.db.query(Document)
                .filter(
                    Document.category_id == category_id, Document.user_id == user_id
                )
                .count()
            )
        except Exception:
            return 0

    def _save_search_history(
        self, user_id: int, query: str, entity_type: str, results_count: int
    ):
        """Save search query to history"""
        try:
            existing_entry = (
                self.db.query(SearchHistory)
                .filter(
                    SearchHistory.user_id == user_id,
                    SearchHistory.query == query,
                    SearchHistory.entity_type == entity_type,
                )
                .first()
            )

            if existing_entry:
                existing_entry.results_count = results_count
                existing_entry.created_at = datetime.utcnow()
            else:
                history_entry = SearchHistory(
                    user_id=user_id,
                    query=query,
                    entity_type=entity_type,
                    results_count=results_count,
                )
                self.db.add(history_entry)

            self.db.commit()

        except Exception as e:
            logger.warning(f"Failed to save search history: {e}")
            self.db.rollback()

    def _parse_search_query(self, query: str) -> List[str]:
        """Parse search query into terms for test compatibility"""
        phrases = re.findall(r'"([^"]*)"', query)
        query_without_quotes = re.sub(r'"[^"]*"', "", query)
        words = query_without_quotes.split()
        return phrases + [word for word in words if len(word) > 1]
