BoniDoc - Complete Development & Deployment Guide
Version: 10.1
Last Updated: October 12, 2025
Status: Production Database | Active Development
Domain: https://bonidoc.com

Table of Contents

Executive Summary & Project Objectives
Technology Stack & Architecture
Project Structure
User Interaction Flows
File Upload Processing Logic
Implementation Standards
Quality Control Process
Current Development Status
Next Development Milestones
Progress Tracking Protocol
Configuration & Deployment


1. Executive Summary & Project Objectives
1.1 Project Vision
BoniDoc is a professional document management system that combines secure storage, intelligent categorization, and multi-language support to help users organize their documents efficiently. The system learns from user behavior to improve accuracy over time.
1.2 Core Objectives
Primary Goals:

Security-First Architecture: Field-level encryption, httpOnly cookies, comprehensive audit logging, rate limiting on all endpoints
Intelligent Document Processing: OCR for scanned documents, AI-powered keyword extraction, automated categorization with learning
Multi-Language Support: Full UI/UX in English, German, and Russian; language-specific document processing
User-Owned Storage: Documents stored in user's personal Google Drive, ensuring data ownership and privacy
Zero Technical Debt: No hardcoded values, no workarounds, no TODO comments in production code

User Experience Goals:

One-click batch upload with automatic analysis
Clear visual feedback on categorization confidence
Multi-category assignment (multiple categories per document)
Learning system that improves suggestions based on user corrections
Mobile-responsive interface with dark mode support
Multilingual platform with initially EN+DE+RU supported, future languages to be added via database

1.3 System Principles
✅ Database-Driven Configuration: All settings, categories, and localization strings stored in database
✅ Production-Ready Code: No fallbacks, temporary solutions, or placeholder code
✅ Modular Architecture: Each file serves a single, well-defined purpose (<300 lines)
✅ Security by Design: Multiple layers of protection, never trust client input
✅ Privacy-First: User data stored in their own Google Drive, not on our servers
✅ Learning System: ML algorithms improve from every user interaction
✅ Accessibility: Multi-input support (mouse, keyboard, touch) on all interactive elements

2. Technology Stack & Architecture
2.1 Technology Stack
Backend:

Framework: FastAPI (Python 3.11+)
Database: PostgreSQL 15.x (Supabase)
Authentication: Google OAuth 2.0 + JWT with httpOnly cookies
Storage: Google Drive API (user-owned storage)
OCR: Tesseract + PyMuPDF for text extraction
Encryption: Fernet (AES-256) for sensitive field encryption
Migrations: Alembic
Deployment: Google Cloud Run (serverless)

Frontend:

Framework: Next.js 15 (React 18)
Language: TypeScript 5.x
Styling: Tailwind CSS 3.x with centralized design system
State Management: React Context API
Authentication: JWT in httpOnly cookies (not localStorage)

Infrastructure:

Platform: Google Cloud Run (Backend + Frontend)
CI/CD: GitHub Actions (automated deployment on push to main)
Region: us-central1
Domain: bonidoc.com (SSL/TLS managed by Cloud Run)
Monitoring: Google Cloud Logging + Monitoring

2.2 Database Architecture
26 Active Tables organized in functional groups:
Authentication & Users (3 tables):

users: User accounts with Google OAuth integration
user_settings: User preferences and configuration
user_sessions: Active session tracking for security

Categories & Translations (3 tables):

categories: Category definitions with codes
category_translations: Multi-language names/descriptions
category_keywords: Learned keyword associations for ML

Documents (3 tables):

documents: Main document metadata
document_categories: Many-to-many (supports 1-5 categories per document)
document_languages: Multi-language detection per document

Keywords & Search (3 tables):

keywords: Normalized keyword dictionary
document_keywords: Document-keyword associations with relevance scores
stop_words: Language-specific stop word filtering

Google Drive Integration (2 tables):

google_drive_folders: Category folder mappings in user's Drive
google_drive_sync_status: Sync state and quota tracking

ML & Classification (2 tables):

document_classification_log: Track all classification decisions
category_classification_metrics: Daily accuracy metrics per category

System Configuration (3 tables):

system_settings: Application-wide configuration
localization_strings: UI translations
audit_logs: Complete security audit trail

Additional Features (7 tables):

upload_batches: Batch upload tracking
collections: Folder organization
document_entities: Named entity extraction (NER)
document_shares: Document sharing
tags: User-created tags
notifications: User notifications
search_history: Search pattern tracking

2.3 System Architecture Principles
Security Layers:

Transport Security: HTTPS with HSTS headers
Authentication: Google OAuth + JWT with short expiry (15 minutes)
Session Management: Refresh tokens with 7-day expiry, tracking active sessions
Field-Level Encryption: Sensitive data encrypted at rest
Rate Limiting: Three-tier limits (auth/write/read operations)
Input Validation: Pydantic models for all API inputs
Audit Logging: All security events logged with sanitization

Data Flow:
User Upload → File Validation → Temporary Storage → OCR/Text Extraction 
→ Keyword Extraction → Classification → User Review 
→ Permanent Storage (Google Drive) → Database Metadata → Learning Update
Learning Cycle:
Classification Suggestion → User Confirmation/Correction 
→ Weight Adjustment → Improved Future Suggestions

