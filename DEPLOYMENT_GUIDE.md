# Bonifatus DMS - Complete Deployment Guide v5.0

**Last Updated:** October 3, 2025  
**Production Status:** Operational  
**Domain:** https://bonidoc.com

---

## 📊 Current Deployment Status

### **✅ Operational Components**

#### **Infrastructure**
- ✅ Google Cloud Run (Backend & Frontend)
- ✅ Supabase PostgreSQL Database
- ✅ GitHub Actions CI/CD Pipeline
- ✅ Domain configured (bonidoc.com)
- ✅ SSL/TLS certificates active

#### **Backend Services**
- ✅ FastAPI application running
- ✅ Authentication system (Google OAuth + JWT)
- ✅ User management API
- ✅ Document management API
- ✅ Settings & localization API
- ✅ Google Drive integration
- ✅ Health monitoring endpoints

#### **Database**
- ✅ Complete schema deployed
- ✅ System settings populated
- ✅ Localization strings (EN, DE, RU)
- ✅ Default categories (Insurance, Legal, Real Estate, Banking, Other)
- ✅ Audit logging operational

#### **Frontend**
- ✅ Next.js 14 application
- ✅ Authentication flow
- ✅ Dashboard interface
- ✅ Responsive design

### **🚧 In Progress**

#### **Categories Management (Current Sprint)**
- ⏳ Categories API implementation
- ⏳ Categories service layer
- ⏳ Categories frontend page
- ⏳ Google Drive folder sync for categories

#### **Next Features (Upcoming)**
- ⏳ Document processing and OCR
- ⏳ AI-powered categorization
- ⏳ Advanced search functionality
- ⏳ Document sharing and collaboration

---

## 🌐 Production URLs

```
Frontend:     https://bonidoc.com
Backend API:  https://bonidoc.com/api (proxied)
API Docs:     https://bonidoc.com/docs
Health Check: https://bonidoc.com/health

Direct Backend URL: https://bonifatus-dms-vpm3xabjwq-uc.a.run.app
Direct Frontend URL: https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app
```

### **Domain Configuration**

The application is deployed on **bonidoc.com** with the following setup:
- Frontend served from root domain
- Backend API proxied through frontend
- SSL certificates managed by Cloud Run
- DNS configured to point to Cloud Run services

---

## ⚙️ Current Deployment Strategy

### **Direct Production Deployment**

**Current Approach:**
- All changes pushed to `main` branch deploy directly to production
- No separate development environment yet
- Rationale: Website not indexed by Google, low traffic during initial development

**Why This Works Now:**
- Rapid iteration during development phase
- Immediate feedback on production environment
- No user impact (pre-launch phase)
- Simplified workflow for solo/small team development

**Trade-offs:**
- No staging environment for testing
- Production is the testing ground
- Higher risk of breaking changes reaching users
- No environment parity testing

---

## 🔄 Future: Development Environment Setup

### **When to Implement Dev Environment**

Implement a development environment **before**:
- Public launch and Google indexing
- Significant user base (>100 active users)
- Team expansion (>2 developers)
- Critical business operations depend on uptime

### **Recommended Approach: Subdomain Strategy**

**Option 1: Subdomain for Development (Recommended)**

```
Production:   https://bonidoc.com
Development:  https://dev.bonidoc.com
Staging:      https://staging.bonidoc.com (optional)
```

**Advantages:**
- Clear separation between environments
- Same authentication domain
- Easy to remember and access
- Professional appearance
- Minimal DNS configuration

**Implementation:**

1. **Create Development Cloud Run Service**
   ```bash
   # Deploy dev backend
   gcloud run deploy bonifatus-dms-dev \
     --image us-central1-docker.pkg.dev/PROJECT/bonifatus-dms/backend:dev \
     --region=us-central1 \
     --set-env-vars "APP_ENVIRONMENT=development"
   
   # Deploy dev frontend
   gcloud run deploy bonifatus-dms-frontend-dev \
     --image us-central1-docker.pkg.dev/PROJECT/bonifatus-dms/frontend:dev \
     --region=us-central1 \
     --set-env-vars "NEXT_PUBLIC_API_URL=https://dev.bonidoc.com/api"
   ```

