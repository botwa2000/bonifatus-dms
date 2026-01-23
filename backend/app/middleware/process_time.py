# backend/app/middleware/process_time.py

import logging
import time
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
from app.services.performance_service import performance_monitor
from app.database.connection import set_request_context, clear_request_context

logger = logging.getLogger(__name__)


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Add request ID, track processing time, and record performance metrics"""

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Get client IP (handle proxies)
        client_ip = request.headers.get("X-Real-IP") or request.headers.get(
            "X-Forwarded-For", ""
        ).split(",")[0].strip() or request.client.host if request.client else ""

        # Start performance tracking
        performance_monitor.start_request(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip
        )

        # Set request context for DB query tracking
        set_request_context(request_id)

        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id

            # Get user_id if available
            user_id: Optional[str] = None
            if hasattr(request.state, "user") and request.state.user:
                user_id = str(getattr(request.state.user, "id", None))

            # Record performance metrics
            performance_monitor.end_request(
                request_id=request_id,
                status_code=response.status_code,
                user_id=user_id
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request error [ID: {request_id}] after {process_time:.3f}s: {e}",
                exc_info=True
            )

            # Record failed request
            performance_monitor.end_request(
                request_id=request_id,
                status_code=500,
                user_id=None
            )

            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": str(process_time)
                }
            )

        finally:
            # Always clear request context
            clear_request_context()