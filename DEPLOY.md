# Quick Deployment Guide

**Last Updated:** 2025-12-20
**Server Access:** See `HETZNER_SETUP_ACTUAL.md` for credentials and detailed server setup

> **Important:** This document references configurations from `HETZNER_SETUP_ACTUAL.md`.
> Always check both files for complete deployment context.

---

## Quick Reference

| Environment | Directory | URL | API URL | Ports | Config Source |
|------------|-----------|-----|---------|-------|---------------|
| **Dev** | `/opt/bonifatus-dms-dev` | https://dev.bonidoc.com | https://api-dev.bonidoc.com | 3001/8081/5001 | `.env` file |
| **Prod** | `/opt/bonifatus-dms` | https://bonidoc.com | https://api.bonidoc.com | 3000/8080/5000 | Environment variables |

**Server IP:** 91.99.212.17 (see HETZNER_SETUP_ACTUAL.md)

**Key Differences:**
- **Dev:** Uses `.env` file, requires nginx reload after deployment, ClamAV disabled
- **Prod:** Uses system environment variables, ClamAV enabled

---

## ONE-COMMAND DEPLOYMENT SEQUENCES

### Deploy to DEV (Single Command - Recommended)

**Simple, reliable deployment that works every time:**

```bash
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && \
  echo "=== [1/8] Pulling latest code ===" && \
  git pull origin main && \
  echo "=== [2/8] Building containers ===" && \
  docker compose build && \
  echo "=== [3/8] Stopping containers ===" && \
  docker compose down && \
  echo "=== [4/8] Running migrations ===" && \
  docker compose run --rm backend alembic upgrade head && \
  echo "=== [5/8] Starting containers ===" && \
  docker compose up -d && \
  sleep 10 && \
  echo "=== [6/8] Reloading nginx ===" && \
  nginx -t && systemctl reload nginx && \
  echo "=== [7/8] Health checks ===" && \
  docker compose ps && \
  echo "" && \
  curl -s https://api-dev.bonidoc.com/health && \
  echo "" && \
  echo "=== [8/8] Backend logs ===" && \
  docker logs bonifatus-backend-dev --tail 20'
```

**Expected Output:**
- All 8 steps complete without errors
- Containers show "Up (healthy)" status
- Backend health returns: `{"status":"healthy","environment":"development"}`
- No errors in backend logs

**Time:** ~3-5 minutes (depending on build cache)

**If you need step-by-step deployment (for debugging):**

Run commands individually:
```bash
# 1. Pull latest code
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && git pull origin main'

# 2. Build containers
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && docker compose build'

# 3. Stop containers
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && docker compose down'

# 4. Run migrations
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && docker compose run --rm backend alembic upgrade head'

# 5. Start containers
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && docker compose up -d'

# 6. Wait and reload nginx
sleep 10
ssh root@91.99.212.17 'nginx -t && systemctl reload nginx'

# 7. Check health
ssh root@91.99.212.17 'docker compose ps && curl -s https://api-dev.bonidoc.com/health'
```

**Common Issues:**

1. **403 Forbidden on frontend/API**: Your IP is not whitelisted
   ```bash
   # Check current IP blocks
   ssh root@91.99.212.17 "tail -20 /var/log/nginx/error.log | grep 'access forbidden'"

   # Add your IP to whitelist
   ssh root@91.99.212.17 "nano /etc/nginx/sites-enabled/dev.bonidoc.com"
   # Add: allow YOUR_IP_HERE;  # Description

   # Reload nginx
   ssh root@91.99.212.17 "nginx -t && systemctl reload nginx"
   ```

2. **502 Bad Gateway**: Port mismatch (should be auto-fixed in step 7, but if not):
   ```bash
   ssh root@91.99.212.17 "sed -i 's|proxy_pass http://localhost:3000;|proxy_pass http://localhost:3001;|g' /etc/nginx/sites-enabled/dev.bonidoc.com && nginx -t && systemctl reload nginx"
   ```

3. **Other errors**: Re-run the deployment sequence or continue manually from the failed step

---

### Deploy to PROD (Single Command)

**⚠️ PRODUCTION DEPLOYMENT - Only run after successful dev testing!**

```bash
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && \
  echo "=== [1/8] Pulling latest code ===" && \
  git pull origin main && \
  echo "=== [2/8] Building containers ===" && \
  docker compose build && \
  echo "=== [3/8] Stopping containers ===" && \
  docker compose down && \
  echo "=== [4/8] Running migrations ===" && \
  docker compose run --rm backend alembic upgrade head && \
  echo "=== [5/8] Starting containers ===" && \
  docker compose up -d && \
  sleep 15 && \
  echo "=== [6/8] Reloading nginx ===" && \
  nginx -t && systemctl reload nginx && \
  echo "=== [7/8] Health checks ===" && \
  docker compose ps && \
  echo "" && \
  curl -s https://api.bonidoc.com/health && \
  echo "" && \
  echo "=== [8/8] Backend logs ===" && \
  docker logs bonifatus-backend --tail 20'
```

**Expected Output:**
- All 8 steps complete without errors
- Containers show "Up (healthy)"
- Backend health returns: `{"status":"healthy","environment":"production"}`
- ClamAV shows as enabled/running
- No errors in backend logs

**Time:** ~3-5 minutes (depending on build cache)

**⚠️ Production Safety Rules:**
1. **ALWAYS** test in dev first
2. **NEVER** fix directly in prod - fix in dev, test, then deploy
3. If deployment fails, check logs and rollback if needed
4. Monitor application for 5-10 minutes after deployment

---

### Deploy to BOTH (Dev → Test → Prod)

**Complete deployment cycle with testing pause:**

```bash
# Step 1: Deploy to DEV
ssh root@91.99.212.17 'cd /opt/bonifatus-dms-dev && \
  git pull origin main && \
  docker compose build && \
  docker compose down && \
  docker compose run --rm backend alembic upgrade head && \
  docker compose up -d && \
  sleep 10 && \
  nginx -t && systemctl reload nginx'

# Step 2: TEST ON DEV
# Open https://dev.bonidoc.com and verify:
# - Login works
# - Document upload works
# - All new features work as expected
# - Check browser console for errors

# Step 3: Deploy to PROD (only if dev testing passed)
ssh root@91.99.212.17 'cd /opt/bonifatus-dms && \
  git pull origin main && \
  docker compose build && \
  docker compose down && \
  docker compose run --rm backend alembic upgrade head && \
  docker compose up -d && \
  sleep 15 && \
  nginx -t && systemctl reload nginx'

# Step 4: VERIFY PROD
# Open https://bonidoc.com and verify deployment was successful
```

---

## Standard Deployment Workflow (Step-by-Step)

Use this when you need more control or if the one-command sequence fails.

### Step 1: Local - Commit and Push

```bash
# Commit your changes
git add -A
git commit -m "Your commit message

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to GitHub
git push origin main
```

### Step 2: Deploy to Dev (ALWAYS TEST FIRST!)

```bash
# SSH to server
ssh root@91.99.212.17

# Navigate to dev directory
cd /opt/bonifatus-dms-dev

# Check git status
git status

# Stash local changes (dev-specific API URL)
git stash

# Pull latest code
git pull origin main

# Restore dev configuration
git stash pop

# Handle conflicts if needed:
# Edit docker-compose.yml and ensure: NEXT_PUBLIC_API_URL: https://api-dev.bonidoc.com
# Then: git add docker-compose.yml && git stash drop

# Rebuild containers
docker compose build

# Restart containers
docker compose up -d

# ⚠️ CRITICAL: ALWAYS RELOAD NGINX AFTER DEV DEPLOYMENT
nginx -t && systemctl reload nginx
echo "✓ Nginx reloaded"

# Check status
docker compose ps

# Verify health
curl https://api-dev.bonidoc.com/health

# Check logs for errors
docker logs bonifatus-backend-dev --tail 50
```

