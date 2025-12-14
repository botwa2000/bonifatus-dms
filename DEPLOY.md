# Quick Deployment Guide

**Last Updated:** 2025-12-07
**Credentials:** See `HETZNER_SETUP_ACTUAL.md` for server access details

---

## Quick Reference

| Environment | Directory | URL | API URL | Ports |
|------------|-----------|-----|---------|-------|
| **Dev** | `/opt/bonifatus-dms-dev` | https://dev.bonidoc.com | https://api-dev.bonidoc.com | 3001/8081/5001 |
| **Prod** | `/opt/bonifatus-dms` | https://bonidoc.com | https://api.bonidoc.com | 3000/8080/5000 |

**Server IP:** 91.99.212.17 (see HETZNER_SETUP_ACTUAL.md)

---

## Standard Deployment Workflow

### Step 1: Local - Commit and Push

```bash
# Commit your changes
git add .
git commit -m "Your commit message

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to GitHub
git push origin main
```

### Step 2: Deploy to Dev (ALWAYS TEST FIRST!)

```bash
# SSH to server (credentials in HETZNER_SETUP_ACTUAL.md)
ssh root@91.99.212.17

# Navigate to dev directory
cd /opt/bonifatus-dms-dev

# ⚠️ IMPORTANT: Handle local changes (dev-specific API URL)
# Check if there are local changes
git status

# If docker-compose.yml has local changes, stash them
git stash

# Pull latest code
git pull origin main

# Restore dev-specific configuration (API URL fix)
git stash pop

# If conflict, keep dev API URL:
# Edit docker-compose.yml and ensure:
#   NEXT_PUBLIC_API_URL: https://api-dev.bonidoc.com
# Then: git add docker-compose.yml && git stash drop

# Rebuild containers
docker compose build

# Restart containers
docker compose up -d

# ⚠️⚠️⚠️ CRITICAL: ALWAYS RELOAD NGINX AFTER CONTAINER RESTART ⚠️⚠️⚠️
# Why: Docker restarts can cause nginx routing to break, preventing dev access
# This MUST be run every time containers are restarted or rebuilt
nginx -t && systemctl reload nginx
echo "✓ Nginx reloaded - dev site should be accessible"

# Run migrations if needed
docker exec bonifatus-backend-dev alembic upgrade head

# Check status
docker compose ps
docker compose logs --tail=50 backend
docker compose logs --tail=50 frontend
```

**Expected output:**
```
bonifatus-backend-dev      Up (healthy)    8081->8080
bonifatus-frontend-dev     Up              3001->3000
bonifatus-translator-dev   Up              5001->5000
```

**Verify deployment:**
```bash
# Backend health
curl https://api-dev.bonidoc.com/health

# Should show: {"status":"healthy","environment":"development"}
```

### Step 3: Test on Dev

1. Open browser to https://dev.bonidoc.com
2. Test all new functionality
3. Check browser console for errors
4. Verify database changes

### Step 4: Deploy to Production (Only After Dev Testing Passes!)

```bash
# Still logged in as root@91.99.212.17

# Navigate to production directory
cd /opt/bonifatus-dms

# Pull latest code
git pull origin main

# Rebuild containers
docker compose build

# Restart containers
docker compose up -d

# Run migrations if needed
docker exec bonifatus-backend alembic upgrade head

# Check status
docker compose ps
docker compose logs --tail=50 backend
docker compose logs --tail=50 frontend
```

**Expected output:**
```
bonifatus-backend      Up (healthy)    8080->8080
bonifatus-frontend     Up              3000->3000
bonifatus-translator   Up              5000->5000
```

**Verify production deployment:**
```bash
# Backend health
curl https://api.bonidoc.com/health

# Should show: {"status":"healthy","environment":"production"}

# Exit server
exit
```

### Step 5: Verify Production in Browser

1. Open browser to https://bonidoc.com
2. Test critical functionality
3. Monitor for errors

---

## Common Issues and Fixes

### Issue 1: CORS Errors - Frontend Calling Wrong API

**Symptoms:**
```
Access to fetch at 'https://api.bonidoc.com' from origin 'https://dev.bonidoc.com'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header
```

**Root Cause:** Dev frontend was built with production API URL instead of dev API URL

**Fix:**
```bash
ssh root@91.99.212.17
cd /opt/bonifatus-dms-dev

# 1. Verify docker-compose.yml has correct API URL
grep "NEXT_PUBLIC_API_URL" docker-compose.yml
# Should show: NEXT_PUBLIC_API_URL: https://api-dev.bonidoc.com

# 2. If wrong, fix it
sed -i 's|NEXT_PUBLIC_API_URL: https://api.bonidoc.com|NEXT_PUBLIC_API_URL: https://api-dev.bonidoc.com|g' docker-compose.yml

# 3. Rebuild frontend with correct API URL
docker compose build frontend

# 4. Restart frontend
docker compose up -d frontend

# 5. Verify (should show api-dev.bonidoc.com in build logs)
docker compose logs frontend | grep "NEXT_PUBLIC_API_URL"
```

