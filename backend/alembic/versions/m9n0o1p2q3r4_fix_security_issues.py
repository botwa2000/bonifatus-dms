# backend/alembic/versions/m9n0o1p2q3r4_fix_security_issues.py
"""fix security issues - rls and function search path

Revision ID: m9n0o1p2q3r4
Revises: l6m7n8o9p0q1
Create Date: 2025-10-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'm9n0o1p2q3r4'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None


def upgrade():
    # Fix Function Search Path - Recreate with SECURITY DEFINER and explicit search_path
    op.execute('DROP TRIGGER IF EXISTS documents_search_vector_trigger ON documents')
    op.execute('DROP FUNCTION IF EXISTS documents_search_vector_update()')
    
    op.execute("""
        CREATE OR REPLACE FUNCTION documents_search_vector_update() 
        RETURNS trigger 
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.extracted_text, '')), 'C');
            RETURN NEW;
        END
        $$;
    """)
    
    op.execute("""
        CREATE TRIGGER documents_search_vector_trigger
        BEFORE INSERT OR UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION documents_search_vector_update();
    """)
    
    # Enable RLS on all tables
    tables_to_secure = [
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
    
    for table_name in tables_to_secure:
        op.execute(f'ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY')
    
    # Create RLS Policies - User can only access their own data
    
    # audit_logs policies
    op.execute("""
        CREATE POLICY audit_logs_select_policy ON audit_logs
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id')::uuid);
    """)
    
    # document_languages policies  
    op.execute("""
        CREATE POLICY document_languages_all_policy ON document_languages
        FOR ALL
        USING (
            document_id IN (
                SELECT id FROM documents 
                WHERE user_id = current_setting('app.current_user_id')::uuid
            )
        );
    """)
    
    # keywords policies (shared resource, read-only for users)
    op.execute("""
        CREATE POLICY keywords_select_policy ON keywords
        FOR SELECT
        USING (true);
    """)
    
    op.execute("""
        CREATE POLICY keywords_insert_policy ON keywords
        FOR INSERT
        WITH CHECK (true);
    """)
    
    # document_keywords policies
    op.execute("""
        CREATE POLICY document_keywords_all_policy ON document_keywords
        FOR ALL
        USING (
            document_id IN (
                SELECT id FROM documents 
                WHERE user_id = current_setting('app.current_user_id')::uuid
            )
        );
    """)
    
    # ocr_results policies
    op.execute("""
        CREATE POLICY ocr_results_all_policy ON ocr_results
        FOR ALL
        USING (
            document_id IN (
                SELECT id FROM documents 
                WHERE user_id = current_setting('app.current_user_id')::uuid
            )
        );
    """)
    
    # document_entities policies
    op.execute("""
        CREATE POLICY document_entities_all_policy ON document_entities
        FOR ALL
        USING (
            document_id IN (
                SELECT id FROM documents 
                WHERE user_id = current_setting('app.current_user_id')::uuid
            )
        );
    """)
    
    # user_storage_quotas policies
    op.execute("""
        CREATE POLICY user_storage_quotas_all_policy ON user_storage_quotas
        FOR ALL
        USING (user_id = current_setting('app.current_user_id')::uuid);
    """)
    
    # ai_processing_queue policies
    op.execute("""
        CREATE POLICY ai_processing_queue_all_policy ON ai_processing_queue
        FOR ALL
        USING (
            document_id IN (
                SELECT id FROM documents 
                WHERE user_id = current_setting('app.current_user_id')::uuid
            )
        );
    """)
    
    # collections policies
    op.execute("""
        CREATE POLICY collections_all_policy ON collections
        FOR ALL
        USING (user_id = current_setting('app.current_user_id')::uuid);
    """)
    
    # collection_documents policies
    op.execute("""
        CREATE POLICY collection_documents_all_policy ON collection_documents
        FOR ALL
        USING (
            collection_id IN (
                SELECT id FROM collections 
                WHERE user_id = current_setting('app.current_user_id')::uuid
            )
        );
    """)
    
    # document_relationships policies
    op.execute("""
        CREATE POLICY document_relationships_all_policy ON document_relationships
        FOR ALL
        USING (
            parent_document_id IN (
                SELECT id FROM documents 
                WHERE user_id = current_setting('app.current_user_id')::uuid
            )
        );
    """)

def downgrade():
    # Remove RLS policies
    tables_to_unsecure = [
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
    
    for table_name in tables_to_unsecure:
        op.execute(f'DROP POLICY IF EXISTS {table_name}_all_policy ON {table_name}')
        op.execute(f'DROP POLICY IF EXISTS {table_name}_select_policy ON {table_name}')
        op.execute(f'DROP POLICY IF EXISTS {table_name}_insert_policy ON {table_name}')
        op.execute(f'ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY')
    
    # Revert function to original (without security settings)
    op.execute('DROP TRIGGER IF EXISTS documents_search_vector_trigger ON documents')
    op.execute('DROP FUNCTION IF EXISTS documents_search_vector_update()')
    
    op.execute("""
        CREATE OR REPLACE FUNCTION documents_search_vector_update() 
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.extracted_text, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER documents_search_vector_trigger
        BEFORE INSERT OR UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION documents_search_vector_update()
    """)