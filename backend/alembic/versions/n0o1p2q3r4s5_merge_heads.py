# backend/alembic/versions/n0o1p2q3r4s5_merge_heads.py
"""Merge all migration branches

Revision ID: n0o1p2q3r4s5
Revises: c1d2e3f4g5h6, m9n0o1p2q3r4, d3e4f5g6h7i8
Create Date: 2025-10-10 17:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'n0o1p2q3r4s5'
down_revision = ('c1d2e3f4g5h6', 'm9n0o1p2q3r4', 'd3e4f5g6h7i8')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass