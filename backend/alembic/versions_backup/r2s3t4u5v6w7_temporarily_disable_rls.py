"""Temporarily disable RLS while implementing proper context handling

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2025-10-18 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'r2s3t4u5v6w7'
down_revision = 'q1r2s3t4u5v6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Temporarily disable RLS on all tables that have it enabled.

    The RLS policies require app.current_user_id to be set, but this causes
    authentication to fail because no user context exists during the auth flow.

    We'll re-enable RLS properly once we implement:
    1. Proper fallback for missing context (using current_setting with true flag)
    2. Bypass policies for system operations (authentication, seed data, etc.)
    """
    tables_with_rls = [
        'audit_logs',
        'document_languages',
        'document_keywords',
        'keywords',
        'ocr_results',
        'document_entities',
        'user_storage_quotas',
        'ai_processing_queue',
        'collection_documents',
        'collections',
        'document_relationships'
    ]

    for table_name in tables_with_rls:
        # Check if table exists before trying to drop policies
        op.execute(sa.text(f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = '{table_name}') THEN
                    -- Drop existing policies
                    DROP POLICY IF EXISTS {table_name}_all_policy ON {table_name};
                    DROP POLICY IF EXISTS {table_name}_select_policy ON {table_name};
                    DROP POLICY IF EXISTS {table_name}_insert_policy ON {table_name};

                    -- Disable RLS
                    ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;
                END IF;
            END $$;
        """))


def downgrade():
    """Re-enable RLS and policies"""
    # This downgrade would re-enable the broken RLS, so we skip it
    # A future migration will implement proper RLS with context handling
    pass