**Expected output:**
```
bonifatus-backend-dev      Up (healthy)    8081->8080
bonifatus-frontend-dev     Up              3001->3000
bonifatus-redis-dev        Up (healthy)    6380->6379
bonifatus-translator-dev   Up              5001->5000
```

### Step 3: Test on Dev

1. Open browser to https://dev.bonidoc.com
2. Test all new functionality
3. Check browser console for errors
4. Verify database changes

### Step 4: Deploy to Production (Only After Dev Testing!)

```bash
# Still on server as root@91.99.212.17

# Navigate to production directory
cd /opt/bonifatus-dms

# Pull latest code
git pull origin main

# Rebuild containers
docker compose build

# Restart containers
docker compose up -d

# Run migrations
docker exec bonifatus-backend alembic upgrade head

# Check status
docker compose ps

# Verify health
curl https://api.bonidoc.com/health

# Check ClamAV (prod only)
docker logs bonifatus-backend --tail 50 | grep -i clamav

# Check for errors
docker logs bonifatus-backend --tail 50 | grep -i error
```

**Expected output:**
```
bonifatus-backend      Up (healthy)    8080->8080
bonifatus-frontend     Up              3000->3000
bonifatus-redis        Up (healthy)    6379->6379
bonifatus-translator   Up              5000->5000
```

### Step 5: Verify Production

1. Open https://bonidoc.com
2. Test critical functionality
3. Monitor logs: `docker logs bonifatus-backend -f`

---

## Error Handling During Deployment

### If Build Fails

```bash
# Check which service failed
docker compose ps

# Check build logs
docker compose logs frontend
docker compose logs backend

# Common fixes:
# 1. Frontend memory issue:
docker compose build frontend --no-cache

# 2. Backend dependencies:
docker compose build backend --no-cache

# 3. Clear all and rebuild:
docker compose down
docker compose build --no-cache
docker compose up -d
```

### If Container Won't Start

```bash
# Check logs for the failing container
docker logs bonifatus-backend-dev --tail 100

# Common issues:
# - Port already in use: Check docker compose ps, stop conflicting container
# - Memory limit: Check docker stats, increase memory in docker-compose.yml
# - Missing env vars: Check .env file (dev) or environment variables (prod)

# Restart specific container
docker compose restart backend

# Or restart all
docker compose down && docker compose up -d
```

### If Health Check Fails

```bash
# Check what the health endpoint returns
curl -v https://api-dev.bonidoc.com/health

# Common issues:
# - 502/504: Backend not responding - check logs
# - 403: IP whitelist - add your IP to nginx config
# - CORS: Wrong API URL in frontend build
# - 500: Backend error - check logs for stack trace

# Quick fixes:
# 1. Check backend is actually running:
docker ps | grep backend

# 2. Check backend logs:
docker logs bonifatus-backend-dev --tail 100

# 3. Restart backend:
docker compose restart backend
```

### Nginx Issues (Common After Deployment)

#### Issue 1: 403 Forbidden (IP Whitelist)

**Symptoms:**
```
HTTP/2 403
access forbidden by rule, client: X.X.X.X
```

**Fix:**
```bash
# Get your current IP from nginx error logs
ssh root@91.99.212.17 "tail -50 /var/log/nginx/error.log | grep 'access forbidden' | tail -5"

# Add your IP to dev whitelist
ssh root@91.99.212.17 "nano /etc/nginx/sites-enabled/dev.bonidoc.com"
# Navigate to the IP whitelist section (around line 45-60)
# Add your IP: allow YOUR_IP_HERE;  # Description

# For IPv4 addresses:
allow 1.2.3.4;  # Your description

# For IPv6 addresses:
allow 2001:db8::1;  # Your description

# Test and reload
ssh root@91.99.212.17 "nginx -t && systemctl reload nginx"

# Verify access
curl -I https://dev.bonidoc.com
```