2. **Configure DNS**
   ```
   # Add A/AAAA records in your DNS provider
   dev.bonidoc.com → [Cloud Run IP for dev services]
   staging.bonidoc.com → [Cloud Run IP for staging services]
   ```

3. **Update GitHub Actions**
   ```yaml
   # .github/workflows/deploy-dev.yml
   on:
     push:
       branches: [develop]
   
   # .github/workflows/deploy-staging.yml
   on:
     push:
       branches: [staging]
   
   # .github/workflows/deploy-prod.yml
   on:
     push:
       branches: [main]
   ```

4. **Separate Databases**
   ```
   Production:   DATABASE_URL_PROD
   Development:  DATABASE_URL_DEV
   Staging:      DATABASE_URL_STAGING (copy of prod)
   ```

**Alternative Options:**

**Option 2: Environment-based Routing**
- Single domain with environment parameter
- https://bonidoc.com?env=dev
- Not recommended: confusing for users, harder to manage

**Option 3: Separate Domain**
- Different domain for development
- https://bonidoc-dev.com
- Not recommended: additional domain cost, more complex OAuth setup

**Option 4: Cloud Run Revisions with Traffic Splitting**
- Use Cloud Run traffic splitting
- 100% to latest for prod, manual traffic for testing
- Not recommended: complex, easy to make mistakes

---

## 🔐 Complete Setup Guide

### **Step 1: Configure GitHub Secrets**

Navigate to: `GitHub Repository → Settings → Secrets and variables → Actions`

#### **Required Secrets (43 Total)**

**Database Configuration (6 secrets)**
```yaml
DATABASE_URL: "postgresql://postgres.xxx:[PASSWORD]@xxx.supabase.co:5432/postgres"
DATABASE_POOL_SIZE: "10"
DATABASE_POOL_RECYCLE: "3600"
DATABASE_ECHO: "false"
DATABASE_POOL_PRE_PING: "true"
DATABASE_CONNECT_TIMEOUT: "60"
```

**Google Services (8 secrets)**
```yaml
GOOGLE_CLIENT_ID: "356302004293-xxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET: "GOCSPX-xxxxxxxxxxxxxxxxxxxx"
GOOGLE_REDIRECT_URI: "https://bonidoc.com/login"
GOOGLE_VISION_ENABLED: "true"
GOOGLE_OAUTH_ISSUERS: "https://accounts.google.com"
GOOGLE_DRIVE_FOLDER_NAME: "Bonifatus_DMS"
GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY: "/secrets/google-drive-key"
GCP_PROJECT: "bonifatus-dms-356302"
```

**Security Configuration (6 secrets)**
```yaml
SECURITY_SECRET_KEY: "generated-secret-key-here"
ALGORITHM: "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: "30"
REFRESH_TOKEN_EXPIRE_DAYS: "30"
DEFAULT_USER_TIER: "free"
ADMIN_EMAILS: "admin@bonidoc.com,admin2@bonidoc.com"
```

**Application Configuration (8 secrets)**
```yaml
APP_ENVIRONMENT: "production"
APP_DEBUG_MODE: "false"
APP_CORS_ORIGINS: "https://bonidoc.com"
APP_HOST: "0.0.0.0"
APP_PORT: "8080"
APP_TITLE: "Bonifatus DMS"
APP_DESCRIPTION: "Professional Document Management System"
APP_VERSION: "1.0.0"
```

**Cloud Run Configuration (6 secrets)**
```yaml
GCP_REGION: "us-central1"
CLOUD_RUN_SERVICE_NAME: "bonifatus-dms"
CLOUD_RUN_MEMORY: "2Gi"
CLOUD_RUN_CPU: "2"
CLOUD_RUN_MAX_INSTANCES: "10"
CLOUD_RUN_TIMEOUT: "300"
```

