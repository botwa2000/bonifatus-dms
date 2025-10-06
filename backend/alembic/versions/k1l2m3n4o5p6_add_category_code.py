# backend/alembic/versions/k1l2m3n4o5p6_add_category_code.py
"""Add category_code field to categories table

Revision ID: k1l2m3n4o5p6
Revises: f1a2b3c4d5e6
Create Date: 2025-10-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'k1l2m3n4o5p6'
down_revision = 'j5e6f7g8h9i0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add category_code column
    op.add_column('categories', 
        sa.Column('category_code', sa.String(length=3), nullable=True)
    )
    
    # Update existing system categories with predefined codes
    op.execute("""
        UPDATE categories 
        SET category_code = CASE reference_key
            WHEN 'category.insurance' THEN 'INS'
            WHEN 'category.legal' THEN 'LEG'
            WHEN 'category.real_estate' THEN 'RES'
            WHEN 'category.banking' THEN 'BNK'
            WHEN 'category.medical' THEN 'MED'
            WHEN 'category.tax' THEN 'TAX'
            WHEN 'category.employment' THEN 'EMP'
            WHEN 'category.education' THEN 'EDU'
            WHEN 'category.other' THEN 'OTH'
            ELSE 'OTH'
        END
        WHERE is_system = true
    """)
    
    # For any existing user categories, assign sequential codes per user
    op.execute("""
        WITH user_categories AS (
            SELECT 
                id,
                user_id,
                ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as row_num
            FROM categories
            WHERE is_system = false AND user_id IS NOT NULL
        )
        UPDATE categories c
        SET category_code = 'C' || LPAD(uc.row_num::text, 2, '0')
        FROM user_categories uc
        WHERE c.id = uc.id
    """)
    
    # Make category_code NOT NULL after populating
    op.alter_column('categories', 'category_code', nullable=False)
    
    # Create index for faster lookups
    op.create_index('idx_category_code', 'categories', ['category_code'])
    
    # Create unique constraint per user (system categories share codes across users)
    op.create_index(
        'idx_category_user_code_unique', 
        'categories', 
        ['user_id', 'category_code'],
        unique=True,
        postgresql_where=sa.text('user_id IS NOT NULL')
    )


def downgrade() -> None:
    op.drop_index('idx_category_user_code_unique', table_name='categories')
    op.drop_index('idx_category_code', table_name='categories')
    op.drop_column('categories', 'category_code')