3. Project Structure
3.1 Current Backend Structure
backend/
├── alembic/                          # Database migrations
│   ├── versions/                     # Migration files (10 migrations)
│   │   ├── 0283144cf0fb_initial_schema.py
│   │   ├── f1a2b3c4d5e6_populate_initial_data.py
│   │   ├── g2b3c4d5e6f7_add_priority_1_tables.py
│   │   ├── h3c4d5e6f7g8_add_priority_2_tables.py
│   │   ├── i4d5e6f7g8h9_add_priority_3_tables.py
│   │   ├── j5e6f7g8h9i0_enhance_existing_tables.py
│   │   ├── k1l2m3n4o5p6_add_category_code.py
│   │   ├── l6m7n8o9p0q1_add_document_categories.py
│   │   ├── b0c1d2e3f4g5_add_ml_tables.py
│   │   └── c1d2e3f4g5h6_add_batch_upload_tracking.py
│   ├── env.py
│   └── script.py.mako
│
├── app/
│   ├── __init__.py
│   │
│   ├── main.py                       # FastAPI application entry point
│   │
│   ├── api/                          # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py                   # Authentication endpoints (login, logout, refresh)
│   │   ├── users.py                  # User management endpoints
│   │   ├── categories.py             # Category CRUD endpoints
│   │   ├── settings.py               # System settings & localization endpoints
│   │   ├── document_analysis.py      # Batch analysis & confirm upload endpoints
│   │   └── documents.py              # Document CRUD endpoints (in progress)
│   │
│   ├── models/                       # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── user.py                   # User, UserSettings, UserSessions
│   │   ├── category.py               # Categories, CategoryTranslations, CategoryKeywords
│   │   ├── document.py               # Documents, DocumentCategories, DocumentLanguages
│   │   ├── keyword.py                # Keywords, DocumentKeywords, StopWords
│   │   ├── google_drive.py           # GoogleDriveFolders, GoogleDriveSyncStatus
│   │   ├── classification.py         # DocumentClassificationLog, CategoryClassificationMetrics
│   │   ├── system.py                 # SystemSettings, LocalizationStrings, AuditLogs
│   │   └── additional.py             # UploadBatches, Collections, Tags, etc.
│   │
│   ├── services/                     # Business logic services
│   │   ├── __init__.py
│   │   │
│   │   ├── auth_service.py           # Authentication & JWT management
│   │   ├── user_service.py           # User CRUD operations
│   │   ├── category_service.py       # Category CRUD & multi-language handling
│   │   ├── config_service.py         # System settings & localization
│   │   │
│   │   ├── document_upload_service.py     # Complete upload workflow
│   │   ├── document_analysis_service.py   # Text extraction & analysis
│   │   ├── batch_upload_service.py        # Batch processing coordination
│   │   ├── document_service.py            # Document CRUD (in progress)
│   │   │
│   │   ├── ml_keyword_service.py          # Keyword extraction (TF-IDF)
│   │   ├── ml_category_service.py         # Category suggestion & learning
│   │   ├── language_detection_service.py   # Language detection
│   │   │
│   │   ├── google_drive_service.py        # Google Drive API integration (planned)
│   │   ├── ocr_service.py                 # OCR processing (planned)
│   │   ├── storage_quota_service.py       # Quota tracking & enforcement
│   │   │
│   │   └── [PLANNED Phase 1 Services]
│   │       ├── encryption_service.py      # Field-level encryption
│   │       ├── session_service.py         # Session management
│   │       ├── rate_limit_service.py      # Rate limiting
│   │       ├── file_validation_service.py # Upload validation
│   │       ├── audit_service.py           # Enhanced audit logging
│   │       └── security_monitoring_service.py  # Anomaly detection
│   │
│   ├── middleware/                   # Custom middleware
│   │   ├── __init__.py
│   │   └── [PLANNED]
│   │       ├── security_headers.py   # Security headers
│   │       └── rate_limit.py         # Rate limiting middleware
│   │
│   ├── core/                         # Core utilities
│   │   ├── __init__.py
│   │   ├── config.py                 # Configuration management
│   │   ├── database.py               # Database session management
│   │   └── security.py               # Security utilities
│   │
│   ├── schemas/                      # Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── auth.py                   # Auth request/response schemas
│   │   ├── user.py                   # User schemas
│   │   ├── category.py               # Category schemas
│   │   ├── document.py               # Document schemas
│   │   └── common.py                 # Shared schemas
│   │
│   └── utils/                        # Utility functions
│       ├── __init__.py
│       ├── file_utils.py             # File handling utilities
│       ├── text_utils.py             # Text processing utilities
│       └── datetime_utils.py         # Date/time utilities
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_categories.py
│   ├── test_document_analysis.py
│   └── [PLANNED]
│       └── test_security.py          # Security test suite
│
├── requirements.txt                  # Python dependencies
├── Dockerfile                        # Backend container definition
├── .env.example                      # Environment variables template
└── README.md                         # Backend documentation
3.2 Current Frontend Structure
frontend/
├── public/                           # Static assets
│   ├── favicon.ico
│   └── images/
│
├── src/
│   ├── app/                          # Next.js App Router pages
│   │   ├── layout.tsx                # Root layout with providers
│   │   ├── page.tsx                  # Landing page (public)
│   │   │
│   │   ├── login/
│   │   │   └── page.tsx              # Login page with Google OAuth
│   │   │
│   │   ├── dashboard/
│   │   │   └── page.tsx              # Main dashboard (protected)
│   │   │
│   │   ├── documents/
│   │   │   ├── upload/
│   │   │   │   └── page.tsx          # Batch upload interface
│   │   │   ├── review/
│   │   │   │   └── page.tsx          # Review before confirm (in progress)
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx          # Document detail page (planned)
│   │   │   └── page.tsx              # Document list (planned)
│   │   │
│   │   ├── categories/
│   │   │   └── page.tsx              # Category management (CRUD)
│   │   │
│   │   ├── settings/
│   │   │   └── page.tsx              # User settings & preferences
│   │   │
│   │   └── profile/
│   │       └── page.tsx              # User profile & account
│   │
│   ├── components/                   # React components
│   │   ├── ui/                       # Base UI components (centralized design)
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Alert.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Spinner.tsx
│   │   │   └── ProgressBar.tsx
│   │   │
│   │   ├── layout/                   # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   │
│   │   ├── auth/                     # Authentication components
│   │   │   ├── GoogleLoginButton.tsx
│   │   │   └── LogoutButton.tsx
│   │   │
│   │   ├── documents/                # Document-related components
│   │   │   ├── FileUploadZone.tsx
│   │   │   ├── DocumentAnalysisCard.tsx
│   │   │   ├── KeywordBadges.tsx
│   │   │   ├── CategorySelector.tsx
│   │   │   └── FilenameEditor.tsx
│   │   │
│   │   ├── categories/               # Category-related components
│   │   │   ├── CategoryList.tsx
│   │   │   ├── CategoryForm.tsx
│   │   │   ├── CategoryCard.tsx
│   │   │   └── [PLANNED]
│   │   │       └── CategoryKeywordsDialog.tsx
│   │   │
│   │   └── common/                   # Shared components
│   │       ├── ThemeToggle.tsx
│   │       ├── LanguageSelector.tsx
│   │       ├── LoadingState.tsx
│   │       └── ErrorBoundary.tsx
│   │
│   ├── contexts/                     # React Context providers
│   │   ├── AuthContext.tsx           # User authentication state
│   │   ├── ThemeContext.tsx          # Dark/light mode
│   │   └── LanguageContext.tsx       # UI language (en/de/ru)
│   │
│   ├── hooks/                        # Custom React hooks
│   │   ├── use-auth.ts               # Authentication hook
│   │   ├── use-categories.ts         # Category management hook
│   │   ├── use-documents.ts          # Document operations hook
│   │   ├── use-theme.ts              # Theme switching hook
│   │   └── use-toast.ts              # Toast notifications hook
│   │
│   ├── services/                     # API client services
│   │   ├── api-client.ts             # Base API client with interceptors
│   │   ├── auth.service.ts           # Authentication API calls
│   │   ├── category.service.ts       # Category CRUD operations
│   │   ├── document.service.ts       # Document operations
│   │   ├── settings.service.ts       # Settings & localization
│   │   └── user.service.ts           # User management
│   │
│   ├── lib/                          # Utility libraries
│   │   ├── auth.ts                   # Auth utilities
│   │   ├── constants.ts              # App constants
│   │   ├── validators.ts             # Input validation
│   │   └── formatters.ts             # Data formatting
│   │
│   ├── types/                        # TypeScript type definitions
│   │   ├── auth.types.ts
│   │   ├── category.types.ts
│   │   ├── document.types.ts
│   │   ├── user.types.ts
│   │   └── common.types.ts
│   │
│   └── styles/                       # Global styles
│       └── globals.css               # Tailwind imports & custom styles
│
├── .env.example                      # Environment variables template
├── next.config.js                    # Next.js configuration
├── tailwind.config.js                # Tailwind CSS configuration
├── tsconfig.json                     # TypeScript configuration
├── package.json                      # Node dependencies
├── Dockerfile                        # Frontend container definition
└── README.md                         # Frontend documentation
3.3 Target Structure (After Phase 1-4)
Backend Additions:
backend/app/
├── services/
│   ├── encryption_service.py         ✅ Added in Phase 1
│   ├── session_service.py            ✅ Added in Phase 1
│   ├── rate_limit_service.py         ✅ Added in Phase 1
│   ├── file_validation_service.py    ✅ Added in Phase 1
│   ├── audit_service.py              ✅ Enhanced in Phase 1
│   ├── security_monitoring_service.py ✅ Added in Phase 1
│   ├── ocr_service.py                ✅ Added in Phase 2
│   ├── document_classifier_service.py ✅ Added in Phase 2
│   ├── category_learning_service.py   ✅ Added in Phase 2
│   ├── category_keyword_service.py    ✅ Added in Phase 2
│   └── google_drive_service.py       ✅ Added in Phase 3
│
├── middleware/
│   ├── security_headers.py           ✅ Added in Phase 1
│   └── rate_limit.py                 ✅ Added in Phase 1
│
├── jobs/                             # Background jobs
│   ├── __init__.py
│   ├── drive_sync_job.py             ✅ Added in Phase 3
│   ├── metrics_calculation_job.py    ✅ Added in Phase 2
│   └── session_cleanup_job.py        ✅ Added in Phase 1
│
└── tests/
    ├── test_security.py              ✅ Added in Phase 1
    ├── test_ocr.py                   ✅ Added in Phase 2
    ├── test_classification.py        ✅ Added in Phase 2
    └── test_drive.py                 ✅ Added in Phase 3
Frontend Additions:
frontend/src/
├── components/
│   ├── categories/
│   │   └── CategoryKeywordsDialog.tsx ✅ Added in Phase 2
│   │
│   ├── documents/
│   │   ├── ClassificationReasoningCard.tsx ✅ Added in Phase 2
│   │   ├── DocumentDetailView.tsx     ✅ Added in Phase 3
│   │   └── DriveConnectionCard.tsx    ✅ Added in Phase 3
│   │
│   └── settings/
│       └── GoogleDriveSettings.tsx    ✅ Added in Phase 3
│
└── app/
    ├── documents/
    │   ├── [id]/page.tsx              ✅ Added in Phase 3
    │   └── page.tsx                   ✅ Added in Phase 3
    │
    └── settings/
        └── [Enhanced with Drive]      ✅ Updated in Phase 3

4. User Interaction Flows
4.1 Authentication Flow
┌─────────────────────────────────────────────────────────────────┐
│ 1. INITIAL ACCESS                                               │
└─────────────────────────────────────────────────────────────────┘