**Permanent Fix (add server localhost to whitelist):**
```bash
# Add server's own IP for health checks
ssh root@91.99.212.17 "sed -i '/allow 216.131.111.81/a \    allow 2a01:4f8:c17:bbd1::1;  # Server localhost IPv6' /etc/nginx/sites-enabled/dev.bonidoc.com && nginx -t && systemctl reload nginx"
```

#### Issue 2: 502 Bad Gateway (Port Mismatch)

**Symptoms:**
```
HTTP/2 502
curl: (52) Empty reply from server
```

**Cause:** Nginx is proxying to wrong port (3000 instead of 3001 for dev)

**Automatic Fix (recommended):**
```bash
ssh root@91.99.212.17 "cd /opt/bonifatus-dms-dev && \
  FRONTEND_PORT=\$(docker compose ps | grep frontend-dev | awk '{print \$NF}' | cut -d':' -f1 | cut -d'>' -f1) && \
  sed -i \"s|proxy_pass http://localhost:[0-9]*;|proxy_pass http://localhost:\$FRONTEND_PORT;|g\" /etc/nginx/sites-enabled/dev.bonidoc.com && \
  nginx -t && systemctl reload nginx && \
  echo 'Port fixed to \$FRONTEND_PORT'"
```

**Manual Fix:**
```bash
# Check what port frontend is running on
ssh root@91.99.212.17 "docker compose ps | grep frontend-dev"
# Should show: 0.0.0.0:3001->3000/tcp

# Fix nginx config to use 3001
ssh root@91.99.212.17 "sed -i 's|proxy_pass http://localhost:3000;|proxy_pass http://localhost:3001;|g' /etc/nginx/sites-enabled/dev.bonidoc.com && nginx -t && systemctl reload nginx"

# Verify
curl -I https://dev.bonidoc.com
```

#### Issue 3: Nginx Won't Reload

**Symptoms:**
```
nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
```

**Fix:**
```bash
# Check what's using port 80/443
ssh root@91.99.212.17 "netstat -tlnp | grep ':80\|:443'"

# Kill conflicting process (if safe)
ssh root@91.99.212.17 "systemctl stop nginx && sleep 2 && systemctl start nginx"
```

#### Issue 4: Config Syntax Error

**Symptoms:**
```
nginx: [emerg] unexpected "}" in /etc/nginx/sites-enabled/dev.bonidoc.com:123
```

**Fix:**
```bash
# Test config syntax
ssh root@91.99.212.17 "nginx -t"

# Check recent changes
ssh root@91.99.212.17 "tail -50 /etc/nginx/sites-enabled/dev.bonidoc.com"

# Restore from backup if needed
ssh root@91.99.212.17 "ls -la /etc/nginx/sites-enabled/*.backup*"
ssh root@91.99.212.17 "cp /etc/nginx/sites-enabled/dev.bonidoc.com.backup /etc/nginx/sites-enabled/dev.bonidoc.com"
```

#### Nginx Quick Diagnostic Commands

```bash
# Check nginx status
ssh root@91.99.212.17 "systemctl status nginx"

# Test config syntax
ssh root@91.99.212.17 "nginx -t"

# View error logs
ssh root@91.99.212.17 "tail -50 /var/log/nginx/error.log"

# Check access logs
ssh root@91.99.212.17 "tail -50 /var/log/nginx/access.log"

# View current port configuration
ssh root@91.99.212.17 "grep 'proxy_pass' /etc/nginx/sites-enabled/dev.bonidoc.com"

# View IP whitelist
ssh root@91.99.212.17 "grep -A 20 'IP Whitelist' /etc/nginx/sites-enabled/dev.bonidoc.com"

# Verify frontend container port
ssh root@91.99.212.17 "docker compose ps | grep frontend"
```

