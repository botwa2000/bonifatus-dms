# backend/app/middleware/security_headers.py

"""
Security headers middleware for FastAPI
Adds security-related HTTP headers to all responses
"""

import logging
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    Protects against common web vulnerabilities
    """
    
    def __init__(self, app, frontend_url: str = None):
        super().__init__(app)
        self.frontend_url = frontend_url or os.getenv(
            "FRONTEND_URL", 
            "https://bonidoc.com"
        )
        self.api_url = os.getenv(
            "API_URL",
            "https://bonifatus-dms-mmdbxdflfa-uc.a.run.app"
        )
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """Add security headers to response"""
        
        try:
            response = await call_next(request)
            
            # Content Security Policy
            csp_directives = [
                "default-src 'self'",
                f"connect-src 'self' {self.api_url} https://accounts.google.com https://www.googleapis.com",
                "script-src 'self' 'unsafe-inline' https://accounts.google.com",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: https:",
                "frame-src 'self' https://accounts.google.com",
                "form-action 'self'",
                "base-uri 'self'",
                "object-src 'none'"
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
            
            # HTTP Strict Transport Security (HSTS)
            # Only add if using HTTPS
            if request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )
            
            # Prevent MIME type sniffing
            response.headers["X-Content-Type-Options"] = "nosniff"
            
            # Clickjacking protection
            response.headers["X-Frame-Options"] = "DENY"
            
            # XSS protection (legacy, but doesn't hurt)
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            # Referrer policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            # Permissions policy
            response.headers["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=()"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Security headers middleware error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )