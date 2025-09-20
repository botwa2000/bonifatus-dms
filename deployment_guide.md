# Bonifatus DMS - Production-Grade Deployment Guide

## 🎯 **Deployment Philosophy**

**One Feature at a Time**  
Each deployment step builds a **single, complete, tested feature** before moving to the next.

**Production Standards Only**  
- No hardcoded values (including helper words)
- No workarounds or temporary solutions  
- Every fix includes precise location indicators
- Black formatting enforced before each commit
- All configuration loaded from database/environment

---

## 📋 **Deployment Sequence** 

### **Phase 1: Foundation (Days 1-2)**
1. **Core Infrastructure** - Database connection, health checks, configuration management
2. **Database Schema** - Core models, migrations, schema validation
3. **Configuration Service** - Database-driven configuration system

### **Phase 2: User System (Days 3-4)**  
4. **User Authentication** - JWT tokens, user model, basic auth
5. **User Management** - Registration, profiles, user services
6. **Tier System** - User tiers, limits, subscription management

### **Phase 3: External Integration (Days 5-6)**
7. **Google OAuth** - OAuth flow, token management
8. **Google Drive API** - Drive connection, folder management
9. **Security Layer** - Rate limiting, CORS, validation

### **Phase 4: Document System (Days 7-9)**
10. **Document Models** - Document schema, status management
11. **File Upload** - Upload handling, validation, processing
12. **Document Storage** - Google Drive integration, metadata management

### **Phase 5: Intelligence (Days 10-12)**
13. **Category System** - Dynamic categories from database
14. **Document Processing** - Text extraction, keyword analysis  
15. **AI Categorization** - Machine learning categorization

### **Phase 6: Search & Discovery (Days 13-14)**
16. **Search Engine** - Full-text search, filtering
17. **Advanced Features** - Favorites, bulk operations, analytics

---

## ⚙️ **Fix Implementation Protocol**

### **Step-by-Step Process for Each Fix:**

1. **Identify Issue** - Clear problem statement
2. **Locate Code** - Exact file and function location
3. **Implement Fix** - Precise before/after line indicators
4. **Format Code** - Run `black --line-length=88 filename.py`
5. **Test Fix** - Verify functionality works
6. **Commit & Deploy** - Single commit per feature
7. **Validate Production** - Test in deployed environment

### **Fix Location Format:**
```
File: backend/src/path/to/file.py
Function: function_name()
Location: Line X (after "previous code line")

BEFORE:
existing_code_here

REPLACE WITH:
new_code_here

AFTER:
next_code_line
```

---

## 🔧 **Configuration Standards**

### **Environment Variables (.env)**
```bash
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres

# Authentication 
SECURITY_SECRET_KEY=[generated-secret-32-chars]
GOOGLE_CLIENT_ID=[google-oauth-client-id]
GOOGLE_CLIENT_SECRET=[google-oauth-client-secret]

# Application
APP_ENVIRONMENT=production
APP_DEBUG_MODE=false

# Google Cloud Platform
GCP_PROJECT=[your-gcp-project-id]
GCP_REGION=us-central1
GCP_SERVICE_NAME=bonifatus-dms-api
```

### **GitHub Secrets (Required)**
```
DATABASE_URL - Supabase connection string
SECURITY_SECRET_KEY - JWT secret key  
GOOGLE_CLIENT_ID - Google OAuth client ID
GOOGLE_CLIENT_SECRET - Google OAuth client secret
GCP_SA_KEY - Complete Google service account JSON key
```

---

## 🚀 **Deployment Phase 1: Core Infrastructure**

### **Feature 1.1: Database Connection**

**Objective:** Establish clean Supabase PostgreSQL connection with health checks

**Files to Create:**
- `backend/src/core/config.py` - Configuration management
- `backend/src/database/connection.py` - Database connection manager
- `backend/src/main.py` - FastAPI application with health endpoint

**Acceptance Criteria:**
- [ ] Health endpoint returns 200 OK
- [ ] Database connection established without hardcoded values
- [ ] Configuration loaded from environment variables
- [ ] No fallback or workaround code

