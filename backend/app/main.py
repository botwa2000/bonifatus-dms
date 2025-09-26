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
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title=settings.app.app_title,
    description=settings.app.app_description,
    version=settings.app.app_version,
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None
)

# Security: Trusted host middleware
if settings.is_production:
    trusted_hosts = [host.strip() for host in settings.cors_origins_list if host.startswith('https://')]
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID"]
)


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Middleware to add processing time and request ID headers"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        import uuid
        
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
            "timestamp": time.time()
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
            "error": str(e) if not settings.is_production else "Health check failed"
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


@app.get("/api/v1/status")
async def detailed_status():
    """Detailed system status endpoint"""
    try:
        status = {
            "application": {
                "name": settings.app.app_title,
                "version": settings.app.app_version,
                "environment": settings.app.app_environment,
                "debug_mode": settings.app.app_debug_mode
            },
            "configuration": {
                "cors_origins_count": len(settings.cors_origins_list),
                "admin_emails_count": len(settings.admin_email_list),
                "google_oauth_enabled": bool(settings.google.google_client_id),
                "google_vision_enabled": settings.google.google_vision_enabled
            },
            "timestamp": time.time()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")


try:
    from app.api.auth import router as auth_router
    app.include_router(auth_router)
    logger.info("Auth router loaded successfully")
except ImportError as e:
    logger.warning(f"Auth router not available: {e}")
    
    from fastapi import APIRouter
    fallback_auth_router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
    
    @fallback_auth_router.get("/google/config")
    async def get_google_oauth_config():
        """Minimal Google OAuth config endpoint"""
        return {
            "google_client_id": settings.google.google_client_id,
            "redirect_uri": settings.google.google_redirect_uri
        }
    
    app.include_router(fallback_auth_router)
    logger.info("Fallback auth router loaded")

try:
    from app.api.users import router as users_router
    app.include_router(users_router)
    logger.info("Users router loaded successfully")
except ImportError as e:
    logger.warning(f"Users router not available: {e}")

try:
    from app.api.documents import router as documents_router
    app.include_router(documents_router)
    logger.info("Documents router loaded successfully")
except ImportError as e:
    logger.warning(f"Documents router not available: {e}")


@app.on_event("startup")
async def startup_event():
    """Application startup configuration"""
    logger.info(f"Starting {settings.app.app_title} v{settings.app.app_version}")
    logger.info(f"Environment: {settings.app.app_environment}")
    logger.info(f"Debug mode: {settings.app.app_debug_mode}")
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


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown cleanup"""
    logger.info(f"Shutting down {settings.app.app_title}")
    
    try:
        from app.database.connection import close_database
        await close_database()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.warning(f"Database shutdown error: {e}")
    
    logger.info("Application shutdown completed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.app.app_host,
        port=settings.app.app_port,
        log_level="info" if settings.is_production else "debug",
        access_log=not settings.is_production
    )