# backend/src/api/__init__.py
"""
Bonifatus DMS - API Module
FastAPI routers and endpoints for all system operations
RESTful API design with comprehensive error handling
"""

from fastapi import APIRouter
from .auth import router as auth_router
from .documents import router as documents_router
from .categories import router as categories_router
from .users import router as users_router

# Main API router with versioning
api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])

api_router.include_router(documents_router, prefix="/documents", tags=["documents"])

api_router.include_router(categories_router, prefix="/categories", tags=["categories"])

api_router.include_router(users_router, prefix="/users", tags=["users"])

__all__ = ["api_router"]
