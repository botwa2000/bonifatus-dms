Bonifatus DMS - Deployment Guide v7.0
Last Updated: October 5, 2025
Production Status: Operational
Development Environment: Local VS Code (Windows) - Migrated from GitHub Codespaces
Production Domain: https://bonidoc.com
Repository: https://github.com/botwa2000/bonifatus-dms

Executive Summary
Bonifatus DMS is a production-grade document management system currently operational at https://bonidoc.com. As of October 5, 2025, development has migrated from GitHub Codespaces to local Windows development environment using Visual Studio Code. The system features Google OAuth authentication, multilingual support (EN/DE/RU), dynamic category management, and cloud storage integration with Supabase PostgreSQL and Google Drive.
Current Status:

Production environment fully operational
Categories CRUD operations working
Settings and dashboard updates ready for deployment
Local development environment configured and tested
Profile page and document management pending implementation


Development Environment Migration
Migration Overview
Migration Date: October 5, 2025
From: GitHub Codespaces (browser-based development)
To: Local Windows development with Visual Studio Code
Migration Rationale
Codespaces Limitations:

60 hours/month free tier limit
Browser-based IDE constraints
Network latency for development operations
Monthly cost considerations for extended usage

Local Development Benefits:

Unlimited development time
Superior debugging capabilities
Faster development iteration
Offline development capability
No monthly usage costs
Better IDE integration and extensions

System Requirements
Development Machine Specifications:

Operating System: Windows 10/11
Python: 3.13.7 (installed)
Node.js: 22.14.0 (installed)
Git: 2.49.0 (installed)
IDE: Visual Studio Code (latest version)
RAM: Minimum 8GB recommended
Storage: Minimum 10GB free space

What Changed
Development Location:

Before: cloud.github.dev subdomain
After: localhost:3000 (frontend), localhost:8000 (backend)

Development Access:

Before: Browser-based access via GitHub Codespaces URL
After: Local machine access via localhost

Environment Configuration:

Before: Automatic Codespaces environment setup
After: Manual one-time setup with .env files

What Remained Unchanged
Critical Continuity:

Production deployment process (GitHub Actions → Cloud Run)
Database location (Supabase cloud)
Production URLs (bonidoc.com)
GitHub repository
CI/CD pipeline
Git workflow
Code structure and architecture


Architecture & Technology Stack
System Architecture
Three-Tier Architecture:

Presentation Layer: Next.js 14 React application
Application Layer: FastAPI Python backend
Data Layer: Supabase PostgreSQL database

External Integrations:

Google OAuth 2.0 for authentication
Google Drive API for document storage
Google Vision API for OCR (planned)
Google Cloud Run for hosting

Technology Stack
Frontend:

Framework: Next.js 14.x
UI Library: React 18.x
Language: TypeScript
Styling: Tailwind CSS
State Management: React Context API
HTTP Client: Axios/Fetch API

Backend:

Framework: FastAPI 0.104.1
Language: Python 3.13 (local), Python 3.11 (production)
ASGI Server: Uvicorn 0.24.0
ORM: SQLAlchemy 2.0.23
Database Driver: psycopg 3.x (local), psycopg2 (production)
Authentication: JWT + Google OAuth
Validation: Pydantic 2.11.10

Database:

Primary Database: PostgreSQL 15.x
Hosting: Supabase (cloud-managed)
Region: EU-North-1 (AWS)
Connection Pooling: PgBouncer
Backup Strategy: Supabase automated daily backups

Infrastructure:

Application Hosting: Google Cloud Run
CI/CD: GitHub Actions
DNS: Google Cloud DNS
SSL/TLS: Automatic via Cloud Run
Region: us-central1

Development Tools:

Version Control: Git + GitHub
IDE: Visual Studio Code
API Testing: Built-in Swagger UI at /docs
Database Client: Supabase Dashboard


Local Development Setup Strategy
One-Time Setup Process
Setup Phases:

Repository cloning
Python environment configuration
Backend dependency installation with Python 3.13 compatibility fixes
Backend environment variable configuration
Frontend dependency installation
Frontend environment variable configuration
Service verification

Critical Setup Considerations:
Python 3.13 Compatibility:

