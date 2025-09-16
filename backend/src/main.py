# backend/src/main.py
"""
Bonifatus DMS - Main FastAPI Application
Production-ready document management system with Google Drive integration
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.connection import init_database
from src.core.config import get_settings
from src.api import api_router
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize FastAPI application
app = FastAPI(
    title="Bonifatus DMS",
    description="Professional Document Management System",
    version="1.0.0",
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url="/api/redoc" if settings.environment != "production" else None,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "bonifatus-dms", "database": "supabase"}


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database connection and tables"""
    await init_database()
    logger.info("Bonifatus DMS started successfully with Supabase")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Bonifatus DMS API", "version": "1.0.0", "database": "supabase"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