User visits: https://bonidoc.com
    ↓
Landing Page Loads
    ↓
User clicks "Sign in with Google"
    ↓
Frontend calls: GET /api/v1/auth/google/config
    ↓
Frontend redirects to Google OAuth consent screen


┌─────────────────────────────────────────────────────────────────┐
│ 2. GOOGLE OAUTH CONSENT                                         │
└─────────────────────────────────────────────────────────────────┘

Google OAuth Screen Shows:
    - BoniDoc requests access to:
        • Email address
        • Profile information
        • [Optional] Google Drive access
    ↓
User clicks "Allow"
    ↓
Google redirects back to: /login?code=OAUTH_CODE


┌─────────────────────────────────────────────────────────────────┐
│ 3. TOKEN EXCHANGE & SESSION CREATION                            │
└─────────────────────────────────────────────────────────────────┘

Frontend receives OAuth code
    ↓
Frontend calls: POST /api/v1/auth/google/callback
    Body: { "code": "OAUTH_CODE" }
    ↓
Backend validates code with Google
    ↓
Backend receives user info (email, name, picture)
    ↓
Backend checks if user exists in database
    IF NOT EXISTS: Create new user record
    ↓
Backend creates session record in user_sessions table
    ↓
Backend generates tokens:
    - access_token (JWT, 15-minute expiry)
    - refresh_token (random string, 7-day expiry)
    ↓
Backend stores refresh_token hash in user_sessions
    ↓
Backend returns response with Set-Cookie headers:
    - access_token (httpOnly, secure, sameSite=strict)
    - refresh_token (httpOnly, secure, sameSite=strict)
    ↓
Frontend stores tokens in cookies (automatic)
    ↓
Frontend redirects to: /dashboard


┌─────────────────────────────────────────────────────────────────┐
│ 4. AUTHENTICATED REQUESTS                                       │
└─────────────────────────────────────────────────────────────────┘

User navigates to protected page
    ↓
Frontend makes API call with credentials: 'include'
    ↓
Browser automatically sends cookies
    ↓
Backend middleware extracts access_token
    ↓
Backend validates JWT signature and expiry
    ↓
IF VALID:
    Process request
    ↓
    Return data
ELSE IF EXPIRED:
    Return 401 Unauthorized
    ↓
    Frontend detects 401
    ↓
    Frontend calls: POST /api/v1/auth/refresh
        (refresh_token cookie sent automatically)
    ↓
    Backend validates refresh_token
    ↓
    Backend generates new access_token
    ↓
    Backend returns new access_token cookie
    ↓
    Frontend retries original request


┌─────────────────────────────────────────────────────────────────┐
│ 5. LOGOUT                                                        │
└─────────────────────────────────────────────────────────────────┘

User clicks "Sign Out"
    ↓
Frontend calls: DELETE /api/v1/auth/logout
    ↓
Backend:
    - Marks session as revoked in database
    - Clears cookies (Set-Cookie with Max-Age=0)
    ↓
Backend returns 200 OK
    ↓
Frontend executes: window.location.href = '/'
    ↓
Browser performs full page reload
    ↓
Landing page loads (user is logged out)
4.2 Category Management Flow
┌─────────────────────────────────────────────────────────────────┐
│ 1. VIEW CATEGORIES                                              │
└─────────────────────────────────────────────────────────────────┘

User clicks "Categories" in navigation
    ↓
Frontend calls: GET /api/v1/categories
    Query: include_system=true, include_documents_count=true
    ↓
Backend:
    - Queries categories table
    - Joins category_translations for user's language
    - Counts documents per category
    ↓
Backend returns:
    [
        {
            id: "uuid",
            reference_key: "category.insurance",
            name: "Insurance",  // Localized
            description: "Insurance policies and documents",
            category_code: "INS",
            color_hex: "#3b82f6",
            icon_name: "shield",
            documents_count: 15,
            is_system: true
        },
        ...
    ]
    ↓
Frontend displays categories in grid with:
    - Color-coded cards
    - Document count badges
    - Edit/Delete buttons (disabled for system categories)


┌─────────────────────────────────────────────────────────────────┐
│ 2. CREATE NEW CATEGORY                                          │
└─────────────────────────────────────────────────────────────────┘

User clicks "Create Category"
    ↓
Modal opens with form:
    - Name (required, 1-100 chars)
    - Description (optional, max 500 chars)
    - Color picker
    - Icon selector
    ↓
User fills form and clicks "Create"
    ↓
Frontend validates input locally
    ↓
Frontend calls: POST /api/v1/categories
    Body: {
        name_en: "Contracts",
        name_de: "Verträge",
        name_ru: "Контракты",
        description_en: "Legal contracts and agreements",
        color_hex: "#10b981",
        icon_name: "document-text"
    }
    ↓
Backend validates with Pydantic:
    - String lengths
    - Hex color format
    - Icon exists in allowed list
    ↓
Backend:
    1. Generates category_code (first 3 letters, uppercase)
    2. Creates category record
    3. Creates category_translation records (en/de/ru)
    4. [Phase 2] Auto-suggests keywords from name/description
    5. Returns created category with translations
    ↓
Frontend:
    - Updates category list
    - Shows success toast
    - Closes modal


┌─────────────────────────────────────────────────────────────────┐
│ 3. EDIT CATEGORY                                                │
└─────────────────────────────────────────────────────────────────┘

User clicks "Edit" on category
    ↓
Modal opens pre-filled with current values
    ↓
User modifies fields and clicks "Save"
    ↓
Frontend calls: PUT /api/v1/categories/{category_id}
    Body: { updated fields }
    ↓
Backend:
    - Updates category record
    - Updates translations
    - [Phase 2] Re-suggests keywords if name changed
    ↓
Frontend:
    - Updates list
    - Shows success toast


┌─────────────────────────────────────────────────────────────────┐
│ 4. DELETE CATEGORY                                              │
└─────────────────────────────────────────────────────────────────┘

***A system category "Other" cannot be deleted - used for allocating un-categorized documents

User clicks "Delete" on category
    ↓
Confirmation dialog shows:
    "Delete category 'Contracts'?
     This category has 5 documents.
     What should happen to these documents?"
    
    Options:
    ○ Move documents to 'Other' category
    ○ Delete documents permanently
    
    [Cancel] [Delete Category]
    ↓
User selects option and confirms
    ↓
Frontend calls: DELETE /api/v1/categories/{category_id}
    Query: move_to_other=true/false
    ↓
Backend:
    IF system category:
        Return 400 "Cannot delete system category"
    ELSE:
        IF move_to_other = true:
            - Find "Other" category
            - Update all documents' primary_category to "Other"
            - Update document_categories entries
        ELSE:
            - Delete all documents in category
        
        - Delete category_translations
        - Delete category_keywords
        - Delete category record
        - Log audit event
    ↓
Frontend:
    - Removes category from list
    - Shows success toast
4.3 Document Upload Flow (Batch Processing)
┌─────────────────────────────────────────────────────────────────┐
│ 1. FILE SELECTION                                               │
└─────────────────────────────────────────────────────────────────┘

User clicks "Upload Documents"
    ↓
Upload page loads with drag-and-drop zone
    ↓
User drags files or clicks to select (supports multi-select)
    ↓
Frontend validates files:
    - File size < 100 MB each
    - Batch size < 10 files
    - Allowed types: PDF, JPEG, PNG, TIFF, DOCX
    ↓
Frontend displays:
    - File list with names, sizes
    - Total file count and size
    - [Analyze] button enabled
    ↓
User clicks "Analyze Documents"


┌─────────────────────────────────────────────────────────────────┐
│ 2. BATCH ANALYSIS (SERVER-SIDE)                                 │
└─────────────────────────────────────────────────────────────────┘

Frontend calls: POST /api/v1/document-analysis/analyze-batch
    Content-Type: multipart/form-data
    Body: FormData with files
    ↓
Backend receives files
    ↓
Backend creates upload_batch record:
    {
        user_id: "uuid",
        total_files: 3,
        status: "processing"
    }
    ↓
