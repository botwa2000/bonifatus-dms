# backend/alembic/versions/n0o1p2q3r4s5_merge_heads.py
"""Merge ML and security branches

Revision ID: n0o1p2q3r4s5
Revises: c1d2e3f4g5h6, m9n0o1p2q3r4
Create Date: 2025-10-10 17:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'n0o1p2q3r4s5'
down_revision = ('c1d2e3f4g5h6', 'm9n0o1p2q3r4')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No changes needed - this is a merge migration
    pass


def downgrade() -> None:
    # No changes needed - this is a merge migration
    pass