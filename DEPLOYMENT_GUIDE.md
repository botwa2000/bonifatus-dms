# Bonifatus DMS - Deployment Guide v8.0

**Last Updated:** October 8, 2025  
**Production Status:** Fully Operational  
**Domain:** https://bonidoc.com  
**Maintainer:** Development Team

---

## Production Status Summary

✅ **Operational:** Authentication, Dashboard, Categories, Settings, Profile, Dark Mode, Upload Navigation  
⏳ **In Development:** Document Upload Processing, OCR, AI Categorization  
📋 **Planned:** Advanced Search, Collaboration Features

---

## Current Production Components

### Infrastructure
- **Cloud Platform:** Google Cloud Run (Backend & Frontend)
- **Database:** Supabase PostgreSQL (15.x)
- **CI/CD:** GitHub Actions (automated)
- **Domain:** bonidoc.com (SSL/TLS active)
- **Region:** us-central1
- **Monitoring:** Cloud Run metrics + Application logs

### Backend Services (FastAPI)
- ✅ Authentication (Google OAuth 2.0 + JWT)
- ✅ User Management API (profile, preferences, statistics)
- ✅ Categories API (multilingual CRUD operations)
- ✅ Settings & Localization API (public + admin)
- ✅ Account Deactivation API
- ✅ Google Drive Integration (infrastructure)
- ✅ Health Monitoring (/health endpoint)
- ⏳ Document Upload Processing (in development)
- ⏳ OCR Processing (planned)
- ⏳ AI Categorization (planned)

### Database Schema (20 Tables)
**Deployed & Active:**
- **Users:** `users`, `user_settings`
- **Categories:** `categories`, `category_translations`
- **Documents:** `documents`, `document_languages`
- **System:** `system_settings`, `localization_strings`
- **Audit:** `audit_logs`

**Schema Ready (Not Used Yet):**
- `keywords`, `document_keywords`
- `collections`, `tags`
- `shared_documents`, `document_shares`
- `ocr_results`, `ai_processing_queue`
- `user_storage_quotas`

### Frontend Features (Next.js 15)
- ✅ Google OAuth Authentication
- ✅ Dashboard with Trial Status & Navigation
- ✅ Categories Management (Full CRUD)
- ✅ Settings Page (Theme, Language, Timezone, Notifications)
- ✅ Profile Page (Account Management & Deactivation)
- ✅ Dark Mode Theme (localStorage persistence)
- ✅ Multilingual Support (EN/DE/RU)
- ✅ User Dropdown Navigation Menu
- ✅ Responsive Design (Mobile/Tablet/Desktop)
- ✅ Upload Page Navigation (Dashboard → Upload)
- ⏳ Document Upload Processing (UI complete, backend in progress)
- ⏳ Document List View (structure ready)
- ⏳ Search Functionality (planned)

---

## Recent Deployments

### Version 8.0 (October 8, 2025) 🔥 **LATEST**

**Dashboard Navigation Enhancement:**
- ✅ Fixed dashboard upload button navigation
- ✅ Added Link components to "Upload Documents" action card
- ✅ Added Link wrapper to "Upload Document" button in empty state
- ✅ Fixed import path from `next/dist/client/link` to `next/link`
- ✅ Added missing grid container wrapper for Quick Actions cards
- ✅ Users can now navigate to upload page from dashboard
- ✅ Consistent hover effects on clickable cards

**Technical Details:**
- Fixed 3 navigation issues in dashboard
- Properly wrapped UI elements with Next.js Link components
- Maintained responsive grid layout for action cards
- No breaking changes to existing functionality

**Files Modified:**
- `frontend/src/app/dashboard/page.tsx`

**User Impact:**
- Upload functionality now accessible from main dashboard
- Improved user experience with clickable action cards
- Seamless navigation to document upload page

**Commit Command:**
```bash
git add frontend/src/app/dashboard/page.tsx
git commit -m "fix: add navigation to upload page from dashboard

- Fix Link import path from next/dist/client/link to next/link
- Add grid container wrapper for Quick Actions cards
- Wrap Upload Documents card with Link to /documents/upload
- Wrap Upload Document button with Link to /documents/upload
- Enable upload functionality from dashboard interface"
git push origin main
```

