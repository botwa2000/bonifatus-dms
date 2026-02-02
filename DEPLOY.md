# Quick Deployment Guide (Docker Swarm Secrets)

**Last Updated:** 2025-12-27
**Server Access:** See `HETZNER_SETUP_ACTUAL.md` for credentials and detailed server setup
**Secret Management:** See `DEPLOYMENT_GUIDE.md` §9.8 for comprehensive secrets documentation

> **IMPORTANT:** This application now uses Docker Swarm Secrets for production-grade secret management.
> Secrets are encrypted at rest, in transit, and mounted as in-memory tmpfs (never written to disk).

---

## Quick Reference

| Environment | Directory | URL | API URL | Deployment Mode |
|------------|-----------|-----|---------|----------------|
| **Dev** | `/opt/bonifatus-dms-dev` | https://dev.bonidoc.com | https://api-dev.bonidoc.com | Docker Swarm (dev secrets) |
| **Prod** | `/opt/bonifatus-dms` | https://bonidoc.com | https://api.bonidoc.com | Docker Swarm (prod secrets) |

**Server IP:** 91.99.212.17 (see HETZNER_SETUP_ACTUAL.md)

**Key Differences:**
- **Dev:** Uses Docker Swarm with `_dev` suffixed secrets (e.g., `database_url_dev`)
- **Prod:** Uses Docker Swarm with `_prod` suffixed secrets (e.g., `database_url_prod`)
- **Both:** Deploy using `docker stack deploy`, run migrations inside running containers

---

## FIRST-TIME SETUP (One-Time Only)

### Prerequisites Check

Before deploying for the first time after the Docker Secrets migration, run:

```bash
ssh root@91.99.212.17 'docker info | grep "Swarm: active"'
```

**If output is empty:** Swarm not initialized - follow "Initial Swarm Setup" below
**If output shows "Swarm: active":** Skip to "Verify Secrets Exist" below

### Initial Swarm Setup (One-Time)

**Run this ONLY ONCE when first migrating to Docker Swarm Secrets:**

```bash
ssh root@91.99.212.17 'bash -s' << 'ENDSSH'
set -e
echo "=== [1/5] Initializing Docker Swarm ==="
docker swarm init --advertise-addr 127.0.0.1 2>/dev/null || echo "Swarm already initialized"

echo "=== [2/5] Generating ENCRYPTION_KEY (CRITICAL) ==="
ENCRYPTION_KEY=$(docker run --rm python:3.11-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "Generated: $ENCRYPTION_KEY"

echo "=== [3/5] Creating secret directories ==="
mkdir -p /opt/bonifatus-secrets/prod /opt/bonifatus-secrets/dev
chmod 700 /opt/bonifatus-secrets

echo "=== [4/5] Reading current .env file ==="
cd /opt/bonifatus-dms
if [ -f .env ]; then
    source .env
    echo "✓ Loaded secrets from .env"
else
    echo "ERROR: .env file not found. Cannot extract secrets."
    exit 1
fi

echo "=== [5/5] Creating secret files ==="
# Database
echo -n "$DATABASE_URL" > /opt/bonifatus-secrets/prod/database_url

# Security
echo -n "${SECURITY_SECRET_KEY}" > /opt/bonifatus-secrets/prod/security_secret_key
echo -n "$ENCRYPTION_KEY" > /opt/bonifatus-secrets/prod/encryption_key
echo -n "${TURNSTILE_SECRET_KEY:-}" > /opt/bonifatus-secrets/prod/turnstile_secret_key

# Google
echo -n "${GOOGLE_CLIENT_ID}" > /opt/bonifatus-secrets/prod/google_client_id
echo -n "${GOOGLE_CLIENT_SECRET}" > /opt/bonifatus-secrets/prod/google_client_secret
echo -n "${GCP_PROJECT}" > /opt/bonifatus-secrets/prod/gcp_project

# OneDrive
echo -n "${ONEDRIVE_CLIENT_ID:-NOT_CONFIGURED}" > /opt/bonifatus-secrets/prod/onedrive_client_id
echo -n "${ONEDRIVE_CLIENT_SECRET:-NOT_CONFIGURED}" > /opt/bonifatus-secrets/prod/onedrive_client_secret

# Email
echo -n "${BREVO_API_KEY}" > /opt/bonifatus-secrets/prod/brevo_api_key
echo -n "${IMAP_PASSWORD}" > /opt/bonifatus-secrets/prod/imap_password

# Stripe
echo -n "${STRIPE_SECRET_KEY}" > /opt/bonifatus-secrets/prod/stripe_secret_key
echo -n "${STRIPE_PUBLISHABLE_KEY}" > /opt/bonifatus-secrets/prod/stripe_publishable_key
echo -n "${STRIPE_WEBHOOK_SECRET:-}" > /opt/bonifatus-secrets/prod/stripe_webhook_secret

# Set permissions
chmod 600 /opt/bonifatus-secrets/prod/*
chown root:root /opt/bonifatus-secrets/prod/*

echo "=== Creating Docker Secrets ==="
cd /opt/bonifatus-secrets/prod
for secret in database_url security_secret_key encryption_key google_client_id google_client_secret onedrive_client_id onedrive_client_secret gcp_project brevo_api_key imap_password stripe_secret_key stripe_publishable_key stripe_webhook_secret turnstile_secret_key; do
    if docker secret inspect $secret >/dev/null 2>&1; then
        echo "Secret $secret already exists (skipping)"
    else
        docker secret create $secret $secret
        echo "✓ Created secret: $secret"
    fi
done

echo ""
echo "=== SETUP COMPLETE ==="
echo "Docker Swarm initialized with 14 encrypted secrets"
echo "CRITICAL: Save this ENCRYPTION_KEY to your password manager:"
echo "$ENCRYPTION_KEY"
echo ""
echo "You can now deploy using: docker stack deploy"
ENDSSH
```

**Expected Output:**
```
✓ Created secret: database_url
✓ Created secret: security_secret_key
✓ Created secret: encryption_key
... (14 secrets total)
CRITICAL: Save this ENCRYPTION_KEY to your password manager:
<long base64 string>
```

**⚠️ CRITICAL:** Copy the ENCRYPTION_KEY from the output and save it in your password manager!

### Verify Secrets Exist

```bash
ssh root@91.99.212.17 'docker secret ls'
```

**Expected:** 14 secrets listed (database_url, security_secret_key, encryption_key, etc.)

**If secrets are missing:** Re-run the "Initial Swarm Setup" above

---

## ONE-COMMAND DEPLOYMENT SEQUENCES

### Deploy to DEV (Docker Swarm)

**DEV uses Docker Swarm with _dev suffixed secrets:**

```bash
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && \
  echo "=== [1/9] Pulling latest code ===" && \
  git pull origin main && \
  echo "=== [2/9] Building images ===" && \
  docker compose -f docker-compose-dev.yml build && \
  echo "=== [3/9] Deploying to Docker Swarm ===" && \
  docker stack deploy -c docker-compose-dev.yml bonifatus-dev && \
  echo "=== [4/10] Forcing backend update ===" && \
  docker service update --force bonifatus-dev_backend && \
  echo "=== [5/10] Forcing frontend update ===" && \
  docker service update --force bonifatus-dev_frontend && \
  echo "=== [6/10] Forcing celery-worker update ===" && \
  docker service update --force bonifatus-dev_celery-worker && \
  echo "=== [7/10] Waiting for services to start (30s) ===" && \
  sleep 30 && \
  echo "=== [8/10] Running migrations ===" && \
  CONTAINER=$(docker ps | grep bonifatus-dev_backend | head -1 | cut -d" " -f1) && \
  docker exec $CONTAINER alembic upgrade head && \
  echo "=== [9/10] Health check ===" && \
  curl -s https://api-dev.bonidoc.com/health && echo "" && \
  echo "=== [10/10] Service status ===" && \
  docker stack ps bonifatus-dev --no-trunc | head -10'
```

