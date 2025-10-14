# backend/app/middleware/process_time.py

import logging
import time
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

logger = logging.getLogger(__name__)


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Add request ID and track processing time"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request error [ID: {request_id}] after {process_time:.3f}s: {e}",
                exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": str(process_time)
                }
            )