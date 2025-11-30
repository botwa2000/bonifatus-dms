# BoniDoc - Complete Development & Deployment Guide

**Version:** 15.1 (Consolidated)  
**Last Updated:** November 2025  
**Status:** Production on Hetzner VPS  
**Domain:** https://bonidoc.com  

---

## Quick Navigation

**New to the project?** Start with §1 (Project Overview) and §2 (Quick Start)  
**Need a procedure?** Jump to §8 (Deployment & Operations)  
**Need configuration?** Jump to §9 (Configuration Reference)  
**Troubleshooting?** Jump to §8.9 (Troubleshooting Guide)  
**Need history?** Jump to §10 (Feature History)  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Quick Start Guide](#2-quick-start-guide)
3. [Technology Stack](#3-technology-stack)
4. [Database Architecture](#4-database-architecture)
5. [System Architecture](#5-system-architecture)
6. [Current Status](#6-current-status)
7. [Go-Live Preparation](#7-go-live-preparation)
8. [Implementation Standards](#8-implementation-standards)
9. [Deployment & Operations](#9-deployment--operations)
10. [Configuration Reference](#10-configuration-reference)
11. [Payment Integration](#11-payment-integration)
12. [Feature History](#12-feature-history)
13. [Project Instructions](#13-project-instructions)

---

## 1. Project Overview

### 1.1 Vision

BoniDoc is a privacy-first document management system combining secure storage, intelligent OCR-based categorization, and multi-language support. Documents are stored in users' personal Google Drive; the system learns from user corrections to improve accuracy over time.

### 1.2 Core Capabilities

**Security-First Architecture**
- HTTPS with HSTS headers, Google OAuth 2.0 + JWT (15min/7day tokens)
- Field-level encryption (OAuth tokens only, using Fernet AES-256)
- httpOnly cookies (XSS-proof token storage)
- 3-tier rate limiting (auth/write/read operations)
- Comprehensive audit logging with context
- Session management with revocation capability

**Intelligent OCR**
- Two-stage processing: PyMuPDF (native text) + Tesseract (scanned PDFs)
- Automatic language detection (EN/DE/RU/FR) with 3-pass accuracy
- Keyword extraction via frequency analysis + stop word filtering
- Structure-based PDF detection: Analyzes PDF structure (fonts, text blocks, images) to determine if document is native text or scanned image
  - Language-agnostic approach (works for all languages without false positives)
  - Avoids misclassification of technical terms, abbreviations, and proper nouns
- Spell-checking validation: Post-OCR quality check using Hunspell dictionaries (en_US, de_DE, ru_RU, fr_FR) to verify extracted text quality
  - Located in `/usr/share/hunspell/` on backend container
  - Used only after OCR completes, not for scanned detection

**Multi-Language Support**
- Full UI in English, German, Russian, French
- Language-specific document processing and categorization
- All text strings externalized in database (NO hardcoding)
- Stop words and keywords tailored per language

**User-Owned Storage**
- All documents stored in user's Google Drive
- System never stores document files on servers
- Users maintain full control and ownership
- Respects privacy and data sovereignty

**Learning System**
- Learns from user corrections to improve suggestions
- Daily accuracy metrics per category
- Keyword weight adjustment (+10% correct, -5% incorrect)
- Confidence-based suggestions

**Zero Technical Debt**
- No hardcoded values in source code
- All configuration stored in database
- Production-ready code only (no TODOs, workarounds, fallbacks)

---

## 2. Quick Start Guide

### 2.1 For Operations/DevOps (5 minutes)

```bash
# Deploy code
ssh deploy@YOUR_SERVER_IP
~/deploy.sh

# View logs
docker-compose logs -f backend

# Check status
curl https://api.bonidoc.com/health
```

→ Jump to §8.2 for full deployment procedures

### 2.2 For Developers (30 minutes)

1. Read §5 (System Architecture) - understand how it works
2. Read §9.3 (Database Schema) - understand data structure
3. Jump to §8.4 (Feature Deployment) when ready to deploy

### 2.3 For New Team Members (1.5 hours)

1. Read §1 (Project Overview)
2. Read §3 (Technology Stack)
3. Read §5 (System Architecture)
4. Skim §9 (Configuration Reference)
5. Bookmark §8 (Procedures) for daily use

### 2.4 For Planning/Product (40 minutes)

1. Read §1 (Project Overview)
2. Read §6 (Current Status)
3. Read §10.2 (Pricing & Business)
4. Read §10.4 (Planned Features)

---

## 3. Technology Stack

### 3.1 Core Technologies

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend** | FastAPI | Python 3.11+ |
| **Database** | PostgreSQL | 16 (local on Hetzner) |
| **Frontend** | Next.js + React | 15 / 18 |
| **Language** | TypeScript | 5.x |
| **Styling** | Tailwind CSS | 3.x |
| **Auth** | Google OAuth 2.0 + JWT | httpOnly cookies |
| **OCR** | PyMuPDF + Tesseract | Quality detection |
| **Encryption** | Fernet AES-256 | OAuth tokens only |
| **Storage** | Google Drive API | User-owned |
| **Migrations** | Alembic | Schema versioning |
| **Deployment** | Docker Compose | Nginx reverse proxy |

### 3.2 Infrastructure (October 24, 2025)

- **Platform:** Hetzner VPS (Ubuntu 24.04 LTS)
- **Server:** CPX22 (2vCPU, 4GB RAM, 80GB SSD)
- **Cost:** €8/month (80% savings vs Cloud Run + Supabase)
- **Database:** PostgreSQL 16 local on Hetzner with SSL
- **SSL:** Cloudflare Origin Certificate (Full Strict)
- **Region:** Europe (Germany) - low latency for EU users
- **Monitoring:** Docker logs + direct server access

---

## 4. Database Architecture

### 4.1 Schema Overview

**30 active tables** organized in functional groups:

| Group | Purpose | Tables |
|-------|---------|--------|
| **Authentication** | User management, OAuth, sessions | users, user_settings, user_sessions |
| **Categories** | System/user categories, translations | categories, category_translations, category_keywords |
| **Documents** | Metadata, storage, language info | documents, document_categories, document_languages, document_dates |
| **Keywords & Search** | Indexing, stop words, search history | keywords, document_keywords, stop_words, search_history |
| **Google Drive** | Drive integration, sync tracking | google_drive_folders, google_drive_sync_status |
| **ML & Logging** | Classification decisions, daily metrics | document_classification_log, category_classification_metrics |
| **System** | Config, UI strings, audit trail | system_settings, localization_strings, audit_logs |
| **Additional** | Batches, collections, entities, sharing | upload_batches, collections, document_entities, document_shares, tags, notifications |

### 4.2 Key Constraints

- `document_categories` allows unlimited categories per document; one marked primary
- All language codes/metadata loaded from `system_settings` (NO hardcoding)
- User preferences (UI language, document languages) in `user_settings` & `preferred_doc_languages`
- Encryption: OAuth tokens only (Fernet AES-256)
- Audit logging: Log standardized filenames, not originals (privacy)

---

## 5. System Architecture

### 5.1 Data Flow

```
User Upload
  ↓
File Validation → Temporary In-Memory Storage
  ↓
Text Extraction (PyMuPDF → Quality Check → Tesseract if needed)
  ↓
Language Detection (3-pass for accuracy)
  ↓
Keyword Extraction (frequency analysis, stop words filtered)
  ↓
Date Extraction
  ↓
Category Classification (suggest ONE primary based on keyword overlap)
  ↓
User Review & Correction (change primary, add secondary categories)
  ↓
Google Drive Storage (in category folder) + Database Metadata
  ↓
ML Learning Update (adjust keyword weights per language per category)
  ↓
Temporary File Cleanup
```

### 5.2 Security Layers

1. **Transport Security:** HTTPS with HSTS headers
2. **Authentication:** Google OAuth + JWT (15-minute access, 7-day refresh)
3. **Session Management:** Track active sessions, enable revocation
4. **Encryption:** OAuth tokens only (Fernet AES-256)
5. **Rate Limiting:** 3-tier (auth/write/read operations)
6. **Input Validation:** Pydantic models on all API inputs
7. **Audit Logging:** All security events with context

### 5.3 Learning Cycle

```
System Suggests Primary Category (highest keyword overlap score)
  ↓
User Confirms, Changes, or Adds Categories
  ↓
Log Decision (with confidence score, user action)
  ↓
Daily: Adjust Keyword Weights (+10% correct, -5% incorrect)
  ↓
Daily: Calculate Accuracy Metrics (precision, recall, F1) per category
  ↓
Improved Suggestions (weights used for next day's classifications)
```

---

## 6. Current Status

### 6.1 Completed Phases

- ✅ **Phase 1:** Security Foundation (database cleanup, encryption, sessions, rate limiting)
- ✅ **Phase 2A:** OCR & Document Processing (PyMuPDF, Tesseract, language detection)
- ✅ **Phase 2B:** Category Learning System (classification logging, daily metrics)
- ✅ **Phase 2C:** Google Drive Integration (folder creation, document sync)
- ✅ **Phase 2D:** Multi-Language Support (EN/DE/RU/FR, UI translations, language-specific keywords)
- ✅ **Production Deployment:** Hetzner VPS, Docker, SSL, monitoring

### 6.2 In Progress / Next Steps

- Phase 2E: Advanced Classification (multi-category suggestions with confidence)
- Phase 3: User Dashboard & Analytics
- Phase 4: Performance Optimization (caching, indexing, query optimization)

### 6.3 Not Started / Future

- Phase 5: Mobile Native Apps
- Advanced collaboration features
- API for third-party integrations
- Browser extension

---

## 7. Go-Live Preparation

### 7.1 Dev/Prod Environment Separation

**Setup dev.bonidoc.com subdomain:**

```bash
# On Hetzner server
ssh root@91.99.212.17

# Create dev database
sudo -u postgres psql
CREATE DATABASE bonifatus_dms_dev;
CREATE USER bonifatus_dev WITH PASSWORD 'YourDevPassword';
GRANT ALL PRIVILEGES ON DATABASE bonifatus_dms_dev TO bonifatus_dev;
\q

# Clone environment
cd /opt
cp -r bonifatus-dms bonifatus-dms-dev
cd bonifatus-dms-dev

# Update docker-compose.yml for dev (ports 3001/8081)
# Update .env file with dev database and settings
```

**Nginx configuration for dev subdomain:**
```nginx
# /etc/nginx/sites-available/dev.bonidoc.com
server {
    listen 443 ssl http2;
    server_name dev.bonidoc.com;

    ssl_certificate /etc/ssl/certs/bonidoc.com.crt;
    ssl_certificate_key /etc/ssl/private/bonidoc.com.key;

    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Cloudflare DNS:**
- Add A record: `dev.bonidoc.com` → `91.99.212.17`
- Add A record: `api-dev.bonidoc.com` → `91.99.212.17`
- SSL mode: Full (Strict)
- Proxy status: Proxied (orange cloud)

**Google OAuth Configuration:**
- Add authorized redirect URI: `https://api-dev.bonidoc.com/api/v1/auth/google/callback`

**⚠️ IMPORTANT: Dev to Prod Migrations**

When migrating features from dev to prod, refer to `/opt/DEV_TO_PROD_MIGRATION.md` for:
- Environment-specific variables that must NEVER be copied
- Safe migration procedures (rsync code only, never config files)
- Verification steps to ensure debug logs stay disabled on prod

**Key environment variables that differ between dev/prod:**
- `NEXT_PUBLIC_DEBUG_LOGS`: `"true"` (dev) vs `"false"` (prod)
- `APP_DEBUG_MODE`: `true` (dev) vs `false` (prod)
- Port mappings, database URLs, API URLs, OAuth redirect URIs

### 7.2 Analytics & Monitoring (100% Free)

**Cloudflare Web Analytics (Recommended - Already Using Cloudflare):**
```html
<!-- Add to frontend/src/app/layout.tsx -->
<script defer src='https://static.cloudflareinsights.com/beacon.min.js'
        data-cf-beacon='{"token": "YOUR_CLOUDFLARE_TOKEN"}'></script>
```

Setup:
1. Cloudflare Dashboard → Web Analytics
2. Add site: bonidoc.com
3. Copy beacon token
4. Zero configuration needed
5. Features: Page views, visitors, referrers, browsers, countries

**Google Search Console (SEO Analytics - Free):**
```bash
# Add to frontend/public/robots.txt
User-agent: *
Allow: /
Sitemap: https://bonidoc.com/sitemap.xml

# Add to frontend/src/app/layout.tsx head
<meta name="google-site-verification" content="YOUR_VERIFICATION_CODE" />
```

Setup:
1. https://search.google.com/search-console
2. Add property: bonidoc.com
3. Verify via DNS or meta tag
4. Submit sitemap
5. Features: Search performance, indexing status, mobile usability

**Umami Analytics (Self-Hosted Alternative - Optional):**
```bash
# If you want privacy-focused self-hosted analytics
docker run -d \
  --name umami \
  -p 3002:3000 \
  -e DATABASE_URL=postgresql://user:pass@host/umami \
  ghcr.io/umami-software/umami:postgresql-latest
```

**Error Monitoring - Sentry (Free: 5k errors/month):**

Backend setup:
```python
# backend/requirements.txt
sentry-sdk[fastapi]

# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "production"),
    traces_sample_rate=0.1,
    integrations=[FastApiIntegration()]
)
```

Frontend setup:
```typescript
// frontend/src/app/layout.tsx
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
});
```

### 7.3 Email Service Setup

**RECOMMENDATION: Use Resend (3,000 emails/month FREE)**

**Why NOT build your own:**
- ❌ Deliverability nightmare (spam filters, blacklists)
- ❌ Need to manage SMTP, DKIM, SPF, DMARC records
- ❌ High maintenance overhead
- ❌ Risk of email bounces affecting domain reputation
- ❌ No email tracking or analytics
- ✅ Third-party services handle all of this

**Resend Setup (Recommended - Free Tier):**

1. Sign up: https://resend.com
2. Add domain: bonidoc.com
3. Add DNS records (provided by Resend):
```
TXT  @  "v=spf1 include:_spf.resend.com ~all"
TXT  resend._domainkey  "YOUR_DKIM_KEY"
CNAME resend  mail.resend.com
```

4. Backend integration:
```python
# backend/requirements.txt
resend

# backend/app/services/email_service.py
import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")

class EmailService:
    @staticmethod
    async def send_welcome_email(user_email: str, user_name: str):
        params = {
            "from": "BoniDoc <noreply@bonidoc.com>",
            "to": [user_email],
            "subject": "Welcome to BoniDoc!",
            "html": f"<h1>Welcome {user_name}!</h1>..."
        }
        return resend.Emails.send(params)

    @staticmethod
    async def send_payment_confirmation(user_email: str, amount: float, plan: str):
        params = {
            "from": "BoniDoc <billing@bonidoc.com>",
            "to": [user_email],
            "subject": f"Payment Confirmed - {plan} Plan",
            "html": f"<h1>Thank you for subscribing!</h1>..."
        }
        return resend.Emails.send(params)
```

**Alternative Free Options:**
- **SendGrid**: 100 emails/day free (3,000/month)
- **Brevo (Sendinblue)**: 300 emails/day free
- **SMTP2GO**: 1,000 emails/month free

**Email Templates Needed:**
1. Welcome email (on signup)
2. Payment confirmation
3. Subscription expiration warning
4. Password reset (future)
5. Monthly usage summary (future)

### 7.4 User Tier System

**Database Schema:**
```sql
-- Add to users table
ALTER TABLE users ADD COLUMN tier INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN tier_expires_at TIMESTAMP;
ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255);
ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(255);
ALTER TABLE users ADD COLUMN stripe_subscription_status VARCHAR(50);
ALTER TABLE users ADD COLUMN pages_used_this_month INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN usage_reset_date TIMESTAMP DEFAULT NOW();

-- Add to system_settings
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('tier_0_pages', '50', 'Free tier monthly page limit'),
('tier_1_pages', '250', 'Starter tier monthly page limit'),
('tier_2_pages', '1500', 'Pro tier monthly page limit'),
('tier_100_pages', '-1', 'Admin tier (unlimited)');
```

**Backend Implementation:**
```python
# backend/app/core/tiers.py
from enum import IntEnum

class UserTier(IntEnum):
    FREE = 0
    STARTER = 1
    PRO = 2
    ADMIN = 100

TIER_FEATURES = {
    UserTier.FREE: {
        "pages_per_month": 50,
        "multi_category": False,
        "bulk_operations": False,
        "bulk_limit": 1,
        "api_access": False,
        "custom_keywords": False
    },
    UserTier.STARTER: {
        "pages_per_month": 250,
        "multi_category": True,
        "bulk_operations": True,
        "bulk_limit": 20,
        "api_access": False,
        "custom_keywords": True
    },
    UserTier.PRO: {
        "pages_per_month": 1500,
        "multi_category": True,
        "bulk_operations": True,
        "bulk_limit": -1,  # unlimited
        "api_access": True,
        "custom_keywords": True,
        "email_to_upload": True
    },
    UserTier.ADMIN: {
        "pages_per_month": -1,  # unlimited
        "multi_category": True,
        "bulk_operations": True,
        "bulk_limit": -1,
        "api_access": True,
        "custom_keywords": True,
        "admin_dashboard": True
    }
}

def check_tier_access(user_tier: int, feature: str) -> bool:
    """Check if user tier has access to feature"""
    return TIER_FEATURES.get(user_tier, TIER_FEATURES[0]).get(feature, False)

def get_tier_limit(user_tier: int, limit_type: str) -> int:
    """Get tier-specific limit"""
    return TIER_FEATURES.get(user_tier, TIER_FEATURES[0]).get(limit_type, 0)

# backend/app/middleware/tier_middleware.py
from functools import wraps
from fastapi import HTTPException, status

def require_tier(min_tier: int, feature: str = None):
    """Decorator to enforce tier requirements"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=None, **kwargs):
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if current_user.tier < min_tier:
                tier_names = {0: "Free", 1: "Starter", 2: "Pro"}
                required_tier_name = tier_names.get(min_tier, "Premium")
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"This feature requires {required_tier_name} plan or higher"
                )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

**Usage Tracking:**
```python
# backend/app/services/usage_service.py
from datetime import datetime, timedelta
from sqlalchemy import func

class UsageService:
    @staticmethod
    async def track_page_usage(user_id: str, pages_processed: int):
        """Track pages processed for billing"""
        user = session.get(User, user_id)

        # Reset counter if month has passed
        if user.usage_reset_date < datetime.utcnow() - timedelta(days=30):
            user.pages_used_this_month = 0
            user.usage_reset_date = datetime.utcnow()

        user.pages_used_this_month += pages_processed
        session.commit()

    @staticmethod
    async def check_usage_limit(user_id: str, pages_to_process: int) -> bool:
        """Check if user has remaining quota"""
        user = session.get(User, user_id)
        limit = get_tier_limit(user.tier, "pages_per_month")

        if limit == -1:  # unlimited
            return True

        return (user.pages_used_this_month + pages_to_process) <= limit
```

### 7.5 Admin Dashboard

**Route Protection:**
```python
# backend/app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.middleware.auth_middleware import get_current_admin_user

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 50,
    tier: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user)
):
    """List all users (admin only)"""
    query = session.query(User)

    if tier is not None:
        query = query.filter(User.tier == tier)

    if status:
        query = query.filter(User.is_active == (status == 'active'))

    total = query.count()
    users = query.offset((page-1)*page_size).limit(page_size).all()

    return {
        "users": [user.to_dict() for user in users],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.patch("/users/{user_id}/tier")
async def update_user_tier(
    user_id: str,
    new_tier: int,
    current_user: User = Depends(get_current_admin_user)
):
    """Update user tier (admin only)"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.tier = new_tier
    session.commit()

    # Log admin action
    await audit_log.log_action(
        admin_id=current_user.id,
        action="update_user_tier",
        target_user_id=user_id,
        details={"old_tier": user.tier, "new_tier": new_tier}
    )

    return {"success": True, "user": user.to_dict()}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Delete user account (admin only)"""
    # Reuse existing hard delete logic from user_service
    result = await user_service.deactivate_user_account(user_id, ...)
    return result
```

**Frontend Admin Dashboard:**
```typescript
// frontend/src/app/admin/page.tsx
'use client'

export default function AdminDashboard() {
  const [users, setUsers] = useState([])
  const [filters, setFilters] = useState({ tier: null, status: null })

  useEffect(() => {
    loadUsers()
  }, [filters])

  const loadUsers = async () => {
    const data = await apiClient.get('/api/v1/admin/users', true, filters)
    setUsers(data.users)
  }

  const updateTier = async (userId: string, newTier: number) => {
    await apiClient.patch(`/api/v1/admin/users/${userId}/tier`,
      { new_tier: newTier }, true)
    loadUsers()
  }

  return (
    <div>
      <h1>Admin Dashboard</h1>

      {/* Filters */}
      <div>
        <select onChange={(e) => setFilters({...filters, tier: e.target.value})}>
          <option value="">All Tiers</option>
          <option value="0">Free</option>
          <option value="1">Starter</option>
          <option value="2">Pro</option>
        </select>
      </div>

      {/* Users Table */}
      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Tier</th>
            <th>Pages Used</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.id}>
              <td>{user.email}</td>
              <td>
                <select value={user.tier}
                        onChange={(e) => updateTier(user.id, e.target.value)}>
                  <option value="0">Free</option>
                  <option value="1">Starter</option>
                  <option value="2">Pro</option>
                  <option value="100">Admin</option>
                </select>
              </td>
              <td>{user.pages_used_this_month}</td>
              <td>{new Date(user.created_at).toLocaleDateString()}</td>
              <td>
                <button onClick={() => deleteUser(user.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

### 7.6 Stripe Integration

**Setup:**
1. Create Stripe account: https://dashboard.stripe.com
2. Add products:
   - Starter: €2.99/month recurring
   - Pro: €7.99/month recurring (coming soon)

**Backend Webhook:**
```python
# backend/app/api/stripe.py
import stripe
from fastapi import APIRouter, Request, HTTPException

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
router = APIRouter(prefix="/api/v1/stripe", tags=["stripe"])

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle different events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await handle_successful_payment(session)

    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        await handle_subscription_update(subscription)

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        await handle_subscription_cancellation(subscription)

    return {"status": "success"}

async def handle_successful_payment(session):
    """Upgrade user tier on successful payment"""
    user_email = session['customer_email']
    stripe_customer_id = session['customer']
    subscription_id = session['subscription']

    user = session.query(User).filter(User.email == user_email).first()
    if user:
        user.stripe_customer_id = stripe_customer_id
        user.stripe_subscription_id = subscription_id
        user.stripe_subscription_status = 'active'
        user.tier = 1  # Starter tier
        user.tier_expires_at = None  # subscription-based
        session.commit()

        # Send confirmation email
        await email_service.send_payment_confirmation(user.email, 2.99, "Starter")

@router.post("/create-checkout-session")
async def create_checkout_session(
    price_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Create Stripe checkout session"""
    checkout_session = stripe.checkout.Session.create(
        customer_email=current_user.email,
        payment_method_types=['card'],
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=f"{settings.app.app_frontend_url}/settings?payment=success",
        cancel_url=f"{settings.app.app_frontend_url}/settings?payment=cancelled",
    )

    return {"checkout_url": checkout_session.url}
```

**Frontend Integration:**
```typescript
// frontend/src/app/settings/page.tsx
const handleUpgrade = async (tier: 'starter' | 'pro') => {
  const priceIds = {
    starter: process.env.NEXT_PUBLIC_STRIPE_STARTER_PRICE_ID,
    pro: process.env.NEXT_PUBLIC_STRIPE_PRO_PRICE_ID
  }

  const response = await apiClient.post('/api/v1/stripe/create-checkout-session',
    { price_id: priceIds[tier] }, true)

  // Redirect to Stripe Checkout
  window.location.href = response.checkout_url
}
```

### 7.7 Legal Compliance (GDPR)

**Terms & Privacy Acceptance:**
```sql
-- Add to users table
ALTER TABLE users ADD COLUMN terms_accepted_at TIMESTAMP;
ALTER TABLE users ADD COLUMN privacy_accepted_at TIMESTAMP;
ALTER TABLE users ADD COLUMN gdpr_consent BOOLEAN DEFAULT FALSE;
```

**Acceptance Modal (Frontend):**
```typescript
// frontend/src/components/TermsAcceptanceModal.tsx
export default function TermsAcceptanceModal() {
  const [accepted, setAccepted] = useState(false)

  const handleAccept = async () => {
    await apiClient.post('/api/v1/auth/accept-terms', {
      terms_version: '1.0',
      privacy_version: '1.0'
    }, true)

    window.location.reload()
  }

  return (
    <Modal>
      <h2>Welcome to BoniDoc!</h2>
      <p>Please review and accept our terms to continue.</p>

      <div>
        <a href="/legal/terms" target="_blank">Terms of Service</a>
        <a href="/legal/privacy" target="_blank">Privacy Policy</a>
      </div>

      <label>
        <input type="checkbox" checked={accepted}
               onChange={(e) => setAccepted(e.target.checked)} />
        I accept the Terms of Service and Privacy Policy
      </label>

      <button disabled={!accepted} onClick={handleAccept}>
        Continue
      </button>
    </Modal>
  )
}
```

### 7.8 Go-Live Checklist

**Critical (Must Complete):**
- [ ] Dev/Prod environments separated
- [ ] User tier system implemented (0, 1, 2, 100)
- [ ] Admin dashboard functional (bonifatus.app@gmail.com = tier 100)
- [ ] Stripe integration tested
- [ ] Email service configured (Resend)
- [ ] Analytics configured (Cloudflare + Google Search Console)
- [ ] Error monitoring (Sentry)
- [ ] Terms/Privacy acceptance flow
- [ ] SSL certificates valid and auto-renewing
- [ ] Database backups automated (daily cron)
- [ ] Bulk operations implemented (tier-gated)

**High Priority (Week 1):**
- [ ] Usage tracking and limits enforced
- [ ] Subscription management in Settings page
- [ ] Tier upgrade prompts in UI
- [ ] Admin can view/edit all users
- [ ] Payment confirmation emails
- [ ] SEO: sitemap.xml, robots.txt, meta tags

**Medium Priority (Week 2-4):**
- [ ] Refund handling
- [ ] Subscription cancellation flow
- [ ] Monthly usage reports
- [ ] Admin analytics dashboard
- [ ] Rate limiting per tier

**Recommended Timeline:**
- **Day 1-2**: Dev/Prod, Tier System, Email Service
- **Day 3**: Admin Dashboard, Bulk Operations
- **Day 4**: Stripe Integration
- **Day 5**: Analytics, Legal, Testing
- **Day 6**: Soft Launch (Free + Starter only)
- **Week 2**: Monitor, iterate, prepare Pro tier

---

## 8. Implementation Standards

### 8.1 Code Quality (Before Any Commit)

- ✅ **Modular Structure:** Single responsibility, <300 lines per file
- ✅ **No Design Elements:** Design system separated from business logic
- ✅ **No Hardcoding:** All config from database or environment variables
- ✅ **Production-Ready:** Zero workarounds, no TODO comments, no fallbacks
- ✅ **Multi-Input Support:** Mouse, keyboard, touch tested
- ✅ **Documented:** File headers, function comments, complex logic explained
- ✅ **Clear Naming:** Concise names without marketing terms
- ✅ **Test Coverage:** Unit tests written and passing
- ✅ **Duplicate Check:** Review existing code before adding new functions

### 7.2 Language Support Standards

- **UI Language:** Single selection in user_settings, controls interface only
- **Document Language:** Multi-selection in preferred_doc_languages (JSONB), controls processing
- **Translations:** No hardcoded language lists; all from system_settings.supported_languages
- **Categories:** Auto-translate to languages in user's preferred_doc_languages only
- **Fallback:** English only (["en"])

### 7.3 Categories & Keywords

**Default System Categories (cannot be deleted):**
1. Insurance (INS) - policies, claims, coverage
2. Legal (LEG) - contracts, agreements, legal docs
3. Real Estate (RES) - property, deeds, mortgages
4. Banking (BNK) - bank statements, transactions
5. Invoices (INV) - bills, payment requests
6. Taxes (TAX) - tax returns, receipts
7. Other (OTH) - miscellaneous, fallback

**Supported Languages:** English (en), German (de), Russian (ru), French (fr)

---

## 9. Deployment & Operations

### 9.1 Current Deployment Status

- **Backend:** Docker container on Hetzner, auto-restarts
- **Frontend:** PM2 + Next.js on Hetzner
- **Database:** PostgreSQL 16 local on Hetzner with SSL
- **Migrations:** Alembic chain (10 applied, clean)
- **CI/CD:** Manual SSH deployment (GitHub Actions disabled)
- **Health Checks:** curl https://api.bonidoc.com/health + https://bonidoc.com

### 8.2 Routine Code Deployment (Most Common)

**CRITICAL: When to Use Docker Cache vs --no-cache**

Docker cache is **SAFE and RECOMMENDED** for 95% of deployments. Use this simple rule:

#### ✅ Use Cache (DEFAULT) - Fast Build (2-3 min)

```bash
docker compose build
```

**Use for ALL of these changes:**
- ✅ Python code changes (any .py file)
- ✅ TypeScript/JavaScript changes (any .ts/.tsx/.js file)
- ✅ requirements.txt changes (adding/updating packages)
- ✅ package.json changes (adding/updating npm packages)
- ✅ Configuration file changes (.env, config.py, etc.)
- ✅ Database migrations (run at runtime, not build time)
- ✅ HTML/CSS/static file changes
- ✅ **Daily deployments, bug fixes, feature additions**

**Why it's safe:** Docker detects file changes and rebuilds from that point forward. Your changes WILL be deployed.

#### ❌ Use --no-cache - Slow Build (10-15 min)

```bash
docker compose build --no-cache
```

**ONLY use for these rare situations:**
- ❌ Monthly maintenance (force fresh system packages)
- ❌ Changing Dockerfile base image (e.g., `FROM python:3.11` → `FROM python:3.12`)
- ❌ System dependency updates (apt-get packages need security updates)
- ❌ Debugging build issues (suspected cache corruption)
- ❌ First deployment to new server
- ❌ After major Docker/OS upgrades

**Why it's slow:** Downloads and installs everything from scratch, even if unchanged.

#### Decision Tree

```
┌─────────────────────────────────────┐
│ What did you change?                │
└─────────────┬───────────────────────┘
              │
      ┌───────┴───────┐
      │               │
  Code/Config?    System/Base?
      │               │
      │               │
   YES│            NO│
      │               │
      ▼               ▼
┌─────────────┐ ┌──────────────────┐
│   USE CACHE │ │ USE --no-cache   │
│  (default)  │ │   (rare)         │
│             │ │                  │
│ ✅ Fast     │ │ ⚠️ Slow          │
│ ✅ Safe     │ │ ⚠️ Only when     │
│ ✅ Changes  │ │    needed        │
│    deployed │ │                  │
└─────────────┘ └──────────────────┘
```

#### How to Know if Cache Worked

Watch the build output:

**✅ Cache Hit (Old Layers Reused):**
```
#5 [3/10] RUN apt-get update && apt-get install -y gcc
#5 CACHED
```
→ No changes in system packages, using cached layer

**✅ Cache Miss (Rebuilding from Here):**
```
#8 [6/10] COPY backend/ /app/
#8 0.234s done
#9 [7/10] RUN pip install -r requirements.txt
#9 12.3s done
```
→ Detected code changes, rebuilding from COPY step forward

#### Monthly Maintenance Schedule

Run this ONCE per month (not during deployments):

```bash
# First Sunday of month, 2 AM
ssh root@91.99.212.17
cd /opt/bonifatus-dms
docker compose build --no-cache backend
docker compose up -d
docker image prune -a --force  # Clean old images
```

**Purpose:** Ensures system packages are up-to-date with security patches.

#### Common Deployment Workflows

**🟢 Normal Deployment (95% of time):**
```bash
ssh root@91.99.212.17
cd /opt/bonifatus-dms
git pull origin main
docker compose build              # ← WITH cache
docker compose up -d
docker compose ps
```
**Time:** 2-3 minutes
**Use for:** Code changes, bug fixes, new features

**🟡 Dev Deployment:**
```bash
ssh root@91.99.212.17
cd /opt/bonifatus-dms-dev
git pull origin main
docker compose build              # ← WITH cache
docker compose up -d
nginx -t && systemctl reload nginx  # IP whitelist
```
**Time:** 2-3 minutes
**Use for:** Testing before production

**🔴 Monthly Maintenance (rare):**
```bash
ssh root@91.99.212.17
cd /opt/bonifatus-dms
docker compose build --no-cache backend  # ← NO cache
docker compose up -d
docker image prune -a --force
```
**Time:** 10-15 minutes
**Use for:** First Sunday of month, system updates

**Simple push - takes 2-3 minutes:**

```bash
ssh deploy@YOUR_SERVER_IP
~/deploy.sh
```

**The deploy script:**
- Pulls latest code from GitHub
- Rebuilds Docker images **with cache** (default behavior)
- Stops containers gracefully
- Starts containers with new code
- Verifies health checks

**Post-deployment verification:**
```bash
# 1. Backend health
curl https://api.bonidoc.com/health

# 2. Frontend health
curl https://bonidoc.com

# 3. Database verification
docker exec bonifatus-backend alembic current

# 4. Smoke test
# - Login with Google OAuth
# - Create test category
# - Upload test document
# - Verify categorization
```

### 8.2a Development Environment Deployment

**Deploy to Dev (dev.bonidoc.com) - Test Before Production**

Development environment is isolated from production with:
- Separate database (`bonifatus_dms_dev`)
- Different ports (3001/8081/5001)
- Different container names (with `-dev` suffix)
- Debug logs enabled
- Clean test data

**⚠️ IMPORTANT:** Always test features on dev first before deploying to production!

**Critical Configuration - Dev docker-compose.yml**

The dev environment MUST have these specific settings to avoid conflicts with production:

```yaml
services:
  backend:
    build: ./backend
    container_name: bonifatus-backend-dev    # ⚠️ MUST have -dev suffix
    ports:
      - "8081:8080"                          # ⚠️ External port 8081 (not 8080)
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      args:
        NEXT_PUBLIC_API_URL: https://api-dev.bonidoc.com  # ⚠️ MUST use dev API
    container_name: bonifatus-frontend-dev   # ⚠️ MUST have -dev suffix
    ports:
      - "3001:3000"                          # ⚠️ External port 3001 (not 3000)
    restart: unless-stopped
    depends_on:
      - backend

  libretranslate:
    image: libretranslate/libretranslate:latest
    container_name: bonifatus-translator-dev # ⚠️ MUST have -dev suffix
    restart: unless-stopped
    user: "0:0"
    ports:
      - "127.0.0.1:5001:5000"                # ⚠️ External port 5001 (not 5000)
    environment:
      - LT_HOST=0.0.0.0
      - LT_PORT=5000
      - LT_CHAR_LIMIT=5000
      - LT_LOAD_ONLY=en,de,ru,fr
    volumes:
      - ./translator-data:/app/db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/languages"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 120s
```

**Key Differences from Production:**

| Setting | Production | Development |
|---------|-----------|-------------|
| **Container Names** | `bonifatus-backend` | `bonifatus-backend-dev` |
| | `bonifatus-frontend` | `bonifatus-frontend-dev` |
| | `bonifatus-translator` | `bonifatus-translator-dev` |
| **Backend Port** | 8080 | 8081 |
| **Frontend Port** | 3000 | 3001 |
| **Translator Port** | 5000 | 5001 |
| **API URL** | `https://api.bonidoc.com` | `https://api-dev.bonidoc.com` |
| **Database** | `bonifatus_dms` | `bonifatus_dms_dev` |
| **Debug Mode** | `false` | `true` |
| **ClamAV** | Enabled | Disabled (CLAMAV_ENABLED=false) |
| **IP Whitelist** | None (public) | Yes (specific IPs only) |
| **CORS Origins** | `bonidoc.com` | `dev.bonidoc.com` |

**⚠️ CRITICAL:** If you see container name conflicts during deployment, the docker-compose.yml was not configured correctly. The `-dev` suffix on container names is MANDATORY to prevent conflicts with production containers.

**Keeping Dev and Prod in Sync:**

Both environments run identical code but with different configurations. To sync:

```bash
# Sync code to both environments (after git push)
ssh root@91.99.212.17

# Update production
cd /opt/bonifatus-dms
git pull origin main
docker compose build
docker compose up -d

# Update development
cd /opt/bonifatus-dms-dev
git pull origin main
docker compose build
docker compose up -d

# Verify both are in sync
curl -s https://api.bonidoc.com/health | grep environment    # Should show "production"
curl -s https://api-dev.bonidoc.com/health | grep environment # Should show "development"
```

**⚠️ Environment-Specific Files (NEVER SYNC):**
- `.env` files contain environment-specific secrets and settings
- `docker-compose.yml` files contain environment-specific ports/names
- Database contents are separate (prod data ≠ dev data)
- **Nginx config for dev includes IP whitelist (see §8.2b)**

**Common Sync Issues:**

1. **Frontend calling wrong API** → Rebuild frontend with `--no-cache`
2. **CORS errors** → Check `APP_CORS_ORIGINS` in `.env` matches frontend URL
3. **Container name conflicts** → Verify `-dev` suffix in dev docker-compose.yml
4. **Database connection errors** → Check pg_hba.conf has entry for dev network (172.21.0.0/16)

**Step 1: Deploy code changes to dev**

```bash
ssh root@91.99.212.17

# Navigate to dev directory
cd /opt/bonifatus-dms-dev

# Pull latest code
git pull origin main

# Rebuild containers (WITH CACHE - see §8.2 for cache decision)
docker compose build              # ← Default: uses cache (2-3 min)
# Only use --no-cache for monthly maintenance or system updates

# Restart containers
docker compose up -d

# Reload nginx (CRITICAL for IP whitelist)
nginx -t && systemctl reload nginx

# Check status
docker compose ps
```

**⚠️ Cache Usage:** Unless you're doing monthly maintenance or changed the Dockerfile base image, **always use cache** (default `docker compose build`). Your code changes WILL be deployed. See §8.2 for full cache decision tree.

**⚠️ If frontend is calling wrong API (CORS errors):**

If you see CORS errors like "Access to fetch at 'https://api.bonidoc.com' from origin 'https://dev.bonidoc.com' has been blocked", the frontend was built with wrong API URL. Rebuild with:

```bash
cd /opt/bonifatus-dms-dev

# Force rebuild frontend with correct API URL
docker compose build frontend --no-cache
docker compose up -d frontend

# Verify it's calling dev API (should show api-dev.bonidoc.com)
curl -s https://dev.bonidoc.com | grep -o 'api[^"]*bonidoc.com' | head -1
```

**Step 2: Verify dev deployment**

```bash
# 1. Backend health
curl https://api-dev.bonidoc.com/health

# 2. Frontend health
curl https://dev.bonidoc.com

# 3. Database verification
docker exec bonifatus-backend-dev alembic current

# 4. Check debug logs are enabled
grep -i debug /opt/bonifatus-dms-dev/.env
grep -i debug /opt/bonifatus-dms-dev/docker-compose.yml

# Should show:
# APP_DEBUG_MODE=true
# NEXT_PUBLIC_DEBUG_LOGS: "true"
```

**Step 3: Test the feature**

- Open browser to https://dev.bonidoc.com
- Test all new functionality thoroughly
- Check browser console for debug logs
- Verify database changes (if any)

**Step 4: Once verified, deploy to production**

```bash
# After dev testing passes, deploy to prod
cd /opt/bonifatus-dms

# ⚠️ NEVER copy .env or docker-compose.yml from dev!
# Only copy application code files

# Pull code (or rsync specific files)
git pull origin main

# Rebuild and restart
docker compose build
docker compose up -d
```

**Important Notes:**
- **Credentials:** See `HETZNER_SETUP_ACTUAL.md` for dev database credentials
- **Migration Guide:** See `/opt/DEV_TO_PROD_MIGRATION.md` for variables that must NOT be copied
- **Debug Logs:** Always verify debug is `false` on prod after deployment
- **Testing:** Always test on dev.bonidoc.com before deploying to bonidoc.com

### 8.2b IP Whitelist and Nginx Reload (CRITICAL for Dev Access)

**⚠️ MANDATORY: After EVERY Dev Deployment**

After deploying to dev, you MUST reload nginx to maintain IP whitelist access:

```bash
ssh root@91.99.212.17 "nginx -t && systemctl reload nginx"
```

**Updated Dev Deployment Procedure (with Nginx reload):**

```bash
ssh root@91.99.212.17
cd /opt/bonifatus-dms-dev
git pull origin main
docker compose build
docker compose up -d

# ⚠️ CRITICAL: Reload nginx after container restart
nginx -t && systemctl reload nginx

# Run migrations if needed
docker exec bonifatus-backend-dev alembic upgrade head

docker compose ps
exit
```

**If Access Is Still Blocked After Deployment:**

Your IPv6 subnet may have changed (common with dynamic IPv6). Check your current IPv6:

```powershell
# On Windows PC:
ipconfig | findstr "IPv6"
```

Look for the IPv6 address starting with `2003:fb:f0e:fc6a:` (your current subnet).

**Update Nginx Whitelist with New IPv6 Subnet:**

If your subnet changed (e.g., from `fc6a` to a different value):

```bash
ssh root@91.99.212.17

# Check current whitelist
grep "allow 2003" /etc/nginx/sites-available/dev.bonidoc.com

# Update to new subnet (replace fc6a with your new subnet)
sed -i 's|2003:fb:f0e:fc6a::/64|2003:fb:f0e:NEW_SUBNET::/64|g' /etc/nginx/sites-available/dev.bonidoc.com

# Reload nginx
nginx -t && systemctl reload nginx
```

**Current Whitelisted IPs:**
- IPv4: `93.197.148.73` (home PC public IP)
- IPv6: `2003:fb:f0e:fc6a::/64` (home PC IPv6 subnet)

**Whitelist Location:**
`/etc/nginx/sites-available/dev.bonidoc.com` (both frontend and API server blocks)

### 8.3 Database Migrations

**Check current status:**
```bash
docker exec bonifatus-backend alembic current
docker exec bonifatus-backend alembic history --verbose
```

**Apply pending migrations:**
```bash
# Backup first (always!)
pg_dump -U bonifatus -d bonifatus_dms > backup_$(date +%Y%m%d).sql

# Apply
docker exec bonifatus-backend alembic upgrade head

# Verify
docker exec bonifatus-backend alembic current
```

**Create new migration:**
```bash
cd backend
alembic revision --autogenerate -m "description"
# Edit migration file
git commit -am "Add migration: description"
git push origin main
ssh deploy@YOUR_SERVER_IP ~/deploy.sh
```

**Rollback one migration:**
```bash
docker exec bonifatus-backend alembic downgrade -1
docker exec bonifatus-backend alembic current
```

### 8.3a Database Access

**Direct Database Access - Production**

Access the production PostgreSQL database directly from the server:

```bash
# SSH to server first
ssh root@91.99.212.17

# Access production database (interactive mode)
PGPASSWORD=<PRODUCTION_DB_PASSWORD> psql -U bonifatus -h localhost -d bonifatus_dms

# Run a single query
PGPASSWORD=<PRODUCTION_DB_PASSWORD> psql -U bonifatus -h localhost -d bonifatus_dms -c "SELECT version_num FROM alembic_version;"

# View table structure
PGPASSWORD=<PRODUCTION_DB_PASSWORD> psql -U bonifatus -h localhost -d bonifatus_dms -c "\d email_templates"

# List all tables
PGPASSWORD=<PRODUCTION_DB_PASSWORD> psql -U bonifatus -h localhost -d bonifatus_dms -c "\dt"
```

**Direct Database Access - Development**

Access the development PostgreSQL database:

```bash
# SSH to server first
ssh root@91.99.212.17

# Access development database (interactive mode)
PGPASSWORD=<DEV_DB_PASSWORD> psql -U bonifatus_dev -h localhost -d bonifatus_dms_dev

# Run a single query
PGPASSWORD=<DEV_DB_PASSWORD> psql -U bonifatus_dev -h localhost -d bonifatus_dms_dev -c "SELECT version_num FROM alembic_version;"

# View table structure
PGPASSWORD=<DEV_DB_PASSWORD> psql -U bonifatus_dev -h localhost -d bonifatus_dms_dev -c "\d email_templates"
```

**Database Credentials Reference**

All database passwords are stored in `HETZNER_SETUP_ACTUAL.md`. **Never commit this file to git.**

| Environment | Database | User | Password Placeholder | Find Password In |
|------------|----------|------|---------------------|------------------|
| **Production** | `bonifatus_dms` | `bonifatus` | `<PRODUCTION_DB_PASSWORD>` | `HETZNER_SETUP_ACTUAL.md` § Database (line 67) |
| **Development** | `bonifatus_dms_dev` | `bonifatus_dev` | `<DEV_DB_PASSWORD>` | `HETZNER_SETUP_ACTUAL.md` § Development Database (line 106) |

**How to Find the Actual Passwords:**

1. Open `HETZNER_SETUP_ACTUAL.md` (located in project root)
2. For production password: Search for "**Password:** BoniDoc" (section "Database")
3. For development password: Search for "**Password:** BoniDocDev" (section "Development Database")
4. Replace the placeholders in commands above with actual passwords

**Common Database Queries**

```bash
# Check current migration version
PGPASSWORD=<PRODUCTION_DB_PASSWORD> psql -U bonifatus -h localhost -d bonifatus_dms -c "SELECT version_num FROM alembic_version;"

# List all email templates
PGPASSWORD=<PRODUCTION_DB_PASSWORD> psql -U bonifatus -h localhost -d bonifatus_dms -c "SELECT name, display_name, category FROM email_templates ORDER BY name;"

# Check subscription data
PGPASSWORD=<PRODUCTION_DB_PASSWORD> psql -U bonifatus -h localhost -d bonifatus_dms -c "SELECT id, stripe_subscription_id, stripe_price_id, status FROM subscriptions ORDER BY created_at DESC LIMIT 10;"

# View currency settings
PGPASSWORD=<PRODUCTION_DB_PASSWORD> psql -U bonifatus -h localhost -d bonifatus_dms -c "SELECT code, symbol, name, exchange_rate FROM currencies WHERE is_active = true;"
```

**Important Notes:**
- **Credentials:** All passwords in `HETZNER_SETUP_ACTUAL.md` (never commit this file)
- **SSL Required:** PostgreSQL connections require SSL (configured in `pg_hba.conf`)
- **Password Method:** Use `PGPASSWORD` environment variable to avoid interactive password prompts
- **Host Access:** The `psql` command is available on the host system (not in Docker containers)
- **Connection:** Always use `-h localhost` when connecting from the Hetzner server

### 8.4 Feature Deployments (Example: Add New Language)

**Step 1: Add language support to backend**
```bash
# Add stop words for new language
docker exec bonifatus-backend python scripts/add_[language]_stopwords.py

# Update supported languages
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "UPDATE system_settings SET setting_value='en,de,ru,fr,[code]' WHERE setting_key='supported_languages';"

# Verify
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT COUNT(*) FROM stop_words WHERE language_code='[code]';"
```

**Step 2: Frontend is automatic**
- Reads language list from system_settings
- No hardcoding needed

**Step 3: Test end-to-end**
1. Change UI language to new language
2. Upload document in new language
3. Verify detection
4. Create category and verify auto-translation

### 8.5 Monitoring & Logs

**View logs:**
```bash
docker-compose logs -f backend              # Live backend logs
docker-compose logs -f frontend             # Live frontend logs
docker-compose logs --tail=100 backend      # Last 100 lines
docker-compose logs --since 2025-11-03 backend
```

**Database monitoring:**
```bash
# Check audit logs
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms << EOF
SELECT event_type, user_id, created_at, details 
FROM audit_logs 
ORDER BY created_at DESC 
LIMIT 50;
EOF

# Check slow queries
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### 8.6 Backup & Recovery

**Daily backup:**
```bash
pg_dump -U bonifatus -d bonifatus_dms > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Restore from backup:**
```bash
psql -U bonifatus -d bonifatus_dms < backup_YYYYMMDD.sql
psql -U bonifatus -d bonifatus_dms -c "SELECT COUNT(*) FROM documents;"  # Verify
```

**Disaster recovery:**
```bash
# 1. Stop services
docker-compose down

# 2. Backup current database (for debugging)
pg_dump -U bonifatus -d bonifatus_dms > backup_corrupted_$(date +%Y%m%d).sql

# 3. Drop and recreate
dropdb -U bonifatus bonifatus_dms
createdb -U bonifatus bonifatus_dms

# 4. Restore from clean backup
psql -U bonifatus -d bonifatus_dms < clean_backup.sql

# 5. Restart and run migrations
docker-compose up -d
docker exec bonifatus-backend alembic upgrade head

# 6. Verify
docker-compose ps
curl https://api.bonidoc.com/health
```

### 8.7 Complete Rollback (Code + Database)

```bash
ssh deploy@YOUR_SERVER_IP

# Backup current broken state
pg_dump -U bonifatus -d bonifatus_dms > backup_broken_$(date +%Y%m%d).sql

# Restore last known good state
psql -U bonifatus -d bonifatus_dms < backup_working_YYYYMMDD.sql

# Revert code
git revert HEAD
git push origin main

# Deploy reverted version
~/deploy.sh
```

### 8.8 Scaling & Performance

**Monitor resource usage:**
```bash
docker stats                    # Real-time stats
docker-compose logs backend | grep memory
df -h                          # Disk usage
du -sh ~/bonidoc-dms          # App directory
```

**Database optimization:**
```bash
# Create indexes on frequently queried columns
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms << EOF
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_document_categories_doc ON document_categories(document_id);
CREATE INDEX idx_category_keywords_cat ON category_keywords(category_id);
EOF

# Analyze query plans
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "EXPLAIN ANALYZE SELECT * FROM documents WHERE user_id = '...';"
```

**PostgreSQL tuning (for CPX22 - 2vCPU, 4GB RAM):**
```bash
# Edit /etc/postgresql/16/main/postgresql.conf
shared_buffers = 1GB                      # 25% of RAM
effective_cache_size = 3GB                # 75% of RAM
maintenance_work_mem = 256MB
work_mem = 52MB
wal_compression = on
max_connections = 200
```

### 8.9 Troubleshooting Guide

**Backend container won't start:**
```bash
docker-compose logs backend
# Check: JSONB imports, database connectivity, environment variables
# Common fixes:
# - Missing dependencies: docker-compose build --no-cache backend
# - Database connection: verify DATABASE_URL in .env
# - Port in use: docker ps | grep 8000
```

**Migration failures:**
```bash
docker exec bonifatus-backend alembic current
docker exec bonifatus-backend alembic upgrade --sql head  # See pending
docker exec bonifatus-backend alembic downgrade -1        # Rollback if needed
```

**Database connection refused:**
```bash
systemctl status postgresql
psql -U bonifatus -h localhost -d bonifatus_dms -c "SELECT 1;"
grep DATABASE_URL .env.backend
```

**Frontend won't load:**
```bash
docker-compose logs frontend
curl https://api.bonidoc.com/health          # Is backend accessible?
rm -rf .next && npm run build                 # Clear and rebuild
```

**High memory usage:**
```bash
docker stats
# If growing: Check for memory leaks, reduce OCR queue, restart container
docker-compose restart backend
```

**Slow performance:**
```bash
# Check if DB is bottleneck
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;"

# Check API response time
curl -w "Total: %{time_total}s\n" https://api.bonidoc.com/health
```

---

## 10. Configuration Reference

### 9.1 Backend Environment Variables

**Required:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/database
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=https://bonidoc.com/login
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
ENCRYPTION_KEY=your-encryption-key-32-bytes
ENVIRONMENT=production
```

**Optional:**
```bash
JWT_ACCESS_TOKEN_EXPIRE_SECONDS=900           # 15 minutes
JWT_REFRESH_TOKEN_EXPIRE_SECONDS=604800       # 7 days
RATE_LIMIT_AUTH=5                             # Login attempts/min
RATE_LIMIT_WRITE=30                           # Uploads/min
RATE_LIMIT_READ=60                            # Searches/min
OCR_QUALITY_THRESHOLD=0.7                     # Confidence threshold
TESSERACT_PATH=/usr/bin/tesseract
MAX_FILE_SIZE_MB=50
LOG_LEVEL=INFO
CORS_ORIGINS=https://bonidoc.com,https://www.bonidoc.com
```

### 9.2 Frontend Environment Variables

```bash
NEXT_PUBLIC_API_URL=https://api.bonidoc.com
```

### 9.3 Database Settings (system_settings table)

All application settings are stored as key-value pairs in `system_settings`:

```sql
SELECT * FROM system_settings;
```

**Key settings:**

| Key | Value | Purpose |
|-----|-------|---------|
| supported_languages | "en,de,ru,fr" | Available languages |
| language_metadata | {JSON with display names} | UI language names |
| default_ui_language | "en" | First login language |
| default_category | "OTH" | Fallback category |
| ocr_quality_threshold | 0.7 | PyMuPDF→Tesseract threshold |
| ocr_timeout_seconds | 60 | Max OCR time per document |
| max_file_size_bytes | 52428800 | Max file size (50MB) |
| learning_update_interval | 86400 | Daily weight updates |
| keyword_weight_increase | 0.1 | +10% for correct |
| keyword_weight_decrease | 0.05 | -5% for incorrect |
| rate_limit_auth_per_min | 5 | Login attempts |
| rate_limit_write_per_min | 30 | Uploads per minute |
| rate_limit_read_per_min | 60 | Searches per minute |
| session_timeout_seconds | 3600 | 1 hour idle timeout |

### 9.4 Database Schema Reference

**Users & Authentication:**
```sql
users (user_id, email, google_oauth_id, oauth_token, refresh_token, 
       ui_language, preferred_doc_languages, created_at)
user_settings (user_id, setting_key, setting_value)
user_sessions (session_id, user_id, ip_address, user_agent, expires_at)
```

**Categories:**
```sql
categories (category_id, user_id, code, is_system)
category_translations (translation_id, category_id, language_code, name, description)
category_keywords (keyword_id, category_id, language_code, keyword, weight)
```

**Documents:**
```sql
documents (document_id, user_id, filename, file_size_bytes, mime_type, 
           drive_file_id, detected_language, ocr_confidence, extracted_text)
document_categories (document_id, category_id, is_primary, suggested, confidence)
document_languages (document_id, language_code, confidence)
document_dates (document_id, date_type, extracted_date)
```

**Keywords & Search:**
```sql
keywords (keyword_id, keyword)
document_keywords (document_id, keyword_id, relevance_score)
stop_words (stop_word_id, language_code, word)
search_history (history_id, user_id, search_query, results_count, created_at)
```

**Google Drive:**
```sql
google_drive_folders (folder_id, user_id, category_id, drive_folder_id)
google_drive_sync_status (sync_id, user_id, last_sync, quota_bytes_used, sync_status)
```

**ML & Logging:**
```sql
document_classification_log (log_id, document_id, user_id, 
                             suggested_category_id, actual_category_id, 
                             suggestion_confidence, user_action)
category_classification_metrics (metrics_id, category_id, date, 
                                 total_suggestions, accepted_count, accuracy)
```

**System:**
```sql
system_settings (setting_id, setting_key, setting_value)
localization_strings (string_id, string_key, language_code, string_value)
audit_logs (log_id, user_id, event_type, resource_type, resource_id,
            status, ip_address, error_message, created_at)
```

**Email:**
```sql
email_templates (id, template_key, language, subject, html_content,
                variables, description, is_active, created_at, updated_at)
UNIQUE(template_key, language)  -- One template per key per language
```

### 9.4.1 Email Service Configuration

**Provider:** Brevo (Sendinblue) - Transactional email API
**Free Tier:** 300 emails/day
**Domains:** info@bonidoc.com, no-reply@bonidoc.com
**Email Routing:** Cloudflare Email Routing (free forwarding)

**Environment Variables:**
```bash
# System environment variable (NOT in .env - same key for dev/staging/prod)
BREVO_API_KEY=xkeysib-xxxxx...  # Set via: setx BREVO_API_KEY "key" (Windows)
                                 # Or export BREVO_API_KEY="key" (Linux)

# Email addresses (.env file - not sensitive)
EMAIL_FROM_INFO=info@bonidoc.com
EMAIL_FROM_NOREPLY=no-reply@bonidoc.com
EMAIL_FROM_NAME=BoniDoc
```

**Why separate API key storage:**
- Same Brevo account/key across all environments
- Never committed to Git (security risk)
- Rotatable without code deployment
- Industry best practice

**Email Template Structure:**
- **template_key**: Identifier (e.g., `welcome_email`, `password_reset`)
- **language**: ISO 639-1 code (`en`, `de`, etc.)
- **subject**: Email subject line
- **html_content**: HTML body with `{{variable}}` placeholders
- **variables**: JSON array of variable names
- **is_active**: Enable/disable template

**Default Templates** (auto-created on migration):
1. `welcome_email` - New user account creation
2. `password_reset` - Password reset with secure link
3. `verification_code` - 2FA verification codes

**Sending Emails:**
```python
from app.services.email_service import email_service

# Basic email
await email_service.send_email(
    to_email="user@example.com",
    to_name="John Doe",
    subject="Welcome!",
    html_content="<p>Hello!</p>"
)

# Template with variables
await email_service.send_welcome_email(
    to_email="user@example.com",
    user_name="John Doe",
    login_url="https://bonidoc.com/login"
)
```

**Admin API Endpoints** (admin auth required):
```bash
GET    /api/v1/admin/email-templates          # List all templates
POST   /api/v1/admin/email-templates          # Create new template
PUT    /api/v1/admin/email-templates/{id}     # Update template
DELETE /api/v1/admin/email-templates/{id}     # Delete template
```

**Multilingual Support:**
- Store one template per language per key
- Select based on user's `preferred_doc_languages[0]`
- Fallback to English (`en`) if language unavailable

**Cloudflare Email Routing Setup:**
1. Add MX records for bonidoc.com
2. Create routing rules:
   - `info@bonidoc.com` → your.email@gmail.com
   - `no-reply@bonidoc.com` → (catch-all or specific inbox)
3. Brevo sends FROM these addresses, replies forward to your inbox

**Deployment:**
```bash
# Development
setx BREVO_API_KEY "your-key-here"  # Windows
export BREVO_API_KEY="your-key"     # Linux

# Run migration
alembic upgrade head

# Production (Railway/Vercel/etc.)
# Set BREVO_API_KEY via platform environment variables UI
```

**Monitoring:**
- Brevo dashboard: delivery rates, bounce rates, API usage
- Application logs: email send success/failure
- Free tier limit: 300 emails/day

### 9.5 Docker Compose Configuration

```yaml
services:
  backend:
    image: bonidoc-backend:latest
    container_name: bonifatus-backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://bonifatus:${DB_PASSWORD}@db:5432/bonifatus_dms
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
      ENVIRONMENT: production
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs
    networks:
      - bonidoc-net

  frontend:
    image: bonidoc-frontend:latest
    container_name: bonifatus-frontend
    restart: always
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: https://api.bonidoc.com
    networks:
      - bonidoc-net

  db:
    image: postgres:16-alpine
    container_name: bonifatus-db
    restart: always
    environment:
      POSTGRES_USER: bonifatus
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: bonifatus_dms
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - bonidoc-net

volumes:
  postgres-data:

networks:
  bonidoc-net:
```

### 9.6 Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name bonidoc.com www.bonidoc.com;
    
    ssl_certificate /etc/ssl/certs/bonidoc.com.crt;
    ssl_certificate_key /etc/ssl/private/bonidoc.com.key;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/m;
    limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
    
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/ {
        limit_req zone=api_limit burst=5 nodelay;
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location ~ /api/auth/ {
        limit_req zone=auth_limit burst=2 nodelay;
        proxy_pass http://backend:8000;
    }
}

server {
    listen 80;
    server_name bonidoc.com www.bonidoc.com;
    return 301 https://$server_name$request_uri;
}
```

### 9.7 Performance Targets

| Metric | Target |
|--------|--------|
| API response (p95) | <200ms |
| DB query (p95) | <100ms |
| Single file upload | <5s |
| Batch (10 files) | <30s |
| OCR per page | <10s |
| Page load time | <2s |

---

## 11. Feature History

### 10.1 Completed Phases

#### Phase 1: Security Foundation ✅

- Database cleanup and consolidation
- Encryption service (Fernet AES-256 for OAuth tokens)
- Session management with revocation
- 3-tier rate limiting system
- File validation service
- Security headers on all responses
- Audit logging with full context
- Replaced localStorage with httpOnly cookies
- Reduced token expiry (15min access, 7day refresh)

#### Phase 2A: OCR & Text Extraction ✅

- PyMuPDF for native PDF text extraction
- Tesseract for scanned/image PDFs
- Structure-based PDF detection: Analyzes embedded fonts, text blocks, and images to determine if PDF is native or scanned (language-agnostic, prevents false positives)
- Spell-checking validation: Post-OCR quality check using Hunspell dictionaries (en_US, de_DE, ru_RU, fr_FR)
- Image preprocessing (rotation, deskewing)
- Language detection (3-pass for accuracy)
- Keyword extraction (frequency + stop word filtering)

#### Phase 2B: Category Learning System ✅

- Classification logging (track all decisions)
- Daily accuracy metrics per category
- Keyword weight adjustment (+10% correct, -5% incorrect)
- Confidence-based suggestions
- Multi-category support (unlimited per document, one primary)

#### Phase 2C: Multi-Language Support ✅

**Supported Languages:** English, German, Russian, French

- Full UI localization
- Document language detection
- Language-specific keyword extraction
- User preference for document languages (separate from UI language)
- Category auto-translation to user's selected languages
- No hardcoded language lists (all from database)

#### Phase 3: Google Drive Integration ✅

- Automatic folder structure creation
- Document upload to category folders
- Temporary download links
- Storage quota tracking
- Sync status monitoring
- User maintains full control (can delete/move in Drive)

### 10.2 Pricing Model & Business

**Page-Based Pricing** (aligns revenue with OCR costs):

| Tier | Price | Pages/Month | Users | Features |
|------|-------|-------------|-------|----------|
| Free | €0 | 50 | Solo | Full AI, community support |
| Starter | €2.99/month | 250 | Solo | Full AI, email support |
| Professional | €7.99/month | 1,500 | Multi (3 delegates) | Full AI, priority |

**Business Advantages:**
- No storage costs (documents in Google Drive)
- Margins: 70-85% on paid tiers
- Competitive: €2.99-7.99 vs €10-30 competitors
- Fair use: soft caps (Pro can use 3,000 pages)

**Revenue Projections (Conservative):**
- 1,000 users = €1,397 MRR (€16.7k/year)
- 5,000 users = €6,985 MRR (€83.8k/year)

**Target Market:**
- Individuals: Freelancers, consultants
- Small business: 1-5 person teams
- Professional services: Accountants, lawyers

### 10.3 Historical Infrastructure Timeline

**Before October 24, 2025:** Google Cloud Run + Supabase
- Cost: €40/month
- Issues: Expensive, high latency from Germany, vendor lock-in

**Current (October 24, 2025+):** Hetzner VPS
- Cost: €8/month (80% savings!)
- Benefits: Low latency for EU, full control, predictable costs
- Server: CPX22 (2vCPU, 4GB RAM, 80GB SSD)

### 10.4 Planned Features (Not Started)

**Phase 4: Advanced Classification**
- Multi-category suggestions with confidence scores
- TOP 3 suggestions instead of ONE
- Filter by confidence threshold
- Estimated: 2-3 days

**Phase 5: User Dashboard & Analytics**
- Upload timeline
- Category breakdown charts
- Search history
- System learning progress
- Estimated: 3-4 days

**Phase 6: Performance Optimization**
- Redis caching (70% query reduction)
- Database indexing
- Query optimization (eliminate N+1)
- CDN for static assets
- Estimated: 3-4 days

**Phase 7: Mobile Native Apps** (Future)
- React Native or Flutter
- Offline support
- Same backend API
- Estimated: 4-6 weeks

### 10.5 Lessons Learned

**What Worked Well:**
- Two-stage OCR approach
- Simple learning algorithm (+10% / -5%)
- Database-driven configuration
- Page-based pricing
- httpOnly cookies for auth

**What Required Iteration:**
- Language detection (3-pass approach)
- Confidence scoring formulas
- Category internationalization
- Database schema (4 tables added during development)
- Frontend category caching

**Best Practices Adopted:**
- Always backup before migrations
- Test language features with real documents
- Store all feature flags in database
- Log security events with full context
- Separate migrations from feature code

---

## 12. Project Instructions

### 11.1 Code Quality Standards

**Before any commit:**

✅ **Modular** - <300 lines, single responsibility  
✅ **No Hardcoding** - all config from database  
✅ **Production-Ready** - no TODOs, workarounds, or fallbacks  
✅ **Documented** - file headers, function comments for complex logic  
✅ **Tested** - unit tests passing  
✅ **No Duplication** - check existing code first  

### 11.2 Security Checklist

- Never trust client input
- Use Pydantic models for validation
- Log all security events with context
- Encrypt only sensitive data (OAuth tokens)
- Fail-safe defaults (deny, then grant)
- Rate limit all public endpoints

### 11.3 Development Workflow

1. One feature at a time, small focused PRs
2. Test thoroughly before committing
3. Run security review for auth/data-handling code
4. Check performance on target benchmarks (§8.7)
5. Update documentation for user-facing changes

---

## 11. Payment Integration

### 11.1 Overview

BoniDoc's payment system supports Stripe and PayPal for subscription billing with flexible tier management, promotional discounts, automated invoicing, and comprehensive email communications.

**Key Capabilities:**
- Multi-tier subscription plans (Free, Basic, Pro, Enterprise)
- Monthly and annual billing cycles with automatic savings
- Flexible discount system (%, fixed amount, free months, referrals)
- Multiple payment methods (cards, PayPal, SEPA, regional options)
- Automated invoice generation with EU VAT compliance
- Comprehensive dunning process for failed payments
- Seamless upgrades, downgrades, and cancellations

### 11.2 Stripe Infrastructure

**Account Setup:**
- Separate development (`sk_test_...`) and production (`sk_live_...`) accounts
- Webhook endpoints for event-driven processing
- Price IDs for each tier and billing cycle combination
- **NO customer portal usage** - all management is in-app

**Environment Variables:**
```bash
STRIPE_SECRET_KEY=sk_test_... (dev) / sk_live_... (prod)
STRIPE_PUBLISHABLE_KEY=pk_test_... / pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_FREE=price_...
STRIPE_PRICE_ID_BASIC_MONTHLY=price_...
STRIPE_PRICE_ID_BASIC_ANNUAL=price_...
STRIPE_PRICE_ID_PRO_MONTHLY=price_...
STRIPE_PRICE_ID_PRO_ANNUAL=price_...
```

### 11.2a OAuth Redirect Logic for Subscribed Users

**⚠️ IMPORTANT: Smart Redirect Based on User State**

When users click "Login" from different locations, the OAuth callback redirects them appropriately:

**Scenario 1: User clicks package selection and logs in**
- OAuth state includes `tier_id` and `billing_cycle`
- Backend checks if user has active subscription
- **If user HAS active subscription** → Redirect to `/profile` (subscription management)
- **If user has NO subscription** → Redirect to `/checkout` with selected tier
- Prevents duplicate subscription attempts
- Better UX - existing subscribers go to manage page

**Scenario 2: User clicks top menu "Login" button**
- OAuth state has no `tier_id` (or `tier_id=0`)
- Backend redirects to `/dashboard` regardless of subscription status
- Standard login flow

**Implementation (backend/app/api/auth.py):**
```python
# In google_oauth_callback_redirect function (line 183-194)
if tier_id and tier_id > 0:
    # User selected a paid tier - check if they already have subscription
    from app.database.models import Subscription
    active_sub = session.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status.in_(['active', 'trialing', 'past_due'])
    ).first()

    if active_sub:
        # User already subscribed - redirect to subscription management
        redirect_url = f"{settings.app.app_frontend_url}/profile"
        logger.info(f"User {user.email} has active subscription, redirecting to profile")
    else:
        # No subscription - proceed to checkout
        redirect_url = f"{settings.app.app_frontend_url}/checkout?tier_id={tier_id}..."
else:
    # Free tier or top menu login - redirect to dashboard
    redirect_url = f"{settings.app.app_frontend_url}/dashboard?welcome=true"
```

**Benefits:**
- Prevents 409 Conflict errors from duplicate subscription attempts
- Clearer user journey
- Existing subscribers immediately see their subscription management page
- New users proceed smoothly to checkout

### 11.3 Database Schema

**Core Payment Tables:**

**payments** - Transaction history
- User linkage, Stripe payment intent/invoice IDs
- Amount, currency, status, payment method details
- Card brand and last 4 digits for display

**subscriptions** - Active subscription tracking
- User and tier linkage, Stripe subscription ID
- Billing cycle, status, period dates
- Cancellation flags, trial tracking

**discount_codes** - Promotional system
- Code and Stripe coupon ID linkage
- Type (percentage, fixed, free months)
- Duration, redemption limits, validity periods
- Tier applicability filters

**user_discount_redemptions** - Usage tracking
- Prevents duplicate redemptions
- Links users to applied discounts

**referrals** - Referral reward system
- Referrer/referee relationships
- Reward types and application status
- Conversion tracking

**invoices** - Billing documentation
- Stripe invoice synchronization
- PDF storage, payment status
- Tax amounts, invoice numbering

### 11.4 Tier Management

**Subscription Operations:**

**Create Subscription:**
- Customer creation or retrieval in Stripe
- Discount code validation and application
- Payment method attachment
- Subscription creation with trial period (if applicable)
- Tier activation and welcome email

**Upgrade:**
- Immediate tier change with prorated billing
- Instant feature access
- Prorated invoice generation
- Upgrade confirmation email

**Downgrade:**
- Scheduled change at current period end
- No immediate refund (credit applied)
- Continued access until transition
- Downgrade notification email

**Cancel:**
- Access continues until period end
- Optional cancellation survey
- Cancellation confirmation email
- 30-day data retention period

**Reactivate:**
- Remove cancel flag if within period
- Resume normal billing
- Reactivation confirmation email

### 11.5 Discount System

**Discount Types:**

1. **Percentage Discounts** - X% off for specified duration
   - Once: Single invoice discount
   - Repeating: X months discounted
   - Forever: Permanent discount

2. **Fixed Amount** - €X off in cents
   - Applied to invoice total
   - Duration configurable

3. **Free Months** - 100% off for X months
   - Trial extensions
   - Promotional campaigns

4. **Annual Savings** - Built-in discount
   - 15-20% savings vs monthly
   - Billed annually upfront

5. **Referral Rewards** - Dual rewards
   - Referrer: €10 credit or 1 month free
   - Referred: 20% off first 3 months

**Admin Management:**
- Code creation with all discount types
- Redemption limit enforcement
- Validity period controls
- Tier applicability filters
- Real-time redemption tracking
- Performance analytics

### 11.6 Payment Methods

**Supported Options:**
- **Credit/Debit Cards** - Via Stripe Elements (PCI compliant)
- **PayPal** - Integrated subscription billing
- **SEPA Direct Debit** - EU bank transfers
- **Regional** - iDEAL (NL), Giropay (DE), Bancontact (BE)

**Security & Compliance:**
- PCI DSS via Stripe tokenization
- No card data storage (tokens only)
- Strong Customer Authentication (SCA) for EU
- HTTPS-only payment processing
- Stored data: customer ID, last 4 digits, brand, expiry

### 11.7 Webhooks & Events

**Critical Stripe Events:**

| Event | Action |
|-------|--------|
| `customer.subscription.created` | Activate tier, send welcome email |
| `customer.subscription.updated` | Handle tier changes, update status |
| `customer.subscription.deleted` | Downgrade to free, send confirmation |
| `invoice.paid` | Store invoice, send receipt |
| `invoice.payment_failed` | Initiate dunning, send failure notice |
| `customer.subscription.trial_will_end` | Send 3-day reminder |
| `charge.refunded` | Process refund, update status |

**Processing Requirements:**
- Webhook signature verification
- Idempotent handling (duplicate prevention)
- Asynchronous processing with retry
- Database transaction consistency
- Email notification triggering

### 11.8 Invoicing

**Auto-Generation:**
- Sequential invoice numbering
- Company letterhead with tax ID
- Itemized line items
- EU VAT calculation by country
- PDF generation and Stripe upload
- Automatic email delivery

**Tax Handling:**
- **B2C**: Apply customer's country VAT (19% DE, 20% AT, etc.)
- **B2B with VAT ID**: Reverse charge (0% VAT)
- VAT ID validation via EU VIES API
- 10-year tax record retention

**Features:**
- Downloadable PDFs from billing dashboard
- Email attachments for payment events
- Historical archive
- Payment status tracking

### 11.9 Email Communications

**Subscription Lifecycle Emails:**

1. **Subscription Confirmation** - Welcome, features, invoice attached
2. **Payment Successful** - Receipt, next billing date
3. **Payment Failed** - Reason, update link, retry schedule
4. **Subscription Upgraded** - New features, prorated charge
5. **Subscription Downgraded** - Effective date, access end
6. **Subscription Canceled** - Access end, data retention, feedback
7. **Trial Ending** - 3-day reminder, payment prompt
8. **Invoice Ready** - Monthly notification, PDF link

**Brevo Integration:**
- Transactional email API
- HTML templates with branding
- PDF invoice attachments
- Personalization (user, tier, amounts, dates)
- Delivery tracking

### 11.10 Billing Dashboard & In-App Subscription Management

**⚠️ IMPORTANT: In-App Management (Not Stripe Portal)**

BoniDoc uses **in-app subscription management** to keep users within the application and prevent logout issues. Users should NEVER be redirected to Stripe's customer portal.

**User Interface:**

**Current Plan Section:**
- Tier name, status badge, price display
- Billing cycle (monthly/annual)
- Next billing date
- Cancellation warnings
- **In-app** Cancel Subscription button (opens CancellationModal)
- **In-app** Update Payment Method button (Stripe Elements embed)

**Payment Method Management:**
- Card brand icon, last 4 digits, expiry
- **Update payment method using Stripe Elements** (embedded, no redirect)
- Backend creates SetupIntent for payment method update
- Frontend displays Stripe CardElement component
- Updates payment method without leaving bonidoc.com
- Success/error messages shown in-app

**Billing History:**
- Invoice table (date, description, amount, status)
- PDF download links
- Status badges
- Transaction archive

**Usage Monitoring:**
- Document count vs limit
- Storage usage vs quota
- Visual progress bars
- Upgrade prompts

**Subscription Cancellation Flow:**
- Multi-step CancellationModal component (frontend/src/components/CancellationModal.tsx)
- Step 1: Retention - Show what user will lose, refund eligibility (14-day money-back)
- Step 2: Reason - Collect cancellation reason and feedback
- Step 3: Confirm - Review cancellation type (immediate vs end of period)
- Step 4: Success - Confirmation with access end date
- Backend endpoint: POST /api/v1/billing/cancel-subscription
- Automatic subscription cancellation in Stripe
- Email notification sent
- User remains within bonidoc.com throughout process

### 11.11 Business Logic

**Proration:**
- **Upgrade**: Immediate prorated charge for remaining period
- **Downgrade**: Credit to next invoice, no refund
- Daily rate calculation based on cycle

**Failed Payment Handling (Dunning):**
- Retry schedule: Day 3, Day 8, Day 15
- Email at each retry
- Status: `past_due` after first failure
- Downgrade to free after 3 failures
- 30-day data retention

**Refund Policy:**
- Full refund within 14 days
- Prorated refund for annual (if applicable)
- No refund after 30 days
- Manual admin approval
- Automatic confirmation emails

**Trial Periods:**
- Free trial duration per tier
- End reminders (7, 3, 1 day)
- Auto-conversion or downgrade
- Payment required before end
- Extension via discount codes

**Account Deletion with Active Subscription:**
- **Automatic subscription cancellation** when user deletes account
- Check for active subscriptions (`status in ['active', 'trialing', 'past_due']`)
- Cancel subscription in Stripe immediately (not at period end)
- Update subscription status to 'canceled' in database
- Log cancellation in audit trail (`had_active_subscription: true`)
- Continue with account deletion even if Stripe cancellation fails
- Implementation: `backend/app/services/user_service.py:397-426`
- User receives account deletion email (subscription cancellation mentioned)
- Prevents continued billing after account deletion
- GDPR compliant - no orphaned billing records

### 11.12 Analytics

**Admin Metrics:**
- Monthly Recurring Revenue (MRR)
- Annual Recurring Revenue (ARR)
- Churn rate (monthly/annual)
- Customer Lifetime Value (LTV)
- Average Revenue Per User (ARPU)
- Discount performance
- Trial-to-paid conversion
- Payment failure rate
- Refund rate
- Revenue by tier

**Export Capabilities:**
- CSV for accounting
- Invoice batch downloads
- Payment history
- Discount redemption reports

### 11.13 Compliance

**PCI DSS:**
- No card data storage
- Client-side input via Stripe.js
- Tokenization only
- HTTPS enforcement

**GDPR:**
- Payment data in user exports
- Invoice deletion on account deletion
- 30-day grace period
- Clear cancellation process

**Tax Compliance:**
- VAT invoice requirements
- VAT ID validation (VIES API)
- Country-specific rates
- 10-year archival

### 11.14 Implementation Phases

**Phase 1 - Foundation (Weeks 1-2):**
Database schema, Stripe setup, webhooks, basic flow

**Phase 2 - Core Features (Weeks 3-4):**
Pricing page, checkout, subscription management

**Phase 3 - Discounts & Invoicing (Weeks 5-6):**
Discount system, referrals, invoice generation, tax

**Phase 4 - Email & UX (Weeks 7-8):**
Email templates, billing dashboard, payment methods

**Phase 5 - Edge Cases (Weeks 9-10):**
Dunning, proration, refunds, trials, testing

**Phase 6 - Analytics (Weeks 11-12):**
Reporting, optimization, monitoring, security audit

**Total Estimated Timeline:** 12 weeks

---

## 12. Feature History

```bash
# Deployment
ssh deploy@YOUR_SERVER_IP && ~/deploy.sh

# Logs
docker-compose logs -f backend
docker-compose logs --tail=100 backend

# Database
docker exec bonifatus-backend alembic current
docker exec bonifatus-backend alembic upgrade head
pg_dump -U bonifatus -d bonifatus_dms > backup.sql

# Health checks
curl https://api.bonidoc.com/health
curl https://bonidoc.com

# Troubleshooting
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms
docker-compose ps
docker stats
```

## Appendix B: Performance Metrics to Monitor

```
API Response Time (p95): <200ms
Database Query Time (p95): <100ms
Error Rate: <0.1%
OCR Processing: <10s per page
Container Memory: <1.5GB
Container CPU: <80%
Database Size: Track growth
```

## Appendix C: Glossary

- **OCR:** Optical Character Recognition (text extraction from images)
- **PyMuPDF:** Fast native PDF text extraction library
- **Tesseract:** OCR library for scanned documents
- **Fernet:** Symmetric encryption (AES-256)
- **JWT:** JSON Web Tokens for stateless authentication
- **httpOnly:** Cookie flag preventing JavaScript access (prevents XSS)
- **Alembic:** Database migration tool
- **Rate Limiting:** Restricting request frequency to prevent abuse

---

**Version:** 15.1 (Consolidated)  
**Last Updated:** November 2025  
**Status:** Production Ready ✅  
**Information Preservation:** 100% ✅