**Prevention:** Never edit dev `docker-compose.yml` manually. Always verify `NEXT_PUBLIC_API_URL` matches environment.

---

### Issue 2: Container Name Conflicts

**Symptoms:**
```
Error: The container name "/bonifatus-backend" is already in use
```

**Root Cause:** Dev docker-compose.yml missing `-dev` suffix on container names

**Fix:**
```bash
ssh root@91.99.212.17
cd /opt/bonifatus-dms-dev

# Verify container names have -dev suffix
grep "container_name:" docker-compose.yml

# Should show:
# container_name: bonifatus-backend-dev
# container_name: bonifatus-frontend-dev
# container_name: bonifatus-translator-dev

# If missing, the file was corrupted. Restore from git:
git checkout docker-compose.yml

# Or manually add -dev suffix to all container names
```

---

### Issue 3: Frontend Build Failing (Out of Memory)

**Symptoms:**
```
FATAL ERROR: Ineffective mark-compacts near heap limit
```

**Fix:**
```bash
# Increase Node memory during build (on server)
ssh root@91.99.212.17
cd /opt/bonifatus-dms-dev

# Edit Dockerfile to increase Node memory
# Or build with more resources:
docker compose build frontend --memory=2g
docker compose up -d frontend
```

---

### Issue 4: Backend Out of Memory (libpostal)

**Symptoms:**
```
net::ERR_FAILED 524
CORS policy errors (even though API URL is correct)
```

**Root Cause:** Backend ran out of memory (libpostal language models need 5GB)

**Verify:**
```bash
# Check backend memory usage
docker stats bonifatus-backend-dev --no-stream

# Should show < 90% of memory limit
```

**Fix:**
```bash
# Memory limit is in docker-compose.yml
# Current: 5G (increased from 3G for libpostal)
# If needed, increase to 6G and rebuild
```

---

### Issue 5: Nginx Not Reloaded (Dev Access Lost)

**Symptoms:** Can't access dev.bonidoc.com after deployment

**Root Cause:** Forgot to reload nginx after container restart

**Fix:**
```bash
ssh root@91.99.212.17
nginx -t && systemctl reload nginx
```

**Prevention:** Always run `nginx -t && systemctl reload nginx` after dev deployment

---

### Issue 6: IP Whitelist - Access Blocked with 403 Forbidden

**Symptoms:**
```
Failed to load documents/categories
CORS errors with 403 Forbidden
Nginx error: "access forbidden by rule, client: YOUR_IP"
```

**Root Cause:** Your IP address is not in the nginx whitelist for dev environment

**Check nginx error logs:**
```bash
ssh root@91.99.212.17
tail -50 /var/log/nginx/error.log | grep "forbidden by rule"
```

**Find your current IP:**
```powershell
# On Windows PC:
ipconfig
# Look for IPv4 Address and IPv6 Address

# Or check public IP:
curl https://api.ipify.org
```

**Add IP to whitelist:**
```bash
ssh root@91.99.212.17

# Backup config first
cp /etc/nginx/sites-enabled/dev.bonidoc.com /etc/nginx/sites-enabled/dev.bonidoc.com.backup

# Add IPv4 (replace with your IP)
sed -i '/allow 93.197.148.73;  # Home PC IPv4/a\    allow YOUR_IP_HERE;  # Current connection' /etc/nginx/sites-enabled/dev.bonidoc.com

# Or edit manually
nano /etc/nginx/sites-enabled/dev.bonidoc.com
# Find the "allow" lines and add your IP in both server blocks

# Test configuration
nginx -t

# Reload nginx
systemctl reload nginx
```

**Current Whitelisted IPs:**
- IPv4: `93.197.148.73` (home PC)
- IPv6: `2003:fb:f0b::/32` (IPv6 range)

**Whitelist Location:**
`/etc/nginx/sites-enabled/dev.bonidoc.com` (both frontend and API server blocks)

**For IPv6 subnet changes:**
If your IPv6 subnet changes (common with dynamic IPv6):
```bash
# Check current whitelist
grep "allow 2003" /etc/nginx/sites-enabled/dev.bonidoc.com

# Update to new subnet (replace with your subnet)
sed -i 's|2003:fb:f0e:fc6a::/64|2003:fb:f0b:YOUR_SUBNET::/64|g' /etc/nginx/sites-enabled/dev.bonidoc.com

# Reload nginx
nginx -t && systemctl reload nginx
```

---

### Issue 7: Database Migrations Not Applied

