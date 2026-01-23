# backend/src/database/connection.py
"""
Bonifatus DMS - Database Connection Management
Supabase PostgreSQL connection with SQLAlchemy ORM
Production-ready connection pooling and health monitoring
"""

import logging
import time
import threading
from typing import Generator
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.performance")

# Thread-local storage for query timing
_query_context = threading.local()


class DatabaseManager:
    """Manages Supabase PostgreSQL database connections and operations"""

    def __init__(self):
        self._engine = None
        self._session_local = None
        self._initialized = False

    @property
    def engine(self):
        """Get or create database engine with mandatory SSL encryption"""
        if self._engine is None:
            # Always require SSL for security, even for local connections
            # All database connections are encrypted end-to-end
            self._engine = create_engine(
                settings.database.database_url,
                pool_size=settings.database.database_pool_size,
                pool_recycle=settings.database.database_pool_recycle,
                pool_pre_ping=settings.database.database_pool_pre_ping,
                echo=settings.database.database_echo,
                connect_args={
                    "connect_timeout": settings.database.database_connect_timeout,
                    "options": "-c timezone=UTC",
                    "sslmode": "require",
                    "application_name": "bonifatus-dms",
                },
            )
            logger.info("Database engine created successfully with SSL encryption")
        return self._engine

    @property
    def session_local(self):
        """Get or create session factory"""
        if self._session_local is None:
            self._session_local = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )
            logger.info("Database session factory created")
        return self._session_local

    async def init_database(self) -> bool:
        """Initialize database connection"""
        try:
            if await self.health_check():
                self._initialized = True
                logger.info("Database initialization completed successfully")
                return True
            else:
                logger.error("Database health check failed after initialization")
                return False
        except SQLAlchemyError as e:
            logger.error(f"Database initialization failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {e}")
            return False

    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            session = self.session_local()
            try:
                result = session.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                return row and row.health_check == 1
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False

    def get_db_session(self) -> Generator[Session, None, None]:
        """Database dependency for FastAPI"""
        session = self.session_local()
        try:
            yield session
        except Exception:
            # Rollback on any exception to prevent "transaction is aborted" errors
            session.rollback()
            raise
        finally:
            session.close()

    async def close(self):
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def _setup_query_timing_events(engine_instance):
    """Set up SQLAlchemy event listeners for query performance monitoring."""
    from app.services.performance_service import performance_monitor

    @event.listens_for(engine_instance, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        _query_context.start_time = time.perf_counter()

    @event.listens_for(engine_instance, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query end time and log if slow."""
        if not hasattr(_query_context, "start_time"):
            return

        duration_ms = (time.perf_counter() - _query_context.start_time) * 1000

        # Determine query type
        stmt_upper = statement.strip().upper()[:20]
        if stmt_upper.startswith("SELECT"):
            query_type = "SELECT"
        elif stmt_upper.startswith("INSERT"):
            query_type = "INSERT"
        elif stmt_upper.startswith("UPDATE"):
            query_type = "UPDATE"
        elif stmt_upper.startswith("DELETE"):
            query_type = "DELETE"
        else:
            query_type = "OTHER"

        # Get request_id from context if available
        request_id = getattr(_query_context, "request_id", "unknown")

        # Record in performance monitor
        performance_monitor.record_db_query(
            request_id=request_id,
            query_type=query_type,
            duration_ms=duration_ms
        )

        del _query_context.start_time


def set_request_context(request_id: str):
    """Set the current request ID for DB query tracking."""
    _query_context.request_id = request_id


def clear_request_context():
    """Clear the current request context."""
    if hasattr(_query_context, "request_id"):
        del _query_context.request_id


# Set up event listeners
_setup_query_timing_events(db_manager.engine)

# Convenience exports for backward compatibility
engine = db_manager.engine
SessionLocal = db_manager.session_local
get_db = db_manager.get_db_session
init_database = db_manager.init_database
close_database = db_manager.close