---

## Configuration Differences: Dev vs Prod

### Environment Variables

**DEV:** Uses `.env` file in `/opt/bonifatus-dms-dev/backend/.env`
```bash
# View dev env vars
cat /opt/bonifatus-dms-dev/backend/.env | grep -v PASSWORD
```

**PROD:** Uses system environment variables
```bash
# Set via systemd service or docker-compose environment section
# Never stored in files for security
```

### Docker Compose Differences

**Key differences to maintain:**

| Setting | Dev | Prod |
|---------|-----|------|
| Container names | `*-dev` suffix | No suffix |
| API URL | `api-dev.bonidoc.com` | `api.bonidoc.com` |
| Ports | 3001/8081/5001 | 3000/8080/5000 |
| ClamAV | Disabled | Enabled |
| Memory limits | 5GB backend | 6GB backend |

### Nginx Configuration Management

**DEV:** Requires nginx verification and reload after deployment

**Why nginx needs attention on dev:**
1. Docker container restart can change port mappings
2. Nginx proxy configuration may get out of sync with container ports
3. IP whitelisting blocks unauthorized access

**Automatic Fix (built into deployment sequence):**
The enhanced dev deployment sequence (steps 7-10) now includes:
- Automatic port verification
- Auto-correction of port mismatches
- Frontend accessibility verification
- Health check validation

**Manual Nginx Management:**
```bash
# Verify and reload nginx (always safe to run)
ssh root@91.99.212.17 "nginx -t && systemctl reload nginx"

# Check if nginx port matches container port
ssh root@91.99.212.17 "
  cd /opt/bonifatus-dms-dev && \
  echo 'Container port:' && docker compose ps | grep frontend-dev | awk '{print \$NF}' && \
  echo 'Nginx proxy port:' && grep 'proxy_pass' /etc/nginx/sites-enabled/dev.bonidoc.com | grep -v '#'
"

# Auto-fix port mismatch
ssh root@91.99.212.17 "cd /opt/bonifatus-dms-dev && \
  FRONTEND_PORT=\$(docker compose ps | grep frontend-dev | awk '{print \$NF}' | cut -d':' -f1 | cut -d'>' -f1) && \
  sed -i \"s|proxy_pass http://localhost:[0-9]*;|proxy_pass http://localhost:\$FRONTEND_PORT;|g\" /etc/nginx/sites-enabled/dev.bonidoc.com && \
  nginx -t && systemctl reload nginx"
```

**PROD:** Nginx reload not typically required (different network setup, stable port mapping)

**Common Nginx Issues:**
- See "Nginx Issues (Common After Deployment)" section for detailed troubleshooting

---

## Health Check Commands

### Backend Health
```bash
# Dev
curl https://api-dev.bonidoc.com/health
# Should return: {"status":"healthy","environment":"development"}

# Prod
curl https://api.bonidoc.com/health
# Should return: {"status":"healthy","environment":"production"}
```

### Frontend Health
```bash
# Dev
curl -I https://dev.bonidoc.com
# Should return: HTTP/2 200

# Prod
curl -I https://bonidoc.com
# Should return: HTTP/2 200
```

### Database Health
```bash
# Dev
docker exec bonifatus-backend-dev alembic current
# Shows current migration version

# Prod
docker exec bonifatus-backend alembic current
```

### ClamAV Health (Prod Only)
```bash
# Check if ClamAV is running
docker exec bonifatus-backend curl localhost:8080/health | grep -i clamav
# Should show: clamav_status: "running"
```

### Full System Health
```bash
# Dev
docker compose -f /opt/bonifatus-dms-dev/docker-compose.yml ps
docker stats --no-stream

# Prod
docker compose -f /opt/bonifatus-dms/docker-compose.yml ps
docker stats --no-stream
```

---

## Rollback Procedure

If deployment breaks production:

