# Bonifatus DMS - Production Deployment Guide v3.0

## **🌐 Production URLs**

```
Backend API:  https://bonifatus-dms-vpm3xabjwq-uc.a.run.app
Frontend App: https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app

API Docs:     https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/docs
Health Check: https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/health
```

---

## **📋 Prerequisites**

### **Required Accounts**
1. **Google Cloud Platform** - Project with billing enabled
2. **Supabase** - PostgreSQL database
3. **GitHub** - Repository with Actions enabled
4. **Google OAuth** - Configured client credentials

### **Required Tools**
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install GitHub CLI (optional)
brew install gh  # macOS
# OR
sudo apt install gh  # Linux
```

---

## **🎯 Production-Grade Standards & Philosophy**

### **Configuration Management**

**Core Principle:** Environment variables ONLY - NO hardcoded values, NO .env files

```
Production deployment = Environment variables from GitHub Secrets
Local development = Environment variables exported in shell session
Testing = Environment variables from CI/CD pipeline

NO .env files → NO hardcoded defaults → NO configuration drift
```

**What TO DO:**
- ✅ Store all configuration in GitHub Secrets
- ✅ Use environment variables in all environments  
- ✅ Fail fast if required variables are missing
- ✅ Document all required variables in this guide
- ✅ Use Secret Manager for sensitive data
- ✅ Export variables in shell for local development

**What NOT TO DO:**
- ❌ Create .env files in repository or locally
- ❌ Use hardcoded fallback values in code
- ❌ Commit sensitive information to git
- ❌ Mix development and production configs
- ❌ Assume default values exist anywhere

### **Deployment Standards**

**What TO DO:**
- ✅ Deploy via GitHub Actions only (automated)
- ✅ Use immutable Docker images
- ✅ Tag images with git SHA for traceability
- ✅ Enable automatic rollback on failure
- ✅ Monitor application health continuously
- ✅ Review all deployment logs

**What NOT TO DO:**
- ❌ Deploy manually from local machine
- ❌ Skip automated testing before deployment
- ❌ Deploy without code review
- ❌ Ignore deployment errors or warnings
- ❌ Skip post-deployment verification

### **Security Standards**

**What TO DO:**
- ✅ Rotate secrets regularly (quarterly minimum)
- ✅ Use least-privilege IAM roles
- ✅ Enable Cloud Run authentication
- ✅ Validate all environment variables on startup
- ✅ Use HTTPS only (no HTTP)
- ✅ Monitor security logs and alerts

**What NOT TO DO:**
- ❌ Share service account keys via email/chat
- ❌ Use default or weak passwords
- ❌ Expose debug endpoints in production
- ❌ Skip security updates
- ❌ Ignore security alerts from GCP

---

## **🔐 Step 1: Configure GitHub Secrets**

### **Navigate to Repository Settings**
```
GitHub Repository → Settings → Secrets and variables → Actions → New repository secret
```

### **Required Secrets (43 Total)**

#### **Database Configuration (6 secrets)**
```yaml
DATABASE_URL: "postgresql://user:pass@host:5432/db"
DATABASE_POOL_SIZE: "10"
DATABASE_POOL_RECYCLE: "3600"
DATABASE_ECHO: "false"
DATABASE_POOL_PRE_PING: "true"
DATABASE_CONNECT_TIMEOUT: "60"
```

#### **Google Services (8 secrets)**
```yaml
GOOGLE_CLIENT_ID: "356302004293-xxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET: "GOCSPX-xxxxxxxxxxxxxxxxxxxx"
GOOGLE_REDIRECT_URI: "https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app/login"
GOOGLE_VISION_ENABLED: "true"
GOOGLE_OAUTH_ISSUERS: "https://accounts.google.com"
GOOGLE_DRIVE_FOLDER_NAME: "Bonifatus_DMS"
GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY: "/secrets/google-drive-key"
GCP_PROJECT: "your-gcp-project-id"
```

#### **Security Configuration (6 secrets)**
```yaml
SECURITY_SECRET_KEY: "generated-secret-key-here"
ALGORITHM: "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: "30"
REFRESH_TOKEN_EXPIRE_DAYS: "30"
DEFAULT_USER_TIER: "free"
ADMIN_EMAILS: "admin@example.com,admin2@example.com"
```

#### **Application Configuration (8 secrets)**
```yaml
APP_ENVIRONMENT: "production"
APP_DEBUG_MODE: "false"
APP_CORS_ORIGINS: "*"
APP_HOST: "0.0.0.0"
APP_PORT: "8080"
APP_TITLE: "Bonifatus DMS"
APP_DESCRIPTION: "Professional Document Management System"
APP_VERSION: "1.0.0"
```

#### **Deployment Secrets (2 secrets)**
```yaml
GCP_SA_KEY: |
  {
    "type": "service_account",
    "project_id": "your-project",
    "private_key_id": "xxx",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "client_email": "deploy@project.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
  }