---

### Version 7.0 (October 5, 2025)

**Dark Mode & Profile Features:**
- ✅ Dark mode theme implementation with localStorage persistence
- ✅ User profile page with account management
- ✅ Account deactivation flow with Google Drive retention notice
- ✅ Language-based automatic category translation updates
- ✅ Improved settings page with theme switching
- ✅ User dropdown menu in dashboard
- ✅ Enhanced navigation between pages

**Files Modified:**
- `frontend/src/contexts/theme-context.tsx` (new)
- `frontend/src/app/profile/page.tsx` (new)
- `frontend/src/app/layout.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/app/settings/page.tsx`
- `frontend/src/app/categories/page.tsx`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/tailwind.config.js`

**Backend Changes:**
- Account deactivation endpoint operational
- User profile update endpoint tested
- Statistics endpoint validated

---

### Version 6.0 (October 4, 2025)

**Category Management:**
- ✅ Categories CRUD operations
- ✅ Database-driven default categories
- ✅ Settings page
- ✅ Dashboard UI updates

---

### Version 5.0 (October 3, 2025)

**Localization & Configuration:**
- ✅ Dynamic multilingual categories
- ✅ System settings infrastructure
- ✅ Localization strings database

---

### Version 4.0 (October 2, 2025)

**Initial Production Launch:**
- ✅ Initial production deployment
- ✅ Google OAuth integration
- ✅ Basic dashboard
- ✅ Database schema (20 tables)

---

## Standard Deployment Process

### Automated Deployment via GitHub Actions

**Trigger:** Push to `main` branch  
**Platform:** GitHub Actions → Google Cloud Run  
**Duration:** ~3-5 minutes  
**Zero Downtime:** Yes (Cloud Run manages traffic routing)

**Deployment Steps:**
```bash
# 1. Make changes locally
cd bonifatus-dms

# 2. Test locally (optional but recommended)
# Backend:
cd backend && uvicorn app.main:app --reload
# Frontend:
cd frontend && npm run dev

# 3. Stage changes
git add .

# 4. Commit with descriptive message
git commit -m "feat: description of changes

- Detail 1: what changed
- Detail 2: why it changed
- Detail 3: impact of change"

# 5. Push to main branch (triggers automatic deployment)
git push origin main

# 6. Monitor deployment
# GitHub Actions: https://github.com/botwa2000/bonifatus-dms/actions

# 7. Verify deployment
curl https://bonidoc.com/health

# 8. Test features in production
# Visit https://bonidoc.com and test changes
```

### Emergency Rollback

```bash
# 1. List recent revisions
gcloud run revisions list \
  --service=bonifatus-dms \
  --region=us-central1

# 2. Route traffic to previous revision
gcloud run services update-traffic bonifatus-dms \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# 3. Verify rollback
curl https://bonidoc.com/health

# 4. Check logs for issues
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

---

## Feature Implementation Roadmap

### Phase 1: Core User Management ✅ **COMPLETE**
**Status:** 100% Complete  
**Completed:** October 8, 2025

**Delivered Features:**
- ✅ Google OAuth authentication
- ✅ User profile management
- ✅ Settings page with preferences
- ✅ Dark mode theme switching
- ✅ Multilingual support (EN/DE/RU)
- ✅ Category management (full CRUD)
- ✅ Dynamic multilingual categories
- ✅ Account deactivation flow
- ✅ Dashboard with trial status
- ✅ User navigation menu
- ✅ Upload page navigation

**Success Metrics:**
- Authentication working: ✅
- Settings persistence: ✅
- Profile updates functional: ✅
- Theme switching: ✅
- Language switching: ✅
- Navigation working: ✅
- Zero critical bugs: ✅

---

### Phase 2: Document Management ⏳ **IN PROGRESS**
**Status:** 30% Complete  
**Timeline:** October 8-15, 2025