FOR EACH file in batch:
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 2.1 FILE VALIDATION                                 │
    └─────────────────────────────────────────────────────┘
    
    Validate file size (< 100 MB)
        ↓
    Check magic bytes:
        PDF: Starts with %PDF
        JPEG: Starts with FF D8 FF
        PNG: Starts with 89 50 4E 47
        ↓
    Verify MIME type matches extension
        ↓
    IF VALIDATION FAILS:
        Mark file as failed
        Continue to next file
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 2.2 TEXT EXTRACTION                                 │
    └─────────────────────────────────────────────────────┘
    
    IF file_type == PDF:
        Try PyMuPDF text extraction
        ↓
        IF extracted_text.length > 100:
            Use native text (fast)
        ELSE:
            Scanned PDF detected
            ↓
            Convert PDF pages to images
            ↓
            [Phase 2] Run Tesseract OCR on each page
            ↓
            Combine page texts
    
    ELSE IF file_type IN [JPEG, PNG, TIFF]:
        [Phase 2] Preprocess image:
            - Convert to grayscale
            - Apply Gaussian blur
            - Otsu's binarization
            - Deskew
        ↓
        [Phase 2] Run Tesseract OCR
    
    ELSE IF file_type == DOCX:
        Extract with python-docx
    
    ↓
    extracted_text = full document text
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 2.3 LANGUAGE DETECTION                              │
    └─────────────────────────────────────────────────────┘
    
    Analyze text with langdetect library
        ↓
    Detect primary language: en/de/ru
        ↓
    Calculate confidence score (0-1)
        ↓
    IF multi-language detected:
        Store secondary languages
    
    ↓
    detected_language = "en"  # Example
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 2.4 KEYWORD EXTRACTION (Current: TF-IDF)            │
    └─────────────────────────────────────────────────────┘
    
    Preprocess text:
        - Convert to lowercase
        - Remove punctuation
        - Split into words
        ↓
    Load stop words from database for detected_language
        ↓
    Filter stop words and single characters
        ↓
    Calculate word frequencies:
        word_freq = Counter(words)
        ↓
    Calculate relevance scores:
        FOR each word:
            relevance = (frequency / total_words) * 100
        ↓
    Sort by relevance descending
        ↓
    Take top 20 keywords
    
    ↓
    keywords = [
        {word: "insurance", count: 15, relevance: 3.2},
        {word: "policy", count: 12, relevance: 2.5},
        ...
    ]
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 2.5 CATEGORY CLASSIFICATION (ML)                    │
    └─────────────────────────────────────────────────────┘
    
    Load user's categories from database
        ↓
    Load category_keywords for each category
        (language-specific, learned from past assignments)
        ↓
    FOR each category:
        ↓
        Calculate overlap score:
            matched_keywords = intersection(
                document_keywords, 
                category_keywords
            )
            ↓
            matched_weight = SUM(
                keyword.weight 
                FOR keyword IN matched_keywords
            )
            ↓
            total_category_weight = SUM(
                all category_keyword weights
            )
            ↓
            overlap_score = matched_weight / total_category_weight
        ↓
        Store: scores[category_id] = overlap_score
    
    ↓
    Sort categories by overlap_score descending
        ↓
    best_category = categories[0]
    best_score = scores[0]
    second_score = scores[1] if exists else 0
    
    ↓
    Apply decision rules:
        confidence_threshold = 0.6  (60%)
        min_gap = 0.2  (20% difference)
        
        IF best_score >= confidence_threshold 
           AND (best_score - second_score) >= min_gap:
            
            suggested_category = best_category
            confidence = best_score * 100  # Convert to percentage
            assigned_to_fallback = false
        
        ELSE:
            # Low confidence or ambiguous
            suggested_category = "Other" category
            confidence = 0
            assigned_to_fallback = true
    
    ↓
    classification_result = {
        suggested_category_id: "uuid",
        confidence: 75.5,  # percentage
        matching_keywords: ["insurance", "policy", "coverage"],
        all_scores: {
            "Insurance": 75.5,
            "Legal": 23.2,
            "Other": 1.3
        },
        assigned_to_fallback: false
    }
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 2.6 FILENAME STANDARDIZATION                        │
    └─────────────────────────────────────────────────────┘
    
    Extract title from first N characters of text:
        title = cleaned_text[:50]
        ↓
    Generate standardized filename:
        pattern: "{Title}_{YYYYMMDD}_{HHMMSS}.{ext}"
        
        Example:
        "Insurance Policy Renewal_20241012_143025.pdf"
    
    ↓
    standardized_filename = result

↓
END FOR EACH file
↓
Backend updates upload_batch:
    - successful_files: count
    - failed_files: count
    - status: "completed"
    ↓
Backend returns analysis results:
{
    batch_id: "uuid",
    total_files: 3,
    successful: 3,
    failed: 0,
    results: [
        {
            temp_id: "temp-uuid-1",
            original_filename: "scan001.pdf",
            standardized_filename: "Insurance Policy_20241012_143025.pdf",
            file_size: 2456789,
            success: true,
            analysis: {
                extracted_text: "...",
                full_text_length: 5432,
                detected_language: "en",
                keywords: [...],
                suggested_category_id: "insurance-uuid",
                confidence: 75.5,
                classification_reasoning: {
                    matching_keywords: ["insurance", "policy"],
                    all_scores: {...},
                    assigned_to_fallback: false
                },
                processing_time_ms: 2450
            }
        },
        ...
    ]
}


┌─────────────────────────────────────────────────────────────────┐
│ 3. USER REVIEW & EDITING                                        │
└─────────────────────────────────────────────────────────────────┘

Frontend receives analysis results
    ↓
Frontend displays review page with cards for each file:
    
    FOR EACH analyzed file:
        ↓
        Card shows:
            - Original filename
            - Suggested new filename (editable)
            - Detected language badge
            - Processing method (OCR/native text)
            
            - Suggested category (auto-selected if confidence ≥ 60%)
            - Confidence badge (color-coded):
                • Green: 80-100% (high confidence)
                • Yellow: 60-79% (medium confidence)
                • Red: <60% (low confidence, fallback)
            
            - Classification reasoning (expandable):
                "Why this category?"
                Matched keywords: insurance, policy, coverage
                [View all scores] ← Expandable detail
                
            - Category selector (multi-select, 1-5 categories)
            - Primary category dropdown (from selected)
            
            - Extracted keywords (editable):
                [insurance] [policy] [renewal] [x remove]
                + Add keyword
            
            - Actions:
                [Edit] [Remove from batch]
        ↓
        User can:
            - Change filename
            - Change suggested category
            - Add/remove categories (1-5)
            - Change primary category
            - Add/remove keywords
            - Remove file from batch


┌─────────────────────────────────────────────────────────────────┐
│ 4. FILENAME UPDATE ON CATEGORY CHANGE                           │
└─────────────────────────────────────────────────────────────────┘

User changes primary category
    ↓
Frontend detects change
    ↓
Frontend regenerates filename:
    - Keeps title part
    - Keeps timestamp
    - Updates with new category_code (if available)
    
    Example:
    Insurance Policy_20241012_143025.pdf
        ↓ User changes to "Legal" category
    Legal Document_20241012_143025.pdf
    ↓
Frontend updates filename input field


┌─────────────────────────────────────────────────────────────────┐
│ 5. CONFIRM UPLOAD (PERMANENT STORAGE)                           │
└─────────────────────────────────────────────────────────────────┘

User clicks "Confirm Upload"
    ↓
Frontend calls: POST /api/v1/document-analysis/confirm-upload
    Body: {
        temp_id: "temp-uuid-1",
        title: "Insurance Policy Renewal",
        filename: "Insurance_Policy_20241012_143025.pdf",
        category_ids: ["insurance-uuid", "legal-uuid"],
        primary_category_id: "insurance-uuid",
        confirmed_keywords: ["insurance", "policy", "renewal"]
    }
    ↓
