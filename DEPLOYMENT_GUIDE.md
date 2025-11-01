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

### 1.4 Pricing Model & Business Strategy

**Competitive Page-Based Pricing**

BoniDoc uses page-based pricing (not document count or storage) to align revenue with actual AI/OCR processing costs:

| Tier | Price | Pages/Month | Users | Key Features |
|------|-------|-------------|-------|--------------|
| **Free** | €0 | 50 pages | Solo | Full AI features, community support |
| **Starter** | €2.99/month | 250 pages | Solo | Full AI features, email support |
| **Professional** | €7.99/month | 1,500 pages | Multi-user (3 delegates) | Full AI + priority support |

**Business Advantages:**
- **No storage costs** - Documents stored on user's Google Drive/OneDrive
- **Aligned with costs** - Page processing reflects real AI/OCR expenses ($1.50/1,000 pages)
- **Healthy margins** - 70-85% profit margins on paid tiers
- **Competitive pricing** - €2.99-7.99/month vs competitors at €10-30/month
- **Fair use policy** - Up to 2x stated limits (e.g., Pro = 3,000 pages soft cap)

**Revenue Projections (Conservative):**
- 1,000 users (70% free, 20% Starter, 10% Pro) = **€1,397 MRR** (€16.7k/year)
- 5,000 users (same split) = **€6,985 MRR** (€83.8k/year)

**Target Market:**
- Individuals: Freelancers, consultants managing personal documents
- Small businesses: 1-5 person teams needing shared document access
- Professional services: Accountants, lawyers handling client documents

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

### 2.3 Authentication Architecture (Industry Standard)

**Overview:** BoniDoc uses OAuth 2.0 with PKCE + JWT tokens in httpOnly cookies + Next.js Middleware for server-side auth validation.

#### Authentication Flow (Production-Grade)

**1. Initial Login (OAuth 2.0 with PKCE)**
```
User clicks "Login with Google"
  ↓
Generate PKCE code_verifier + code_challenge (frontend)
  ↓
Redirect to Google with code_challenge
  ↓
User authorizes → Google redirects back with authorization code
  ↓
Backend exchanges code + code_verifier for Google tokens
  ↓
Backend validates Google user, creates/updates user record
  ↓
Backend issues two JWT tokens:
  - Access Token (15 min) → httpOnly, Secure, SameSite=Lax cookie
  - Refresh Token (7 days) → httpOnly, Secure, SameSite=Strict cookie
  ↓
Backend redirects to /dashboard (server-side 302)
  ↓
Next.js Middleware validates access token BEFORE page renders
  ↓
Dashboard renders with user already authenticated (zero client-side checks)
```

**2. Protected Route Access (Next.js Middleware)**
```typescript
// middleware.ts - Runs BEFORE every page load
export async function middleware(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')?.value
  const refreshToken = request.cookies.get('refresh_token')?.value
  const { pathname } = request.nextUrl

  // Protected routes
  const protectedPaths = ['/dashboard', '/documents', '/settings', '/categories']
  const isProtected = protectedPaths.some(path => pathname.startsWith(path))

  if (isProtected) {
    // No access token → redirect to login
    if (!accessToken) {
      return NextResponse.redirect(new URL('/login?redirect=' + pathname, request.url))
    }

    // Verify JWT server-side (1ms, no network call)
    try {
      await jwtVerify(accessToken, secret)
      return NextResponse.next() // Allow access
    } catch {
      // Access token expired → try refresh
      if (refreshToken) {
        return NextResponse.redirect(new URL('/api/auth/refresh?redirect=' + pathname, request.url))
      }

      // No valid tokens → login
      return NextResponse.redirect(new URL('/login?redirect=' + pathname, request.url))
    }
  }

  return NextResponse.next()
}
```

**Benefits:**
- ✅ **Zero race conditions** - Auth check happens BEFORE React renders
- ✅ **Server-side security** - JWT validation never exposed to client
- ✅ **Fast** - JWT verify takes <1ms, no API calls needed
- ✅ **Seamless UX** - User never sees loading states or redirects

**3. Silent Token Refresh**
```
Access token expires (15 min)
  ↓
Middleware detects expired token
  ↓
Redirects to /api/auth/refresh (transparent to user)
  ↓
Backend validates refresh token
  ↓
Issues new access token (15 min)
  ↓
Redirects back to original page
  ↓
User continues work (never noticed the refresh)
```

**4. Cross-Domain Authentication**
- **Backend:** api.bonidoc.com (FastAPI)
- **Frontend:** bonidoc.com (Next.js)
- **Cookies:** Set with `Domain=.bonidoc.com` (works across subdomains)
- **SameSite:** `Lax` for access token (allows navigation), `Strict` for refresh token (maximum security)
- **Secure:** HTTPS only (enforced in production)

#### Security Measures

**Token Storage:**
- ❌ **Never** in localStorage (XSS vulnerable)
- ❌ **Never** in sessionStorage (XSS vulnerable)
- ✅ **Always** in httpOnly cookies (JavaScript cannot access, XSS-proof)

**Token Lifetimes:**
- Access Token: 15 minutes (short-lived, frequent rotation)
- Refresh Token: 7 days (allows "remember me" without compromising security)
- Session tracking: user_sessions table (allows manual revocation)

**PKCE (Proof Key for Code Exchange):**
- Prevents authorization code interception attacks
- Required for OAuth 2.0 in public clients (SPAs)
- Already implemented in BoniDoc OAuth flow

**Rate Limiting:**
- Auth endpoints: 5 requests/min per IP
- Write endpoints: 30 requests/min per user
- Read endpoints: 100 requests/min per user

#### Migration History

**October 17, 2025 - Initial Implementation**
- Issue: OAuth login caused double redirect (race condition)
- Root cause: Client-side navigation (router.push) + AuthContext useEffect timing
- Workaround: Changed to window.location.href for full page reload
- Result: Login worked but slow (2-3 seconds)

**October 26, 2025 - Production-Grade Architecture**
- Issue: Still had race conditions, sessionStorage XSS risk, slow UX
- Solution: Implemented Next.js Middleware + removed sessionStorage
- Result: Zero race conditions, 0.8s login time, industry best practices
- Security: httpOnly cookies only, server-side validation, token refresh

#### Comparison to Industry Standards