Standard psycopg2-binary fails to build on Python 3.13
Solution: Use psycopg 3.x instead
Database URL format change required: postgresql+psycopg://

Pydantic Compatibility:

Pydantic 2.5.0 has build issues with Python 3.13
Solution: Upgrade to pydantic 2.11.10+
Must install before other dependencies

Environment File Locations:

Backend .env must be in /backend directory (not root)
Frontend .env.local must be in /frontend directory
Files automatically ignored by git

Configuration File Updates:

Backend config.py requires env_file = ".env" in all Settings classes
Ensures proper .env file loading in local development

Daily Development Workflow
Starting Development:

Open two PowerShell terminals
Terminal 1: Activate Python venv, start backend (uvicorn)
Terminal 2: Start frontend (npm run dev)
Access via localhost:3000 (frontend) and localhost:8000/docs (backend)

Development Iteration:

Pull latest changes from main branch
Make code changes in VS Code
Test locally at localhost URLs
Commit changes with descriptive messages
Push to main branch
GitHub Actions automatically deploys to production
Verify deployment via production health checks

Stopping Development:

Press Ctrl+C in each terminal window
Virtual environment deactivates automatically
No cleanup required


Python 3.13 Compatibility Strategy
Compatibility Challenges
Primary Issue:

psycopg2-binary 2.9.9 cannot build native extensions on Python 3.13
Compilation fails with unresolved external symbol errors
Affects local development only (production uses Python 3.11)

Secondary Issue:

pydantic 2.5.0 has build dependencies incompatible with Python 3.13
Requires newer pydantic-core with pre-built Python 3.13 wheels

Solution Architecture
Database Driver Migration:

Local Development: psycopg 3.x (psycopg[binary])
Production: psycopg2-binary 2.9.9 (Docker image with Python 3.11)
SQLAlchemy dialect: postgresql+psycopg:// (local) vs postgresql:// (production)

Dependency Installation Order:

Install pydantic 2.11.10+ first (provides Python 3.13 wheels)
Install psycopg[binary] second
Install remaining dependencies third

Configuration Implications:

Local DATABASE_URL uses postgresql+psycopg:// prefix
Production DATABASE_URL uses postgresql:// prefix
Both connect to same Supabase instance
No application code changes required

Production vs Development Differences
Production Environment (Docker Container):

Python 3.11.x
psycopg2-binary 2.9.9
Standard PostgreSQL URL format
Built via Dockerfile
Dependencies from requirements.txt

Local Development Environment:

Python 3.13.7
psycopg 3.x
Modified PostgreSQL URL format
Manual installation
Dependencies installed individually

Why This Works:

SQLAlchemy abstracts database driver differences
psycopg 3.x maintains API compatibility
No business logic changes required
Seamless development-to-production workflow


Production Deployment Process
Automated Deployment Pipeline
Trigger: Push to main branch
Platform: GitHub Actions
Target: Google Cloud Run (us-central1 region)
Deployment Phases:

Build Phase:

GitHub Actions runner starts
Checks out repository code
Builds Docker images (frontend + backend)
Pushes images to Google Artifact Registry


Deploy Phase:

Deploys backend to Cloud Run service: bonifatus-dms
Deploys frontend to Cloud Run service: bonifatus-dms-frontend
Injects environment variables from GitHub Secrets
Configures service settings (memory, CPU, autoscaling)


Verification Phase:

Cloud Run performs health checks
Routes traffic to new revision
Retains previous revision for rollback



Deployment Monitoring:

GitHub Actions URL: https://github.com/botwa2000/bonifatus-dms/actions
Cloud Run Console: https://console.cloud.google.com
Production Health: https://bonidoc.com/health

Rollback Strategy:

Cloud Run maintains previous revisions
Manual traffic routing via gcloud CLI
Zero-downtime rollback capability

Environment Variable Management
Storage: GitHub Repository Secrets
Access: Repository Settings → Secrets and Variables → Actions
URL: https://github.com/botwa2000/bonifatus-dms/settings/secrets/actions
Required Secrets Categories:

Database Configuration (6 secrets)
Google Services (8 secrets)
Security Configuration (6 secrets)
Application Settings (8 secrets)

