# backend/src/api/search.py
"""
Bonifatus DMS - Search API
Unified search functionality across all entities
Advanced filtering, ranking, and suggestion features
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from src.database import get_db
from src.services.auth_service import AuthService
from src.services.search_service import SearchService

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request model"""
    query: str
    category_ids: Optional[List[int]] = None
    file_types: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    sort_by: Optional[str] = "relevance"
    sort_order: Optional[str] = "desc"


class GlobalSearchRequest(BaseModel):
    """Global search across all entities"""
    query: str
    entities: Optional[List[str]] = ["documents", "categories"]
    limit: Optional[int] = 20


@router.post("/documents")
async def search_documents(
    search_request: SearchRequest,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Advanced document search with filters and ranking
    """
    try:
        # Authenticate user
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)  # REMOVED await
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Initialize search service
        search_service = SearchService(db)

        # Build search filters
        search_filters = {
            "user_id": user.id,
            "category_ids": search_request.category_ids,
            "file_types": search_request.file_types,
            "date_from": search_request.date_from,
            "date_to": search_request.date_to,
            "page": page,
            "per_page": per_page,
            "sort_by": search_request.sort_by,
            "sort_order": search_request.sort_order,
        }

        # Perform search
        results = await search_service.advanced_search(search_request.query, search_filters)

        return {
            "results": results["documents"],
            "total": results["total"],
            "query": search_request.query,
            "search_time_ms": results["search_time_ms"],
            "suggestions": results.get("suggestions", []),
            "pagination": {
                "page": page,
                "per_page": per_page,
                "pages": (results["total"] + per_page - 1) // per_page,
            },
            "filters_applied": {
                "category_ids": search_request.category_ids,
                "file_types": search_request.file_types,
                "date_range": {
                    "from": search_request.date_from,
                    "to": search_request.date_to
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.post("/categories")
async def search_categories(
    query: str,
    include_system: bool = Query(True),
    language: str = Query("en", regex="^(en|de)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Search categories with multilingual support
    """
    try:
        # Authenticate user
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Initialize search service
        search_service = SearchService(db)

        # Search categories
        results = await search_service.search_categories(
            user_id=user.id,
            query=query,
            include_system=include_system,
            language=language
        )

        return {
            "results": results["categories"],
            "total": results["total"],
            "query": query,
            "language": language,
            "search_time_ms": results["search_time_ms"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Category search failed"
        )


@router.post("/global")
async def global_search(
    search_request: GlobalSearchRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Global search across multiple entities
    """
    try:
        # Authenticate user
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Initialize search service
        search_service = SearchService(db)

        # Perform global search
        results = await search_service.global_search(
            user_id=user.id,
            query=search_request.query,
            entities=search_request.entities,
            limit=search_request.limit
        )

        return {
            "query": search_request.query,
            "entities_searched": search_request.entities,
            "results": results["results"],
            "total_results": results["total_results"],
            "search_time_ms": results["search_time_ms"],
            "results_by_entity": results["results_by_entity"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Global search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Global search failed"
        )


@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=2),
    entity: str = Query("documents", regex="^(documents|categories|all)$"),
    limit: int = Query(5, ge=1, le=10),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get search suggestions as user types
    """
    try:
        # Authenticate user
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Initialize search service
        search_service = SearchService(db)

        # Get suggestions
        suggestions = await search_service.get_search_suggestions(
            user_id=user.id,
            query=query,
            entity=entity,
            limit=limit
        )

        return {
            "query": query,
            "suggestions": suggestions,
            "entity": entity
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get suggestions"
        )


@router.get("/recent")
async def get_recent_searches(
    limit: int = Query(10, ge=1, le=20),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get user's recent search queries
    """
    try:
        # Authenticate user
        auth_service = AuthService(db)
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Initialize search service
        search_service = SearchService(db)

        # Get recent searches
        recent_searches = await search_service.get_recent_searches(
            user_id=user.id,
            limit=limit
        )

        return {
            "recent_searches": recent_searches,
            "total": len(recent_searches)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recent searches failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recent searches"
        )