"""Initial database schema - all 30 tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-10-24 16:00:00.000000

This migration creates all database tables from SQLAlchemy models.
No dependencies on previous migrations - clean start.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables using SQLAlchemy models"""
    # Import models to ensure all tables are registered
    import sys
    sys.path.insert(0, '/app')
    from app.database.models import Base
    from app.database.connection import DatabaseManager

    # Get the connection from Alembic
    connection = op.get_bind()

    # Create all tables from models
    Base.metadata.create_all(bind=connection)

    print("✅ Created all 30 database tables")


def downgrade() -> None:
    """Drop all tables"""
    # Import models
    import sys
    sys.path.insert(0, '/app')
    from app.database.models import Base

    # Get the connection from Alembic
    connection = op.get_bind()

    # Drop all tables
    Base.metadata.drop_all(bind=connection)

    print("✅ Dropped all database tables")
