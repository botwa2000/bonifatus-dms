# Bonifatus DMS - Deployment Guide v7.0

**Last Updated:** October 5, 2025  
**Production Status:** Fully Operational  
**Domain:** https://bonidoc.com

---

## Production Status Summary

✅ **Operational:** Authentication, Dashboard, Categories, Settings, Profile, Dark Mode  
⏳ **In Development:** Document Upload, Advanced Search  
📋 **Planned:** OCR, AI Categorization, Collaboration Features

---

## Current Production Components

### Infrastructure
- **Cloud Platform:** Google Cloud Run (Backend & Frontend)
- **Database:** Supabase PostgreSQL
- **CI/CD:** GitHub Actions
- **Domain:** bonidoc.com (SSL/TLS active)
- **Region:** us-central1

### Backend Services (FastAPI)
- ✅ Authentication (Google OAuth + JWT)
- ✅ User Management API
- ✅ Categories API (Multilingual)
- ✅ Settings & Localization API
- ✅ User Preferences API
- ✅ Account Deactivation API
- ⏳ Document Management API (placeholder)
- ✅ Google Drive Integration
- ✅ Health Monitoring

### Database Schema (20 Tables Deployed)
- **Users:** `users`, `user_settings`
- **Categories:** `categories`, `category_translations`
- **Documents:** `documents`, `document_languages` (schema ready)
- **System:** `system_settings`, `localization_strings`
- **Audit:** `audit_logs`
- **Planned:** `keywords`, `collections`, `tags`, etc.

### Frontend Features (Next.js 14)
- ✅ Google OAuth Authentication
- ✅ Dashboard with Trial Status
- ✅ Categories Management (Full CRUD)
- ✅ Settings Page (Theme, Language, Preferences)
- ✅ Profile Page (Account Management)
- ✅ Dark Mode Theme Switching
- ✅ Multilingual Support (EN/DE/RU)
- ✅ User Dropdown Navigation
- ✅ Responsive Design
- ⏳ Document Upload (placeholder)

---

## Recent Deployments

### Version 7.0 (October 5, 2025)

**Features Added:**
- Dark mode theme implementation with localStorage persistence
- User profile page with account management
- Account deactivation flow with Google Drive retention notice
- Language-based automatic category translation updates
- Improved settings page with theme switching
- User dropdown menu in dashboard
- Enhanced navigation between pages

**Files Modified:**
- `frontend/src/contexts/theme-context.tsx` (new)
- `frontend/src/app/profile/page.tsx` (new)
- `frontend/src/app/layout.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/app/settings/page.tsx`
- `frontend/src/app/categories/page.tsx`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/tailwind.config.js`
- `.vscode/settings.json` (new)

**Backend Changes:**
- Account deactivation endpoint operational
- User profile update endpoint tested
- Statistics endpoint validated

### Version 6.0 (October 4, 2025)
- Fixed categories update/delete operations
- Implemented database-driven default categories
- Enhanced multilingual support
- Improved category-to-folder sync

---

## Production URLs

### Frontend
- **Main App:** https://bonidoc.com
- **Dashboard:** https://bonidoc.com/dashboard
- **Categories:** https://bonidoc.com/categories
- **Settings:** https://bonidoc.com/settings
- **Profile:** https://bonidoc.com/profile
- **Login:** https://bonidoc.com/login
- **Documents:** https://bonidoc.com/documents (placeholder)

### Backend
- **API Base:** https://bonidoc.com/api
- **API Docs:** https://bonidoc.com/docs
- **Health Check:** https://bonidoc.com/health
- **Direct Backend:** https://bonifatus-dms-vpm3xabjwq-uc.a.run.app

---

## API Endpoints Reference

### Authentication (8 endpoints)
GET  /api/v1/auth/google/config     - OAuth configuration
GET  /api/v1/auth/google/login      - Initiate OAuth flow
POST /api/v1/auth/google/callback   - Complete OAuth
POST /api/v1/auth/refresh           - Refresh access token
GET  /api/v1/auth/me                - Current user profile
DELETE /api/v1/auth/logout          - User logout
POST /api/v1/auth/admin/verify      - Admin verification
GET  /api/v1/auth/health            - Auth service health

### User Management (10 endpoints)
GET  /api/v1/users/profile          - Get user profile
PUT  /api/v1/users/profile          - Update profile
GET  /api/v1/users/statistics       - User statistics
GET  /api/v1/users/preferences      - Get preferences
PUT  /api/v1/users/preferences      - Update preferences
POST /api/v1/users/preferences/reset - Reset to defaults
GET  /api/v1/users/dashboard        - Dashboard data
POST /api/v1/users/deactivate       - Account deactivation
GET  /api/v1/users/export           - Export user data

### Categories (6 endpoints)
GET    /api/v1/categories           - List categories (in user's language)
POST   /api/v1/categories           - Create category
PUT    /api/v1/categories/{id}      - Update category
DELETE /api/v1/categories/{id}      - Delete category
POST   /api/v1/categories/restore-defaults - Restore system defaults

### Settings (3 endpoints)
GET /api/v1/settings/public              - Public system settings
GET /api/v1/settings/localization/{lang} - Language strings
GET /api/v1/settings/localization        - All localizations

### Documents (Planned - 6+ endpoints)
POST   /api/v1/documents/upload        - Upload document
GET    /api/v1/documents               - List documents
GET    /api/v1/documents/{id}          - Get document
PUT    /api/v1/documents/{id}          - Update document
DELETE /api/v1/documents/{id}          - Delete document
GET    /api/v1/documents/{id}/download - Download document

---

## Deployment Workflow

### Standard Deployment Process
```bash
# 1. Make changes locally
cd bonifatus-dms

