# backend/src/database/connection.py
"""
Bonifatus DMS - Database Connection Management
Supabase PostgreSQL connection with SQLAlchemy ORM
Production-ready connection pooling and health monitoring
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from src.core.config import get_settings
from src.database.models import Base
import logging
import asyncio
from typing import Generator

logger = logging.getLogger(__name__)
settings = get_settings()


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
        """Initialize database tables and default data"""
        try:
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")

            # Initialize default data if needed
            await self._create_default_data()

            # Verify database connection
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
            with self.session_local() as session:
                # Simple query to test connection
                result = session.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                return row and row.health_check == 1
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False

    async def _create_default_data(self):
        """Create default system data (categories, settings, etc.)"""
        try:
            from src.database.models import Category, SystemSettings

            with self.session_local() as session:
                # Check if default categories exist
                existing_categories = (
                    session.query(Category)
                    .filter(Category.is_system_category == True)
                    .count()
                )

                if existing_categories == 0:
                    # Create default categories
                    default_categories = [
                        {
                            "name_en": "Finance",
                            "name_de": "Finanzen",
                            "description_en": "Financial documents, invoices, receipts",
                            "description_de": "Finanzielle Dokumente, Rechnungen, Quittungen",
                            "color": "#10B981",
                            "is_system_category": True,
                            "keywords": "invoice,receipt,bank,financial,money,payment",
                        },
                        {
                            "name_en": "Personal",
                            "name_de": "Persönlich",
                            "description_en": "Personal documents, certificates, ID",
                            "description_de": "Persönliche Dokumente, Zertifikate, Ausweis",
                            "color": "#3B82F6",
                            "is_system_category": True,
                            "keywords": "personal,certificate,passport,id,identification",
                        },
                        {
                            "name_en": "Business",
                            "name_de": "Geschäft",
                            "description_en": "Business documents, contracts, reports",
                            "description_de": "Geschäftsdokumente, Verträge, Berichte",
                            "color": "#8B5CF6",
                            "is_system_category": True,
                            "keywords": "business,contract,report,presentation,meeting",
                        },
                        {
                            "name_en": "Legal",
                            "name_de": "Rechtlich",
                            "description_en": "Legal documents, contracts, insurance",
                            "description_de": "Rechtsdokumente, Verträge, Versicherung",
                            "color": "#EF4444",
                            "is_system_category": True,
                            "keywords": "legal,contract,insurance,law,court,agreement",
                        },
                        {
                            "name_en": "Archive",
                            "name_de": "Archiv",
                            "description_en": "Archived documents, old files",
                            "description_de": "Archivierte Dokumente, alte Dateien",
                            "color": "#6B7280",
                            "is_system_category": True,
                            "keywords": "archive,old,historical,reference",
                        },
                    ]

                    for cat_data in default_categories:
                        category = Category(**cat_data)
                        session.add(category)

                    session.commit()
                    logger.info(f"Created {len(default_categories)} default categories")

                # Check if system settings exist
                existing_settings = session.query(SystemSettings).count()
                if existing_settings == 0:
                    # Create default system settings
                    default_settings = SystemSettings(
                        free_tier_document_limit=100,
                        premium_trial_document_limit=500,
                        premium_document_limit=0,  # 0 = unlimited
                        free_tier_monthly_uploads=50,
                        premium_monthly_uploads=0,  # 0 = unlimited
                        max_file_size_mb=50,
                        ocr_enabled=True,
                        ai_categorization_enabled=True,
                        default_language="en",
                        supported_languages=["en", "de"],
                        maintenance_mode=False,
                    )
                    session.add(default_settings)
                    session.commit()
                    logger.info("Created default system settings")

        except Exception as e:
            logger.error(f"Failed to create default data: {e}")

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
