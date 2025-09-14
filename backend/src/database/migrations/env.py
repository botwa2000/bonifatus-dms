# backend/migrations/env.py
"""
Bonifatus DMS - Alembic Environment Configuration
Database migration environment setup for PostgreSQL
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.database.models import Base
from src.core.config import get_settings

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Load settings
try:
    settings = get_settings()
    database_url = settings.database.database_url
except Exception:
    # Fallback for cases where settings can't be loaded
    database_url = os.getenv(
        "DATABASE_URL", 
        "postgresql://bonifatus:password@localhost:5432/bonifatus_dms"
    )

# Override sqlalchemy.url from configuration
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,
            # Handle PostgreSQL-specific features
            render_item=render_item,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


def render_item(type_, obj, autogen_context):
    """Custom rendering for specific items."""
    if type_ == "type":
        # Handle custom PostgreSQL types
        if obj.name in ["user_tier", "document_status"]:
            return f"postgresql.ENUM{obj.enums!r}, name='{obj.name}'"
    
    return False


def process_revision_directives(context, revision, directives):
    """Process revision directives to add custom logic."""
    # Skip empty migrations
    if getattr(config.cmd_opts, 'autogenerate', False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            print("No changes detected, skipping migration generation.")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()