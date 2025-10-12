BoniDoc Deployment Guide v2.0 - Complete Implementation Roadmap
Executive Summary
Document Purpose: Complete production deployment guide integrating security, document processing, classification, and Google Drive storage.
Approach: No rollback strategy. We move forward from current state, removing technical debt, implementing security essentials, and building production-grade features.
Timeline: 4 weeks to production-ready MVP

Week 1: Security essentials + database cleanup
Week 2: Document processing (text extraction + OCR) + classification
Week 3: Google Drive integration
Week 4: Testing, monitoring, production deployment


Part 1: Current Status Assessment
1.1 What's Working (Keep & Build Upon)
Infrastructure (Deployed & Functional):

✅ Google Cloud Run (backend + frontend)
✅ Supabase PostgreSQL database
✅ GitHub Actions CI/CD pipeline
✅ Google OAuth authentication
✅ JWT-based session management
✅ Alembic database migrations (10 migrations deployed)

Database Schema (26 Tables Active):
Core Tables (Production-Ready):

✅ users - User accounts (Google OAuth)
✅ user_settings - User preferences
✅ categories - Category definitions with codes
✅ category_translations - Multi-language support (en/de/ru)
✅ documents - Document metadata
✅ document_categories - Many-to-many relationship
✅ document_languages - Multi-language detection
✅ upload_batches - Batch upload tracking
✅ stop_words - Stop word filtering (162 entries)
✅ system_settings - Application configuration
✅ localization_strings - UI translations
✅ audit_logs - Activity tracking

Backend Services (Functional):

✅ Authentication service (Google OAuth + JWT)
✅ User service (CRUD operations)
✅ Category service (CRUD with translations)
✅ Document analysis service (text extraction basics)
✅ Language detection service
✅ Batch upload service (analysis endpoint)
✅ Config service (system settings)

Frontend (Deployed):

✅ Next.js 14 application
✅ Authentication flow (Google OAuth)
✅ Dark mode theme
✅ Categories page (CRUD interface)
✅ Settings page
✅ Batch upload UI (file selection, analysis results)
✅ Responsive design (mobile-friendly)

API Endpoints (Working):