Total Required Secrets: 43 environment variables
Security Measures:

All secrets encrypted by GitHub
Never logged in Actions output
Injected at container runtime
Never stored in source code

Production URLs
Frontend:

Main Application: https://bonidoc.com
Dashboard: https://bonidoc.com/dashboard
Categories: https://bonidoc.com/categories
Settings: https://bonidoc.com/settings
Login: https://bonidoc.com/login

Backend:

API Base: https://bonidoc.com/api
Interactive Docs: https://bonidoc.com/docs
Health Check: https://bonidoc.com/health
Direct Backend: https://bonifatus-dms-vpm3xabjwq-uc.a.run.app

Cloud Resources:

GCP Project: bonifatus-calculator
Supabase Project: bonifatus-dms
GitHub Repository: https://github.com/botwa2000/bonifatus-dms


Current Implementation Status
Fully Operational Components
Authentication System:

Google OAuth 2.0 integration complete
JWT token generation and validation
Refresh token mechanism
User profile management
Admin access verification
Session management

User Management:

User registration via Google OAuth
User profile CRUD operations
User preferences management
User statistics tracking
Dashboard data aggregation
Multi-tier support (free/premium/enterprise)

Category Management:

Dynamic multilingual categories
Default system categories (Insurance, Legal, Real Estate, Banking, Other)
Custom category creation
Category translations (EN/DE/RU)
Category CRUD operations
Restore defaults functionality
Category-to-folder sync with Google Drive

Settings System:

System-wide configuration storage
Public settings API endpoint
Localization strings management
Multi-language support (EN/DE/RU)
User preference persistence
Theme management (light/dark)

Database Infrastructure:

Complete schema deployed (20 tables)
User authentication tables
Category management tables
Settings and localization tables
Audit logging tables
Foreign key constraints
Proper indexing

Components Ready for Deployment
Settings Page (Frontend):

Interface language selection
Theme selection (light/dark)
Timezone configuration
Email notification preferences
AI auto-categorization toggle
Professional UI with save/reset functionality

Dashboard Navigation (Frontend):

Main navigation header
Tab-based navigation (Dashboard/Categories/Documents)
User dropdown menu
Settings and Profile access
Sign out functionality
Premium trial status badge
Responsive mobile design

Pending Implementation
High Priority (Next 1-2 Days):
User Profile Page:

Account information display
Email and name updates
Subscription status display
Tier information (free/premium/enterprise)
Account deactivation flow
Google Drive data retention notice
Security settings

Categories Page Improvements:

Reduced stats card sizes
Replace "Custom Categories" with "Storage Used"
Add "Total Space" metric
Improved visual hierarchy
Better mobile responsiveness

Medium Priority (Next Week):
Document Upload System:

File upload handler
Google Drive API integration
Virus scanning integration
File type validation
Size limit enforcement
Progress indicators
Error handling

Document Management:

Document listing with pagination
Search functionality
Category assignment
Metadata editing
Document preview
Download functionality

Low Priority (Next 2-3 Weeks):
Advanced Features:

OCR text extraction (Google Vision API)
AI-powered categorization
Keyword extraction
Multi-language document support
Advanced search filters
Document sharing
Collections/folders


Development Roadmap & Milestones
Phase 1: Core User Management (Current Sprint - Days 1-3)
Status: 60% Complete
Completed:

✅ Category system with full CRUD
✅ Settings page UI implementation
✅ Dashboard navigation structure
✅ Local development environment migration

In Progress:

⏳ Deploy settings page to production
⏳ Deploy dashboard updates to production
⏳ Verify production functionality

Next Actions:

User profile page implementation
Account deletion with confirmation flow
Subscription management UI
Google Drive data retention notices

Success Metrics:

All user management features deployed
Settings persistence working
Profile updates functional
Zero critical bugs

Phase 2: Document Management (Sprint 2 - Days 4-8)
Status: Not Started
Backend Tasks:

Implement file upload endpoint
Google Drive folder creation/management
Storage quota validation logic
File type and size validation
Virus scanning integration setup
Document metadata extraction

Frontend Tasks:

