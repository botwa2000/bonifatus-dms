# BoniDoc - Development & Deployment Guide
Version: 11.0
Last Updated: October 16, 2025
Status: Phase 1 Complete | Production Deployment Active
Domain: https://bonidoc.com

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
- Extract text from scanned documents using OCR
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
- Multi-category assignment (1-5 categories per document)
- Learning system that improves with use
- Mobile-responsive interface with dark mode
- Accessible via mouse, keyboard, and touch

---

## 2. Technology Stack & Architecture Overview

### 2.1 Technology Stack

**Backend**
- Framework: FastAPI (Python 3.11+)
- Database: PostgreSQL 15.x (Supabase hosted)
- Authentication: Google OAuth 2.0 + JWT with httpOnly cookies
- Storage: Google Drive API (user-owned storage)
- OCR: Tesseract + PyMuPDF for text extraction
- Encryption: Fernet (AES-256) for field-level encryption
- Migrations: Alembic
- Deployment: Google Cloud Run (serverless)

**Frontend**
- Framework: Next.js 15 (React 18)
- Language: TypeScript 5.x
- Styling: Tailwind CSS 3.x with centralized design system
- State Management: React Context API
- Authentication: JWT in httpOnly cookies

**Infrastructure**
- Platform: Google Cloud Run (Backend + Frontend containers)
- CI/CD: GitHub Actions (automated deployment on push to main)
- Region: us-central1
- Domain: bonidoc.com with SSL/TLS
- Monitoring: Google Cloud Logging + Monitoring

### 2.2 Database Architecture

26 active tables organized in functional groups:

**Authentication & Users (3 tables)**
- users: User accounts with Google OAuth integration
- user_settings: User preferences and configuration
- user_sessions: Active session tracking for security

**Categories & Translations (3 tables)**
- categories: Category definitions with unique codes
- category_translations: Multi-language names/descriptions
- category_keywords: Learned keyword associations for ML

**Documents (3 tables)**
- documents: Main document metadata and Drive links
- document_categories: Many-to-many (supports 1-5 categories per document)
- document_languages: Multi-language detection per document

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
4. Field-Level Encryption: Sensitive data encrypted at rest
5. Rate Limiting: Three-tier limits (auth/write/read operations)
6. Input Validation: Pydantic models for all API inputs
7. Audit Logging: All security events logged with context

**Data Flow**
```
User Upload → File Validation → Temporary Storage → Text Extraction (OCR if needed)
→ Language Detection → Keyword Extraction → Category Classification
→ User Review & Correction → Permanent Storage (Google Drive)
→ Database Metadata → ML Learning Update
```

