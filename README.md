# Bonifatus DMS - Professional Document Management System - Sep 2025

[![Deploy to Cloud Run](https://github.com/yourusername/bonifatus-dms/actions/workflows/deploy.yml/badge.svg)](https://github.com/yourusername/bonifatus-dms/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## 🎯 **Project Objectives**

Bonifatus DMS is a **production-grade document management system** that provides:

- **🤖 AI-Powered Categorization** - Intelligent document classification using machine learning
- **🔍 Advanced Search** - Full-text search with filtering and keyword extraction  
- **☁️ Google Drive Integration** - Seamless synchronization with user's Google Drive
- **🌍 Multilingual Support** - German and English interface with database-driven content
- **👥 User Tier Management** - Free, trial, and premium subscription tiers
- **🔒 Enterprise Security** - OAuth 2.0, JWT tokens, rate limiting, and audit logging
- **📱 Multi-Device Support** - Responsive design for desktop, tablet, and mobile
- **⚡ High Performance** - Async operations, database optimization, caching strategies

### **Business Value**
- **For Individuals**: Personal document organization with AI assistance
- **For Small Companies**: Team collaboration and document workflow management  
- **For Enterprises**: Scalable document management with advanced security features

### **Technical Excellence Standards**
- **Zero Hardcoded Values** - All configuration from database/environment
- **Production-Grade Code** - No workarounds, fallbacks, or temporary solutions
- **Modular Architecture** - Single responsibility, <300 lines per file
- **Comprehensive Testing** - Unit, integration, and end-to-end test coverage
- **Security First** - OAuth, JWT, rate limiting, input validation, audit trails

---

## 🏗️ **Architecture Overview**

### **Technology Stack**
- **Backend**: Python 3.11+ with FastAPI (async, auto-documentation)
- **Database**: Supabase PostgreSQL (cloud-native, full-text search)
- **Authentication**: Google OAuth 2.0 + JWT tokens
- **Storage**: Google Drive API (user's own storage)
- **Hosting**: Google Cloud Run (serverless, auto-scaling)
- **CI/CD**: GitHub Actions (automated testing and deployment)

### **System Architecture**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API    │    │   Database      │
│   React/TS      │◄──►│   FastAPI        │◄──►│   PostgreSQL    │
│   Tailwind CSS  │    │   Python 3.11+   │    │   Supabase      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Authentication│    │   Integrations   │    │   File Storage  │
│   Google OAuth  │    │   Google APIs    │    │   Google Drive  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Core Features Flow**
1. **User Authentication** → Google OAuth → JWT tokens → Session management
2. **Document Upload** → File validation → Google Drive storage → Metadata extraction
3. **AI Processing** → Text extraction → Keyword analysis → Category suggestion
4. **Search & Discovery** → Full-text indexing → Advanced filtering → Real-time results

---

## 🚀 **Quick Start Guide**

### **Prerequisites**
- GitHub account (for repository and CI/CD)
- Google Cloud Platform account (free tier available)
- Supabase account (free tier available)

### **30-Minute Setup**

1. **Create Supabase Database**
   ```bash
   # 1. Visit https://supabase.com → Create project
   # 2. Choose region closest to users
   # 3. Copy connection string from Settings → Database
   ```

2. **Setup Google Cloud Project**
   ```bash
   # 1. Visit https://console.cloud.google.com → Create project
   # 2. Enable APIs: Cloud Run, Cloud Build, Google Drive
   # 3. Create service account for deployment
   # 4. Setup OAuth 2.0 credentials
   ```

3. **Deploy to Production**
   ```bash
   # 1. Fork this repository
   # 2. Add GitHub Secrets (see Configuration section)
   # 3. Push to main branch → Automatic deployment
   # 4. Visit deployed URL: https://your-app.run.app
   ```

### **Local Development**
```bash
# Clone repository
git clone https://github.com/yourusername/bonifatus-dms.git
cd bonifatus-dms

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Install dependencies
cd backend
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# API Documentation: http://localhost:8000/docs
```

---

## ⚙️ **Configuration & Secrets**

### **Environment Variables (.env)**
```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres

# Authentication & Security
SECURITY_SECRET_KEY=[generate-with-python-secrets]
GOOGLE_CLIENT_ID=[from-google-cloud-console]
GOOGLE_CLIENT_SECRET=[from-google-cloud-console]

# Application Settings
APP_ENVIRONMENT=production
APP_DEBUG_MODE=false
APP_CORS_ORIGINS=https://your-domain.com

# Google Cloud Platform
GCP_PROJECT=[your-gcp-project-id]
GCP_REGION=us-central1
GCP_SERVICE_NAME=bonifatus-dms-api
```

### **GitHub Secrets (Required for Deployment)**
| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `DATABASE_URL` | Supabase PostgreSQL connection | Supabase Dashboard → Settings → Database |
| `SECURITY_SECRET_KEY` | JWT signing key | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `GOOGLE_CLIENT_ID` | OAuth client ID | Google Cloud Console → APIs & Services → Credentials |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | Google Cloud Console → APIs & Services → Credentials |
| `GCP_SA_KEY` | Service account JSON | Google Cloud Console → IAM → Service Accounts |

### **Google Cloud Setup Commands**
```bash
# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com drive.googleapis.com

# Create deployment service account
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

---

## 🔧 **Development Methodology**

### **Production-Grade Development Process**

We follow a **methodical, one-feature-at-a-time approach** to ensure production quality:

#### **Phase-Based Development**
1. **Foundation** → Core infrastructure, database, configuration
2. **Authentication** → User management, OAuth, JWT security  
3. **Integration** → Google Drive API, external services
4. **Documents** → Upload, processing, storage management
5. **Intelligence** → AI categorization, search, analytics
6. **Advanced** → Collaboration, reporting, optimization

#### **Quality Standards for Each Feature**
- **🚫 Zero Hardcoded Values** - All text, configurations from database
- **🏭 Production-Ready Code** - No TODO, FIXME, or temporary workarounds
- **🎯 Single Responsibility** - Each file <300 lines, focused functionality
- **🧪 Comprehensive Testing** - Unit, integration, and end-to-end tests
- **📝 Complete Documentation** - Function comments, API documentation
- **🔍 Code Review Process** - All changes reviewed before deployment

#### **Fix Implementation Protocol**

Every code change follows this strict process:

1. **📍 Precise Location**
   ```
   File: backend/src/path/to/file.py
   Function: function_name() 
   Line: 42 (after "previous_code_line")
   
   BEFORE:
   existing_code_here
   
   REPLACE WITH:
   new_production_code_here
   
   AFTER:  
   next_code_line
   ```

2. **🎨 Code Formatting**
   ```bash
   # Format before every commit
   black --line-length=88 backend/src/
   
   # Verify formatting
   black --check --line-length=88 backend/src/
   ```

3. **✅ Testing & Validation**
   ```bash
   # Test syntax
   python -m py_compile backend/src/**/*.py
   
   # Test imports
   python -c "from src.main import app; print('✓ Imports successful')"
   
   # Test functionality
   pytest backend/tests/ -v
   ```

4. **🚀 Deployment**
   ```bash
   # Single-feature commits
   git add .
   git commit -m "feat: specific feature description
   
   - Bullet point of changes
   - No hardcoded values
   - Production-ready implementation"
   
   # Deploy
   git push origin main
   ```

### **Feature Development Checklist**

Before moving to the next feature, ensure:

- [ ] **Code Quality**: Black formatting, no linting errors
- [ ] **Functionality**: Feature works as designed, no errors
- [ ] **Production Ready**: No hardcoded values, proper error handling
- [ ] **Testing**: All tests pass, adequate test coverage
- [ ] **Documentation**: Code comments, API docs updated
- [ ] **Deployment**: Successfully deployed to production
- [ ] **Verification**: Production health checks pass

---

## 📚 **API Documentation**

### **Core Endpoints**

#### **Health & Status**
- `GET /health` - Application health check
- `GET /api/v1/status` - Detailed system status

#### **Authentication**  
- `GET /api/v1/auth/google/login` - Initiate Google OAuth
- `POST /api/v1/auth/token` - Exchange code for JWT
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `DELETE /api/v1/auth/logout` - Logout user

#### **User Management**
- `GET /api/v1/users/profile` - Get user profile
- `PUT /api/v1/users/profile` - Update user profile  
- `GET /api/v1/users/settings` - Get user preferences
- `PUT /api/v1/users/settings` - Update user preferences

#### **Document Management**
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List user documents
- `GET /api/v1/documents/{id}` - Get document details
- `PUT /api/v1/documents/{id}` - Update document metadata
- `DELETE /api/v1/documents/{id}` - Delete document

#### **Categories & Search**
- `GET /api/v1/categories` - List categories
- `POST /api/v1/categories` - Create custom category
- `GET /api/v1/search` - Search documents
- `GET /api/v1/search/suggestions` - Search suggestions

### **Interactive API Documentation**
- **Swagger UI**: `https://your-app.run.app/api/docs`
- **ReDoc**: `https://your-app.run.app/api/redoc`

---

## 🧪 **Testing Strategy**

### **Test Coverage Requirements**
- **Unit Tests**: >90% code coverage for business logic
- **Integration Tests**: API endpoint testing with database
- **End-to-End Tests**: Complete user workflows
- **Performance Tests**: Response time and load testing

### **Running Tests**
```bash
# Unit tests
pytest backend/tests/unit/ -v --cov=src

# Integration tests  
pytest backend/tests/integration/ -v

# All tests with coverage
pytest backend/tests/ -v --cov=src --cov-report=html

# Performance tests
pytest backend/tests/performance/ -v --benchmark-only
```

### **Test Data Management**
- **No Hardcoded Test Data** - All test data loaded from fixtures
- **Database Isolation** - Each test uses fresh database state
- **Mock External Services** - Google APIs mocked for consistent testing

---

## 🔒 **Security Features**

### **Authentication & Authorization**
- **Google OAuth 2.0** - Secure third-party authentication
- **JWT Tokens** - Stateless session management with refresh tokens
- **Role-Based Access** - User, admin, and system roles
- **Session Security** - Automatic token rotation and expiry

### **Data Protection**
- **Input Validation** - Pydantic models for all API inputs
- **SQL Injection Prevention** - SQLAlchemy ORM with parameterized queries  
- **XSS Protection** - Content Security Policy headers
- **Rate Limiting** - API endpoint throttling and abuse prevention

### **Infrastructure Security**
- **HTTPS Everywhere** - TLS encryption for all communications
- **CORS Configuration** - Strict cross-origin resource sharing
- **Environment Isolation** - Separate staging and production environments
- **Audit Logging** - Complete audit trail of user actions

---

## 📈 **Performance & Scalability**

### **Performance Targets**
- **API Response Time**: <200ms for 95th percentile
- **Search Performance**: <100ms for full-text search queries
- **File Upload**: Support up to 100MB files with progress tracking
- **Concurrent Users**: 1000+ simultaneous users

### **Scalability Features**
- **Async Operations** - FastAPI async/await for high concurrency
- **Database Optimization** - Proper indexing and query optimization
- **Caching Strategy** - Redis caching for frequently accessed data
- **Auto-Scaling** - Google Cloud Run automatic scaling based on load

### **Monitoring & Observability**
- **Health Checks** - Comprehensive application and database health monitoring
- **Performance Metrics** - Response time, throughput, error rate tracking
- **Log Aggregation** - Structured logging with correlation IDs
- **Error Tracking** - Automatic error reporting and alerting

---

## 🤝 **Contributing**

### **Development Setup**
1. Fork the repository
2. Create feature branch: `git checkout -b feat/feature-name`
3. Follow the development methodology above
4. Submit pull request with comprehensive description

### **Code Standards**
- Follow PEP 8 and project coding standards
- Include tests for all new functionality
- Update documentation for API changes
- Ensure all CI/CD checks pass

### **Commit Message Format**
```
feat: brief description of feature

- Detailed bullet points of changes
- Reference any issues: closes #123
- Mention breaking changes if any
```

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 **Support & Documentation**

- **📖 Full Documentation**: [docs/](docs/)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/yourusername/bonifatus-dms/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/yourusername/bonifatus-dms/discussions)
- **📧 Contact**: [your-email@domain.com](mailto:your-email@domain.com)

---

## 🏆 **Project Status**

- **Current Phase**: Foundation Development
- **Next Milestone**: Authentication System
- **Production Ready**: Q2 2025
- **Active Development**: ✅ Yes

Built with ❤️ for efficient document management# Trigger deployment with Secret Manager integration
# Fix Cloud Run service account secret access
