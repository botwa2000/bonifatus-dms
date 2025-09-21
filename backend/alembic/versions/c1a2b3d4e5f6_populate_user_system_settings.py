"""Populate user management system settings

Revision ID: c1a2b3d4e5f6
Revises: b01d5256f12f
Create Date: 2025-09-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'c1a2b3d4e5f6'
down_revision = 'b01d5256f12f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insert user management system settings"""
    
    now = datetime.utcnow()
    
    # Define system settings for user management
    system_settings = [
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'default_user_language',
            'setting_value': 'en',
            'data_type': 'string',
            'description': 'Default language for new users',
            'is_public': True,
            'category': 'user_preferences',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'default_timezone',
            'setting_value': 'UTC',
            'data_type': 'string',
            'description': 'Default timezone for new users',
            'is_public': True,
            'category': 'user_preferences',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'default_notifications_enabled',
            'setting_value': 'true',
            'data_type': 'boolean',
            'description': 'Default notification setting for new users',
            'is_public': True,
            'category': 'user_preferences',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'default_auto_categorization',
            'setting_value': 'true',
            'data_type': 'boolean',
            'description': 'Default AI auto-categorization setting for new users',
            'is_public': True,
            'category': 'user_preferences',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'supported_languages',
            'setting_value': 'en,de,ru',
            'data_type': 'string',
            'description': 'Comma-separated list of supported languages',
            'is_public': True,
            'category': 'application',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'data_retention_days',
            'setting_value': '30',
            'data_type': 'integer',
            'description': 'Number of days to retain user data after account deactivation',
            'is_public': False,
            'category': 'security',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'default_activity_limit',
            'setting_value': '10',
            'data_type': 'integer',
            'description': 'Default number of recent activities to show',
            'is_public': True,
            'category': 'user_interface',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'max_file_size_mb',
            'setting_value': '100',
            'data_type': 'integer',
            'description': 'Maximum file size for document uploads in MB',
            'is_public': True,
            'category': 'documents',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'storage_limit_free_tier_mb',
            'setting_value': '1024',
            'data_type': 'integer',
            'description': 'Storage limit for free tier users in MB',
            'is_public': True,
            'category': 'user_limits',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'setting_key': 'storage_limit_premium_tier_mb',
            'setting_value': '10240',
            'data_type': 'integer',
            'description': 'Storage limit for premium tier users in MB',
            'is_public': True,
            'category': 'user_limits',
            'created_at': now,
            'updated_at': now
        }
    ]
    
    # Insert system settings using raw SQL
    for setting in system_settings:
        op.execute(f"""
            INSERT INTO system_settings (
                id, setting_key, setting_value, data_type, description, 
                is_public, category, created_at, updated_at
            ) VALUES (
                '{setting['id']}', '{setting['setting_key']}', '{setting['setting_value']}', 
                '{setting['data_type']}', '{setting['description']}', {setting['is_public']}, 
                '{setting['category']}', '{setting['created_at']}', '{setting['updated_at']}'
            )
        """)


def downgrade() -> None:
    """Remove user management system settings"""
    settings_to_remove = [
        'default_user_language', 'default_timezone', 'default_notifications_enabled',
        'default_auto_categorization', 'supported_languages', 'data_retention_days',
        'default_activity_limit', 'max_file_size_mb', 'storage_limit_free_tier_mb',
        'storage_limit_premium_tier_mb'
    ]
    
    for setting_key in settings_to_remove:
        op.execute(f"DELETE FROM system_settings WHERE setting_key = '{setting_key}'")