-- database/schema.sql
-- Bonifatus DMS - PostgreSQL Database Schema
-- Complete schema for Supabase PostgreSQL database
-- Run this script to set up the database structure

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- User tiers enumeration
CREATE TYPE user_tier AS ENUM ('free', 'premium_trial', 'premium', 'admin');

-- Document status enumeration
CREATE TYPE document_status AS ENUM ('uploading', 'processing', 'ready', 'error', 'archived');

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    
    -- User tier and limits
    tier user_tier DEFAULT 'free' NOT NULL,
    document_count INTEGER DEFAULT 0 NOT NULL,
    monthly_uploads INTEGER DEFAULT 0 NOT NULL,
    storage_used_bytes INTEGER DEFAULT 0 NOT NULL,
    
    -- Trial management
    trial_started_at TIMESTAMPTZ,
    trial_ended_at TIMESTAMPTZ,
    
    -- Google Drive integration
    google_drive_token JSONB,
    google_drive_folder_id VARCHAR(255),
    google_drive_connected BOOLEAN DEFAULT FALSE NOT NULL,
    last_sync_at TIMESTAMPTZ,
    
    -- User preferences
    preferred_language VARCHAR(10) DEFAULT 'en' NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC' NOT NULL,
    theme VARCHAR(20) DEFAULT 'light' NOT NULL,
    
    -- Account status
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
    last_login_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Categories table
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Multilingual names and descriptions
    name_en VARCHAR(100) NOT NULL,
    name_de VARCHAR(100) NOT NULL,
    description_en TEXT,
    description_de TEXT,
    
    -- Visual and organizational
    color VARCHAR(7) DEFAULT '#6B7280' NOT NULL,
    icon VARCHAR(50),
    sort_order INTEGER DEFAULT 0 NOT NULL,
    
    -- Category properties
    is_system_category BOOLEAN DEFAULT FALSE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    keywords TEXT,
    
    -- Usage statistics
    document_count INTEGER DEFAULT 0 NOT NULL,
    last_used_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    
    -- File identification
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    google_drive_file_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- File metadata
    file_size_bytes INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_extension VARCHAR(10) NOT NULL,
    file_hash VARCHAR(64),
    
    -- Processing status
    status document_status DEFAULT 'uploading' NOT NULL,
    processing_error TEXT,
    
    -- Content and metadata
    title VARCHAR(255),
    description TEXT,
    extracted_text TEXT,
    extracted_keywords JSONB,
    language_detected VARCHAR(10),
    
    -- AI processing results
    ai_confidence_score FLOAT,
    ai_suggested_category INTEGER,
    ai_extracted_entities JSONB,
    
    -- User interaction
    user_keywords JSONB,
    notes TEXT,
    is_favorite BOOLEAN DEFAULT FALSE NOT NULL,
    view_count INTEGER DEFAULT 0 NOT NULL,
    last_viewed_at TIMESTAMPTZ,
    
    -- Google Drive sync
    google_drive_modified_time TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    sync_version INTEGER DEFAULT 1 NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- User settings table
CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Document processing preferences
    auto_categorization_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    ocr_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    ai_suggestions_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Notification preferences
    email_notifications BOOLEAN DEFAULT TRUE NOT NULL,
    processing_notifications BOOLEAN DEFAULT TRUE NOT NULL,
    weekly_summary BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Google Drive preferences
    sync_frequency_minutes INTEGER DEFAULT 60 NOT NULL,
    create_subfolder_structure BOOLEAN DEFAULT TRUE NOT NULL,
    backup_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- UI preferences
    documents_per_page INTEGER DEFAULT 20 NOT NULL,
    default_view_mode VARCHAR(20) DEFAULT 'grid' NOT NULL,
    show_processing_details BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Privacy and data preferences
    analytics_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    improve_ai_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    data_retention_days INTEGER DEFAULT 365 NOT NULL,
    
    -- Advanced settings
    max_upload_size_mb INTEGER DEFAULT 50 NOT NULL,
    concurrent_uploads INTEGER DEFAULT 3 NOT NULL,
    custom_categories_limit INTEGER DEFAULT 20 NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- System settings table
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    
    -- Tier limits
    free_tier_document_limit INTEGER DEFAULT 100 NOT NULL,
    premium_trial_document_limit INTEGER DEFAULT 500 NOT NULL,
    premium_document_limit INTEGER DEFAULT 0 NOT NULL,
    free_tier_monthly_uploads INTEGER DEFAULT 50 NOT NULL,
    premium_monthly_uploads INTEGER DEFAULT 0 NOT NULL,
    
    -- File processing limits
    max_file_size_mb INTEGER DEFAULT 50 NOT NULL,
    max_concurrent_processing INTEGER DEFAULT 5 NOT NULL,
    ocr_monthly_limit INTEGER DEFAULT 1000 NOT NULL,
    ai_processing_monthly_limit INTEGER DEFAULT 500 NOT NULL,
    
    -- Feature flags
    ocr_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    ai_categorization_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    google_drive_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    user_registration_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    maintenance_mode BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Localization
    default_language VARCHAR(10) DEFAULT 'en' NOT NULL,
    supported_languages JSONB DEFAULT '["en", "de"]' NOT NULL,
    
    -- API and integration settings
    google_api_rate_limit INTEGER DEFAULT 100 NOT NULL,
    session_timeout_minutes INTEGER DEFAULT 60 NOT NULL,
    
    -- Maintenance and monitoring
    database_backup_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    error_reporting_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    performance_monitoring_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Audit logs table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Event details
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(50),
    
    -- Request details
    ip_address INET,
    user_agent VARCHAR(500),
    request_id VARCHAR(100),
    
    -- Event data
    event_data JSONB,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Create indexes for performance

-- Users table indexes
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_google_id ON users(google_id);
CREATE INDEX idx_user_tier ON users(tier);
CREATE INDEX idx_user_active ON users(is_active);
CREATE INDEX idx_user_created ON users(created_at);

-- Categories table indexes
CREATE INDEX idx_category_user ON categories(user_id);
CREATE INDEX idx_category_system ON categories(is_system_category);
CREATE INDEX idx_category_active ON categories(is_active);
CREATE INDEX idx_category_sort ON categories(sort_order);

-- Documents table indexes
CREATE INDEX idx_document_user ON documents(user_id);
CREATE INDEX idx_document_category ON documents(category_id);
CREATE INDEX idx_document_status ON documents(status);
CREATE INDEX idx_document_google_id ON documents(google_drive_file_id);
CREATE INDEX idx_document_filename ON documents(filename);
CREATE INDEX idx_document_created ON documents(created_at);
CREATE INDEX idx_document_updated ON documents(updated_at);
CREATE INDEX idx_document_favorite ON documents(is_favorite);

-- Full-text search index
CREATE INDEX idx_document_text_search ON documents USING gin(to_tsvector('english', extracted_text));
CREATE INDEX idx_document_title_search ON documents USING gin(to_tsvector('english', title));

-- JSONB indexes
CREATE INDEX idx_document_keywords ON documents USING gin(extracted_keywords);
CREATE INDEX idx_document_user_keywords ON documents USING gin(user_keywords);

-- Audit logs indexes
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_audit_success ON audit_logs(success);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default system settings
INSERT INTO system_settings DEFAULT VALUES;