Document upload UI component
Drag-and-drop file upload
Upload progress indicators
Document list view with pagination
Document detail modal
Category assignment interface

Success Metrics:

Upload success rate >95%
Average upload time <5 seconds for 10MB files
Proper error handling for all failure cases
Mobile-responsive upload interface

Phase 3: Enhanced Features (Sprint 3 - Days 9-15)
Status: Not Started
OCR Implementation:

Google Vision API integration
Text extraction from PDF/images
Language detection
OCR results storage in database
OCR status tracking

Search Functionality:

Full-text search implementation
Search by category, date, language
Keyword-based search
Search result ranking
Search filters and sorting

AI Categorization:

Document content analysis
Category suggestion algorithm
Confidence scoring
User feedback loop
Model training preparation

Success Metrics:

OCR accuracy >90% for clear documents
Search response time <100ms
AI categorization accuracy >80%
User satisfaction with suggestions

Phase 4: Collaboration Features (Sprint 4 - Days 16-30)
Status: Planned
Document Sharing:

Share link generation
Permission management
Expiration dates
Access logging

Collections/Folders:

Folder creation and management
Document organization
Nested folder support
Bulk operations

Activity & Notifications:

Document activity tracking
User activity feeds
Email notifications
In-app notifications

Success Metrics:

Share feature adoption >40%
Collection usage >60%
Notification delivery rate >99%


Database Architecture
Schema Overview
Total Tables: 20
Database Type: PostgreSQL 15.x
Hosting: Supabase (managed)
Total Size: ~50MB (current)
Backup Frequency: Daily automated backups
Core Tables
users (Authentication & Profile)

Columns: id, google_id, email, full_name, profile_picture, tier, created_at, updated_at
Primary Key: id (UUID)
Unique Constraints: google_id, email
Tier Values: free, premium, enterprise
Relationships: One-to-many with user_settings, categories, documents

system_settings (Configuration)

Columns: key, value (JSONB), description, is_public, created_at, updated_at
Primary Key: key
Contains: default_system_categories, theme_options, language_options, file_limits
Access: Public settings API for frontend configuration

localization_strings (Multi-Language)

Columns: id, language_code, context, key, value, created_at, updated_at
Primary Key: id
Supported Languages: en, de, ru
Coverage: Navigation, UI labels, error messages, notifications

user_settings (User Preferences)

Columns: user_id, theme, interface_language, timezone, email_notifications, ai_auto_categorization
Primary Key: user_id
Foreign Key: user_id → users.id
Default Values: theme=light, language=en, notifications=true

Category Tables
categories (Category Master)

Columns: id, user_id, is_system_default, google_drive_folder_id, sort_order, is_active
Primary Key: id (UUID)
Foreign Key: user_id → users.id
System Categories: is_system_default=true (Insurance, Legal, Real Estate, Banking, Other)

category_translations (Multilingual Names)

Columns: id, category_id, language_code, name
Primary Key: id
Foreign Keys: category_id → categories.id
Unique Constraint: (category_id, language_code)
Supports: Dynamic translation loading

Document Tables (Implemented Schema)
documents (Document Master)

Columns: id, user_id, category_id, file_name, file_path, file_size, mime_type, google_drive_file_id, upload_date, last_modified
Primary Key: id (UUID)
Foreign Keys: user_id → users.id, category_id → categories.id
Status: Table exists, no data yet

document_languages (Language Detection)

Columns: id, document_id, language_code, confidence_score
Primary Key: id
Foreign Key: document_id → documents.id
Purpose: Track detected languages in documents

Audit & System Tables
audit_logs (Activity Tracking)

Columns: id, user_id, action, entity_type, entity_id, changes, ip_address, user_agent, timestamp
Primary Key: id
Foreign Key: user_id → users.id
Retention: 90 days
Purpose: Security auditing, compliance

Planned Tables (Not Yet Implemented)
Priority 1 - Document Enhancement:

keywords (extracted terms)
document_keywords (linking table)
ai_processing_queue (async OCR jobs)
user_storage_quotas (quota tracking)
document_entities (named entity recognition)
ocr_results (extracted text storage)

Priority 2 - Organization:

collections (folder equivalent)
collection_documents (linking table)
document_relationships (related docs)
document_shares (sharing permissions)

Priority 3 - Engagement:

tags (user-defined labels)
document_tags (linking table)
notifications (user alerts)
search_analytics (search tracking)

Database Performance Considerations
Indexing Strategy:

Primary keys: Automatic B-tree indexes
Foreign keys: Indexed for join performance
Search fields: Full-text search indexes planned
User lookups: Index on google_id, email

Connection Pooling:

Provider: Supabase PgBouncer
Mode: Transaction pooling
Max Connections: 15 (free tier)
Pool Size: 10 (application setting)

Query Optimization:

Use of SQLAlchemy ORM with selective loading
Lazy loading for relationships
Pagination for large result sets
Query result caching planned


API Structure
API Versioning
Current Version: v1
Base Path: /api/v1
Documentation: Auto-generated via FastAPI at /docs
Interactive Testing: Swagger UI at https://bonidoc.com/docs
Endpoint Categories
Health & Status (2 endpoints)

GET /health - Application health check
GET / - Root endpoint information

Authentication (8 endpoints)

GET /api/v1/auth/google/config - OAuth configuration
GET /api/v1/auth/google/login - Initiate OAuth flow
POST /api/v1/auth/google/callback - Complete OAuth
POST /api/v1/auth/refresh - Refresh access token
GET /api/v1/auth/me - Current user profile
DELETE /api/v1/auth/logout - User logout
POST /api/v1/auth/admin/verify - Admin verification
GET /api/v1/auth/health - Auth service health

User Management (10 endpoints)

GET /api/v1/users/profile - Get user profile
PUT /api/v1/users/profile - Update profile
GET /api/v1/users/statistics - User statistics
GET /api/v1/users/preferences - Get preferences
PUT /api/v1/users/preferences - Update preferences
POST /api/v1/users/preferences/reset - Reset preferences
GET /api/v1/users/dashboard - Dashboard data
POST /api/v1/users/deactivate - Account deactivation
GET /api/v1/users/export - Export user data
(Profile page endpoints to be added)

Settings (3 endpoints)

GET /api/v1/settings/public - Public system settings
GET /api/v1/settings/localization/{language} - Localization strings
GET /api/v1/settings/localization - All localizations

Categories (6 endpoints)

GET /api/v1/categories - List user categories
POST /api/v1/categories - Create category
PUT /api/v1/categories/{id} - Update category
DELETE /api/v1/categories/{id} - Delete category
POST /api/v1/categories/restore-defaults - Restore system defaults
GET /api/v1/categories/{id}/documents-count - Category document count

Documents (Planned - 6+ endpoints)

POST /api/v1/documents/upload - Upload document
GET /api/v1/documents - List documents (paginated)
GET /api/v1/documents/{id} - Get document details
PUT /api/v1/documents/{id} - Update document metadata
DELETE /api/v1/documents/{id} - Delete document
GET /api/v1/documents/{id}/download - Download document
(OCR, search, and sharing endpoints to be added)

API Design Principles
RESTful Standards:

HTTP methods align with operations (GET/POST/PUT/DELETE)
Resource-based URLs
Consistent response formats
Proper status codes

Response Format:
Success: { data: {...}, message?: string }
Error: { error: string, message: string, timestamp: ISO datetime }
Authentication:

Bearer token authentication (JWT)
Token expiry: 60 minutes (access), 7 days (refresh)
Admin endpoints require tier verification

Pagination:

Query parameters: page, limit
Response includes: total, page, limit, data[]
Default limit: 50 items

Error Handling:

400: Bad request / validation errors
401: Unauthorized / invalid token
403: Forbidden / insufficient permissions
404: Resource not found
500: Internal server error


Quality Standards & Requirements
Code Quality Requirements
Modular Structure:

Maximum file length: 300 lines
Single responsibility per file
Clear separation of concerns
No circular dependencies

Zero Hardcoded Values:

All text from database localization_strings
All configuration from system_settings or environment variables
No business logic constants in code
Feature flags for conditional features

Production-Ready Code Only:

No TODO comments in main branch
No FIXME markers
No temporary workarounds
No commented-out code blocks
No development-only code paths