**Monitoring & Logging (2 secrets)**
```yaml
LOG_LEVEL: "INFO"
SENTRY_DSN: "https://xxx@sentry.io/xxx"  # Optional
```

**Frontend Configuration (2 secrets)**
```yaml
NEXT_PUBLIC_API_URL: "https://bonidoc.com/api"
NODE_ENV: "production"
```

**Deployment Secrets (5 secrets)**
```yaml
GCP_SA_KEY: |
  {
    "type": "service_account",
    "project_id": "bonifatus-dms-356302",
    "private_key_id": "xxx",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "client_email": "deploy@bonifatus-dms-356302.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
  }

DOCKER_REGISTRY: "us-central1-docker.pkg.dev"
ARTIFACT_REGISTRY_REPO: "bonifatus-dms"
GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY: "[JSON service account key]"
PORT: "8080"
```

### **Generate Security Secret**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### **Step 2: Setup Google Cloud Platform**

#### **2.1 Create GCP Project**
```bash
export PROJECT_ID="bonifatus-dms-356302"

gcloud projects create $PROJECT_ID --name="Bonifatus DMS"
gcloud config set project $PROJECT_ID

# Link billing account
gcloud billing projects link $PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT_ID
```

#### **2.2 Enable Required APIs**
```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  drive.googleapis.com \
  vision.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

#### **2.3 Create Service Account**
```bash
gcloud iam service-accounts create bonifatus-deploy \
  --description="Bonifatus DMS CI/CD Deployment" \
  --display-name="Bonifatus Deploy"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Generate key
gcloud iam service-accounts keys create key.json \
  --iam-account=bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com

cat key.json  # Add to GitHub Secrets as GCP_SA_KEY
```

#### **2.4 Create Artifact Registry**
```bash
gcloud artifacts repositories create bonifatus-dms \
  --repository-format=docker \
  --location=us-central1 \
  --description="Bonifatus DMS Docker images"
```

---

### **Step 3: Setup Database (Supabase)**

#### **3.1 Create Supabase Project**
```
1. Visit https://supabase.com
2. Click "New Project"
3. Enter details:
   - Name: bonifatus-dms
   - Database Password: [strong password]
   - Region: us-east-1 (or closest to users)
4. Wait for provisioning
```

#### **3.2 Get Connection String**
```
Settings → Database → Connection Pooling
Copy: postgresql://postgres.xxx:[PASSWORD]@xxx.supabase.co:5432/postgres
```

#### **3.3 Run Migrations**
```bash
cd backend
pip install -r requirements.txt

export DATABASE_URL="your-connection-string"

alembic upgrade head

# Verify
psql $DATABASE_URL -c "\dt"
```

---

### **Step 4: Configure Google OAuth**

#### **4.1 Create OAuth Credentials**
```
1. https://console.cloud.google.com
2. APIs & Services → Credentials
3. Create Credentials → OAuth 2.0 Client ID
4. Configure:
   - Application type: Web application
   - Name: Bonifatus DMS Production
   - Authorized JavaScript origins:
     * https://bonidoc.com
   - Authorized redirect URIs:
     * https://bonidoc.com/login
5. Copy Client ID and Client Secret
```

#### **4.2 Configure OAuth Consent Screen**
```
1. APIs & Services → OAuth consent screen
2. External user type
3. Fill required fields:
   - App name: Bonifatus DMS
   - User support email: support@bonidoc.com
   - Developer contact: dev@bonidoc.com
4. Add scopes:
   - .../auth/userinfo.email
   - .../auth/userinfo.profile
   - openid
5. Submit for verification (for production)
```

---

### **Step 5: Deploy to Production**

#### **5.1 Push to Main Branch**
```bash
git add .
git commit -m "feat: initial production deployment"
git push origin main
```

#### **5.2 Monitor Deployment**
```bash
# GitHub Actions
gh run list --workflow=deploy.yml
gh run watch

# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

#### **5.3 Configure Custom Domain**