✅ POST /auth/google/login - Google OAuth
✅ GET /users/me - Current user profile
✅ GET /categories - List categories
✅ POST /categories - Create category
✅ POST /document-analysis/analyze-batch - Analyze documents
✅ GET /settings/* - System settings

1.2 What Needs Deletion (Technical Debt)
Database Tables to DELETE:

❌ spelling_corrections - Unused, adds complexity
❌ ngram_patterns - Overcomplicated, no benefit
❌ keyword_training_data - Redundant with new approach
❌ category_training_data - Being replaced
❌ ocr_results - Not storing OCR results separately
❌ language_detection_patterns - Unnecessary

Database Tables to RENAME:

🔄 category_term_weights → category_keywords (clearer purpose)

Code Files to DELETE:

❌ backend/app/services/spelling_correction_service.py (if exists)
❌ References to spelling correction in ml_keyword_service.py
❌ References to n-grams in ml_keyword_service.py
❌ Bayesian training logic in ml_category_service.py (keep learning, remove Bayesian complexity)

Dependencies to REMOVE:

❌ PyPDF2==3.0.1 (replaced by PyMuPDF)

Code to REFACTOR:

🔄 ml_keyword_service.py - Simplify keyword extraction
🔄 ml_category_service.py - Replace with simpler classification
🔄 document_analysis_service.py - Add OCR support
🔄 Frontend token storage - Move from localStorage to httpOnly cookies

1.3 What's Missing (Must Implement)
Security Essentials (P0 - Week 1):

❌ HTTPS security headers (HSTS, CSP, X-Frame-Options)
❌ Field-level encryption (OAuth tokens)
❌ Token storage in httpOnly cookies (currently in localStorage)
❌ Rate limiting on all endpoints
❌ File upload validation (magic bytes, size limits)
❌ Comprehensive audit logging
❌ Session management (track active sessions)
❌ Input sanitization and validation

Document Processing (P0 - Week 2):

❌ OCR service (Tesseract for images)
❌ PDF text extraction (PyMuPDF)
❌ Image preprocessing (deskew, denoise)
❌ Keyword extraction (simplified algorithm)
❌ Document classification engine
❌ Category learning service

Google Drive Integration (P0 - Week 3):

❌ Drive OAuth flow (separate from auth)
❌ Folder structure creation
❌ File upload to Drive
❌ File download from Drive
❌ Folder management (create/rename/delete)
❌ Quota tracking

Missing Database Tables:

❌ category_keywords (renamed from category_term_weights)
❌ document_classification_log - Track classification decisions
❌ category_classification_metrics - Performance tracking
❌ google_drive_folders - Category folder mappings
❌ google_drive_sync_status - Sync state tracking
❌ user_sessions - Active session tracking


Part 2: Implementation Phases
PHASE 1: Security Foundation (Week 1)
Objective: Lock down the platform before adding features
Duration: 5 days
Output: Production-ready security baseline

Day 1: Database Cleanup & Security Schema
Step 1.1: Database Cleanup Migration
File: backend/alembic/versions/xxx_security_cleanup.py
Migration Actions:

Drop unused tables
Rename category_term_weights to category_keywords
Add encryption columns
Create session tracking table
Add security audit columns

Database Changes:
Drop Tables:
sqlDROP TABLE IF EXISTS spelling_corrections CASCADE;
DROP TABLE IF EXISTS ngram_patterns CASCADE;
DROP TABLE IF EXISTS keyword_training_data CASCADE;
DROP TABLE IF EXISTS category_training_data CASCADE;
DROP TABLE IF EXISTS language_detection_patterns CASCADE;
DROP TABLE IF EXISTS ocr_results CASCADE;
Rename Table:
sqlALTER TABLE category_term_weights RENAME TO category_keywords;
ALTER TABLE category_keywords RENAME COLUMN term TO keyword;
ALTER TABLE category_keywords RENAME COLUMN document_frequency TO match_count;
ALTER TABLE category_keywords ADD COLUMN is_system_default BOOLEAN DEFAULT false;
ALTER TABLE category_keywords ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE category_keywords ADD COLUMN last_matched_at TIMESTAMP;
Create user_sessions Table:
sqlCREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(64) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMP,
    revoked_reason VARCHAR(100)
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id, is_revoked, expires_at);
CREATE INDEX idx_sessions_token ON user_sessions(refresh_token_hash);
CREATE INDEX idx_sessions_active ON user_sessions(user_id, is_revoked) WHERE is_revoked = false;
Enhance users Table:
sqlALTER TABLE users ADD COLUMN drive_refresh_token_encrypted TEXT;
ALTER TABLE users ADD COLUMN drive_token_expires_at TIMESTAMP;
ALTER TABLE users ADD COLUMN google_drive_enabled BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN drive_permissions_granted_at TIMESTAMP;
ALTER TABLE users ADD COLUMN last_ip_address VARCHAR(45);
ALTER TABLE users ADD COLUMN last_user_agent TEXT;
ALTER TABLE users ADD COLUMN failed_login_attempts INT DEFAULT 0;
ALTER TABLE users ADD COLUMN account_locked_until TIMESTAMP;
Enhance audit_logs Table:
sqlALTER TABLE audit_logs ADD COLUMN security_level VARCHAR(20);
ALTER TABLE audit_logs ADD COLUMN security_flags JSONB;
CREATE INDEX idx_audit_security ON audit_logs(security_level, created_at DESC);
CREATE INDEX idx_audit_suspicious ON audit_logs((security_flags->>'suspicious')) WHERE security_flags->>'suspicious' = 'true';
Verification Query:
sql-- Verify cleanup
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- Should NOT include: spelling_corrections, ngram_patterns, keyword_training_data, etc.
-- Should include: category_keywords (not category_term_weights)
Execute Migration:
bashcd backend
alembic revision -m "security_cleanup_and_session_management"
# Edit generated migration file with above SQL
alembic upgrade head
Git Commit:
bashgit add backend/alembic/versions/
git commit -m "feat: database cleanup and security schema

- Drop unused tables (spelling_corrections, ngram_patterns, etc.)
- Rename category_term_weights to category_keywords
- Add user_sessions table for session tracking
- Add security columns to users and audit_logs
- Add field-level encryption support columns
- Remove technical debt from database schema"
git push origin main
Wait for Feedback:
Expected Output:
- Migration executes successfully
- Tables dropped: 6
- Table renamed: 1
- New table created: user_sessions
- Columns added to users: 6
- Columns added to audit_logs: 2

Verify in Supabase:
1. Check Tables list (should show category_keywords, not category_term_weights)
2. Query: SELECT COUNT(*) FROM user_sessions; (should return 0)
3. Query: \d users (should show new encryption columns)

Reply with: "Migration successful" or describe any errors

Step 1.2: Encryption Service Implementation
File: backend/app/services/encryption_service.py
Purpose: Encrypt sensitive data (OAuth tokens) before storing in database
Implementation:
Dependencies to Add:
backend/requirements.txt:
cryptography==41.0.5
Service Structure:
Class: EncryptionService
Methods:

__init__() - Load encryption key from environment
encrypt(plaintext: str) -> str - Encrypt data (returns base64 string)
decrypt(ciphertext: str) -> str - Decrypt data
_get_encryption_key() -> bytes - Load key from Secret Manager or env
verify_encryption() -> bool - Test encryption/decryption works

Key Management:
Environment Variable: ENCRYPTION_KEY
Generation:
bash# Generate new encryption key (run once, locally)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Output: something like "A3fG7kL9mP2qR5tW8xZ1bC4dE6hJ0nO..."

# Add to .env (development):
ENCRYPTION_KEY=<generated_key>

# Add to Google Secret Manager (production):
gcloud secrets create encryption-key --data-file=- <<< "<generated_key>"
Usage Pattern:
python# Encrypt before storing
encrypted_token = encryption_service.encrypt(oauth_refresh_token)
user.drive_refresh_token_encrypted = encrypted_token

# Decrypt when retrieving
encrypted_token = user.drive_refresh_token_encrypted
oauth_refresh_token = encryption_service.decrypt(encrypted_token)
Error Handling:

If decryption fails: Clear token, require re-authentication
If key missing: Raise configuration error, don't start server
Log decryption failures as security events

Testing:
python# Test encryption service
plaintext = "test_secret_value"
encrypted = encryption_service.encrypt(plaintext)
decrypted = encryption_service.decrypt(encrypted)

assert decrypted == plaintext
assert encrypted != plaintext
assert len(encrypted) > len(plaintext)
Git Commit:
bashgit add backend/app/services/encryption_service.py
git add backend/requirements.txt
git commit -m "feat: add field-level encryption service

- Implement AES-256 encryption using cryptography.fernet
- Support encryption/decryption of sensitive fields
- Load encryption key from environment/Secret Manager
- Add error handling for decryption failures
- Include verification tests"
git push origin main
Wait for Feedback:
Test Encryption Service:

1. Set ENCRYPTION_KEY in .env file
2. Run test:
   cd backend
   python -c "from app.services.encryption_service import encryption_service; print(encryption_service.verify_encryption())"

Expected Output: True

If errors occur, describe the error message.

Step 1.3: Security Headers Middleware
File: backend/app/middleware/security_headers.py
Purpose: Add security headers to all HTTP responses
Headers to Add:
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.bonidoc.com https://accounts.google.com; font-src 'self'; frame-ancestors 'none'
Middleware Implementation:
Structure:

FastAPI middleware that runs on every request
Adds headers to response
Applies to all routes (no exceptions)

Integration:
File: backend/app/main.py
Add middleware registration:
pythonfrom app.middleware.security_headers import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
Testing:
bash# Test headers are present
curl -I https://api.bonidoc.com/health

# Should include all security headers in response
Git Commit:
bashgit add backend/app/middleware/security_headers.py
git add backend/app/main.py
git commit -m "feat: add security headers middleware

- Add HSTS with 1-year max-age
- Add X-Frame-Options: DENY (clickjacking protection)
- Add CSP to prevent XSS attacks
- Add X-Content-Type-Options: nosniff
- Add Referrer-Policy for privacy
- Apply to all HTTP responses automatically"
git push origin main
Wait for Feedback:
Verify Security Headers:

1. Deploy to staging
2. Test endpoint: curl -I https://<your-backend-url>/health
3. Check response headers include all security headers

Paste the headers output here.

Day 2: Session Management & Token Security
Step 2.1: Session Service Implementation
File: backend/app/services/session_service.py
Purpose: Manage user sessions securely
Methods:

create_session(user_id, ip_address, user_agent) - Create new session, return refresh_token
verify_session(refresh_token) - Validate session, return user_id
revoke_session(session_id, reason) - Invalidate session
revoke_all_user_sessions(user_id, reason) - Logout all devices
get_user_sessions(user_id) - List active sessions
cleanup_expired_sessions() - Background cleanup job
refresh_session_activity(session_id) - Update last_activity_at
check_suspicious_session(user_id, ip_address) - Detect anomalies

Session Lifecycle:
Login:
1. Verify credentials (Google OAuth)
2. Create session record in database
3. Generate refresh_token (cryptographically random, 64 chars)
4. Hash refresh_token before storing
5. Return refresh_token to client (httpOnly cookie)
6. Set expires_at = NOW() + 7 days

Request:
1. Extract refresh_token from cookie
2. Hash token
3. Lookup session by token hash
4. Verify not expired, not revoked
5. Update last_activity_at
6. Return user_id

Logout:
1. Extract refresh_token from cookie
2. Find session
3. Set is_revoked = true, revoked_reason = 'logout'
4. Clear cookie

Expiry:
- Background job runs hourly
- Delete sessions where expires_at < NOW()
- Delete sessions where last_activity_at < NOW() - 7 days
Security Features:

Store hash of token (not plaintext)
Track IP and user agent (detect session hijacking)
Limit 5 concurrent sessions per user
Auto-revoke on password change
Suspicious activity detection (new country, multiple IPs)

Git Commit:
bashgit add backend/app/services/session_service.py
git commit -m "feat: implement session management service

- Create/verify/revoke sessions
- Track active sessions per user
- Limit concurrent sessions to 5
- Store token hashes (not plaintext)
- Detect suspicious session activity
- Background cleanup of expired sessions"
git push origin main
Wait for Feedback:
Test Session Creation:

Run test script:
python -c "
from app.services.session_service import session_service
session_id = session_service.create_session(
    user_id='test-uuid',
    ip_address='192.168.1.1',
    user_agent='Mozilla/5.0'
)
print(f'Session created: {session_id}')
"

Expected: Session ID returned, no errors.
Reply with output.

Step 2.2: Update Authentication Service
File: backend/app/services/auth_service.py
Changes:
Replace JWT-Only Authentication with Session-Based:
Current Flow:
Login → Issue JWT (24h expiry) → Store in localStorage
New Flow:
Login → Create session → Issue access_token (15min) + refresh_token (7d)
→ Store both in httpOnly cookies
Token Structure:
Access Token (JWT):

Expiry: 15 minutes
Claims: user_id, email, role, issued_at, expires_at
Stored in httpOnly cookie
Used for API requests

Refresh Token:

Expiry: 7 days
Random string (not JWT)
Stored in user_sessions table (hashed)
Stored in httpOnly cookie
Used to obtain new access token

Methods to Update:

login() - Create session, return both tokens
verify_token() - Verify access token (JWT)
refresh_access_token() - Use refresh token to get new access token
logout() - Revoke session, clear cookies
logout_all_devices() - Revoke all sessions

Cookie Configuration:
Set-Cookie: access_token=<JWT>; 
    HttpOnly; 
    Secure; 
    SameSite=Strict; 
    Max-Age=900; 
    Path=/

Set-Cookie: refresh_token=<random>; 
    HttpOnly; 
    Secure; 
    SameSite=Strict; 
    Max-Age=604800; 
    Path=/auth/refresh
Git Commit:
bashgit add backend/app/services/auth_service.py
git add backend/app/api/auth.py
git commit -m "feat: replace JWT-only auth with session-based tokens

- Reduce access token expiry to 15 minutes
- Add refresh token with 7-day expiry
- Store tokens in httpOnly cookies (not localStorage)
- Integrate with session service
- Add refresh endpoint for new access tokens
- Add logout all devices functionality"
git push origin main
Wait for Feedback:
Test Login Flow:

1. Call login endpoint:
   curl -X POST https://<backend>/auth/google/login \
   -H "Content-Type: application/json" \
   -d '{"code": "<google_oauth_code>"}'

2. Check response includes:
   - Set-Cookie headers for access_token and refresh_token
   - Both cookies have HttpOnly, Secure, SameSite flags

3. Verify session created in database:
   SELECT * FROM user_sessions ORDER BY created_at DESC LIMIT 1;

Reply with: Success or error details.

Step 2.3: Update Frontend Token Storage
Files to Update:

frontend/src/lib/auth.ts
frontend/src/hooks/use-auth.ts
frontend/src/services/*.service.ts

Changes:
Remove localStorage Usage:
Current (Insecure):
typescript// REMOVE THIS
localStorage.setItem('access_token', token);
const token = localStorage.getItem('access_token');
New (Secure):
typescript// Tokens automatically included in cookies
// No need to manually manage tokens in frontend
API Client Configuration:
Update axios/fetch to include credentials:
typescript// All API calls must include credentials: 'include'
fetch(url, {
    credentials: 'include',  // Automatically send cookies
    headers: { ... }
})
Authentication Hook Update:
useAuth Hook:

Remove token management from state
Tokens handled by cookies automatically
Call /auth/refresh if 401 received
Redirect to login if refresh fails

Logout Implementation:
typescriptconst logout = async () => {
    await fetch('/auth/logout', { 
        method: 'POST',
        credentials: 'include' 
    });
    // Cookies cleared by backend
    router.push('/login');
}
Git Commit:
bashgit add frontend/src/lib/auth.ts
git add frontend/src/hooks/use-auth.ts
git add frontend/src/services/
git commit -m "refactor: move token storage from localStorage to httpOnly cookies

- Remove all localStorage.setItem/getItem for tokens
- Use credentials: 'include' in all API calls
- Tokens automatically sent in cookies
- Update logout to call backend endpoint
- Remove manual token management from frontend"
git push origin main
Wait for Feedback:
Test Frontend Authentication:

1. Clear browser localStorage
2. Login via Google OAuth
3. Check browser DevTools:
   - Application → Cookies → Should see access_token and refresh_token
   - Both should have HttpOnly flag
4. Navigate to protected page
5. Check Network tab: cookies automatically sent with requests

Reply with: Success or describe issues.

Day 3: Rate Limiting & Input Validation
Step 3.1: Rate Limiting Service
File: backend/app/services/rate_limit_service.py
Purpose: Prevent abuse and brute force attacks
Implementation:
Storage: In-memory dictionary with TTL (MVP) or Redis (production)
Rate Limit Tiers:
Tier 1 - Authentication:
- POST /auth/login: 5 per 15 minutes per IP
- POST /auth/refresh: 10 per hour per user

Tier 2 - Write Operations:
- POST /documents/*: 100 per hour per user
- POST /categories: 20 per hour per user
- DELETE /documents/*: 50 per hour per user

Tier 3 - Read Operations:
- GET /documents: 1000 per hour per user
- GET /categories: 1000 per hour per user
Methods:

check_rate_limit(key, limit, window) - Returns (allowed: bool, remaining: int, retry_after: int)
increment_counter(key, window)
get_rate_limit_info(key, limit, window) - For headers
reset_limit(key) - Admin override

Response Headers:
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1697123456
Retry-After: 3600  (if limit exceeded)
Error Response (429):
json{
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Try again in 59 minutes.",
    "retry_after": 3540
}
Git Commit:
bashgit add backend/app/services/rate_limit_service.py
git add backend/app/middleware/rate_limit.py
git commit -m "feat: implement rate limiting service

- Three-tier rate limits (auth/write/read)
- In-memory storage with TTL
- Return rate limit headers
- Return 429 with retry-after on exceed
- Configurable limits per endpoint"
git push origin main

Step 3.2: File Upload Validation Service
File: backend/app/services/file_validation_service.py
Purpose: Validate uploaded files before processing
Validation Pipeline:
1. Size Check
   - Max 100 MB per file
   - Max 500 MB per batch
   - Reject if exceeded

2. File Type Validation
   - Allowed: PDF, JPEG, PNG, TIFF, BMP, DOCX
   - Check Content-Type header
   - Verify extension matches MIME type

3. Magic Bytes Verification
   - Read first 16 bytes
   - Verify matches declared type
   - PDF: %PDF (25 50 44 46)
   - JPEG: FF D8 FF
   - PNG: 89 50 4E 47
   - DOCX: 50 4B 03 04 (ZIP)

4. Filename Sanitization
   - Remove: \ / : * ? " < > | null bytes
   - Remove path traversal: ../ ..\
   - Max 255 characters
   - Convert to ASCII-safe characters

5. Content Validation
   - Attempt to open PDF with PyMuPDF
   - Attempt to open image with Pillow
   - Reject if corrupted
Methods:

validate_file_upload(file, filename, mime_type) - Main validation
check_file_size(file, max_size)
verify_mime_type(file, declared_mime)
check_magic_bytes(file_bytes)
sanitize_filename(filename)
is_allowed_file_type(mime_type)
validate_pdf_integrity(file_bytes)
validate_image_integrity(file_bytes)

Rejection Criteria:

Executable files (.exe, .sh, .bat)
Script files (.js, .py, .php)
Archive files (.zip, .rar) - must extract first
HTML files (XSS vector)
SVG files (can contain scripts)
Mismatched MIME and extension
Corrupted files

Error Responses:
json{
    "error": "invalid_file_type",
    "message": "Only PDF, JPEG, PNG, TIFF, and DOCX files are allowed",
    "filename": "document.zip"
}

{
    "error": "file_too_large",
    "message": "File exceeds maximum size of 100 MB",
    "filename": "large.pdf",
    "size_mb": 150
}
Git Commit:
bashgit add backend/app/services/file_validation_service.py
git commit -m "feat: implement file upload validation service

- Validate file size (max 100 MB)
- Validate file type (whitelist only)
- Verify magic bytes (prevent disguised files)
- Sanitize filenames (remove special chars)
- Validate file integrity (can be opened)
- Reject executables, scripts, archives
- Comprehensive error messages"
git push origin main
Wait for Feedback:
Test File Validation:

1. Test valid file:
   python test_file_validation.py --file=test.pdf

2. Test invalid file:
   python test_file_validation.py --file=test.exe

3. Test oversized file:
   python test_file_validation.py --file=large.pdf

Expected: Valid files pass, invalid files rejected with clear errors.
Reply with test results.

Day 4: Input Sanitization & Audit Logging
Step 4.1: Input Validation with Pydantic
Files: Update all backend/app/api/*.py files
Pydantic Models to Create/Update:
File: backend/app/models/requests.py
Models:
CategoryCreateRequest:
- name: str (1-100 chars, alphanumeric + spaces)
- description: Optional[str] (max 500 chars)
- color_hex: str (valid hex color)
- icon_name: str (allowed icon list)

DocumentUploadRequest:
- title: str (1-255 chars)
- category_ids: List[UUID] (1-10 categories)
- primary_category_id: UUID
- keywords: List[str] (max 50 items, each 1-50 chars)

UserSettingsUpdate:
- setting_key: str (allowed keys only)
- setting_value: str (max 1000 chars)
- validated against type

SearchRequest:
- query: str (1-500 chars, no SQL keywords)
- filters: Optional[Dict]
- limit: int (1-100)
- offset: int (0+)
Validation Rules:

All UUIDs validated automatically
String lengths enforced
Regex patterns for special fields (email, hex color)
Enum validation (file types, statuses)
Custom validators for complex logic

Error Response Format:
json{
    "error": "validation_error",
    "message": "Invalid input",
    "details": [
        {
            "field": "category_name",
            "error": "String should have at most 100 characters"
        }
    ]
}
Git Commit:
bashgit add backend/app/models/requests.py
git add backend/app/api/
git commit -m "feat: add comprehensive input validation with Pydantic

- Create request models for all endpoints
- Validate string lengths, types, formats
- Validate UUIDs, emails, hex colors
- Return structured validation errors
- Prevent SQL injection via validation"
git push origin main

Step 4.2: Security Audit Logging Enhancement
File: backend/app/services/audit_service.py
Purpose: Comprehensive audit logging for security events
Enhanced Logging:
Events to Log:
Authentication:
- login_success (user_id, ip, user_agent)
- login_failed (email, ip, reason)
- logout (user_id, ip)
- session_revoked (user_id, session_id, reason)
- token_refresh (user_id, ip)

Authorization:
- access_denied (user_id, resource, action)
- suspicious_activity (user_id, pattern, details)

Data Operations:
- document_uploaded (user_id, document_id, filename, size)
- document_viewed (user_id, document_id)
- document_deleted (user_id, document_id)
- category_created (user_id, category_id)
- settings_changed (user_id, setting_key)

Security Events:
- rate_limit_exceeded (user_id/ip, endpoint)
- invalid_file_upload (user_id, filename, reason)
- malware_detected (user_id, filename)
- sql_injection_attempt (user_id, payload)
Enhanced audit_logs Fields:
Use Existing Columns:

security_level: 'low', 'medium', 'high', 'critical'
security_flags: JSON with indicators

Security Flags:
json{
    "suspicious": true,
    "rate_limited": false,
    "automated": false,
    "geolocation_change": true,
    "new_device": true
}
Sanitization Rules:

Never log passwords, tokens, keys
Truncate long values (max 1000 chars)
Mask email: user@example.com → u***@example.com
Mask IP: 192.168.1.100 → 192.168.1.***
Remove stack traces from error_message

Methods:

log_auth_event(event_type, user_id, success, details)
log_data_event(event_type, user_id, resource_type, resource_id, changes)
log_security_event(event_type, user_id, severity, details)
log_api_call(endpoint, user_id, status_code, duration_ms)
sanitize_log_data(data) - Remove sensitive info

Git Commit:
bashgit add backend/app/services/audit_service.py
git add backend/app/api/  # Update all endpoints to call audit_service
git commit -m "feat: enhance security audit logging

- Log all authentication events
- Log authorization failures
- Log data operations (create/read/delete)
- Log security events (rate limits, invalid uploads)
- Add security levels and flags
- Sanitize sensitive data before logging
- Never log passwords, tokens, or keys"
git push origin main

Day 5: Security Monitoring & Testing
Step 5.1: Security Monitoring Service
File: backend/app/services/security_monitoring_service.py
Purpose: Detect anomalies and alert on security events
Anomaly Detection:
Detect:
- Login from new country (compare to last_login_country)
- Unusual access hours (3 AM when usually 9-5)
- Spike in API calls (10x normal)
- Multiple failed logins (5+ in 15 min)
- Rapid document downloads (100+ in 1 hour)
- Session from multiple IPs simultaneously

Actions:
- Low: Log + monitor
- Medium: Log + require CAPTCHA
- High: Log + lock account + notify user
- Critical: Log + lock account + notify admin
Alerting:
Alert Channels:

Email (immediate for critical)
Slack webhook (all security events)
Database (security_alerts table for dashboard)

Alert Types:
Immediate Alerts:
- 5+ failed login attempts in 1 minute
- Malware upload detected
- SQL injection attempt
- Account takeover suspected
- Mass document deletion

Daily Digest:
- Total failed logins
- Top rate-limited IPs
- Unusual access patterns
- New user registrations

Weekly Report:
- Security metrics summary
- Top security events
- Recommendations
Methods:

detect_suspicious_login(user_id, ip_address, user_agent)
detect_anomalous_api_usage(user_id, endpoint, count)
alert_admin(severity, event_type, details)
generate_security_report(date_range)

Git Commit:
bashgit add backend/app/services/security_monitoring_service.py
git commit -m "feat: implement security monitoring and alerting

- Detect login anomalies (new country, unusual hours)
- Detect API usage spikes
- Detect failed authentication patterns
- Alert on critical security events
- Daily and weekly security reports
- Slack/email notifications"
git push origin main

Step 5.2: Security Testing Suite
File: backend/tests/test_security.py
Test Categories:
Authentication Tests:
- test_login_rate_limiting()
- test_session_expiry()
- test_token_validation()
- test_logout_all_devices()

Authorization Tests:
- test_unauthorized_document_access()
- test_cross_user_data_access()
- test_admin_only_endpoints()

Input Validation Tests:
- test_sql_injection_prevention()
- test_xss_prevention()
- test_file_upload_validation()
- test_filename_sanitization()

Rate Limiting Tests:
- test_auth_rate_limit()
- test_api_rate_limit()
- test_rate_limit_headers()

Encryption Tests:
- test_token_encryption()
- test_decryption_with_wrong_key()
- test_encryption_roundtrip()

Audit Logging Tests:
- test_login_logged()
- test_sensitive_data_not_logged()
- test_security_event_logged()
Run Tests:
bashcd backend
pytest tests/test_security.py -v
Git Commit:
bashgit add backend/tests/test_security.py
git commit -m "test: add comprehensive security test suite

- Test authentication flows
- Test authorization enforcement
- Test SQL injection prevention
- Test XSS prevention
- Test file upload validation
- Test rate limiting
- Test audit logging
- Test encryption/decryption"
git push origin main
Wait for Feedback:
Run Security Tests:

1. Execute test suite:
   cd backend
   pytest tests/test_security.py -v --tb=short

2. All tests should pass

Reply with:
- Number of tests passed
- Any failures or errors

Phase 1 Summary & Verification
At End of Week 1:
Checklist:
Database:
☐ Unused tables deleted (6 tables)
☐ category_keywords table created
☐ user_sessions table created
☐ Security columns added to users
☐ Audit log enhancements complete

Backend Services:
☐ Encryption service implemented
☐ Session service implemented
☐ Rate limiting service implemented
☐ File validation service implemented
☐ Audit service enhanced
☐ Security monitoring service implemented

Middleware:
☐ Security headers added
☐ Rate limiting middleware active
☐ HTTPS enforced

Authentication:
☐ Session-based auth implemented
☐ Tokens in httpOnly cookies
☐ 15-minute access token expiry
☐ 7-day refresh token expiry
☐ Logout all devices working

Frontend:
☐ localStorage removed for tokens
☐ Credentials: 'include' on all API calls
☐ Login/logout flows updated

Testing:
☐ All security tests passing
☐ Manual testing completed
☐ No critical vulnerabilities
Final Verification:
bash# Database schema
psql $DATABASE_URL -c "\dt" | grep -E "category_keywords|user_sessions"

# Security headers
curl -I https://<backend-url>/health | grep -E "Strict-Transport|X-Frame"

# Rate limiting
for i in {1..6}; do curl -X POST https://<backend-url>/auth/login; done
# Should return 429 on 6th request

# Token storage
# Login via frontend, check DevTools → Application → Cookies
# Should see httpOnly cookies, not localStorage entries
Deploy to Production:
bashgit tag v1.0.0-security
git push origin v1.0.0-security
# GitHub Actions deploys automatically

PHASE 2: Document Processing & Classification (Week 2)
Objective: Implement OCR, text extraction, keyword extraction, and classification
Duration: 5 days

Day 6: OCR & Text Extraction
Step 6.1: Add OCR Dependencies
File: backend/requirements.txt
Remove:
PyPDF2==3.0.1
Add:
PyMuPDF==1.23.8
pytesseract==0.3.10
Pillow==10.1.0
pdf2image==1.16.3
opencv-python-headless==4.8.1.78
numpy==1.24.3
Dockerfile Updates:
File: backend/Dockerfile
Add system packages before Python dependencies:
dockerfile# Install OCR and image processing dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-rus \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
Cloud Run Configuration:
File: .github/workflows/deploy.yml
Update memory allocation:
yaml--memory=1Gi  # Increased from 512Mi for OCR processing
Git Commit:
bashgit add backend/requirements.txt
git add backend/Dockerfile
git add .github/workflows/deploy.yml
git commit -m "feat: add OCR dependencies and system packages

- Add PyMuPDF for PDF text extraction
- Add Tesseract OCR for images
- Add Pillow, OpenCV for image preprocessing
- Add pdf2image for PDF to image conversion
- Install Tesseract system packages (eng, deu, rus)
- Increase Cloud Run memory to 1Gi for OCR"
git push origin main
Wait for Feedback:
Verify Docker Build:

1. Build locally:
   cd backend
   docker build -t bonidoc-backend .

2. Verify Tesseract installed:
   docker run bonidoc-backend tesseract --version

Expected Output: tesseract 5.x.x

Reply with: Success or build errors.

Step 6.2: OCR Service Implementation
File: backend/app/services/ocr_service.py
Purpose: Extract text from images and scanned PDFs
Methods:
Core Methods:

extract_text_from_image(image_bytes, language_code) - Main entry point
preprocess_image(image) - Enhance quality before OCR
run_tesseract(image, language_code) - Execute OCR
validate_extracted_text(text) - Check if output is meaningful
get_tesseract_language_code(language_code) - Map to Tesseract format

Image Preprocessing Pipeline:
1. Load image (Pillow)
2. Convert to grayscale
3. Apply Gaussian blur (reduce noise)
4. Otsu's binarization (threshold to black/white)
5. Deskew (correct rotation)
6. Resize if too large (max 3000px width)
7. Return preprocessed image
OCR Configuration:
Tesseract PSM (Page Segmentation Mode):
- PSM 3: Fully automatic (default)
- PSM 6: Uniform block of text
- PSM 11: Sparse text (fallback)

Language Codes:
- en → eng
- de → deu
- ru → rus
- Multi: eng+deu+rus
Quality Validation:
Text is valid if:
- Length > 50 characters
- Contains alphanumeric characters
- Word count > 10
- Average word length 3-15 characters
- Tesseract confidence > 60%
Error Handling:
If OCR fails:
1. Log error details
2. Try fallback PSM mode
3. If still fails, return error:
   "Unable to extract text. Image may be too blurry or rotated."
Git Commit:
bashgit add backend/app/services/ocr_service.py
git commit -m "feat: implement OCR service with Tesseract

- Extract text from images (JPEG, PNG, TIFF)
- Preprocess images (grayscale, denoise, deskew)
- Support multiple languages (en, de, ru)
- Validate OCR output quality
- Fallback modes for difficult images
- Error handling with user-friendly messages"
git push origin main

Step 6.3: Update Document Analysis Service
File: backend/app/services/document_analysis_service.py
Major Refactor: Add OCR support and improve text extraction
Text Extraction Logic:
IF file_type == PDF:
    # Try native text extraction first
    text = extract_with_pymupdf(pdf_bytes)
    
    IF len(text.strip()) < 100:
        # Scanned PDF - no embedded text
        # Convert to images and OCR
        images = convert_pdf_to_images(pdf_bytes)
        text_parts = []
        
        FOR page_num, image IN enumerate(images):
            page_text = ocr_service.extract_text_from_image(
                image, 
                language_code
            )
            IF page_text is valid:
                text_parts.append(f"[Page {page_num + 1}]\n{page_text}")
        
        text = "\n\n".join(text_parts)

ELIF file_type IN [JPEG, PNG, TIFF, BMP]:
    # Image file - OCR only option
    text = ocr_service.extract_text_from_image(
        file_bytes,
        language_code
    )

ELIF file_type == DOCX:
    # Extract with python-docx
    text = extract_with_python_docx(file_bytes)

ELSE:
    RAISE "Unsupported file type"
Updated Response Structure:
json{
    "extracted_text": "...",
    "full_text_length": 5432,
    "keywords": [...],
    "suggested_category_id": "uuid",
    "confidence": 75.5,
    "detected_language": "de",
    "processing_info": {
        "method": "ocr",  // or "native_text"
        "pages_processed": 3,
        "processing_time_ms": 2450,
        "ocr_confidence": 85.2
    }
}
Processing Time Targets:

PDF with text: 1-2 seconds
Scanned PDF (5 pages): 10-20 seconds
Image: 3-5 seconds

Git Commit:
bashgit add backend/app/services/document_analysis_service.py
git commit -m "feat: add OCR support to document analysis

- Try native text extraction first (fast)
- Fallback to OCR for scanned PDFs
- OCR images (JPEG, PNG, TIFF)
- Multi-page PDF OCR support
- Return processing method and time
- Handle all supported file types"
git push origin main
Wait for Feedback:
Test Document Analysis:

1. Test PDF with text:
   curl -X POST http://localhost:8000/api/v1/document-analysis/analyze \
   -F "file=@sample_typed.pdf"

2. Test scanned PDF:
   curl -X POST http://localhost:8000/api/v1/document-analysis/analyze \
   -F "file=@sample_scanned.pdf"

3. Test image:
   curl -X POST http://localhost:8000/api/v1/document-analysis/analyze \
   -F "file=@sample_image.jpg"

Expected:
- Text extracted successfully
- Keywords present
- Processing time reasonable

Reply with: Processing times and any errors.

Day 7: Keyword Extraction & Classification Database
Step 7.1: Simplify Keyword Extraction
File: backend/app/services/ml_keyword_service.py
Refactor: Remove complex TF-IDF, spelling correction, n-grams
New Simple Algorithm:
1. Text Preprocessing
   - Lowercase all text
   - Remove punctuation
   - Split into words

2. Stop Word Filtering
   - Load stop words from database (stop_words table)
   - Remove all stop words
   - Remove single characters
   - Remove numbers-only words

3. Frequency Counting
   - Count occurrence of each word
   - Require minimum 2 occurrences

4. Relevance Scoring
   - relevance = (frequency / total_words) * 100
   - Sort by relevance descending

5. Return Top N
   - Default: top 20 keywords
   - Each: {word, count, relevance}
Removed Logic:

❌ TF-IDF calculations (too complex for MVP)
❌ Spelling correction (unnecessary for typed documents)
❌ N-gram extraction (added complexity, little benefit)
❌ Learned scoring weights (replaced with simple learning)

Methods:

extract_keywords(text, language_code, max_keywords=20) - Main extraction
preprocess_text(text) - Clean and normalize
filter_stop_words(words, language_code) - Remove stop words
calculate_frequency(words) - Count occurrences
score_keywords(word_freq, total_words) - Calculate relevance

Git Commit:
bashgit add backend/app/services/ml_keyword_service.py
git commit -m "refactor: simplify keyword extraction algorithm

- Remove TF-IDF complexity
- Remove spelling correction
- Remove n-gram extraction
- Use simple frequency-based extraction
- Filter stop words from database
- Calculate relevance as (frequency / total) * 100
- Return top 20 keywords by relevance"
git push origin main

Step 7.2: Classification Database Schema
File: backend/alembic/versions/xxx_classification_schema.py
New Tables:
Table 1: document_classification_log
sqlCREATE TABLE document_classification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    suggested_category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    actual_category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    confidence_score FLOAT NOT NULL,
    matching_keywords JSONB,  -- ["keyword1", "keyword2"]
    all_scores JSONB,  -- {"cat-id-1": 0.85, "cat-id-2": 0.23}
    was_correct BOOLEAN NOT NULL,
    correction_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_classification_log_document ON document_classification_log(document_id);
CREATE INDEX idx_classification_log_suggested ON document_classification_log(suggested_category_id, was_correct);
CREATE INDEX idx_classification_log_created ON document_classification_log(created_at DESC);
Table 2: category_classification_metrics
sqlCREATE TABLE category_classification_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_assignments INT DEFAULT 0,
    correct_assignments INT DEFAULT 0,
    accuracy_rate FLOAT DEFAULT 0,
    avg_confidence FLOAT DEFAULT 0,
    keyword_suggestions JSONB,  -- Suggested keywords to add
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(category_id, date)
);

CREATE INDEX idx_metrics_category_date ON category_classification_metrics(category_id, date DESC);
Populate System Keywords:
Insert predefined keywords for 9 system categories × 3 languages (en/de/ru).
Example for Insurance:
sqlWITH insurance_category AS (
    SELECT id FROM categories 
    WHERE reference_key = 'category.insurance' 
    AND is_system = true
)
INSERT INTO category_keywords (
    category_id, keyword, language_code, weight, 
    is_system_default, match_count
)
SELECT 
    insurance_category.id,
    keyword,
    lang,
    weight,
    true,
    0
FROM insurance_category
CROSS JOIN LATERAL (VALUES
    ('insurance', 'en', 3.0),
    ('policy', 'en', 2.8),
    ('coverage', 'en', 2.5),
    ('premium', 'en', 2.5),
    ('claim', 'en', 2.3),
    ('deductible', 'en', 2.0),
    ('versicherung', 'de', 3.0),
    ('police', 'de', 2.8),
    ('deckung', 'de', 2.5),
    ('страхование', 'ru', 3.0),
    ('полис', 'ru', 2.8)
) AS keywords(keyword, lang, weight);
Repeat for all 9 categories (Insurance, Legal, Bank, Medical, Tax, Real Estate, Employment, Education, Other).
Expected Total: 150-200 system keywords
Git Commit:
bashgit add backend/alembic/versions/xxx_classification_schema.py
git commit -m "feat: add classification database schema

- Create document_classification_log table
- Create category_classification_metrics table
- Populate system keywords for 9 categories
- Add 150+ keywords in en/de/ru languages
- Add indexes for performance
- Ready for classification engine"
git push origin main
Wait for Feedback:
Run Migration:

cd backend
alembic upgrade head

Verify:
SELECT COUNT(*) FROM document_classification_log;  -- Should be 0
SELECT COUNT(*) FROM category_classification_metrics;  -- Should be 0
SELECT COUNT(*) FROM category_keywords WHERE is_system_default = true;  -- Should be ~150-200

Reply with: Row counts.

Day 8: Classification Engine
Step 8.1: Document Classifier Service
File: backend/app/services/document_classifier_service.py
Purpose: Core classification logic using keyword matching
Classification Algorithm:
INPUT: document_keywords, language_code, user_categories

FOR each category:
    1. Load category keywords from database
       WHERE category_id = cat.id 
       AND language_code = doc_language
    
    2. Calculate overlap score:
       matched_weight = SUM(keyword.weight) 
                       FOR keywords IN both doc AND category
       
       total_category_weight = SUM(keyword.weight) 
                              FOR all category keywords
       
       overlap_score = matched_weight / total_category_weight
       
    3. Store:
       scores[category_id] = overlap_score
       matching_keywords[category_id] = [matched keyword list]

4. Sort categories by score (descending)

5. Decision Logic:
   best_score = scores[0]
   second_score = scores[1] if exists else 0
   
   threshold = 0.6  (60% confidence)
   min_gap = 0.2     (20% difference)
   
   IF best_score >= threshold AND (best_score - second_score) >= min_gap:
       → Assign to best category
   ELSE:
       → Assign to "Other" category

6. RETURN:
   - suggested_category_id
   - confidence (0-1)
   - matching_keywords
   - all_scores (for transparency)
   - assigned_to_fallback (boolean)
Methods:

classify_document(doc_keywords, language_code, user_categories) - Main classifier
calculate_keyword_overlap(doc_keywords, category_keywords) - Scoring
get_other_category_id(user_id) - Fetch "Other" category
format_classification_result(...) - Structure response

Configuration:

Default threshold: 0.6
Default min_gap: 0.2
Stored in system_settings table

Git Commit:
bashgit add backend/app/services/document_classifier_service.py
git commit -m "feat: implement keyword-based document classifier

- Calculate overlap scores between document and category keywords
- Apply confidence threshold (60%) and gap requirement (20%)
- Assign to best category or fallback to Other
- Return matching keywords for transparency
- Return all scores for debugging
- Configurable thresholds via settings"
git push origin main

Step 8.2: Category Learning Service
File: backend/app/services/category_learning_service.py
Purpose: Learn from user corrections and improve classification
Methods:
record_classification():
INPUT: document_id, suggested_category_id, actual_category_id, 
       confidence, matching_keywords, all_scores

1. Calculate was_correct:
   was_correct = (suggested == actual)

2. Insert into document_classification_log:
   - All input parameters
   - was_correct flag
   - created_at timestamp

3. RETURN log entry ID
learn_from_assignment():
INPUT: document_id, category_id, doc_keywords, language_code

Called when user confirms suggested category (correct prediction).

FOR each keyword IN doc_keywords:
    1. Find keyword in category_keywords table
    
    2. IF exists:
       - Increase weight by 10% (max 5.0)
       - Increment match_count
       - Update last_matched_at
    
    3. IF not exists AND keyword_frequency > 2:
       - Insert with weight 0.5
       - Set match_count = 1
       - Set is_system_default = false

4. RETURN count of keywords updated
learn_from_correction():
INPUT: document_id, from_category_id, to_category_id, 
       doc_keywords, language_code

Called when user changes suggested category (wrong prediction).

1. FROM category (incorrect suggestion):
   FOR each keyword IN matching_keywords:
       - Decrease weight by 5% (min 0.1)
       - Don't remove (might be correct for other docs)

2. TO category (correct choice):
   FOR each keyword IN doc_keywords:
       - IF exists: increase weight by 10%
       - IF not exists: add with weight 0.5

3. Log correction:
   - Update classification_log
   - Set correction_timestamp = NOW()

4. RETURN keywords adjusted
calculate_daily_metrics():
Background job (runs daily at midnight).

FOR each category:
    1. Query classification_log for today:
       - COUNT(*) as total
       - SUM(CASE WHEN was_correct) as correct
    
    2. Calculate:
       - accuracy_rate = correct / total
       - avg_confidence = AVG(confidence_score)
    
    3. Identify keywords in misclassifications:
       - Find common keywords NOT in category_keywords
       - Suggest adding them
    
    4. INSERT/UPDATE category_classification_metrics:
       - date = today
       - All calculated metrics
Git Commit:
bashgit add backend/app/services/category_learning_service.py
git commit -m "feat: implement category learning service

- Record all classification decisions in log
- Learn from correct suggestions (increase weights)
- Learn from corrections (adjust weights both categories)
- Calculate daily accuracy metrics per category
- Suggest keywords for low-performing categories
- Keyword weights range from 0.1 to 5.0"
git push origin main

Day 9: Integration & Category Management
Step 9.1: Integrate Classification into Upload Flow
File: backend/app/services/batch_upload_service.py
Update analyze_batch() method:
After keyword extraction:

# NEW: Classify document
classification = document_classifier_service.classify_document(
    doc_keywords=extracted_keywords,
    language_code=detected_language,
    user_categories=user_categories
)

# Add to response
analysis_result = {
    ...existing fields...,
    'suggested_category_id': classification['category_id'],
    'confidence': classification['confidence'] * 100,  # As percentage
    'classification_reasoning': {
        'matching_keywords': classification['matching_keywords'],
        'assigned_to_fallback': classification['assigned_to_fallback'],
        'category_scores': classification['all_scores']
    }
}
Update confirm_upload() method:
After document saved to database:

# NEW: Record classification
log_id = category_learning_service.record_classification(
    document_id=document.id,
    suggested_category_id=analysis['suggested_category_id'],
    actual_category_id=primary_category_id,  # User's choice
    confidence=analysis['confidence'] / 100,
    matching_keywords=analysis['classification_reasoning']['matching_keywords'],
    all_scores=analysis['classification_reasoning']['category_scores']
)

# NEW: Learn from user's choice
IF actual_category_id == suggested_category_id:
    # Correct suggestion
    category_learning_service.learn_from_assignment(
        document_id=document.id,
        category_id=actual_category_id,
        doc_keywords=confirmed_keywords,
        language_code=detected_language
    )
ELSE:
    # User corrected
    category_learning_service.learn_from_correction(
        document_id=document.id,
        from_category_id=suggested_category_id,
        to_category_id=actual_category_id,
        doc_keywords=confirmed_keywords,
        language_code=detected_language
    )
Git Commit:
bashgit add backend/app/services/batch_upload_service.py
git commit -m "feat: integrate classification into upload flow

- Classify documents after keyword extraction
- Return suggested category with confidence
- Return classification reasoning (matching keywords, scores)
- Record classification decision in log
- Learn from user confirmation or correction
- Update keyword weights based on feedback"
git push origin main

Step 9.2: Category Keyword Management Service
File: backend/app/services/category_keyword_service.py
Purpose: CRUD operations for category keywords
Methods:
add_keywords_to_category():
INPUT: category_id, keywords, language_code

FOR each keyword:
    1. Validate keyword (length, characters)
    2. Check if stop word (reject if yes)
    3. INSERT or UPDATE category_keywords:
       - Initial weight: 1.0 (user-added)
       - is_system_default: false
       - match_count: 0

RETURN count added
get_category_keywords():
INPUT: category_id, language_code

SELECT keyword, weight, match_count, is_system_default
FROM category_keywords
WHERE category_id = ? AND language_code = ?
ORDER BY weight DESC, match_count DESC

RETURN list of keywords
suggest_keywords_from_text():
INPUT: text (category name + description), language_code

1. Extract keywords using ml_keyword_service
2. Filter:
   - Not already in category
   - Not stop words
   - Length 3-50 characters
3. Return top 10 suggestions
remove_keyword():
INPUT: category_id, keyword, language_code

IF is_system_default:
    # Don't delete, just set weight to 0
    UPDATE category_keywords
    SET weight = 0
ELSE:
    # User-added, safe to delete
    DELETE FROM category_keywords
    WHERE ...
get_keyword_effectiveness():
INPUT: category_id, language_code

SELECT 
    ck.keyword,
    ck.match_count,
    COUNT(dcl.*) as total_uses,
    SUM(CASE WHEN dcl.was_correct THEN 1 ELSE 0 END) as correct_uses,
    (correct_uses::float / total_uses) as effectiveness
FROM category_keywords ck
LEFT JOIN document_classification_log dcl ON 
    ck.keyword = ANY(dcl.matching_keywords::text[])
    AND dcl.actual_category_id = ck.category_id
WHERE ck.category_id = ?
GROUP BY ck.keyword, ck.match_count
ORDER BY effectiveness DESC

RETURN keyword statistics
Git Commit:
bashgit add backend/app/services/category_keyword_service.py
git commit -m "feat: implement category keyword management service

- Add keywords to categories
- Get keywords with weights
- Suggest keywords from category name/description
- Remove keywords (soft delete for system, hard delete for user)
- Calculate keyword effectiveness from classification logs
- Validate keywords against stop words"
git push origin main

Step 9.3: Category Management Enhancements
File: backend/app/services/category_service.py
Update create_category() method:
After category created:

# NEW: Auto-suggest keywords
suggested_keywords = category_keyword_service.suggest_keywords_from_text(
    text=f"{category_name} {category_description}",
    language_code=language_code
)

# NEW: Optionally auto-add keywords
IF auto_add_keywords:
    category_keyword_service.add_keywords_to_category(
        category_id=category.id,
        keywords=[kw['word'] for kw in suggested_keywords],
        language_code=language_code
    )

RETURN {
    'category': category,
    'suggested_keywords': suggested_keywords
}
Update delete_category() method:
Before deletion:

# NEW: Check if protected
IF category.is_protected OR category.reference_key == 'category.other':
    RAISE "Cannot delete protected category"

# NEW: Move all documents to "Other"
other_category = get_other_category(user_id)

documents = get_category_documents(category.id)

FOR document IN documents:
    # Update primary category
    UPDATE document_categories
    SET category_id = other_category.id
    WHERE document_id = document.id
    AND category_id = category.id
    AND is_primary = true

# Then proceed with delete
DELETE FROM categories WHERE id = category.id
API Endpoints to Add:
File: backend/app/api/categories.py
POST /api/v1/categories/{category_id}/keywords
  → Add keywords to category

GET /api/v1/categories/{category_id}/keywords
  → Get category keywords

DELETE /api/v1/categories/{category_id}/keywords/{keyword}
  → Remove keyword from category

GET /api/v1/categories/{category_id}/metrics
  → Get classification metrics

GET /api/v1/categories/{category_id}/suggestions
  → Get keyword suggestions
Git Commit:
bashgit add backend/app/services/category_service.py
git add backend/app/api/categories.py
git commit -m "feat: enhance category management with keywords

- Auto-suggest keywords when creating category
- Prevent deletion of protected categories
- Move documents to Other when category deleted
- Add keyword management API endpoints
- Add classification metrics endpoint
- Add keyword suggestions endpoint"
git push origin main

Day 10: Frontend Classification UI
Step 10.1: Update Upload Page
File: frontend/src/app/documents/upload/page.tsx
Changes:
1. Auto-select category from classification:
typescriptWhen analysis results received:

const states: FileUploadState[] = result.results.map((r: FileAnalysis) => {
  const suggestedCat = r.analysis.suggested_category_id;
  const confidence = r.analysis.confidence;
  
  // Auto-select if confidence >= 60%
  const autoSelected = (confidence >= 60 && suggestedCat) 
    ? suggestedCat 
    : categories[0]?.id || null;  // Fallback to first category
  
  return {
    ...r,
    selected_categories: autoSelected ? [autoSelected] : [],
    primary_category: autoSelected,
    confirmed_keywords: r.analysis.keywords.slice(0, 10).map(k => k.word),
    custom_filename: r.standardized_filename,
    filename_error: null
  };
});
2. Show classification reasoning:
typescriptAdd UI section:

{state.analysis.classification_reasoning && (
  <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm">
    <div className="flex items-center justify-between mb-2">
      <p className="font-medium text-blue-900 dark:text-blue-300">
        Why this category?
      </p>
      <Badge 
        variant={
          state.analysis.confidence >= 80 ? "success" : 
          state.analysis.confidence >= 60 ? "warning" : 
          "error"
        }
      >
        {state.analysis.confidence}% confidence
      </Badge>
    </div>
    
    <p className="text-xs text-blue-800 dark:text-blue-400">
      Matched keywords: {
        state.analysis.classification_reasoning.matching_keywords.join(', ')
      }
    </p>
    
    {state.analysis.classification_reasoning.assigned_to_fallback && (
      <p className="text-xs text-orange-600 dark:text-orange-400 mt-2">
        ⚠️ Low confidence - please review category assignment
      </p>
    )}
    
    <details className="mt-2">
      <summary className="cursor-pointer text-xs text-blue-600 dark:text-blue-400">
        View all scores
      </summary>
      <div className="mt-2 space-y-1">
        {Object.entries(state.analysis.classification_reasoning.category_scores).map(([catName, score]) => (
          <div key={catName} className="flex justify-between text-xs">
            <span>{catName}</span>
            <span>{score}%</span>
          </div>
        ))}
      </div>
    </details>
  </div>
)}
3. Update filename when primary category changes:
typescriptconst setPrimaryCategory = (fileIndex: number, categoryId: string) => {
  const category = categories.find(c => c.id === categoryId);
  const currentState = uploadStates[fileIndex];
  
  updateFileState(fileIndex, {
    primary_category: categoryId
  });
  
  // Regenerate filename with new category code
  if (category?.category_code) {
    const newFilename = generateFilename(
      currentState.file.name,
      category.category_code
    );
    updateFileState(fileIndex, {
      custom_filename: newFilename
    });
  }
};
Git Commit:
bashgit add frontend/src/app/documents/upload/page.tsx
git commit -m "feat: add classification UI to upload page

- Auto-select category if confidence >= 60%
- Show classification confidence badge
- Display matching keywords that led to suggestion
- Show warning for low confidence
- Expandable view of all category scores
- Update filename when primary category changes
- Visual indicators (green/yellow/red) for confidence levels"
git push origin main

Step 10.2: Category Keywords Management UI
File: frontend/src/components/category-keywords-dialog.tsx
Purpose: Modal for managing keywords when creating/editing categories
Structure:
typescriptComponent: CategoryKeywordsDialog

Props:
- category: Category (existing category or null for new)
- open: boolean
- onClose: () => void

State:
- suggestedKeywords: string[] (from API)
- selectedKeywords: {keyword: string, weight: number}[]
- customKeyword: string (input field)

Sections:

1. Suggested Keywords (if creating new category):
   - Extract from category name + description
   - Show as clickable badges
   - Click to add to selected

2. Selected Keywords:
   - Display with weights
   - Show match count (for existing categories)
   - Remove button
   - Adjust weight slider (optional)

3. Add Custom Keyword:
   - Text input
   - Validation (length, no special chars)
   - Add button

4. Keyword Effectiveness (for existing categories):
   - Show statistics from classification logs
   - Effectiveness percentage
   - Suggest removing low-performing keywords
Git Commit:
bashgit add frontend/src/components/category-keywords-dialog.tsx
git commit -m "feat: add category keywords management dialog

- Show suggested keywords from name/description
- Add/remove keywords
- Display keyword weights and match counts
- Show keyword effectiveness metrics
- Input validation for custom keywords
- Visual indicators for high/low performing keywords"
git push origin main

Phase 2 Summary & Testing
At End of Week 2:
Checklist:
OCR & Text Extraction:
☐ Tesseract installed and working
☐ PDF text extraction (PyMuPDF)
☐ Image OCR (JPEG, PNG, TIFF)
☐ Image preprocessing (deskew, denoise)
☐ Multi-page PDF OCR
☐ Processing time acceptable (<20s for 5-page PDF)

Keyword Extraction:
☐ Simplified algorithm implemented
☐ Stop words filtered
☐ Frequency-based extraction
☐ Returns 10-20 keywords per document

Classification:
☐ Keyword overlap scoring working
☐ Confidence threshold (60%) applied
☐ Gap requirement (20%) enforced
☐ Fallback to "Other" for low confidence
☐ System keywords populated (150+ keywords)

Learning:
☐ Classification logged to database
☐ Correct suggestions reinforce keywords
☐ Corrections adjust weights both directions
☐ Daily metrics calculation scheduled

Category Management:
☐ Keywords suggested on create
☐ Keywords manageable via UI
☐ Protected categories cannot be deleted
☐ Documents moved to Other on category delete

Frontend:
☐ Auto-select category based on classification
☐ Show confidence and reasoning
☐ Update filename on category change
☐ Keywords management dialog
Testing:
bash# Test OCR
1. Upload typed PDF → Should extract text without OCR (fast)
2. Upload scanned PDF → Should OCR (slower but works)
3. Upload image → Should OCR

# Test Classification
1. Upload insurance document → Should suggest Insurance category
2. Upload bank statement → Should suggest Bank category
3. Upload generic document → Should go to Other category
4. Check confidence scores are reasonable (60-90%)

# Test Learning
1. Accept suggested category → Check weights increased in DB
2. Change suggested category → Check weights adjusted in DB
3. Upload similar document → Should classify better

# Verify in database
SELECT * FROM document_classification_log ORDER BY created_at DESC LIMIT 10;
SELECT * FROM category_keywords WHERE category_id = '<insurance-id>' ORDER BY weight DESC;
Deploy:
bashgit tag v1.1.0-classification
git push origin v1.1.0-classification

PHASE 3: Google Drive Integration (Week 3)
Objective: Store documents in user's Google Drive
Duration: 5 days

Day 11: Google Drive Schema & OAuth
Step 11.1: Drive Database Schema
File: backend/alembic/versions/xxx_google_drive_schema.py
New Tables:
google_drive_folders:
sqlCREATE TABLE google_drive_folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    drive_folder_id VARCHAR(100) NOT NULL UNIQUE,
    folder_path VARCHAR(500),
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, category_id)
);

CREATE INDEX idx_drive_folders_user ON google_drive_folders(user_id);
CREATE INDEX idx_drive_folders_category ON google_drive_folders(category_id);
CREATE INDEX idx_drive_folders_drive_id ON google_drive_folders(drive_folder_id);
google_drive_sync_status:
sqlCREATE TABLE google_drive_sync_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    root_folder_id VARCHAR(100) NOT NULL,
    metadata_folder_id VARCHAR(100),
    trash_folder_id VARCHAR(100),
    last_sync_at TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    total_files INT DEFAULT 0,
    synced_files INT DEFAULT 0,
    failed_files INT DEFAULT 0,
    drive_quota_used BIGINT,
    drive_quota_total BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_drive_sync_user ON google_drive_sync_status(user_id);
CREATE INDEX idx_drive_sync_status ON google_drive_sync_status(sync_status);
Enhance documents table:
sqlALTER TABLE documents ADD COLUMN drive_file_id VARCHAR(100) UNIQUE;
ALTER TABLE documents ADD COLUMN drive_folder_id VARCHAR(100);
ALTER TABLE documents ADD COLUMN drive_web_view_link TEXT;
ALTER TABLE documents ADD COLUMN drive_web_content_link TEXT;
ALTER TABLE documents ADD COLUMN drive_thumbnail_link TEXT;
ALTER TABLE documents ADD COLUMN drive_mime_type VARCHAR(100);
ALTER TABLE documents ADD COLUMN drive_file_size BIGINT;
ALTER TABLE documents ADD COLUMN drive_md5_checksum VARCHAR(32);
ALTER TABLE documents ADD COLUMN is_synced_to_drive BOOLEAN DEFAULT false;
ALTER TABLE documents ADD COLUMN sync_error TEXT;
ALTER TABLE documents ADD COLUMN last_synced_at TIMESTAMP;

CREATE INDEX idx_document_drive_file_id ON documents(drive_file_id);
CREATE INDEX idx_document_synced ON documents(is_synced_to_drive, last_synced_at);
Git Commit:
bashgit add backend/alembic/versions/xxx_google_drive_schema.py
git commit -m "feat: add Google Drive integration schema

- Create google_drive_folders table (category folder mapping)
- Create google_drive_sync_status table (track sync state)
- Add Drive-related columns to documents table
- Add Drive-related columns to users table
- Create indexes for performance"
git push origin main
Wait for Feedback:
Run Migration:

alembic upgrade head

Verify:
SELECT tablename FROM pg_tables 
WHERE tablename LIKE '%drive%';

Should show: google_drive_folders, google_drive_sync_status

Reply with: Success or migration errors.

Step 11.2: Google Drive OAuth Setup
Environment Variables:
Add to .env and Google Secret Manager:
GOOGLE_CLIENT_ID=<existing>
GOOGLE_CLIENT_SECRET=<existing>
GOOGLE_DRIVE_FOLDER_NAME=BoniDoc
OAuth Scopes:
Update OAuth request to include Drive scope:
Existing scopes:
- openid
- email
- profile

Add scope:
- https://www.googleapis.com/auth/drive.file
  (Can only access files created by app, not all user files)
OAuth Flow:
1. Initial Login (Authentication):
   - Request: openid, email, profile
   - Get: User identity
   - Create: User account

2. Connect Google Drive (Authorization):
   - Show: "Connect Google Drive" button in frontend
   - Request: Additional scope (drive.file)
   - User grants: Drive permission
   - Get: Authorization code
   - Exchange: For access token + refresh token
   - Store: Encrypted refresh token in database

3. Token Management:
   - Access token: Valid 1 hour
   - Refresh token: Valid indefinitely (until revoked)
   - Auto-refresh: 5 minutes before expiry
   - Store expires_at in database
Dependencies:
Add to requirements.txt:
google-api-python-client==2.108.0
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
Git Commit:
bashgit add backend/requirements.txt
git add backend/app/services/google_oauth_service.py
git commit -m "feat: add Google Drive OAuth integration

- Add Drive API scope to OAuth request
- Implement separate Drive permission flow
- Store encrypted refresh token
- Auto-refresh access token
- Handle token expiry and refresh
- Add google-api-python-client dependency"
git push origin main

Day 12: Google Drive Service
Step 12.1: Core Drive Service
File: backend/app/services/google_drive_service.py
Purpose: All Google Drive operations
Methods:
Setup & Authentication:

initialize_user_drive(user_id) - Create folder structure on first use
get_drive_client(user_id) - Get authenticated Drive API client
refresh_access_token(user_id) - Get fresh token
check_drive_permission(user_id) - Verify app has access

Folder Management:

create_root_folder(user_id) - Create /BoniDoc/ folder
create_category_folder(user_id, category_id, category_name) - Create subfolder
get_or_create_folder(user_id, folder_name, parent_id) - Idempotent creation
rename_folder(folder_id, new_name) - Rename category folder
list_folders(user_id) - Get all BoniDoc folders
delete_folder(folder_id, move_to_trash=True) - Delete folder

File Operations:

upload_file(user_id, file_bytes, filename, mime_type, folder_id) - Upload document
download_file(user_id, file_id) - Download document bytes
get_file_metadata(file_id) - Get file info without downloading
generate_download_link(file_id, expires_in=3600) - Temporary URL
move_file(file_id, new_folder_id) - Move between categories
rename_file(file_id, new_name) - Rename document
delete_file(file_id, permanent=False) - Delete or trash
check_file_exists(file_id) - Verify file still exists

Quota Management:

get_storage_info(user_id) - Check Drive quota
check_available_space(user_id, file_size) - Before upload

Batch Operations:

batch_upload_files(user_id, files_list) - Upload multiple efficiently

Error Handling:

handle_rate_limit() - Exponential backoff on 429
handle_auth_error() - Re-authenticate on 401
handle_not_found() - File deleted gracefully

Folder Structure to Create:
/BoniDoc/
  ├── Insurance/
  ├── Legal/
  ├── Banking/
  ├── Medical/
  ├── Tax/
  ├── Real_Estate/
  ├── Employment/
  ├── Education/
  ├── Other/
  ├── .metadata/
  └── .trash/
Git Commit:
bashgit add backend/app/services/google_drive_service.py
git commit -m "feat: implement Google Drive service

- Create folder structure in user's Drive
- Upload/download files
- Manage folders (create, rename, delete)
- Generate temporary download links
- Check storage quota before upload
- Batch operations for efficiency
- Rate limiting with exponential backoff
- Comprehensive error handling"
git push origin main
Wait for Feedback:
Test Drive Service:

1. Set up test Google account
2. Grant Drive permissions
3. Run test:
   python test_drive_service.py --user-id=<test-user-id>

Expected:
- /BoniDoc/ folder created
- Subfolders for all categories created
- Test file uploaded successfully
- File can be downloaded

Reply with: Success or errors encountered.

Day 13: Drive Integration in Upload Flow
Step 13.1: Update Batch Upload Service
File: backend/app/services/batch_upload_service.py
Update confirm_upload() method:
Add Drive upload logic:
After classification, before database save:

1. Check Drive Permission:
   IF not user.google_drive_enabled:
       RETURN error "Google Drive not connected"

2. Check Drive Quota:
   available = google_drive_service.check_available_space(
       user_id, file_size
   )
   IF available < file_size:
       RETURN error "Insufficient Drive storage"

3. Get/Create Category Folder:
   drive_folder = db.query(GoogleDriveFolder).filter(
       user_id=user_id,
       category_id=primary_category_id
   ).first()
   
   IF not drive_folder:
       folder_id = google_drive_service.create_category_folder(
           user_id, primary_category_id, category_name
       )
       drive_folder = GoogleDriveFolder(...)
       db.add(drive_folder)

4. Upload File to Drive:
   TRY:
       drive_file = google_drive_service.upload_file(
           user_id=user_id,
           file_bytes=file_content,
           filename=standardized_filename,
           mime_type=mime_type,
           folder_id=drive_folder.drive_folder_id
       )
   EXCEPT RateLimitError:
       # Queue for background retry
       RETURN {"status": "queued"}
   EXCEPT QuotaExceeded:
       RETURN error "Drive storage full"
   EXCEPT Exception as e:
       # Log and queue for retry
       RETURN error "Upload failed, will retry"

5. Save Metadata to Database:
   document = Document(
       ...,
       drive_file_id=drive_file['id'],
       drive_folder_id=drive_folder.drive_folder_id,
       drive_web_view_link=drive_file['webViewLink'],
       drive_web_content_link=drive_file['webContentLink'],
       drive_mime_type=drive_file['mimeType'],
       drive_file_size=drive_file['size'],
       drive_md5_checksum=drive_file['md5Checksum'],
       is_synced_to_drive=True,
       last_synced_at=NOW()
   )
   db.add(document)
   db.commit()

6. Update Sync Status:
   UPDATE google_drive_sync_status
   SET synced_files = synced_files + 1,
       last_sync_at = NOW()
   WHERE user_id = user_id

7. Record Classification & Learning:
   (existing logic)

8. Return Success:
   RETURN {
       document_id: document.id,
       drive_file_id: drive_file['id'],
       view_link: drive_file['webViewLink']
   }
Error Handling:
IF Drive upload fails:
    - Set is_synced_to_drive = false
    - Store error in sync_error column
    - Queue for background retry
    - Still save metadata to database
    - Show user: "Upload queued, will retry automatically"
Git Commit:
bashgit add backend/app/services/batch_upload_service.py
git commit -m "feat: integrate Google Drive into upload flow

- Check Drive permission before upload
- Check storage quota
- Create category folders on first use
- Upload files to user's Drive
- Store Drive metadata in database
- Handle errors gracefully (queue for retry)
- Update sync status
- Return Drive view links to user"
git push origin main

Step 13.2: Background Sync Job
File: backend/app/jobs/drive_sync_job.py
Purpose: Retry failed uploads, verify integrity, cleanup
Job Tasks:
Schedule: Every 15 minutes

Tasks:

1. Retry Failed Uploads:
   - Find documents WHERE is_synced_to_drive = false
   - AND created_at < 5 minutes ago
   - Retry upload to Drive
   - Update status

2. Verify File Integrity:
   - Random sample 10% of documents
   - Check file still exists in Drive
   - Verify MD5 checksum matches
   - Flag discrepancies

3. Update Storage Quotas:
   - For users who uploaded today
   - Fetch quota from Drive API
   - Update user.drive_quota_used

4. Cleanup Expired Sessions:
   (existing logic from session_service)
Scheduler Setup:
Use APScheduler or Cloud Scheduler (Google Cloud)
File: backend/app/jobs/__init__.py
Register jobs:
- drive_sync_job: Every 15 minutes
- session_cleanup_job: Every hour
- metrics_calculation_job: Daily at midnight
Git Commit:
bashgit add backend/app/jobs/drive_sync_job.py
git add backend/app/jobs/__init__.py
git commit -m "feat: add background Drive sync job

- Retry failed uploads every 15 minutes
- Verify file integrity (random sampling)
- Update storage quotas
- Cleanup expired sessions
- Daily metrics calculation
- Use APScheduler for job management"
git push origin main

Day 14: Document Access & Download
Step 14.1: Document View Endpoint
File: backend/app/api/documents.py
New Endpoint:
GET /api/v1/documents/{document_id}/view

Returns:
{
    document_id: "uuid",
    filename: "Insurance_Policy_20241012.pdf",
    download_link: "https://drive.google.com/...",  // Valid 1 hour
    expires_at: "2024-10-12T15:00:00Z",
    mime_type: "application/pdf",
    file_size: 2456789,
    view_in_drive_link: "https://drive.google.com/file/d/..."
}
Implementation:
1. Verify user owns document:
   document = db.query(Document).filter(
       id=document_id,
       user_id=authenticated_user_id
   ).first()
   
   IF not document:
       RETURN 404 "Document not found"

2. Check if synced to Drive:
   IF not document.is_synced_to_drive:
       RETURN 503 "Document not yet synced"

3. Verify file still exists:
   exists = google_drive_service.check_file_exists(
       document.drive_file_id
   )
   
   IF not exists:
       document.is_synced_to_drive = False
       document.sync_error = "File not found in Drive"
       db.commit()
       RETURN 410 "File deleted from Google Drive"

4. Generate temporary download link:
   download_link = google_drive_service.generate_download_link(
       file_id=document.drive_file_id,
       expires_in=3600  # 1 hour
   )

5. Update access tracking:
   document.last_accessed_at = NOW()
   document.download_count += 1
   db.commit()

6. Log access:
   audit_service.log_data_event(
       'document_viewed',
       user_id,
       'document',
       document_id
   )

7. RETURN response with download link
Git Commit:
bashgit add backend/app/api/documents.py
git commit -m "feat: add document view/download endpoint

- Generate temporary Drive download link (1 hour expiry)
- Verify document ownership
- Check file still exists in Drive
- Update access tracking (count, timestamp)
- Log access to audit log
- Handle deleted files gracefully"
git push origin main

Day 15: Frontend Drive Integration
Step 15.1: Drive Connection Flow
File: frontend/src/app/settings/page.tsx
Add Google Drive Section:
typescriptComponent: GoogleDriveSettings

State:
- driveConnected: boolean (from user.google_drive_enabled)
- driveQuota: {used: number, total: number}
- syncStatus: SyncStatus

UI:

IF not driveConnected:
    <Card>
      <h3>Google Drive Storage</h3>
      <p>Store your documents securely in your personal Google Drive.</p>
      <Button onClick={connectDrive}>Connect Google Drive</Button>
    </Card>

ELSE:
    <Card>
      <h3>Google Drive Connected ✓</h3>
      <p>Documents stored in: /BoniDoc/</p>
      
      <ProgressBar 
        value={driveQuota.used} 
        max={driveQuota.total}
        label={`${formatBytes(driveQuota.used)} / ${formatBytes(driveQuota.total)}`}
      />
      
      <div className="actions">
        <Button variant="outline" onClick={openInDrive}>
          View in Google Drive
        </Button>
        <Button variant="destructive" onClick={disconnectDrive}>
          Disconnect Drive
        </Button>
      </div>
    </Card>
Connect Drive Flow:
typescriptconst connectDrive = async () => {
  // 1. Request additional OAuth scope
  const authUrl = await fetch('/api/v1/auth/google/drive-auth-url');
  
  // 2. Redirect to Google OAuth
  window.location.href = authUrl.url;
  
  // 3. After redirect back:
  // Backend exchanges code for token
  // Initializes Drive (creates folders)
  // Returns success
  
  // 4. Show success message
  toast.success("Google Drive connected successfully!");
};
Git Commit:
bashgit add frontend/src/app/settings/page.tsx
git add frontend/src/components/google-drive-settings.tsx
git commit -m "feat: add Google Drive connection UI

- Show Drive connection status
- Connect Drive button (OAuth flow)
- Display storage quota with progress bar
- Open in Drive button
- Disconnect Drive button
- Success/error notifications"
git push origin main

Step 15.2: Document View UI
File: frontend/src/app/documents/[id]/page.tsx
Document Detail Page:
typescriptComponent: DocumentDetailPage

Sections:

1. Document Header:
   - Title
   - Category badges
   - Date uploaded
   - File size

2. Actions:
   - View in Browser (opens Drive link)
   - Download (temporary link)
   - Open in Google Drive (Drive web UI)
   - Share (future feature)
   - Delete

3. Metadata:
   - Keywords (with relevance)
   - Detected language
   - Processing method (OCR or native text)
   - Classification confidence

4. Classification Info:
   - Suggested category
   - Actual category (if different)
   - Matching keywords
   - Feedback widget (if misclassified)
Git Commit:
bashgit add frontend/src/app/documents/[id]/page.tsx
git commit -m "feat: add document detail page

- Display document metadata
- Show keywords and categories
- View/download actions
- Open in Google Drive link
- Classification information
- Keywords that matched
- Future: Classification feedback widget"
git push origin main

Phase 3 Summary & Testing
At End of Week 3:
Checklist:
Database:
☐ google_drive_folders table created
☐ google_drive_sync_status table created
☐ Drive columns added to documents table

Google Drive:
☐ OAuth flow with Drive scope working
☐ Folder structure created in user's Drive
☐ File upload to Drive working
☐ File download from Drive working
☐ Category folders created automatically
☐ Storage quota checked before upload

Backend:
☐ google_drive_service implemented
☐ Drive integration in upload flow
☐ Background sync job running
☐ Document view endpoint working
☐ Temporary download links generated

Frontend:
☐ Drive connection UI implemented
☐ Storage quota displayed
☐ Document view page working
☐ Download functionality working
☐ Open in Drive button working
Testing:
bash# Test Drive Connection
1. Go to Settings
2. Click "Connect Google Drive"
3. Grant permission
4. Verify folder structure created in Drive

# Test Document Upload
1. Upload document
2. Verify file appears in Drive
3. Check file in correct category folder
4. Verify metadata in database

# Test Document Access
1. Click document to view
2. Click "Download"
3. Verify file downloads correctly
4. Click "Open in Drive"
5. Verify opens in Drive web UI

# Verify in database
SELECT * FROM google_drive_folders WHERE user_id = '<user-id>';
SELECT * FROM documents WHERE is_synced_to_drive = true ORDER BY created_at DESC;
Deploy:
bashgit tag v1.2.0-drive
git push origin v1.2.0-drive

PHASE 4: Production Deployment & Monitoring (Week 4)
Objective: Deploy to production, setup monitoring, verify everything works
Duration: 5 days
This phase will be outlined as high-level steps since by this point the implementation pattern is established.

Day 16-17: Final Security Hardening

Enable Cloud Armor (WAF)
Configure security alerts (Slack/Email)
Run penetration testing suite
Fix any security vulnerabilities found
Update privacy policy and terms of service
Setup GDPR compliance features (data export working)

Day 18: Production Deployment

Final code review
Database backup before deployment
Deploy to production Cloud Run
Verify all environment variables set
Run smoke tests on production
Monitor error rates closely

Day 19: Monitoring & Alerts

Setup Cloud Monitoring dashboards
Configure alerts (error rate, latency, quota)
Setup Sentry for error tracking
Configure uptime monitoring
Setup log aggregation
Create runbook for common issues

Day 20: Documentation & Handoff

Update API documentation
Create user guide
Create admin guide
Document deployment process
Document troubleshooting procedures
Handoff to operations team


Appendix: Debug Protocol
When Issues Arise:
Step 1: Identify the Issue
User reports problem → Gather details:
- What were you trying to do?
- What did you expect?
- What happened instead?
- Error message (if any)?
- Steps to reproduce
Step 2: Check Logs
Backend logs:
gcloud logging read "resource.type=cloud_run_revision" --limit=50

Database queries:
SELECT * FROM audit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 20;

Frontend console:
Check browser DevTools → Console for errors
Step 3: Isolate the Problem
Test in isolation:
- Can you reproduce locally?
- Does it happen for all users or just one?
- Does it happen for all files or specific type?
- Does it happen consistently or intermittently?
Step 4: Fix & Verify
Implement fix → Test locally → Deploy → Verify in production → Monitor
Step 5: Git Commit
git add <fixed-files>
git commit -m "fix: <description of issue and fix>"
git push origin main
Step 6: Document
Add to troubleshooting guide if it's a common issue
Update runbook with resolution steps

Final Notes
This deployment guide provides:

Clear current state - What exists and what doesn't
Elimination of technical debt - Remove unused code and tables
Security-first approach - Lock down before adding features
Step-by-step implementation - One day at a time with verification
Git commits at each milestone - Clear version control
Debug protocol - One step at a time, wait for feedback
Production-ready system - Security + OCR + Classification + Drive
Zero rollback - Move forward, fix forward

Total Timeline: 4 weeks to production-ready MVP
At the end, you will have:

Secure, production-grade platform
OCR and classification working
Google Drive integration complete
All technical debt removed
Comprehensive monitoring
Ready for users