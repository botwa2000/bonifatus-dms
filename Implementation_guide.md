Bonifatus DMS - Implementation Status & Roadmap
Document Version: 6.0
Date: October 4, 2025
Status: Development Phase - Database Architecture Enhancement

Current Implementation Status
Infrastructure (Operational)
Cloud Services:

Google Cloud Run: Backend and frontend deployed
Supabase PostgreSQL: Database operational
GitHub Actions: CI/CD pipeline functional
Domain: bonidoc.com (mapped and SSL active)
API endpoint: api.bonidoc.com

Deployment Status:

Last successful deployment: Frontend build failed (TypeScript errors)
Migration status: Cycle detected in revision chain
Production accessibility: Frontend showing error page

Completed Components
Backend (80% Complete):

✓ FastAPI application structure
✓ Google OAuth authentication + JWT
✓ User management API
✓ Settings API (system + localization)
✓ Document upload API (basic)
✓ Categories API (structure defined, needs migration fix)
✓ Middleware (auth, CORS, logging)
✓ Database connection pooling
✓ Audit logging framework

Frontend (70% Complete):

✓ Next.js 14 application structure
✓ Authentication flow (Google OAuth)
✓ Dashboard layout
✓ Categories page UI (needs backend integration)
✓ Responsive design system
✓ API client abstraction
✓ Error handling framework

Database (60% Complete):

✓ Core tables: users, system_settings, localization_strings
✓ Audit logging table
⚠ Categories: Schema defined but migration broken
⚠ Documents: Basic structure, missing enhancements
✗ Keywords management: Missing
✗ Entities extraction: Missing
✗ AI processing queue: Missing
✗ Document relationships: Missing
✗ Sharing system: Missing

Critical Blockers
Immediate Issues:

Migration Cycle Error: Circular dependencies in alembic revisions
TypeScript Build Failure: Frontend Category type mismatch
Incomplete Schema: Missing 11+ critical tables for core functionality

Architecture Gaps:

Keywords stored as JSON (not searchable)
No AI processing queue (can't scale async tasks)
No entity extraction tables (can't search structured data)
No storage quota enforcement (tier limits not enforced)
No sharing/collaboration infrastructure


Phase 1: Fix Critical Blockers (Days 1-2)
1.1 Clean Migration Structure
Objective: Single, clean migration history for production deployment
Tasks:
Step 1: Delete problematic migration files
bashcd backend/alembic/versions
rm -f ae442d52930d_*.py
rm -f b01d5256f12f_*.py
rm -f b7f3e21a4d5c_*.py
rm -f c1a2b3d4e5f6_*.py
rm -f d2c3e4f5g6h7_*.py
rm -f 5c448b08fbc7_*.py
rm -f 9ca3c4514de4_*.py
Step 2: Create comprehensive initial migration

File: 0283144cf0fb_initial_database_schema.py
Include: All 20+ tables (existing + new)
Structure: Proper foreign keys, indexes, constraints

Step 3: Create single data population migration

File: populate_initial_data.py
Include: System settings, localization strings, default categories with translations
No circular dependencies

Step 4: Test migration locally
bash# Set DATABASE_URL environment variable
export DATABASE_URL="postgresql://..."

# Run migrations
cd backend
alembic upgrade head

# Verify all tables created
psql $DATABASE_URL -c "\dt"
1.2 Fix Frontend Type Errors
File: frontend/src/services/category.service.ts
Ensure proper export:
typescriptexport interface Category {
  id: string
  reference_key: string
  name: string  // NOT name_en
  description?: string  // NOT description_en
  color_hex: string
  icon_name: string
  sort_order: number
  is_active: boolean
  is_system: boolean
  user_id?: string
  documents_count?: number
  created_at: string
  updated_at: string
}
File: frontend/src/app/categories/page.tsx
Import correctly:
typescriptimport { 
  categoryService, 
  type Category, 
  type CategoryCreateData, 
  type CategoryUpdateData 
} from '@/services/category.service'
Remove any local Category type definitions.
1.3 Commit and Deploy
bashgit add .
git commit -m "fix: clean migration structure and resolve type errors

- Consolidate migrations into single clean history
- Add 11 new critical tables for full functionality
- Fix Category type definition (name vs name_en)
- Implement dynamic multilingual architecture
- Add keywords, entities, AI queue, sharing tables"

git push origin main
Expected Result: Clean deployment, categories API functional

Phase 2: Enhanced Database Schema (Days 3-5)
2.1 New Tables Implementation
Priority 1 - Core Functionality (Implement First):
A. Keywords Management
sqlkeywords (11 columns)
  - Normalized keyword storage
  - Language-aware
  - Usage tracking

document_keywords (9 columns)
  - Many-to-many link
  - Relevance scoring
  - Extraction method tracking
B. AI Processing Queue
sqlai_processing_queue (20 columns)
  - Task management
  - Retry logic
  - Cost tracking
  - Provider selection
C. User Storage Quotas
sqluser_storage_quotas (9 columns)
  - Tier-based limits
  - Real-time usage tracking
  - Enforcement logic
D. Entity Extraction
sqldocument_entities (15 columns)
  - Structured data extraction
  - Person, organization, date, amount detection
  - Position tracking for highlighting
E. OCR Results Archive
sqlocr_results (11 columns)
  - Provider comparison
  - Quality tracking
  - Cost analysis
  - Reprocessing support
Priority 2 - Collaboration (Implement Next):
F. Collections (Folders)
sqlcollections (11 columns)
  - Nested folder structure
  - Smart collections (rule-based)

collection_documents (4 columns)
  - Document grouping
G. Document Relationships
sqldocument_relationships (7 columns)
  - Amendment chains
  - Version history
  - Attachments
H. Sharing System
sqldocument_shares (15 columns)
  - Email-based sharing
  - Token-based access
  - Permission levels
  - Expiration
Priority 3 - User Experience:
I. Tags System
sqltags (6 columns)
  - User-defined labels

document_tags (3 columns)
  - Flexible categorization
J. Notifications
sqlnotifications (14 columns)
  - Processing alerts
  - Share notifications
  - Storage warnings
K. Search History
sqlsearch_history (11 columns)
  - ML training data
  - Analytics
  - Query optimization
2.2 Existing Table Enhancements
Documents Table - Add Columns:
sqlALTER TABLE documents ADD COLUMN file_hash VARCHAR(64);
ALTER TABLE documents ADD COLUMN original_filename VARCHAR(255);
ALTER TABLE documents ADD COLUMN thumbnail_url TEXT;
ALTER TABLE documents ADD COLUMN preview_url TEXT;
ALTER TABLE documents ADD COLUMN page_count INT;
ALTER TABLE documents ADD COLUMN document_type VARCHAR(50);
ALTER TABLE documents ADD COLUMN is_duplicate BOOLEAN DEFAULT false;
ALTER TABLE documents ADD COLUMN duplicate_of_document_id UUID;
ALTER TABLE documents ADD COLUMN web_view_link TEXT;
ALTER TABLE documents ADD COLUMN download_count INT DEFAULT 0;
ALTER TABLE documents ADD COLUMN last_accessed_at TIMESTAMP;
ALTER TABLE documents ADD COLUMN search_vector tsvector;

CREATE INDEX idx_document_file_hash ON documents(file_hash);
CREATE INDEX idx_document_type ON documents(document_type);
CREATE INDEX idx_documents_search ON documents USING gin(search_vector);
Users Table - Add Columns:
sqlALTER TABLE users ADD COLUMN preferred_language VARCHAR(5) DEFAULT 'en';
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC';
ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN onboarding_completed_at TIMESTAMP;
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP;
ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN last_activity_at TIMESTAMP;

CREATE INDEX idx_user_preferred_language ON users(preferred_language);
CREATE INDEX idx_user_last_activity ON users(last_activity_at);
2.3 Migration Strategy
Create separate migrations for each priority group:
0283144cf0fb_initial_database_schema.py (base tables)
  ↓
populate_initial_data.py (system settings, localization, categories)
  ↓
add_priority1_tables.py (keywords, ai_queue, quotas, entities, ocr)
  ↓
add_priority2_tables.py (collections, relationships, sharing)
  ↓
add_priority3_tables.py (tags, notifications, search)
  ↓
enhance_existing_tables.py (documents + users enhancements)
Rationale: Incremental deployment reduces risk, allows testing between phases

Phase 3: Service Layer Implementation (Days 6-10)
3.1 Keywords Service
File: backend/app/services/keyword_service.py
Core Methods:

extract_keywords(document_id, text, language) - TF-IDF + AI extraction
normalize_keyword(keyword) - Stemming, lowercase
link_keyword_to_document(document_id, keyword, relevance, method) - Association
get_document_keywords(document_id) - Retrieve with relevance scores
get_trending_keywords(user_id, limit) - Most used keywords
suggest_keywords(text) - AI-powered suggestions

3.2 AI Processing Service
File: backend/app/services/ai_processing_service.py
Core Methods:

enqueue_task(document_id, task_type, priority) - Add to queue
process_task(task_id) - Execute AI operation
retry_failed_task(task_id) - Reprocess failures
get_queue_status(user_id) - User's pending tasks
estimate_processing_time(task_type) - Queue depth analysis
track_cost(task_id, tokens, cost) - Usage monitoring

Supported Tasks:

categorize - AI-powered category suggestion
extract_keywords - Keyword extraction
extract_entities - Named entity recognition
detect_language - Language identification
summarize - Document summarization
extract_dates - Important dates extraction

3.3 Entity Extraction Service
File: backend/app/services/entity_extraction_service.py
Core Methods:

extract_entities(document_id, text, language) - NER processing
normalize_entity(entity_type, value) - Standardize formats
get_document_entities(document_id, entity_type) - Filter by type
search_by_entity(user_id, entity_value) - Find documents containing entity
extract_financial_data(text) - Amounts, IBANs, currencies
extract_dates(text) - Date extraction with context

Entity Types:

person, organization, location
date, amount, currency
email, phone, iban
contract_number, invoice_number
address, postal_code

3.4 Storage Quota Service
File: backend/app/services/storage_quota_service.py
Core Methods:

check_quota(user_id, file_size) - Pre-upload validation
calculate_usage(user_id) - Real-time calculation
enforce_quota(user_id) - Block if exceeded
send_quota_warning(user_id, percentage) - Notifications at 80%, 90%, 95%
get_tier_limits(tier) - Quota by tier
upgrade_tier(user_id, new_tier) - Tier management

Tier Limits:
pythonTIER_LIMITS = {
    'free': 1_073_741_824,      # 1 GB
    'premium': 10_737_418_240,   # 10 GB
    'enterprise': 107_374_182_400 # 100 GB
}
3.5 Sharing Service
File: backend/app/services/sharing_service.py
Core Methods:

create_share(document_id, email, permission_level, expires_at) - Share document
create_public_link(document_id, expires_at) - Generate public URL
revoke_share(share_id) - Remove access
update_permissions(share_id, new_permission) - Modify access level
track_access(share_token) - Analytics
get_shared_with_me(user_id) - Incoming shares
get_my_shares(user_id) - Outgoing shares


Phase 4: Document Processing Pipeline (Days 11-15)
4.1 Enhanced Upload Handler
File: backend/app/api/documents.py
Process Flow:
python@router.post("/upload")
async def upload_document(file: UploadFile, user: User):
    # 1. Validate file type and size
    # 2. Check storage quota
    # 3. Calculate file hash (deduplication)
    # 4. Upload to Google Drive
    # 5. Create document record (status: uploaded)
    # 6. Enqueue OCR task
    # 7. Return document_id immediately
4.2 OCR Processing Worker
File: backend/app/workers/ocr_worker.py
Process Flow:
pythonasync def process_ocr(document_id):
    # 1. Fetch document from database
    # 2. Download from Google Drive
    # 3. Detect optimal OCR provider (PDF vs image)
    # 4. Process each page → ocr_results table
    # 5. Combine full text → documents.extracted_text
    # 6. Calculate confidence score
    # 7. Enqueue language detection task
    # 8. Update document status
OCR Provider Selection Logic:
pythondef select_ocr_provider(mime_type, page_count):
    if mime_type == 'application/pdf' and page_count > 10:
        return 'google_vision'  # Better for bulk
    elif 'image' in mime_type:
        return 'tesseract'  # Cost-effective for images
    else:
        return 'google_vision'  # Default
4.3 Language Detection Worker
File: backend/app/workers/language_worker.py
Process Flow:
pythonasync def detect_languages(document_id):
    # 1. Analyze extracted text
    # 2. Detect all languages with confidence
    # 3. Insert → document_languages table
    # 4. Determine primary language (highest confidence)
    # 5. Update documents.primary_language
    # 6. Enqueue keyword extraction (language-aware)
    # 7. Enqueue entity extraction (language-aware)
4.4 Keyword Extraction Worker
File: backend/app/workers/keyword_worker.py
Process Flow:
pythonasync def extract_keywords(document_id):
    # 1. Get document text and primary language
    # 2. TF-IDF extraction (fast, baseline)
    # 3. AI extraction (GPT-4 or Claude) (slow, high quality)
    # 4. Merge results with weighted scoring
    # 5. Normalize keywords
    # 6. Insert → keywords + document_keywords tables
    # 7. Update document status
Extraction Methods:

TF-IDF: Fast, language-agnostic, decent quality
spaCy: Medium speed, good for entities
OpenAI API: Slow, expensive, best quality
Claude API: Slow, expensive, context-aware

4.5 Entity Extraction Worker
File: backend/app/workers/entity_worker.py
Process Flow:
pythonasync def extract_entities(document_id):
    # 1. Get document text and language
    # 2. Run NER (Named Entity Recognition)
    # 3. Extract financial data (amounts, IBANs)
    # 4. Extract dates with context
    # 5. Normalize entities
    # 6. Insert → document_entities table
    # 7. Enqueue AI categorization task
4.6 AI Categorization Worker
File: backend/app/workers/categorization_worker.py
Process Flow:
pythonasync def suggest_category(document_id):
    # 1. Get document text, keywords, entities
    # 2. Get user's existing categories
    # 3. Build AI prompt with context
    # 4. Call AI API (GPT-4 or Claude)
    # 5. Parse response → category_id + confidence
    # 6. Store → document_languages.ai_category_suggestion
    # 7. If confidence > 0.8, auto-assign category
    # 8. Otherwise, notify user for review
    # 9. Update document status: completed
AI Prompt Template:
You are categorizing a document for a user.

Document text (excerpt): {text[:1000]}
Extracted keywords: {keywords}
Detected entities: {entities}
Primary language: {language}

Available categories:
{categories_list}

Suggest the most appropriate category and explain why.
Respond in JSON: {"category_id": "...", "confidence": 0.0-1.0, "reasoning": "..."}

Phase 5: Frontend Integration (Days 16-20)
5.1 Keywords Management UI
File: frontend/src/app/documents/[id]/keywords.tsx
Features:

Display extracted keywords with relevance bars
Add/remove keywords manually
Keyword-based search
Trending keywords widget

5.2 Entity Viewer
File: frontend/src/app/documents/[id]/entities.tsx
Features:

Entity type filtering (persons, dates, amounts)
Click to search all documents with same entity
Entity editing (correct OCR mistakes)
Entity export (CSV)

5.3 Processing Queue Dashboard
File: frontend/src/app/processing/page.tsx
Features:

Real-time queue status
Task progress indicators
Failed task retry buttons
Cost tracking per user
Processing time estimates

5.4 Sharing Interface
File: frontend/src/app/documents/[id]/share.tsx
Features:

Share via email with permission levels
Generate public links
Expiration date picker
Revoke access buttons
Access analytics (who viewed, when)

5.5 Collections (Folders)
File: frontend/src/app/collections/page.tsx
Features:

Nested folder tree view
Drag-and-drop documents into folders
Smart collections with rule builder
Bulk operations on folders


Phase 6: Search & Analytics (Days 21-25)
6.1 Advanced Search Implementation
File: backend/app/api/search.py
Search Types:
Full-Text Search:
sqlSELECT * FROM documents 
WHERE search_vector @@ to_tsquery('english', 'insurance & policy')
ORDER BY ts_rank(search_vector, to_tsquery('english', 'insurance & policy')) DESC
Keyword Search:
sqlSELECT d.* FROM documents d
JOIN document_keywords dk ON d.id = dk.document_id
JOIN keywords k ON dk.keyword_id = k.id
WHERE k.normalized_form IN ('insurance', 'policy')
ORDER BY dk.relevance_score DESC
Entity Search:
sqlSELECT d.* FROM documents d
JOIN document_entities de ON d.id = de.document_id
WHERE de.entity_type = 'organization' 
  AND de.normalized_value ILIKE '%Allianz%'
Date Range Search:
sqlSELECT d.* FROM documents d
JOIN document_entities de ON d.id = de.document_id
WHERE de.entity_type = 'date'
  AND de.normalized_value::date BETWEEN '2024-01-01' AND '2024-12-31'
Combined Search:
sql-- Full-text + category + date range + language
SELECT DISTINCT d.* FROM documents d
WHERE d.search_vector @@ to_tsquery(?)
  AND d.category_id = ?
  AND d.created_at BETWEEN ? AND ?
  AND d.primary_language = ?
ORDER BY d.created_at DESC
6.2 Search Analytics
File: backend/app/services/analytics_service.py
Metrics to Track:

Popular search queries
No-results queries (for improving search)
Click-through rates by position
Average search duration
Most clicked documents
Search refinement patterns

Use Cases:

Improve search relevance
Suggest better keywords
Identify missing documents
Optimize indexing


Phase 7: Testing & Optimization (Days 26-30)
7.1 Unit Tests
Coverage Target: >90% for business logic
Test Files:

backend/tests/test_keyword_service.py
backend/tests/test_ai_processing_service.py
backend/tests/test_entity_extraction_service.py
backend/tests/test_storage_quota_service.py
backend/tests/test_sharing_service.py

7.2 Integration Tests
Test Scenarios:

Complete upload → OCR → extraction → categorization pipeline
Category CRUD with translations
Sharing workflow with permissions
Storage quota enforcement
Search with various filters

7.3 Performance Optimization
Database:

Query analysis with EXPLAIN ANALYZE
Index optimization
Connection pool tuning
Materialized views for expensive queries

API:

Response caching (Redis)
Pagination for large results
Async task offloading
Rate limiting per tier

Frontend:

Code splitting
Image optimization
Lazy loading
Service worker for offline support

7.4 Load Testing
Tools: k6, Locust, or Artillery
Scenarios:

100 concurrent users uploading documents
1000 concurrent search queries
AI processing queue under load
Database query performance at scale


Implementation Priorities
Must Have (MVP - Weeks 1-4)

Clean migrations with dynamic multilingual categories
Keywords + document_keywords tables
AI processing queue
Basic entity extraction
Storage quota enforcement
Enhanced document upload pipeline
Search by keywords and entities

Should Have (Phase 2 - Weeks 5-8)

Collections (folders)
Document relationships
Sharing system
Notifications
Tags
OCR results archive
Processing queue dashboard
Advanced search UI

Nice to Have (Phase 3 - Weeks 9-12)

Search analytics
ML-powered categorization improvement
Duplicate detection
Document versioning
Bulk operations
Export functionality
API rate limiting per tier
Two-factor authentication


Next Immediate Steps (This Week)
Day 1: Fix Blockers

 Clean alembic migration files
 Create comprehensive initial migration (20+ tables)
 Fix Category TypeScript types
 Test migration locally
 Commit and deploy

Day 2: Verify Deployment

 Monitor GitHub Actions deployment
 Verify database schema in production
 Test categories API endpoints
 Test frontend categories page
 Document any issues

Day 3: Priority 1 Tables

 Create migration for keywords tables
 Create migration for ai_processing_queue
 Create migration for user_storage_quotas
 Create migration for document_entities
 Create migration for ocr_results
 Test migrations locally
 Deploy to production

Day 4: Service Layer - Keywords

 Implement KeywordService
 API endpoints for keyword management
 Frontend keyword viewer component
 Test keyword extraction
 Document API

Day 5: Service Layer - AI Queue

 Implement AIProcessingService
 Create worker framework
 Implement OCR worker
 Implement language detection worker
 Test async processing


Success Metrics
Technical Metrics

Migration success rate: 100%
Test coverage: >90%
API response time: <200ms (p95)
Search response time: <500ms (p95)
OCR processing time: <30s per page
Zero downtime deployments

User Experience Metrics

Document upload success rate: >99%
Auto-categorization accuracy: >85%
Keyword extraction relevance: >80%
Search result relevance: >75%
User onboarding completion: >60%

Business Metrics

Storage quota enforcement: 100%
AI cost per document: <$0.10
OCR cost per page: <$0.01
Average processing time: <2 minutes
Failed task retry success: >70%


Risk Mitigation
Database Migration Risks

Risk: Data loss during migration
Mitigation: Backup before every migration, test in staging
Rollback: Alembic downgrade to previous revision

AI Processing Risks

Risk: API rate limits, costs spiral
Mitigation: Queue with rate limiting, cost caps per user/tier
Fallback: TF-IDF for keywords if AI unavailable

Storage Risks

Risk: Google Drive quota exceeded
Mitigation: Monitor usage, tiered limits, compression
Fallback: Block uploads before quota exhausted

Performance Risks

Risk: Slow searches as data grows
Mitigation: Proper indexing, pagination, caching
Monitoring: Query analysis, slow query logs


Conclusion
This implementation guide provides a structured path from current blocked state to full production system with comprehensive document management capabilities. The phased approach allows for incremental testing and deployment while maintaining system stability.
Estimated Timeline: 12 weeks to full feature parity
Immediate Focus: Fix migrations and deploy functional categories API (Days 1-2)
Critical Path: Enhanced schema → Processing pipeline → Search (Weeks 1-6)

status 4 Oct 2025