**For Cloud Run:**
```bash
# Map domain to Cloud Run service
gcloud run domain-mappings create \
  --service=bonifatus-dms-frontend \
  --domain=bonidoc.com \
  --region=us-central1

# Get verification token
gcloud run domain-mappings describe \
  --domain=bonidoc.com \
  --region=us-central1
```

**DNS Configuration:**
```
# Add these records to your DNS provider (e.g., Google Domains, Cloudflare)

Type: A
Name: @
Value: [Cloud Run IP from domain-mappings]

Type: AAAA
Name: @
Value: [Cloud Run IPv6 from domain-mappings]

Type: CNAME
Name: www
Value: bonidoc.com
```

---

### **Step 6: Verify Deployment**

#### **6.1 Health Check**
```bash
curl https://bonidoc.com/health
# Expected: {"status": "healthy", "service": "bonifatus-dms"}
```

#### **6.2 OAuth Configuration**
```bash
curl https://bonidoc.com/api/v1/auth/google/config
# Expected: {"google_client_id": "...", "redirect_uri": "https://bonidoc.com/login"}
```

#### **6.3 API Documentation**
```
Visit: https://bonidoc.com/docs
Should display: Interactive Swagger UI
```

#### **6.4 End-to-End Test**
```
1. Visit: https://bonidoc.com
2. Click "Sign In with Google"
3. Authenticate
4. Verify redirect to /dashboard
5. Check localStorage for tokens
```

---

## 🔧 Local Development

### **7.1 Environment Variables (No .env files)**

```bash
# Create environment script (DO NOT COMMIT)
cat > set_env_vars.sh << 'EOF'
#!/bin/bash

# Database
export DATABASE_URL="postgresql://postgres.xxx:[PASSWORD]@xxx.supabase.co:5432/postgres"
export DATABASE_POOL_SIZE="10"
export DATABASE_POOL_RECYCLE="3600"
export DATABASE_ECHO="false"
export DATABASE_POOL_PRE_PING="true"
export DATABASE_CONNECT_TIMEOUT="60"

# Google Services
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:3000/login"
export GOOGLE_VISION_ENABLED="true"
export GOOGLE_OAUTH_ISSUERS="https://accounts.google.com"
export GOOGLE_DRIVE_FOLDER_NAME="Bonifatus_DMS"
export GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY="/path/to/key.json"
export GCP_PROJECT="bonifatus-dms-356302"

# Security
export SECURITY_SECRET_KEY="your-secret-key"
export ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES="30"
export REFRESH_TOKEN_EXPIRE_DAYS="30"
export DEFAULT_USER_TIER="free"
export ADMIN_EMAILS="admin@bonidoc.com"

# Application
export APP_ENVIRONMENT="development"
export APP_DEBUG_MODE="true"
export APP_CORS_ORIGINS="http://localhost:3000"
export APP_HOST="0.0.0.0"
export APP_PORT="8000"
export APP_TITLE="Bonifatus DMS"
export APP_DESCRIPTION="Professional Document Management System"
export APP_VERSION="1.0.0"

# Frontend
export NEXT_PUBLIC_API_URL="http://localhost:8000"
export NODE_ENV="development"
EOF

chmod +x set_env_vars.sh
echo "set_env_vars.sh" >> .gitignore
```

### **7.2 Run Backend Locally**
```bash
source set_env_vars.sh

cd backend
pip install -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Verify: http://localhost:8000/health
```

### **7.3 Run Frontend Locally**
```bash
source set_env_vars.sh

cd frontend
npm install
npm run dev

# Visit: http://localhost:3000
```

---

## 📊 Monitoring & Maintenance

### **View Logs**
```bash
# Backend logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=bonifatus-dms" \
  --limit 100 \
  --format json

# Frontend logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=bonifatus-dms-frontend" \
  --limit 100 \
  --format json

# Errors only
gcloud logging read "resource.type=cloud_run_revision AND \
  severity>=ERROR" \
  --limit 50
```

