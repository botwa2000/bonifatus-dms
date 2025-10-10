# backend/alembic/versions/d3e4f5g6h7i8_add_language_detection_patterns.py
"""Add language detection patterns table for scalable multilingual support

Revision ID: d3e4f5g6h7i8
Revises: c1d2e3f4g5h6
Create Date: 2025-10-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
import uuid
from datetime import datetime, timezone

revision = 'd3e4f5g6h7i8'
down_revision = 'm9n0o1p2q3r4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Language detection patterns table
    op.create_table('language_detection_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('pattern', sa.String(length=100), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),  # 'common_word', 'character_set', 'grammar'
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('language_code', 'pattern', name='uq_lang_pattern')
    )
    op.create_index('idx_lang_detect_code', 'language_detection_patterns', ['language_code', 'is_active', 'weight'])
    
    # Populate initial language detection patterns
    conn = op.get_bind()
    now = datetime.now(timezone.utc)
    
    # English patterns
    english_patterns = [
        # Most common English words
        ('the', 'common_word', 3.0),
        ('and', 'common_word', 2.5),
        ('for', 'common_word', 2.0),
        ('that', 'common_word', 2.0),
        ('with', 'common_word', 2.0),
        ('from', 'common_word', 1.8),
        ('this', 'common_word', 1.8),
        ('have', 'common_word', 1.5),
        ('are', 'common_word', 1.5),
        ('was', 'common_word', 1.5),
        ('were', 'common_word', 1.5),
        ('will', 'common_word', 1.5),
        ('been', 'common_word', 1.3),
        ('can', 'common_word', 1.3),
        ('has', 'common_word', 1.3),
        ('not', 'common_word', 1.3),
        ('but', 'common_word', 1.2),
        ('all', 'common_word', 1.2),
        ('which', 'common_word', 1.2),
        ('their', 'common_word', 1.2),
    ]
    
    # German patterns
    german_patterns = [
        # Most common German words
        ('der', 'common_word', 3.0),
        ('die', 'common_word', 3.0),
        ('das', 'common_word', 3.0),
        ('und', 'common_word', 2.8),
        ('den', 'common_word', 2.5),
        ('dem', 'common_word', 2.5),
        ('des', 'common_word', 2.5),
        ('für', 'common_word', 2.3),
        ('mit', 'common_word', 2.0),
        ('ist', 'common_word', 2.0),
        ('auf', 'common_word', 1.8),
        ('von', 'common_word', 1.8),
        ('zu', 'common_word', 1.8),
        ('ein', 'common_word', 1.8),
        ('eine', 'common_word', 1.8),
        ('auch', 'common_word', 1.5),
        ('sich', 'common_word', 1.5),
        ('nicht', 'common_word', 1.5),
        ('wird', 'common_word', 1.5),
        ('bei', 'common_word', 1.3),
        # German-specific characters
        ('ä', 'character_set', 2.0),
        ('ö', 'character_set', 2.0),
        ('ü', 'character_set', 2.0),
        ('ß', 'character_set', 2.5),
    ]
    
    # Russian patterns
    russian_patterns = [
        # Most common Russian words
        ('и', 'common_word', 3.0),
        ('в', 'common_word', 3.0),
        ('не', 'common_word', 2.8),
        ('на', 'common_word', 2.5),
        ('что', 'common_word', 2.3),
        ('с', 'common_word', 2.3),
        ('по', 'common_word', 2.0),
        ('как', 'common_word', 2.0),
        ('для', 'common_word', 2.0),
        ('это', 'common_word', 1.8),
        ('от', 'common_word', 1.8),
        ('из', 'common_word', 1.8),
        ('при', 'common_word', 1.5),
        ('или', 'common_word', 1.5),
        ('его', 'common_word', 1.5),
        ('так', 'common_word', 1.5),
        ('был', 'common_word', 1.3),
        ('быть', 'common_word', 1.3),
        ('если', 'common_word', 1.3),
        ('все', 'common_word', 1.3),
        # Cyrillic character detection
        ('а', 'character_set', 1.5),
        ('е', 'character_set', 1.5),
        ('о', 'character_set', 1.5),
        ('я', 'character_set', 1.5),
        ('ё', 'character_set', 2.0),
        ('ж', 'character_set', 2.0),
        ('ш', 'character_set', 2.0),
        ('щ', 'character_set', 2.0),
        ('ы', 'character_set', 2.0),
        ('ю', 'character_set', 2.0),
    ]
    
    # Insert English patterns
    for pattern, ptype, weight in english_patterns:
        conn.execute(
            text("""
                INSERT INTO language_detection_patterns 
                (id, language_code, pattern, pattern_type, weight, is_active, created_at, updated_at)
                VALUES (:id, 'en', :pattern, :ptype, :weight, true, :created, :updated)
            """),
            {
                'id': str(uuid.uuid4()),
                'pattern': pattern,
                'ptype': ptype,
                'weight': weight,
                'created': now,
                'updated': now
            }
        )
    
    # Insert German patterns
    for pattern, ptype, weight in german_patterns:
        conn.execute(
            text("""
                INSERT INTO language_detection_patterns 
                (id, language_code, pattern, pattern_type, weight, is_active, created_at, updated_at)
                VALUES (:id, 'de', :pattern, :ptype, :weight, true, :created, :updated)
            """),
            {
                'id': str(uuid.uuid4()),
                'pattern': pattern,
                'ptype': ptype,
                'weight': weight,
                'created': now,
                'updated': now
            }
        )
    
    # Insert Russian patterns
    for pattern, ptype, weight in russian_patterns:
        conn.execute(
            text("""
                INSERT INTO language_detection_patterns 
                (id, language_code, pattern, pattern_type, weight, is_active, created_at, updated_at)
                VALUES (:id, 'ru', :pattern, :ptype, :weight, true, :created, :updated)
            """),
            {
                'id': str(uuid.uuid4()),
                'pattern': pattern,
                'ptype': ptype,
                'weight': weight,
                'created': now,
                'updated': now
            }
        )
    
    # Add system setting for fallback language
    conn.execute(
        text("""
            INSERT INTO system_settings (id, setting_key, setting_value, data_type, description, is_public, category, created_at, updated_at)
            VALUES (:id, 'fallback_language', 'en', 'string', 'Fallback language when detection fails', false, 'ml', :created, :updated)
        """),
        {
            'id': str(uuid.uuid4()),
            'created': now,
            'updated': now
        }
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DELETE FROM system_settings WHERE setting_key = 'fallback_language'"))
    op.drop_table('language_detection_patterns')