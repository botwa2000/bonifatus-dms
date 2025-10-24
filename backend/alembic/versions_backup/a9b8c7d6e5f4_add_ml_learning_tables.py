# backend/alembic/versions/a9b8c7d6e5f4_add_ml_learning_tables.py
"""Add ML learning tables for document analysis quality improvement

Revision ID: a9b8c7d6e5f4
Revises: l6m7n8o9p0q1
Create Date: 2025-10-10 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a9b8c7d6e5f4'
down_revision = 'l6m7n8o9p0q1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stop words for keyword filtering (language-agnostic architecture)
    op.create_table('stop_words',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('word', sa.String(length=100), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('word', 'language_code', name='uq_stop_word_language')
    )
    op.create_index('idx_stop_words_language', 'stop_words', ['language_code', 'is_active'])

    # Spelling corrections for OCR errors (learns over time)
    op.create_table('spelling_corrections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('incorrect_term', sa.String(length=200), nullable=False),
        sa.Column('correct_term', sa.String(length=200), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('incorrect_term', 'language_code', name='uq_spelling_correction')
    )
    op.create_index('idx_spelling_incorrect', 'spelling_corrections', ['incorrect_term', 'language_code'])
    op.create_index('idx_spelling_usage', 'spelling_corrections', ['usage_count', 'confidence_score'])

    # Category term weights (learned TF-IDF weights per language)
    op.create_table('category_term_weights',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term', sa.String(length=200), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('document_frequency', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('category_id', 'term', 'language_code', name='uq_category_term_lang')
    )
    op.create_index('idx_category_terms', 'category_term_weights', ['category_id', 'language_code', 'weight'])
    op.create_index('idx_category_term_lookup', 'category_term_weights', ['term', 'language_code'])

    # Keyword training data (tracks user acceptance/rejection)
    op.create_table('keyword_training_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('keyword', sa.String(length=200), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=True),
        sa.Column('was_accepted', sa.Boolean(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_keyword_training_acceptance', 'keyword_training_data', ['keyword', 'language_code', 'was_accepted'])
    op.create_index('idx_keyword_training_score', 'keyword_training_data', ['language_code', 'was_accepted', 'relevance_score'])

    # Category training data (tracks document → category mappings)
    op.create_table('category_training_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('suggested_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actual_category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('was_correct', sa.Boolean(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('text_sample', sa.Text(), nullable=True),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['suggested_category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['actual_category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_category_training_actual', 'category_training_data', ['actual_category_id', 'was_correct'])
    op.create_index('idx_category_training_lang', 'category_training_data', ['language_code', 'was_correct'])

    # N-gram patterns for multi-word keyword extraction
    op.create_table('ngram_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('pattern', sa.String(length=500), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('importance_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pattern', 'language_code', name='uq_ngram_pattern_lang')
    )
    op.create_index('idx_ngram_language', 'ngram_patterns', ['language_code', 'is_active', 'importance_score'])


def downgrade() -> None:
    op.drop_table('ngram_patterns')
    op.drop_table('category_training_data')
    op.drop_table('keyword_training_data')
    op.drop_table('category_term_weights')
    op.drop_table('spelling_corrections')
    op.drop_table('stop_words')