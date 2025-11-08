# Dev to Prod Migration Guide

## Environment-Specific Variables (DO NOT COPY)

When migrating features from dev to prod, **NEVER** copy these variables:

### 1. Frontend Debug Logs
**Location**: `docker-compose.yml` → frontend → build → args

```yaml
# DEV (keep as true)
NEXT_PUBLIC_DEBUG_LOGS: "true"

# PROD (keep as false)
NEXT_PUBLIC_DEBUG_LOGS: "false"
```

### 2. Backend Debug Mode
**Location**: `.env`

```bash
# DEV
APP_DEBUG_MODE=true

# PROD
APP_DEBUG_MODE=false
```

### 3. Environment Identifier
**Location**: `.env`

```bash
# DEV
APP_ENVIRONMENT=development

# PROD
APP_ENVIRONMENT=production
```

### 4. Database URLs
**Location**: `.env`

```bash
# DEV
DATABASE_URL=postgresql://bonifatus_dev:BoniDocDev2025Password@host.docker.internal:5432/bonifatus_dms_dev

# PROD
DATABASE_URL=postgresql://bonifatus:BoniDocProd2025Password@host.docker.internal:5432/bonifatus_dms
```

### 5. API URLs
**Location**: `.env` and `docker-compose.yml`

```bash
# DEV
NEXT_PUBLIC_API_URL=https://api-dev.bonidoc.com
NEXTAUTH_URL=https://dev.bonidoc.com

# PROD
NEXT_PUBLIC_API_URL=https://api.bonidoc.com
NEXTAUTH_URL=https://bonidoc.com
```

### 6. OAuth Redirect URIs
**Location**: `.env`

```bash
# DEV
GOOGLE_REDIRECT_URI=https://api-dev.bonidoc.com/api/v1/auth/google/callback

# PROD
GOOGLE_REDIRECT_URI=https://api.bonidoc.com/api/v1/auth/google/callback
```

### 7. Port Mappings
**Location**: `docker-compose.yml`

```yaml
# DEV
ports:
  - "3001:3000"  # frontend
  - "8081:8080"  # backend

# PROD
ports:
  - "3000:3000"  # frontend
  - "8080:8080"  # backend
```

---

## Safe Migration Process

### Step 1: Copy Code Files Only
```bash
# Copy application code (frontend/backend directories)
rsync -av --exclude='node_modules' --exclude='.next' --exclude='__pycache__' \
  /opt/bonifatus-dms-dev/frontend/ /opt/bonifatus-dms/frontend/

rsync -av --exclude='__pycache__' --exclude='logs' \
  /opt/bonifatus-dms-dev/backend/ /opt/bonifatus-dms/backend/
```

### Step 2: NEVER Copy These Files
- ❌ `.env`
- ❌ `docker-compose.yml`
- ❌ `nginx` configs

### Step 3: Rebuild and Deploy
```bash
cd /opt/bonifatus-dms
docker compose build
docker compose up -d
```

### Step 4: Verify Environment Variables
```bash
# Check debug is disabled on prod
grep -i debug /opt/bonifatus-dms/.env
grep -i debug /opt/bonifatus-dms/docker-compose.yml

# Should show:
# APP_DEBUG_MODE=false
# NEXT_PUBLIC_DEBUG_LOGS: "false"
```

---

## Quick Reference

| Variable | Dev Value | Prod Value |
|----------|-----------|------------|
| NEXT_PUBLIC_DEBUG_LOGS | true | false |
| APP_DEBUG_MODE | true | false |
| APP_ENVIRONMENT | development | production |
| Frontend Port | 3001 | 3000 |
| Backend Port | 8081 | 8080 |
| Domain | dev.bonidoc.com | bonidoc.com |
| API Domain | api-dev.bonidoc.com | api.bonidoc.com |