### **Update Environment Variables**
```bash
# Update backend
gcloud run services update bonifatus-dms \
  --region=us-central1 \
  --set-env-vars "LOG_LEVEL=DEBUG"

# Update frontend
gcloud run services update bonifatus-dms-frontend \
  --region=us-central1 \
  --set-env-vars "NEXT_PUBLIC_API_URL=https://bonidoc.com/api"
```

### **Rollback Deployment**
```bash
# List revisions
gcloud run revisions list \
  --service=bonifatus-dms \
  --region=us-central1

# Rollback to previous
gcloud run services update-traffic bonifatus-dms \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100
```

---

## 🚨 Troubleshooting

### **Common Issues**

#### **OAuth Redirect Mismatch**
```bash
# Problem: redirect_uri_mismatch error

# Solution 1: Verify redirect URI
curl https://bonidoc.com/api/v1/auth/google/config
# Should return: {"redirect_uri": "https://bonidoc.com/login"}

# Solution 2: Check Google Console
# Ensure authorized redirect URI is exactly: https://bonidoc.com/login

# Solution 3: Update GitHub Secret
# GOOGLE_REDIRECT_URI = "https://bonidoc.com/login"
```

#### **Database Connection Failed**
```bash
# Test connection
psql "your-database-url"

# Check environment variable
gcloud run services describe bonifatus-dms \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env)' \
  | grep DATABASE_URL
```

#### **Service Won't Start**
```bash
# View startup logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=bonifatus-dms" \
  --limit 100 \
  --format json | jq '.[] | select(.textPayload | contains("ERROR"))'

# Common causes:
# 1. Missing environment variable
# 2. Invalid environment variable format
# 3. Database migration not applied
# 4. Service account key issue
```

---

## 🎯 Next Steps (Current Sprint)

### **Immediate: Categories Management API**

**Files to Create:**
1. `backend/app/api/categories.py` - API endpoints
2. `backend/app/services/category_service.py` - Business logic
3. `backend/app/schemas/category_schemas.py` - Pydantic models

**Endpoints to Implement:**
- `GET /api/v1/categories` - List all categories
- `POST /api/v1/categories` - Create new category
- `PUT /api/v1/categories/{id}` - Update category
- `DELETE /api/v1/categories/{id}` - Delete category
- `POST /api/v1/categories/restore-defaults` - Recreate defaults
- `GET /api/v1/categories/{id}/documents-count` - Get document count

**Key Features:**
- All categories fully editable (no restrictions on system categories)
- Automatic Google Drive folder sync
- Multilingual support (EN, DE, RU)
- Document reassignment on category deletion

### **After Categories API:**

1. **Frontend Categories Page**
   - `frontend/src/app/categories/page.tsx`
   - Create/Edit/Delete UI
   - Google Drive sync status
   - Drag-and-drop reordering

2. **Document Processing**
   - OCR text extraction
   - Keyword extraction
   - Language detection

3. **AI Categorization**
   - Automatic category suggestion
   - Confidence scoring
   - User feedback loop

4. **Advanced Search**
   - Full-text search
   - Filters by category, date, language
   - Search suggestions

---

## 📞 Support & Resources

### **Production Monitoring**
- **Frontend**: https://bonidoc.com
- **Backend API**: https://bonidoc.com/api
- **API Docs**: https://bonidoc.com/docs
- **Health Check**: https://bonidoc.com/health

### **Cloud Resources**
- **GCP Console**: https://console.cloud.google.com
- **Supabase Dashboard**: https://supabase.com/dashboard
- **GitHub Actions**: https://github.com/yourusername/bonifatus-dms/actions

### **Key Commands**
```bash
# Service status
gcloud run services describe bonifatus-dms --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Update environment variable
gcloud run services update bonifatus-dms --set-env-vars "KEY=VALUE" --region=us-central1

# Force redeploy
git commit --allow-empty -m "redeploy" && git push

# Database migrations
cd backend && alembic upgrade head

# Health check
curl https://bonidoc.com/health
```

---

**Deployment Guide Version:** 5.0  
**Last Updated:** October 3, 2025  
**Status:** Production operational, categories API in development