Backend processes confirmation:
    
    ┌─────────────────────────────────────────────────────┐
    │ 5.1 RETRIEVE TEMPORARY ANALYSIS                     │
    └─────────────────────────────────────────────────────┘
    
    Load temp analysis from cache/temp storage
        ↓
    Retrieve: extracted_text, detected_language, suggested_category, etc.
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 5.2 GOOGLE DRIVE UPLOAD                             │
    └─────────────────────────────────────────────────────┘
    
    [Phase 3] Check user's Google Drive permission
        ↓
    [Phase 3] Check storage quota available
        ↓
    [Phase 3] Get/Create category folder in Drive:
        /BoniDoc/Insurance/
        ↓
    [Phase 3] Upload file to Drive:
        - Returns: drive_file_id, web_view_link
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 5.3 CREATE DATABASE RECORDS                         │
    └─────────────────────────────────────────────────────┘
    
    Create document record:
        INSERT INTO documents (
            title, file_name, file_size, mime_type,
            drive_file_id, web_view_link,
            detected_language, processing_status,
            user_id, batch_id
        )
        ↓
    document_id = generated UUID
    
    ↓
    Create document_categories records:
        FOR EACH category_id IN category_ids:
            INSERT INTO document_categories (
                document_id,
                category_id,
                is_primary: (category_id == primary_category_id),
                assigned_by_ai: (category_id == suggested_category_id)
            )
    
    ↓
    Create document_keywords records:
        FOR EACH keyword IN confirmed_keywords:
            - Find or create in keywords table
            - Create document_keywords link
            - Store relevance_score
    
    ↓
    Create document_languages record:
        INSERT INTO document_languages (
            document_id,
            language_code: detected_language,
            confidence_score,
            is_primary: true,
            extracted_text,
            keywords: JSON(keywords)
        )
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 5.4 CLASSIFICATION LOGGING                          │
    └─────────────────────────────────────────────────────┘
    
    [Phase 2] Record classification decision:
        INSERT INTO document_classification_log (
            document_id,
            suggested_category_id: (from analysis),
            actual_category_id: primary_category_id,
            confidence_score,
            matching_keywords: JSON,
            all_scores: JSON,
            was_correct: (suggested == actual)
        )
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 5.5 ML LEARNING UPDATE                              │
    └─────────────────────────────────────────────────────┘
    
    [Phase 2] IF user accepted suggestion (was_correct = true):
        
        Learn from correct assignment:
            FOR EACH keyword IN confirmed_keywords:
                ↓
                Find in category_keywords:
                    WHERE category_id = actual_category
                    AND keyword = keyword
                    AND language_code = detected_language
                ↓
                IF EXISTS:
                    # Reinforce: increase weight
                    new_weight = current_weight * 1.1  (10% boost)
                    new_weight = MIN(new_weight, 5.0)  (cap at 5.0)
                    match_count = match_count + 1
                    last_matched_at = NOW()
                    ↓
                    UPDATE category_keywords
                ELSE:
                    # New keyword for this category
                    INSERT INTO category_keywords (
                        category_id,
                        keyword,
                        language_code,
                        weight: 1.0,  (initial weight)
                        match_count: 1,
                        is_system_default: false
                    )
    
    ELSE IF user corrected suggestion (was_correct = false):
        
        Learn from correction:
            
            # Penalize incorrect category
            FOR EACH keyword IN matching_keywords:
                UPDATE category_keywords
                SET weight = weight * 0.95  (5% penalty)
                WHERE category_id = suggested_category
                AND keyword = keyword
            
            ↓
            # Reinforce correct category
            FOR EACH keyword IN confirmed_keywords:
                (Same as "correct assignment" above)
                WHERE category_id = actual_category
    
    ↓
    ┌─────────────────────────────────────────────────────┐
    │ 5.6 AUDIT LOGGING                                   │
    └─────────────────────────────────────────────────────┘
    
    INSERT INTO audit_logs (
        user_id,
        action: "document_uploaded",
        resource_type: "document",
        resource_id: document_id,
        new_values: JSON({
            title, categories, keywords
        }),
        status: "success"
    )
    
    ↓
    Backend returns success response:
        {
            document_id: "uuid",
            drive_file_id: "google-drive-id",
            view_link: "https://drive.google.com/file/d/..."
        }
    ↓
    Frontend:
        - Shows success toast
        - Removes file from batch
        - Updates upload progress
        - If all files confirmed: redirect to documents list


┌─────────────────────────────────────────────────────────────────┐
│ 6. LEARNING IMPACT ON FUTURE UPLOADS                            │
└─────────────────────────────────────────────────────────────────┘

User uploads similar document in future
    ↓
Same classification process runs
    ↓
BUT now category_keywords have updated weights:
    
    Example: "Insurance" category
    
    BEFORE (first upload):
        keyword "policy" → weight: 1.0
        
    AFTER (user confirmed 5 insurance documents):
        keyword "policy" → weight: 1.61  (1.0 * 1.1^5)
        match_count: 5
    
    ↓
    Overlap score calculation gives higher weight to learned keywords
    ↓
    Classification confidence increases
    ↓
    System becomes more accurate over time
    ↓
    Future insurance documents more likely to be suggested correctly
4.4 Document Search & Retrieval Flow
┌─────────────────────────────────────────────────────────────────┐
│ SEARCH FLOW (Planned - Phase 4)                                 │
└─────────────────────────────────────────────────────────────────┘

User navigates to Documents page
    ↓
Page loads with:
    - Search bar
    - Filters (category, date range, language, tags)
    - Sort options (date, name, relevance)
    - View options (grid, list)
    ↓
User enters search query: "insurance policy 2024"
    ↓
Frontend calls: GET /api/v1/documents/search
    Query: {
        q: "insurance policy 2024",
        category_ids: ["insurance-uuid"],
        date_from: "2024-01-01",
        date_to: "2024-12-31",
        language: "en",
        limit: 20,
        offset: 0
    }
    ↓
Backend processes search:
    
    Parse query into keywords: ["insurance", "policy", "2024"]
        ↓
    Build SQL query with filters:
        SELECT d.*
        FROM documents d
        JOIN document_keywords dk ON d.id = dk.document_id
        JOIN keywords k ON dk.keyword_id = k.id
        WHERE k.keyword IN ('insurance', 'policy', '2024')
        AND d.category_id IN (category_ids)
        AND d.created_at BETWEEN date_from AND date_to
        AND d.primary_language = 'en'
        GROUP BY d.id
        ORDER BY COUNT(*) DESC  -- Relevance score
        LIMIT 20 OFFSET 0
        ↓
    Load document metadata
        ↓
    Calculate relevance scores
        ↓
    Log search to search_history table
    ↓
Backend returns:
    {
        total_results: 15,
        page: 1,
        per_page: 20,
        documents: [
            {
                id: "uuid",
                title: "Insurance Policy Renewal",
                filename: "Insurance_Policy_20241012.pdf",
                categories: [
                    {id: "...", name: "Insurance", is_primary: true}
                ],
                keywords: ["insurance", "policy", "renewal"],
                detected_language: "en",
                file_size: 2456789,
                created_at: "2024-10-12T14:30:25Z",
                thumbnail_url: "...",
                relevance_score: 0.95
            },
            ...
        ]
    }
    ↓
Frontend displays:
    - Document cards with thumbnails
    - Highlighted matching keywords
    - Category badges
    - File size and date
    - Relevance indicator
    ↓
User clicks document
    ↓
Navigate to: /documents/{document_id}


┌─────────────────────────────────────────────────────────────────┐
│ DOCUMENT DETAIL VIEW (Phase 3)                                  │
└─────────────────────────────────────────────────────────────────┘

Frontend calls: GET /api/v1/documents/{document_id}
    ↓
Backend:
    - Verifies user owns document
    - Loads document with all relationships
    - Updates last_accessed_at
    - Increments download_count
    ↓
Backend returns complete document data:
    {
        id, title, filename, file_size,
        categories: [...],
        keywords: [...],
        detected_language,
        created_at, updated_at,
        drive_file_id,
        web_view_link,
        classification_info: {
            suggested_category,
            actual_category,
            confidence,
            was_correct
        }
    }
    ↓
Frontend displays:
    - Document header (title, date, size)
    - Category badges (primary highlighted)
    - Keywords with relevance scores
    - Classification information (if available)
    - Action buttons:
        • View in Drive
        • Download
        • Edit metadata
        • Delete
    ↓
User clicks "Download"
    ↓
Frontend calls: GET /api/v1/documents/{document_id}/download
    ↓
Backend:
    - Verifies ownership
    - Checks file exists in Drive
    - Generates temporary download link (1-hour expiry)
    - Logs download to audit_logs
    ↓
Backend returns: temporary_download_url
    ↓
Frontend opens URL in new tab
    ↓
Browser downloads file

5. File Upload Processing Logic
5.1 Uniform Filename Generation
Objective: Create consistent, standardized filenames for all documents
Process:
python# backend/app/services/document_analysis_service.py

