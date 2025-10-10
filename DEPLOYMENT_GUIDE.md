# Bonifatus DMS - Complete Deployment Guide v9.0

**Last Updated:** October 11, 2025  
**Production Status:** Database Complete | Features In Progress  
**Domain:** https://bonidoc.com  
**Maintainer:** Development Team

---

## Executive Summary

**Bonifatus DMS** is a professional document management system with AI-powered categorization, OCR processing, and multi-language support. The system supports **bulk document uploads** with **multi-category assignment** and uses **machine learning** to learn from user categorization behavior.

### Current Status

| Component | Status | Details |
|-----------|--------|---------|
| **Database** | ✅ Complete | All 26 tables deployed and operational |
| **Authentication** | ✅ Production | Google OAuth + JWT fully functional |
| **Categories** | ✅ Production | Multi-language CRUD with learning system |
| **Document Upload** | ⏳ Development | Batch upload analysis ready, storage pending |
| **OCR Processing** | ⏳ Planned | Architecture ready, implementation pending |
| **AI Categorization** | ⏳ Development | ML learning framework implemented |
| **Search** | ⏳ Planned | Schema ready, implementation pending |

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Database Schema (26 Tables)](#2-database-schema-26-tables)
3. [Migration Chain](#3-migration-chain)
4. [Backend Services](#4-backend-services)
5. [Frontend Architecture](#5-frontend-architecture)
6. [Deployment Process](#6-deployment-process)
7. [Configuration](#7-configuration)
8. [Monitoring & Troubleshooting](#8-monitoring--troubleshooting)
9. [Development Workflow](#9-development-workflow)
10. [Roadmap](#10-roadmap)

---

## 1. Architecture Overview

### 1.1 Technology Stack

**Backend:**
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 15.x (Supabase)
- **Authentication:** Google OAuth 2.0 + JWT
- **Storage:** Google Drive API
- **OCR:** Google Vision API (planned)
- **ML/AI:** OpenAI GPT-4 / Anthropic Claude (planned)
- **Migrations:** Alembic

**Frontend:**
- **Framework:** Next.js 15 (React 18)
- **Language:** TypeScript 5.x
- **Styling:** Tailwind CSS 3.x
- **State:** React Context API
- **UI Components:** Centralized design system

**Infrastructure:**
- **Platform:** Google Cloud Run (Serverless)
- **CI/CD:** GitHub Actions
- **Region:** us-central1
- **Domain:** bonidoc.com (SSL/TLS via Cloud Run)
- **Logs:** Cloud Logging

### 1.2 System Design Principles

✅ **Multi-Language First:** All UI strings externalized, categories translated dynamically  
✅ **Bulk Operations:** Documents processed in batches for efficiency  
✅ **Multi-Category Assignment:** Documents can belong to 1-5 categories  
✅ **ML Learning:** System learns from user categorization patterns  
✅ **Centralized Design:** All UI components use uniform theming  
✅ **Database-Driven:** Zero hardcoded values, all config from DB  
✅ **Production-Ready:** No TODO/FIXME, proper error handling everywhere

---

## 2. Database Schema (26 Tables)

### 2.1 Core Tables (Deployed & Active)

#### **Authentication & Users**
```sql
users                      -- User accounts (Google OAuth)
  - id, google_id, email, full_name, profile_picture
  - tier (free/premium/enterprise)
  - is_active, is_admin
  - last_login_at, last_login_ip
  - created_at, updated_at

user_settings              -- User preferences
  - id, user_id, setting_key, setting_value, data_type
  - created_at, updated_at
  
user_storage_quotas        -- Storage limits by tier
  - id, user_id, tier
  - total_quota_bytes, used_bytes
  - document_count, largest_file_bytes
  - last_calculated_at
```

#### **Categories (Multi-Language)**
```sql
categories                 -- Category definitions
  - id, reference_key, category_code
  - color_hex, icon_name
  - is_system, user_id
  - sort_order, is_active
  - created_at, updated_at

category_translations      -- Multi-language names
  - id, category_id, language_code
  - name, description
  - created_at, updated_at

category_term_weights      -- ML: Learned category associations
  - id, category_id, term, language_code
  - weight, document_frequency
  - last_updated
```

#### **Documents (Core)**
```sql
documents                  -- Main document table
  - id, title, description
  - file_name, original_filename, file_size, mime_type
  - file_hash (deduplication)
  - google_drive_file_id, web_view_link
  - thumbnail_url, preview_url, page_count
  - document_type
  - is_duplicate, duplicate_of_document_id
  - processing_status (uploaded/processing/completed/failed)
  - primary_language
  - download_count, last_accessed_at
  - batch_id (batch upload tracking)
  - user_id, category_id (legacy, now uses document_categories)
  - created_at, updated_at

document_categories        -- Many-to-many: Document ↔ Category
  - id, document_id, category_id
  - is_primary (one primary category per document)
  - assigned_at, assigned_by_ai
  
document_languages         -- Multi-language detection per document
  - id, document_id, language_code
  - confidence_score, is_primary
  - extracted_text, keywords (JSON)
  - processing_status
  - ai_category_suggestion, ai_confidence
  - created_at, updated_at
```

#### **Keywords & Entities (Searchable)**
```sql
keywords                   -- Normalized keyword dictionary
  - id, keyword, normalized_form
  - language_code
  - usage_count, category
  - created_at, updated_at

document_keywords          -- Many-to-many: Document ↔ Keyword
  - id, document_id, keyword_id
  - relevance_score
  - is_auto_extracted, is_user_added
  - extraction_method (tfidf/spacy/ai)
  - created_at

document_entities          -- Named entities (NER)
  - id, document_id
  - entity_type (person/org/location/date/amount/iban/email/phone)
  - entity_value, normalized_value
  - confidence_score
  - position_start, position_end (for highlighting)
  - context_before, context_after
  - language_code
  - created_at

language_detection_patterns -- ML: Language-specific patterns
  - id, pattern_type, pattern_value, language_code
  - confidence_weight, usage_count
  - created_at
```

#### **OCR Processing**
```sql
ocr_results                -- OCR processing archive
  - id, document_id, page_number
  - ocr_provider (google_vision/tesseract)
  - raw_text, confidence_score
  - bounding_boxes (JSON)
  - detected_language
  - processing_time_ms
  - provider_response (JSON)
  - cost_credits
  - created_at

stop_words                 -- Stop words for keyword filtering
  - id, word, language_code
  - is_active, created_at

spelling_corrections       -- ML: Learned OCR error corrections
  - id, incorrect_term, correct_term
  - language_code, confidence_score
  - usage_count, last_used_at
  - created_at, updated_at
```

#### **AI Processing Queue**
```sql
ai_processing_queue        -- Async AI task management
  - id, document_id
  - task_type (categorize/extract_keywords/extract_entities/detect_language/summarize)
  - status (pending/processing/completed/failed)
  - priority (1-10)
  - attempts, max_attempts
  - error_message, error_stack, result (JSON)
  - processing_started_at, processing_completed_at
  - processing_duration_ms
  - ai_provider (openai/anthropic/google)
  - ai_model (gpt-4/claude-3/gemini-pro)
  - tokens_used, cost_usd
  - created_at, updated_at

upload_batches             -- Batch upload tracking
  - id, user_id
  - total_files, processed_files
  - successful_files, failed_files
  - status (processing/completed/failed)
  - created_at, completed_at
```

#### **Collections & Organization**
```sql
collections                -- Folders/Smart Collections
  - id, user_id, name, description
  - color_hex, icon_name
  - parent_collection_id (nested folders)
  - sort_order
  - is_smart (rule-based filtering)
  - smart_rules (JSON)
  - created_at, updated_at

collection_documents       -- Many-to-many: Collection ↔ Document
  - collection_id, document_id
  - added_at, sort_order

document_relationships     -- Document links (amendments, versions, attachments)
  - id, source_document_id, target_document_id
  - relationship_type (amendment/version/attachment/reference)
  - description, created_at
```

#### **Sharing & Collaboration**
```sql
document_shares            -- Document sharing
  - id, document_id, shared_by_user_id
  - share_token (public link)
  - share_type (email/link)
  - shared_with_email
  - permission_level (view/comment/edit)
  - expires_at
  - access_count, last_accessed_at
  - is_active, created_at
```

#### **Tags & Notifications**
```sql
tags                       -- User-created tags
  - id, user_id, name, color_hex
  - usage_count, created_at

document_tags              -- Many-to-many: Document ↔ Tag
  - document_id, tag_id, added_at

notifications              -- User notifications
  - id, user_id
  - notification_type (document_shared/processing_complete/quota_warning)
  - title, message
  - related_document_id, action_url
  - is_read, created_at
```

#### **Search & Analytics**
```sql
search_history             -- User search patterns
  - id, user_id
  - search_query, search_type
  - filters_used (JSON)
  - results_count
  - clicked_result_ids (array)
  - created_at

keyword_training_data      -- ML: Keyword quality feedback
  - id, keyword, language_code
  - document_type
  - was_accepted (user feedback)
  - user_id, relevance_score
  - created_at
```

#### **System Configuration**
```sql
system_settings            -- Application-wide configuration
  - id, setting_key, setting_value, data_type
  - description, is_public, category
  - created_at, updated_at

localization_strings       -- Multi-language UI strings
  - id, string_key, language_code
  - string_value, context
  - created_at, updated_at

audit_logs                 -- Complete audit trail
  - id, user_id
  - action, resource_type, resource_id
  - ip_address, user_agent
  - old_values (JSON), new_values (JSON)
  - status (success/error)
  - error_message, user_locale
  - extra_data (JSON)
  - created_at, updated_at
```

### 2.2 Database Indexes & Constraints

**Critical Indexes (Performance):**
```sql
-- User lookups
idx_user_email, idx_user_google_id, idx_user_tier

-- Categories
idx_category_reference_key, idx_category_code, idx_category_active
idx_category_trans_category_id, idx_category_trans_lang

-- Documents
idx_document_user_id, idx_document_status, idx_document_google_drive
idx_document_primary_lang, idx_document_batch
idx_doc_cats_document, idx_doc_cats_category, idx_doc_cats_primary

-- Keywords & Search
idx_keyword_normalized, idx_keyword_language, idx_keyword_usage
idx_doc_keywords_doc, idx_doc_keywords_keyword
idx_doc_entities_doc, idx_doc_entities_type, idx_doc_entities_value

-- AI Processing
idx_ai_queue_status (status, priority DESC, created_at)
idx_ai_queue_document, idx_ai_queue_task_type

-- Audit & Search
idx_audit_user_action, idx_audit_resource, idx_audit_timestamp
idx_search_history_user
```

**Unique Constraints:**
```sql
-- Prevent duplicates
uq_category_language (category_id, language_code)
uq_document_category (document_id, category_id)
uq_user_tag_name (user_id, name)
uq_collection_doc (collection_id, document_id)
```

---

## 3. Migration Chain

### 3.1 Migration Sequence (10 Migrations)

```
0283144cf0fb - Initial schema (base tables: users, categories, documents, etc.)
      ↓
f1a2b3c4d5e6 - Populate initial data (settings, localization, default categories)
      ↓
g2b3c4d5e6f7 - Add Priority 1 tables (keywords, AI queue, quotas, entities, OCR)
      ↓
h3c4d5e6f7g8 - Add Priority 2 tables (collections, relationships, sharing)
      ↓
i4d5e6f7g8h9 - Add Priority 3 tables (tags, notifications, search history)
      ↓
j5e6f7g8h9i0 - Enhance existing tables (add columns to documents & users)
      ↓
k1l2m3n4o5p6 - Add category_code field
      ↓
l6m7n8o9p0q1 - Add document_categories many-to-many
      ↓
b0c1d2e3f4g5 - Add ML tables (language patterns, training data, weights)
      ↓
c1d2e3f4g5h6 - Add batch upload tracking
```

### 3.2 Migration Dependencies

**Foundation Layer (Must Deploy First):**
- `0283144cf0fb`: Creates all base tables
- `f1a2b3c4d5e6`: Populates critical initial data

**Enhancement Layer (Sequential):**
- `g2b3c4d5e6f7` through `i4d5e6f7g8h9`: Add advanced features
- `j5e6f7g8h9i0`: Enhance existing tables (safe, adds columns only)

**Multi-Category Support:**
- `k1l2m3n4o5p6`: Adds category codes for filename generation
- `l6m7n8o9p0q1`: **CRITICAL** - Enables multi-category assignment per document

**ML & Batch Upload:**
- `b0c1d2e3f4g5`: ML learning infrastructure
- `c1d2e3f4g5h6`: Batch upload tracking

### 3.3 Running Migrations

**Prerequisites:**
```bash
# Ensure DATABASE_URL is set (Supabase connection string)
export DATABASE_URL="postgresql://postgres:[password]@[host]:5432/postgres"
```

**Clean Deployment (Production):**
```bash
cd backend

# STEP 1: Clear any existing migration state
psql $DATABASE_URL -c "DELETE FROM alembic_version;"

# STEP 2: Run all migrations sequentially
alembic upgrade head

# STEP 3: Verify all tables created
psql $DATABASE_URL -c "\dt" | grep -c "table" # Should be 26+ tables

# STEP 4: Verify migration version
alembic current

# STEP 5: Verify system categories populated
psql $DATABASE_URL -c "SELECT COUNT(*) FROM categories WHERE is_system = true;" 
# Should return 5 or more
```

**Rollback (Emergency):**
```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade f1a2b3c4d5e6

# Rollback all
alembic downgrade base
```

### 3.4 Data Population Details

**System Settings (45+ settings):**
- Appearance: themes, colors
- Localization: languages, date formats
- Upload: file size limits, allowed types
- Documents: pagination, sort defaults
- Storage: quotas by tier
- ML: confidence thresholds, providers
- Security: session timeouts

**Default Categories (9 system categories):**
- Insurance (INS) - Versicherung (de), Страхование (ru)
- Legal (LEG) - Rechtliches (de), Юридические (ru)
- Real Estate (RES) - Immobilien (de), Недвижимость (ru)
- Banking (BNK) - Banking (de), Банковские (ru)
- Medical (MED) - Medizinisch (de), Медицинские (ru)
- Tax (TAX) - Steuern (de), Налоги (ru)
- Employment (EMP) - Beschäftigung (de), Трудовые (ru)
- Education (EDU) - Bildung (de), Образование (ru)
- Other (OTH) - Sonstiges (de), Прочее (ru)

**Localization Strings (300+ strings in 3 languages):**
- UI labels, buttons, messages
- Error messages
- Success notifications
- Category descriptions
- Help text

---

## 4. Backend Services

### 4.1 API Routers (6 Main Routers)

#### **Authentication Router** (`/api/v1/auth`)
```python
# backend/app/api/auth.py
GET  /google/config          # OAuth configuration for frontend
GET  /google/login           # Initiate Google OAuth flow
POST /google/callback        # Exchange auth code for JWT tokens
POST /refresh                # Refresh access token
DELETE /logout               # Invalidate tokens
GET  /me                     # Get current user profile
POST /admin/verify           # Verify admin access
```

**Status:** ✅ Production | Fully functional

#### **Users Router** (`/api/v1/users`)
```python
# backend/app/api/users.py
GET  /{user_id}              # Get user profile
PUT  /{user_id}              # Update user profile
POST /{user_id}/deactivate   # Deactivate account (30-day retention)
GET  /{user_id}/statistics   # User statistics (storage, documents)
```

**Status:** ✅ Production | Fully functional

#### **Categories Router** (`/api/v1/categories`)
```python
# backend/app/api/categories.py
GET    /                     # List categories (multi-language, with counts)
POST   /                     # Create new category
GET    /{category_id}        # Get category details
PUT    /{category_id}        # Update category
DELETE /{category_id}        # Delete category (move or delete docs)
POST   /restore-defaults     # Restore system categories
GET    /{category_id}/documents-count  # Document count
```

**Status:** ✅ Production | Multi-language support active

#### **Settings Router** (`/api/v1/settings`)
```python
# backend/app/api/settings.py
GET /public                  # Public system settings
GET /localization/{language} # Localized UI strings
GET /localization            # All localization strings
```

**Status:** ✅ Production | Used by frontend

#### **Document Analysis Router** (`/api/v1/document-analysis`)
```python
# backend/app/api/document_analysis.py
POST /analyze                # Analyze single document (temp storage)
POST /analyze-batch          # Analyze multiple documents in batch
POST /confirm-upload         # Confirm upload after user review
```

**Status:** ⏳ Development | Analysis works, storage integration pending

#### **Documents Router** (`/api/v1/documents`)
```python
# backend/app/api/documents.py
POST   /upload               # Upload document (legacy, single file)
GET    /                     # List documents (with filters, pagination)
GET    /{id}                 # Document details
PUT    /{id}                 # Update document metadata
DELETE /{id}                 # Delete document
GET    /{id}/download        # Download document
POST   /batch-operation      # Bulk operations (delete, move, tag)
```

**Status:** ⏳ Partial | Schema ready, implementation in progress

### 4.2 Service Layer (15+ Services)

#### **Core Services**
```python
auth_service              # Authentication, JWT, session management
user_service              # User CRUD, statistics, deactivation
category_service          # Category CRUD, multi-language, learning
config_service            # System settings, localization strings
```

#### **Document Services**
```python
document_upload_service   # Complete upload workflow with Google Drive
document_analysis_service # ML-powered document analysis
batch_upload_service      # Batch upload coordination
document_service          # Document CRUD operations (in progress)
```

#### **ML Services**
```python
ml_keyword_service        # Keyword extraction, learning from feedback
ml_category_service       # Category suggestion, weight learning
google_drive_service      # Google Drive API integration
ocr_service               # OCR processing (planned)
```

#### **Storage & Processing**
```python
storage_quota_service     # Quota enforcement, usage tracking
ai_processing_service     # Async AI task queue management (planned)
entity_extraction_service # Named entity recognition (planned)
```

### 4.3 Key Service Implementations

**Multi-Category Assignment:**
```python
# backend/app/services/document_upload_service.py
async def confirm_upload(..., category_ids: List[str], primary_category_id: Optional[str]):
    """
    Documents can have 1-5 categories
    One category must be marked as primary
    """
    # Validate 1-5 categories
    if not category_ids or len(category_ids) > 5:
        raise ValueError("Documents must have 1-5 categories")
    
    # Determine primary category
    if primary_category_id and primary_category_id in category_ids:
        primary = primary_category_id
    else:
        primary = category_ids[0]  # First category is primary by default
    
    # Create document_categories entries
    for idx, cat_id in enumerate(category_ids):
        create_document_category(
            document_id=document_id,
            category_id=cat_id,
            is_primary=(cat_id == primary),
            assigned_by_ai=(cat_id == suggested_category_id)
        )
```

**ML Category Learning:**
```python
# backend/app/services/ml_category_service.py
async def record_category_assignment(
    document_id: str,
    category_id: str,
    keywords: List[str],
    language_code: str
):
    """
    Learn from user's category assignments
    Update category_term_weights for better future suggestions
    """
    for keyword in keywords:
        # Update term weight for this category
        existing_weight = get_term_weight(category_id, keyword, language_code)
        
        if existing_weight:
            # Increase weight (term appears in this category again)
            new_weight = existing_weight.weight * 1.1  # 10% boost
            new_freq = existing_weight.document_frequency + 1
            update_term_weight(existing_weight.id, new_weight, new_freq)
        else:
            # Create new term association
            create_term_weight(
                category_id=category_id,
                term=keyword,
                language_code=language_code,
                weight=1.0,  # Initial weight
                document_frequency=1
            )
```

**Batch Upload Workflow:**
```python
# backend/app/services/batch_upload_service.py
async def analyze_batch(files_data, user_id, user_categories):
    """
    1. Create upload_batches record (tracking)
    2. Analyze each file concurrently (ML extraction)
    3. Generate standardized filenames (Title_YYYYMMDD_HHMMSS.ext)
    4. Store temp results (expires in 24h)
    5. Return analysis for user review
    6. User confirms → confirm_upload() stores permanently
    """
    batch_id = create_batch_record(user_id, len(files_data))
    
    results = await asyncio.gather(*[
        _analyze_single_file(file_data, user_categories, batch_id)
        for file_data in files_data
    ])
    
    return {
        'batch_id': batch_id,
        'total_files': len(files_data),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success']),
        'results': results
    }
```

---

## 5. Frontend Architecture

### 5.1 Page Structure (Next.js App Router)

```
frontend/src/app/
├── page.tsx                 # Landing page (public)
├── login/
│   └── page.tsx             # Login page with OAuth
├── dashboard/
│   └── page.tsx             # Main dashboard (protected)
├── documents/
│   ├── upload/
│   │   └── page.tsx         # Batch upload interface
│   └── review/
│       └── page.tsx         # Document review before confirm
├── categories/
│   └── page.tsx             # Category management (CRUD)
├── settings/
│   └── page.tsx             # User settings & preferences
├── profile/
│   └── page.tsx             # User profile & account
└── layout.tsx               # Root layout with theme provider
```

### 5.2 Centralized UI Components

**Component Library** (`frontend/src/components/ui/`)
```typescript
Button.tsx               # Primary, secondary, danger variants
Card.tsx                 # CardHeader, CardContent, CardFooter
Input.tsx                # Text, password, email, number
Select.tsx               # Dropdown with search
Alert.tsx                # Success, error, warning, info
Badge.tsx                # Status indicators
Modal.tsx                # Dialogs and confirmations
Table.tsx                # Data tables with sorting
```

**Design System:**
```typescript
// All components use centralized theme
const theme = {
  colors: {
    primary: '#2563eb',      // admin-primary
    secondary: '#6b7280',    // neutral-600
    success: '#10b981',      // green-500
    error: '#ef4444',        // red-500
    warning: '#f59e0b',      // amber-500
  },
  spacing: '0.25rem',        // Tailwind spacing scale
  borderRadius: '0.375rem',  // rounded-md
  fontSize: {
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
  }
}

// Usage in components
<Button variant="primary" size="md">Upload</Button>
<Alert type="success">Documents uploaded successfully</Alert>
```

### 5.3 State Management

**Context Providers:**
```typescript
// frontend/src/contexts/
AuthContext              # User authentication state
ThemeContext             # Dark/light mode
LanguageContext          # UI language (en/de/ru)
```

**Custom Hooks:**
```typescript
// frontend/src/hooks/
useAuth()                # Authentication state & actions
useCategories()          # Category management
useDocuments()           # Document operations
useTheme()               # Theme switching
```

### 5.4 Services (API Clients)

```typescript
// frontend/src/services/
api-client.ts            # Base API client with interceptors
auth.service.ts          # Authentication API calls
category.service.ts      # Category CRUD operations
document.service.ts      # Document operations
settings.service.ts      # Settings & localization
```

**Example Service:**
```typescript
// frontend/src/services/category.service.ts
export interface Category {
  id: string
  reference_key: string
  name: string              // Localized name (not name_en)
  description?: string      // Localized description
  category_code: string     // 3-char code (INS, LEG, etc.)
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

export const categoryService = {
  async listCategories(includeSystem = true, includeCounts = true): Promise<CategoryListResponse> {
    return await apiClient.get('/api/v1/categories', {
      params: { include_system: includeSystem, include_documents_count: includeCounts }
    })
  },
  
  async createCategory(data: CategoryCreateData): Promise<Category> {
    return await apiClient.post('/api/v1/categories', data)
  },
  
  // ... update, delete, restore methods
}
```

### 5.5 Batch Upload Flow (Frontend)

```typescript
// frontend/src/app/documents/upload/page.tsx
const BatchUploadPage = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploadStates, setUploadStates] = useState<FileUploadState[]>([])
  
  const handleAnalyzeBatch = async () => {
    // 1. Upload files to /api/v1/document-analysis/analyze-batch
    const formData = new FormData()
    selectedFiles.forEach(file => formData.append('files', file))
    
    const response = await fetch('/api/v1/document-analysis/analyze-batch', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` },
      body: formData
    })
    
    const result = await response.json()
    
    // 2. Build upload states from analysis results
    const states = result.results.map(r => ({
      ...r,
      file: selectedFiles.find(f => f.name === r.original_filename),
      selected_categories: r.analysis.suggested_category_id ? [r.analysis.suggested_category_id] : [],
      primary_category: r.analysis.suggested_category_id,
      confirmed_keywords: r.analysis.keywords.slice(0, 10).map(k => k.word),
      custom_filename: r.standardized_filename,
      filename_error: null
    }))
    
    setUploadStates(states)
  }
  
  const handleConfirmUpload = async (fileState: FileUploadState) => {
    // 3. User reviews and confirms upload
    await fetch('/api/v1/document-analysis/confirm-upload', {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        temp_id: fileState.temp_id,
        title: fileState.custom_filename.split('.')[0],
        category_ids: fileState.selected_categories,
        primary_category_id: fileState.primary_category,
        confirmed_keywords: fileState.confirmed_keywords
      })
    })
    
    // 4. Document stored in Google Drive and database
  }
}
```

---

## 6. Deployment Process

### 6.1 Automated Deployment (GitHub Actions)

**Trigger:** Push to `main` branch  
**Platform:** Google Cloud Run (Backend + Frontend)  
**Duration:** 3-5 minutes  
**Zero Downtime:** Yes (managed by Cloud Run)

**Workflow:**
```bash
# 1. Developer commits code
git add .
git commit -m "feat: add batch upload functionality"
git push origin main

# 2. GitHub Actions triggered automatically
# .github/workflows/deploy.yml executes:
#    a. Build backend Docker image
#    b. Push to Artifact Registry
#    c. Deploy to Cloud Run (backend)
#    d. Run database migrations (alembic upgrade head)
#    e. Build frontend Docker image
#    f. Deploy to Cloud Run (frontend)

# 3. Verify deployment
curl https://api.bonidoc.com/health
curl https://bonidoc.com
```

### 6.2 Manual Deployment (If Needed)

**Backend:**
```bash
cd backend

# Build Docker image
docker build -t us-central1-docker.pkg.dev/bon-dms/bonifatus-dms/bonifatus-dms:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/bon-dms/bonifatus-dms/bonifatus-dms:latest

# Deploy to Cloud Run
gcloud run deploy bonifatus-dms \
  --image us-central1-docker.pkg.dev/bon-dms/bonifatus-dms/bonifatus-dms:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars DATABASE_URL=$DATABASE_URL,JWT_SECRET_KEY=$JWT_SECRET_KEY
```

**Frontend:**
```bash
cd frontend

# Build Docker image
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.bonidoc.com \
  -t us-central1-docker.pkg.dev/bon-dms/bonifatus-dms/bonifatus-dms-frontend:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/bon-dms/bonifatus-dms/bonifatus-dms-frontend:latest

# Deploy to Cloud Run
gcloud run deploy bonifatus-dms-frontend \
  --image us-central1-docker.pkg.dev/bon-dms/bonifatus-dms/bonifatus-dms-frontend:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 3000
```

### 6.3 Rollback Procedure

**Application Rollback:**
```bash
# List recent revisions
gcloud run revisions list --service=bonifatus-dms --region=us-central1

# Route 100% traffic to previous revision
gcloud run services update-traffic bonifatus-dms \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# Verify rollback
curl https://api.bonidoc.com/health
```

**Database Rollback:**
```bash
# Rollback one migration
cd backend
alembic downgrade -

# Bonifatus DMS - Deployment Guide v9.0 (Part 2)

## 7. Configuration

### 7.1 Environment Variables (Backend)

**Required Secrets (GitHub Secrets / Cloud Run):**

#### **Database (1 variable)**
```bash
DATABASE_URL="postgresql://postgres:[password]@[host]:5432/postgres"
```

#### **Google OAuth (3 variables)**
```bash
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
GOOGLE_REDIRECT_URI="https://bonidoc.com/login"
```

#### **Google Drive (2 variables)**
```bash
GOOGLE_DRIVE_FOLDER_ID="..."      # Root folder for document storage
GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account",...}'  # JSON
```

#### **JWT Security (2 variables)**
```bash
JWT_SECRET_KEY="..."              # Strong random string (256 bits)
JWT_ALGORITHM="HS256"             # HMAC-SHA256
```

#### **Application Settings (5 variables)**
```bash
ENVIRONMENT="production"          # production/staging/development
CORS_ORIGINS="https://bonidoc.com,https://api.bonidoc.com"
FRONTEND_URL="https://bonidoc.com"
BACKEND_URL="https://api.bonidoc.com"
PORT="8080"
```

### 7.2 Environment Variables (Frontend)

```bash
NEXT_PUBLIC_API_URL="https://api.bonidoc.com"
```

### 7.3 System Settings (Database)

All configurable via `system_settings` table:

**Upload Settings:**
```json
{
  "max_file_size_mb": 50,
  "allowed_file_types": ["pdf", "doc", "docx", "jpg", "jpeg", "png", "txt", "tiff", "bmp"],
  "max_batch_upload_size": 10,
  "max_filename_length": 200,
  "filename_pattern": "[A-Za-z0-9_-]+",
  "enable_virus_scan": false
}
```

**Storage Quotas:**
```json
{
  "free_tier_quota_bytes": 1073741824,        // 1 GB
  "premium_tier_quota_bytes": 10737418240,     // 10 GB
  "enterprise_tier_quota_bytes": 107374182400  // 100 GB
}
```

**ML Settings:**
```json
{
  "keyword_relevance_threshold": 0.3,
  "category_confidence_threshold": 0.6,
  "max_keywords_per_document": 50,
  "enable_auto_categorization": true,
  "ai_provider": "openai",                     // openai/anthropic/google
  "ai_model": "gpt-4",                         // gpt-4/claude-3/gemini-pro
  "max_ai_retries": 3
}
```

**Localization:**
```json
{
  "default_language": "en",
  "available_languages": ["en", "de", "ru"],
  "default_theme": "light",
  "available_themes": ["light", "dark"]
}
```

### 7.4 Feature Flags

```json
{
  "enable_ocr": false,                  // OCR processing
  "enable_ai_categorization": false,    // AI category suggestions
  "enable_collections": false,          // Folder organization
  "enable_sharing": false,              // Document sharing
  "enable_notifications": false,        // User notifications
  "enable_search_analytics": false      // Search tracking
}
```

---

## 8. Monitoring & Troubleshooting

### 8.1 Health Checks

**Backend Health Endpoint:**
```bash
curl https://api.bonidoc.com/health

# Response:
{
  "status": "healthy",
  "service": "bonifatus-dms",
  "version": "9.0.0",
  "environment": "production",
  "database": "connected",
  "timestamp": "2025-10-11T10:00:00Z",
  "port": "8080"
}
```

**Database Health Check:**
```sql
-- Verify all tables exist
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public';
-- Should return 26

-- Verify migration version
SELECT version_num FROM alembic_version;
-- Should return: c1d2e3f4g5h6

-- Verify system categories
SELECT COUNT(*) FROM categories WHERE is_system = true;
-- Should return: 5-9

-- Check active users
SELECT COUNT(*) FROM users WHERE is_active = true;
```

### 8.2 Logging

**Cloud Logging (GCP):**
```bash
# View backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=bonifatus-dms" \
  --limit 50 \
  --format json

# View frontend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=bonifatus-dms-frontend" \
  --limit 50 \
  --format json

# Filter by severity
gcloud logging read "severity>=ERROR" --limit 100

# Real-time tail
gcloud logging tail "resource.type=cloud_run_revision"
```

**Application Logs (FastAPI):**
```python
# Structured logging format
{
  "timestamp": "2025-10-11T10:00:00Z",
  "level": "INFO",
  "logger": "app.services.batch_upload_service",
  "message": "Batch analysis completed: batch_id - 3/3 files",
  "user_id": "uuid",
  "request_id": "uuid"
}
```

### 8.3 Common Issues & Solutions

#### **Issue 1: Categories Endpoint Returns 404**

**Symptom:** `GET /api/v1/categories` returns 404 Not Found

**Root Cause:** Database migration not run, `categories` table doesn't exist

**Solution:**
```bash
cd backend
alembic upgrade head
psql $DATABASE_URL -c "SELECT COUNT(*) FROM categories WHERE is_system = true;"
```

#### **Issue 2: Logout Redirects to Blank Page**

**Symptom:** After clicking "Sign Out", user sees blank page instead of landing page

**Root Cause:** React router cache issue, token not fully cleared

**Solution:** (Already fixed in codebase)
```typescript
// frontend/src/hooks/use-auth.ts
const logout = async () => {
  await authService.logout()
  
  // Force full page reload to clear cache
  window.location.href = '/'  // Instead of router.push('/')
}
```

#### **Issue 3: Batch Analysis Returns "[object Object]"**

**Symptom:** Upload page shows "[object Object]" error message

**Root Cause:** Frontend error serialization doesn't handle complex error objects

**Solution:** (Already fixed in codebase)
```typescript
// frontend/src/app/documents/upload/page.tsx
if (!response.ok) {
  let errorDetail = 'Analysis failed'
  try {
    const errorData = await response.json()
    if (typeof errorData === 'object') {
      if (errorData.detail && typeof errorData.detail === 'string') {
        errorDetail = errorData.detail
      } else if (Array.isArray(errorData.detail)) {
        errorDetail = errorData.detail.map(err => 
          `${err.loc?.join('.')}: ${err.msg}`
        ).join('; ')
      }
    }
  } catch {
    errorDetail = `HTTP ${response.status}: ${response.statusText}`
  }
  throw new Error(errorDetail)
}
```

#### **Issue 4: Migration Circular Dependency**

**Symptom:** `alembic upgrade head` fails with "Cycle detected in revision chain"

**Root Cause:** Conflicting migration files with incorrect `down_revision` references

**Solution:**
```bash
# Delete alembic_version
psql $DATABASE_URL -c "DELETE FROM alembic_version;"

# Delete all migration files
cd backend/alembic/versions
rm -f *.py

# Restore migrations from project knowledge (in correct order)
# Run migrations sequentially
alembic upgrade head
```

#### **Issue 5: Google Drive Upload Fails**

**Symptom:** Document upload returns error "Failed to upload to Google Drive"

**Root Cause:** Service account credentials invalid or folder permissions incorrect

**Solution:**
```bash
# Verify service account key format
echo $GOOGLE_SERVICE_ACCOUNT_KEY | python -m json.tool

# Test Google Drive API
python backend/test_google_drive.py

# Verify folder permissions
# Visit: https://drive.google.com/drive/folders/[FOLDER_ID]
# Share folder with service account email
```

### 8.4 Performance Monitoring

**Key Metrics:**
```
API Response Time (p95): < 200ms
Database Query Time (p95): < 100ms
Document Upload Time: < 5s per file
Batch Analysis Time: < 30s for 10 files
OCR Processing Time: < 30s per page
```

**Monitoring Dashboard (Google Cloud Console):**
- Request count & latency
- Error rate (4xx, 5xx)
- Container CPU & memory usage
- Database connection pool
- Storage usage

---

## 9. Development Workflow

### 9.1 Local Development Setup

**Prerequisites:**
```bash
# Install required tools
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (or use Supabase)
- Docker (optional)
- Git
```

**Backend Setup:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# API docs available at: http://localhost:8080/docs
```

**Frontend Setup:**
```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
cp .env.example .env.local
# Edit .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8080

# Start development server
npm run dev

# Frontend available at: http://localhost:3000
```

### 9.2 Development Standards

**Code Quality Checklist (Before Every Commit):**
```
✅ Files are modular (<300 lines)
✅ No hardcoded values (database-driven config)
✅ Production-ready code only (no TODO/FIXME)
✅ Checked for duplicate functions
✅ Professional comments (no implementation details in comments)
✅ Root cause fixes (no workarounds)
✅ All imports at top of file
✅ File header comment with path
✅ Multi-input support tested (mouse, keyboard, touch)
```

**Commit Message Format:**
```bash
git commit -m "type: brief description

- Detail 1: specific change made
- Detail 2: reason for change
- Detail 3: impact or benefit"

# Types: feat, fix, docs, style, refactor, test, chore
```

**Example:**
```bash
git commit -m "feat: add multi-category assignment to documents

- Modify document_upload_service to support 1-5 categories per document
- Add primary_category_id parameter for explicit primary selection
- Update database schema with document_categories junction table
- Frontend batch upload UI now supports multi-category selection
- ML category learning updated to handle multiple category associations"
```

### 9.3 Testing

**Backend Tests:**
```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_category_service.py

# Run with coverage
pytest --cov=app --cov-report=html

# Test database migrations
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

**Frontend Tests:**
```bash
cd frontend

# Run unit tests (when implemented)
npm test

# Run E2E tests (when implemented)
npm run test:e2e
```

**Manual Testing Checklist:**
```
1. Authentication Flow
   ✅ Google OAuth login works
   ✅ JWT tokens refresh correctly
   ✅ Logout clears session and redirects to landing page

2. Category Management
   ✅ List categories loads (multi-language)
   ✅ Create new category works
   ✅ Edit category updates all translations
   ✅ Delete category handles documents correctly
   ✅ Restore defaults creates system categories

3. Document Upload (Batch)
   ✅ Select multiple files (3-10 files)
   ✅ Analyze batch extracts keywords and suggests categories
   ✅ Review page shows all analyzed files
   ✅ Edit filename, categories, keywords
   ✅ Confirm upload stores in Google Drive
   ✅ Documents appear in database with multi-category assignments

4. Settings & Profile
   ✅ Change theme (light/dark)
   ✅ Change language (en/de/ru)
   ✅ Update profile information
   ✅ View storage statistics

5. Dark Mode
   ✅ Toggle dark mode in settings
   ✅ Theme persists across sessions
   ✅ All pages render correctly in dark mode
```

### 9.4 Database Development

**Create New Migration:**
```bash
cd backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "add new feature"

# Create empty migration
alembic revision -m "manual migration"

# Edit migration file
# backend/alembic/versions/[revision]_description.py

# Test migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

**Migration Best Practices:**
```python
def upgrade():
    # Always include indexes for foreign keys
    op.create_table('new_table',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), ForeignKey('users.id')),
        sa.Column('name', sa.String(255), nullable=False)
    )
    op.create_index('idx_new_table_user', 'new_table', ['user_id'])
    
    # Always provide default values for NOT NULL columns
    op.add_column('existing_table', 
        sa.Column('new_field', sa.String(50), nullable=False, server_default='default_value')
    )
    
    # Then remove server_default if not needed
    op.alter_column('existing_table', 'new_field', server_default=None)

