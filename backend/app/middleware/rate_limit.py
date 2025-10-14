# backend/app/middleware/rate_limit.py

"""
Rate limiting middleware for FastAPI
Applies rate limits to all API endpoints based on operation type
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
import re

from app.services.rate_limit_service import rate_limit_service


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limiting on API endpoints
    Uses different tiers based on endpoint patterns
    """
    
    # Patterns for tier classification
    AUTH_PATTERNS = [
        r"/api/v1/auth/.*",
        r"/api/v1/login.*",
        r"/api/v1/register.*"
    ]
    
    WRITE_PATTERNS = [
        r"/api/v1/.*/upload.*",
        r"/api/v1/documents(?:/.*)?",
        r"/api/v1/categories(?:/.*)?",
        r"/api/v1/settings(?:/.*)?",
    ]
    
    EXEMPT_PATTERNS = [
        r"/health",
        r"/docs",
        r"/openapi.json",
        r"/redoc"
    ]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """Apply rate limiting before processing request"""
        
        path = request.url.path
        method = request.method
        
        # Skip rate limiting for exempt endpoints
        if self._is_exempt(path):
            return await call_next(request)
        
        # Determine rate limit tier
        tier = self._determine_tier(path, method)
        
        # Get identifier (user_id or IP)
        identifier = self._get_identifier(request)
        
        # Check rate limit
        is_allowed, retry_after = rate_limit_service.check_rate_limit(
            identifier, 
            tier
        )
        
        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Retry after {retry_after} seconds."
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        remaining = rate_limit_service.get_remaining(identifier, tier)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Tier"] = tier
        
        return response
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting"""
        return any(
            re.match(pattern, path) 
            for pattern in self.EXEMPT_PATTERNS
        )
    
    def _determine_tier(self, path: str, method: str) -> str:
        """Determine which rate limit tier to apply"""
        
        # Auth tier
        if any(re.match(pattern, path) for pattern in self.AUTH_PATTERNS):
            return "auth"
        
        # Write tier (POST, PUT, PATCH, DELETE)
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            if any(re.match(pattern, path) for pattern in self.WRITE_PATTERNS):
                return "write"
        
        # Default to read tier
        return "read"
    
    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        
        # Try to get user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"