NEXT_PUBLIC_API_URL: "https://bonifatus-dms-vpm3xabjwq-uc.a.run.app"
```

### **Generate Security Secret**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## **☁️ Step 2: Setup Google Cloud Platform**

### **2.1 Create GCP Project**
```bash
# Set project ID
export PROJECT_ID="bonifatus-dms-356302"

# Create project
gcloud projects create $PROJECT_ID --name="Bonifatus DMS"

# Set as active project
gcloud config set project $PROJECT_ID

# Link billing account (required for Cloud Run)
gcloud billing projects link $PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### **2.2 Enable Required APIs**
```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  drive.googleapis.com \
  vision.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

### **2.3 Create Service Account for Deployment**
```bash
# Create service account
gcloud iam service-accounts create bonifatus-deploy \
  --description="Bonifatus DMS CI/CD Deployment" \
  --display-name="Bonifatus Deploy"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Generate and download key
gcloud iam service-accounts keys create key.json \
  --iam-account=bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com

# Add to GitHub Secrets as GCP_SA_KEY (copy entire JSON contents)
cat key.json
```

### **2.4 Create Artifact Registry**
```bash
gcloud artifacts repositories create bonifatus-dms \
  --repository-format=docker \
  --location=us-central1 \
  --description="Bonifatus DMS container images"
```

### **2.5 Create Secret for Google Drive Service Account**
```bash
# Create service account for Google Drive access
gcloud iam service-accounts create bonifatus-drive \
  --description="Bonifatus DMS Google Drive Access" \
  --display-name="Bonifatus Drive"

# Generate key
gcloud iam service-accounts keys create drive-key.json \
  --iam-account=bonifatus-drive@$PROJECT_ID.iam.gserviceaccount.com

# Store in Secret Manager
gcloud secrets create bonifatus-drive-service-key \
  --data-file=drive-key.json \
  --replication-policy=automatic

# Grant Cloud Run service account access to secret
gcloud secrets add-iam-policy-binding bonifatus-drive-service-key \
  --member="serviceAccount:bonifatus-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## **🗄️ Step 3: Setup Supabase Database**

### **3.1 Create Supabase Project**
```
1. Visit https://supabase.com/dashboard
2. Click "New Project"
3. Enter details:
   - Name: bonifatus-dms
   - Database Password: (generate strong password)
   - Region: (choose closest to Cloud Run region)
4. Wait for provisioning (2-3 minutes)
```

### **3.2 Get Connection String**
```
1. Go to Project Settings → Database
2. Copy "Connection string" under "Connection pooling"
3. Replace [YOUR-PASSWORD] with your database password
4. Add to GitHub Secrets as DATABASE_URL
```

### **3.3 Initialize Database Schema**
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/bonifatus-dms.git
cd bonifatus-dms/backend

# Install dependencies
pip install -r requirements.txt

# Run migrations (requires DATABASE_URL environment variable)
export DATABASE_URL="your-supabase-connection-string"
alembic upgrade head
```

---

## **🔒 Step 4: Configure Google OAuth**

### **4.1 Create OAuth Credentials**
```
1. Visit https://console.cloud.google.com
2. Select your project
3. Navigate to: APIs & Services → Credentials
4. Click "Create Credentials" → "OAuth 2.0 Client ID"
5. Configure:
   - Application type: Web application
   - Name: Bonifatus DMS Production
   - Authorized JavaScript origins:
     * https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app
   - Authorized redirect URIs:
     * https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app/login
6. Click "Create"
7. Copy Client ID and Client Secret
```

### **4.2 Add to GitHub Secrets**
```yaml
GOOGLE_CLIENT_ID: "from-step-4.1"
GOOGLE_CLIENT_SECRET: "from-step-4.1"
GOOGLE_REDIRECT_URI: "https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app/login"
```

### **4.3 Configure OAuth Consent Screen**
```
1. APIs & Services → OAuth consent screen
2. Select "External" user type
3. Fill required fields:
   - App name: Bonifatus DMS
   - User support email: your-email@domain.com
   - Developer contact: your-email@domain.com
4. Add scopes:
   - .../auth/userinfo.email
   - .../auth/userinfo.profile
   - openid
5. Add test users (for development)
6. Submit for verification (for production)
```

---

## **🚀 Step 5: Deploy to Production**

### **5.1 Verify GitHub Actions Workflow**

Check `.github/workflows/deploy.yml` contains:
```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
  # ... all other environment variables from secrets
```

### **5.2 Deploy via Git Push**
```bash
# Ensure all changes are committed
git add .
git commit -m "feat: production deployment configuration"

