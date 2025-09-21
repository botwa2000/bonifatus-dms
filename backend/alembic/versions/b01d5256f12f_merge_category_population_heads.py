"""Merge category population heads

Revision ID: b01d5256f12f
Revises: ae442d52930d, populate_initial_categories
Create Date: 2025-09-21 10:31:45.563708

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b01d5256f12f'
down_revision = ('ae442d52930d', 'populate_initial_categories')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass