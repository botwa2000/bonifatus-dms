# Bonifatus DMS - Production Document Management System

[![Deploy to Cloud Run](https://github.com/botwa2000/bonifatus-dms/actions/workflows/deploy.yml/badge.svg)](https://github.com/botwa2000/bonifatus-dms/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)

**Production URL:** [https://bonidoc.com](https://bonidoc.com)  
**API Documentation:** [https://bonidoc.com/docs](https://bonidoc.com/docs)  
**Status:** ✅ Fully Operational

---

## 🎯 Project Overview

Bonifatus DMS is a **production-grade, AI-powered document management system** built with modern technologies and enterprise-level architecture. The system provides intelligent document organization, Google Drive integration, and multilingual support.

### **Core Features**

#### ✅ **Implemented & Operational**
- **🔐 Google OAuth 2.0 Authentication** - Secure passwordless login
- **👤 User Management** - Profile, preferences, account deactivation
- **📁 Dynamic Category System** - Multilingual categories (EN/DE/RU)
- **🎨 Theme Support** - Light/dark mode with localStorage persistence
- **🌍 Multilingual Interface** - English, German, Russian
- **☁️ Google Drive Integration** - Backend infrastructure ready
- **📊 User Dashboard** - Trial status, statistics, quick actions
- **⚙️ Settings Management** - Theme, language, timezone, notifications
- **🔍 Category Management** - Full CRUD, translations, restore defaults
- **📱 Responsive Design** - Mobile, tablet, desktop optimization
- **🎭 User Tiers** - Free, Premium Trial, Premium, Enterprise
- **📝 Audit Logging** - Complete user action tracking

#### ⏳ **In Development**
- **📤 Document Upload** - UI complete, backend processing in progress
- **🔎 Advanced Search** - Full-text search with filters
- **🤖 AI Categorization** - Intelligent document classification
- **📄 OCR Processing** - Text extraction from PDFs and images

#### 📋 **Planned Features**
- **🤝 Document Sharing** - Collaborative access control
- **📦 Collections** - Folder organization system
- **🔔 Notifications** - Real-time activity alerts
- **📈 Analytics** - Usage statistics and insights

---

## 🏗️ Architecture & Technology Stack

### **System Architecture**
```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Frontend       │    │   Backend API    │    │   Database       │
│   Next.js 15.5   │◄──►│   FastAPI 0.104  │◄──►│   PostgreSQL 15  │
│   React 18       │    │   Python 3.11    │    │   Supabase       │
│   TypeScript     │    │   SQLAlchemy 2.0 │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  OAuth 2.0       │    │  Google APIs     │    │  Cloud Storage   │
│  JWT Tokens      │    │  Drive, Vision   │    │  Google Drive    │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

### **Technology Stack**

#### **Frontend**
```json
{
  "framework": "Next.js 15.5.3",
  "runtime": "React 18.3.1",
  "language": "TypeScript 5.7.3",
  "styling": "Tailwind CSS 3.4.17",
  "state": "React Context API",
  "http": "Native Fetch API"
}
```

#### **Backend**
```python
{
  "framework": "FastAPI 0.104.1",
  "language": "Python 3.11 (prod), 3.13 (local dev)",
  "server": "Uvicorn 0.24.0",
  "orm": "SQLAlchemy 2.0.23",
  "db_driver": "psycopg2-binary 2.9.9 (prod), psycopg 3.x (dev)",
  "validation": "Pydantic 2.11.10+",
  "auth": "PyJWT 2.8.0, python-jose 3.3.0"
}
```

#### **Infrastructure**
- **Hosting:** Google Cloud Run (us-central1)
- **Database:** Supabase PostgreSQL (managed)
- **CI/CD:** GitHub Actions
- **DNS:** Google Cloud DNS  
- **SSL:** Automatic via Cloud Run

#### **Development Tools**
- **IDE:** Visual Studio Code
- **Version Control:** Git + GitHub
- **API Testing:** Swagger UI (auto-generated)
- **Database Client:** Supabase Dashboard

---

## 🚀 Quick Start

### **Prerequisites**

**For Local Development:**
- Python 3.13.7 or higher
- Node.js 22.14.0 or higher
- Git 2.49.0 or higher
- PostgreSQL access (Supabase account)
- Google Cloud project with OAuth credentials

**For Production Deployment:**
- GitHub account
- Google Cloud Platform account
- Supabase account
- Domain name (optional)

### **Local Development Setup**

#### **1. Clone Repository**
```bash
git clone https://github.com/botwa2000/bonifatus-dms.git
cd bonifatus-dms
```

#### **2. Backend Setup**

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Upgrade pydantic first (Python 3.13 compatibility)
pip install "pydantic>=2.11.10"

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials
```

**Backend .env Configuration:**
```bash
# Database (Supabase)
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db

# Security
SECURITY_SECRET_KEY=generate-with-python-secrets
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/login

# Application
APP_ENVIRONMENT=development
APP_DEBUG_MODE=true
APP_CORS_ORIGINS=http://localhost:3000
```

**Generate Secret Key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Run Database Migrations:**
```bash
alembic upgrade head
```

**Start Backend:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access API Documentation:** http://localhost:8000/docs

#### **3. Frontend Setup**

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file
cp .env.example .env.local
# Edit .env.local
```

**Frontend .env.local Configuration:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Start Frontend:**
```bash
npm run dev
```

**Access Application:** http://localhost:3000

### **Production Deployment**

#### **1. Setup Google Cloud**

```bash
# Enable required APIs
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  drive.googleapis.com

# Create service account
gcloud iam service-accounts create bonifatus-deploy \
  --description="Bonifatus DMS Deployment" \
  --display-name="Bonifatus Deploy"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
  --member="serviceAccount:bonifatus-deploy@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Generate service account key
gcloud iam service-accounts keys create key.json \
  --iam-account=bonifatus-deploy@YOUR-PROJECT-ID.iam.gserviceaccount.com
```

#### **2. Configure GitHub Secrets**

Navigate to: `Repository Settings → Secrets and Variables → Actions`

**Required Secrets:**

| Secret Name | Description | How to Obtain |
|-------------|-------------|---------------|
| `DATABASE_URL` | PostgreSQL connection string | Supabase Dashboard → Settings → Database |
| `SECURITY_SECRET_KEY` | JWT signing key | Generate with Python secrets module |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID | Google Cloud Console → Credentials |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 secret | Google Cloud Console → Credentials |
| `GCP_SA_KEY` | Service account JSON key | Created in step 1 above |
| `GCP_PROJECT` | Google Cloud project ID | Google Cloud Console |

#### **3. Deploy**

```bash
# Push to main branch triggers automatic deployment
git push origin main

# Monitor deployment
# Visit: https://github.com/your-repo/actions

# Verify deployment
curl https://your-domain.com/health
```

---

## 📚 API Documentation

### **Authentication Endpoints**
```
GET  /api/v1/auth/google/config      - OAuth configuration
GET  /api/v1/auth/google/login       - Initiate Google login
POST /api/v1/auth/google/callback    - OAuth callback
POST /api/v1/auth/refresh            - Refresh JWT token
GET  /api/v1/auth/me                 - Current user info
DELETE /api/v1/auth/logout           - Logout user
```

### **User Management Endpoints**
```
GET  /api/v1/users/profile           - User profile
PUT  /api/v1/users/profile           - Update profile
GET  /api/v1/users/statistics        - User statistics
GET  /api/v1/users/preferences       - User preferences
PUT  /api/v1/users/preferences       - Update preferences
POST /api/v1/users/preferences/reset - Reset to defaults
GET  /api/v1/users/dashboard         - Dashboard data
POST /api/v1/users/deactivate        - Deactivate account
```

### **Category Endpoints**
```
GET    /api/v1/categories            - List categories
POST   /api/v1/categories            - Create category
PUT    /api/v1/categories/{id}       - Update category
DELETE /api/v1/categories/{id}       - Delete category
POST   /api/v1/categories/restore-defaults - Restore system defaults
```

### **Settings Endpoints**
```
GET /api/v1/settings/public                    - Public settings
GET /api/v1/settings/localization/{language}   - Localized strings
GET /api/v1/settings/localization              - All localizations
```

### **Document Endpoints** (In Development)
```
POST   /api/v1/documents/upload      - Upload document
GET    /api/v1/documents              - List documents
GET    /api/v1/documents/{id}         - Document details
PUT    /api/v1/documents/{id}         - Update document
DELETE /api/v1/documents/{id}         - Delete document
GET    /api/v1/documents/{id}/download - Download document
```

**Interactive API Documentation:** https://bonidoc.com/docs

---

## 🗄️ Database Schema

### **Core Tables (20 Total)**

#### **Authentication & Users**
- `users` - User accounts and profiles
- `user_settings` - User preferences and configuration
- `audit_logs` - Complete action tracking

#### **Categories**
- `categories` - Category definitions with codes
- `category_translations` - Multilingual category names

#### **Documents** (Schema Ready)
- `documents` - Document metadata
- `document_languages` - Multi-language document tracking
- `document_keywords` - Extracted keywords
- `document_entities` - Named entity recognition

#### **System Configuration**
- `system_settings` - Application-wide settings
- `localization_strings` - UI translations
- `user_storage_quotas` - Storage limits by tier

#### **Advanced Features** (Planned)
- `keywords` - Keyword dictionary
- `collections` - Document folders
- `tags` - Custom tags
- `shared_documents` - Sharing permissions
- `ocr_results` - OCR processing results
- `ai_processing_queue` - Background job queue

---

## 🔧 Development Methodology

### **Code Quality Standards**

✅ **Zero Hardcoded Values** - All configuration database-driven  
✅ **Modular Architecture** - Files <300 lines, single responsibility  
✅ **Production-Ready Only** - No TODO, FIXME, or workarounds  
✅ **Type Safety** - Full TypeScript + Pydantic validation  
✅ **Error Handling** - Comprehensive try-catch blocks  
✅ **Documentation** - Function docstrings and inline comments  

### **Development Workflow**

```bash
# 1. Pull latest changes
git pull origin main

# 2. Create feature branch (optional)
git checkout -b feature/feature-name

# 3. Make changes in VS Code

# 4. Test locally
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:3000

# 5. Commit with descriptive message
git add .
git commit -m "feat: add feature description

- Bullet point 1
- Bullet point 2
- Production-ready implementation"

# 6. Push to main (triggers auto-deployment)
git push origin main

# 7. Monitor GitHub Actions
# Visit: https://github.com/botwa2000/bonifatus-dms/actions

# 8. Verify production
curl https://bonidoc.com/health
```

### **Testing Checklist**

Before every commit:
- [ ] Code formatted (Black for Python, Prettier for TypeScript)
- [ ] No linting errors
- [ ] Manual testing completed
- [ ] All CRUD operations verified
- [ ] Mobile responsive checked
- [ ] Error handling tested
- [ ] No console errors

---

## 📁 Project Structure

```
bonifatus-dms/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Configuration
│   │   ├── database/      # DB connection & models
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── main.py        # FastAPI application
│   ├── alembic/           # Database migrations
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Backend container
│
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   ├── contexts/      # React contexts
│   │   ├── hooks/         # Custom hooks
│   │   ├── services/      # API clients
│   │   └── types/         # TypeScript types
│   ├── package.json       # Node dependencies
│   └── Dockerfile         # Frontend container
│
├── .github/
│   └── workflows/
│       └── deploy.yml     # CI/CD pipeline
│
├── README.md              # This file
├── DEPLOYMENT_GUIDE.md    # Deployment documentation
└── DEVELOPMENT_GUIDE_VS.md # Development guide
```

---

## 🔐 Security Features

- **OAuth 2.0** - Secure authentication via Google
- **JWT Tokens** - Short-lived access tokens (60 min)
- **Refresh Tokens** - Long-lived refresh capability (7 days)
- **HTTPS Only** - All traffic encrypted
- **CORS Protection** - Restricted origins
- **Input Validation** - Pydantic schemas
- **SQL Injection Prevention** - ORM parameterized queries
- **XSS Protection** - React built-in escaping
- **Audit Logging** - Complete action tracking
- **Rate Limiting** - API protection (planned)

---

## 🌍 Multilingual Support

**Supported Languages:**
- 🇬🇧 English (en)
- 🇩🇪 German (de)
- 🇷🇺 Russian (ru)

**Localized Components:**
- UI labels and buttons
- Error messages
- Notification texts
- Category names
- System messages

**Adding New Languages:**
1. Add language code to `system_settings.available_languages`
2. Add translations to `localization_strings` table
3. Create category translations in `category_translations`
4. Update frontend language selector

---

## 📊 Performance Metrics

**Current Production Performance:**
- API Response Time: <200ms (avg)
- Page Load Time: <1.5s
- Time to Interactive: <2.5s
- Uptime: >99.9%
- Error Rate: <0.1%

**Optimization Techniques:**
- Async database operations
- Connection pooling
- React code splitting
- Image optimization
- Lazy loading
- CDN for static assets (Cloud Run)

---

## 🐛 Troubleshooting

### **Common Issues**

#### **Build Fails with pydantic Error**
```bash
# Solution: Install pydantic 2.11.10+ first
pip install "pydantic>=2.11.10"
pip install -r requirements.txt
```

#### **psycopg2 Won't Install (Python 3.13)**
```bash
# Solution: Use psycopg 3.x for local development
pip install "psycopg[binary]"

# Update DATABASE_URL prefix:
# From: postgresql://...
# To: postgresql+psycopg://...
```

#### **Frontend Can't Connect to Backend**
```bash
# Check NEXT_PUBLIC_API_URL in .env.local
echo $NEXT_PUBLIC_API_URL

# Verify backend is running
curl http://localhost:8000/health

# Check browser console for CORS errors
```

#### **Database Connection Fails**
```bash
# Verify DATABASE_URL format
# Local: postgresql+psycopg://user:pass@host:5432/db
# Prod: postgresql://user:pass@host:5432/db

# Test connection
python -c "from app.database.connection import db_manager; print(db_manager.test_connection())"
```

---

## 🤝 Contributing

We follow a **one-feature-at-a-time** development approach:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Follow code quality standards
4. Test thoroughly
5. Commit changes: `git commit -m 'feat: add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open Pull Request

**Code Review Checklist:**
- [ ] Functionality works as intended
- [ ] No hardcoded values
- [ ] Production-ready code
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support & Resources

- **Production Site:** https://bonidoc.com
- **API Documentation:** https://bonidoc.com/docs
- **Repository:** https://github.com/botwa2000/bonifatus-dms
- **Issues:** https://github.com/botwa2000/bonifatus-dms/issues
- **Deployment Guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Development Guide:** [DEVELOPMENT_GUIDE_VS.md](DEVELOPMENT_GUIDE_VS.md)

---

## 🎯 Roadmap

### **Q4 2025**
- ✅ Core authentication and user management
- ✅ Category system with multilingual support
- ✅ Settings and profile pages
- ⏳ Document upload and management
- ⏳ OCR text extraction
- ⏳ Basic search functionality

### **Q1 2026**
- AI-powered categorization
- Advanced search with filters
- Document sharing
- Collections/folders
- Real-time notifications

### **Q2 2026**
- Mobile applications (iOS/Android)
- Advanced analytics
- Team collaboration features
- API rate limiting
- Two-factor authentication

---

**Built using FastAPI, Next.js, and modern best practices**