def downgrade():
    # Always implement downgrade
    op.drop_index('idx_new_table_user')
    op.drop_table('new_table')
```

---

## 10. Roadmap

### 10.1 Completed Features ✅

**Phase 0: Foundation (October 2025)**
- ✅ Google Cloud Run deployment (backend + frontend)
- ✅ Supabase PostgreSQL database
- ✅ GitHub Actions CI/CD
- ✅ Google OAuth authentication + JWT
- ✅ Database schema (26 tables complete)
- ✅ Alembic migrations (10 migrations, clean chain)

**Phase 1: Core Features (October 2025)**
- ✅ User management (profile, settings, statistics)
- ✅ Multi-language categories (9 system categories in en/de/ru)
- ✅ Category CRUD with translations
- ✅ Dark mode theme
- ✅ Settings & localization API
- ✅ Account deactivation with 30-day retention
- ✅ Audit logging framework

**Phase 2: Document Upload Foundation (October 2025)**
- ✅ Batch upload analysis endpoint
- ✅ ML keyword extraction (TF-IDF)
- ✅ Document analysis service
- ✅ Standardized filename generation
- ✅ Multi-category assignment architecture
- ✅ ML category learning framework
- ✅ Frontend batch upload UI

### 10.2 Current Development (October-November 2025) ⏳

**Document Upload Completion:**
- ⏳ Google Drive storage integration testing
- ⏳ Confirm upload endpoint (store permanently)
- ⏳ Document list view with filters
- ⏳ Document detail page
- ⏳ Document download functionality
- ⏳ Storage quota enforcement

**ML Category Learning:**
- ⏳ Train category weights from user assignments
- ⏳ Improve suggestion accuracy based on feedback
- ⏳ Language-specific term weights
- ⏳ Category suggestion confidence scoring

### 10.3 Q4 2025 Roadmap (November-December)

**OCR Processing:**
- ⏳ Google Vision API integration
- ⏳ Tesseract fallback for cost optimization
- ⏳ Page-by-page OCR processing
- ⏳ OCR results archive (quality tracking)
- ⏳ Text extraction from PDFs and images

**AI Processing Queue:**
- ⏳ Async task queue implementation
- ⏳ Background workers for AI tasks
- ⏳ Retry logic with exponential backoff
- ⏳ Cost tracking per task
- ⏳ Queue dashboard (admin view)

**Advanced Document Features:**
- ⏳ Named entity extraction (person, org, date, amount, IBAN)
- ⏳ Language detection (multi-language documents)
- ⏳ Duplicate detection (file hash matching)
- ⏳ Document versioning

### 10.4 Q1 2026 Roadmap (January-March)

**Collections & Organization:**
- ⏳ Folder hierarchy (nested collections)
- ⏳ Smart collections (rule-based filtering)
- ⏳ Drag & drop document organization
- ⏳ Bulk document operations

**Search & Discovery:**
- ⏳ Full-text search (keywords + entities)
- ⏳ Advanced filters (date range, category, language, size)
- ⏳ Saved searches
- ⏳ Search suggestions based on history

**Sharing & Collaboration:**
- ⏳ Share documents via email
- ⏳ Public link sharing with expiration
- ⏳ Permission levels (view/comment/edit)
- ⏳ Access tracking and analytics

### 10.5 Q2 2026 Roadmap (April-June)

**Advanced ML Features:**
- ⏳ AI document summarization
- ⏳ Important date extraction (deadlines, expiration dates)
- ⏳ Sentiment analysis (contracts, legal docs)
- ⏳ Document classification (invoice, contract, receipt, etc.)

**User Experience:**
- ⏳ Document preview (inline PDF viewer)
- ⏳ Thumbnail generation
- ⏳ Drag & drop upload
- ⏳ Mobile-responsive UI improvements

**Analytics & Insights:**
- ⏳ Document statistics dashboard
- ⏳ Storage usage trends
- ⏳ Most accessed documents
- ⏳ Search analytics (popular queries, no-results tracking)

### 10.6 Future Enhancements (H2 2026)

**Enterprise Features:**
- Two-factor authentication
- Team collaboration (multi-user workspaces)
- Role-based access control (RBAC)
- API rate limiting by tier
- Audit log export
- Custom category templates

**Integration & Export:**
- Export documents in bulk (ZIP archive)
- Integration with other cloud storage (Dropbox, OneDrive)
- Webhook notifications
- REST API for third-party integrations

**Performance & Scale:**
- Redis caching layer
- Elasticsearch for advanced search
- CDN for static assets
- Multi-region deployment
- Database read replicas

---

## 11. Support & Resources

### 11.1 Documentation

- **Production Site:** https://bonidoc.com
- **API Documentation:** https://api.bonidoc.com/docs (Swagger/OpenAPI)
- **GitHub Repository:** https://github.com/botwa2000/bonifatus-dms
- **Deployment Guide:** This document
- **Implementation Guide:** IMPLEMENTATION_GUIDE.md (project knowledge)

### 11.2 Key Commands Reference

**Deployment:**
```bash
git push origin main                           # Trigger auto-deployment
gcloud run services list --region=us-central1  # View services
gcloud run revisions list --service=bonifatus-dms  # List revisions
```

**Database:**
```bash
alembic upgrade head         # Run all migrations
alembic current              # Show current version
alembic downgrade -1         # Rollback one migration
psql $DATABASE_URL -c "\dt"  # List all tables
```

**Monitoring:**
```bash
curl https://api.bonidoc.com/health  # Health check
gcloud logging tail "resource.type=cloud_run_revision"  # Live logs
```

**Development:**
```bash
# Backend
uvicorn app.main:app --reload --port 8080

