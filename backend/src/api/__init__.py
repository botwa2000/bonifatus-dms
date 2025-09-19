# backend/src/api/__init__.py
"""
Bonifatus DMS - API Module
FastAPI routers and endpoints for all system operations
RESTful API design with comprehensive error handling
"""

from fastapi import APIRouter

# Import individual routers for main.py
from . import auth
from . import documents
from . import categories
from . import search
from . import users

# Main API router with versioning (optional unified approach)
api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers in unified router
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Export both individual routers and unified router
__all__ = ["api_router", "auth", "documents", "categories", "search", "users"]
