"""Populate initial system categories

Revision ID: ae442d52930d
Revises: 9ca3c4514de4
Create Date: 2024-09-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'ae442d52930d'
down_revision = '9ca3c4514de4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insert initial system categories"""
    
    now = datetime.utcnow()
    
    # Define initial categories with multilingual support
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
            'is_active': True,
            'created_at': now,
            'updated_at': now
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
            'is_active': True,
            'created_at': now,
            'updated_at': now
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
            'is_active': True,
            'created_at': now,
            'updated_at': now
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
            'is_active': True,
            'created_at': now,
            'updated_at': now
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
            'is_active': True,
            'created_at': now,
            'updated_at': now
        }
    ]
    
    # Insert categories using raw SQL
    for category in categories_data:
        op.execute(f"""
            INSERT INTO categories (
                id, name_en, name_de, name_ru, description_en, description_de, description_ru,
                color_hex, icon_name, is_system, user_id, sort_order, is_active, created_at, updated_at
            ) VALUES (
                '{category['id']}', '{category['name_en']}', '{category['name_de']}', '{category['name_ru']}',
                '{category['description_en']}', '{category['description_de']}', '{category['description_ru']}',
                '{category['color_hex']}', '{category['icon_name']}', {category['is_system']}, 
                NULL, {category['sort_order']}, {category['is_active']}, 
                '{category['created_at']}', '{category['updated_at']}'
            )
        """)


def downgrade() -> None:
    """Remove initial system categories"""
    op.execute("DELETE FROM categories WHERE is_system = true")