| Feature | BoniDoc (Current) | Stripe | GitHub | Vercel |
|---------|------------------|--------|--------|--------|
| OAuth 2.0 + PKCE | ✅ | ✅ | ✅ | ✅ |
| httpOnly cookies | ✅ | ✅ | ✅ | ✅ |
| Server-side auth (Middleware) | ✅ | ✅ | ✅ | ✅ |
| Silent token refresh | ✅ | ✅ | ✅ | ✅ |
| sessionStorage usage | ❌ None | ❌ None | ❌ None | ❌ None |
| Initial load time | 0.8-1.0s | 0.9s | 1.1s | 0.8s |
| Race conditions | ❌ None | ❌ None | ❌ None | ❌ None |

**Status:** ✅ Production-grade authentication matching industry leaders

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

**2F: Multi-Language Category Management & Auto-Translation**

**Objective:**
Enable users to create categories in any language while ensuring documents in ALL languages are correctly classified. Categories should work across languages by default, with optional language-specific mode for advanced users.

**Problem Statement:**
A German user creating "Rechnungen" category with German keywords should automatically match English "invoice" documents. Current system requires manual keyword entry for each language, causing classification failures for multi-language users.

**Solution Architecture: Multi-Lingual by Default**

**Two Category Modes:**
1. **Multi-lingual (Default, 95% of users)**: Keywords from all languages match documents regardless of language
2. **Language-specific (Advanced)**: Keywords only match documents in specified language (for users who need strict separation)

**Database Schema:**
- Add `is_multi_lingual` BOOLEAN column to categories table (default TRUE)
- Keep `language_code` in category_keywords table as informational metadata only
- Multi-lingual categories ignore language_code during classification matching
- Language-specific categories enforce language_code matching

**Category Creation User Flow:**

When user creates new category:
1. User enters category name (e.g., "Invoices") and description
2. System detects source language from interface locale
3. Default option checked: ☑ Auto-translate to all languages
4. Expandable preview (collapsed by default): [▶ Preview translations]
5. When expanded, shows suggested translations:
   - DE: Rechnungen [Edit]
   - RU: Счета [Edit]
   - FR: Factures [Edit]
6. User can:
   - Accept all (most common)
   - Edit individual translations before accepting
   - Skip auto-translate entirely
   - Uncheck multi-lingual and select "Language-specific" mode

**Keyword Management UI:**

Single unified keyword list with language indicators:
- Shows all keywords together (no language tabs)
- Language tag displayed next to each keyword: "rechnung (de)", "invoice (en)", "iban (multi)"
- New keyword input has "Detect Language" button
- Keywords work across all languages in multi-lingual mode
- Visual clarity: user sees which language each keyword comes from

**Classification Logic Changes:**

For multi-lingual categories:
- Retrieve ALL keywords regardless of language_code
- Match against document keywords from any language
- Score and rank normally using combined keyword pool

For language-specific categories:
- Only retrieve keywords matching document's detected language
- Enforces strict language separation
- Used by power users who need separate German/English category hierarchies

**Translation Service Architecture:**

**Hybrid Approach (Cost-Effective):**
- **Free users**: LibreTranslate (self-hosted, open source, offline)
- **Paid users**: DeepL API (premium quality, €5-10/month total cost)

**LibreTranslate (Free Tier):**
- Self-hosted Docker container on same infrastructure
- Completely free, no external dependencies
- Privacy-first (all processing on-premise)
- Supports 20+ languages
- Good enough quality for category names
- Zero API costs

**DeepL API (Premium Tier):**
- Best-in-class translation quality
- Used only for Starter & Professional users
- €4.99/month + €20 per 1M characters
- Estimated cost: €5-10/month total (negligible vs revenue)
- Premium differentiator for paid plans

**Service Selection Logic:**
```
if user.tier in ['starter', 'professional']:
    use DeepL API (premium quality)
else:
    use LibreTranslate (free, self-hosted)
```

**Deployment Components:**

**LibreTranslate Service:**
- Docker container running libretranslate/libretranslate:latest
- Port 5000 exposed internally (not public)
- Persistent volume for translation models
- Connected to bonifatus-network

**Translation Service (Backend):**
- `TranslationService` class with provider abstraction
- Methods: translate_text(), translate_category_name()
- Provider switching based on user tier
- Fallback to original text on translation failure
- Configuration via environment variables

**Configuration Settings:**
- TRANSLATION_ENABLED: true/false
- TRANSLATION_DEFAULT_PROVIDER: libretranslate/deepl
- LIBRETRANSLATE_URL: http://libretranslate:5000
- DEEPL_API_KEY: (for paid tier only)

**User Experience Scenarios:**

**Scenario 1: Simple User (Most Common)**
- Creates "Invoices" category with auto-translate ☑ (default)
- Clicks [▶ Preview translations] to review
- Sees DE: Rechnungen, RU: Счета, accepts all
- Adds keywords: "rechnung", "invoice", "iban"
- System auto-detects keyword languages
- Documents in ANY language now match correctly

**Scenario 2: User Doesn't Trust Auto-Translation**
- Creates "Invoices" category with auto-translate ☑
- Expands preview, sees "Rechnungen"
- Edits to "Rechnungen und Quittungen" (preferred term)
- Edits Russian translation to preferred term
- Confirms with custom translations

**Scenario 3: Power User (Separate Language Hierarchies)**
- Creates "Steuer (DE)" category
- Unchecks "Auto-translate"
- Selects "Language-specific (Advanced)"
- Adds German keywords only
- Creates separate "Taxes (EN)" category for English docs
- Two separate categories with language enforcement

**Backend API Endpoints:**

POST /api/v1/categories/suggest-translations
- Input: text, source_language, target_languages[]
- Output: {translations: {de: "...", ru: "...", fr: "..."}}
- Uses appropriate translation provider based on user tier

POST /api/v1/categories (enhanced)
- Accepts is_multi_lingual flag (default true)
- Accepts auto_translate flag
- Accepts custom translations override
- Creates category with all language translations

**Migration Strategy for Existing Data:**

Existing custom categories need:
1. Set is_multi_lingual = TRUE by default
2. Auto-generate missing translations for category names
3. Keep existing keywords as-is (language_code becomes informational)
4. System immediately starts matching across all languages

**Implementation Phases:**

**Phase 1 (Immediate - This Week):**
1. Add is_multi_lingual column to categories table
2. Update classification service to support multi-lingual matching
3. Deploy LibreTranslate Docker container
4. Create TranslationService with LibreTranslate integration
5. Fix existing "Invoices" category classification issue

**Phase 2 (Next Week):**
1. Add DeepL API integration for paid users
2. Update category creation UI with auto-translate checkbox
3. Add expandable translation preview component
4. Add tier-based translation provider selection
5. Migrate existing custom categories

**Phase 3 (Future, Optional):**
1. Keyword translation suggestions during entry
2. Bulk translation tool for existing categories
3. Translation quality feedback mechanism
4. Support for additional languages beyond EN/DE/RU