# 2. Test locally (if development environment available)
cd frontend && npm run dev
cd backend && uvicorn app.main:app --reload

# 3. Commit changes
git add .
git commit -m "feat: description of changes"

# 4. Push to main branch (triggers automatic deployment)
git push origin main

# 5. Monitor deployment
# GitHub Actions: https://github.com/your-repo/actions
# Watch build logs in GitHub Actions tab

# 6. Verify deployment
curl https://bonidoc.com/health
# Visit https://bonidoc.com and test features

# 7. Check logs if needed
gcloud logging read "resource.type=cloud_run_revision" --limit 50
Emergency Rollback
bash# List recent revisions
gcloud run revisions list --service=bonifatus-dms --region=us-central1

# Route traffic to previous revision
gcloud run services update-traffic bonifatus-dms \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

Feature Implementation Roadmap
Phase 1: Core User Management ✅ COMPLETE
Status: 100% Complete
Completed: October 5, 2025
Delivered Features:

✅ Google OAuth authentication
✅ User profile management
✅ Settings page with preferences
✅ Dark mode theme switching
✅ Multilingual support (EN/DE/RU)
✅ Category management (full CRUD)
✅ Dynamic multilingual categories
✅ Account deactivation flow
✅ Dashboard with trial status
✅ User navigation menu

Success Metrics:

Authentication working: ✅
Settings persistence: ✅
Profile updates functional: ✅
Theme switching: ✅
Language switching: ✅
Zero critical bugs: ✅


Phase 2: Document Management ⏳ IN PROGRESS
Status: 20% Complete
Timeline: October 6-12, 2025
Backend Tasks:

⏳ Implement file upload handler
⏳ Google Drive folder management
⏳ Storage quota validation
⏳ File type and size validation
⏳ Virus scanning integration
⏳ Document metadata extraction

Frontend Tasks:

⏳ Document upload UI component
⏳ Drag-and-drop file upload
⏳ Upload progress indicators
⏳ Document list view with pagination
⏳ Document detail modal
⏳ Category assignment interface
⏳ Document search functionality

Success Metrics:

Upload success rate: >95%
Average upload time: <5s
Storage quota enforcement: 100%
File type validation: 100%


Phase 3: Enhanced Features 📋 PLANNED
Status: Not Started
Timeline: October 13-27, 2025
Features:

OCR text extraction (Google Vision API)
AI-powered auto-categorization
Keyword extraction
Advanced search filters
Multi-language document support
Document preview
Bulk operations

Success Metrics:

OCR accuracy: >90%
AI categorization accuracy: >80%
Search response time: <500ms


