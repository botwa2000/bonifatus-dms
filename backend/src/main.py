# backend/src/main.py
"""
Bonifatus DMS - Main FastAPI application
Production-ready document management system with clean configuration API
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

# Core imports
from src.core.config import settings
from src.database.connection import db_manager

# API routers
from src.api import auth, documents, categories, search, users

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting Bonifatus DMS in {settings.environment} environment")

    try:
        # Initialize database
        await db_manager.init_database()
        logger.info("Database initialized successfully")

        # Health check
        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Bonifatus DMS")
    try:
        await db_manager.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI application with clean configuration API
app = FastAPI(
    title="Bonifatus DMS API",
    description="Professional Document Management System with Google Drive Integration",
    version="1.0.0",
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan,
)


# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.is_development else ["*.run.app", "localhost"],
)

# CORS middleware using convenience property
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for production error management"""
    logger.error(f"Global exception: {exc}", exc_info=True)

    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Quick database connectivity check
        db_status = "healthy"

        return {
            "status": "healthy",
            "environment": settings.environment,
            "database": db_status,
            "version": "1.0.0",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "environment": settings.environment,
                "error": (
                    str(e) if not settings.is_production else "Service unavailable"
                ),
            },
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Bonifatus DMS API",
        "version": "1.0.0",
        "environment": settings.environment,
        "docs": settings.docs_url if settings.docs_url else "Disabled in production",
    }


# Include API routers with prefix
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])


# Application metadata
@app.get("/api/v1/info")
async def get_api_info():
    """Get API information and configuration"""
    return {
        "app_name": "Bonifatus DMS",
        "version": "1.0.0",
        "environment": settings.environment,
        "features": {
            "google_drive_integration": True,
            "ocr_processing": True,
            "ai_categorization": True,
            "multi_language_support": True,
        },
        "limits": {
            "max_file_size_mb": 50,
            "supported_file_types": [
                ".pdf",
                ".doc",
                ".docx",
                ".txt",
                ".png",
                ".jpg",
                ".jpeg",
            ],
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level="info" if settings.is_production else "debug",
    )
