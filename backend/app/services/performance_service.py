# backend/app/services/performance_service.py
"""
Performance Monitoring Service
Tracks request times, DB queries, and provides internal metrics.
Logs are silent (not exposed externally) and configurable via environment variables.
"""

import logging
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Deque
from app.core.config import settings

# Use a dedicated logger for performance metrics
perf_logger = logging.getLogger("app.performance")


@dataclass
class RequestMetric:
    """Single request performance metric"""
    request_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    db_query_count: int = 0
    db_query_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    client_ip: str = ""
    user_id: Optional[str] = None


@dataclass
class DbQueryMetric:
    """Single database query metric"""
    request_id: str
    query_type: str  # SELECT, INSERT, UPDATE, DELETE, OTHER
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceMonitor:
    """
    Centralized performance monitoring service.
    Thread-safe, stores recent metrics in memory for analysis.
    """

    def __init__(self, max_history: int = 1000):
        self._lock = threading.Lock()
        self._request_history: Deque[RequestMetric] = deque(maxlen=max_history)
        self._db_query_history: Deque[DbQueryMetric] = deque(maxlen=max_history * 5)
        self._current_requests: Dict[str, Dict] = {}  # Track in-flight requests
        self._total_requests = 0
        self._total_db_queries = 0
        self._slow_requests = 0
        self._slow_db_queries = 0

    def start_request(self, request_id: str, method: str, path: str, client_ip: str = "") -> float:
        """Start tracking a request. Returns start time."""
        start_time = time.perf_counter()
        with self._lock:
            self._current_requests[request_id] = {
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "start_time": start_time,
                "db_queries": [],
            }
        return start_time

    def record_db_query(self, request_id: str, query_type: str, duration_ms: float):
        """Record a database query for the current request."""
        if not settings.performance.perf_logging_enabled:
            return

        with self._lock:
            if request_id in self._current_requests:
                self._current_requests[request_id]["db_queries"].append({
                    "type": query_type,
                    "duration_ms": duration_ms
                })

            self._total_db_queries += 1

            # Log slow queries
            threshold = settings.performance.perf_slow_db_query_threshold_ms
            if duration_ms > threshold:
                self._slow_db_queries += 1
                if settings.performance.perf_log_db_queries:
                    perf_logger.warning(
                        f"[SLOW DB] {query_type} query took {duration_ms:.2f}ms (threshold: {threshold}ms)"
                    )

            # Store in history
            metric = DbQueryMetric(
                request_id=request_id,
                query_type=query_type,
                duration_ms=duration_ms
            )
            self._db_query_history.append(metric)

    def end_request(
        self,
        request_id: str,
        status_code: int,
        user_id: Optional[str] = None
    ) -> Optional[RequestMetric]:
        """End request tracking and record metrics."""
        if not settings.performance.perf_logging_enabled:
            return None

        end_time = time.perf_counter()

        with self._lock:
            if request_id not in self._current_requests:
                return None

            req_data = self._current_requests.pop(request_id)
            duration_ms = (end_time - req_data["start_time"]) * 1000

            # Calculate DB metrics
            db_queries = req_data.get("db_queries", [])
            db_query_count = len(db_queries)
            db_query_time_ms = sum(q["duration_ms"] for q in db_queries)

            metric = RequestMetric(
                request_id=request_id,
                method=req_data["method"],
                path=req_data["path"],
                status_code=status_code,
                duration_ms=duration_ms,
                db_query_count=db_query_count,
                db_query_time_ms=db_query_time_ms,
                client_ip=req_data["client_ip"],
                user_id=user_id
            )

            self._request_history.append(metric)
            self._total_requests += 1

            # Log slow requests
            threshold = settings.performance.perf_slow_request_threshold_ms
            is_slow = duration_ms > threshold

            if is_slow:
                self._slow_requests += 1
                perf_logger.warning(
                    f"[SLOW REQUEST] {metric.method} {metric.path} "
                    f"took {duration_ms:.2f}ms (threshold: {threshold}ms) "
                    f"[status={status_code}, db_queries={db_query_count}, db_time={db_query_time_ms:.2f}ms]"
                )
            elif settings.performance.perf_log_all_requests:
                perf_logger.info(
                    f"[REQUEST] {metric.method} {metric.path} "
                    f"{duration_ms:.2f}ms [status={status_code}]"
                )

            return metric

    def get_stats(self) -> Dict:
        """Get performance statistics (for internal metrics endpoint)."""
        with self._lock:
            if not self._request_history:
                return {
                    "total_requests": self._total_requests,
                    "total_db_queries": self._total_db_queries,
                    "slow_requests": self._slow_requests,
                    "slow_db_queries": self._slow_db_queries,
                    "avg_request_time_ms": 0,
                    "avg_db_time_ms": 0,
                    "in_flight_requests": len(self._current_requests),
                }

            recent_requests = list(self._request_history)
            avg_request_time = sum(r.duration_ms for r in recent_requests) / len(recent_requests)
            avg_db_time = (
                sum(r.db_query_time_ms for r in recent_requests) / len(recent_requests)
                if recent_requests else 0
            )

            # Calculate percentiles
            durations = sorted(r.duration_ms for r in recent_requests)
            p50_idx = len(durations) // 2
            p95_idx = int(len(durations) * 0.95)
            p99_idx = int(len(durations) * 0.99)

            return {
                "total_requests": self._total_requests,
                "total_db_queries": self._total_db_queries,
                "slow_requests": self._slow_requests,
                "slow_db_queries": self._slow_db_queries,
                "in_flight_requests": len(self._current_requests),
                "recent_request_count": len(recent_requests),
                "avg_request_time_ms": round(avg_request_time, 2),
                "avg_db_time_ms": round(avg_db_time, 2),
                "p50_request_time_ms": round(durations[p50_idx] if durations else 0, 2),
                "p95_request_time_ms": round(durations[p95_idx] if len(durations) > p95_idx else 0, 2),
                "p99_request_time_ms": round(durations[p99_idx] if len(durations) > p99_idx else 0, 2),
                "thresholds": {
                    "slow_request_ms": settings.performance.perf_slow_request_threshold_ms,
                    "slow_db_query_ms": settings.performance.perf_slow_db_query_threshold_ms,
                }
            }

    def get_recent_slow_requests(self, limit: int = 20) -> List[Dict]:
        """Get recent slow requests for debugging."""
        threshold = settings.performance.perf_slow_request_threshold_ms
        with self._lock:
            slow = [
                {
                    "request_id": r.request_id,
                    "method": r.method,
                    "path": r.path,
                    "duration_ms": round(r.duration_ms, 2),
                    "status_code": r.status_code,
                    "db_query_count": r.db_query_count,
                    "db_query_time_ms": round(r.db_query_time_ms, 2),
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self._request_history
                if r.duration_ms > threshold
            ]
            return slow[-limit:]


# Global instance
performance_monitor = PerformanceMonitor()