-- Insert default system categories
INSERT INTO categories (user_id, name_en, name_de, description_en, description_de, color, is_system_category, keywords) VALUES
    (NULL, 'Finance', 'Finanzen', 'Financial documents, invoices, receipts', 'Finanzielle Dokumente, Rechnungen, Quittungen', '#10B981', TRUE, 'invoice,receipt,bank,financial,money,payment,tax,accounting'),
    (NULL, 'Personal', 'Persönlich', 'Personal documents, certificates, ID', 'Persönliche Dokumente, Zertifikate, Ausweis', '#3B82F6', TRUE, 'personal,certificate,passport,id,identification,birth,marriage,medical'),
    (NULL, 'Business', 'Geschäft', 'Business documents, contracts, reports', 'Geschäftsdokumente, Verträge, Berichte', '#8B5CF6', TRUE, 'business,contract,report,presentation,meeting,proposal,strategy'),
    (NULL, 'Legal', 'Rechtlich', 'Legal documents, contracts, insurance', 'Rechtsdokumente, Verträge, Versicherung', '#EF4444', TRUE, 'legal,contract,insurance,law,court,agreement,terms,policy'),
    (NULL, 'Archive', 'Archiv', 'Archived documents, old files', 'Archivierte Dokumente, alte Dateien', '#6B7280', TRUE, 'archive,old,historical,reference,backup');

-- Create RLS (Row Level Security) policies for multi-tenancy
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Users can only access their own data
CREATE POLICY users_policy ON users
    FOR ALL USING (auth.uid()::text = google_id);

-- Categories: users can access their own + system categories
CREATE POLICY categories_policy ON categories
    FOR ALL USING (
        user_id = (SELECT id FROM users WHERE google_id = auth.uid()::text)
        OR is_system_category = TRUE
    );

-- Documents: users can only access their own documents
CREATE POLICY documents_policy ON documents
    FOR ALL USING (
        user_id = (SELECT id FROM users WHERE google_id = auth.uid()::text)
    );

-- User settings: users can only access their own settings
CREATE POLICY user_settings_policy ON user_settings
    FOR ALL USING (
        user_id = (SELECT id FROM users WHERE google_id = auth.uid()::text)
    );

-- Audit logs: users can only access their own audit logs
CREATE POLICY audit_logs_policy ON audit_logs
    FOR ALL USING (
        user_id = (SELECT id FROM users WHERE google_id = auth.uid()::text)
    );

-- Create view for document search with category names
CREATE VIEW document_search_view AS
SELECT 
    d.id,
    d.user_id,
    d.filename,
    d.original_filename,
    d.title,
    d.description,
    d.extracted_text,
    d.extracted_keywords,
    d.user_keywords,
    d.file_size_bytes,
    d.mime_type,
    d.status,
    d.is_favorite,
    d.view_count,
    d.created_at,
    d.updated_at,
    c.name_en as category_name_en,
    c.name_de as category_name_de,
    c.color as category_color,
    -- Full text search vector
    to_tsvector('english', 
        COALESCE(d.title, '') || ' ' ||
        COALESCE(d.filename, '') || ' ' ||
        COALESCE(d.extracted_text, '') || ' ' ||
        COALESCE(c.name_en, '') || ' ' ||
        COALESCE(c.name_de, '')
    ) as search_vector
FROM documents d
LEFT JOIN categories c ON d.category_id = c.id;

-- Create materialized view for analytics (refresh periodically)
CREATE MATERIALIZED VIEW user_analytics AS
SELECT 
    u.id as user_id,
    u.tier,
    u.created_at as user_since,
    COUNT(d.id) as total_documents,
    COUNT(CASE WHEN d.created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as documents_last_30_days,
    COUNT(CASE WHEN d.created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as documents_last_7_days,
    COALESCE(SUM(d.file_size_bytes), 0) as total_storage_bytes,
    COUNT(DISTINCT d.category_id) as categories_used,
    MAX(d.created_at) as last_upload,
    AVG(d.view_count) as avg_views_per_document
FROM users u
LEFT JOIN documents d ON u.id = d.user_id
GROUP BY u.id, u.tier, u.created_at;

-- Create index on the materialized view
CREATE UNIQUE INDEX idx_user_analytics_user_id ON user_analytics(user_id);

-- Function to refresh analytics (call periodically)
CREATE OR REPLACE FUNCTION refresh_user_analytics()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_analytics;
END;
$$ LANGUAGE plpgsql;