def generate_standardized_filename(
    extracted_text: str,
    original_filename: str,
    category_code: Optional[str] = None
) -> str:
    """
    Generate standardized filename from document content.
    
    Pattern: {Title}_{YYYYMMDD}_{HHMMSS}.{ext}
    Optional: {CategoryCode}_{Title}_{YYYYMMDD}_{HHMMSS}.{ext}
    """
    
    # 1. Extract title from first portion of text
    title = extract_title_from_text(extracted_text, max_length=50)
    
    # 2. Clean title for filename
    title_clean = clean_for_filename(title)
    # - Remove special characters: \ / : * ? " < > |
    # - Replace spaces with underscores
    # - Remove multiple consecutive underscores
    # - Truncate to 50 characters
    
    # 3. Generate timestamp
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")  # 20241012
    time_str = now.strftime("%H%M%S")  # 143025
    
    # 4. Get file extension from original filename
    extension = get_extension(original_filename)
    
    # 5. Build filename
    if category_code:
        # With category prefix
        filename = f"{category_code}_{title_clean}_{date_str}_{time_str}.{extension}"
    else:
        # Without category prefix
        filename = f"{title_clean}_{date_str}_{time_str}.{extension}"
    
    # 6. Ensure filename length < 255 characters
    if len(filename) > 255:
        # Truncate title part
        max_title_length = 255 - len(f"_{date_str}_{time_str}.{extension}")
        if category_code:
            max_title_length -= len(f"{category_code}_")
        title_clean = title_clean[:max_title_length]
        # Rebuild filename
        filename = f"{category_code}_{title_clean}_{date_str}_{time_str}.{extension}" if category_code else f"{title_clean}_{date_str}_{time_str}.{extension}"
    
    return filename
Examples:
Original: "scan001.pdf"
Extracted Text: "Insurance Policy Renewal Notice..."
→ Standardized: "Insurance_Policy_Renewal_20241012_143025.pdf"

Original: "IMG_2024_05_23.jpg"
Extracted Text: "Mietvertrag für Wohnung..."
Category: Real Estate (RES)
→ Standardized: "RES_Mietvertrag_Wohnung_20241012_143025.jpg"

Original: "document (1) copy final.docx"
Extracted Text: "Employment Contract between..."
→ Standardized: "Employment_Contract_20241012_143025.docx"
5.2 Keyword Extraction Logic
Current Implementation: Frequency-Based Extraction (TF-IDF planned for simplification in Phase 2)
Objective: Extract 10-20 most relevant keywords from document text
Process:
python# backend/app/services/ml_keyword_service.py

def extract_keywords(
    text: str,
    language_code: str,
    max_keywords: int = 20
) -> List[KeywordResult]:
    """
    Extract relevant keywords using frequency-based analysis.
    
    Returns list of keywords with relevance scores.
    """
    
    # STEP 1: Text Preprocessing
    text_lower = text.lower()
    
    # Remove punctuation
    text_clean = remove_punctuation(text_lower)
    
    # Split into words
    words = text_clean.split()
    
    # STEP 2: Stop Word Filtering
    # Load stop words from database for this language
    stop_words = load_stop_words(language_code)
    # Database query:
    # SELECT word FROM stop_words 
    # WHERE language_code = ? AND is_active = true
    
    # Filter out:
    # - Stop words
    # - Single characters
    # - Numbers only
    # - Words < 3 characters
    filtered_words = [
        word for word in words
        if word not in stop_words
        and len(word) >= 3
        and not word.isdigit()
        and contains_letters(word)
    ]
    
    # STEP 3: Frequency Counting
    word_counts = Counter(filtered_words)
    
    # Require minimum 2 occurrences
    word_counts = {
        word: count 
        for word, count in word_counts.items() 
        if count >= 2
    }
    
    # STEP 4: Relevance Scoring
    total_words = len(filtered_words)
    
    keyword_scores = []
    for word, count in word_counts.items():
        relevance = (count / total_words) * 100
        
        keyword_scores.append({
            'word': word,
            'count': count,
            'relevance': round(relevance, 2)
        })
    
    # STEP 5: Sort & Return Top N
    keyword_scores.sort(key=lambda x: x['relevance'], reverse=True)
    
    top_keywords = keyword_scores[:max_keywords]
    
    return top_keywords
Example:
Input Text:
"Insurance policy renewal notice. Your insurance policy number 
12345 is due for renewal. Please review the policy terms and 
conditions. The policy coverage includes health insurance and 
life insurance. Policy premium payment is due by December 31."

Language: English

Processing:
1. Lowercase & clean
2. Split: ["insurance", "policy", "renewal", "notice", ...]
3. Filter stop words: ["your", "is", "for", "the", "and", "by"] removed
4. Count frequencies:
   - "insurance": 4
   - "policy": 6
   - "renewal": 2
   - "coverage": 1  ← Below minimum, excluded
5. Calculate relevance:
   - total_words (after filtering): 25
   - "policy": (6/25) * 100 = 24.0%
   - "insurance": (4/25) * 100 = 16.0%
   - "renewal": (2/25) * 100 = 8.0%
6. Sort & return top 20

Output:
[
    {word: "policy", count: 6, relevance: 24.0},
    {word: "insurance", count: 4, relevance: 16.0},
    {word: "renewal", count: 2, relevance: 8.0},
    {word: "premium", count: 2, relevance: 8.0},
    {word: "payment", count: 2, relevance: 8.0},
    ...
]
5.3 ML Categorization Process
Objective: Automatically suggest the most appropriate category for a document
Algorithm: Keyword Overlap Scoring
Process:
python# backend/app/services/ml_category_service.py

