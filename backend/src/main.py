# backend/src/main.py - Fixed Application (Database-Only Initialization)

"""
Bonifatus DMS - Main Application
Complete document management system with Google Drive integration
Production-ready FastAPI application with proper database initialization
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import traceback

from src.database.connection import init_database, close_database
from src.core.config import settings
from src.api import auth, documents, categories, search, users
from src.database import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info(f"Starting Bonifatus DMS in {settings.environment} environment")
    
    try:
        # Initialize database (includes default categories via migrations/connection.py)
        await init_database()
        logger.info("Database initialized successfully")
        
        # Default categories are created by database initialization, not service layer
        logger.info("Application startup completed successfully")
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Bonifatus DMS")
        await close_database()
        logger.info("Database connections closed")

# Initialize FastAPI application
app = FastAPI(
    title="Bonifatus DMS API",
    description="Professional Document Management System with Google Drive Integration",
    version="1.0.0",
    docs_url=settings.docs_url if not settings.is_production else None,
    redoc_url=settings.redoc_url if not settings.is_production else None,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Request processing time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "traceback": traceback.format_exc()
            }
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    try:
        # Basic health check
        health_status = {
            "status": "healthy",
            "environment": settings.environment,
            "version": "1.0.0"
        }
        
        # Database health check
        try:
            db = next(get_db())
            db.execute("SELECT 1")
            health_status["database"] = "healthy"
            db.close()
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            health_status["database"] = "unhealthy"
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "environment": settings.environment,
                "error": str(e) if not settings.is_production else "Service unavailable"
            }
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Bonifatus DMS API",
        "version": "1.0.0",
        "environment": settings.environment,
        "features": {
            "document_processing": True,
            "categorization": True,
            "search": True,
            "google_drive_integration": True,
            "multilingual_support": True
        },
        "docs": settings.docs_url if settings.docs_url else "Disabled in production"
    }

# API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

# API information endpoint
@app.get("/api/v1/info")
async def get_api_info():
    """Get comprehensive API information and capabilities"""
    return {
        "app_name": "Bonifatus DMS",
        "version": "1.0.0",
        "environment": settings.environment,
        "features": {
            "document_upload": True,
            "text_extraction": True,
            "keyword_extraction": True,
            "ai_categorization": True,
            "full_text_search": True,
            "google_drive_integration": True,
            "multilingual_support": True,
            "user_categories": True,
            "advanced_filtering": True
        },
        "limits": {
            "max_file_size_mb": 50,
            "supported_file_types": [".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg"],
            "free_tier_document_limit": 100,
            "premium_trial_document_limit": 500,
            "max_user_categories": 50
        },
        "supported_languages": ["en", "de"],
        "default_categories": [
            "Finance", "Personal", "Business", "Legal", 
            "Archive", "Health", "Education", "Travel"
        ]
    }

# Metrics endpoint (for monitoring)
@app.get("/api/v1/metrics")
async def get_metrics():
    """Get basic application metrics"""
    try:
        db = next(get_db())
        
        # Get basic statistics
        from src.database.models import User, Document, Category
        
        total_users = db.query(User).count()
        total_documents = db.query(Document).count()
        total_categories = db.query(Category).count()
        
        db.close()
        
        return {
            "total_users": total_users,
            "total_documents": total_documents,
            "total_categories": total_categories,
            "environment": settings.environment,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Metrics unavailable"}
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level="info" if settings.is_production else "debug",
        workers=1 if settings.is_development else 4
    )