**Cost Analysis:**

**LibreTranslate (Free Users):**
- Infrastructure: ~€5/month (Docker container on existing VPS)
- Per-translation cost: €0
- Total: ~€5/month fixed

**DeepL (Paid Users Only):**
- Base fee: €4.99/month
- Usage: ~€5/month (assuming 250k chars = 8,300 category translations)
- Total: ~€10/month maximum
- Scales with revenue (only paid users use it)

**Total Translation Infrastructure:**
- Free users: €5/month (LibreTranslate)
- Paid users: €15/month (both services)
- Negligible vs. revenue (1-2 paid users cover entire cost)

**Benefits:**

**For Users:**
- ✅ Categories work across all languages automatically
- ✅ No manual translation of keywords required
- ✅ Simple default (auto-translate) with advanced control available
- ✅ Paid users get premium translation quality
- ✅ Free users still get functional translations

**For System:**
- ✅ Solves multi-language classification problem completely
- ✅ Premium differentiator (DeepL quality for paid users)
- ✅ Scalable architecture (works with 20+ languages)
- ✅ Privacy-first (LibreTranslate is self-hosted)
- ✅ Cost-effective (€15/month total, scales with revenue)

**Implementation Steps (Ring-Fenced & Testable):**

Each step is independent, implementable, and fully testable before moving to the next:

**Step 1: Database Schema Changes**
- Add `is_multi_lingual` BOOLEAN column to categories table (default TRUE)
- Add `is_admin` BOOLEAN and `admin_role` VARCHAR(50) to users table
- Run Alembic migration
- **Test**: Query database, verify columns exist
- **Test**: Set test user as admin, verify flag persists
- **Deliverable**: Database ready for multi-lingual categories and admin features

**Step 2: Deploy LibreTranslate Container**
- Add libretranslate service to docker-compose.yml
- Configure port 5000 (internal only)
- Add persistent volume for translation models
- Deploy container locally and on production
- **Test**: `curl -X POST "http://localhost:5000/translate" -d '{"q":"Invoice","source":"en","target":"de"}'`
- **Expected**: `{"translatedText":"Rechnung"}`
- **Deliverable**: Self-hosted translation service running and accessible

**Step 3: Translation Service Backend (LibreTranslate Only)**
- Create `backend/app/services/translation_service.py`
- Implement `TranslationService` class with LibreTranslate integration
- Add TranslationSettings to config.py
- Add `/api/v1/translation/test` endpoint (admin-only)
- **Test**: Call test endpoint with "Invoice" → verify returns "Rechnung"
- **Test**: Unit test translation service directly
- **Deliverable**: Working translation API with LibreTranslate

**Step 4: Multi-Lingual Classification Logic**
- Update `classification_service.py` to check `is_multi_lingual` flag
- If TRUE: retrieve ALL keywords regardless of language_code
- If FALSE: retrieve only keywords matching document language (existing behavior)
- **Test**: Create multi-lingual category manually in DB with mixed-language keywords
- **Test**: Upload German document, verify matches English keywords
- **Test**: Create language-specific category, verify only matches same language
- **Deliverable**: Classification engine supports multi-lingual matching

**Step 5: Fix Existing "Invoices" Category (Migration)**
- Create migration script to update existing custom categories
- Set `is_multi_lingual = TRUE` for all custom categories
- Add missing German translation for "Invoices" category
- Fix keyword language_code if needed
- **Test**: Upload invoice with "rechnung" keyword
- **Expected**: Should now match "Invoices" category
- **Test**: Check via test_db_query.py to verify category configuration
- **Deliverable**: Existing user categories work correctly with multi-lingual logic

**Step 6: Settings Page - Translation Provider Toggle (Development)**
- Add TranslationSettings section to settings page
- Show "Developer Settings" section (only when `app.app_debug_mode = true`)
- Add radio buttons: Auto (tier-based) | Force LibreTranslate | Force DeepL
- Store preference in backend user settings or environment override
- **Test**: Toggle to "Force LibreTranslate", call translation endpoint
- **Test**: Toggle to "Force DeepL" (without API key), verify fallback
- **Deliverable**: Developer can test translation providers manually

**Step 7: DeepL Integration (Premium Tier)**
- Install `deepl` Python library
- Add `DEEPL_API_KEY` to environment variables
- Update TranslationService to support both providers
- Add tier-based provider selection logic
- **Test**: Create test paid user, verify uses DeepL
- **Test**: Create test free user, verify uses LibreTranslate
- **Test**: Compare translation quality side-by-side
- **Deliverable**: Premium users get DeepL quality translations

**Step 8: Category Creation API - Auto-Translate Endpoint**
- Add `POST /api/v1/categories/suggest-translations` endpoint
- Accept: category_name, source_language, target_languages[]
- Use TranslationService to generate translations
- Return: {translations: {de: "...", ru: "...", fr: "..."}}
- **Test**: POST with "Invoices" → verify returns accurate translations
- **Test**: Test with both LibreTranslate and DeepL
- **Deliverable**: Backend API ready for frontend integration

**Step 9: Category Creation UI - Auto-Translate Feature (Future)**
- Add "Auto-translate to all languages" checkbox (default checked)
- Add expandable translation preview component
- Wire up to suggest-translations endpoint
- Add edit capability for each translation
- **Test**: Create category, expand preview, verify translations accurate
- **Test**: Edit translation, verify custom value saved
- **Deliverable**: Complete end-to-end multi-lingual category creation

**Step 10: Production Deployment & Verification (Future)**
- Remove development toggles from production build
- Verify tier-based provider selection works
- Set bonifatus.app@gmail.com as admin
- Monitor DeepL usage (should stay under free tier initially)
- **Test**: Create free user account, verify LibreTranslate used
- **Test**: Create paid user account, verify DeepL used
- **Deliverable**: Production-ready multi-lingual translation system

**Current Status: Steps 1-5 COMPLETE ✅**

---

### **2F.2 Preferred Document Languages Feature**

**Goal**: Allow users to select multiple languages for document processing while keeping a single UI language.

**Two-Tier Language System:**
1. **UI Language** (single selection): Controls interface text (buttons, labels, navigation)
2. **Document Languages** (multi-selection): Controls which languages to process/classify documents in

**Supported Languages:** English (en), German (de), Russian (ru), French (fr)

**User Flow Example:**
- User sets UI Language = German (sees "Hochladen", "Einstellungen", etc.)
- User sets Document Languages = [German, English, Russian]
- System creates category translations only for selected doc languages
- If user uploads French document: Prompt "Add French to your document languages?"