**Learning Cycle**
```
System Suggests Category → User Confirms or Corrects
→ Adjust Keyword Weights → Improved Future Suggestions
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

**Milestone Criteria:**
- All tokens stored in httpOnly cookies
- Session revocation working
- Rate limiting active on all endpoints
- Security headers present on all responses
- Audit logs capturing all security events

---

### Phase 2: Document Processing & Classification

**Objective:** Enable intelligent document categorization with OCR support

**OCR & Text Extraction**
- Integrate Tesseract for scanned document processing
- Implement image preprocessing (grayscale, binarization, deskew)
- Update document analysis to detect scanned vs native text PDFs
- Extract text from images (JPEG, PNG, TIFF)

**Classification Engine**
- Implement keyword overlap scoring algorithm
- Apply confidence thresholds (60% minimum, 20% gap requirement)
- Populate system keywords (150+ keywords in en/de/ru)
- Handle ambiguous cases (assign to "Other" category)

**Category Learning**
- Record all classification decisions in database
- Reinforce correct suggestions (10% weight boost)
- Penalize incorrect suggestions (5% weight reduction)
- Calculate daily accuracy metrics per category
- Display learning progress to users

**Milestone Criteria:**
- OCR successfully extracts text from scanned documents
- Classification suggests correct category ≥70% of the time
- System learns from user corrections
- Daily metrics show accuracy trends
- Users can view "why this category?" explanation

---

### Phase 3: Google Drive Integration

**Objective:** Store documents securely in user's personal Google Drive

**Drive Schema**
- Create google_drive_folders table (category folder mappings)
- Create google_drive_sync_status table (quota tracking)
- Add Drive columns to documents table (drive_file_id, web_view_link)
- Add Drive permissions to users table

**Drive Service**
- Initialize Drive connection with OAuth scope
- Create folder structure (/BoniDoc/CategoryName/)
- Upload files to appropriate category folders
- Generate temporary download links (1-hour expiry)
- Track storage quotas and warn users
- Handle Drive API errors gracefully

**Frontend Updates**
- Drive connection UI in settings
- Storage quota display with progress bar
- Document detail page with "View in Drive" link
- Download functionality via temporary links

**Milestone Criteria:**
- Users can connect their Google Drive
- Documents upload to Drive successfully
- Folder structure created automatically
- Download links work reliably
- Quota tracking accurate

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

**Phase 1: Security Foundation** (Complete)
- httpOnly cookie authentication (replaced localStorage)
- Session management with 7-day refresh tokens
- Rate limiting (3-tier: auth/write/read)
- Security headers middleware (HSTS, CSP, etc.)
- Field-level encryption service (AES-256)
- Behavioral trust scoring
- CAPTCHA service integration
- File validation (multi-layer security)

**Infrastructure** (Production)
- Google Cloud Run deployment (backend + frontend)
- Supabase PostgreSQL database (26 tables)
- GitHub Actions CI/CD pipeline
- Alembic migrations (10 migrations, clean chain)
- Google OAuth authentication
- JWT-based session management

**Core Features** (Production)
- User management (profile, settings, deactivation)
- Multi-language categories (9 system categories in en/de/ru)
- Category CRUD with translations
- Dark mode theme
- Settings & localization API
- Comprehensive audit logging
- Multi-category assignment architecture (1-5 categories per document)

**Document Processing** (Partial)
- Batch upload analysis endpoint
- ML keyword extraction (frequency-based)
- Language detection (en/de/ru)
- Standardized filename generation
- ML category learning framework (structure in place)

### 5.2 In Progress ⏳

**Document Upload Flow**
- Google Drive storage integration (Phase 3)
- Confirm upload endpoint (permanent storage)
- Document list view with filters
- Document detail page
- Download functionality

### 5.3 Next Immediate Steps

**Start Phase 2: Document Processing & Classification**

1. **OCR Integration**
   - Add Tesseract dependencies to Dockerfile
   - Implement image preprocessing
   - Create OCR service for scanned PDFs and images
   - Update document analysis service to use OCR when needed

2. **Classification Engine**
   - Implement keyword overlap scoring
   - Apply confidence thresholds and decision rules
   - Populate system keywords (150+ in en/de/ru)
   - Test classification accuracy on sample documents

3. **Learning Mechanism**
   - Record all classification decisions
   - Implement weight adjustment (10% boost, 5% penalty)
   - Create daily metrics calculation job
   - Display category performance metrics to users

---

## 6. Quality Control & Deployment Process

### 6.1 Pre-Commit Checklist

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

### 6.2 Deployment Process

**Automated Deployment**
```
1. Push code to main branch
2. GitHub Actions triggers CI/CD pipeline
3. Backend: Run tests → Build Docker image → Deploy to Cloud Run
4. Frontend: Run tests → Build Next.js → Deploy to Cloud Run
5. Completes in 3-5 minutes
```

**Post-Deployment Verification**
```
1. Backend health check: curl https://api.bonidoc.com/health
2. Frontend health check: curl https://bonidoc.com
3. Database check: Verify tables exist and migrations applied
4. Smoke test: Login → Create category → Upload document → Logout
```

### 6.3 Performance Benchmarks

**Target Metrics**
- API response time (p95): <200ms
- Database query time (p95): <100ms
- Document upload (single file): <5s
- Batch analysis (10 files): <30s
- OCR processing (per page): <10s
- Page load time: <2s

---

## 7. Project Instructions Summary

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

## 8. Environment Variables

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

## 9. Database Migrations

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
