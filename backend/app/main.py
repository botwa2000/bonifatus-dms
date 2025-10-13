from starlette.middleware.base import BaseHTTPMiddleware# backend/app/main.py
import os
import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Callable
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info(f"Starting {settings.app.app_title} v{settings.app.app_version}")
    logger.info(f"Environment: {settings.app.app_environment}")
    logger.info(f"Debug mode: {settings.app.app_debug_mode}")
    logger.info(f"Port: {os.getenv('PORT', 'not set')}")
    logger.info(f"CORS origins: {settings.cors_origins_list}")
    
    try:
        from app.database.connection import init_database
        await init_database()
        logger.info("Database initialized successfully")
    except ImportError:
        logger.warning("Database module not found - operating without database")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing without database): {e}")
    
    logger.info("Application startup completed successfully")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app.app_title}")
    
    try:
        from app.database.connection import close_database
        await close_database()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.warning(f"Database shutdown error: {e}")
    
    logger.info("Application shutdown completed")

# Create FastAPI application
app = FastAPI(
    title=settings.app.app_title,
    description=settings.app.app_description,
    version=settings.app.app_version,
    docs_url="/docs" if settings.app.app_debug_mode else None,
    redoc_url="/redoc" if settings.app.app_debug_mode else None,
    lifespan=lifespan
)

# CORS configuration
allowed_origins = ["*"] if settings.app.app_cors_origins == "*" else settings.app.app_cors_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

logger.info(f"CORS enabled for origins: {allowed_origins}")

class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID and process time"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

app.add_middleware(ProcessTimeMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with request tracking"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(f"Unhandled exception [Request ID: {request_id}]: {exc}")
    logger.error(f"Request URL: {request.url}")
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": request_id
            }
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if settings.is_production else str(exc),
            "request_id": request_id
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    try:
        health_info = {
            "status": "healthy",
            "service": "bonifatus-dms",
            "version": settings.app.app_version,
            "environment": settings.app.app_environment,
            "timestamp": time.time(),
            "port": os.getenv("PORT", "unknown")
        }
        
        try:
            from app.database.connection import db_manager
            db_healthy = await db_manager.health_check()
            health_info["database"] = "connected" if db_healthy else "disconnected"
        except ImportError:
            health_info["database"] = "not_configured"
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            health_info["database"] = "error"
        
        try:
            from app.services.google_service import google_service
            drive_healthy = await google_service.test_drive_connection()
            health_info["google_drive"] = "connected" if drive_healthy else "disconnected"
        except ImportError:
            health_info["google_drive"] = "not_configured"
        except Exception as e:
            logger.warning(f"Google services health check failed: {e}")
            health_info["google_drive"] = "error"
        
        return health_info
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "bonifatus-dms",
            "version": settings.app.app_version,
            "environment": settings.app.app_environment,
            "error": str(e) if not settings.is_production else "Health check failed",
            "port": os.getenv("PORT", "unknown")
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app.app_title,
        "description": settings.app.app_description,
        "version": settings.app.app_version,
        "environment": settings.app.app_environment
    }

# Include routers - all prefixes defined in router files
routers = [
    ("app.api.auth", "Auth"),
    ("app.api.users", "Users"),
    ("app.api.settings", "Settings"),
    ("app.api.categories", "Categories"),
    ("app.api.document_analysis", "DocumentAnalysis"),
    ("app.api.documents", "Documents"),
    ("app.api.security", "Security"),
]

for module_path, name in routers:
    try:
        module = __import__(module_path, fromlist=["router"])
        app.include_router(module.router)
        logger.info(f"✓ {name} router loaded")
    except Exception as e:
        logger.error(f"✗ {name} router failed: {e}")
        import traceback
        traceback.print_exc()
        raise  # Fail deployment if any router fails
    
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Bonifatus DMS server on {host}:{port}")
    logger.info(f"Environment: {settings.app.app_environment}")
    logger.info(f"Debug mode: {settings.app.app_debug_mode}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info" if settings.is_production else "debug",
        access_log=not settings.is_production,
        workers=1,
        timeout_keep_alive=30,
        timeout_graceful_shutdown=10
    )