```bash
ssh root@91.99.212.17
cd /opt/bonifatus-dms

# Find last working commit
git log --oneline -10

# Rollback code
git reset --hard <commit-hash>

# Rebuild and restart
docker compose build
docker compose up -d

# Verify
curl https://api.bonidoc.com/health
docker compose ps

# If database migrations need rollback:
docker exec bonifatus-backend alembic downgrade -1
```

**For dev rollback:** Same process in `/opt/bonifatus-dms-dev` + remember to reload nginx

---

## Common Issues and Fixes

### Issue 1: CORS Errors - Frontend Calling Wrong API

**Symptoms:**
```
Access to fetch at 'https://api.bonidoc.com' from origin 'https://dev.bonidoc.com'
has been blocked by CORS policy
```

**Fix:**
```bash
cd /opt/bonifatus-dms-dev

# Verify API URL
grep "NEXT_PUBLIC_API_URL" docker-compose.yml
# Should show: https://api-dev.bonidoc.com

# If wrong, fix and rebuild frontend
docker compose build frontend
docker compose up -d frontend
nginx -t && systemctl reload nginx
```

### Issue 2: Dev Site Inaccessible After Deployment

**Fix:**
```bash
# Always reload nginx after dev deployment
nginx -t && systemctl reload nginx
```

### Issue 3: Container Name Conflicts

**Fix:**
```bash
# Verify dev containers have -dev suffix
cd /opt/bonifatus-dms-dev
grep "container_name:" docker-compose.yml

# Should show: bonifatus-backend-dev, etc.
```

### Issue 4: Memory Issues (libpostal)

**Symptoms:**
```
Backend logs: "Killed"
HTTP 502/524 errors
```

**Fix:**
```bash
# Check memory usage
docker stats bonifatus-backend-dev --no-stream

# Increase in docker-compose.yml if needed:
# mem_limit: 6g
```

---

## Quick Diagnostic Commands

```bash
# Container status
docker compose ps

# Backend logs
docker logs bonifatus-backend-dev --tail 100 | grep -i error

# Frontend build verification
docker logs bonifatus-frontend-dev | grep NEXT_PUBLIC_API_URL

# Database migration status
docker exec bonifatus-backend-dev alembic current

# Memory usage
docker stats --no-stream

# Nginx config test
nginx -t

# Check which API frontend is calling
curl -s https://dev.bonidoc.com | grep -o 'api[^"]*bonidoc.com' | head -1
```

---

## Deployment Checklist

**Before Any Deployment:**
- [ ] Code committed and pushed to main
- [ ] No hardcoded values or secrets in code
- [ ] Dependencies added to requirements.txt/package.json
- [ ] Environment variables configured (dev: .env, prod: env vars)

**Dev Deployment:**
- [ ] Run consolidated dev deployment command
- [ ] Verify health check passes
- [ ] Test on https://dev.bonidoc.com
- [ ] Check browser console for errors
- [ ] Verify new features work correctly

**Prod Deployment (only after dev testing):**
- [ ] Dev testing completed and passed
- [ ] Run consolidated prod deployment command
- [ ] Verify health check passes
- [ ] Check ClamAV status (should be enabled)
- [ ] Test on https://bonidoc.com
- [ ] Monitor logs for 5-10 minutes
- [ ] Verify critical user flows work

---

## Notes

- **Always deploy to dev first, test, then prod**
- **Use one-command sequences for consistent deployments**
- **Deployment sequence will stop on errors - fix and retry**
- **Dev requires nginx reload, prod does not**
- **Dev uses .env file, prod uses environment variables**
- **ClamAV is disabled on dev, enabled on prod**
- **Check HETZNER_SETUP_ACTUAL.md for server access and detailed setup**

---

**For More Information:**
- Server setup details: `HETZNER_SETUP_ACTUAL.md`
- Dev/Prod configuration differences: `DEV_TO_PROD_MIGRATION.md`
- Full deployment explanations: `deployment_guide.md` (if exists)
