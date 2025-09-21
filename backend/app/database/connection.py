# backend/src/database/connection.py
"""
Bonifatus DMS - Database Connection Management
Supabase PostgreSQL connection with SQLAlchemy ORM
Production-ready connection pooling and health monitoring
"""

import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings

logger = logging.getLogger(__name__)


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
        finally:
            session.close()

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
get_db = db_manager.get_db_session
init_database = db_manager.init_database
close_database = db_manager.close