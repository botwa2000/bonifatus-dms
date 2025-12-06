"""add libpostal address extraction

Revision ID: 038_libpostal_addresses
Revises: 037_expand_stopwords
Create Date: 2025-12-06 17:00:00

Add libpostal address extraction configuration and improve address entity recognition
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '038_libpostal_addresses'
down_revision = '037_expand_stopwords'
branch_labels = None
depends_on = None


def upgrade():
    # Add libpostal configuration for address extraction
    op.execute("""
        INSERT INTO entity_quality_config (config_key, config_value, category, description, min_value, max_value)
        VALUES
        -- libpostal feature flag and settings
        ('libpostal_enabled', 1.0, 'feature', 'Enable libpostal for high-accuracy address extraction (60+ countries)', 0.0, 1.0),
        ('address_confidence_threshold', 0.70, 'threshold', 'Minimum confidence for ADDRESS entities', 0.5, 0.9),
        ('address_libpostal_confidence', 0.90, 'algorithm', 'Base confidence for libpostal-extracted addresses', 0.75, 0.95),
        ('address_regex_confidence', 0.70, 'algorithm', 'Base confidence for regex-extracted addresses (fallback)', 0.6, 0.85),

        -- Address component validation
        ('address_min_components', 2.0, 'threshold', 'Minimum address components for valid address (e.g., street+number)', 1.0, 4.0),
        ('address_max_length', 200.0, 'threshold', 'Maximum address length in characters', 100.0, 300.0)
    """)


def downgrade():
    # Remove libpostal configuration
    op.execute("""
        DELETE FROM entity_quality_config
        WHERE config_key IN (
            'libpostal_enabled',
            'address_confidence_threshold',
            'address_libpostal_confidence',
            'address_regex_confidence',
            'address_min_components',
            'address_max_length'
        )
    """)