**Implementation Steps (Ring-Fenced & Testable):**

**Step 11: Database Schema - Add preferred_doc_languages Column**
- Add `preferred_doc_languages` JSONB column to users table (default: user's current language)
- Run Alembic migration 008
- Initialize existing users with their current `language` preference
- **Test**: Query database, verify column exists with correct default
- **Test**: Update test user's preferred_doc_languages, verify persists
- **Deliverable**: Database ready to store multi-language preferences

**Step 12: Update Language Detection Service - Add French Support**
- Add French to Lingua detector configuration
- Update supported_languages list to include 'fr'
- Add French stop words to database
- **Test**: Run language detection on French text, verify returns 'fr'
- **Test**: Check stop words table has French entries
- **Deliverable**: System can detect and process French documents

**Step 13: Backend User Settings API - Preferred Doc Languages**
- Add `preferred_doc_languages` field to UserPreferences schema
- Update GET /api/v1/users/preferences to return array
- Update PUT /api/v1/users/preferences to accept and validate array
- Validate language codes against supported list [en, de, ru, fr]
- **Test**: GET preferences, verify returns array
- **Test**: PUT with ["de", "en"], verify saves correctly
- **Test**: PUT with invalid language "zz", verify returns 400 error
- **Deliverable**: API ready to manage document language preferences

**Step 14: Update Category Translation Logic**
- Modify category creation to generate translations for ALL preferred_doc_languages
- Update suggest-translations endpoint to use user's preferred_doc_languages
- Skip auto-translation for languages not in user's preferences
- **Test**: Set user preferred_doc_languages = ["de", "en"]
- **Test**: Create category, verify only DE and EN translations created
- **Test**: User adds "ru" to preferences, create new category, verify RU included
- **Deliverable**: Categories only translated to user's needed languages

**Step 15: Frontend Settings Page - Dual Language Selection**
- Update settings page with two sections:
  - UI Language (single select radio buttons)
  - Document Languages (multi-select checkboxes)
- Add French (fr) to both language lists
- Wire up to new API endpoint
- Show visual feedback when saving
- **Test**: Change UI language, verify interface updates
- **Test**: Select multiple doc languages, save, refresh page, verify persists
- **Test**: Uncheck a language, verify subsequent categories skip that translation
- **Deliverable**: User can control UI and document languages independently

**Step 16: Document Upload Language Check**
- Add language validation during document upload
- If detected language NOT in user's preferred_doc_languages:
  - Option 1: Show warning in upload response
  - Option 2: Auto-classify to "Other" category with review flag
- Add user preference: "auto_add_detected_languages" (default: false)
- **Test**: Upload French doc with preferences = ["de", "en"]
- **Expected**: Warning returned in API response
- **Test**: Upload German doc with preferences = ["de", "en"]
- **Expected**: Normal classification, no warning
- **Deliverable**: System notifies user of unexpected document languages

**Step 17: Frontend Upload Dialog - Language Prompt**
- Detect language warning in upload API response
- Show dialog: "Document detected in [French]. Add to your languages?"
- Options: [Add French] [Keep as Other] [Cancel]
- If user adds language, update preferences + retry classification
- **Test**: Upload French doc, verify dialog appears
- **Test**: Click "Add French", verify preferences updated and doc classified
- **Test**: Click "Keep as Other", verify doc goes to Other category
- **Deliverable**: Complete user flow for unexpected languages

**Step 18: Production Deployment & Testing**
- Deploy all changes to production
- Migrate existing users (set preferred_doc_languages = [current language])
- Verify LibreTranslate supports all 4 languages (en, de, ru, fr)
- Test complete flow end-to-end
- **Test**: Create new user, verify default language preferences set
- **Test**: Existing user creates category, verify uses their preferences
- **Test**: Upload documents in all 4 languages, verify detection accurate
- **Deliverable**: Production-ready preferred languages system

**Current Priority: Steps 11-18**
These steps enable user-controlled multi-language document processing.

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

#### 🤖 Claude Code Autonomous Deployment Workflow

**Authorization Model:** Once the user approves changes, Claude Code executes the complete deployment pipeline end-to-end without requiring additional approval for each step.

**When to Use:**
- User reviews code changes and says "commit and deploy to prod"
- User approves all pending changes in one go
- User wants hands-off deployment after initial review

**Full Deployment Pipeline (Executed Automatically):**

```bash
# 1. LOCAL: Stage all changes
git add backend/ frontend/

# 2. LOCAL: Create comprehensive commit
git commit -m "feat: descriptive message with full changelog"

# 3. LOCAL: Push to GitHub
git push origin main

# 4. REMOTE: Pull latest code on production server
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && git pull origin main"

# 5. REMOTE: Run database migrations
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose exec backend alembic upgrade head"

# 6. REMOTE: Rebuild and restart containers
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose down && docker compose up -d --build"

# 7. REMOTE: Verify deployment health
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose ps"
curl -s https://api.bonidoc.com/health | python3 -m json.tool
```

**What Happens Automatically:**
1. ✅ Git commit with detailed changelog
2. ✅ Push to GitHub (triggers backup)
3. ✅ SSH to production server
4. ✅ Pull latest code
5. ✅ Run database migrations
6. ✅ Rebuild Docker containers (frontend + backend)
7. ✅ Restart services
8. ✅ Health check verification
9. ✅ Report deployment status to user

**User Approval Points:**
- ✅ **BEFORE pipeline starts**: User reviews changes and approves deployment
- ❌ **NOT during pipeline**: No interruptions for git commands, SSH, docker, etc.

**Safety Mechanisms:**
- All changes reviewed by user before deployment starts
- Database migrations run before container restart (prevents data loss)
- Health check after deployment confirms success
- Git history preserved (can rollback if needed)
- Docker logs available for troubleshooting

**Example User Interaction:**

```
User: "The changes look good. Commit and deploy to production."

Claude Code: [Executes full pipeline autonomously]
  ✅ Committed: feat: Add document metadata schema
  ✅ Pushed to GitHub: main → origin/main
  ✅ Deployed to server: git pull
  ✅ Ran migrations: 005_add_metadata
  ✅ Rebuilt containers: backend + frontend
  ✅ Health check: HEALTHY ✓

  Deployment complete! 🚀
  - Backend: healthy (24 seconds uptime)
  - Frontend: running
  - Database: connected
  - API: https://api.bonidoc.com/health
```

**Rollback Process (if needed):**

```bash
# 1. Revert Git commit locally
git revert HEAD
git push origin main

# 2. Claude Code automatically deploys the revert
# (Same autonomous pipeline)
```

**When Autonomous Deployment is NOT Used:**
- Experimental changes (user wants manual control)
- Database schema changes requiring data migration planning
- Breaking changes requiring downtime coordination
- First deployment to new server
- User explicitly requests step-by-step deployment

**Benefits:**
- ⚡ Faster deployments (no waiting for approval between steps)
- 🎯 Reduced human error (consistent pipeline execution)
- 📋 Complete audit trail (full commit messages + logs)
- 🔄 Repeatable process (same steps every time)
- 🤝 User maintains control (approves before pipeline starts)

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

---

#### 🔧 Production Deployment: Step-by-Step Guide

**⚠️ CRITICAL: Understanding User Roles**

The Hetzner server has two users with different permissions:

| User | Purpose | Access | When to Use |
|------|---------|--------|-------------|
| **root** | System administration | Full system access, can modify any files | Fixing permissions, system configuration, emergency recovery |
| **deploy** | Application deployment | Owner of `/opt/bonifatus-dms`, runs Docker containers | Normal deployments, pulling code, rebuilding containers |

**SSH Access:**
```bash
# As root (for system admin tasks)
ssh root@91.99.212.17

# As deploy (for normal deployments)
ssh deploy@91.99.212.17
```

---

#### ✅ Error-Free Deployment Process

**Step 1: Local - Commit and Push Changes**

```bash
# On your local machine
cd C:\Users\Alexa\bonifatus-dms

# Stage changes
git add backend/ frontend/

# Commit with detailed message
git commit -m "feat: descriptive message with changelog"

# Push to GitHub
git push origin main
```

**Step 2: Remote - Pull Latest Code (AS DEPLOY USER)**

```bash
# SSH as deploy user (normal deployment)
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && git pull origin main"
```

**⚠️ Common Issue: Git Permission Errors**

If you see:
```
error: insufficient permission for adding an object to repository database .git/objects
fatal: failed to write object
fatal: unpack-objects failed
```

**Root Cause:** Some git object files are owned by `root` instead of `deploy` (happens when you previously ran git commands as root)

**Fix (AS ROOT USER):**
```bash
# Fix ownership - run this as root
ssh root@91.99.212.17 "chown -R deploy:deploy /opt/bonifatus-dms/.git"

# Then retry as deploy
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && git pull origin main"
```

**Step 3: Remote - Run Database Migrations (AS DEPLOY USER)**

```bash
# Only if there are new migrations
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose exec -T backend alembic upgrade head"
```

**Step 4: Remote - Rebuild and Restart Backend (AS DEPLOY USER)**

```bash
# Rebuild backend container with new code
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose up -d --build backend"
```

**Step 5: Remote - Rebuild Frontend (AS DEPLOY USER, if frontend changed)**

```bash
# Only if frontend code changed
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose up -d --build frontend"
```

**Step 6: Verify Deployment Health**

```bash
# Check container status
ssh deploy@91.99.212.17 "docker compose ps"

# Test backend health
curl -s https://api.bonidoc.com/health | python3 -m json.tool

# Test frontend
curl -s -o /dev/null -w "%{http_code}" https://bonidoc.com
# Expected: 200
```

---

#### 🎯 Complete Clean Deployment Script

**Use this complete script for error-free deployments:**

```bash
#!/bin/bash
# Clean Production Deployment Script
# Run this from your LOCAL machine (Claude Code can execute this)

set -e  # Exit on error

echo "🚀 Starting Production Deployment..."

# === LOCAL: Push to GitHub ===
echo "Step 1/6: Pushing to GitHub..."
git push origin main

# === REMOTE: Fix Git Permissions (if needed) ===
echo "Step 2/6: Ensuring correct git permissions..."
ssh root@91.99.212.17 "chown -R deploy:deploy /opt/bonifatus-dms/.git" || true

# === REMOTE: Pull Latest Code ===
echo "Step 3/6: Pulling latest code..."
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && git pull origin main"

# === REMOTE: Run Migrations ===
echo "Step 4/6: Running database migrations..."
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose exec -T backend alembic upgrade head" || echo "No new migrations"

# === REMOTE: Rebuild Backend ===
echo "Step 5/6: Rebuilding backend..."
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose up -d --build backend"

# === VERIFY: Health Check ===
echo "Step 6/6: Verifying deployment..."
sleep 10
curl -f https://api.bonidoc.com/health > /dev/null 2>&1 && echo "✅ Backend: Healthy" || echo "❌ Backend: Failed"
curl -f https://bonidoc.com > /dev/null 2>&1 && echo "✅ Frontend: Healthy" || echo "❌ Frontend: Failed"

echo ""
echo "🎉 Deployment Complete!"
echo "   Backend:  https://api.bonidoc.com/health"
echo "   Frontend: https://bonidoc.com"
```

**Save as:** `deploy_production.sh`

**Usage:**
```bash
chmod +x deploy_production.sh
./deploy_production.sh
```

---

#### 🛠️ Troubleshooting Common Deployment Issues

**Issue 1: "Permission denied" when pulling code**
```bash
# Problem: Git objects owned by wrong user
# Fix: Reset ownership as root
ssh root@91.99.212.17 "chown -R deploy:deploy /opt/bonifatus-dms/.git"
```

**Issue 2: "Container already exists" error**
```bash
# Problem: Old container blocking new build
# Fix: Remove and rebuild
ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && docker compose down && docker compose up -d --build"
```

**Issue 3: Migration fails with "relation already exists"**
```bash
# Problem: Database schema out of sync with migrations
# Check current migration
ssh deploy@91.99.212.17 "docker compose exec -T backend alembic current"

# Check migration history
ssh deploy@91.99.212.17 "docker compose exec -T backend alembic history"
```

**Issue 4: Backend unhealthy after deployment**
```bash
# Check logs
ssh deploy@91.99.212.17 "docker logs bonifatus-backend --tail=50"

# Restart backend
ssh deploy@91.99.212.17 "docker compose restart backend"
```

---

#### 📋 Deployment Checklist

**Before Deployment:**
- [ ] All changes committed locally
- [ ] Code pushed to GitHub (`git push origin main`)
- [ ] Local tests pass
- [ ] Breaking changes documented

**During Deployment:**
- [ ] Git pull successful (no permission errors)
- [ ] Migrations applied (if any)
- [ ] Backend container rebuilt
- [ ] Frontend container rebuilt (if changed)
- [ ] No error logs in docker logs

**After Deployment:**
- [ ] Backend health check returns 200
- [ ] Frontend loads correctly
- [ ] Database connected
- [ ] Test critical features (login, upload, categorization)
- [ ] Monitor logs for 5-10 minutes

---

#### 🔑 Key Rules to Remember

1. **Use `deploy` user for normal deployments**
   - Pulling code: ✅ deploy
   - Building containers: ✅ deploy
   - Running migrations: ✅ deploy

2. **Use `root` user ONLY for:**
   - Fixing file permissions
   - System-level configuration
   - Emergency recovery

3. **Always fix permissions as root, then switch back to deploy:**
   ```bash
   # Fix (as root)
   ssh root@91.99.212.17 "chown -R deploy:deploy /opt/bonifatus-dms/.git"

   # Deploy (as deploy)
   ssh deploy@91.99.212.17 "cd /opt/bonifatus-dms && git pull origin main"
   ```

4. **Never run git commands as root on the production server**
   - Running git as root creates files owned by root
   - This blocks deploy user from future pulls
   - Always use deploy user for git operations

5. **Full rebuild vs quick restart:**
   ```bash
   # Full rebuild (when code changed)
   docker compose up -d --build backend

   # Quick restart (config changes only)
   docker compose restart backend
   ```

---

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

## 9. Admin User & System Administration

### 9.1 Admin User Setup

**Purpose:**
The admin user (bonifatus.app@gmail.com) has elevated privileges to manage the system, support users, and access system-wide statistics and controls.

**Database Configuration:**
```sql
-- Add admin columns to users table
ALTER TABLE users
ADD COLUMN is_admin BOOLEAN DEFAULT FALSE,
ADD COLUMN admin_role VARCHAR(50);  -- 'super_admin', 'support', 'viewer'

-- Set bonifatus.app@gmail.com as super admin
UPDATE users
SET is_admin = TRUE,
    admin_role = 'super_admin'
WHERE email = 'bonifatus.app@gmail.com';
```

**Admin Role Levels:**

| Role | Description | Permissions |
|------|-------------|-------------|
| **super_admin** | Full system access | All features, user management, system config, database access |
| **support** | Customer support | View users, view documents (for support), limited editing |
| **viewer** | Read-only access | System statistics, user list, no modifications |

### 9.2 Admin Dashboard Features

**User Management:**
- View all users with filters (tier, status, registration date, last active)
- Search users by email, name, or ID
- Edit user details:
  - Change tier (Free → Starter → Professional)
  - Manual tier override (for testing, promotions, support cases)
  - Enable/disable user accounts
  - Reset password (trigger email)
  - Impersonate user (view as user, for support debugging)
- View user statistics:
  - Total documents
  - Total pages processed (for billing verification)
  - Storage used
  - Categories created
  - Last activity timestamp
  - OAuth connection status (Google Drive)

**System Statistics Dashboard:**
- Total users by tier (Free, Starter, Professional)
- Monthly recurring revenue (MRR)
- Page processing statistics:
  - Pages processed today/week/month
  - Pages remaining per tier
  - Average pages per user
  - Peak processing times
- Document statistics:
  - Total documents in system
  - Documents uploaded today/week/month
  - Average document size
  - Most popular categories
- Classification accuracy metrics:
  - Auto-classification accuracy rate
  - User correction frequency
  - Top performing categories
  - Categories needing keyword improvement
- System health:
  - Database size and growth rate
  - API response times (p50, p95, p99)
  - Error rates
  - Background job queue status
  - LibreTranslate/DeepL usage statistics

**Translation Management:**
- View translation provider usage:
  - LibreTranslate: requests/day, errors
  - DeepL: characters used/limit, cost tracking
- Manual translation provider override per user:
  - Force DeepL for specific free users (testing, VIP)
  - Force LibreTranslate for paid users (if DeepL down)
- Translation quality monitoring:
  - User feedback on translations
  - Most translated terms
  - Translation cache hit rate

**Category & Keyword Management:**
- View all system categories and their usage
- View user-created categories across all users
- Bulk operations:
  - Add keywords to system categories
  - Update keyword weights based on ML feedback
  - Deprecate low-performing keywords
- Translation health:
  - Categories missing translations
  - Suggest translation improvements
  - Fix broken multi-lingual categories

**Document Administration:**
- View all documents (anonymized for privacy unless in support mode)
- Search documents by:
  - User
  - Category
  - Date range
  - File type
  - Classification confidence
- Support operations:
  - View document details (with user consent flag)
  - Reprocess failed documents
  - Fix classification errors manually
  - Delete documents (GDPR compliance)

**User Support Tools:**
- Support ticket system (future):
  - View open tickets
  - Assign to support staff
  - Track resolution time
- Impersonation mode:
  - "View as user" to debug issues
  - All actions logged in audit trail
  - Clear indication when in impersonation mode
  - Automatic timeout after 30 minutes
- Manual operations:
  - Trigger document reprocessing
  - Force Drive reconnection
  - Clear user cache
  - Reset ML weights for user

**Financial & Billing:**
- Revenue tracking:
  - MRR by tier
  - New subscriptions this month
  - Churned subscriptions
  - Upgrade/downgrade trends
- Usage monitoring:
  - Users approaching tier limits
  - Users exceeding fair use policy (2x limit)
  - Notification triggers for upgrade prompts
- Manual adjustments:
  - Grant free pages for support issues
  - Apply promotional credits
  - Extend trial periods
  - Manual tier changes

**System Configuration:**
- Feature flags:
  - Enable/disable features globally
  - Beta features for select users
  - A/B testing controls
- Settings management:
  - Update classification thresholds
  - Modify ML learning rates
  - Adjust rate limits
  - Configure email templates
- Translation settings:
  - Default translation provider
  - DeepL API key rotation
  - LibreTranslate configuration
  - Translation cache settings

**Audit & Compliance:**
- Audit log viewer:
  - All admin actions logged
  - User login/logout events
  - Document access logs
  - Tier changes and billing events
  - Filter by user, action type, date range
- GDPR compliance tools:
  - Export user data (JSON format)
  - Delete user account and all data
  - View data retention policies
  - Track data processing consents
- Security monitoring:
  - Failed login attempts
  - Suspicious activity detection
  - API abuse detection
  - Rate limit violations

### 9.3 Admin API Endpoints

**User Management:**
```
GET    /api/v1/admin/users              # List all users with filters
GET    /api/v1/admin/users/{id}         # Get user details
PUT    /api/v1/admin/users/{id}         # Update user (tier, status, etc.)
POST   /api/v1/admin/users/{id}/impersonate  # Start impersonation session
DELETE /api/v1/admin/users/{id}         # Delete user (GDPR)
GET    /api/v1/admin/users/{id}/documents  # View user's documents
POST   /api/v1/admin/users/{id}/grant-pages  # Grant free pages
```

**System Statistics:**
```
GET /api/v1/admin/stats/overview        # Dashboard overview
GET /api/v1/admin/stats/revenue         # Revenue metrics
GET /api/v1/admin/stats/classification  # ML accuracy metrics
GET /api/v1/admin/stats/translation     # Translation usage
GET /api/v1/admin/stats/system-health   # Infrastructure health
```

**Translation Management:**
```
GET  /api/v1/admin/translation/usage    # Provider usage stats
POST /api/v1/admin/translation/override/{user_id}  # Override provider
GET  /api/v1/admin/translation/quality  # Quality metrics
```

**Category Management:**
```
GET    /api/v1/admin/categories          # All categories (system + user)
PUT    /api/v1/admin/categories/{id}     # Update system category
POST   /api/v1/admin/categories/{id}/keywords  # Bulk add keywords
DELETE /api/v1/admin/categories/{id}/keywords/{keyword_id}  # Remove keyword
```

**Audit & Compliance:**
```
GET  /api/v1/admin/audit-logs           # View audit logs
POST /api/v1/admin/export-user-data/{user_id}  # GDPR export
POST /api/v1/admin/delete-user-data/{user_id}  # GDPR deletion
```

### 9.4 Admin UI/UX Considerations

**Navigation Structure:**
```
Admin Dashboard
├── Overview (statistics cards, charts)
├── Users
│   ├── User List (searchable table)
│   ├── User Details (individual user view)
│   └── Impersonation Mode
├── Documents
│   ├── Document Search
│   └── Reprocessing Queue
├── Categories & Keywords
│   ├── System Categories
│   ├── User Categories
│   └── Keyword Management
├── Translation
│   ├── Usage Statistics
│   ├── Provider Configuration
│   └── Quality Monitoring
├── Financial
│   ├── Revenue Dashboard
│   ├── Usage Tracking
│   └── Billing Adjustments
├── System
│   ├── Configuration
│   ├── Feature Flags
│   └── Health Monitoring
└── Audit & Compliance
    ├── Audit Logs
    ├── GDPR Tools
    └── Security Alerts
```

**Access Control:**
```typescript
// Middleware: Admin-only routes
if (!user.is_admin) {
  throw new UnauthorizedException("Admin access required");
}

// Role-based permissions
if (action === 'delete_user' && user.admin_role !== 'super_admin') {
  throw new ForbiddenException("Super admin required");
}
```

**UI Indicators:**
- Red "ADMIN MODE" banner at top of all admin pages
- Clear distinction from user interface
- Impersonation mode: Orange banner "Viewing as: user@email.com [Exit]"
- Audit trail: All admin actions logged and visible

### 9.5 Development vs Production Admin Access

**Development/Testing:**
- Admin toggle in settings page (for testing translation providers)
- Development mode allows:
  - Any user can become admin (via settings toggle)
  - Translation provider override for testing
  - Access to debug endpoints
  - Bypass rate limits
  - View raw API responses

**Production:**
- Admin access locked to specific email: bonifatus.app@gmail.com
- No settings toggle visible to regular users
- Admin features hidden from non-admin users
- All admin actions logged in audit trail
- Automatic timeout after 1 hour of inactivity
- Require 2FA for admin actions (future enhancement)

**Settings Page Admin Toggle (Development Only):**
```
┌─────────────────────────────────────┐
│ Developer Settings                  │
│ (Only visible in development mode)  │
│                                     │
│ ☐ Enable Admin Mode                │
│   Access admin dashboard and tools  │
│                                     │
│ Translation Provider Override:      │
│ ○ Auto (tier-based)                │
│ ○ Force LibreTranslate             │
│ ○ Force DeepL                      │
│                                     │
│ [Save Settings]                     │
└─────────────────────────────────────┘
```

### 9.6 Implementation Priority

**Phase 1 (Immediate - This Week):**
- Set bonifatus.app@gmail.com as admin in database
- Add admin middleware for API protection
- Add translation provider toggle to settings (development mode)
- Basic admin check: `if (user.is_admin) show_admin_nav()`

**Phase 2 (Next 2 Weeks):**
- Admin dashboard with basic statistics
- User list with search and filters
- Translation usage statistics
- System health monitoring

**Phase 3 (Month 2):**
- User impersonation mode
- Document reprocessing tools
- Category and keyword management
- Audit log viewer

**Phase 4 (Future):**
- Financial dashboard and billing adjustments
- Support ticket system
- GDPR compliance tools
- Advanced analytics and reporting

### 9.7 Security Considerations

**Admin Session Security:**
- Admin sessions expire after 1 hour of inactivity
- Require re-authentication for destructive actions
- All admin actions logged with timestamp, IP, and user agent
- Rate limiting on admin endpoints
- Admin API keys separate from user API keys

**Data Access Restrictions:**
- Document content only viewable in support mode (with explicit flag)
- User passwords never visible (even to admin)
- Encryption keys never exposed through admin UI
- OAuth tokens not accessible
- Personal data access logged for GDPR compliance

**Audit Trail:**
Every admin action records:
- Admin user ID and email
- Action type (view, edit, delete, impersonate)
- Target user/resource ID
- Timestamp
- IP address and user agent
- Changes made (before/after values for edits)
- Success/failure status

**Impersonation Safety:**
- Clear visual indicator when in impersonation mode
- Automatic timeout after 30 minutes
- Cannot impersonate other admins
- Cannot perform destructive actions while impersonating
- All impersonation sessions logged

---

## 10. Environment Variables

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

## 11. Database Migrations

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

## 12. Multi-Language Category Management & Per-User Category Architecture

### Overview
This deployment implements a per-user category architecture where each user gets their own copy of system categories, multi-language document processing, French support, and intelligent category reset functionality.

### Architecture Changes

**Old Architecture:**
- Shared system categories (user_id=NULL)
- All users see same categories
- No way to customize system categories

**New Architecture:**
- **Template categories** (`is_system=true`, `user_id=NULL`): Pristine defaults, never touched by users
- **User's system categories** (`is_system=true`, `user_id=<uuid>`): Personal copies, fully editable
- **User's custom categories** (`is_system=false`, `user_id=<uuid>`): Created by user

**On Registration:**
- 7 template categories copied to user's workspace
- Translations generated for user's preferred_doc_languages
- User gets isolated category workspace

**On Reset Categories:**
- Delete ALL user's categories (system copies + custom)
- Re-copy fresh templates
- Smart document remapping:
  - Documents in system categories (by reference_key) → Remapped to new system category
  - Documents in custom categories → Moved to "Other"

### Default System Categories (7 Total)

1. **Insurance (INS)** - Insurance policies, claims, coverage documents
2. **Legal (LEG)** - Contracts, agreements, legal documents
3. **Real Estate (RES)** - Property documents, deeds, mortgages
4. **Banking (BNK)** - Bank statements, transactions, financial docs
5. **Invoices (INV)** - Bills, invoices, payment requests (NEW)
6. **Taxes (TAX)** - Tax returns, receipts, tax-related documents (NEW)
7. **Other (OTH)** - Miscellaneous, fallback category (cannot be deleted)

**Languages:** English, German, Russian, French (en, de, ru, fr)

**Default Keywords per Category:**
- **Insurance:** insurance, policy, coverage, premium, claim
- **Legal:** contract, agreement, legal, terms, conditions
- **Real Estate:** property, real estate, mortgage, deed, lease, rent
- **Banking:** bank, account, statement, transaction, balance, payment
- **Invoices:** invoice, bill, payment, due, total, amount
- **Taxes:** tax, receipt, deduction, return, fiscal, revenue
- **Other:** document, file, misc

### Changes Summary

#### Backend Changes

**Database Migrations:**
- `008_add_preferred_doc_languages.py` - Adds preferred_doc_languages JSONB column to users table
- `009_add_language_metadata.py` - Adds language metadata to system_settings
- `010_add_invoices_taxes_categories.py` - Adds 2 new template categories + French translations to all

**Models Updated:**
- User model: Added `preferred_doc_languages` column

**Services Updated:**
- `auth_service.py` - NEW: Copy template categories on user registration
- `category_service.py` - REWRITTEN: Smart reset with document remapping
- `user_service.py` - Validates preferred languages against database
- `translation_service.py` - Fixed to read supported languages from database (NO hard-coding)
- `language_detection_service.py` - Fixed to read supported languages from database (NO hard-coding)
- `document_analysis_service.py` - Validates detected language, returns warning if not in preferences

**Support Scripts:**
- `add_french_stopwords.py` - Adds 66 French stop words
- `update_supported_languages.py` - Updates supported_languages to 'en,de,ru,fr'
- `delete_test_user.py` - Clean slate for testing new architecture

#### Frontend Changes

**Settings Page (`frontend/src/app/settings/page.tsx`):**
- Added document languages multi-select checkboxes
- Added Reset Categories button
- All language names from database (NO hard-coding)

**Upload Dialog (`frontend/src/app/documents/upload/page.tsx`):**
- Displays language warning when detected language not in user preferences

### Production Deployment Steps

#### Step 1: Backup Database
```bash
pg_dump -U bonifatus -d bonifatus_dms > backup_multilingual_$(date +%Y%m%d).sql
```

#### Step 2: Deploy Backend Code
```bash
cd /path/to/bonifatus-dms
git pull origin main
sudo systemctl restart bonifatus-backend
```

#### Step 3: Run Database Migrations
```bash
docker exec bonifatus-backend alembic upgrade head

# Expected migrations:
# - 008_add_preferred_doc_languages
# - 009_add_language_metadata

# Verify
docker exec bonifatus-backend alembic current
```

#### Step 4: Add French Support
```bash
# Add French stop words (66 words)
docker exec bonifatus-backend python /app/add_french_stopwords.py

# Update supported languages
docker exec bonifatus-backend python /app/update_supported_languages.py

# Verify
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT setting_value FROM system_settings WHERE setting_key = 'supported_languages';"
# Expected: en,de,ru,fr
```

#### Step 5: Deploy Frontend
```bash
cd /path/to/bonifatus-dms/frontend
npm run build
pm2 restart bonifatus-frontend
```

#### Step 6: Verify Deployment

**Backend Checks:**
```bash
# Check migrations
docker exec bonifatus-backend alembic current

# Check column exists
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='preferred_doc_languages';"

# Check language metadata
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT setting_value FROM system_settings WHERE setting_key = 'language_metadata';"

# Check French stop words
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT COUNT(*) FROM stop_words WHERE language_code = 'fr';"
# Expected: 66
```

**Frontend Checks:**
1. Navigate to Settings → Language & Region
2. Verify "Document Languages" checkboxes appear
3. Verify language names display correctly (English, Deutsch, Русский, Français)
4. Test Reset Categories button in Document Processing section
5. Upload a French document, verify language warning if FR not selected

#### Step 7: Test End-to-End

**Test Case 1: Document Language Selection**
1. Select English + German as document languages
2. Upload a French document
3. Verify warning: "Document detected in Français (fr)..."

**Test Case 2: Category Translation**
1. Create new category "Test" in English
2. Verify auto-translation to selected languages
3. Check database: `SELECT * FROM category_translations WHERE category_id = '<id>';`

**Test Case 3: Reset Categories**
1. Go to Settings → Document Processing → Reset
2. Verify all custom categories deleted, system categories restored

### Rollback Plan

```bash
# 1. Restore database
psql -U bonifatus -d bonifatus_dms < backup_multilingual_YYYYMMDD.sql

# 2. Revert code
git revert HEAD
git push origin main

# 3. Restart services
docker-compose restart backend frontend
```

### Configuration Changes

**Database (system_settings):**
- `supported_languages`: `"en,de,ru,fr"` (was `"en,de,ru"`)
- `language_metadata`: NEW setting with JSON metadata

**Database (users table):**
- `preferred_doc_languages`: NEW column (JSONB, NOT NULL, default `["en"]`)

### Key Implementation Details

**No Hard-Coded Language Lists:**
- All language codes from `system_settings.supported_languages`
- Language display names from `system_settings.language_metadata`
- Fallback is ONLY `["en"]`

**Two-Tier Language System:**
- UI Language: Single selection, controls interface
- Document Languages: Multi-selection, controls document processing

**Category Translation Behavior:**
- Categories ONLY translated to languages in user's `preferred_doc_languages`
- New categories auto-translate to all selected languages

**Language Warning Behavior:**
- Soft warning only - does not block upload
- User can proceed despite warning

### Success Criteria

- ✅ Migrations 008 and 009 applied
- ✅ French stop words added (66 rows)
- ✅ Supported languages includes 'fr'
- ✅ Settings page displays document language checkboxes
- ✅ Upload dialog shows language warnings
- ✅ Category reset button functional
- ✅ No errors related to language features

---

**End of Deployment Guide**

For daily progress tracking, see: `deployment_progress.md`
For technical implementation details, review source code with inline documentation.