**Backend Tasks:**
- ⏳ Implement file upload handler
- ⏳ Google Drive folder creation/management
- ⏳ Storage quota validation logic
- ⏳ File type and size validation
- ⏳ Virus scanning integration
- ⏳ Document metadata extraction
- ⏳ Text extraction preparation (OCR pipeline)

**Frontend Tasks:**
- ✅ Document upload UI component (complete)
- ✅ Drag-and-drop file upload (complete)
- ✅ Upload progress indicators (complete)
- ✅ Category selection interface (complete)
- ⏳ Document list view with pagination
- ⏳ Document detail modal
- ⏳ Document search functionality
- ⏳ Document download functionality

**Current Week Goals (October 8-12):**
- **Monday-Tuesday:** Complete backend upload handler
- **Wednesday-Thursday:** Implement storage quota validation
- **Friday:** Integration testing and bug fixes

**Success Metrics:**
- Upload success rate: >95%
- Average upload time: <5s for 10MB files
- Storage quota enforcement: 100%
- File type validation: 100%
- Error handling: All edge cases covered

---

### Phase 3: Enhanced Features 📋 **PLANNED**
**Status:** Not Started  
**Timeline:** October 16-27, 2025

**OCR Implementation:**
- Google Vision API integration
- Text extraction from PDF/images
- Language detection
- OCR results storage
- Processing status tracking

**AI Categorization:**
- Document content analysis
- Category suggestion algorithm
- Confidence scoring
- User feedback loop
- Model training preparation

**Search Functionality:**
- Full-text search implementation
- Search by category, date, language
- Keyword-based search
- Search result ranking
- Search filters and sorting

**Success Metrics:**
- OCR accuracy: >90%
- AI categorization accuracy: >80%
- Search response time: <500ms
- User satisfaction: >85%

---

### Phase 4: Collaboration Features 📋 **PLANNED**
**Status:** Not Started  
**Timeline:** October 28 - November 15, 2025

**Document Sharing:**
- Share link generation
- Permission management (view/edit)
- Expiration dates
- Access logging

**Collections/Folders:**
- Folder creation and management
- Document organization
- Nested folder support
- Bulk operations

**Activity & Notifications:**
- Document activity tracking
- User activity feeds
- Email notifications
- In-app notifications
- Real-time updates

**Success Metrics:**
- Share feature adoption: >40%
- Collection usage: >60%
- Notification delivery rate: >99%

---

## Configuration Management

### Environment Variables (GitHub Secrets)

**Total Required Secrets:** 43 environment variables

#### **Database Configuration (6 secrets)**
```
DATABASE_URL              - PostgreSQL connection string
SUPABASE_URL             - Supabase project URL
SUPABASE_KEY             - Supabase anon key
DB_POOL_SIZE             - Connection pool size (default: 10)
DB_ECHO                  - SQL logging (default: false)
DB_POOL_RECYCLE          - Pool recycle time (default: 3600)
```

#### **Google Services (8 secrets)**
```
GOOGLE_CLIENT_ID         - OAuth 2.0 client ID
GOOGLE_CLIENT_SECRET     - OAuth 2.0 client secret
GOOGLE_REDIRECT_URI      - OAuth callback URL
GOOGLE_DRIVE_FOLDER_ID   - Root folder for documents
GOOGLE_SERVICE_ACCOUNT_KEY - Service account JSON
GOOGLE_SCOPES            - Drive API scopes
GOOGLE_OAUTH_SCOPES      - OAuth scopes
GOOGLE_API_KEY           - Google API key
```

#### **Security Configuration (6 secrets)**
```
JWT_SECRET_KEY           - JWT signing key
JWT_ALGORITHM            - JWT algorithm (default: HS256)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES  - Access token expiry (default: 60)
JWT_REFRESH_TOKEN_EXPIRE_DAYS    - Refresh token expiry (default: 7)
CORS_ORIGINS             - Allowed CORS origins
ALLOWED_HOSTS            - Allowed hostnames
```

