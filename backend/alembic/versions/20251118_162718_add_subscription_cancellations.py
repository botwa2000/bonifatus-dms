"""add subscription cancellations

Revision ID: 20251118_162718
Revises: 20251118_154253
Create Date: 2025-11-18 16:27:18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251118_162718'
down_revision = '20251118_154253'
branch_labels = None
depends_on = None


def upgrade():
    # Create subscription_cancellations table
    op.create_table(
        'subscription_cancellations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cancellation_reason', sa.String(50), nullable=True),  # Reason code from system_settings
        sa.Column('feedback_text', sa.Text, nullable=True),  # Optional user feedback
        sa.Column('cancel_type', sa.String(20), nullable=False),  # immediate, at_period_end
        sa.Column('refund_requested', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('refund_issued', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('refund_amount_cents', sa.Integer, nullable=True),
        sa.Column('refund_currency', sa.String(3), nullable=True),
        sa.Column('stripe_refund_id', sa.String(100), nullable=True),
        sa.Column('subscription_age_days', sa.Integer, nullable=True),  # Age at cancellation for analytics
        sa.Column('canceled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('cancellation_metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # Create indexes
    op.create_index('idx_cancellation_subscription', 'subscription_cancellations', ['subscription_id'])
    op.create_index('idx_cancellation_user', 'subscription_cancellations', ['user_id'])
    op.create_index('idx_cancellation_reason', 'subscription_cancellations', ['cancellation_reason'])
    op.create_index('idx_cancellation_refund', 'subscription_cancellations', ['refund_issued'])
    op.create_index('idx_cancellation_date', 'subscription_cancellations', ['canceled_at'])

    # Add cancellation reasons to system_settings
    op.execute(r"""
        INSERT INTO system_settings (id, setting_key, setting_value, description, data_type, is_public, category)
        VALUES
        (
            gen_random_uuid(),
            'subscription_cancellation_reasons',
            $$[
                {"value": "too_expensive", "label_en": "Too expensive", "label_de": "Zu teuer", "label_ru": "Слишком дорого", "label_fr": "Trop cher"},
                {"value": "not_using", "label_en": "Not using it enough", "label_de": "Nicht genug genutzt", "label_ru": "Недостаточно используется", "label_fr": "Pas assez utilisé"},
                {"value": "missing_features", "label_en": "Missing features I need", "label_de": "Fehlende Funktionen", "label_ru": "Нужные функции отсутствуют", "label_fr": "Fonctionnalités manquantes"},
                {"value": "switching", "label_en": "Switching to another service", "label_de": "Wechsel zu anderem Dienst", "label_ru": "Переход на другой сервис", "label_fr": "Passage à un autre service"},
                {"value": "technical_issues", "label_en": "Technical issues", "label_de": "Technische Probleme", "label_ru": "Технические проблемы", "label_fr": "Problèmes techniques"},
                {"value": "customer_service", "label_en": "Customer service issues", "label_de": "Kundenservice-Probleme", "label_ru": "Проблемы с поддержкой", "label_fr": "Problèmes de service client"},
                {"value": "other", "label_en": "Other reason", "label_de": "Anderer Grund", "label_ru": "Другая причина", "label_fr": "Autre raison"}
            ]$$::jsonb,
            'Available cancellation reasons for subscription cancellations',
            'json',
            true,
            'billing'
        ),
        (
            gen_random_uuid(),
            'refund_policy_days',
            '14',
            'Number of days for full refund eligibility (money-back guarantee)',
            'integer',
            true,
            'billing'
        ),
        (
            gen_random_uuid(),
            'free_tier_features',
            $$[
                {"feature_en": "Upload up to 50 documents per month", "feature_de": "Bis zu 50 Dokumente pro Monat hochladen", "feature_ru": "Загрузка до 50 документов в месяц", "feature_fr": "Télécharger jusqu'à 50 documents par mois"},
                {"feature_en": "Basic document categorization", "feature_de": "Basis-Dokumentenkategorisierung", "feature_ru": "Базовая категоризация документов", "feature_fr": "Catégorisation de base des documents"},
                {"feature_en": "Access to your document history", "feature_de": "Zugriff auf Ihre Dokumenthistorie", "feature_ru": "Доступ к истории документов", "feature_fr": "Accès à l'historique des documents"}
            ]$$::jsonb,
            'Free tier features shown during cancellation and in cancellation emails',
            'json',
            true,
            'billing'
        )
    """)


def downgrade():
    op.drop_index('idx_cancellation_date', table_name='subscription_cancellations')
    op.drop_index('idx_cancellation_refund', table_name='subscription_cancellations')
    op.drop_index('idx_cancellation_reason', table_name='subscription_cancellations')
    op.drop_index('idx_cancellation_user', table_name='subscription_cancellations')
    op.drop_index('idx_cancellation_subscription', table_name='subscription_cancellations')
    op.drop_table('subscription_cancellations')
