# backend/src/database/__init__.py
"""
Bonifatus DMS - Database Module
Supabase PostgreSQL integration with SQLAlchemy ORM
All database models and connection management
"""

from .connection import engine, SessionLocal, get_db, init_database
from .models import (
    Base,
    User,
    Document,
    Category,
    UserSettings,
    SystemSettings,
    AuditLog,
    UserTier,
    DocumentStatus,
)

__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "init_database",
    "Base",
    "User",
    "Document",
    "Category",
    "UserSettings",
    "SystemSettings",
    "AuditLog",
    "UserTier",
    "DocumentStatus",
]
