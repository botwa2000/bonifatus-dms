# Create this as: alembic/versions/XXXX_populate_initial_categories.py

"""Populate initial system categories

Revision ID: XXXX
Revises: 9ca3c4514de4
Create Date: 2024-09-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = 'populate_initial_categories'
down_revision = '9ca3c4514de4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insert initial system categories"""
    
    # Create categories table reference
    categories_table = sa.table('categories',
        sa.column('id', UUID),
        sa.column('name_en', sa.String),
        sa.column('name_de', sa.String),
        sa.column('name_ru', sa.String),
        sa.column('description_en', sa.Text),
        sa.column('description_de', sa.Text),
        sa.column('description_ru', sa.Text),
        sa.column('color_hex', sa.String),
        sa.column('icon_name', sa.String),
        sa.column('is_system', sa.Boolean),
        sa.column('user_id', UUID),
        sa.column('sort_order', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )
    
    # Initial system categories data
    categories_data = [
        {
            'id': str(uuid.uuid4()),
            'name_en': 'Insurance',
            'name_de': 'Versicherung',
            'name_ru': 'Страхование',
            'description_en': 'Insurance policies, claims, and related documents',
            'description_de': 'Versicherungspolicen, Schadensfälle und verwandte Dokumente',
            'description_ru': 'Страховые полисы, заявления и связанные документы',
            'color_hex': '#3B82F6',
            'icon_name': 'shield',
            'is_system': True,
            'user_id': None,
            'sort_order': 1,
            'is_active': True
        },
        {
            'id': str(uuid.uuid4()),
            'name_en': 'Legal',
            'name_de': 'Rechtlich',
            'name_ru': 'Юридические',
            'description_en': 'Legal documents, contracts, and agreements',
            'description_de': 'Rechtsdokumente, Verträge und Vereinbarungen',
            'description_ru': 'Юридические документы, договоры и соглашения',
            'color_hex': '#8B5CF6',
            'icon_name': 'scales',
            'is_system': True,
            'user_id': None,
            'sort_order': 2,
            'is_active': True
        },
        {
            'id': str(uuid.uuid4()),
            'name_en': 'Real Estate',
            'name_de': 'Immobilien',
            'name_ru': 'Недвижимость',
            'description_en': 'Property documents, deeds, and real estate transactions',
            'description_de': 'Immobiliendokumente, Urkunden und Immobilientransaktionen',
            'description_ru': 'Документы на недвижимость, сделки и операции',
            'color_hex': '#10B981',
            'icon_name': 'home',
            'is_system': True,
            'user_id': None,
            'sort_order': 3,
            'is_active': True
        },
        {
            'id': str(uuid.uuid4()),
            'name_en': 'Banking',
            'name_de': 'Banking',
            'name_ru': 'Банковские',
            'description_en': 'Bank statements, financial documents, and transactions',
            'description_de': 'Kontoauszüge, Finanzdokumente und Transaktionen',
            'description_ru': 'Банковские выписки, финансовые документы и операции',
            'color_hex': '#F59E0B',
            'icon_name': 'bank',
            'is_system': True,
            'user_id': None,
            'sort_order': 4,
            'is_active': True
        },
        {
            'id': str(uuid.uuid4()),
            'name_en': 'Other',
            'name_de': 'Sonstige',
            'name_ru': 'Прочие',
            'description_en': 'Miscellaneous documents and files',
            'description_de': 'Verschiedene Dokumente und Dateien',
            'description_ru': 'Разные документы и файлы',
            'color_hex': '#6B7280',
            'icon_name': 'folder',
            'is_system': True,
            'user_id': None,
            'sort_order': 5,
            'is_active': True
        }
    ]
    
    # Insert categories
    op.bulk_insert(categories_table, categories_data)


def downgrade() -> None:
    """Remove initial system categories"""
    op.execute("DELETE FROM categories WHERE is_system = true")