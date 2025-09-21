# backend/src/main.py
"""
Bonifatus DMS - Main FastAPI Application
Production-ready document management system with Google Drive integration
"""
import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.database.connection import init_database, close_database
from app.api.auth import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Bonifatus DMS",
    description="Professional Document Management System",
    version="1.0.0",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
)

# CORS configuration
cors_origins = [origin.strip() for origin in settings.app.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Middleware to add processing time header"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


app.add_middleware(ProcessTimeMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(f"Request URL: {request.url}")
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include API routers
app.include_router(auth_router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    from src.database.connection import db_manager
    
    database_healthy = await db_manager.health_check()
    
    return {
        "status": "healthy" if database_healthy else "unhealthy",
        "service": "bonifatus-dms",
        "database": "connected" if database_healthy else "disconnected",
        "environment": settings.app.app_environment,
        "authentication": "enabled"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Bonifatus DMS API",
        "version": "1.0.0",
        "environment": settings.app.app_environment,
        "docs": "/api/docs" if settings.is_development else "disabled",
        "authentication": "enabled"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database connection"""
    logger.info(f"Starting Bonifatus DMS in {settings.app.app_environment} environment")
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        if not settings.is_production:
            raise
    
    logger.info("Application startup completed successfully")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections"""
    logger.info("Shutting down Bonifatus DMS")
    await close_database()
    logger.info("Database connections closed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.app.port,
        log_level="info" if settings.is_production else "debug"
    )