# Push to trigger deployment
git push origin main

# Monitor deployment
gh workflow view deploy --web
# OR visit: https://github.com/YOUR_USERNAME/bonifatus-dms/actions
```

### **5.3 Monitor Deployment**
```bash
# View GitHub Actions logs
gh run list --workflow=deploy.yml
gh run view <RUN_ID> --log

# Check Cloud Run service
gcloud run services describe bonifatus-dms \
  --region=us-central1 \
  --format='value(status.url)'
```

---

## **✅ Step 6: Verify Deployment**

### **6.1 Automated Testing**
```bash
# Run deployment tests for backend
cd backend
python test_config.py https://bonifatus-dms-vpm3xabjwq-uc.a.run.app
```

### **6.2 Manual Testing**

#### **Health Check**
```bash
curl https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/health
# Expected: {"status": "healthy"}
```

#### **OAuth Configuration**
```bash
curl https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/api/v1/auth/google/config
# Expected: {"google_client_id": "...", "redirect_uri": "..."}
```

#### **API Documentation**
```
Visit: https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/docs
Should display: Interactive Swagger UI
```

#### **Frontend Application**
```
Visit: https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app
Should display: Landing page with "Sign In with Google" button
```

### **6.3 End-to-End OAuth Flow**
```
1. Visit: https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app
2. Click "Sign In with Google"
3. Select Google account
4. Grant permissions
5. Should redirect to /login with code
6. Should exchange code for JWT tokens
7. Should redirect to /dashboard
8. Verify tokens in localStorage
```

---

## **🔧 Step 7: Local Development Setup**

### **7.1 Use Production Environment Variables**

**NEVER create .env files.** Instead, export production variables locally:

```bash
# Create a script to export variables (DO NOT COMMIT)
cat > set_env_vars.sh << 'EOF'
#!/bin/bash
export DATABASE_URL="your-production-db-url"
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:3000/login"
export SECURITY_SECRET_KEY="your-secret-key"
export APP_ENVIRONMENT="development"
export APP_DEBUG_MODE="true"
export APP_CORS_ORIGINS="http://localhost:3000"
export APP_HOST="0.0.0.0"
export APP_PORT="8000"
export APP_TITLE="Bonifatus DMS"
export APP_DESCRIPTION="Professional Document Management System"
export APP_VERSION="1.0.0"
# ... add all other required variables
EOF

chmod +x set_env_vars.sh

# Add to .gitignore
echo "set_env_vars.sh" >> .gitignore
```

### **7.2 Run Backend Locally**
```bash
# Source environment variables
source set_env_vars.sh

# Start backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Verify
curl http://localhost:8000/health
```

### **7.3 Run Frontend Locally**
```bash
# Export frontend env var (point to production backend OR local backend)
export NEXT_PUBLIC_API_URL="https://bonifatus-dms-vpm3xabjwq-uc.a.run.app"
# OR for local backend:
# export NEXT_PUBLIC_API_URL="http://localhost:8000"

# Start frontend
cd frontend
npm run dev

# Visit http://localhost:3000
```

---

## **📊 Monitoring & Maintenance**

### **View Cloud Run Logs**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=bonifatus-dms" \
  --limit 50 \
  --format json
```

### **View Application Metrics**
```bash
# CPU utilization
gcloud monitoring timeseries list \
  --filter='metric.type="run.googleapis.com/container/cpu/utilizations"' \
  --format=json

# Request count
gcloud monitoring timeseries list \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --format=json
```

### **Update Environment Variables**
```bash
# Update single variable
gcloud run services update bonifatus-dms \
  --region=us-central1 \
  --set-env-vars "APP_DEBUG_MODE=false"

# Update multiple variables
gcloud run services update bonifatus-dms \
  --region=us-central1 \
  --set-env-vars "VAR1=value1,VAR2=value2"
```

---

## **🚨 Troubleshooting**

### **Deployment Fails - Missing Environment Variables**
```bash
# Check GitHub Secrets are set
gh secret list

# Verify workflow uses secrets correctly
cat .github/workflows/deploy.yml | grep secrets

# Check Cloud Run service environment variables
gcloud run services describe bonifatus-dms \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env)'
```

### **OAuth Authentication Fails**
```bash
# Verify redirect URI matches (should return frontend URL)
curl https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/api/v1/auth/google/config
# Expected: {"redirect_uri": "https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app/login"}

# Check Google Cloud Console OAuth configuration
# Ensure redirect URI in Google Console matches:
# https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app/login

# Update GitHub Secret if needed
# GitHub → Settings → Secrets → GOOGLE_REDIRECT_URI
# Value: https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app/login

# Force new deployment to apply changes
git commit --allow-empty -m "redeploy: force refresh environment variables"
git push origin main
```