**Expected Output:**
- All 10 steps complete without errors
- Backend health returns: `{"status":"healthy","environment":"development"}`
- Services show "Running" state
- Backend, frontend, and celery worker updated with latest code

**Time:** ~3-5 minutes

**CRITICAL:** Always force-update frontend and celery-worker services to ensure they have the latest code changes!

**Note:** If the new container hasn't started yet after 30 seconds, wait an additional 10-20 seconds before running migrations.

---

### Deploy to PROD (Docker Swarm)

**⚠️ PRODUCTION DEPLOYMENT - Uses Docker Swarm with encrypted secrets!**

**Prerequisites:**
- Docker Swarm initialized (see "First-Time Setup" above)
- All 14 `_prod` suffixed secrets created (verify with `docker secret ls`)
- Dev deployment tested successfully

```bash
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && \
  echo "=== [1/9] Pulling latest code ===" && \
  git pull origin main && \
  echo "=== [2/9] Building images ===" && \
  docker compose build && \
  echo "=== [3/9] Verifying secrets exist ===" && \
  docker secret ls | grep -E "database_url_prod|security_secret_key_prod|encryption_key_prod" && \
  echo "=== [4/9] Deploying to Docker Swarm ===" && \
  docker stack deploy -c docker-compose.yml bonifatus && \
  echo "=== [5/10] Forcing backend update ===" && \
  docker service update --force bonifatus_backend && \
  echo "=== [6/10] Forcing frontend update ===" && \
  docker service update --force bonifatus_frontend && \
  echo "=== [7/10] Forcing celery-worker update ===" && \
  docker service update --force bonifatus_celery-worker && \
  echo "=== [8/10] Waiting for services to start (40s) ===" && \
  sleep 40 && \
  echo "=== [9/10] Running migrations ===" && \
  CONTAINER=$(docker ps | grep bonifatus_backend | head -1 | cut -d" " -f1) && \
  docker exec $CONTAINER alembic upgrade head && \
  echo "=== [10/10] Health check ===" && \
  curl -s https://api.bonidoc.com/health && echo "" && \
  docker stack ps bonifatus --no-trunc | head -10'
```

**Expected Output:**
```
✓ All 10 steps complete
✓ Services show "Running" state in docker stack ps
✓ Backend health: {"status":"healthy","environment":"production"}
✓ Backend, frontend, and celery worker updated with latest code
✓ No migration errors
```

**Time:** ~4-6 minutes (Swarm rolling update adds time)

**Key Points:**
- `docker stack deploy` for zero-downtime rolling updates
- Migrations run AFTER deployment in running container
- Secrets loaded from `/run/secrets/` (encrypted tmpfs)
- Services named `bonifatus_backend` (underscore, not dash)

**Note:** If health check returns 502, wait an additional 10-20 seconds for the new container to finish starting, then re-check.

---

### Deploy to BOTH (Dev → Test → Prod)

**Complete deployment cycle with testing pause:**

```bash
# Step 1: Deploy to DEV
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && \
  git pull origin main && \
  docker compose -f docker-compose-dev.yml build && \
  docker stack deploy -c docker-compose-dev.yml bonifatus-dev && \
  docker service update --force bonifatus-dev_backend && \
  docker service update --force bonifatus-dev_frontend && \
  docker service update --force bonifatus-dev_celery-worker && \
  sleep 30 && \
  CONTAINER=$(docker ps | grep bonifatus-dev_backend | head -1 | cut -d" " -f1) && \
  docker exec $CONTAINER alembic upgrade head && \
  curl -s https://api-dev.bonidoc.com/health'

# Step 2: TEST ON DEV
# Open https://dev.bonidoc.com and verify:
# - Login works
# - Document upload works (tests celery-worker)
# - All new features work as expected
# - Check browser console for errors

# Step 3: Deploy to PROD (only if dev testing passed)
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && \
  git pull origin main && \
  docker compose build && \
  docker stack deploy -c docker-compose.yml bonifatus && \
  docker service update --force bonifatus_backend && \
  docker service update --force bonifatus_frontend && \
  docker service update --force bonifatus_celery-worker && \
  sleep 40 && \
  CONTAINER=$(docker ps | grep bonifatus_backend | head -1 | cut -d" " -f1) && \
  docker exec $CONTAINER alembic upgrade head && \
  curl -s https://api.bonidoc.com/health'

# Step 4: VERIFY PROD
# Open https://bonidoc.com and verify deployment was successful
```