#### **Application Settings (8 secrets)**
```
ENVIRONMENT              - Application environment
LOG_LEVEL                - Logging level
API_VERSION              - API version
FRONTEND_URL             - Frontend URL
BACKEND_URL              - Backend URL
MAX_UPLOAD_SIZE          - Max file size (bytes)
ALLOWED_FILE_TYPES       - Allowed MIME types
DATA_RETENTION_DAYS      - Data retention period
```

#### **GCP Deployment (5 secrets)**
```
GCP_PROJECT              - Google Cloud project ID
GCP_REGION               - Deployment region
GCP_SA_KEY               - Service account key (JSON)
NEXT_PUBLIC_API_URL      - API URL for frontend
PORT                     - Server port (default: 8080)
```

### System Settings (Database-Driven)

Stored in `system_settings` table:

```json
{
  "default_theme": "light",
  "available_themes": ["light", "dark"],
  "default_language": "en",
  "available_languages": ["en", "de", "ru"],
  "max_file_size": 52428800,
  "storage_quotas": {
    "free": 1073741824,
    "premium": 10737418240,
    "enterprise": 107374182400
  },
  "default_system_categories": [
    {"reference_key": "insurance", "code": "INS"},
    {"reference_key": "legal", "code": "LEG"},
    {"reference_key": "real_estate", "code": "REA"},
    {"reference_key": "banking", "code": "BAN"},
    {"reference_key": "other", "code": "OTH"}
  ]
}
```

---

## Development Standards

### Code Quality Checklist

**Before Every Commit:**
- [ ] Files are modular (<300 lines)
- [ ] No hardcoded values (database-driven)
- [ ] Production-ready code only (no TODO/FIXME)
- [ ] Checked for duplicate functions
- [ ] Professional comments
- [ ] Root cause fixes (no workarounds)
- [ ] All imports at top of file
- [ ] File header comment with path

**Testing:**
- [ ] Manual testing in production
- [ ] All CRUD operations verified
- [ ] Multilingual support tested
- [ ] Responsive design verified
- [ ] Dark mode tested
- [ ] Error handling checked

**Deployment:**
- [ ] Single-feature commits
- [ ] Clear commit messages
- [ ] GitHub Actions monitored
- [ ] Health checks verified post-deployment
- [ ] No breaking changes

### Commit Message Format

```bash
git commit -m "type: brief description

- Detail 1: specific change made
- Detail 2: reason for change
- Detail 3: impact or benefit"
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**
```bash
# Good commit messages
git commit -m "feat: add document upload page navigation

- Add Link components to dashboard upload buttons
- Fix import path for Next.js Link
- Enable seamless navigation to upload page"

git commit -m "fix: resolve dark mode persistence issue

- Store theme preference in localStorage
- Apply theme on initial page load
- Prevent flash of wrong theme"

# Bad commit messages (avoid these)
git commit -m "updates"
git commit -m "fix stuff"
git commit -m "WIP"
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Application health
curl https://bonidoc.com/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-10-08T12:00:00Z",
  "version": "1.0.0",
  "database": "connected"
}

# Backend health
curl https://bonidoc.com/api/v1/auth/health

# Check specific service status
curl https://bonidoc.com/api/v1/categories
```

### Logging

```bash
# View recent logs (last 50 entries)
gcloud logging read "resource.type=cloud_run_revision" \
  --limit 50 \
  --format=json

# Filter by severity
gcloud logging read \
  "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit 20

# Filter by timestamp
gcloud logging read \
  "resource.type=cloud_run_revision AND timestamp>\"2025-10-08T00:00:00Z\"" \
  --limit 100

# Filter by service
gcloud logging read \
  "resource.labels.service_name=bonifatus-dms" \
  --limit 50
```

### Performance Monitoring

**Target Metrics:**
- API Response Time: <200ms (95th percentile)
- Page Load Time: <1.5s
- Time to Interactive: <2.5s
- Uptime: >99.9%
- Error Rate: <0.1%

**Monitor via:**
- Google Cloud Console: https://console.cloud.google.com
- Cloud Run Metrics Dashboard
- Application logs
- Supabase Dashboard

### Database Monitoring

```bash
# Check database size
# Visit: Supabase Dashboard → Database → Disk Usage

