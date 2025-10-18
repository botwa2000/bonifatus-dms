# backend/alembic/env.py
"""
Alembic environment configuration for Bonifatus DMS
Database migration management with SQLAlchemy models
"""

import asyncio
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required for migrations")

config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)"""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Use the same connection parameters as the application (from app.database.connection)
    # This ensures SSL and other settings match production environment
    from sqlalchemy import create_engine

    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
        connect_args={
            "connect_timeout": 60,
            "options": "-c timezone=UTC",
            "sslmode": "require",  # Required for Supabase/PostgreSQL
            "application_name": "bonifatus-dms-migrations",
        },
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()