---

## Docker Swarm Commands Reference

### Service Management

| Task | Dev (bonifatus-dev) | Prod (bonifatus) |
|------|---------------------|------------------|
| Deploy | `docker stack deploy -c docker-compose-dev.yml bonifatus-dev` | `docker stack deploy -c docker-compose.yml bonifatus` |
| Stop | `docker stack rm bonifatus-dev` | `docker stack rm bonifatus` |
| Logs | `docker service logs bonifatus-dev_backend` | `docker service logs bonifatus_backend` |
| Status | `docker stack ps bonifatus-dev` | `docker stack ps bonifatus` |
| Restart service | `docker service update --force bonifatus-dev_backend` | `docker service update --force bonifatus_backend` |
| Scale | `docker service scale bonifatus-dev_backend=2` | `docker service scale bonifatus_backend=2` |
| List services | `docker stack services bonifatus-dev` | `docker stack services bonifatus` |

### Secret Management

```bash
# List secrets
docker secret ls

# Inspect secret metadata (does NOT show value - secure!)
docker secret inspect database_url

# Rotate a secret (example: database password)
echo -n 'new_password' | docker secret create database_url_v2 -
docker service update --secret-rm database_url --secret-add source=database_url_v2,target=database_url bonifatus_backend

# Remove old secret
docker secret rm database_url
docker secret rm database_url_v2  # After rotating, rename v2 to original name
```

---

## Health Check Commands

### Backend Health

```bash
# Dev (Docker Compose)
curl https://api-dev.bonidoc.com/health
# Should return: {"status":"healthy","environment":"development"}

# Prod (Docker Swarm)
curl https://api.bonidoc.com/health
# Should return: {"status":"healthy","environment":"production"}
```

### Check Secret Loading

```bash
# Verify secrets are loaded from Docker Swarm (not env vars)
ssh root@91.99.212.17 'docker service logs bonifatus_backend --tail 100 | grep "Loaded secret"'

# Expected output:
# Loaded secret 'database_url' from Docker Swarm
# Loaded secret 'security_secret_key' from Docker Swarm
# Loaded secret 'encryption_key' from Docker Swarm
```

### Service Status

```bash
# Dev (Swarm)
ssh root@91.99.212.17 'docker stack ps bonifatus-dev'
ssh root@91.99.212.17 'docker stack services bonifatus-dev'

# Prod (Swarm)
ssh root@91.99.212.17 'docker stack ps bonifatus'
ssh root@91.99.212.17 'docker stack services bonifatus'
```

### Database Health

```bash
# Dev (Swarm - find container ID)
CONTAINER=$(docker ps | grep bonifatus-dev_backend | head -1 | cut -d" " -f1)
docker exec $CONTAINER alembic current

# Prod (Swarm - find container ID)
CONTAINER=$(docker ps | grep bonifatus_backend | head -1 | cut -d" " -f1)
docker exec $CONTAINER alembic current
```

---

## Rollback Procedure

### Rollback Production (Docker Swarm)

If deployment breaks production:

```bash
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && \
  echo "=== Finding last working commit ===" && \
  git log --oneline -10 && \
  echo "" && \
  read -p "Enter commit hash to rollback to: " COMMIT && \
  echo "=== Rolling back code ===" && \
  git reset --hard $COMMIT && \
  echo "=== Rebuilding images ===" && \
  docker compose build && \
  echo "=== Redeploying to Swarm ===" && \
  docker stack deploy -c docker-compose.yml bonifatus && \
  echo "=== Waiting for rollout ===" && \
  sleep 30 && \
  echo "=== Verifying rollback ===" && \
  curl https://api.bonidoc.com/health && \
  docker stack ps bonifatus'
```

**For database migration rollback:**

```bash
# Find backend container
CONTAINER=$(docker ps | grep bonifatus_backend | awk '{print $1}' | head -1)

# Rollback one migration
docker exec $CONTAINER alembic downgrade -1

# Or rollback to specific version
docker exec $CONTAINER alembic downgrade <revision>
```

### Rollback Dev

Uses Docker Swarm (same as prod):

```bash
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && \
  echo "=== Finding last working commit ===" && \
  git log --oneline -10 && \
  echo "" && \
  read -p "Enter commit hash to rollback to: " COMMIT && \
  echo "=== Rolling back code ===" && \
  git reset --hard $COMMIT && \
  echo "=== Rebuilding images ===" && \
  docker compose -f docker-compose-dev.yml build && \
  echo "=== Redeploying to Swarm ===" && \
  docker stack deploy -c docker-compose-dev.yml bonifatus-dev && \
  echo "=== Waiting for rollout ===" && \
  sleep 30 && \
  echo "=== Verifying rollback ===" && \
  curl https://api-dev.bonidoc.com/health && \
  docker stack ps bonifatus-dev'
```

---

## Emergency Procedures

### If Swarm Services Won't Start

```bash
# Check service errors
ssh root@91.99.212.17 'docker service ps bonifatus_backend --no-trunc'

# Check if secrets are accessible
ssh root@91.99.212.17 'docker secret ls'

# Remove stack and redeploy
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && \
  docker stack rm bonifatus && \
  sleep 10 && \
  docker stack deploy -c docker-compose.yml bonifatus'
```

### If Secrets Are Missing

```bash
# List existing secrets
ssh root@91.99.212.17 'docker secret ls'

# If secrets are missing, re-run the "Initial Swarm Setup" section
# Or manually create missing secret:
ssh root@91.99.212.17 'echo -n "secret_value_here" | docker secret create secret_name -'
```

### Revert to Docker Compose (Emergency Only)

If Docker Swarm is causing issues and you need to revert:

```bash
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && \
  echo "=== Removing Swarm stack ===" && \
  docker stack rm bonifatus && \
  sleep 10 && \
  echo "=== Reverting code to pre-Swarm commit ===" && \
  git reset --hard <commit-before-swarm> && \
  echo "=== Starting with Docker Compose ===" && \
  docker compose build && \
  docker compose up -d'
```

**Note:** This will revert to loading secrets from environment variables (less secure)

---

## Common Issues and Fixes

### Issue 1: "Secret not found" Error

**Symptoms:**
```
ValueError: Secret 'database_url' not found in /run/secrets/ or environment variable 'DATABASE_URL'
```

**Fix:**
```bash
# Verify secret exists
ssh root@91.99.212.17 'docker secret inspect database_url'

# If not found, create it:
ssh root@91.99.212.17 'echo -n "postgresql+psycopg2://..." | docker secret create database_url -'

# Redeploy
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && docker stack deploy -c docker-compose.yml bonifatus'
```

### Issue 2: Services Stuck in "Pending" State

**Symptoms:**
```
docker stack ps bonifatus shows "Pending" for 5+ minutes
```

**Fix:**
```bash
# Check why service is pending
ssh root@91.99.212.17 'docker service ps bonifatus_backend --no-trunc'

# Common causes:
# - Image not built: Run docker compose build
# - Secret not created: Run docker secret ls
# - Resource limits: Check docker stats

# Force recreate
ssh root@91.99.212.17 'docker service update --force bonifatus_backend'
```

