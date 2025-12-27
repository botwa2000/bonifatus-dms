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

# Load environment variables from .env file
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

from app.database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Read database URL from Docker secret or environment variable
from pathlib import Path

def read_secret(secret_name: str, fallback_env_var: str = None) -> str:
    """Read secret from Docker Swarm or environment variable"""
    app_env = os.getenv('APP_ENVIRONMENT', 'development')
    env_suffix = '_dev' if app_env == 'development' else '_prod'
    secret_path = Path(f"/run/secrets/{secret_name}{env_suffix}")

    if secret_path.exists():
        return secret_path.read_text().strip()

    if fallback_env_var and os.getenv(fallback_env_var):
        return os.getenv(fallback_env_var)

    raise ValueError(f"Secret '{secret_name}{env_suffix}' not found")

database_url = read_secret("database_url", "DATABASE_URL")
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