Phase 4: Collaboration Features 📋 PLANNED
Status: Not Started
Timeline: October 28 - November 15, 2025
Features:

Document sharing
Collections/folders
Document relationships
Activity feeds
Email notifications
Document comments
Version history


Configuration Management
Environment Variables (GitHub Secrets)
Required Secrets (43 total):
Database (6 secrets):

DATABASE_URL
SUPABASE_URL
SUPABASE_KEY
DB_POOL_SIZE
DB_ECHO
DB_POOL_RECYCLE

Google Services (8 secrets):

GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
GOOGLE_DRIVE_FOLDER_ID
GOOGLE_SERVICE_ACCOUNT_KEY
GOOGLE_SCOPES
GOOGLE_OAUTH_SCOPES
GOOGLE_API_KEY

Security (6 secrets):

JWT_SECRET_KEY
JWT_ALGORITHM
JWT_ACCESS_TOKEN_EXPIRE_MINUTES
JWT_REFRESH_TOKEN_EXPIRE_DAYS
CORS_ORIGINS
ALLOWED_HOSTS

Application Settings (8 secrets):

ENVIRONMENT
LOG_LEVEL
API_VERSION
FRONTEND_URL
BACKEND_URL
MAX_UPLOAD_SIZE
ALLOWED_FILE_TYPES
DATA_RETENTION_DAYS

System Settings (Database-Driven)
Stored in system_settings table:

Default theme: light
Available themes: ["light", "dark"]
Default language: en
Available languages: ["en", "de", "ru"]
Max file size: 52428800 (50 MB)
Storage quotas: Free (1GB), Premium (10GB), Enterprise (100GB)
Default categories: JSON configuration in database


Development Standards
Code Quality Checklist
Before Every Commit:

 Files are modular (<300 lines)
 No hardcoded values (database-driven)
 Production-ready code only
 Checked for duplicate functions
 Professional comments
 Root cause fixes (no workarounds)
 All imports at top of file
 File header comment with path

Testing:

 Manual testing in production
 All CRUD operations verified
 Multilingual support tested
 Responsive design verified
 Dark mode tested (if applicable)

Deployment:

 Single-feature commits
 Clear commit messages
 GitHub Actions monitored
 Health checks verified post-deployment

Commit Message Format
bashgit commit -m "type: brief description

- Detail 1
- Detail 2
- Detail 3"
Types: feat, fix, docs, style, refactor, test, chore

Monitoring & Maintenance
Health Checks
bash# Application health
curl https://bonidoc.com/health

# Backend health
curl https://bonidoc.com/api/v1/auth/health

# Database connectivity (via backend)
# Check /health endpoint response
Logging
bash# View recent logs (last 50 entries)
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Filter by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit 20

# Filter by timestamp
gcloud logging read "resource.type=cloud_run_revision AND timestamp>\"2025-10-05T00:00:00Z\"" --limit 100
Performance Monitoring
Target Metrics:

API Response Time: <300ms (95th percentile)
Page Load Time: <2s
Time to Interactive: <3s
Uptime: >99.5%
Error Rate: <1%

Monitor via:

Google Cloud Console: https://console.cloud.google.com
Cloud Run Metrics Dashboard
Application logs


Database Backup & Recovery
Automated Backups

Provider: Supabase
Frequency: Daily automatic backups
Retention: 7 days (free tier)
Access: Supabase Dashboard

Manual Backup
bash# Contact Supabase support or use Supabase Dashboard
# Point-in-time recovery available
Recovery Procedures
Application Rollback:
bashgcloud run revisions list --service=bonifatus-dms --region=us-central1
gcloud run services update-traffic bonifatus-dms \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100
Database Restore:

Access Supabase Dashboard
Navigate to Backups section
Select restore point
Follow Supabase restoration wizard


Troubleshooting Guide
Common Issues
1. Build Failures
bash# Check GitHub Actions logs
# Common causes:
# - TypeScript errors
# - Missing dependencies
# - Environment variable issues

# Solution:
# Review error logs in GitHub Actions
# Fix locally and push again
2. Authentication Issues
bash# Verify Google OAuth credentials
# Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in GitHub Secrets
# Verify redirect URI matches: https://bonidoc.com/login