# Monitor active connections
# Visit: Supabase Dashboard → Database → Connection Pooling

# Review slow queries
# Visit: Supabase Dashboard → Database → Query Performance
```

---

## Backup & Recovery

### Automated Backups

**Provider:** Supabase  
**Frequency:** Daily automatic backups  
**Retention:** 7 days (free tier), 30 days (pro tier)  
**Access:** Supabase Dashboard → Database → Backups

### Manual Backup

```bash
# Export database via Supabase Dashboard
# 1. Navigate to: Database → Backups
# 2. Click: "Download backup"
# 3. Select date range
# 4. Export format: SQL or CSV
```

### Recovery Procedures

**Application Rollback:**
```bash
# 1. List revisions
gcloud run revisions list \
  --service=bonifatus-dms \
  --region=us-central1

# 2. Route traffic to previous revision
gcloud run services update-traffic bonifatus-dms \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# 3. Verify rollback
curl https://bonidoc.com/health
```

**Database Restore:**
1. Access Supabase Dashboard
2. Navigate to Database → Backups
3. Select restore point
4. Click "Restore backup"
5. Confirm restoration
6. Monitor progress
7. Verify data integrity

---

## Troubleshooting Guide

### Common Issues

#### **1. Build Failures**

**Symptom:** GitHub Actions build fails

**Common Causes:**
- TypeScript compilation errors
- Missing dependencies
- Environment variable issues
- Docker build errors

**Solution:**
```bash
# Check GitHub Actions logs
# Visit: https://github.com/botwa2000/bonifatus-dms/actions

# Fix locally
cd frontend && npm run build
cd backend && python -m py_compile app/**/*.py

# Verify and redeploy
git push origin main
```

#### **2. Authentication Issues**

**Symptom:** Users cannot log in

**Common Causes:**
- Invalid OAuth credentials
- Incorrect redirect URI
- JWT secret mismatch
- Token expiration

**Solution:**
```bash
# Verify Google OAuth credentials
# Visit: Google Cloud Console → Credentials

# Check secrets in GitHub
# Visit: Repository Settings → Secrets → Actions

# Test OAuth flow
curl https://bonidoc.com/api/v1/auth/google/config

# Verify JWT configuration
# Check JWT_SECRET_KEY, JWT_ALGORITHM in secrets
```

#### **3. Database Connection Errors**

**Symptom:** "Database connection failed" errors

**Common Causes:**
- Incorrect DATABASE_URL
- Supabase project paused
- Connection pool exhausted
- Network issues

**Solution:**
```bash
# Check DATABASE_URL in GitHub Secrets
# Verify format: postgresql://user:pass@host:5432/db

# Verify Supabase project status
# Visit: https://supabase.com/dashboard

# Test connection
curl https://bonidoc.com/health

# Check connection pooling
# Supabase Dashboard → Database → Connection Pooling
```

#### **4. Upload Page Not Accessible**

**Symptom:** Clicking upload button does nothing

**Common Causes:**
- Missing Link component wrapper
- Incorrect route configuration
- JavaScript errors

**Solution:**
```bash
# Check browser console for errors
# F12 → Console

# Verify Link component usage
# See Version 8.0 fixes above

# Clear browser cache
# Ctrl+Shift+Delete → Clear cache

# Test navigation
# Visit: https://bonidoc.com/documents/upload directly
```

#### **5. Dark Mode Not Applying**

**Symptom:** Theme doesn't persist or apply

**Common Causes:**
- localStorage not accessible
- Theme context not initialized
- CSS not loaded

**Solution:**
```bash
# Clear localStorage
# Browser console: localStorage.clear()

# Reload page and set theme again
# Visit: Settings → Theme → Select theme