Documentation Standards:

File header comment with location and purpose
Function docstrings with parameters and return types
Complex logic explained inline
API endpoints documented in OpenAPI spec
README files for major components

Naming Conventions:

Concise, descriptive variable names
No marketing terms in technical code
Consistent naming across similar functions
TypeScript/Python style guide compliance

Testing Requirements
Pre-Deployment Testing (Current Manual Process):

Functional testing of all CRUD operations
Cross-browser testing (Chrome, Firefox, Safari, Edge)
Mobile responsive testing
Authentication flow verification
Error handling verification

Planned Automated Testing:

Unit tests for business logic functions
Integration tests for API endpoints
End-to-end tests for critical user flows
Test coverage target: 80% for business logic

Production Verification:

Health endpoint checks after deployment
Smoke tests of critical features
Monitoring dashboard review
Error log review

Code Review Requirements
Review Checklist:

Functionality matches requirements
Architecture compliance verified
No hardcoded values present
Security vulnerabilities checked
Performance implications considered
Documentation adequate
Naming standards followed
Prior code duplication checked

Review Process:

Currently: Self-review before commit
Planned: Peer review for significant changes
Required: All production deployments verified


Security Requirements
Authentication Security
OAuth Implementation:

Google OAuth 2.0 standard compliance
Authorization code flow (not implicit)
State parameter for CSRF protection
Nonce for replay attack prevention
Secure token storage (httpOnly cookies planned)

JWT Token Security:

HS256 algorithm (symmetric encryption)
Secret key minimum 32 bytes
Access token expiry: 60 minutes
Refresh token expiry: 7 days
Token rotation on refresh
Blacklist for revoked tokens (planned)

Session Management:

Server-side session validation
Automatic logout on token expiry
Manual logout clears all tokens
Concurrent session limits (planned)

Data Protection
Encryption:

TLS 1.3 for all connections
Database connections encrypted
Secrets encrypted in GitHub
Environment variables never logged

Input Validation:

Pydantic models for all API inputs
Type checking enforced
Range validation for numeric inputs
Length validation for strings
File type validation for uploads

SQL Injection Prevention:

SQLAlchemy ORM parameterized queries
No raw SQL string concatenation
Input sanitization before queries
Prepared statements only

XSS Prevention:

React automatic escaping
Content Security Policy headers
No innerHTML usage
Sanitization of user-generated content

CSRF Protection:

SameSite cookie attributes
Origin header validation
Custom CSRF tokens (planned)

Access Control
Role-Based Access:

User tiers: free, premium, enterprise
Admin role verification
Resource ownership validation
Permission checks on all operations

Rate Limiting (Planned):

Authentication endpoints: 5 requests/minute
API endpoints: 100 requests/minute
File uploads: 10 uploads/hour
IP-based throttling

Audit Logging:

All sensitive operations logged
User actions tracked
IP address recorded
Retention period: 90 days

File Upload Security
Validation:

File type whitelist (PDF, DOCX, images)
File size limits (50MB free tier)
MIME type verification
Magic number checking

Virus Scanning (Planned):

Integration with ClamAV or similar
Scan before storage
Quarantine suspicious files
User notification on threats

Storage Security:

Google Drive private folders
Access control per user
Signed URLs for downloads
Automatic deletion on account closure


Performance Requirements
Response Time Targets
API Endpoints:

Health check: <50ms (p95)
Authentication: <200ms (p95)
CRUD operations: <200ms (p95)
List operations: <300ms (p95)
Search queries: <100ms (p95)

Frontend Load Times:

Initial page load: <2 seconds
Time to interactive: <3 seconds
Subsequent navigation: <500ms
API call responses: <1 second

File Operations:

Upload progress visible: <100ms
Upload completion: <5 seconds for 10MB file
Download initiation: <200ms
OCR processing: <30 seconds per document

Scalability Targets
Concurrent Users:

Current capacity: 1,000 simultaneous users
Target capacity: 10,000 simultaneous users
Auto-scaling threshold: CPU >70%

Database Performance:

Query response time: <100ms average
Connection pool: 10-50 connections
Transaction throughput: 100 TPS

Storage Scaling:

