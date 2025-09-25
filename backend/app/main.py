# backend/app/main.py
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bonifatus DMS",
    description="Professional Document Management System",
    version="1.0.0",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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


@app.on_event("startup")
async def startup_event():
    """Application startup configuration"""
    logger.info("Bonifatus DMS starting up...")
    await init_database()
    logger.info(f"Environment: {settings.app.app_environment}")
    logger.info(f"CORS origins configured: {settings.cors_origins_list}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown cleanup"""
    logger.info("Bonifatus DMS shutting down...")
    await close_database()


from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.documents import router as documents_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        from app.database.connection import db_manager
        database_healthy = await db_manager.health_check()
        
        return {
            "status": "healthy" if database_healthy else "unhealthy",
            "service": "bonifatus-dms",
            "version": "1.0.0",
            "environment": settings.app.app_environment,
            "database": "connected" if database_healthy else "disconnected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "bonifatus-dms",
            "version": "1.0.0",
            "environment": settings.app.app_environment,
            "error": str(e)
        }