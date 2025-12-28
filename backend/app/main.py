# backend/app/main.py

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

# Configure environment-aware logging
log_level = getattr(logging, settings.app.app_log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Production hardening: Force WARNING level in production unless explicitly overridden
if settings.is_production and settings.app.app_log_level == "INFO":
    logging.getLogger().setLevel(logging.WARNING)
    logger.info("Production mode: Forcing log level to WARNING to prevent sensitive data exposure")

# Reduce SQLAlchemy verbosity - only show warnings and errors
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # CORS origins will be logged after middleware is configured
    # Startup
    logger.info(f"Starting {settings.app.app_title} v{settings.app.app_version}")
    logger.info(f"Environment: {settings.app.app_environment}")
    logger.info(f"Debug mode: {settings.app.app_debug_mode}")
    logger.info(f"Port: {os.getenv('PORT', 'not set')}")
    
    try:
        from app.database.connection import init_database
        await init_database()
        logger.info("Database initialized successfully")
    except ImportError:
        logger.warning("Database module not found - operating without database")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing without database): {e}")
    
    # Start rate limit cleanup task
    try:
        from app.services.rate_limit_service import rate_limit_service
        rate_limit_service.start_cleanup_task()
        logger.info("Rate limit service initialized")
    except Exception as e:
        logger.warning(f"Rate limit service initialization failed: {e}")

    # Start ClamAV auto-restart monitoring
    try:
        from app.services.clamav_health_service import clamav_health_service
        import asyncio

        async def clamav_health_monitor():
            """Background task to monitor and auto-restart ClamAV"""
            while True:
                try:
                    await asyncio.sleep(60)  # Check every 60 seconds
                    result = await clamav_health_service.auto_restart_if_needed()
                    if result.get('auto_restart_attempted'):
                        logger.warning(f"ClamAV auto-restart triggered: {result}")
                except Exception as e:
                    logger.error(f"ClamAV health monitor error: {e}")

        asyncio.create_task(clamav_health_monitor())
        logger.info("ClamAV auto-restart monitor initialized (checks every 60s)")
    except Exception as e:
        logger.warning(f"ClamAV monitor initialization failed: {e}")

    # Start expired temp files cleanup task
    try:
        import asyncio
        from pathlib import Path
        from datetime import datetime
        import json
        import shutil

        async def temp_files_cleanup():
            """Background task to cleanup expired temp files"""
            while True:
                try:
                    await asyncio.sleep(300)  # Check every 5 minutes

                    batch_dir = Path("/app/temp/batches")
                    if not batch_dir.exists():
                        continue

                    deleted_count = 0
                    # Iterate through all batch directories
                    for batch_folder in batch_dir.iterdir():
                        if not batch_folder.is_dir():
                            continue

                        # Check all metadata files in this batch
                        for metadata_file in batch_folder.glob("*.json"):
                            try:
                                with open(metadata_file, 'r') as f:
                                    metadata = json.load(f)

                                expires_at = datetime.fromisoformat(metadata['expires_at'])
                                if datetime.utcnow() > expires_at:
                                    # Delete the entire batch directory if expired
                                    shutil.rmtree(batch_folder)
                                    deleted_count += 1
                                    logger.info(f"Deleted expired batch: {batch_folder.name}")
                                    break  # Batch deleted, no need to check other files
                            except Exception as e:
                                logger.warning(f"Error checking temp file {metadata_file}: {e}")

                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} expired temp batch(es)")

                except Exception as e:
                    logger.error(f"Temp files cleanup error: {e}")

        asyncio.create_task(temp_files_cleanup())
        logger.info("Temp files cleanup task initialized (runs every 5 minutes)")
    except Exception as e:
        logger.warning(f"Temp files cleanup initialization failed: {e}")

    # Start email polling task
    try:
        from app.tasks import start_email_poller
        start_email_poller()
        logger.info("Email polling task initialized")
    except Exception as e:
        logger.warning(f"Email polling initialization failed: {e}")

    logger.info("Application startup completed successfully")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app.app_title}")

    # Stop email polling task
    try:
        from app.tasks import stop_email_poller
        stop_email_poller()
        logger.info("Email polling task stopped")
    except Exception as e:
        logger.warning(f"Email polling shutdown error: {e}")
    
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

# CORS configuration - include both main domain and API subdomain
def build_allowed_origins(cors_config: str) -> list[str]:
    """Build CORS allowed origins including API subdomain variants"""
    if cors_config == "*":
        return ["*"]

    base_origins = [origin.strip() for origin in cors_config.split(",")]
    allowed_origins = []

    for origin in base_origins:
        allowed_origins.append(origin)
        # Add api subdomain variant if not already present
        if "://" in origin and "api" not in origin.split("://")[1].split(".")[0]:
            parts = origin.split("://")
            domain = parts[1]

            # Handle dev subdomain: dev.bonidoc.com -> api-dev.bonidoc.com
            if domain.startswith("dev."):
                api_origin = f"{parts[0]}://api-{domain}"
            # Handle main domain: bonidoc.com -> api.bonidoc.com
            else:
                api_origin = f"{parts[0]}://api.{domain}"

            allowed_origins.append(api_origin)

    return allowed_origins

allowed_origins = build_allowed_origins(settings.app.app_cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=settings.cors_allow_methods_list,
    allow_headers=settings.cors_allow_headers_list,
    expose_headers=settings.cors_expose_headers_list,
)

# Import and apply middleware in correct order
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.process_time import ProcessTimeMiddleware

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Process time and request ID middleware
app.add_middleware(ProcessTimeMiddleware)

logger.info(f"CORS enabled for origins: {allowed_origins}")
logger.info(f"Middleware stack: SecurityHeaders -> RateLimit -> ProcessTime")

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

        # ClamAV malware scanner status
        try:
            from app.services.malware_scanner_service import malware_scanner_service
            scanner_status = await malware_scanner_service.get_scanner_status()
            health_info["malware_scanner"] = {
                "clamav": "available" if scanner_status["clamav"]["available"] else "unavailable",
                "clamav_version": scanner_status["clamav"].get("version", "unknown"),
                "pdf_validator": "available" if scanner_status["pdf_validator"]["available"] else "unavailable"
            }
        except Exception as e:
            logger.warning(f"Malware scanner health check failed: {e}")
            health_info["malware_scanner"] = "error"

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
    ("app.api.admin", "Admin"),
    ("app.api.users", "Users"),
    ("app.api.storage_providers", "StorageProviders"),
    ("app.api.settings", "Settings"),
    ("app.api.categories", "Categories"),
    ("app.api.document_analysis", "DocumentAnalysis"),
    ("app.api.documents", "Documents"),
    ("app.api.security", "Security"),
    ("app.api.translation", "Translation"),
    ("app.api.entity_quality", "EntityQuality"),
    ("app.api.billing_subscriptions", "Billing"),
    ("app.api.billing_cancellations", "BillingCancellations"),
    ("app.api.webhooks", "Webhooks"),
    ("app.api.email_processing", "EmailProcessing"),
    ("app.api.delegates", "Delegates"),
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