# Check theme persistence
# Close browser and reopen
```

---

## Known Limitations

### Current Limitations

1. **No Staging Environment**
   - All changes deploy directly to production
   - Requires careful testing before push
   - Consider creating staging branch in future

2. **Limited Testing Coverage**
   - Manual testing only (pre-automation)
   - No automated test suite yet
   - Plan to add Jest/Cypress tests

3. **Single Region Deployment**
   - us-central1 only
   - Future: Multi-region for better performance
   - Consider CDN for static assets

4. **Free Tier Constraints**
   - Supabase: 500MB database, 7-day backups
   - Cloud Run: Scales to zero when idle
   - Consider upgrading for production scale

5. **Document Processing Not Complete**
   - Upload UI ready, backend in development
   - OCR not yet implemented
   - AI categorization planned

---

## Security Considerations

### Authentication & Authorization

- ✅ OAuth 2.0 with Google
- ✅ JWT tokens (short-lived access, long-lived refresh)
- ✅ Secure token storage recommended (httpOnly cookies)
- ✅ Password-less authentication
- ⏳ Rate limiting (planned)
- ⏳ Two-factor authentication (planned)

### Data Protection

- ✅ All API calls over HTTPS
- ✅ Database encryption at rest (Supabase)
- ✅ Secure environment variable storage (GitHub Secrets)
- ✅ Audit logging for all user actions
- ⏳ Field-level encryption (planned for sensitive data)

### GDPR Compliance

- ✅ Account deactivation with 30-day retention
- ✅ User data export available
- ✅ Google Drive data remains with user
- ⏳ Clear privacy policy (needed)
- ⏳ Cookie consent banner (needed)

---

## Support & Resources

### Documentation

- **API Docs:** https://bonidoc.com/docs
- **This Guide:** DEPLOYMENT_GUIDE.md
- **Development Guide:** DEVELOPMENT_GUIDE_VS.md
- **README:** README.md
- **Code Standards:** Implementation Quality Checklist (Section 15.2)

### Cloud Resources

- **GCP Console:** https://console.cloud.google.com
- **Supabase Dashboard:** https://supabase.com/dashboard
- **GitHub Repository:** https://github.com/botwa2000/bonifatus-dms
- **GitHub Actions:** https://github.com/botwa2000/bonifatus-dms/actions

### Key Commands Reference

```bash
# Deployment
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
```

---

## Next Immediate Actions

### This Week (October 8-12, 2025)

**Monday:**
- ✅ Deploy dashboard navigation fix (Version 8.0)
- ✅ Test upload page accessibility
- ⏳ Begin backend upload handler implementation

**Tuesday-Wednesday:**
- ⏳ Complete file upload endpoint
- ⏳ Implement storage quota validation
- ⏳ Add virus scanning integration

**Thursday-Friday:**
- ⏳ Integration testing
- ⏳ Bug fixes and optimization
- ⏳ Prepare for OCR implementation

### Next Week (October 14-18, 2025)

**Document Management:**
- Complete upload processing
- Implement document list view
- Add document detail modal
- Enable document download

**OCR Preparation:**
- Google Vision API setup
- OCR pipeline architecture
- Text extraction testing

**Testing & QA:**
- End-to-end upload testing
- Performance optimization
- Error handling verification

---

## Changelog

### Version 8.0 (October 8, 2025) - Current
- ✅ Dashboard upload navigation fixed
- ✅ Link components properly implemented
- ✅ Grid container wrapper added
- ✅ User experience improved

### Version 7.0 (October 5, 2025)
- ✅ Dark mode implementation
- ✅ Profile page complete
- ✅ Account deactivation flow
- ✅ Navigation enhancements

### Version 6.0 (October 4, 2025)
- ✅ Categories CRUD
- ✅ Settings page
- ✅ Dashboard updates

### Version 5.0 (October 3, 2025)
- ✅ Multilingual categories
- ✅ System settings
- ✅ Localization strings

### Version 4.0 (October 2, 2025)
- ✅ Initial production deployment
- ✅ Google OAuth
- ✅ Database schema

---

**Deployment Guide Version:** 8.0  
**Status:** Production-ready with active development  
**Last Verified:** October 8, 2025  
**Next Review:** October 15, 2025