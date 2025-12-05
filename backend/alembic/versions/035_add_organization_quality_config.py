"""add organization quality config

Revision ID: 035_org_quality_config
Revises: 034_user_monthly_usage
Create Date: 2025-12-05 00:00:00

Add organization-specific quality check configuration values
to improve precision of organization entity extraction and
reduce false positives from all-caps form text
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '035_org_quality_config'
down_revision = '034_user_monthly_usage'
branch_labels = None
depends_on = None


def upgrade():
    # Add organization-specific quality config values
    op.execute("""
        INSERT INTO entity_quality_config (config_key, config_value, category, description, min_value, max_value)
        VALUES
        -- Organization-specific penalties (language-agnostic)
        ('org_allcaps_stopword_penalty', 0.15, 'entity_type', 'Penalty for all-caps single word that is stop word (e.g., PATIENT, TAG)', 0.05, 0.3),
        ('org_allcaps_single_penalty', 0.4, 'entity_type', 'Penalty for all-caps single word (not stop word)', 0.2, 0.6),
        ('org_allcaps_high_stopwords_penalty', 0.2, 'entity_type', 'Penalty for all-caps multi-word with >60% stop words', 0.1, 0.4),
        ('org_contains_field_label_penalty', 0.25, 'entity_type', 'Penalty when org contains field labels (extraction error)', 0.1, 0.5),
        ('org_dict_stopword_penalty', 0.3, 'entity_type', 'Penalty for dictionary word that is also stop word', 0.1, 0.5),
        ('org_too_short_penalty', 0.2, 'entity_type', 'Penalty for organization name < 3 characters', 0.1, 0.4),
        ('org_too_long_penalty', 0.3, 'entity_type', 'Penalty for organization name > 60 characters', 0.1, 0.5),

        -- Organization-specific bonuses (language-agnostic)
        ('org_multi_capital_bonus', 1.2, 'entity_type', 'Bonus for multiple capitalized words (e.g., Deutsche Bank)', 1.0, 1.4),
        ('org_proper_case_bonus', 1.1, 'entity_type', 'Bonus for proper case (not all-caps)', 1.0, 1.3),

        -- Organization confidence threshold
        ('confidence_threshold_organization', 0.85, 'threshold', 'Stricter confidence threshold for ORG entities (vs 0.75 general)', 0.75, 0.95),

        -- Keyword conversion threshold
        ('org_to_keyword_min_confidence', 0.50, 'threshold', 'Min confidence to convert rejected ORG to keyword', 0.3, 0.75)
    """)


def downgrade():
    # Remove organization-specific config values
    op.execute("""
        DELETE FROM entity_quality_config
        WHERE config_key IN (
            'org_allcaps_stopword_penalty',
            'org_allcaps_single_penalty',
            'org_allcaps_high_stopwords_penalty',
            'org_contains_field_label_penalty',
            'org_dict_stopword_penalty',
            'org_too_short_penalty',
            'org_too_long_penalty',
            'org_multi_capital_bonus',
            'org_proper_case_bonus',
            'confidence_threshold_organization',
            'org_to_keyword_min_confidence'
        )
    """)