User quota: 1GB (free), 10GB (premium), 100GB (enterprise)
Total storage capacity: Unlimited (Google Drive)
Upload bandwidth: 10 Mbps per user

Optimization Strategy
Frontend Optimization:

Code splitting per route
Lazy loading for images
Component-level code splitting
Minification and compression
CDN for static assets (planned)

Backend Optimization:

Database query optimization
Connection pooling tuning
Response caching for static data
Async operations for long tasks
Background job processing (planned)

Database Optimization:

Proper indexing strategy
Query result pagination
Selective column loading
Join optimization
Full-text search indexes

Monitoring & Metrics
Application Monitoring:

Google Cloud Run metrics
Request latency distribution
Error rate tracking
Resource utilization (CPU, memory)

Database Monitoring:

Supabase dashboard metrics
Query performance insights
Connection pool status
Slow query identification

User Experience Monitoring:

Core Web Vitals tracking (planned)
Real user monitoring (planned)
Synthetic monitoring (planned)
Error tracking service (planned)


Backup & Recovery Strategy
Database Backup
Automated Backups:

Provider: Supabase automatic backups
Frequency: Daily snapshots
Retention: 7 days (free tier)
Point-in-time recovery: Available

Backup Verification:

Monthly restore test (planned)
Backup integrity checks
Recovery time objective (RTO): 4 hours
Recovery point objective (RPO): 24 hours

Application Backup
Code Repository:

Primary: GitHub repository
All code version controlled
Complete commit history
Branch protection on main

Container Images:

Storage: Google Artifact Registry
Retention: Last 10 revisions
Tagging: Git commit SHA

Configuration Backup:

GitHub Secrets: Encrypted storage
Environment variables documented
Infrastructure as code (planned)

Disaster Recovery
Recovery Procedures:
Database Restore:

Contact Supabase support
Request point-in-time recovery
Verify restored data integrity
Update application configuration if needed

Application Rollback:

Identify last stable revision
Route traffic to previous Cloud Run revision
Verify application functionality
Investigate and fix root cause

Complete System Recovery:

Restore database from backup
Deploy last stable application revision
Verify all integrations working
Restore user access
Communicate status to users

Recovery Time Estimates:

Database restore: 1-2 hours
Application rollback: 5-10 minutes
Complete system recovery: 2-4 hours


Environment Variables Reference
Backend Environment Variables
Required for Local Development:

DATABASE_URL: PostgreSQL connection string (use postgresql+psycopg:// prefix)
SECURITY_SECRET_KEY: JWT signing key
GOOGLE_CLIENT_ID: OAuth client ID
GOOGLE_CLIENT_SECRET: OAuth client secret
GOOGLE_REDIRECT_URI: OAuth redirect (http://localhost:3000/login for local)
GCP_PROJECT: Google Cloud project ID
APP_ENVIRONMENT: development/production
APP_DEBUG_MODE: true/false
APP_CORS_ORIGINS: Comma-separated allowed origins
APP_HOST: Server bind address
APP_PORT: Server port
APP_TITLE: API title
APP_DESCRIPTION: API description
APP_VERSION: API version

Optional with Defaults:

DATABASE_POOL_SIZE: Connection pool size (default: 10)
DATABASE_POOL_RECYCLE: Pool recycle time (default: 3600)
DATABASE_ECHO: SQL logging (default: false)
ALGORITHM: JWT algorithm (default: HS256)
ACCESS_TOKEN_EXPIRE_MINUTES: Token expiry (default: 60)
REFRESH_TOKEN_EXPIRE_DAYS: Refresh expiry (default: 7)

Frontend Environment Variables
Required for Local Development:

NEXT_PUBLIC_API_URL: Backend API URL (http://localhost:8000 for local)

Security Notes
Never Commit:

.env files
.env.local files
Any files containing credentials
Secret keys or tokens

Secure Storage:

Local: .env files (gitignored)
Production: GitHub Secrets
Never share credentials via email or chat


Troubleshooting Guide
Backend Issues
Server Won't Start - Environment Variable Error:

Symptom: "Field required" validation errors
Cause: .env file not found or in wrong location
Solution: Verify .env is in /backend directory, not root

Database Connection Failed:

Symptom: Connection timeout or authentication error
Cause: Incorrect DATABASE_URL or network issues
Solution: Verify URL uses postgresql+psycopg:// prefix for local

Import Errors - Module Not Found:

Symptom: ModuleNotFoundError when starting server
Cause: Virtual environment not activated or dependencies missing
Solution: Activate venv, reinstall dependencies

psycopg2 Build Error:

Symptom: Error building psycopg2-binary wheel
Cause: Python 3.13 incompatibility
Solution: Use psycopg[binary] instead, update DATABASE_URL

Frontend Issues
Server Won't Start - Environment Variable Missing:

Symptom: "NEXT_PUBLIC_API_URL must be set" error
Cause: .env.local not found or created after server started
Solution: Stop server, verify .env.local in /frontend, restart

API Calls Failing:

Symptom: Network errors or CORS errors
Cause: Backend not running or wrong API URL
Solution: Verify backend at localhost:8000/docs, check NEXT_PUBLIC_API_URL

Module Not Found:

Symptom: Cannot find module errors
Cause: node_modules missing or corrupted
Solution: Delete node_modules, run npm install

Development Environment Issues
Virtual Environment Won't Activate:

Symptom: PowerShell execution policy error
Cause: Restricted execution policy
Solution: Run Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Port Already in Use:

Symptom: EADDRINUSE error
Cause: Another process using port 8000 or 3000
Solution: Stop conflicting process or change port

Git Push Rejected:

Symptom: "Updates were rejected" error
Cause: Local branch behind remote
Solution: git pull --rebase origin main, then push

Production Issues
Deployment Failed:

Symptom: GitHub Actions workflow fails
Cause: Build errors, test failures, or configuration issues
Solution: Check Actions logs, fix errors, retry

Production Site Down:

Symptom: bonidoc.com not responding
Cause: Cloud Run service issue or database problem
Solution: Check Cloud Run console, verify database connectivity

Features Not Working After Deploy:

Symptom: New features not visible in production
Cause: Cache issues or deployment incomplete
Solution: Hard refresh browser, verify Cloud Run revision


Support & Resources
Development Resources
Local Development:

Frontend: http://localhost:3000
Backend: http://localhost:8000
API Documentation: http://localhost:8000/docs
API Health: http://localhost:8000/health

Production:

Application: https://bonidoc.com
API: https://bonidoc.com/api
Documentation: https://bonidoc.com/docs
Health Check: https://bonidoc.com/health

Cloud Resources
GitHub:

Repository: https://github.com/botwa2000/bonifatus-dms
Actions: https://github.com/botwa2000/bonifatus-dms/actions
Secrets: https://github.com/botwa2000/bonifatus-dms/settings/secrets/actions

Google Cloud:

Console: https://console.cloud.google.com
Cloud Run: https://console.cloud.google.com/run
Project: bonifatus-calculator
Region: us-central1

Supabase:

Dashboard: https://supabase.com/dashboard
Project: bonifatus-dms
Region: EU-North-1

Command Reference
Development Commands:
# Backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev

# Git
git pull origin main
git add .
git commit -m "message"
git push origin main
Production Commands:
# View Cloud Run services
gcloud run services list --region=us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Force redeploy
git commit --allow-empty -m "redeploy" && git push

# Check health
curl https://bonidoc.com/health

Next Immediate Actions
Today (October 5, 2025)

Deploy Pending Frontend Changes:

Settings page
Dashboard navigation updates
Verify production deployment


Test Production Features:

Settings persistence
Dashboard navigation
User preferences
Category operations



Tomorrow (October 6, 2025)

Implement Profile Page:

Account information display
Email/name update functionality
Subscription status
Account deletion flow


Update Categories Stats:

Reduce card sizes
Add storage metrics
Improve layout



Next Week (October 7-11, 2025)

Document Upload Implementation:

Backend upload handler
Google Drive integration
Frontend upload UI
Progress indicators
Error handling


Document Management:

List view with pagination
Search functionality
Category assignment
Metadata editing




Deployment Guide Version: 7.0
Last Updated: October 5, 2025
Status: Local development operational, production stable, profile page and documents pending