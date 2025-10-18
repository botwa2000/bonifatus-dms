# backend/src/database/connection.py
"""
Bonifatus DMS - Database Connection Management
Supabase PostgreSQL connection with SQLAlchemy ORM
Production-ready connection pooling and health monitoring
"""

import logging
from typing import Generator, Optional
from contextvars import ContextVar
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings

logger = logging.getLogger(__name__)

# Context variable to store current user ID for RLS
current_user_id_context: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)


class DatabaseManager:
    """Manages Supabase PostgreSQL database connections and operations"""

    def __init__(self):
        self._engine = None
        self._session_local = None
        self._initialized = False

    @property
    def engine(self):
        """Get or create database engine"""
        if self._engine is None:
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
            logger.info("Database engine created successfully")
        return self._engine

    @property
    def session_local(self):
        """Get or create session factory"""
        if self._session_local is None:
            self._session_local = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            # Register event listener to set RLS user context
            @event.listens_for(self._session_local, "after_begin")
            def receive_after_begin(session, transaction, connection):
                """Set app.current_user_id for Row Level Security policies"""
                user_id = current_user_id_context.get()
                if user_id:
                    # Set the session variable for RLS policies
                    connection.execute(
                        text("SELECT set_config('app.current_user_id', :user_id, false)"),
                        {"user_id": str(user_id)}
                    )
                    logger.debug(f"Set RLS context for user: {user_id}")

            logger.info("Database session factory created with RLS support")
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

    def get_db_session(self, user_id: Optional[str] = None) -> Generator[Session, None, None]:
        """
        Database dependency for FastAPI

        Args:
            user_id: Optional user ID to set for RLS context
        """
        # Set user ID in context for RLS
        token = None
        if user_id:
            token = current_user_id_context.set(user_id)

        session = self.session_local()
        try:
            yield session
        finally:
            session.close()
            # Reset context
            if token:
                current_user_id_context.reset(token)

    async def close(self):
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()

# Convenience exports for backward compatibility
engine = db_manager.engine
SessionLocal = db_manager.session_local
init_database = db_manager.init_database
close_database = db_manager.close


def get_db(user_id: Optional[str] = None) -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI endpoints

    Args:
        user_id: Optional user ID to set RLS context

    Usage:
        # Without user context (for public endpoints)
        def endpoint(db: Session = Depends(get_db)):
            ...

        # With user context (for authenticated endpoints) - use get_db_with_user instead
    """
    yield from db_manager.get_db_session(user_id=user_id)


class GetDBWithUser:
    """
    Callable dependency class that creates a database session with user context for RLS

    Usage in FastAPI endpoints:
        @router.post("/endpoint")
        async def endpoint(
            current_user: User = Depends(get_current_active_user),
            db: Session = Depends(GetDBWithUser())
        ):
            # The database session will automatically have RLS context set
            ...
    """

    def __call__(self) -> Generator[Session, None, None]:
        """Create database session with user context from ContextVar"""
        user_id = current_user_id_context.get()
        yield from db_manager.get_db_session(user_id=user_id)


# Create singleton instance for dependency injection
get_db_with_user = GetDBWithUser()