### Issue 3: "Network bonifatus_default not found"

**Symptoms:**
```
Error response from daemon: network bonifatus_default not found
```

**Fix:**
```bash
# Swarm creates networks automatically, but if missing:
ssh root@91.99.212.17 'docker network create --driver overlay bonifatus_default'

# Then redeploy
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && docker stack deploy -c docker-compose.yml bonifatus'
```

### Issue 4: CORS Errors After Swarm Deployment

**Cause:** Frontend environment variables not passed correctly

**Fix:**
```bash
# Verify frontend has correct API URL
ssh root@91.99.212.17 'docker service inspect bonifatus_frontend | grep NEXT_PUBLIC_API_URL'

# Should show: https://api.bonidoc.com

# If wrong, rebuild frontend image and redeploy
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && \
  docker compose build frontend && \
  docker stack deploy -c docker-compose.yml bonifatus'
```

---

## Deployment Checklist

**Before Any Deployment:**
- [ ] Code committed and pushed to main
- [ ] No hardcoded secrets in code
- [ ] Dependencies added to requirements.txt/package.json

**First-Time Swarm Setup (Production):**
- [ ] Docker Swarm initialized (`docker swarm init`)
- [ ] All 14 secrets created (`docker secret ls`)
- [ ] ENCRYPTION_KEY saved to password manager
- [ ] Secret files backed up to `/opt/bonifatus-secrets/prod/`

**Dev Deployment:**
- [ ] Run dev deployment command
- [ ] Verify health check passes
- [ ] Test on https://dev.bonidoc.com
- [ ] Check browser console for errors

**Prod Deployment (only after dev testing):**
- [ ] Dev testing completed and passed
- [ ] Verify secrets exist (`docker secret ls`)
- [ ] Run prod deployment command (Swarm)
- [ ] Verify health check passes
- [ ] Check logs show "Loaded secret ... from Docker Swarm"
- [ ] Test on https://bonidoc.com
- [ ] Monitor for 10-15 minutes

---

## Quick Diagnostic Commands

### Docker Swarm Status

```bash
# Check Swarm is active
docker info | grep Swarm

# List all secrets
docker secret ls

# List all stacks
docker stack ls

# List services in stack
docker stack services bonifatus

# Detailed service status
docker stack ps bonifatus --no-trunc

# Service logs
docker service logs bonifatus_backend --tail 100
```

### Secret Verification

```bash
# Verify backend can read secrets
docker service logs bonifatus_backend | grep "Loaded secret"

# Check which secrets a service has access to
docker service inspect bonifatus_backend | grep -A 20 Secrets

# Verify secret file exists in container (read-only check)
CONTAINER=$(docker ps | grep bonifatus_backend | awk '{print $1}' | head -1)
docker exec $CONTAINER ls -la /run/secrets/
```

---

## Notes

- **Both Dev and Prod use Docker Swarm** (encrypted secrets, rolling updates)
- **Dev uses `_dev` suffixed secrets** (e.g., `database_url_dev`)
- **Prod uses `_prod` suffixed secrets** (e.g., `database_url_prod`)
- **Secrets are encrypted at rest and in transit**
- **Zero downtime deployments** (rolling updates in Swarm)
- **Always test in dev first, then deploy to prod**
- **Secret rotation requires service update** (no restart needed)
- **Swarm initialized once, persists across reboots**
- **Migrations run AFTER deployment** in running containers (not before)
- **Use `-f docker-compose-dev.yml` for dev** to avoid using prod config

---

**For More Information:**
- Comprehensive secrets guide: `DEPLOYMENT_GUIDE.md` §9.8
- Server setup details: `HETZNER_SETUP_ACTUAL.md`
- Migration plan: `C:\Users\Alexa\.claude\plans\memoized-prancing-iverson.md`