### **Database Connection Fails**
```bash
# Test connection string
psql "your-database-url"

# Check Cloud Run service has correct DATABASE_URL
gcloud run services describe bonifatus-dms \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env)' | grep DATABASE_URL

# Update if needed
gcloud run services update bonifatus-dms \
  --region=us-central1 \
  --set-env-vars "DATABASE_URL=new-connection-string"
```

### **Application Won't Start**
```bash
# View startup logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=bonifatus-dms" \
  --limit 100 \
  --format json | jq '.[] | select(.textPayload | contains("ERROR"))'

# Common issues:
# 1. Missing required environment variable → Add to GitHub Secrets
# 2. Invalid environment variable value → Validate format
# 3. Database migration needed → Run: alembic upgrade head
```

---

## **🔄 Continuous Deployment Workflow**

### **Standard Development Cycle**
```bash
# 1. Make code changes
vim backend/app/api/new_feature.py

# 2. Test locally with production env vars
source set_env_vars.sh
uvicorn app.main:app --reload

# 3. Commit changes
git add .
git commit -m "feat: add new feature"

# 4. Push to trigger deployment
git push origin main

# 5. Monitor deployment
gh run watch

# 6. Verify backend in production
curl https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/api/v1/new-endpoint

# 7. Verify frontend in production
# Visit: https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app

# 8. Run full test suite
python backend/test_config.py https://bonifatus-dms-vpm3xabjwq-uc.a.run.app
```

### **Emergency Rollback**
```bash
# List recent backend revisions
gcloud run revisions list \
  --service=bonifatus-dms \
  --region=us-central1

# Rollback backend to previous revision
gcloud run services update-traffic bonifatus-dms \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100

# List recent frontend revisions
gcloud run revisions list \
  --service=bonifatus-dms-frontend \
  --region=us-central1

# Rollback frontend to previous revision
gcloud run services update-traffic bonifatus-dms-frontend \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100
```

---

## **📋 Deployment Checklist**

### **Before First Deployment**
- [ ] All 43 GitHub Secrets configured
- [ ] GCP project created and billing enabled
- [ ] All GCP APIs enabled
- [ ] Service accounts created with correct permissions
- [ ] Artifact Registry repository created
- [ ] Supabase database created and initialized
- [ ] Google OAuth credentials configured
- [ ] OAuth consent screen configured
- [ ] Test users added (for development)

### **Before Each Deployment**
- [ ] Code passes local tests
- [ ] All required environment variables present in workflow
- [ ] No hardcoded values in code
- [ ] No .env files committed to repository
- [ ] Database migrations prepared (if needed)
- [ ] Breaking changes documented

### **After Deployment**
- [ ] Automated tests pass (`python test_config.py <URL>`)
- [ ] Health endpoint returns 200
- [ ] OAuth configuration endpoint accessible
- [ ] API documentation loads
- [ ] End-to-end OAuth flow works
- [ ] Application logs show no errors
- [ ] Database connections successful

---

## **📞 Support & Resources**

### **Official Documentation**
- Google Cloud Run: https://cloud.google.com/run/docs
- Supabase: https://supabase.com/docs
- GitHub Actions: https://docs.github.com/actions

### **Monitoring URLs**
- Production Backend API: https://bonifatus-dms-vpm3xabjwq-uc.a.run.app
- Production Frontend App: https://bonifatus-dms-frontend-vpm3xabjwq-uc.a.run.app
- API Documentation: https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/docs
- API Health Check: https://bonifatus-dms-vpm3xabjwq-uc.a.run.app/health

### **Key Commands Reference**
```bash
# View backend service status
gcloud run services describe bonifatus-dms --region=us-central1

# View frontend service status
gcloud run services describe bonifatus-dms-frontend --region=us-central1

# View logs (backend)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=bonifatus-dms" --limit 50

# View logs (frontend)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=bonifatus-dms-frontend" --limit 50

# Update env var (backend)
gcloud run services update bonifatus-dms --set-env-vars "KEY=VALUE" --region=us-central1

# Update env var (frontend)
gcloud run services update bonifatus-dms-frontend --set-env-vars "KEY=VALUE" --region=us-central1

# Force deployment
git commit --allow-empty -m "redeploy" && git push

# Test backend deployment
python backend/test_config.py https://bonifatus-dms-vpm3xabjwq-uc.a.run.app

# Get backend URL
gcloud run services describe bonifatus-dms --region=us-central1 --format='value(status.url)'

# Get frontend URL
gcloud run services describe bonifatus-dms-frontend --region=us-central1 --format='value(status.url)'
```

---

**Last Updated:** September 30, 2025  
**Version:** 3.0  
**Status:** Production Ready ✅