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
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
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
    """Run migrations in online mode with mandatory SSL encryption"""

    # Always require SSL for security, even for local connections
    # Local PostgreSQL: SSL enabled with self-signed certificate
    # Supabase/Cloud: SSL with CA-signed certificate
    connect_args = {
        "connect_timeout": 60,
        "application_name": "alembic_migrations",
        "sslmode": "require"
    }

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()