# Test OAuth flow:
curl https://bonidoc.com/api/v1/auth/google/config
3. Database Connection Errors
bash# Check DATABASE_URL in GitHub Secrets
# Verify Supabase project is active
# Check connection pooling settings

# Test database connectivity:
curl https://bonidoc.com/health
4. Categories Not Updating After Language Change
bash# This should work automatically after v7.0
# If issue persists:
# 1. Clear browser cache
# 2. Logout and login again
# 3. Check browser console for errors
5. Dark Mode Not Applying
bash# Clear localStorage:
# Open browser console and run: localStorage.clear()
# Then reload page and set theme again

Known Limitations
Current Limitations:

No Staging Environment

All changes deploy directly to production
Requires careful testing before push
Consider creating a staging branch in future


Limited Testing Coverage

Manual testing only (pre-launch)
No automated test suite yet
Plan to add Jest/Cypress tests


Single Region Deployment

us-central1 only
Future: Multi-region for better performance


Free Tier Limits

Supabase: 500MB database, 7-day backups
Cloud Run: Scales to zero when idle
Consider upgrading for production scale




Security Considerations
Authentication & Authorization

OAuth 2.0 with Google
JWT tokens (short-lived access, long-lived refresh)
Secure token storage (httpOnly cookies recommended)
Password-less authentication

Data Protection

All API calls over HTTPS
Database encryption at rest (Supabase)
Secure environment variable storage (GitHub Secrets)
Audit logging for all user actions

GDPR Compliance

Account deactivation with 30-day retention
User data export available
Google Drive data remains with user
Clear privacy policy required


Support & Resources
Documentation

API Docs: https://bonidoc.com/docs
This Guide: DEPLOYMENT_GUIDE.md
Development Guide: DEVELOPMENT_GUIDE_VS.md
Code Standards: Section 15.2 of project docs

Cloud Resources

GCP Console: https://console.cloud.google.com
Supabase Dashboard: https://supabase.com/dashboard
GitHub Repository: https://github.com/botwa2000/bonifatus-dms
GitHub Actions: https://github.com/botwa2000/bonifatus-dms/actions

Key Commands Reference
bash# Deployment
git push origin main

# View services
gcloud run services list --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Force redeploy
git commit --allow-empty -m "redeploy" && git push

# Health check
curl https://bonidoc.com/health

# Rollback
gcloud run services update-traffic bonifatus-dms \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100

Next Immediate Actions
This Week (October 6-12, 2025)
Monday:

✅ Deploy profile page
✅ Test account deactivation flow
⏳ Begin document upload backend implementation

Tuesday-Wednesday:

⏳ Complete file upload handler
⏳ Implement storage quota validation
⏳ Add virus scanning integration

Thursday-Friday:

⏳ Create document upload UI
⏳ Implement drag-and-drop
⏳ Add progress indicators


Changelog
Version 7.0 (October 5, 2025)

✅ Dark mode theme implementation
✅ User profile page
✅ Account deactivation flow
✅ Language-based category updates
✅ Enhanced navigation

Version 6.0 (October 4, 2025)

✅ Categories CRUD operations
✅ Database-driven default categories
✅ Settings page
✅ Dashboard updates

Version 5.0 (October 3, 2025)

✅ Dynamic multilingual categories
✅ System settings
✅ Localization strings

Version 4.0 (October 2, 2025)

✅ Initial production deployment
✅ Google OAuth
✅ Basic dashboard
✅ Database schema


Deployment Guide Version: 7.0
Last Updated: October 5, 2025
Status: All core features operational, document management in development
Maintainer: Development Team

---

## Commit Command
```bash
git add frontend/src/app/settings/page.tsx
git add frontend/src/app/profile/page.tsx
git add DEPLOYMENT_GUIDE.md

git commit -m "feat: add profile page and update deployment guide

- Create comprehensive user profile page
- Account information display with edit capability
- Subscription tier and trial status display
- Account statistics (documents, categories, storage)
- Account deactivation with Google Drive retention notice
- Improve language change to force navigation to dashboard
- Update deployment guide to v7.0 with complete documentation
- Document all features, APIs, and operational procedures"

git push origin main