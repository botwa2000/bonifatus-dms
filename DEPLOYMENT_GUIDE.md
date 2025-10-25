# BoniDoc - Development & Deployment Guide
Version: 15.0 - HETZNER PRODUCTION
Last Updated: October 24, 2025
Status: Phase 1 Complete | Phase 2A Complete (OCR) | PRODUCTION ON HETZNER VPS
Domain: https://bonidoc.com
Hosting: Hetzner VPS + Local PostgreSQL 16

## Table of Contents

1. Executive Summary & Project Objectives
2. Technology Stack & Architecture Overview
3. System Principles & Implementation Standards
4. Development Phases & Milestones
5. Current Status & Next Steps
6. Quality Control & Deployment Process

---

## 1. Executive Summary & Project Objectives

### 1.1 Project Vision
BoniDoc is a professional document management system that combines secure storage, intelligent categorization, and multi-language support. The system learns from user behavior to improve accuracy over time, providing a privacy-first solution where users maintain full ownership of their data.

### 1.2 Core Objectives

**Security-First Architecture**
- Protect user data at every layer (transport, storage, access)
- Implement field-level encryption for sensitive information
- Use httpOnly cookies to prevent XSS token theft
- Comprehensive audit logging for accountability
- Rate limiting to prevent abuse

**Intelligent Document Processing**
- Extract text from documents using intelligent two-stage OCR (PyMuPDF + quality check + Tesseract)
- Automatically detect document language (EN/DE/RU)
- Extract relevant keywords using frequency analysis
- Suggest appropriate categories based on content
- Learn from user corrections to improve accuracy

**Multi-Language Support**
- Full UI/UX in English, German, and Russian
- Language-specific document processing and categorization
- All text strings externalized for easy translation
- Stop words and keywords tailored per language

**User-Owned Storage**
- Documents stored in user's personal Google Drive
- System never stores document files on our servers
- Users maintain full control and ownership
- Respects privacy and data sovereignty

**Zero Technical Debt**
- No hardcoded values in source code
- No temporary workarounds or TODO comments in production
- All configuration stored in database
- Production-ready code only

### 1.3 User Experience Goals
- One-click batch upload with automatic analysis
- Clear visual feedback on categorization confidence
- Multi-category assignment (unlimited categories per document)
- System suggests ONE primary category, user can approve/change and add more
- Learning system that improves with use
- Mobile-responsive interface with dark mode
- Accessible via mouse, keyboard, and touch

---

## 2. Technology Stack & Architecture Overview

### 2.1 Technology Stack

**Backend**
- Framework: FastAPI (Python 3.11+)
- Database: PostgreSQL 16 (Local Hetzner with SSL)
- Authentication: Google OAuth 2.0 + JWT with httpOnly cookies
- Storage: Google Drive API (user-owned storage)
- OCR: PyMuPDF (native text) + Tesseract (scanned docs) with intelligent quality detection
- Encryption: Fernet (AES-256) for field-level encryption
- Migrations: Alembic
- Deployment: Docker containers on Hetzner VPS

**Frontend**
- Framework: Next.js 15 (React 18)
- Language: TypeScript 5.x
- Styling: Tailwind CSS 3.x with centralized design system
- State Management: React Context API
- Authentication: JWT in httpOnly cookies

**Infrastructure (PRODUCTION ON HETZNER - October 24, 2025)**
- Platform: **Hetzner VPS** running Ubuntu 24.04 LTS
- Previous: Google Cloud Run + Supabase (cost reduction: ~$40/mo → ~$8/mo = 80% savings)
- Database: PostgreSQL 16 (local installation with SSL encryption)
- Deployment: Docker Compose + Nginx reverse proxy
- CI/CD: Manual deployment (GitHub Actions disabled)
- Region: Europe (Germany)
- Domain: bonidoc.com with Cloudflare Origin Certificate (Full Strict SSL)
- Monitoring: Docker logs + direct server access
- Server: CPX22 (2 vCPU, 4GB RAM, 80GB SSD)

### 2.2 Database Architecture

**PostgreSQL 16 - Local Hetzner Installation with SSL**

30 active tables organized in functional groups:

**Authentication & Users (3 tables)**
- users: User accounts with Google OAuth integration
- user_settings: User preferences and configuration
- user_sessions: Active session tracking for security

**Categories & Translations (3 tables)**
- categories: Category definitions with unique codes
- category_translations: Multi-language names/descriptions
- category_keywords: Learned keyword associations for ML

**Documents (4 tables)**
- documents: Main document metadata, Drive links, and document dates
- document_categories: Many-to-many (unlimited categories per document, one marked as primary)
- document_languages: Multi-language detection per document
- document_dates: Additional extracted dates (expiry, due dates, tax years)

**Keywords & Search (3 tables)**
- keywords: Normalized keyword dictionary
- document_keywords: Document-keyword associations with relevance
- stop_words: Language-specific stop word filtering

**Google Drive Integration (2 tables)**
- google_drive_folders: Category folder mappings in user's Drive
- google_drive_sync_status: Sync state and quota tracking