# Frontend
npm run dev

# Tests
pytest
npm test
```

### 11.3 Contact & Support

- **Issues:** https://github.com/botwa2000/bonifatus-dms/issues
- **Email:** bonifatus.app@gmail.com
- **Documentation:** https://docs.bonidoc.com (planned)

---

## 12. Conclusion

**Bonifatus DMS** has a solid foundation with:
- ✅ Complete database schema (26 tables)
- ✅ Production-ready authentication
- ✅ Multi-language support infrastructure
- ✅ ML learning framework for categorization
- ✅ Batch document upload analysis
- ✅ Centralized, professional UI components

**Next Steps:**
1. Complete Google Drive storage integration
2. Deploy confirm upload endpoint
3. Implement document list & detail views
4. Add OCR processing pipeline
5. Deploy AI categorization workers

**System is production-ready for:**
- User authentication & management
- Category management (multi-language)
- Document upload analysis (batch)
- Settings & localization
- Dark mode & responsive UI

**In active development:**
- Document storage & retrieval
- OCR processing
- AI categorization
- Search functionality

---

**Version:** 9.0  
**Status:** Production Database | Development Features  
**Last Verified:** October 11, 2025  
**Next Review:** November 1, 2025

**Deployment Guide Maintained By:** Development Team  
**For Questions:** Create issue on GitHub or contact bonifatus.app@gmail.com