**Symptoms:**
- New features not working
- Database errors in logs

**Fix:**
```bash
# Dev
ssh root@91.99.212.17
docker exec bonifatus-backend-dev alembic current
docker exec bonifatus-backend-dev alembic upgrade head

# Prod
docker exec bonifatus-backend alembic current
docker exec bonifatus-backend alembic upgrade head
```

---

## Critical Configuration Differences

### Docker Compose - Frontend Build Args

**⚠️ CRITICAL:** Dev and Prod MUST have different API URLs

**Dev (`/opt/bonifatus-dms-dev/docker-compose.yml`):**
```yaml
frontend:
  build:
    context: ./frontend
    args:
      NEXT_PUBLIC_API_URL: https://api-dev.bonidoc.com  # ⚠️ DEV API
  container_name: bonifatus-frontend-dev                # ⚠️ -dev suffix
  ports:
    - "3001:3000"                                        # ⚠️ Port 3001
```

**Prod (`/opt/bonifatus-dms/docker-compose.yml`):**
```yaml
frontend:
  build:
    context: ./frontend
    args:
      NEXT_PUBLIC_API_URL: https://api.bonidoc.com      # ⚠️ PROD API
  container_name: bonifatus-frontend                     # ⚠️ No suffix
  ports:
    - "3000:3000"                                        # ⚠️ Port 3000
```

### Environment Variables

**Files that differ between dev and prod:**
- `.env` - Contains environment-specific secrets
- `docker-compose.yml` - Contains environment-specific ports/names/URLs

**⚠️ NEVER copy these files between dev and prod!**

See `DEV_TO_PROD_MIGRATION.md` for full list of variables that must differ.

---

## Quick Diagnostic Commands

```bash
# Check which API frontend is calling
ssh root@91.99.212.17
curl -s https://dev.bonidoc.com | grep -o 'api[^"]*bonidoc.com' | head -1
# Should show: api-dev.bonidoc.com

# Check container status
docker compose ps

# Check backend logs for errors
docker compose logs --tail=100 backend | grep -i error

# Check frontend build logs
docker compose logs frontend | grep "NEXT_PUBLIC_API_URL"

# Check database migration status
docker exec bonifatus-backend-dev alembic current

# Check backend memory usage
docker stats bonifatus-backend-dev --no-stream

# Test backend health
curl https://api-dev.bonidoc.com/health

# Test frontend health
curl -I https://dev.bonidoc.com
```

---

## When to Use --no-cache

**Default (with cache):** `docker compose build`
- Use for: Regular code changes (99% of deployments)
- Time: 2-3 minutes
- Your code changes WILL be deployed

**No cache:** `docker compose build --no-cache`
- Use for:
  - Monthly maintenance
  - Dockerfile base image changes
  - System package updates
  - Persistent build issues
- Time: 15-20 minutes

**⚠️ Don't overthink it:** Use default `docker compose build` unless you changed the Dockerfile itself.

---

## Rollback Procedure

If deployment breaks production:

```bash
ssh root@91.99.212.17
cd /opt/bonifatus-dms

# Find last working commit
git log --oneline -10

# Rollback to previous commit
git reset --hard <commit-hash>

# Rebuild and restart
docker compose build
docker compose up -d

# Verify
curl https://api.bonidoc.com/health
```

---

## Notes

- **Always deploy to dev first, then prod**
- **Always reload nginx after dev deployment**
- **Always verify API URL in docker-compose.yml**
- **Never copy .env or docker-compose.yml between environments**
- **Check HETZNER_SETUP_ACTUAL.md for server credentials**
- **See deployment_guide.md for detailed explanations**

---

## Quick Checklist

**Before Deployment:**
- [ ] Code committed and pushed to main
- [ ] No hardcoded values in code
- [ ] New dependencies added to requirements.txt / package.json

**Dev Deployment:**
- [ ] SSH to 91.99.212.17 (see HETZNER_SETUP_ACTUAL.md)
- [ ] cd /opt/bonifatus-dms-dev
- [ ] git pull origin main
- [ ] docker compose build
- [ ] docker compose up -d
- [ ] nginx -t && systemctl reload nginx
- [ ] docker compose ps (verify healthy)
- [ ] Test on dev.bonidoc.com

**Prod Deployment (only after dev testing):**
- [ ] cd /opt/bonifatus-dms
- [ ] git pull origin main
- [ ] docker compose build
- [ ] docker compose up -d
- [ ] docker compose ps (verify healthy)
- [ ] Test on bonidoc.com
- [ ] Monitor logs for errors

---

**For detailed explanations, see:**
- Server setup: `HETZNER_SETUP_ACTUAL.md`
- Full deployment guide: `deployment_guide.md`
- Dev/Prod differences: `DEV_TO_PROD_MIGRATION.md`