def classify_document(
    document_keywords: List[str],
    detected_language: str,
    user_categories: List[Category]
) -> ClassificationResult:
    """
    Classify document based on keyword overlap with categories.
    
    Uses learned keyword weights from past user assignments.
    """
    
    # STEP 1: Load Category Keywords
    category_scores = {}
    category_matches = {}
    
    for category in user_categories:
        # Load learned keywords for this category
        category_keywords = load_category_keywords(
            category_id=category.id,
            language_code=detected_language
        )
        # Database query:
        # SELECT keyword, weight, match_count 
        # FROM category_keywords
        # WHERE category_id = ? AND language_code = ?
        
        # STEP 2: Calculate Keyword Overlap
        matched_keywords = []
        matched_weight = 0.0
        
        for doc_keyword in document_keywords:
            for cat_keyword in category_keywords:
                if doc_keyword.lower() == cat_keyword['keyword'].lower():
                    matched_keywords.append(doc_keyword)
                    matched_weight += cat_keyword['weight']
        
        # STEP 3: Calculate Overlap Score
        total_category_weight = sum(
            kw['weight'] for kw in category_keywords
        )
        
        if total_category_weight > 0:
            overlap_score = matched_weight / total_category_weight
        else:
            overlap_score = 0.0
        
        category_scores[category.id] = overlap_score
        category_matches[category.id] = matched_keywords
    
    # STEP 4: Sort Categories by Score
    sorted_categories = sorted(
        category_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # STEP 5: Apply Decision Rules
    confidence_threshold = 0.6  # 60% minimum
    min_gap = 0.2  # 20% gap between top 2
    
    if len(sorted_categories) == 0:
        # No categories available
        return assign_to_fallback("other")
    
    best_category_id = sorted_categories[0][0]
    best_score = sorted_categories[0][1]
    
    second_score = sorted_categories[1][1] if len(sorted_categories) > 1 else 0.0
    
    # Decision Logic
    if best_score >= confidence_threshold and (best_score - second_score) >= min_gap:
        # High confidence assignment
        return ClassificationResult(
            suggested_category_id=best_category_id,
            confidence=best_score,
            matching_keywords=category_matches[best_category_id],
            all_scores=category_scores,
            assigned_to_fallback=False
        )
    else:
        # Low confidence or ambiguous → Assign to "Other"
        other_category = find_other_category(user_categories)
        return ClassificationResult(
            suggested_category_id=other_category.id,
            confidence=0.0,
            matching_keywords=[],
            all_scores=category_scores,
            assigned_to_fallback=True
        )
Example Classification:
Document Keywords:
["policy", "insurance", "renewal", "premium", "coverage"]

User Categories with Learned Keywords:

Insurance Category:
  - insurance: weight 3.0, match_count 15
  - policy: weight 2.5, match_count 12
  - coverage: weight 2.0, match_count 8
  - premium: weight 1.8, match_count 7
  - claim: weight 1.5, match_count 5
  Total weight: 10.8

Legal Category:
  - contract: weight 3.0, match_count 10
  - agreement: weight 2.5, match_count 8
  - clause: weight 2.0, match_count 6
  Total weight: 7.5

Banking Category:
  - account: weight 3.0, match_count 12
  - transaction: weight 2.5, match_count 9
  - balance: weight 2.0, match_count 7
  Total weight: 7.5

Calculation:

Insurance:
  - Matched: insurance (3.0), policy (2.5), coverage (2.0), premium (1.8)
  - Matched weight: 9.3
  - Total weight: 10.8
  - Overlap score: 9.3 / 10.8 = 0.861 (86.1%)

Legal:
  - Matched: none
  - Overlap score: 0.0 / 7.5 = 0.0 (0%)

Banking:
  - Matched: none
  - Overlap score: 0.0 / 7.5 = 0.0 (0%)

Sorted:
1. Insurance: 86.1%
2. Legal: 0%
3. Banking: 0%

Decision:
  best_score = 0.861 (86.1%)
  second_score = 0.0
  gap = 0.861 - 0.0 = 0.861 (86.1%)
  
  0.861 >= 0.6 (threshold) ✓
  0.861 >= 0.2 (min_gap) ✓
  
  → Suggest: Insurance category
  → Confidence: 86.1%
  → Matching keywords: ["insurance", "policy", "coverage", "premium"]
  → Assigned to fallback: false
5.4 ML Learning Mechanism
Objective: Improve classification accuracy by learning from user behavior
Learning Scenarios:
Scenario 1: User Accepts Suggestion (Correct Prediction)
python# backend/app/services/category_learning_service.py

def learn_from_assignment(
    document_id: str,
    category_id: str,
    document_keywords: List[str],
    language_code: str
):
    """
    Reinforce keyword associations when user accepts suggestion.
    """
    
    for keyword in document_keywords:
        # Find existing keyword weight
        existing = find_category_keyword(
            category_id=category_id,
            keyword=keyword,
            language_code=language_code
        )
        
        if existing:
            # REINFORCE: Increase weight
            new_weight = existing.weight * 1.1  # 10% boost
            new_weight = min(new_weight, 5.0)  # Cap at 5.0
            
            update_category_keyword(
                id=existing.id,
                weight=new_weight,
                match_count=existing.match_count + 1,
                last_matched_at=datetime.now()
            )
        else:
            # NEW ASSOCIATION: Create keyword entry
            create_category_keyword(
                category_id=category_id,
                keyword=keyword,
                language_code=language_code,
                weight=1.0,  # Initial weight
                match_count=1,
                is_system_default=False
            )
Example:
User uploads insurance document with keywords:
["policy", "insurance", "renewal"]

System suggests: Insurance category (75% confidence)
User accepts suggestion

Before:
  Insurance category keywords:
    - policy: weight 2.0, match_count 10
    - insurance: weight 1.8, match_count 8
    - renewal: weight 0.0 (not in category yet)

After learning:
  Insurance category keywords:
    - policy: weight 2.2 (2.0 * 1.1), match_count 11
    - insurance: weight 1.98 (1.8 * 1.1), match_count 9
    - renewal: weight 1.0 (newly added), match_count 1

Impact:
  Next similar document will have higher overlap score
  → More confident suggestions
  → Better user experience
Scenario 2: User Corrects Suggestion (Wrong Prediction)
pythondef learn_from_correction(
    document_id: str,
    from_category_id: str,  # Incorrect suggestion
    to_category_id: str,    # User's choice
    document_keywords: List[str],
    matching_keywords: List[str],  # Keywords that led to wrong suggestion
    language_code: str
):
    """
    Adjust weights when user corrects classification.
    
    Penalize incorrect category, reinforce correct category.
    """
    
    # PART 1: Penalize incorrect category
    for keyword in matching_keywords:
        existing = find_category_keyword(
            category_id=from_category_id,
            keyword=keyword,
            language_code=language_code
        )
        
        if existing:
            # PENALIZE: Decrease weight
            new_weight = existing.weight * 0.95  # 5% penalty
            new_weight = max(new_weight, 0.1)  # Minimum 0.1
            
            update_category_keyword(
                id=existing.id,
                weight=new_weight
                # Don't update match_count (wasn't a match)
            )
    
    # PART 2: Reinforce correct category
    for keyword in document_keywords:
        # Same logic as learn_from_assignment()
        # Increase weights in correct category
        ...
Example:
User uploads document with keywords:
["policy", "employee", "benefits", "contract"]

System suggests: Insurance category (65% confidence)
  Reason: "policy" matched strongly

User corrects to: Employment category

Before:
  Insurance category:
    - policy: weight 2.5, match_count 12
  
  Employment category:
    - employee: weight 2.0, match_count 8
    - benefits: weight 1.8, match_count 6
    - contract: weight 1.5, match_count 5
    - policy: weight 0.0 (not in category)

After learning:
  Insurance category:
    - policy: weight 2.375 (2.5 * 0.95), match_count 12
    (Penalized because led to wrong suggestion)
  
  Employment category:
    - employee: weight 2.2 (2.0 * 1.1), match_count 9
    - benefits: weight 1.98 (1.8 * 1.1), match_count 7
    - contract: weight 1.65 (1.5 * 1.1), match_count 6
    - policy: weight 1.0 (newly added), match_count 1
    (All reinforced in correct category)

Impact:
  Future documents with similar keywords:
    - "policy" now associated with both categories
    - But stronger association with Employment in this context
    - System learns that "policy" + "employee" → Employment
    - Not just "policy" → Insurance
5.5 User-Driven Classification Override
User Controls During Review:

Change Suggested Category

User can reject ML suggestion
Select any category from dropdown
System learns from this correction


Multi-Category Assignment

User can add 1-5 categories
One must be marked as primary
System learns associations for all selected categories


Edit Keywords

User can add relevant keywords ML missed
User can remove irrelevant keywords ML extracted
Edited keywords used for learning


Edit Filename

User can modify generated filename
Title extraction improves from feedback (future enhancement)



Learning from Override:
Every user action is recorded in document_classification_log:

{
    document_id: "uuid",
    suggested_category_id: "insurance-uuid",  # What ML suggested
    actual_category_id: "employment-uuid",     # What user chose
    confidence_score: 0.65,                    # ML confidence
    matching_keywords: ["policy", "premium"],  # Why ML suggested Insurance
    all_scores: {...},                         # All category scores
    was_correct: false,                        # User corrected
    correction_timestamp: "2024-10-12T14:30:25Z"
}

This data feeds back into learning algorithms:
- Adjust weights in both categories
- Improve future suggestions
- Calculate accuracy metrics
- Identify weak keywords
Daily Metrics Calculation (Background Job):
python# Runs daily at midnight
def calculate_daily_metrics():
    """
    Calculate classification performance metrics.
    """
    
    for category in all_categories:
        # Query today's classifications
        logs = query_classification_logs(
            category_id=category.id,
            date=today()
        )
        
        total = len(logs)
        correct = sum(1 for log in logs if log.was_correct)
        
        accuracy_rate = (correct / total) if total > 0 else 0.0
        avg_confidence = mean(log.confidence_score for log in logs)
        
        # Identify keywords in misclassifications
        misclassified_logs = [log for log in logs if not log.was_correct]
        common_keywords = Counter()
        for log in misclassified_logs:
            common_keywords.update(log.matching_keywords)
        
        # Suggest keywords to add (from correctly classified docs)
        correct_logs = [log for log in logs if log.was_correct]
        suggested_keywords = extract_common_keywords(correct_logs)
        
        # Store metrics
        upsert_classification_metrics(
            category_id=category.id,
            date=today(),
            total_assignments=total,
            correct_assignments=correct,
            accuracy_rate=accuracy_rate,
            avg_confidence=avg_confidence,
            keyword_suggestions=suggested_keywords
        )
User Dashboard Showing Learning Progress:
Category Performance (Last 30 Days):

Insurance
  ✓ 85% accuracy (34/40 correct)
  📈 Improving (+5% this week)
  🎯 Avg confidence: 78%
  💡 Suggested keywords: "policyholder", "deductible"

Employment
  ✓ 72% accuracy (18/25 correct)
  📉 Needs attention (-3% this week)
  🎯 Avg confidence: 65%
  💡 Suggested keywords: "salary", "termination"
  ⚠️ Often confused with: Legal category

Legal
  ✓ 90% accuracy (27/30 correct)
  ✨ Excellent performance
  🎯 Avg confidence: 82%

6. Implementation Standards
6.1 Code Quality Checklist (MANDATORY Before Every Commit)
✅ Modular Structure: File serves single functionality, <300 lines
✅ Design Separation: Zero design elements in core files
✅ No Hardcoding: All configuration values from database/config files
✅ Production Ready: No fallbacks, workarounds, or TODO comments
✅ Multi-Input Support: Mouse, keyboard, and touch functionality tested
✅ Documentation: File header, function comments, complex logic explained
✅ Naming Standards: Concise names without marketing terms
✅ Test Coverage: Unit tests written and passing
✅ Code Start: Start each file with a comment line: file location/file name
✅ Prior Code Check: Before each code output, check if similar functions already exist. Amend/update them instead of adding new duplicate functions
6.2 Database Standards
Configuration Validation:
✅ Dynamic Categories: Default categories loaded from database
✅ User Settings: All user preferences stored in database
✅ System Configuration: Feature flags and settings configurable
✅ Localization Data: All text strings externalized and translatable
✅ No Static Data: Zero hardcoded business rules or data
Migration Standards:

Always include downgrade() implementation
Add indexes for all foreign keys
Provide default values for NOT NULL columns
Test both upgrade and downgrade before committing
Never break the migration chain

6.3 Code Review Requirements
Before Any Pull Request:
✅ Functionality Review: Code implements requirements correctly
✅ Architecture Compliance: Follows modular structure principles
✅ Performance Review: Meets defined performance benchmarks
✅ Security Review: No security vulnerabilities or data exposure
✅ Documentation Review: Adequate comments and documentation
✅ Standards Compliance: Follows all development standards
6.4 Commit Message Format
bashtype: brief description (max 72 characters)

- Detail 1: Specific change made
- Detail 2: Reason for change  
- Detail 3: Impact or benefit
- Root cause analysis if fixing a bug

Types: feat, fix, refactor, docs, test, security, perf
6.5 Error Handling Standards
Backend:

Always return structured error responses with clear messages
Never expose stack traces or internal details to users
Log detailed errors internally with context
Provide actionable error messages ("Try X" not "Error occurred")

Frontend:

Parse complex error objects into user-friendly messages
Never display "[object Object]" to users
Show specific field validation errors
Provide recovery actions where possible

6.6 Comment Standards
Professional Comments:
python# GOOD: Clear, professional, explains "why"
# Calculate overlap score between document and category keywords
# Higher scores indicate better category match

# BAD: Implementation details, obvious statements
# This function loops through keywords and adds them up

7. Quality Control Process
7.1 Pre-Commit Checklist
Code Quality:

Run linter: flake8 . (backend) or npm run lint (frontend)
Check for hardcoded values: grep -r "TODO\|FIXME\|HACK" .
Verify file length: All files <300 lines
Check for duplicate functions: Search for similar function names
Verify imports at file top
Confirm file header comment present

Functionality:

Test locally: All affected features work
Test edge cases: Invalid inputs, empty states, large datasets
Test multi-language: Verify translations load correctly
Test dark mode: UI renders correctly in both themes
Test mobile: Responsive design on small screens

Security:

No sensitive data in code (API keys, passwords)
No user input used directly in queries
All file uploads validated
Rate limiting present on new endpoints
Audit logging added for sensitive operations

7.2 Post-Deployment Verification
Health Checks:
bash# Backend health
curl https://api.bonidoc.com/health
# Expected: {"status":"healthy","database":"connected"}

# Frontend health  
curl https://bonidoc.com
# Expected: 200 OK, loads landing page

# Database health
psql $DATABASE_URL -c "SELECT COUNT(*) FROM categories WHERE is_system = true;"
# Expected: 9 (system categories)
Smoke Tests:

Login with Google OAuth → Success
Navigate to Categories → List loads
Create test category → Saves successfully
Upload test document → Analyzes successfully
Logout → Redirects to landing page

7.3 Performance Benchmarks
Target Metrics:

API response time (p95): <200ms
Database query time (p95): <100ms
Document upload (single file): <5s
Batch analysis (10 files): <30s
OCR processing (per page): <10s
Page load time: <2s


8. Current Development Status
8.1 Completed Features ✅
Infrastructure (Production):

Google Cloud Run deployment (backend + frontend)
Supabase PostgreSQL database (26 tables)
GitHub Actions CI/CD pipeline
Alembic migrations (10 migrations, clean chain)
Google OAuth authentication
JWT-based session management

Core Features (Production):

User management (profile, settings, deactivation)
Multi-language categories (9 system categories in en/de/ru)
Category CRUD with translations
Dark mode theme
Settings & localization API
Comprehensive audit logging
Multi-category assignment architecture (1-5 categories per document)

Document Processing (Partial):

Batch upload analysis endpoint (working)
ML keyword extraction (TF-IDF algorithm)
Standardized filename generation
ML category learning framework (structure in place)

8.2 In Progress ⏳
Document Upload:

Google Drive storage integration (testing)
Confirm upload endpoint (stores permanently)
Document list view with filters
Document detail page
Download functionality

Security Enhancements:

Session management implementation
Rate limiting service
Field-level encryption for OAuth tokens
Security headers middleware

8.3 Known Issues
Issue: JSONB Import Missing

Status: Fixed 2025-10-12
Solution: Added JSONB import to database models


9. Next Development Milestones
9.1 Phase 1: Security Foundation (Week 1)
Objective: Lock down the platform before adding features
Database Cleanup:

Drop unused tables
Rename category_term_weights → category_keywords
Add encryption columns
Create user_sessions table
Add security columns to audit_logs

Security Services:

Encryption service (Fernet AES-256)
Session management service
Rate limiting service
File validation service
Security monitoring service

Authentication Updates:

Replace localStorage with httpOnly cookies
Reduce access token expiry to 15 minutes
Add refresh token with 7-day expiry
Implement session tracking

Security Middleware:

Security headers
Rate limiting on all endpoints
Input sanitization with Pydantic
Comprehensive audit logging

9.2 Phase 2: Document Processing & Classification (Week 2)
OCR & Text Extraction:

Add Tesseract and PyMuPDF dependencies
Implement image preprocessing
Create OCR service
Update document analysis for scanned PDFs

Classification Engine:

Implement keyword overlap scoring
Create classification database tables
Populate system keywords (150+ in en/de/ru)
Apply confidence thresholds

Category Learning:

Record all classification decisions
Learn from correct suggestions
Learn from corrections
Calculate daily metrics

9.3 Phase 3: Google Drive Integration (Week 3)
Drive Schema:

Create google_drive_folders table
Create google_drive_sync_status table
Add Drive columns to documents/users tables

Drive Service:

Initialize Drive with folder structure
Upload files to category folders
Generate temporary download links
Track storage quotas

Frontend:

Drive connection UI
Storage quota display
Document detail page with Drive links

9.4 Phase 4: Production Deployment & Monitoring (Week 4)
Security Hardening:

Enable Cloud Armor
Run penetration testing
Update privacy policy

Monitoring:

Setup dashboards
Configure alerts
Setup error tracking

Documentation:

Update API docs
Create user guide
Create admin guide


10. Progress Tracking Protocol
10.1 Progress Log Format
After Each Significant Implementation:

Complete the feature/fix
Test thoroughly
Commit with proper message
Deploy (if applicable)
Verify deployment
Update this document

10.2 Progress Log (Chronological)
2025-10-12 : [Phase 1] - Database Cleanup & JSONB Import Fix
  - Added missing JSONB import to database models
  - Fixed NameError preventing container startup
  - Deployed to production successfully
  - Impact: Backend container now starts correctly

[Next entries will be added here as development progresses]

11. Configuration & Deployment
11.1 Environment Variables
Backend (Required):
bashDATABASE_URL="postgresql://..."
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
JWT_SECRET_KEY="..."
ENCRYPTION_KEY="..."
ENVIRONMENT="production"
Frontend (Required):
bashNEXT_PUBLIC_API_URL="https://api.bonidoc.com"
11.2 Deployment Process
Automated:
bashgit push origin main
# GitHub Actions handles deployment
# Completes in 3-5 minutes
11.3 Database Migrations
bashcd backend
alembic current
alembic upgrade head
psql $DATABASE_URL -c "\dt" | wc -l  # Should be 26+

12. Project Instructions Summary
I understand and will follow these principles precisely:

Files modular (<300 lines), production-ready only
No hardcoded values, all from database
Root cause fixes, no workarounds
Check for duplicates before creating
Professional comments explaining "why"
Security-first: encryption, httpOnly cookies, rate limiting
One step at a time, wait for confirmation
Precise code replacements with context


13. Next Steps
Immediate Actions:
Step 1: Verify Current Deployment

Confirm backend health endpoint responds
Verify database migration status
Check all 26 tables exist
Verify system categories populated