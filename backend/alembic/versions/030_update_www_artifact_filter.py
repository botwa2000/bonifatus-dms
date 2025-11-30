"""update www artifact filter pattern

Revision ID: 030_update_www_filter
Revises: 029_entity_filtering_data
Create Date: 2025-11-30 00:00:00

Update ADDRESS_COMPONENT filtering pattern to catch both newlines AND spaces before www/http
This fixes entities like "64283 Darmstadt www" which have a space before "www"
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '030_update_www_filter'
down_revision = '029_entity_filtering_data'
branch_labels = None
depends_on = None


def upgrade():
    # Update the pattern for all 4 languages to match space OR newline before www/http
    for lang in ['de', 'en', 'ru', 'fr']:
        op.execute(f"""
            UPDATE entity_invalid_patterns
            SET regex_pattern = '(\\\\n|\\\\s)(www|http)',
                description = 'Addresses with web artifacts (space or newline)'
            WHERE language = '{lang}'
              AND entity_type = 'ADDRESS_COMPONENT'
              AND regex_pattern = '\\\\n(www|http)';
        """)


def downgrade():
    # Revert to original pattern (newline only)
    for lang in ['de', 'en', 'ru', 'fr']:
        op.execute(f"""
            UPDATE entity_invalid_patterns
            SET regex_pattern = '\\\\n(www|http)',
                description = 'Addresses with web artifacts'
            WHERE language = '{lang}'
              AND entity_type = 'ADDRESS_COMPONENT'
              AND regex_pattern = '(\\\\n|\\\\s)(www|http)';
        """)
