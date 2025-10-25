"""Add unique constraint to category_keywords

Revision ID: 004_add_category_keyword_constraint
Revises: 003_add_file_hash
Create Date: 2025-01-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_category_keyword_constraint'
down_revision = '003_add_file_hash'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraint to prevent duplicate keywords per category+language"""
    # First, remove any existing duplicates (keep the one with highest weight)
    op.execute("""
        DELETE FROM category_keywords
        WHERE id NOT IN (
            SELECT DISTINCT ON (category_id, LOWER(keyword), language_code) id
            FROM category_keywords
            ORDER BY category_id, LOWER(keyword), language_code, weight DESC, created_at ASC
        )
    """)

    # Add unique constraint
    op.create_unique_constraint(
        'uq_category_keyword_lang',
        'category_keywords',
        ['category_id', sa.text('LOWER(keyword)'), 'language_code']
    )


def downgrade() -> None:
    """Remove unique constraint"""
    op.drop_constraint('uq_category_keyword_lang', 'category_keywords', type_='unique')