**ML & Classification (2 tables)**
- document_classification_log: Track all classification decisions
- category_classification_metrics: Daily accuracy metrics

**System Configuration (3 tables)**
- system_settings: Application-wide configuration
- localization_strings: UI translations
- audit_logs: Complete security audit trail

**Additional Features (7 tables)**
- upload_batches, collections, document_entities, document_shares, tags, notifications, search_history

### 2.3 System Architecture Principles

**Security Layers**
1. Transport Security: HTTPS with HSTS headers
2. Authentication: Google OAuth + JWT (15-minute access, 7-day refresh)
3. Session Management: Track and revoke active sessions
4. Field-Level Encryption: OAuth tokens only (pragmatic approach)
5. Rate Limiting: Three-tier limits (auth/write/read operations)
6. Input Validation: Pydantic models for all API inputs
7. Audit Logging: All security events logged with context

**Encryption Strategy**
- Documents: NOT encrypted (stored in user's Google Drive, already protected)
- OAuth Tokens: Encrypted with Fernet AES-256
- Keywords: NOT encrypted (semantic descriptors, not sensitive data)
- Metadata: NOT encrypted (filenames, categories, timestamps - needed for queries)
- Audit Logs: Log standardized filenames only, not original filenames

**Data Flow**
```
User Upload → File Validation → Temporary In-Memory Storage → Text Extraction (OCR if needed)
→ Language Detection → Keyword Extraction (semantic only, no entities) → Date Extraction
→ Category Classification (suggest ONE primary) → User Review & Correction (change primary, add more)
→ Permanent Storage (Google Drive in category folder) → Database Metadata (encrypted where needed)
→ ML Learning Update (adjust keyword weights per language) → Temp File Cleanup
```

**Learning Cycle**
```
System Suggests Primary Category → User Confirms/Changes Primary + Adds Secondary Categories
→ Log Decision → Adjust Keyword Weights (+10% correct, -5% incorrect)
→ Calculate Daily Accuracy Metrics → Improved Future Suggestions
```

**Document Naming Convention**
```
Format: YYYYMMDD_HHMMSS_CategoryCode_OriginalName.ext
Example: 20251017_143022_TAX_invoice_2024.pdf

Immutable Filename Strategy:
- Filename preserves original primary category (audit trail)
- On reclassification: Document moves to new folder, filename stays same
- Current primary category always available in UI and database
- Prevents broken links, simpler implementation, clear history
```

---

## 3. System Principles & Implementation Standards

### 3.1 Core Principles

**Database-Driven Configuration**
- All settings, categories, and localization strings stored in database
- No business rules hardcoded in source code
- Feature flags and settings configurable at runtime

**Production-Ready Code**
- No fallbacks, temporary solutions, or placeholder code
- No TODO, FIXME, or HACK comments in production
- Every feature fully implemented before merge

**Modular Architecture**
- Each file serves a single, well-defined purpose
- Files limited to <300 lines for maintainability
- Clear separation of concerns (routes, services, models)

**Security by Design**
- Multiple layers of protection
- Never trust client input
- Fail-safe defaults (deny by default)

**Privacy-First**
- User data stored in their own Google Drive
- System only stores metadata and preferences
- Users can delete all data at any time

**Learning System**
- ML algorithms improve from every user interaction
- Track classification accuracy per category
- Provide transparency (show why category was suggested)

**Accessibility**
- Multi-input support (mouse, keyboard, touch) on all interactive elements
- Responsive design for mobile, tablet, desktop
- Color-blind friendly design
- Dark mode support

### 3.2 Code Quality Standards

**Before Every Commit**
- File serves single functionality, <300 lines
- Zero design elements in core business logic files
- All configuration values from database/config files
- No fallbacks, workarounds, or TODO comments
- Multi-input support tested (mouse, keyboard, touch)
- File header comment explaining purpose
- Check for duplicate functions before adding new ones

**Database Standards**
- All migrations include downgrade() implementation
- Indexes added for all foreign keys
- Default values for NOT NULL columns
- Test both upgrade and downgrade before committing

**Error Handling**
- Return structured error responses with clear messages
- Never expose stack traces to users
- Log detailed errors internally with context
- Provide actionable error messages

---

## 4. Development Phases & Milestones

### Phase 1: Security Foundation ✅ COMPLETE

**Objective:** Lock down the platform before adding features

**Database Updates**
- Rename category_term_weights → category_keywords
- Create user_sessions table for session tracking
- Add encryption columns for sensitive data

**Security Services**
- Encryption service (Fernet AES-256)
- Session management service (7-day refresh tokens)
- Rate limiting service (3-tier: auth/write/read)
- File validation service (multi-layer security)
- Security monitoring service (behavioral analysis)

**Authentication Updates**
- Replace localStorage with httpOnly cookies
- Reduce access token expiry to 15 minutes
- Implement refresh token with 7-day expiry
- Track active sessions in database

**Security Middleware**
- Security headers (HSTS, CSP, X-Frame-Options)
- Rate limiting on all endpoints
- Input sanitization with Pydantic
- Comprehensive audit logging

**Cross-Domain Authentication Architecture**
- Backend (api.bonidoc.com) sets httpOnly cookies with SameSite=None
- Frontend (bonidoc.com) automatically sends cookies with API requests
- Authentication enforced at API level, not middleware
- Protected pages check auth via /auth/me API endpoint
- Full page reload after OAuth login for proper context initialization
- No client-side token manipulation (security by design)

**OAuth Login Flow** (October 17, 2025)
- Issue: After Google OAuth login, users were redirected back to blank login page
- Root cause: Client-side navigation (router.push) didn't re-initialize AuthContext
- Solution: Changed to window.location.href for full page reload after login
- Result: OAuth flow now works correctly end-to-end
- Security: All authentication tokens remain in httpOnly cookies only

**Milestone Criteria:**
- All tokens stored in httpOnly cookies ✅
- Session revocation working ✅
- Rate limiting active on all endpoints ✅
- Security headers present on all responses ✅
- Audit logs capturing all security events ✅
- OAuth login flow working correctly ✅

---

### Phase 2: Document Processing & Classification

**Objective:** Enable intelligent document categorization with OCR support and date extraction

**2A: OCR & Text Extraction**
- Integrate Tesseract for scanned document processing
- Implement image preprocessing (grayscale, binarization, deskew)
- Update document analysis to detect scanned vs native text PDFs
- Extract text from images (JPEG, PNG, TIFF)
- Process documents in-memory (files <10MB), encrypted temp dir for larger files
- Immediate cleanup of temporary files after processing

**2B: Keyword Extraction (Language-Aware)**
- Extract semantic keywords only (nouns, verbs), not entities (names, numbers)
- Filter stop words per language (ru/en/de, scalable to more)
- Frequency-based keyword scoring
- Limit keyword length (max 50 chars to prevent full sentences)
- Store keywords unencrypted (semantic descriptors, not sensitive data)

**2C: Classification Engine**
- Implement keyword overlap scoring algorithm per language
- Apply confidence thresholds (60% minimum, 20% gap requirement)
- Suggest ONE primary category (highest confidence)
- Populate system keywords database (150+ keywords in en/de/ru)
- Handle ambiguous cases (suggest "Other" category)
- Language-scalable architecture (easy to add new languages)

**2D: Date Extraction**
- Extract ONE primary document date per document (invoice date, tax year, signature date, etc.)
- Store in documents.document_date with confidence score
- Multi-language date pattern recognition (DD.MM.YYYY, MM/DD/YYYY, etc.)
- Store as ISO format (YYYY-MM-DD) internally, display per user locale
- Optional: Extract secondary dates (expiry, due date) in document_dates table

**2E: Category Learning & ML Feedback Loop**
- Record all classification decisions in document_classification_log
- Track user's final choice (confirmed, changed primary, added secondary)
- Reinforce correct suggestions (+10% keyword weight for that language)
- Penalize incorrect suggestions (-5% keyword weight for that language)
- Calculate daily accuracy metrics per category per language
- Display learning progress and "why this category?" explanations to users

**Multi-Category Assignment Logic**
- System suggests ONE primary category
- User can: approve, change primary, add unlimited secondary categories
- document_categories table tracks is_primary flag
- ML learns from both primary and secondary assignments
- All user decisions feed back into keyword weight adjustments

**Milestone Criteria:**
- OCR successfully extracts text from scanned documents
- Classification suggests correct primary category ≥70% of the time
- System learns from user corrections (weights adjust per language)
- Date extraction works with ≥80% accuracy
- Daily metrics show accuracy improvement trends
- Users can view "why this category?" explanation with keyword matches
- Architecture supports easy addition of new languages (not hardcoded to ru/en/de)

---

### Phase 3: Google Drive Integration

**Objective:** Store documents securely in user's personal Google Drive with proper folder organization

**Drive Schema (Already in Place)**
- google_drive_folders: Category folder mappings (user_id, category_id, folder_id)
- google_drive_sync_status: Quota tracking and sync state
- documents.drive_file_id: Google's unique file ID
- documents.drive_folder_id: Category folder reference
- users.google_drive_connected: Connection status flag

**Drive Folder Structure**
```
/BoniDoc/
├── Tax Documents/
├── Insurance/
├── Contracts/
├── Legal/
├── Medical/
├── Receipts/
├── Certificates/
├── Real Estate/
└── Other/
```

**Drive Service Implementation**
- Initialize Drive connection with OAuth scope (drive.file for security)
- Create folder structure on first upload (lazy initialization)
- Upload files with standardized names to appropriate category folders
- Generate temporary download links (1-hour expiry for security)
- Track storage quotas and warn users at 80% capacity
- Handle Drive API errors gracefully (rate limits, quota exceeded, network failures)
- Move files between folders on category reclassification (filename stays same)

**Upload Flow with Drive Integration**
1. User uploads document → Temporary backend storage
2. OCR/text extraction → Classification → User review
3. User confirms categories → Upload to Drive in primary category folder
4. Store drive_file_id and metadata in database
5. Delete temporary file from backend
6. Return success with Drive link to user

**Reclassification Flow**
- User changes primary category → Move file to new folder in Drive
- Filename remains unchanged (immutable naming strategy)
- Update documents.primary_category_id and documents.drive_folder_id
- Log reclassification in audit_logs
- No broken links (drive_file_id stays same even after move)

**Frontend Updates**
- Drive connection UI in settings page
- Storage quota display with progress bar
- Document detail page with "View in Drive" button
- Download functionality via temporary links
- Warning messages when quota approaching limit

**Security Considerations**
- OAuth scope limited to drive.file (only access BoniDoc-created files)
- All Drive API calls over HTTPS
- Temporary download links expire after 1 hour
- No document content logged or stored in backend
- User can revoke Drive access anytime

**Milestone Criteria:**
- Users can connect their Google Drive via OAuth
- Folder structure created automatically on first upload
- Documents upload to correct category folders
- Standardized filenames preserved across reclassifications
- Move operation works correctly (file moves, filename stays same)
- Download links work reliably
- Quota tracking accurate and warnings displayed
- Drive connection can be revoked from settings

---

### Phase 4: Production Hardening & Monitoring

**Objective:** Ensure system is production-ready and monitored

**Security Hardening**
- Enable Cloud Armor (DDoS protection)
- Run penetration testing
- Review and update privacy policy
- Implement CAPTCHA for sensitive operations

**Monitoring & Observability**
- Setup Cloud Monitoring dashboards
- Configure alerts (error rate, latency, quota)
- Setup error tracking (Sentry or similar)
- Log aggregation and analysis

**Documentation**
- Update API documentation (OpenAPI/Swagger)
- Create user guide (how to use the system)
- Create admin guide (deployment, maintenance)
- Document troubleshooting procedures

**Milestone Criteria:**
- All services monitored with alerts
- Error rate <0.1%
- API response time p95 <200ms
- Documentation complete and accessible
- Penetration test passed

---

## 5. Current Status & Next Steps

### 5.1 Completed Features ✅

**Phase 1: Security Foundation** (Complete - October 17, 2025)
- httpOnly cookie authentication (replaced localStorage)
- Cross-domain authentication architecture (api.bonidoc.com ↔ bonidoc.com)
- OAuth 2.0 login flow with Google (fully working, first attempt success)
- Session management with 7-day refresh tokens
- Rate limiting (3-tier: auth/write/read)
- Security headers middleware (HSTS, CSP, X-Frame-Options)
- Field-level encryption service (AES-256) with dedicated ENCRYPTION_KEY
- Behavioral trust scoring
- CAPTCHA service integration
- File validation (multi-layer security)
- AuthContext with localStorage caching for performance
- Secure token storage (Google Drive refresh tokens encrypted with Fernet)

**Infrastructure** (Production - October 25, 2025)
- Hetzner VPS deployment (Docker + Nginx)
- Local PostgreSQL 16 database (30 tables + SSL)
- Manual deployment workflow
- Alembic migrations (2 clean migrations: schema + data)
- Google OAuth authentication (login + Drive scopes)
- JWT-based session management
- Docker container deployment (frontend + backend)
- Automated container rebuilds (clearing Python bytecode cache)

**Core Features** (Production)
- User management (profile, settings, deactivation)
- Multi-language categories (9 system categories in en/de/ru)
- Category CRUD with translations
- Dark mode theme
- Settings & localization API
- Comprehensive audit logging
- Multi-category assignment architecture (unlimited categories, one primary)

**Phase 2A: OCR & Text Extraction** ✅ COMPLETE (October 24, 2025)
- ✅ Replaced PyPDF2 with PyMuPDF for superior text extraction
- ✅ Implemented spell-check based quality assessment (pyspellchecker)
- ✅ Created two-stage extraction strategy (fast path + quality check + re-OCR)
- ✅ Added Tesseract with enhanced preprocessing (adaptive thresholding)
- ✅ Multi-language spell-checking support (EN, DE, RU, ES, FR, PT, IT)
- ✅ PyMuPDF-based PDF-to-image rendering (no poppler dependency)
- ✅ Tested: 100% accuracy on problematic bank statement (9/9 keywords)
- Performance: 95% of docs <1s, 5% need OCR (3-8s/page)

**Phase 3: Google Drive Integration** ✅ COMPLETE (October 25, 2025)
- ✅ OAuth 2.0 Drive connection with scope: `drive.file` (secure, limited access)
- ✅ Folder structure initialization on first connection:
  - Main folder: `/Bonifatus_DMS/`
  - Category subfolders created automatically with translations
  - Config folder: `.config/` for metadata
- ✅ Document upload to Drive with standardized filenames
- ✅ Filename normalization: `YYYYMMDD_HHMMSS_CategoryCode_OriginalName.ext`
- ✅ Drive file ID storage in database
- ✅ Google Drive service with proper error handling
- ✅ Drive connection status in settings UI
- ✅ Document metadata stored in PostgreSQL, files in user's Drive

**Phase 2B: Date Extraction** ✅ COMPLETE (October 25, 2025 - 14:50 UTC)
- ✅ Multi-language date pattern recognition (en/de/ru)
- ✅ 11 date types supported: invoice_date, due_date, tax_year, signature_date, effective_date, expiry_date, tax_period_start, tax_period_end, birth_date, issue_date, unknown
- ✅ Database-driven configuration (9 system_settings entries)
- ✅ Date extraction service fully integrated into document analysis workflow
- ✅ Primary date storage in documents.document_date with type and confidence
- ✅ UI display with date badge showing date, type, and confidence percentage
- ✅ Standardized filename generation using extracted document date
- ✅ Initialization script: `backend/scripts/init_date_patterns.py`
- Deployment: Frontend rebuilt 14:42 UTC, Backend rebuilt 14:50 UTC
- Database: 9 patterns populated (3 per language: patterns, month names, keywords)
- Example UI output: "📅 10/15/2024 (invoice date) 90% confidence"

**Document Processing** (October 25, 2025)
- ✅ Batch upload analysis endpoint with virus scanning
- ✅ Confirm upload endpoint (saves to Drive + database)
- ✅ ML keyword extraction service (frequency-based, language-aware)
- ✅ Language detection (en/de/ru)
- ✅ Standardized filename generation with category codes
- ✅ Date extraction service (comprehensive, multi-language) - ✅ COMPLETE
- ✅ Date extraction UI display (badge with date type and confidence)
- ✅ Date patterns configuration (9 system_settings entries for en/de/ru)
- ⏳ ML category learning framework (structure in place, needs training data)
- ⏳ Classification engine (needs keyword population)

### 5.2 In Progress ⏳

**Phase 2: Document Processing & Classification** (Active - October 25, 2025)
- ⏳ Classification engine training (populate category_keywords)
- ⏳ ML learning loop activation
- ⏳ Keyword extraction integration with classification

**UI Development**
- ⏳ Document list view with filters and search
- ⏳ Document detail page with Drive preview
- ⏳ Download functionality via temporary links
- ⏳ "Why this category?" explanation UI

### 5.3 Next Immediate Steps

**PRIORITY 1: Populate Category Keywords** (Phase 2C)

The classification engine exists but needs training data:

1. Create seed data script with 150+ keywords across 9 categories
2. Populate category_keywords table with initial weights (1.0 default)
3. Map keywords to categories for each language (en, de, ru)
4. Test classification accuracy on sample documents

**PRIORITY 2: Activate ML Learning Loop** (Phase 2E)

1. Integrate classification logging on document confirm
2. Implement weight adjustment on user corrections
3. Create daily metrics calculation job
4. Build UI to show matched keywords and confidence

**PRIORITY 3: Complete UI Features**

1. Document list view with category filters
2. Document detail page with metadata
3. Download via temporary Drive links
4. Search functionality with date range filters

---

## 6. Design Decisions & Rationale

### 6.1 Classification & Categorization

**Multi-Category Assignment**
- Decision: Unlimited categories per document, one marked as primary
- Rationale: Real-world documents often belong to multiple categories (e.g., "Tax" + "Real Estate")
- Implementation: document_categories table with is_primary boolean flag
- User Flow: System suggests ONE primary → user can approve/change/add more
- ML Impact: All assignments (primary + secondary) feed into learning algorithm

**Primary Category Selection**
- Decision: System suggests ONE primary based on highest confidence score
- Rationale: Reduces cognitive load, provides clear recommendation, user maintains control
- Fallback: If confidence <60% or top two within 20%, suggest "Other" category
- User Override: User can always change suggested primary to any category

**Category Learning Strategy**
- Decision: Keyword weight adjustment per language (+10% correct, -5% incorrect)
- Rationale: Asymmetric learning (faster reinforcement, slower penalty) prevents over-correction
- Granularity: Weights tracked per category per keyword per language
- Scalability: Architecture supports unlimited languages without code changes

### 6.2 Keyword Extraction Philosophy

**Semantic Keywords Only**
- Decision: Extract nouns/verbs, NOT entities (names, numbers, IDs)
- Rationale: "invoice" helps classification, "123-45-6789" does not
- Security Benefit: No PII accidentally stored as keywords
- Example: Extract "passport application" not "John Smith passport A1234567"

**No Keyword Encryption**
- Decision: Store keywords in plaintext (unencrypted)
- Rationale: Keywords are content descriptors, not sensitive data
- Performance: Enables fast searches, efficient indexing, no decryption overhead
- User Benefit: Fast classification, instant search results

**Language-Specific Processing**
- Decision: Stop words, patterns, and weights tracked per language
- Rationale: Word importance varies by language ("the" irrelevant in English, meaningful in other contexts)
- Scalability: New languages added via database configuration, not code changes
- Storage: language column in keywords, category_keywords, and stop_words tables

### 6.3 OCR & Text Extraction Strategy

**Two-Stage Intelligent Extraction**
- Decision: PyMuPDF for native PDFs, Tesseract OCR only when needed
- Rationale: Most PDFs have good embedded text; OCR is slow and resource-intensive
- Stage 1: Fast extraction with PyMuPDF (milliseconds)
- Stage 2: Quality assessment with spell-checking
- Stage 3: Re-OCR only if quality < 60% threshold
- Result: 95% of documents use fast path, 5% get high-quality re-OCR

**Quality Assessment with Spell-Checking**
- Decision: Use pyspellchecker library to detect OCR corruption
- Rationale: ML-based, language-aware, catches ALL OCR errors (not hardcoded patterns)
- Method: Sample 100 words, check spelling error rate
- Thresholds:
  - <15% errors = excellent (0.95-1.0 score) → use embedded text
  - 15-30% errors = good (0.7-0.95 score) → use embedded text
  - 30-50% errors = poor (0.5-0.7 score) → use embedded text
  - >50% errors = garbage (<0.5 score) → re-OCR with Tesseract
- Languages: EN, DE, RU, ES, FR, PT, IT (cached for performance)

**PyMuPDF for Superior Text Extraction**
- Decision: Replace PyPDF2 with PyMuPDF (fitz)
- Rationale: 10x better text extraction quality, handles complex PDFs
- Benefits:
  - Preserves formatting, tables, multi-column layouts
  - Fast (written in C)
  - No external dependencies (no poppler needed)
  - Also used for PDF-to-image rendering (300 DPI)
- Free: AGPL license, completely open source

**Tesseract OCR Configuration**
- Engine: OEM 3 (LSTM neural network mode)
- Page Segmentation: PSM 3 (automatic page segmentation)
- Preprocessing:
  - Grayscale conversion
  - Fast non-local means denoising
  - Adaptive Gaussian thresholding (better than Otsu for varying lighting)
  - Optional morphological operations for very poor scans
- Resolution: 300 DPI rendering for optimal accuracy
- Languages: Multi-language support (deu+eng for German documents)

**Example: Bank Statement Test Case**
- **Before (PyPDF2)**: "peptember", "bro", "fmportant", "holderW" (garbage)
- **After (PyMuPDF + quality check)**: Detected poor quality (58.8% score)
- **Re-OCR (Tesseract)**: "September", "EUR", "Important", "holder" (94.5% confidence)
- **Result**: 9/9 keywords found, 100% accuracy

**Performance Characteristics**
- Native PDF extraction: <100ms per page
- Quality assessment: <50ms (cached spell checker)
- OCR processing (when needed): 3-8 seconds per page at 300 DPI
- Overall: 95% of documents processed in <1 second

**Cost & Dependencies**
- Zero API costs (all processing local)
- Dependencies: PyMuPDF (free), Tesseract (free), pyspellchecker (free)
- No cloud services required
- Scales horizontally without additional costs

### 6.4 Document Naming & File Management

**Immutable Filename Strategy**
- Decision: Filenames never change after creation
- Format: YYYYMMDD_HHMMSS_CategoryCode_OriginalName.ext
- Rationale: Preserves audit trail, prevents broken links, simpler implementation
- On Reclassification: File moves to new folder, filename stays same
- Trade-off Accepted: Filename shows original category, not current (current always in UI)

**Upload Timestamp vs Document Date**
- Decision: Both stored separately, different purposes
- Upload Timestamp: In filename, immutable, system-generated
- Document Date: Extracted from content, editable, user-meaningful
- Display: Show both in UI ("Uploaded Oct 17, 2025 • Document Date: Mar 15, 2024")
- Search: Users search by document date, not upload timestamp

**Google Drive Folder Structure**
- Decision: Flat folder structure by category (/BoniDoc/CategoryName/)
- Rationale: Simple, mirrors category system, easy to navigate
- On Reclassification: Move file between folders using Drive API
- User Benefit: Clear organization, manual Drive access makes sense

### 6.4 Security & Encryption Strategy

**Pragmatic Encryption Approach**
- Decision: Encrypt only OAuth tokens, not keywords/metadata
- Rationale: Balance security, performance, maintenance cost, user experience
- Documents: NOT encrypted (stored in user's Google Drive, already protected)
- Keywords: NOT encrypted (semantic descriptors, not sensitive)
- Tokens: Encrypted with Fernet AES-256 (highest risk attack vector)

**No PII Detection/Extraction**
- Decision: Skip automatic PII detection
- Rationale: High complexity, constant maintenance, low value-add, false positives
- Alternative: Extract semantic keywords only (ignore entities by design)
- Benefit: Simpler codebase, no language-specific regex patterns needed

**Audit Logging Approach**
- Decision: Log standardized filenames, not original filenames
- Rationale: Balance traceability with privacy
- Example Logged: "20251017_143022_TAX_invoice.pdf" ✓
- Example NOT Logged: "john_smith_secret_tax_return.pdf" ✗
- User Benefit: Can identify their documents in audit logs without exposing sensitive names

### 6.5 Date Extraction Design

**Primary Document Date**
- Decision: Extract ONE main date per document
- Storage: documents.document_date (DATE) + document_date_confidence (FLOAT)
- Rationale: Most documents have one meaningful date (invoice date, contract date, tax year)
- Display: Show with context ("Invoice Date: Mar 15, 2024")

**Secondary Dates (Optional)**
- Decision: Extract additional dates only if useful for search/organization
- Storage: document_dates table (future enhancement)
- Examples: Expiry dates, due dates, tax years, contract periods
- Implementation: Phase 2D (optional), can defer to later phase

**Date Format Strategy**
- Storage: ISO format (YYYY-MM-DD) in database (universal, sortable)
- Display: User's locale preference (MM/DD/YYYY for US, DD.MM.YYYY for EU/RU)
- Extraction: Multi-language pattern matching (handle all common formats)

### 6.6 Language Scalability

**Database-Driven Language Support**
- Decision: All language-specific data in database tables, not code
- Tables: stop_words, category_keywords, localization_strings all have language column
- Rationale: Adding new language = data migration, not code deployment
- Process: Admin adds new language via database, no code changes needed

**Initial Language Set**
- Start: Russian, English, German (ru, en, de)
- Why: User base primary languages, sufficient to prove scalability
- Future: Any language supported by adding data (stop words, translations, system keywords)

**Language Detection**
- Decision: Detect document language during text extraction
- Storage: document_languages table (supports multi-language documents)
- Impact: Classification uses language-specific keyword weights
- Fallback: If detection fails, use user's preferred language from settings

### 6.7 Machine Learning Approach

**Keyword Overlap Scoring**
- Algorithm: Count matching keywords between document and category
- Formula: score = (matching_keywords * avg_weight) / total_document_keywords
- Thresholds: 60% minimum confidence, 20% gap between top two
- Rationale: Simple, explainable, language-agnostic, fast

**Weight Adjustment Rules**
- Correct Prediction: +10% to all matching keywords
- Incorrect Prediction: -5% to all matching keywords that led to wrong choice
- Rationale: Asymmetric learning prevents over-correction from single mistakes
- Bounds: Weights bounded [0.1, 10.0] to prevent extreme values

**Transparency & Explainability**
- Decision: Show users WHY a category was suggested
- Display: "Matched keywords: invoice, payment, tax (85% confidence)"
- Benefit: Users trust system, understand decisions, provide better corrections
- ML Impact: Explicit feedback improves learning quality

### 6.8 User Experience Principles

**Batch Upload Flow**
1. User uploads multiple files → System analyzes in parallel
2. Show progress per file with extracted info preview
3. User reviews all suggestions at once (approve/modify/add categories)
4. Confirm → Upload to Drive + Store metadata + Learn from decisions
5. Show success with links to Drive files

**Confidence Visualization**
- High Confidence (≥80%): Green indicator, "Recommended"
- Medium Confidence (60-80%): Yellow indicator, "Suggested"
- Low Confidence (<60%): Gray indicator, "Uncertain - Please Review"
- Rationale: Clear visual feedback builds trust, prompts user attention where needed

**Mobile-First Design**
- All interactions work with touch (no hover-only features)
- Large touch targets (min 44x44px)
- Swipe gestures for common actions
- Responsive tables/lists collapse to cards on mobile

---

## 7. Quality Control & Deployment Process

### 7.1 Pre-Commit Checklist

**Code Quality**
- Run linter (flake8 for Python, eslint for TypeScript)
- Verify no hardcoded values (grep for common patterns)
- Confirm all files <300 lines
- Check for duplicate functions
- Verify file header comment present

**Functionality**
- Test locally: All affected features work correctly
- Test edge cases: Invalid inputs, empty states, large datasets
- Test multi-language: Verify translations load correctly
- Test dark mode: UI renders correctly in both themes
- Test mobile: Responsive design on small screens

**Security**
- No sensitive data in code (API keys, passwords, secrets)
- No user input used directly in SQL queries
- All file uploads validated (magic bytes, size, type)
- Rate limiting present on new endpoints
- Audit logging added for sensitive operations

### 7.2 Deployment Process

**🔄 HETZNER VPS DEPLOYMENT (October 23, 2025)**

For complete migration guide, see: **`HETZNER_MIGRATION_GUIDE.md`**

#### Claude Code Remote Server Access

When working with Claude Code, it can execute commands directly on the remote Hetzner server via SSH. This requires proper SSH key configuration on your local machine.

**Prerequisites:**
1. SSH keys must be configured between your local machine and the Hetzner server
2. The local machine where Claude Code runs must have SSH access to `deploy@YOUR_SERVER_IP`
3. Server credentials stored in `HETZNER_SETUP_ACTUAL.md` (not committed to Git)

**How Claude Code Accesses the Server:**

Claude Code uses the Bash tool to execute SSH commands from your local machine:

```bash
# Example: Claude Code can run commands like this
ssh deploy@YOUR_SERVER_IP "command_to_execute"

# Check server status
ssh deploy@YOUR_SERVER_IP "docker ps"

# View logs
ssh deploy@YOUR_SERVER_IP "cd /opt/bonifatus-dms && docker compose logs -f backend --tail=50"

# Deploy updates
ssh deploy@YOUR_SERVER_IP "~/deploy.sh"
```

**Setup SSH Access for Claude Code:**

1. **Verify SSH Key Exists on Local Machine:**
   ```bash
   ls ~/.ssh/id_rsa
   ls ~/.ssh/id_rsa.pub
   ```

2. **Test SSH Connection:**
   ```bash
   ssh deploy@YOUR_SERVER_IP "whoami"
   # Should output: deploy
   ```

3. **If Connection Fails:**
   - Ensure your SSH public key is in `/home/deploy/.ssh/authorized_keys` on server
   - Check SSH config: `~/.ssh/config` (optional host alias)
   - Verify firewall allows SSH (port 22)
   - Check `HETZNER_SETUP_ACTUAL.md` for server IP and credentials

**Common Claude Code Server Operations:**

```bash
# Check deployment status
ssh deploy@YOUR_SERVER_IP "cd /opt/bonifatus-dms && docker compose ps"

# View recent logs
ssh deploy@YOUR_SERVER_IP "cd /opt/bonifatus-dms && docker compose logs --tail=100"

# Check server resources
ssh deploy@YOUR_SERVER_IP "free -h && df -h"

# Restart services
ssh deploy@YOUR_SERVER_IP "cd /opt/bonifatus-dms && docker compose restart"

# Pull latest code
ssh deploy@YOUR_SERVER_IP "cd /opt/bonifatus-dms && git pull"

# Check environment variables (redacted)
ssh deploy@YOUR_SERVER_IP "cd /opt/bonifatus-dms && cat .env | grep -E 'GOOGLE|DATABASE' | sed 's/=.*/=***REDACTED***/'"
```

**Security Notes:**
- Never commit server credentials to Git
- Store credentials in `HETZNER_SETUP_ACTUAL.md` (gitignored)
- Use SSH keys instead of passwords
- Limit SSH access to `deploy` user (non-root)
- Claude Code only executes commands you approve

**Workflow Example:**

1. User: "Check if the backend is running on the server"
2. Claude Code: Executes `ssh deploy@SERVER_IP "docker ps"`
3. User: Approves or rejects the command
4. Claude Code: Shows results and interprets status

This allows Claude Code to help debug, deploy, and maintain the production server without requiring manual terminal work.

---

#### Automated Deployment (GitHub Actions → Hetzner)

```
1. Push code to main branch
2. GitHub Actions triggers CI/CD pipeline
3. Backend: Run tests → Build Docker image
4. Frontend: Run tests → Build Next.js
5. SSH to Hetzner VPS
6. Execute deployment script: ~/deploy.sh
7. Script: Pull code → Rebuild containers → Restart services
8. Completes in 5-8 minutes
```

#### Manual Deployment (on Hetzner server)

**Method 1: Direct SSH**
```bash
ssh deploy@YOUR_SERVER_IP
~/deploy.sh
```

**Method 2: Via Claude Code**
```bash
# Claude Code can execute this from your local machine
ssh deploy@YOUR_SERVER_IP "~/deploy.sh"
```

**The deploy script does:**
- Pulls latest code from GitHub
- Rebuilds Docker images
- Stops containers
- Starts containers with new code
- Verifies health checks

**Post-Deployment Verification**
```
1. Backend health check: curl https://api.bonidoc.com/health
2. Frontend health check: curl https://bonidoc.com
3. Database check: Verify tables exist and migrations applied
4. Smoke test: Login → Create category → Upload document → Logout
5. Check logs: docker-compose logs -f
6. Monitor resources: htop, docker stats
```

### 7.3 Performance Benchmarks

**Target Metrics**
- API response time (p95): <200ms
- Database query time (p95): <100ms
- Document upload (single file): <5s
- Batch analysis (10 files): <30s
- OCR processing (per page): <10s
- Page load time: <2s

---

## 8. Project Instructions Summary

### Principles to Follow

**Code Quality**
- Files modular (<300 lines), production-ready only
- No hardcoded values, all from database/config
- Root cause fixes, no workarounds
- Check for duplicates before creating new code
- Professional comments explaining "why" not "what"

**Security**
- Security-first: encryption, httpOnly cookies, rate limiting
- Never trust client input
- Log all security events with context
- Fail-safe defaults

**Development Process**
- One step at a time, wait for confirmation
- Test thoroughly before committing
- Update deployment_progress.md after each fix
- Update DEPLOYMENT_GUIDE.md after completing phases

---

## 9. Environment Variables

### Backend (Required)
```
DATABASE_URL=postgresql://...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://bonidoc.com/login
JWT_SECRET_KEY=...
ENCRYPTION_KEY=...
ENVIRONMENT=production
```

### Frontend (Required)
```
NEXT_PUBLIC_API_URL=https://api.bonidoc.com
```

---

## 10. Database Migrations

### Current Migration Status
- Total migrations: 10
- Migration chain: Clean, no forks
- Tables: 26 active tables

### Running Migrations
```
cd backend
alembic current                    # Check current version
alembic upgrade head               # Apply all pending migrations
alembic downgrade -1               # Rollback one migration
psql $DATABASE_URL -c "\dt"        # List all tables
```

---

**End of Deployment Guide**

For daily progress tracking, see: `deployment_progress.md`
For technical implementation details, review source code with inline documentation.
