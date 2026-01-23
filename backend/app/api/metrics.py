# backend/app/api/metrics.py
"""
Internal Performance Metrics API
Only accessible from localhost/internal networks.
"""

from fastapi import APIRouter, Request, HTTPException, status
from app.services.performance_service import performance_monitor
from app.core.config import settings

router = APIRouter(tags=["metrics"])


def _is_internal_request(request: Request) -> bool:
    """Check if request is from localhost/internal network."""
    client_host = request.client.host if request.client else ""

    # Allow localhost and Docker internal IPs
    internal_ips = [
        "127.0.0.1",
        "::1",
        "localhost",
    ]

    # Docker internal network ranges
    if client_host.startswith("172.") or client_host.startswith("10."):
        return True

    return client_host in internal_ips


@router.get("/metrics")
async def get_metrics(request: Request):
    """
    Get performance metrics.
    Only accessible from localhost/internal networks.
    """
    if not settings.performance.perf_metrics_endpoint_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics endpoint is disabled"
        )

    if settings.is_production and not _is_internal_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Metrics endpoint is only accessible internally"
        )

    return {
        "status": "ok",
        "environment": settings.app.app_environment,
        "performance": performance_monitor.get_stats()
    }


@router.get("/metrics/slow-requests")
async def get_slow_requests(request: Request, limit: int = 20):
    """
    Get recent slow requests for debugging.
    Only accessible from localhost/internal networks.
    """
    if not settings.performance.perf_metrics_endpoint_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics endpoint is disabled"
        )

    if settings.is_production and not _is_internal_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Metrics endpoint is only accessible internally"
        )

    return {
        "environment": settings.app.app_environment,
        "slow_request_threshold_ms": settings.performance.perf_slow_request_threshold_ms,
        "slow_requests": performance_monitor.get_recent_slow_requests(limit=limit)
    }