**Implementation Steps:**

1. **Create Configuration Manager**
   ```
   File: backend/src/core/config.py  
   Location: New file
   
   Implementation: Complete Pydantic settings with database, security, and app configuration sections
   Test: `python -c "from src.core.config import settings; print(settings.database.database_url)"`
   ```

2. **Create Database Manager**
   ```
   File: backend/src/database/connection.py
   Location: New file
   
   Implementation: SQLAlchemy engine with connection pooling, health checks
   Test: `python -c "from src.database.connection import db_manager; print(db_manager.health_check())"`
   ```

3. **Create Main Application**  
   ```
   File: backend/src/main.py
   Location: New file
   
   Implementation: FastAPI app with health endpoint, CORS, exception handling
   Test: `uvicorn src.main:app --reload` → Visit http://localhost:8000/health
   ```

**Deployment Test:**
```bash
# Format code
black --line-length=88 backend/src/

# Commit feature
git add backend/src/core/config.py backend/src/database/connection.py backend/src/main.py
git commit -m "feat: core infrastructure with database connection

- Add Pydantic configuration management
- Add SQLAlchemy database connection manager  
- Add FastAPI application with health endpoint
- Zero hardcoded values, production-ready"

# Deploy
git push origin main

# Verify deployment
curl https://your-app.run.app/health
# Expected: {"status":"healthy","database":"connected"}
```

### **Feature 1.2: Database Schema Foundation**

**Objective:** Create core database models and migration system

**Files to Create:**
- `backend/src/database/models.py` - SQLAlchemy models
- `backend/alembic.ini` - Database migration configuration
- `backend/alembic/env.py` - Migration environment

**Implementation Location:**
```
File: backend/src/database/models.py
Location: New file (after connection.py completion)

IMPLEMENTATION:
- User model (id, email, google_id, tier, timestamps)  
- Category model (id, name_en, name_de, user_id, is_system)
- SystemSettings model (configuration from database)
- Base class with proper relationships

TEST COMMAND:
python -c "from src.database.models import User, Category; print('Models imported successfully')"
```

**No Hardcoded Data Rule:**
- No default categories in code
- No hardcoded text strings
- All defaults come from database queries or environment variables

---

## 📝 **Quality Gates for Each Phase**

### **Before Moving to Next Feature:**
1. **✅ Code Quality**
   - Black formatting: `black --check --line-length=88 backend/src/`
   - No import errors: `python -c "import sys; sys.path.append('backend'); from src.main import app"`
   - No syntax errors: `python -m py_compile backend/src/**/*.py`

2. **✅ Functionality**  
   - Health endpoint responds correctly
   - Database connection established
   - No error logs in application startup

3. **✅ Production Readiness**
   - Environment variables properly configured
   - No hardcoded values in source code
   - Proper error handling and logging

4. **✅ Deployment Success**
   - GitHub Actions pipeline passes
   - Cloud Run deployment successful
   - Production health check passes

### **Phase Completion Checklist:**
- [ ] All features in phase deployed and tested
- [ ] No failing tests or linting issues  
- [ ] Production environment verified working
- [ ] Documentation updated
- [ ] Ready for next phase

---

## 🔄 **Continuous Integration Pipeline**

### **GitHub Actions Workflow:**
1. **Code Quality** - Black formatting, linting
2. **Testing** - Unit tests, integration tests
3. **Build** - Docker image creation
4. **Deploy** - Google Cloud Run deployment
5. **Verify** - Health check and smoke tests

### **Failure Protocol:**
If any step fails:
1. **Stop immediately** - Do not proceed to next feature
2. **Analyze failure** - Identify root cause  
3. **Implement fix** - Single-purpose fix commit
4. **Re-validate** - Ensure fix resolves issue
5. **Continue** - Only after complete success

---

This methodical approach ensures each feature is production-ready before moving forward, eliminating the accumulation of technical debt and configuration issues.